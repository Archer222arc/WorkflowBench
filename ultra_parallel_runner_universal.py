#!/usr/bin/env python3
"""
通用Qwen队列调度器 - 集成到ultra_parallel_runner.py
====================================================

核心原则：
1. 所有qwen模型都使用队列调度，无论哪个phase
2. 自动检测并发场景，智能调度
3. 向后兼容，不影响非qwen模型
"""

import time
import threading
import subprocess
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import logging
from queue import Queue
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UniversalQwenScheduler:
    """通用Qwen调度器 - 适用于所有phases
    
    特性：
    1. 自动检测qwen模型
    2. 智能分配API keys
    3. 确保同key串行，不同key并行
    4. 支持所有测试场景（5.1-5.5）
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式，全局共享调度器"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.num_keys = 3  # 3个API keys
            self.key_queues = {i: Queue() for i in range(self.num_keys)}
            self.key_busy = {i: False for i in range(self.num_keys)}
            self.key_locks = {i: threading.Lock() for i in range(self.num_keys)}
            
            # API Key分配策略（固定映射）
            self.KEY_ASSIGNMENT = {
                "72b": 0,
                "32b": 1,
                "14b": 2,
                "7b": 0,   # 与72b共享key0
                "3b": 1,   # 与32b共享key1
            }
            
            # 启动worker线程
            self._start_workers()
    
    def _start_workers(self):
        """启动处理各个key队列的worker线程"""
        for key_idx in range(self.num_keys):
            thread = threading.Thread(
                target=self._key_worker,
                args=(key_idx,),
                daemon=True,
                name=f"QwenKey{key_idx}Worker"
            )
            thread.start()
            logger.debug(f"启动Key{key_idx} worker线程")
    
    def _key_worker(self, key_idx: int):
        """处理单个key的任务队列"""
        while True:
            # 从队列获取任务
            task = self.key_queues[key_idx].get()
            
            if task is None:  # 退出信号
                break
            
            # 标记key为忙碌
            with self.key_locks[key_idx]:
                self.key_busy[key_idx] = True
            
            try:
                # 执行任务
                logger.info(f"🔄 Key{key_idx}: 开始执行 {task['description']}")
                task['function'](*task['args'], **task['kwargs'])
                logger.info(f"✅ Key{key_idx}: 完成 {task['description']}")
            except Exception as e:
                logger.error(f"❌ Key{key_idx}: 执行失败 - {e}")
            finally:
                # 标记key为空闲
                with self.key_locks[key_idx]:
                    self.key_busy[key_idx] = False
                self.key_queues[key_idx].task_done()
    
    def schedule_qwen_task(self, model: str, task_func, *args, **kwargs):
        """调度一个qwen任务
        
        Args:
            model: qwen模型名称
            task_func: 要执行的函数
            args, kwargs: 函数参数
        """
        # 分配API key
        key_idx = self._assign_key(model)
        
        # 构建任务
        task = {
            'description': f"{model}-{kwargs.get('difficulty', 'unknown')}",
            'function': task_func,
            'args': args,
            'kwargs': kwargs
        }
        
        # 添加到队列
        self.key_queues[key_idx].put(task)
        logger.info(f"📝 任务 {task['description']} 添加到 Key{key_idx} 队列")
    
    def _assign_key(self, model: str) -> int:
        """根据模型分配API key"""
        import re
        match = re.search(r'(\d+b)', model.lower())
        if match:
            model_size = match.group(1)
            return self.KEY_ASSIGNMENT.get(model_size, 0)
        return 0
    
    def wait_all(self):
        """等待所有队列完成"""
        for key_idx in range(self.num_keys):
            self.key_queues[key_idx].join()
        logger.info("✅ 所有Qwen任务完成")
    
    def shutdown(self):
        """关闭调度器"""
        # 发送退出信号
        for key_idx in range(self.num_keys):
            self.key_queues[key_idx].put(None)


# 修改后的ultra_parallel_runner.py核心方法
class UltraParallelRunnerEnhanced:
    """增强版Ultra Parallel Runner with Qwen Queue Scheduling"""
    
    def __init__(self):
        # ... 原有初始化代码 ...
        self.qwen_scheduler = UniversalQwenScheduler()
    
    def run_ultra_parallel_test(self, model: str, prompt_types: str, difficulty: str,
                               task_types: str = "all", num_instances: int = 20,
                               rate_mode: str = "adaptive", result_suffix: str = "",
                               silent: bool = False, tool_success_rate: float = 0.8,
                               max_workers: int = None) -> bool:
        """运行超高并行度测试 - 自动检测并使用qwen调度器"""
        
        # 检测是否是qwen模型
        if "qwen" in model.lower():
            logger.info(f"🎯 检测到Qwen模型，使用队列调度器")
            
            # 使用调度器执行
            self.qwen_scheduler.schedule_qwen_task(
                model=model,
                task_func=self._execute_qwen_test,
                model=model,
                prompt_types=prompt_types,
                difficulty=difficulty,
                task_types=task_types,
                num_instances=num_instances,
                rate_mode=rate_mode,
                result_suffix=result_suffix,
                silent=silent,
                tool_success_rate=tool_success_rate,
                max_workers=max_workers
            )
            
            # 如果是单个模型调用，等待完成
            # 如果是批量调用，由调用方决定何时wait
            if not hasattr(self, '_batch_mode'):
                self.qwen_scheduler.wait_all()
            
            return True
        
        else:
            # 非qwen模型，使用原有逻辑
            return self._run_original_test(model, prompt_types, difficulty,
                                          task_types, num_instances, rate_mode,
                                          result_suffix, silent, tool_success_rate,
                                          max_workers)
    
    def run_batch_qwen_tests(self, models: List[str], prompt_types: str, 
                            difficulties: List[str], **kwargs):
        """批量运行qwen测试 - 用于Phase 5.2等场景"""
        
        logger.info(f"🚀 批量Qwen测试：{len(models)}个模型，{len(difficulties)}个难度")
        
        # 设置批量模式标记
        self._batch_mode = True
        
        # 提交所有任务到调度器
        for difficulty in difficulties:
            for model in models:
                self.run_ultra_parallel_test(
                    model=model,
                    prompt_types=prompt_types,
                    difficulty=difficulty,
                    **kwargs
                )
        
        # 等待所有任务完成
        self.qwen_scheduler.wait_all()
        
        # 清除批量模式标记
        self._batch_mode = False
        
        logger.info("✅ 批量Qwen测试完成")
        return True
    
    def _execute_qwen_test(self, model: str, prompt_types: str, difficulty: str,
                          task_types: str, num_instances: int, rate_mode: str,
                          result_suffix: str, silent: bool, tool_success_rate: float,
                          max_workers: int):
        """实际执行qwen测试的内部方法"""
        
        logger.info(f"执行Qwen测试: {model}-{difficulty}")
        
        # 创建任务分片（使用修改后的方法，只创建1个分片）
        shards = self._create_qwen_smart_shards(model, prompt_types, difficulty,
                                               task_types, num_instances, tool_success_rate)
        
        if not shards:
            logger.error(f"无法创建任务分片: {model}")
            return False
        
        # 执行分片（只有1个）
        shard = shards[0]
        process = self.execute_shard_async(shard, rate_mode=rate_mode, 
                                         result_suffix=result_suffix,
                                         silent=silent, max_workers=max_workers,
                                         shard_index=1)
        
        # 等待完成
        process.wait()
        
        return process.returncode == 0


# 使用示例
def demo_all_phases():
    """演示所有phases的使用"""
    
    print("=" * 80)
    print("通用Qwen队列调度器 - 适用于所有Phases")
    print("=" * 80)
    
    runner = UltraParallelRunnerEnhanced()
    
    print("\n📋 Phase 5.1 - 基准测试")
    print("-" * 40)
    print("串行执行每个模型，但qwen模型自动使用调度器")
    print("确保不会有key冲突")
    
    print("\n📋 Phase 5.2 - Qwen规模效应")
    print("-" * 40)
    print("批量提交10个任务（5模型×2难度）")
    print("3个key队列并行处理")
    print("每个key同时只有1个模型运行")
    
    print("\n📋 Phase 5.3 - 缺陷工作流")
    print("-" * 40)
    print("每个qwen模型的3个缺陷组")
    print("如果并发提交，自动排队")
    print("避免同一模型的3个组争抢同一个key")
    
    print("\n📋 Phase 5.4 & 5.5")
    print("-" * 40)
    print("串行测试，但仍然使用调度器")
    print("保证资源管理的一致性")
    
    print("\n✨ 关键优势：")
    print("1. 一套代码适用所有phases")
    print("2. 自动检测qwen模型")
    print("3. 透明的队列调度")
    print("4. 向后兼容")
    print("5. 最大化资源利用")


if __name__ == "__main__":
    demo_all_phases()
    
    print("\n" + "=" * 80)
    print("集成方案")
    print("=" * 80)
    print("""
1. 将UniversalQwenScheduler类添加到ultra_parallel_runner.py

2. 修改UltraParallelRunner的__init__方法：
   添加 self.qwen_scheduler = UniversalQwenScheduler()

3. 修改run_ultra_parallel_test方法：
   - 检测是否是qwen模型
   - 如果是，使用调度器
   - 如果不是，使用原逻辑

4. 添加run_batch_qwen_tests方法：
   用于Phase 5.2等批量场景

优势：
- 所有phase自动获得改进
- 无需修改调用脚本
- 完全透明的优化
    """)