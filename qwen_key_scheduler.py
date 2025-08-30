#!/usr/bin/env python3
"""
Qwen模型API Key调度器
====================

实现同一key串行、不同key并行的调度策略
"""

import time
import threading
import subprocess
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class QwenTask:
    """Qwen任务定义"""
    model: str
    prompt_types: str
    difficulty: str
    task_types: str
    num_instances: int
    description: str
    key_idx: int
    
class QwenKeyScheduler:
    """Qwen模型的API Key智能调度器
    
    核心功能：
    1. 每个key维护独立的任务队列
    2. 同一key的任务串行执行
    3. 不同key之间并行执行
    """
    
    def __init__(self, num_keys: int = 3):
        self.num_keys = num_keys
        self.key_queues = {i: [] for i in range(num_keys)}
        self.key_threads = {}
        self.completion_status = {i: [] for i in range(num_keys)}
        
        # Key分配策略（固定映射）
        self.KEY_ASSIGNMENT = {
            "72b": 0,
            "32b": 1, 
            "14b": 2,
            "7b": 0,   # 与72b共享key0
            "3b": 1,   # 与32b共享key1
        }
        
    def assign_key(self, model: str) -> int:
        """根据模型分配API key"""
        import re
        match = re.search(r'(\d+b)', model.lower())
        if match:
            model_size = match.group(1)
            return self.KEY_ASSIGNMENT.get(model_size, 0)
        return 0
    
    def add_task(self, task: QwenTask):
        """添加任务到对应key的队列"""
        key_idx = task.key_idx if task.key_idx >= 0 else self.assign_key(task.model)
        self.key_queues[key_idx].append(task)
        logger.info(f"📝 任务 {task.model}-{task.difficulty} 添加到 Key{key_idx} 队列")
    
    def execute_all(self, rate_mode: str = "fixed", max_workers: int = None):
        """执行所有队列中的任务"""
        logger.info(f"🚀 开始执行Qwen任务调度（{self.num_keys}个key并行）")
        
        # 显示队列状态
        for key_idx, queue in self.key_queues.items():
            if queue:
                logger.info(f"  Key{key_idx}: {len(queue)}个任务待执行")
                for task in queue:
                    logger.info(f"    - {task.model}-{task.difficulty}")
        
        # 为每个key创建处理线程
        threads = []
        for key_idx in range(self.num_keys):
            if self.key_queues[key_idx]:  # 只为有任务的key创建线程
                thread = threading.Thread(
                    target=self._process_key_queue,
                    args=(key_idx, rate_mode, max_workers)
                )
                threads.append(thread)
                thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        logger.info("✅ 所有Qwen任务执行完成")
        
        # 返回执行结果
        return self.completion_status
    
    def _process_key_queue(self, key_idx: int, rate_mode: str, max_workers: int):
        """处理单个key的任务队列（串行）"""
        queue = self.key_queues[key_idx]
        logger.info(f"🔄 Key{key_idx} 开始处理 {len(queue)} 个任务")
        
        for i, task in enumerate(queue, 1):
            logger.info(f"⚡ Key{key_idx} [{i}/{len(queue)}]: 开始 {task.model}-{task.difficulty}")
            
            # 构建命令
            cmd = self._build_command(task, key_idx, rate_mode, max_workers)
            
            # 执行任务
            start_time = time.time()
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                duration = time.time() - start_time
                
                if result.returncode == 0:
                    logger.info(f"✅ Key{key_idx} [{i}/{len(queue)}]: 完成 {task.model}-{task.difficulty} (耗时: {duration:.1f}秒)")
                    self.completion_status[key_idx].append((task, True, duration))
                else:
                    logger.error(f"❌ Key{key_idx} [{i}/{len(queue)}]: 失败 {task.model}-{task.difficulty}")
                    logger.error(f"  错误: {result.stderr[:200]}")
                    self.completion_status[key_idx].append((task, False, duration))
                    
            except Exception as e:
                logger.error(f"❌ Key{key_idx}: 执行失败 - {e}")
                self.completion_status[key_idx].append((task, False, 0))
        
        logger.info(f"✅ Key{key_idx} 队列处理完成")
    
    def _build_command(self, task: QwenTask, key_idx: int, rate_mode: str, max_workers: int) -> str:
        """构建执行命令"""
        # 这里应该调用ultra_parallel_runner.py
        # 为了演示，返回一个示例命令
        cmd = f"""python ultra_parallel_runner.py \\
            --model {task.model} \\
            --prompt-types {task.prompt_types} \\
            --difficulty {task.difficulty} \\
            --task-types {task.task_types} \\
            --num-instances {task.num_instances} \\
            --rate-mode {rate_mode}"""
        
        if max_workers:
            cmd += f" --max-workers {max_workers}"
            
        return cmd

def demo_phase_5_2_scheduling():
    """演示Phase 5.2的调度策略"""
    scheduler = QwenKeyScheduler(num_keys=3)
    
    # Phase 5.2的所有任务
    models = [
        "qwen2.5-72b-instruct",
        "qwen2.5-32b-instruct",
        "qwen2.5-14b-instruct",
        "qwen2.5-7b-instruct",
        "qwen2.5-3b-instruct"
    ]
    
    difficulties = ["very_easy", "medium"]
    
    # 添加所有任务到调度器
    for difficulty in difficulties:
        for model in models:
            task = QwenTask(
                model=model,
                prompt_types="optimal",
                difficulty=difficulty,
                task_types="all",
                num_instances=20,
                description=f"Qwen规模效应({difficulty})",
                key_idx=-1  # 自动分配
            )
            scheduler.add_task(task)
    
    # 模拟执行（实际执行会调用ultra_parallel_runner）
    print("\n" + "=" * 60)
    print("模拟Phase 5.2执行时间轴")
    print("=" * 60)
    
    # 显示预期的执行顺序
    print("\n预期执行顺序（3个key并行）：")
    print("-" * 40)
    print("时间点  Key0              Key1              Key2")
    print("------  ----              ----              ----")
    print("T+0     72b-very_easy     32b-very_easy     14b-very_easy")
    print("T+X     7b-very_easy      3b-very_easy      14b-medium")
    print("T+Y     72b-medium        32b-medium        (空闲)")
    print("T+Z     7b-medium         3b-medium         (空闲)")
    
    print("\n关键优势：")
    print("✅ 每个key同一时间只有1个模型运行")
    print("✅ 不会出现key冲突")
    print("✅ 最大化并行度（3个key同时工作）")

if __name__ == "__main__":
    demo_phase_5_2_scheduling()