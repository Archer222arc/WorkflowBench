#!/usr/bin/env python3
"""
Smart Result Collector - 智能结果收集器
解决当前数据收集机制的僵化问题，提供灵活、可靠的数据管理

设计原则：
1. 多重触发条件 - 不依赖单一阈值
2. 实时持久化 - 每个结果立即备份
3. 分层保存策略 - 内存→文件→数据库
4. 自适应机制 - 根据实际情况调整策略
5. 容错恢复 - 异常情况下的数据保护
"""

import json
import os
import time
import atexit
import signal
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
import logging

logger = logging.getLogger(__name__)

class SmartResultCollector:
    """智能结果收集器 - 灵活可靠的数据管理"""
    
    def __init__(self, 
                 temp_dir: str = "temp_results",
                 max_memory_results: int = 100,
                 max_time_seconds: int = 300,  # 5分钟
                 auto_save_interval: int = 60,  # 1分钟自动保存
                 adaptive_threshold: bool = True):
        """
        初始化智能结果收集器
        
        Args:
            temp_dir: 临时文件目录
            max_memory_results: 内存中最大结果数（触发保存）
            max_time_seconds: 最大等待时间（触发保存）
            auto_save_interval: 自动保存间隔（秒）
            adaptive_threshold: 是否启用自适应阈值
        """
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(exist_ok=True)
        
        # 配置参数
        self.max_memory_results = max_memory_results
        self.max_time_seconds = max_time_seconds
        self.auto_save_interval = auto_save_interval
        self.adaptive_threshold = adaptive_threshold
        
        # 运行时状态
        self.memory_results = []
        self.last_save_time = time.time()
        self.total_results_count = 0
        self.session_id = f"session_{int(time.time())}"
        
        # 线程安全
        self.lock = threading.Lock()
        
        # 保存回调
        self.save_callbacks = []
        
        # 启动自动保存线程
        self.auto_save_thread = None
        self.shutdown_flag = threading.Event()
        self._start_auto_save()
        
        # 注册退出处理
        atexit.register(self.shutdown)
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        logger.info(f"SmartResultCollector初始化完成")
        logger.info(f"  - 临时目录: {self.temp_dir}")
        logger.info(f"  - 内存阈值: {self.max_memory_results}")
        logger.info(f"  - 时间阈值: {self.max_time_seconds}秒")
        logger.info(f"  - 自动保存: {self.auto_save_interval}秒")
        logger.info(f"  - 自适应阈值: {self.adaptive_threshold}")

    def add_result(self, result: Dict[str, Any]) -> bool:
        """
        添加单个测试结果（实时处理）
        
        Args:
            result: 测试结果字典
            
        Returns:
            是否触发了保存操作
        """
        with self.lock:
            # 添加元数据
            result['_collector_timestamp'] = datetime.now().isoformat()
            result['_collector_session'] = self.session_id
            result['_collector_index'] = self.total_results_count
            
            # 立即写入临时文件（L2持久化）
            self._write_temp_file(result)
            
            # 添加到内存缓存（L1缓存）
            self.memory_results.append(result)
            self.total_results_count += 1
            
            logger.debug(f"添加结果 #{self.total_results_count}: {result.get('model', 'unknown')}")
            
            # 检查是否需要保存
            if self._should_save():
                return self._trigger_save("threshold_reached")
                
        return False

    def add_batch(self, results: List[Dict[str, Any]], 
                  model: str = None, 
                  process_info: Dict = None) -> bool:
        """
        批量添加结果
        
        Args:
            results: 结果列表
            model: 模型名称
            process_info: 进程信息
            
        Returns:
            是否触发了保存操作
        """
        if not results:
            return False
            
        with self.lock:
            # 批量处理结果
            for result in results:
                if model and 'model' not in result:
                    result['model'] = model
                if process_info:
                    result['_process_info'] = process_info
                    
                self.add_result(result)
                
        logger.info(f"批量添加 {len(results)} 个结果，当前总数: {self.total_results_count}")
        return False  # add_result内部已经检查了保存条件

    def _should_save(self) -> bool:
        """检查是否应该触发保存"""
        current_time = time.time()
        memory_count = len(self.memory_results)
        time_elapsed = current_time - self.last_save_time
        
        # 自适应阈值调整
        effective_threshold = self.max_memory_results
        if self.adaptive_threshold:
            # 根据历史数据调整阈值
            if self.total_results_count < 10:
                effective_threshold = min(5, self.max_memory_results)  # 小批次使用小阈值
            elif time_elapsed > self.max_time_seconds / 2:
                effective_threshold = min(memory_count + 1, self.max_memory_results)  # 时间压力下降低阈值
        
        # 多重触发条件
        reasons = []
        if memory_count >= effective_threshold:
            reasons.append(f"内存结果数 ({memory_count}) >= 阈值 ({effective_threshold})")
        if time_elapsed >= self.max_time_seconds:
            reasons.append(f"时间间隔 ({time_elapsed:.1f}s) >= 阈值 ({self.max_time_seconds}s)")
        if memory_count > 0 and time_elapsed >= self.max_time_seconds / 3:
            reasons.append(f"有数据且时间过半 ({time_elapsed:.1f}s)")
            
        if reasons:
            logger.debug(f"触发保存条件: {'; '.join(reasons)}")
            return True
            
        return False

    def _trigger_save(self, reason: str = "manual") -> bool:
        """触发保存操作"""
        if not self.memory_results:
            return False
            
        try:
            save_count = len(self.memory_results)
            logger.info(f"🔄 触发保存: {reason}, 保存 {save_count} 个结果")
            
            # 执行保存回调
            for callback in self.save_callbacks:
                try:
                    callback(self.memory_results.copy())
                except Exception as e:
                    logger.error(f"保存回调执行失败: {e}")
            
            # 清空内存缓存
            self.memory_results.clear()
            self.last_save_time = time.time()
            
            logger.info(f"✅ 保存完成: {save_count} 个结果")
            return True
            
        except Exception as e:
            logger.error(f"❌ 保存失败: {e}")
            return False

    def _write_temp_file(self, result: Dict[str, Any]):
        """写入单个结果到临时文件"""
        try:
            # 使用时间戳和索引确保文件名唯一
            timestamp = int(time.time() * 1000000)
            filename = f"result_{self.session_id}_{self.total_results_count}_{timestamp}.json"
            temp_file = self.temp_dir / filename
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"写入临时文件失败: {e}")

    def _start_auto_save(self):
        """启动自动保存线程"""
        def auto_save_worker():
            while not self.shutdown_flag.wait(self.auto_save_interval):
                try:
                    with self.lock:
                        if self.memory_results:
                            current_time = time.time()
                            time_elapsed = current_time - self.last_save_time
                            if time_elapsed >= self.auto_save_interval:
                                self._trigger_save("auto_save")
                except Exception as e:
                    logger.error(f"自动保存失败: {e}")
        
        self.auto_save_thread = threading.Thread(target=auto_save_worker, daemon=True)
        self.auto_save_thread.start()
        logger.info("自动保存线程已启动")

    def add_save_callback(self, callback: Callable[[List[Dict]], None]):
        """添加保存回调函数"""
        self.save_callbacks.append(callback)
        logger.info(f"添加保存回调，当前回调数: {len(self.save_callbacks)}")

    def force_save(self, reason: str = "manual") -> bool:
        """强制保存所有待处理结果"""
        with self.lock:
            return self._trigger_save(f"force_{reason}")

    def get_stats(self) -> Dict[str, Any]:
        """获取收集器统计信息"""
        with self.lock:
            current_time = time.time()
            return {
                'total_results': self.total_results_count,
                'memory_results': len(self.memory_results),
                'last_save_time': self.last_save_time,
                'time_since_last_save': current_time - self.last_save_time,
                'session_id': self.session_id,
                'temp_files': len(list(self.temp_dir.glob("result_*.json"))),
                'auto_save_active': self.auto_save_thread and self.auto_save_thread.is_alive()
            }

    def recover_from_temp_files(self) -> List[Dict[str, Any]]:
        """从临时文件恢复结果"""
        recovered_results = []
        temp_files = list(self.temp_dir.glob("result_*.json"))
        
        logger.info(f"尝试从 {len(temp_files)} 个临时文件恢复结果")
        
        for temp_file in temp_files:
            try:
                with open(temp_file, 'r', encoding='utf-8') as f:
                    result = json.load(f)
                    recovered_results.append(result)
            except Exception as e:
                logger.error(f"恢复文件 {temp_file} 失败: {e}")
        
        logger.info(f"成功恢复 {len(recovered_results)} 个结果")
        return recovered_results

    def cleanup_temp_files(self, older_than_hours: int = 24):
        """清理旧的临时文件"""
        current_time = time.time()
        cutoff_time = current_time - (older_than_hours * 3600)
        
        cleaned = 0
        for temp_file in self.temp_dir.glob("result_*.json"):
            try:
                if temp_file.stat().st_mtime < cutoff_time:
                    temp_file.unlink()
                    cleaned += 1
            except Exception as e:
                logger.error(f"清理文件 {temp_file} 失败: {e}")
        
        if cleaned > 0:
            logger.info(f"清理了 {cleaned} 个超过 {older_than_hours} 小时的临时文件")

    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"收到信号 {signum}，准备关闭")
        self.shutdown()

    def shutdown(self):
        """关闭收集器"""
        logger.info("SmartResultCollector 正在关闭...")
        
        # 停止自动保存线程
        self.shutdown_flag.set()
        if self.auto_save_thread and self.auto_save_thread.is_alive():
            self.auto_save_thread.join(timeout=5)
        
        # 强制保存所有待处理结果
        with self.lock:
            if self.memory_results:
                logger.info(f"关闭时强制保存 {len(self.memory_results)} 个结果")
                self._trigger_save("shutdown")
        
        logger.info("SmartResultCollector 已关闭")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()


# 使用示例
if __name__ == "__main__":
    # 创建智能收集器
    collector = SmartResultCollector(
        max_memory_results=5,  # 5个结果触发保存
        max_time_seconds=60,   # 1分钟触发保存
        auto_save_interval=30  # 30秒自动检查
    )
    
    # 添加保存回调
    def save_to_database(results):
        print(f"模拟保存到数据库: {len(results)} 个结果")
        for result in results:
            print(f"  - {result.get('model', 'unknown')}: {result.get('success', 'unknown')}")
    
    collector.add_save_callback(save_to_database)
    
    # 模拟测试结果
    import random
    for i in range(12):
        result = {
            'model': f'test_model_{i % 3}',
            'success': random.choice([True, False]),
            'score': random.uniform(0.5, 1.0),
            'test_id': f'test_{i}'
        }
        
        triggered = collector.add_result(result)
        print(f"添加结果 {i}: 触发保存={triggered}")
        
        if i % 4 == 0:
            time.sleep(1)  # 模拟处理时间
    
    # 显示统计
    print("\n统计信息:")
    stats = collector.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # 强制保存剩余结果
    collector.force_save("example_end")
    
    # 清理
    collector.shutdown()