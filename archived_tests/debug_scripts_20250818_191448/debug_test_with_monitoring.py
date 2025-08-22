#!/usr/bin/env python3
"""
调试测试脚本 - 带有完整监控和日志功能
用于诊断进程卡死问题
"""

import os
import sys
import time
import json
import logging
import threading
import signal
import traceback
from pathlib import Path
from datetime import datetime
import subprocess
import psutil

# 配置详细日志
log_dir = Path(f"logs/debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'main.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 启用Python的故障处理器
import faulthandler
faulthandler.enable(file=open(log_dir / 'faulthandler.log', 'w'))

class ProcessMonitor:
    """进程监控器"""
    
    def __init__(self):
        self.processes = {}
        self.start_time = time.time()
        self.heartbeat_thread = None
        self.monitor_thread = None
        self.should_stop = False
        
    def start_monitoring(self):
        """启动监控线程"""
        # 心跳线程
        self.heartbeat_thread = threading.Thread(target=self._heartbeat, daemon=True)
        self.heartbeat_thread.start()
        
        # 进程监控线程
        self.monitor_thread = threading.Thread(target=self._monitor_processes, daemon=True)
        self.monitor_thread.start()
        
    def _heartbeat(self):
        """定期打印心跳信息"""
        while not self.should_stop:
            elapsed = time.time() - self.start_time
            logger.info(f"💓 心跳 - 运行时间: {elapsed:.0f}秒, 活跃进程: {len(self.processes)}")
            
            # 打印进程状态
            for pid, info in self.processes.items():
                try:
                    proc = psutil.Process(pid)
                    cpu_percent = proc.cpu_percent(interval=0.1)
                    mem_info = proc.memory_info()
                    logger.info(f"  PID {pid}: CPU={cpu_percent:.1f}%, MEM={mem_info.rss/1024/1024:.0f}MB, {info['name']}")
                except psutil.NoSuchProcess:
                    logger.warning(f"  PID {pid}: 进程已结束")
                    
            time.sleep(30)  # 每30秒一次心跳
            
    def _monitor_processes(self):
        """监控进程状态"""
        while not self.should_stop:
            for pid in list(self.processes.keys()):
                try:
                    proc = psutil.Process(pid)
                    # 检查是否卡死（CPU使用率持续为0）
                    cpu_samples = []
                    for _ in range(5):
                        cpu_samples.append(proc.cpu_percent(interval=0.5))
                    
                    avg_cpu = sum(cpu_samples) / len(cpu_samples)
                    if avg_cpu < 0.1:  # CPU使用率极低
                        logger.warning(f"⚠️ PID {pid} 可能卡死 (平均CPU: {avg_cpu:.2f}%)")
                        
                except psutil.NoSuchProcess:
                    del self.processes[pid]
                    
            time.sleep(60)  # 每分钟检查一次
            
    def add_process(self, process, name):
        """添加进程到监控列表"""
        self.processes[process.pid] = {
            'name': name,
            'start_time': time.time(),
            'process': process
        }
        logger.info(f"📌 开始监控进程 PID {process.pid}: {name}")
        
    def stop(self):
        """停止监控"""
        self.should_stop = True
        
class DebugTestRunner:
    """调试测试运行器"""
    
    def __init__(self):
        self.monitor = ProcessMonitor()
        self.log_dir = log_dir
        
    def run_single_model_test(self, model, prompt_type="baseline", num_instances=2):
        """运行单个模型的小规模测试"""
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🧪 测试模型: {model}")
        logger.info(f"   Prompt类型: {prompt_type}")
        logger.info(f"   实例数: {num_instances}")
        logger.info(f"{'='*60}\n")
        
        # 设置环境变量
        env = os.environ.copy()
        env['STORAGE_FORMAT'] = 'json'  # 使用JSON格式以简化调试
        env['PYTHONUNBUFFERED'] = '1'  # 无缓冲输出
        env['PYTHONFAULTHANDLER'] = '1'  # 启用故障处理
        
        # 构建命令 - 使用保守参数
        cmd = [
            'python', '-u',  # 无缓冲模式
            'smart_batch_runner.py',
            '--model', model,
            '--prompt-types', prompt_type,
            '--difficulty', 'easy',
            '--task-types', 'simple_task',
            '--num-instances', str(num_instances),
            '--max-workers', '5',  # 低并发
            '--tool-success-rate', '0.8',
            '--batch-commit',
            '--checkpoint-interval', '1',  # 频繁保存
            '--no-adaptive',  # 固定速率
            '--qps', '5',  # 低QPS
            '--no-save-logs'
        ]
        
        # 日志文件
        log_file = self.log_dir / f"{model}_{prompt_type}.log"
        
        logger.info(f"📝 执行命令: {' '.join(cmd)}")
        logger.info(f"📁 日志文件: {log_file}")
        
        # 启动进程
        with open(log_file, 'w') as log_f:
            process = subprocess.Popen(
                cmd,
                stdout=log_f,
                stderr=subprocess.STDOUT,
                env=env,
                text=True
            )
            
            # 添加到监控
            self.monitor.add_process(process, f"{model}_{prompt_type}")
            
            # 设置超时（5分钟）
            timeout = 300
            start_time = time.time()
            
            while True:
                # 检查进程状态
                poll_result = process.poll()
                
                if poll_result is not None:
                    # 进程结束
                    if poll_result == 0:
                        logger.info(f"✅ 测试成功完成 (退出码: 0)")
                    else:
                        logger.error(f"❌ 测试失败 (退出码: {poll_result})")
                        # 显示最后的日志
                        self._show_tail_log(log_file)
                    break
                    
                # 检查超时
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    logger.error(f"⏱️ 测试超时 ({timeout}秒)")
                    process.terminate()
                    time.sleep(5)
                    if process.poll() is None:
                        process.kill()
                    self._show_tail_log(log_file)
                    break
                    
                # 短暂等待
                time.sleep(1)
                
        return process.returncode == 0
        
    def _show_tail_log(self, log_file, lines=20):
        """显示日志文件的最后几行"""
        try:
            with open(log_file, 'r') as f:
                all_lines = f.readlines()
                if all_lines:
                    logger.info(f"\n📋 日志最后{lines}行:")
                    for line in all_lines[-lines:]:
                        print(f"  | {line.rstrip()}")
        except Exception as e:
            logger.error(f"无法读取日志: {e}")
            
    def check_data_save(self):
        """检查数据是否成功保存"""
        logger.info("\n🔍 检查数据保存状态...")
        
        # 检查JSON数据库
        json_db = Path("pilot_bench_cumulative_results/master_database.json")
        if json_db.exists():
            with open(json_db) as f:
                db = json.load(f)
            
            logger.info(f"📊 JSON数据库:")
            logger.info(f"   总测试数: {db['summary'].get('total_tests', 0)}")
            logger.info(f"   模型数: {len(db.get('models', {}))}")
            
            # 显示最近的测试
            if 'test_groups' in db:
                recent_groups = sorted(
                    db['test_groups'].items(),
                    key=lambda x: x[1].get('timestamp', ''),
                    reverse=True
                )[:3]
                
                if recent_groups:
                    logger.info(f"   最近的测试组:")
                    for group_id, group_data in recent_groups:
                        logger.info(f"     - {group_data.get('model', 'N/A')}: {group_data.get('total_tests', 0)} tests at {group_data.get('timestamp', 'N/A')}")
                        
    def run_diagnostic_test(self):
        """运行诊断测试"""
        logger.info("🔧 开始诊断测试")
        logger.info(f"📁 日志目录: {self.log_dir}")
        
        # 启动监控
        self.monitor.start_monitoring()
        
        try:
            # 测试1: 单个小规模测试
            logger.info("\n📌 测试1: 单个gpt-4o-mini测试")
            success = self.run_single_model_test("gpt-4o-mini", "baseline", 1)
            
            if success:
                logger.info("✅ 基础测试通过")
                
                # 测试2: 稍大规模
                logger.info("\n📌 测试2: 增加实例数")
                success = self.run_single_model_test("gpt-4o-mini", "baseline", 3)
                
                if success:
                    logger.info("✅ 扩展测试通过")
                    
                    # 测试3: 开源模型
                    logger.info("\n📌 测试3: 测试开源模型")
                    success = self.run_single_model_test("qwen2.5-7b-instruct", "baseline", 2)
                    
                    if success:
                        logger.info("✅ 开源模型测试通过")
                    else:
                        logger.error("❌ 开源模型测试失败")
                else:
                    logger.error("❌ 扩展测试失败")
            else:
                logger.error("❌ 基础测试失败")
                
        except KeyboardInterrupt:
            logger.info("\n⚠️ 测试被用户中断")
        except Exception as e:
            logger.error(f"❌ 测试异常: {e}")
            traceback.print_exc()
        finally:
            # 停止监控
            self.monitor.stop()
            
            # 检查数据保存
            self.check_data_save()
            
            logger.info(f"\n📊 测试完成")
            logger.info(f"📁 完整日志保存在: {self.log_dir}")
            
def main():
    """主函数"""
    runner = DebugTestRunner()
    
    # 设置信号处理
    def signal_handler(sig, frame):
        logger.info("\n🛑 收到中断信号，正在清理...")
        runner.monitor.stop()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 运行诊断测试
    runner.run_diagnostic_test()
    
if __name__ == "__main__":
    main()