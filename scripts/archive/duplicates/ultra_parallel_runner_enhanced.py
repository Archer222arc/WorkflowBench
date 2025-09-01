#!/usr/bin/env python3
"""
增强版Ultra Parallel Runner - 实现API Key队列调度
=================================================

主要改进：
1. 为qwen模型实现API key队列调度
2. 同一key串行执行，不同key并行
3. 解决Phase 5.2的并发冲突问题
"""

import asyncio
import concurrent.futures
import json
import os
import time
import logging
from dataclasses import dataclass
from typing import List, Dict, Set, Optional, Tuple
from pathlib import Path
import subprocess
import threading
from queue import Queue, Empty

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class QwenBatch:
    """Qwen批量任务定义"""
    models: List[str]
    prompt_types: str
    difficulties: List[str]
    task_types: str
    num_instances: int
    rate_mode: str
    result_suffix: str
    silent: bool
    tool_success_rate: float
    max_workers: Optional[int]

class QwenKeyQueueScheduler:
    """Qwen模型API Key队列调度器
    
    实现策略：
    1. 每个API key维护独立的任务队列
    2. 同一key的任务串行执行
    3. 不同key之间并行执行
    """
    
    def __init__(self, num_keys: int = 3):
        self.num_keys = num_keys
        self.key_queues = {i: Queue() for i in range(num_keys)}
        self.key_workers = {}
        self.results = {i: [] for i in range(num_keys)}
        
        # Key分配映射（基于模型大小）
        self.KEY_ASSIGNMENT = {
            "72b": 0,
            "32b": 1,
            "14b": 2,
            "7b": 0,   # 与72b共享key0
            "3b": 1,   # 与32b共享key1
        }
    
    def assign_key(self, model: str) -> int:
        """根据模型名称分配API key"""
        import re
        match = re.search(r'(\d+b)', model.lower())
        if match:
            model_size = match.group(1)
            return self.KEY_ASSIGNMENT.get(model_size, 0)
        return 0
    
    def schedule_batch(self, batch: QwenBatch) -> bool:
        """调度一批qwen任务"""
        logger.info(f"🎯 开始调度Qwen批量任务")
        logger.info(f"   模型数: {len(batch.models)}")
        logger.info(f"   难度: {batch.difficulties}")
        
        # 将任务分配到各个key的队列
        task_count = {i: 0 for i in range(self.num_keys)}
        
        for difficulty in batch.difficulties:
            for model in batch.models:
                key_idx = self.assign_key(model)
                task = {
                    'model': model,
                    'prompt_types': batch.prompt_types,
                    'difficulty': difficulty,
                    'task_types': batch.task_types,
                    'num_instances': batch.num_instances,
                    'rate_mode': batch.rate_mode,
                    'result_suffix': batch.result_suffix,
                    'silent': batch.silent,
                    'tool_success_rate': batch.tool_success_rate,
                    'max_workers': batch.max_workers
                }
                self.key_queues[key_idx].put(task)
                task_count[key_idx] += 1
        
        # 显示队列分配情况
        logger.info(f"📋 任务队列分配:")
        for key_idx in range(self.num_keys):
            if task_count[key_idx] > 0:
                logger.info(f"   Key{key_idx}: {task_count[key_idx]}个任务")
        
        # 创建worker线程处理每个key的队列
        threads = []
        for key_idx in range(self.num_keys):
            if task_count[key_idx] > 0:
                thread = threading.Thread(
                    target=self._process_key_queue,
                    args=(key_idx,),
                    name=f"Key{key_idx}Worker"
                )
                threads.append(thread)
                thread.start()
                logger.info(f"   🚀 启动Key{key_idx}处理线程")
        
        # 等待所有线程完成
        logger.info(f"⏳ 等待所有任务完成...")
        for thread in threads:
            thread.join()
        
        logger.info(f"✅ 所有Qwen任务执行完成")
        return True
    
    def _process_key_queue(self, key_idx: int):
        """处理单个key的任务队列（串行执行）"""
        queue = self.key_queues[key_idx]
        completed = 0
        
        while not queue.empty():
            try:
                task = queue.get(timeout=1)
                completed += 1
                
                logger.info(f"🔄 Key{key_idx} [{completed}]: 开始 {task['model']}-{task['difficulty']}")
                
                # 执行任务
                success = self._execute_single_task(task, key_idx)
                
                if success:
                    logger.info(f"✅ Key{key_idx} [{completed}]: 完成 {task['model']}-{task['difficulty']}")
                else:
                    logger.error(f"❌ Key{key_idx} [{completed}]: 失败 {task['model']}-{task['difficulty']}")
                
                self.results[key_idx].append({
                    'model': task['model'],
                    'difficulty': task['difficulty'],
                    'success': success
                })
                
                queue.task_done()
                
            except Empty:
                break
        
        logger.info(f"✅ Key{key_idx}队列处理完成，共{completed}个任务")
    
    def _execute_single_task(self, task: dict, key_idx: int) -> bool:
        """执行单个任务"""
        # 构建命令
        cmd = [
            'python', 'ultra_parallel_runner.py',
            '--model', task['model'],
            '--prompt-types', task['prompt_types'],
            '--difficulty', task['difficulty'],
            '--task-types', task['task_types'],
            '--num-instances', str(task['num_instances']),
            '--rate-mode', task['rate_mode']
        ]
        
        if task['max_workers']:
            cmd.extend(['--max-workers', str(task['max_workers'])])
        
        if task['result_suffix']:
            cmd.extend(['--result-suffix', task['result_suffix']])
        
        if task['silent']:
            cmd.append('--silent')
        
        cmd.extend(['--tool-success-rate', str(task['tool_success_rate'])])
        
        # 设置环境变量，指定使用的API key
        env = os.environ.copy()
        env[f'QWEN_API_KEY_INDEX'] = str(key_idx)
        
        try:
            # 执行命令
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=1800  # 30分钟超时
            )
            
            return result.returncode == 0
            
        except subprocess.TimeoutExpired:
            logger.error(f"任务超时: {task['model']}-{task['difficulty']}")
            return False
        except Exception as e:
            logger.error(f"执行失败: {e}")
            return False

def run_phase_5_2_with_queue_scheduling():
    """使用队列调度运行Phase 5.2"""
    
    # Phase 5.2的qwen模型
    qwen_models = [
        "qwen2.5-72b-instruct",
        "qwen2.5-32b-instruct",
        "qwen2.5-14b-instruct",
        "qwen2.5-7b-instruct",
        "qwen2.5-3b-instruct"
    ]
    
    # 创建批量任务
    batch = QwenBatch(
        models=qwen_models,
        prompt_types="optimal",
        difficulties=["very_easy", "medium"],
        task_types="all",
        num_instances=20,
        rate_mode="fixed",
        result_suffix="",
        silent=False,
        tool_success_rate=0.8,
        max_workers=1
    )
    
    # 创建调度器并执行
    scheduler = QwenKeyQueueScheduler(num_keys=3)
    success = scheduler.schedule_batch(batch)
    
    # 显示执行结果
    print("\n" + "=" * 60)
    print("执行结果总结")
    print("=" * 60)
    
    for key_idx, results in scheduler.results.items():
        if results:
            print(f"\nKey{key_idx}:")
            for r in results:
                status = "✅" if r['success'] else "❌"
                print(f"  {status} {r['model']}-{r['difficulty']}")
    
    return success

if __name__ == "__main__":
    print("=" * 80)
    print("增强版Ultra Parallel Runner - API Key队列调度演示")
    print("=" * 80)
    
    print("\n关键改进：")
    print("1. 同一个API key的任务串行执行")
    print("2. 不同API key之间并行执行")
    print("3. 避免同一key被多个模型同时使用")
    print("4. 最大化资源利用率")
    
    print("\n执行时间轴：")
    print("-" * 40)
    print("Key0队列: 72b-very_easy → 7b-very_easy → 72b-medium → 7b-medium")
    print("Key1队列: 32b-very_easy → 3b-very_easy → 32b-medium → 3b-medium")
    print("Key2队列: 14b-very_easy → 14b-medium")
    print("\n3个队列并行执行，每个队列内串行")
    
    print("\n这将完全解决Phase 5.2的并发冲突问题！")