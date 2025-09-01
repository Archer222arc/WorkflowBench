#!/usr/bin/env python3
"""
实现API Key队列策略 - 同一key串行，不同key并行
=============================================

核心思想：
1. 每个API key维护自己的任务队列
2. 同一个key的任务必须串行执行（前一个完成后才开始下一个）
3. 不同key之间可以并行执行
4. 这样可以最大化并行度，同时避免同一key被多个进程使用
"""

import time
import threading
from typing import List, Dict, Tuple
from dataclasses import dataclass

@dataclass
class QwenTask:
    """Qwen模型任务"""
    model: str
    difficulty: str
    key_index: int
    task_name: str

def show_execution_strategy():
    """展示新的执行策略"""
    print("=" * 80)
    print("API Key队列策略设计")
    print("=" * 80)
    
    # Phase 5.2的任务分配
    tasks = [
        # very_easy难度
        ("qwen2.5-72b", "very_easy", 0),
        ("qwen2.5-32b", "very_easy", 1),
        ("qwen2.5-14b", "very_easy", 2),
        ("qwen2.5-7b", "very_easy", 0),   # 排队等待72b完成
        ("qwen2.5-3b", "very_easy", 1),   # 排队等待32b完成
        # medium难度
        ("qwen2.5-72b", "medium", 0),     # 排队等待7b完成
        ("qwen2.5-32b", "medium", 1),     # 排队等待3b完成
        ("qwen2.5-14b", "medium", 2),     # 排队等待14b-very_easy完成
        ("qwen2.5-7b", "medium", 0),      # 排队等待72b-medium完成
        ("qwen2.5-3b", "medium", 1),      # 排队等待32b-medium完成
    ]
    
    # 按key分组
    key_queues = {0: [], 1: [], 2: []}
    for model, diff, key in tasks:
        key_queues[key].append((model, diff))
    
    print("\n📋 任务队列分配：")
    print("-" * 40)
    for key_idx, queue in key_queues.items():
        print(f"\nKey{key_idx} 队列（串行执行）：")
        for i, (model, diff) in enumerate(queue, 1):
            print(f"  {i}. {model}-{diff}")
    
    print("\n⚡ 执行时间轴（3个key并行）：")
    print("-" * 40)
    print("""
    时间    Key0                Key1                Key2
    ----    ----                ----                ----
    T+0     72b-very_easy 开始   32b-very_easy 开始   14b-very_easy 开始
    T+X     72b-very_easy 完成   32b-very_easy 完成   14b-very_easy 完成
            7b-very_easy 开始    3b-very_easy 开始    14b-medium 开始
    T+Y     7b-very_easy 完成    3b-very_easy 完成    14b-medium 完成
            72b-medium 开始      32b-medium 开始      (空闲)
    T+Z     72b-medium 完成      32b-medium 完成      
            7b-medium 开始       3b-medium 开始       
    """)
    
    print("\n✅ 优势：")
    print("  1. 每个key同一时间只有1个模型在运行")
    print("  2. 不同key之间充分并行（3个并发）")
    print("  3. 没有key冲突和限流风险")
    print("  4. 资源利用率最大化")

def generate_implementation():
    """生成实现代码"""
    print("\n" + "=" * 80)
    print("实现方案")
    print("=" * 80)
    
    implementation = '''
# 方案1：修改run_systematic_test_final.sh的5.2执行逻辑
# ======================================================

run_qwen_with_key_queues() {
    local models=("$@")
    
    # 创建3个命名管道作为key队列
    mkfifo /tmp/qwen_key0_queue /tmp/qwen_key1_queue /tmp/qwen_key2_queue
    
    # Key0队列处理器
    (
        while read task; do
            eval "$task"
            wait
        done < /tmp/qwen_key0_queue
    ) &
    
    # Key1队列处理器
    (
        while read task; do
            eval "$task"
            wait
        done < /tmp/qwen_key1_queue
    ) &
    
    # Key2队列处理器
    (
        while read task; do
            eval "$task"
            wait
        done < /tmp/qwen_key2_queue
    ) &
    
    # 分配任务到队列
    echo "run_test qwen2.5-72b very_easy" > /tmp/qwen_key0_queue
    echo "run_test qwen2.5-32b very_easy" > /tmp/qwen_key1_queue
    echo "run_test qwen2.5-14b very_easy" > /tmp/qwen_key2_queue
    echo "run_test qwen2.5-7b very_easy" > /tmp/qwen_key0_queue
    echo "run_test qwen2.5-3b very_easy" > /tmp/qwen_key1_queue
    # ... 继续添加medium难度的任务
    
    # 等待所有队列处理完成
    wait
    
    # 清理管道
    rm -f /tmp/qwen_key*_queue
}

# 方案2：在ultra_parallel_runner.py中实现智能调度
# ================================================

class QwenKeyScheduler:
    """Qwen模型的API Key智能调度器"""
    
    def __init__(self):
        self.key_queues = {0: [], 1: [], 2: []}
        self.key_locks = {0: threading.Lock(), 1: threading.Lock(), 2: threading.Lock()}
        self.key_busy = {0: False, 1: False, 2: False}
    
    def schedule_models(self, models: List[Tuple[str, str]]):
        """调度模型执行"""
        # 分配模型到key队列
        key_assignment = {
            "72b": 0, "32b": 1, "14b": 2,
            "7b": 0, "3b": 1
        }
        
        for model, difficulty in models:
            model_size = self._extract_size(model)
            key_idx = key_assignment.get(model_size, 0)
            self.key_queues[key_idx].append((model, difficulty))
        
        # 启动3个worker线程，每个处理一个key的队列
        threads = []
        for key_idx in range(3):
            t = threading.Thread(target=self._process_queue, args=(key_idx,))
            threads.append(t)
            t.start()
        
        # 等待所有队列完成
        for t in threads:
            t.join()
    
    def _process_queue(self, key_idx: int):
        """处理单个key的任务队列"""
        queue = self.key_queues[key_idx]
        
        for model, difficulty in queue:
            with self.key_locks[key_idx]:
                self.key_busy[key_idx] = True
                print(f"Key{key_idx}: 开始执行 {model}-{difficulty}")
                
                # 执行实际的测试
                self._run_test(model, difficulty, key_idx)
                
                print(f"Key{key_idx}: 完成 {model}-{difficulty}")
                self.key_busy[key_idx] = False
    
    def _run_test(self, model: str, difficulty: str, key_idx: int):
        """执行实际的测试（调用ultra_parallel_runner）"""
        # 这里调用实际的测试代码
        pass
'''
    print(implementation)

def show_comparison():
    """对比新旧方案"""
    print("\n" + "=" * 80)
    print("新旧方案对比")
    print("=" * 80)
    
    print("\n❌ 当前方案（问题）：")
    print("""
    T+0s:  72b→key0 启动
    T+15s: 32b→key1 启动  
    T+30s: 14b→key2 启动
    T+45s: 7b→key0 启动  ⚠️ key0冲突！72b还在运行
    T+60s: 3b→key1 启动  ⚠️ key1冲突！32b还在运行
    
    问题：同一个key被多个模型同时使用
    """)
    
    print("\n✅ 新方案（队列）：")
    print("""
    T+0s:  72b→key0 启动, 32b→key1 启动, 14b→key2 启动
    T+X:   72b完成, 7b→key0 启动（等待72b完成后）
    T+Y:   32b完成, 3b→key1 启动（等待32b完成后）
    T+Z:   14b完成, 14b-medium→key2 启动
    
    优势：每个key始终只有1个模型在运行，没有冲突
    """)

if __name__ == "__main__":
    show_execution_strategy()
    generate_implementation()
    show_comparison()
    
    print("\n" + "=" * 80)
    print("实施建议")
    print("=" * 80)
    print("""
    1. 短期方案：修改bash脚本，使用命名管道实现队列
    2. 中期方案：在Python中实现QwenKeyScheduler
    3. 长期方案：实现通用的资源池管理器
    
    推荐：先实施短期方案，快速解决限流问题
    """)