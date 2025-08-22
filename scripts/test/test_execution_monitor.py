#!/usr/bin/env python3
"""
测试执行监控器
- 监控测试进程的执行状态
- 自动检测失败和超时
- 与失败测试管理器集成
"""

import subprocess
import time
import signal
import psutil
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enhanced_failed_tests_manager import EnhancedFailedTestsManager

@dataclass
class TestProcess:
    """测试进程信息"""
    pid: int
    model: str
    group_name: str
    prompt_types: str
    command: List[str]
    start_time: datetime
    timeout: int = 7200  # 2小时默认超时
    status: str = "running"  # running, completed, failed, timeout
    exit_code: Optional[int] = None
    
class TestExecutionMonitor:
    """测试执行监控器"""
    
    def __init__(self, failed_manager: EnhancedFailedTestsManager = None):
        self.failed_manager = failed_manager or EnhancedFailedTestsManager()
        self.active_processes: Dict[int, TestProcess] = {}
        self.monitor_thread = None
        self.stop_monitoring = threading.Event()
        self.callbacks = {
            "on_success": [],
            "on_failure": [], 
            "on_timeout": [],
            "on_start": []
        }
        
    def add_callback(self, event_type: str, callback: Callable):
        """添加事件回调"""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
    
    def start_monitoring(self):
        """开始监控"""
        if self.monitor_thread is None or not self.monitor_thread.is_alive():
            self.stop_monitoring.clear()
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            print("🔍 测试监控器已启动")
    
    def stop_monitoring_all(self):
        """停止监控"""
        self.stop_monitoring.set()
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        print("⏹️  测试监控器已停止")
    
    def register_test_process(self, process: subprocess.Popen, model: str, 
                            group_name: str, prompt_types: str, timeout: int = 7200):
        """注册测试进程"""
        test_process = TestProcess(
            pid=process.pid,
            model=model,
            group_name=group_name,
            prompt_types=prompt_types,
            command=process.args if hasattr(process, 'args') else [],
            start_time=datetime.now(),
            timeout=timeout
        )
        
        self.active_processes[process.pid] = test_process
        
        # 触发启动回调
        for callback in self.callbacks["on_start"]:
            try:
                callback(test_process)
            except Exception as e:
                print(f"启动回调错误: {e}")
        
        print(f"📝 注册测试进程: PID {process.pid} - {model} - {group_name}")
        
        # 确保监控正在运行
        self.start_monitoring()
        
        return test_process
    
    def _monitor_loop(self):
        """监控循环"""
        while not self.stop_monitoring.is_set():
            try:
                self._check_processes()
                time.sleep(10)  # 每10秒检查一次
            except Exception as e:
                print(f"监控循环错误: {e}")
                time.sleep(5)
    
    def _check_processes(self):
        """检查所有进程状态"""
        current_time = datetime.now()
        completed_pids = []
        
        for pid, test_process in self.active_processes.items():
            try:
                # 检查进程是否还存在
                if not psutil.pid_exists(pid):
                    # 进程已结束，检查退出状态
                    self._handle_process_completion(test_process)
                    completed_pids.append(pid)
                    continue
                
                # 检查超时
                if current_time - test_process.start_time > timedelta(seconds=test_process.timeout):
                    self._handle_process_timeout(test_process)
                    completed_pids.append(pid)
                    continue
                
                # 检查进程状态
                try:
                    process = psutil.Process(pid)
                    if process.status() == psutil.STATUS_ZOMBIE:
                        self._handle_process_completion(test_process)
                        completed_pids.append(pid)
                        continue
                except psutil.NoSuchProcess:
                    self._handle_process_completion(test_process)
                    completed_pids.append(pid)
                    continue
                    
            except Exception as e:
                print(f"检查进程 {pid} 时出错: {e}")
        
        # 清理已完成的进程
        for pid in completed_pids:
            del self.active_processes[pid]
    
    def _handle_process_completion(self, test_process: TestProcess):
        """处理进程完成"""
        try:
            # 尝试获取退出码
            if psutil.pid_exists(test_process.pid):
                process = psutil.Process(test_process.pid)
                exit_code = process.wait(timeout=1)
            else:
                # 进程已不存在，假设正常退出
                exit_code = 0
        except:
            exit_code = None
        
        test_process.exit_code = exit_code
        
        if exit_code == 0:
            # 成功完成
            test_process.status = "completed"
            self._handle_success(test_process)
        else:
            # 失败
            test_process.status = "failed"
            self._handle_failure(test_process, f"进程退出码: {exit_code}")
    
    def _handle_process_timeout(self, test_process: TestProcess):
        """处理进程超时"""
        test_process.status = "timeout"
        
        # 尝试终止进程
        try:
            if psutil.pid_exists(test_process.pid):
                process = psutil.Process(test_process.pid)
                process.terminate()
                time.sleep(5)
                if process.is_running():
                    process.kill()
        except Exception as e:
            print(f"终止超时进程 {test_process.pid} 失败: {e}")
        
        self._handle_timeout(test_process)
    
    def _handle_success(self, test_process: TestProcess):
        """处理测试成功"""
        print(f"✅ 测试成功: {test_process.model} - {test_process.group_name}")
        
        # 检查是否是重测成功
        was_retry = len(self.failed_manager.get_failed_tests_for_model(test_process.model)) > 0
        self.failed_manager.record_test_success(
            test_process.model, 
            test_process.group_name, 
            was_retry=was_retry
        )
        
        # 触发成功回调
        for callback in self.callbacks["on_success"]:
            try:
                callback(test_process)
            except Exception as e:
                print(f"成功回调错误: {e}")
    
    def _handle_failure(self, test_process: TestProcess, reason: str):
        """处理测试失败"""
        print(f"❌ 测试失败: {test_process.model} - {test_process.group_name}")
        print(f"   失败原因: {reason}")
        
        # 记录失败
        self.failed_manager.record_test_failure(
            model=test_process.model,
            group_name=test_process.group_name,
            prompt_types=test_process.prompt_types,
            test_type="workflow_test",
            failure_reason=reason
        )
        
        # 触发失败回调
        for callback in self.callbacks["on_failure"]:
            try:
                callback(test_process, reason)
            except Exception as e:
                print(f"失败回调错误: {e}")
    
    def _handle_timeout(self, test_process: TestProcess):
        """处理测试超时"""
        timeout_minutes = test_process.timeout // 60
        reason = f"测试超时 ({timeout_minutes}分钟)"
        
        print(f"⏰ 测试超时: {test_process.model} - {test_process.group_name}")
        
        # 记录超时失败
        self.failed_manager.record_test_failure(
            model=test_process.model,
            group_name=test_process.group_name,
            prompt_types=test_process.prompt_types,
            test_type="workflow_test",
            failure_reason=reason
        )
        
        # 触发超时回调
        for callback in self.callbacks["on_timeout"]:
            try:
                callback(test_process)
            except Exception as e:
                print(f"超时回调错误: {e}")
    
    def get_active_processes(self) -> List[TestProcess]:
        """获取当前活跃的进程"""
        return list(self.active_processes.values())
    
    def kill_all_processes(self):
        """终止所有活跃进程"""
        print("🛑 终止所有测试进程...")
        
        for pid, test_process in self.active_processes.items():
            try:
                if psutil.pid_exists(pid):
                    process = psutil.Process(pid)
                    process.terminate()
                    print(f"   终止进程: PID {pid} - {test_process.model}")
            except Exception as e:
                print(f"   终止进程 {pid} 失败: {e}")
        
        # 等待进程终止
        time.sleep(3)
        
        # 强制杀死仍在运行的进程
        for pid, test_process in self.active_processes.items():
            try:
                if psutil.pid_exists(pid):
                    process = psutil.Process(pid)
                    if process.is_running():
                        process.kill()
                        print(f"   强制杀死进程: PID {pid}")
            except Exception as e:
                print(f"   强制杀死进程 {pid} 失败: {e}")
        
        self.active_processes.clear()
    
    def show_monitoring_status(self):
        """显示监控状态"""
        print("=" * 50)
        print("🔍 测试执行监控状态")
        print("=" * 50)
        
        print(f"活跃进程数: {len(self.active_processes)}")
        print(f"监控状态: {'运行中' if self.monitor_thread and self.monitor_thread.is_alive() else '已停止'}")
        print()
        
        if self.active_processes:
            print("📋 当前测试进程:")
            for pid, test_process in self.active_processes.items():
                runtime = datetime.now() - test_process.start_time
                timeout_remaining = test_process.timeout - runtime.total_seconds()
                
                print(f"  PID {pid}: {test_process.model} - {test_process.group_name}")
                print(f"    运行时间: {runtime}")
                print(f"    剩余时间: {int(timeout_remaining//60)}分钟")
                print(f"    状态: {test_process.status}")
                print()

# 创建全局监控器实例
_global_monitor = None

def get_global_monitor() -> TestExecutionMonitor:
    """获取全局监控器实例"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = TestExecutionMonitor()
    return _global_monitor

def monitor_test_command(command: List[str], model: str, group_name: str, 
                        prompt_types: str, timeout: int = 7200) -> subprocess.Popen:
    """监控测试命令执行"""
    monitor = get_global_monitor()
    
    # 启动进程
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # 注册到监控器
    monitor.register_test_process(process, model, group_name, prompt_types, timeout)
    
    return process

if __name__ == "__main__":
    import sys
    
    monitor = get_global_monitor()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "status":
            monitor.show_monitoring_status()
        elif command == "kill":
            monitor.kill_all_processes()
        elif command == "stop":
            monitor.stop_monitoring_all()
        else:
            print(f"未知命令: {command}")
            print("可用命令: status, kill, stop")
    else:
        monitor.show_monitoring_status()