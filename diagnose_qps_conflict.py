#!/usr/bin/env python3
"""
诊断QPS限流问题：分析是否存在多个分片使用同一key的冲突
"""

import json
import time
from pathlib import Path
import threading
import subprocess

def analyze_shard_key_distribution():
    """分析分片和key分配逻辑"""
    print("=" * 80)
    print("分析Ultra Parallel Runner的分片策略")
    print("=" * 80)
    
    print("\n1. 当前分片策略（ultra_parallel_runner.py）：")
    print("-" * 40)
    print("标准场景（5.1/5.2/5.4/5.5）：")
    print("  - 总任务均匀分配到3个keys")
    print("  - 每个分片使用不同的key_index (0, 1, 2)")
    print("  - 分片ID格式: model_difficulty_key{idx}")
    print()
    print("5.3场景（缺陷工作流）：")
    print("  - 每个flawed类型创建独立分片")
    print("  - 轮询分配key_index")
    print("  - 每个分片仍然使用独立的key")
    
    print("\n2. 潜在问题分析：")
    print("-" * 40)
    
    # 模拟5.1场景
    print("\n场景5.1 - 基准测试（假设30个任务）：")
    num_instances = 30
    instances_per_key = num_instances // 3
    remainder = num_instances % 3
    
    for key_idx in range(3):
        shard_instances = instances_per_key + (1 if key_idx < remainder else 0)
        print(f"  分片key{key_idx}: {shard_instances}个任务")
        print(f"    → 使用idealab_qwen_key{key_idx}_qps_state.json")
    
    # 模拟5.3场景
    print("\n场景5.3 - 缺陷工作流（7种缺陷类型）：")
    flawed_types = [
        "flawed_logical_inconsistency",
        "flawed_semantic_drift", 
        "flawed_incomplete_information",
        "flawed_redundant_steps",
        "flawed_missing_steps",
        "flawed_sequence_disorder",
        "flawed_output_format"
    ]
    
    for i, ftype in enumerate(flawed_types):
        key_idx = i % 3  # 轮询分配
        print(f"  {ftype}: 使用key{key_idx}")
    
    print("\n3. 并发执行时的实际情况：")
    print("-" * 40)
    print("如果同时运行多个qwen模型（如72b, 32b, 14b, 7b, 3b）：")
    models = ["qwen2.5-72b", "qwen2.5-32b", "qwen2.5-14b", "qwen2.5-7b", "qwen2.5-3b"]
    
    print("\n每个模型都会创建3个分片：")
    for model in models:
        print(f"\n{model}:")
        for key_idx in range(3):
            print(f"  → 分片{key_idx}: 使用key{key_idx}")
    
    print("\n⚠️ 问题识别：")
    print("  5个模型 × 3个分片 = 15个并发进程")
    print("  但只有3个API keys！")
    print("  结果：每个key被5个进程同时使用")
    print("  → 5个进程共享同一个QPS限制器")
    print("  → 每个进程实际QPS = 10 / 5 = 2 QPS")

def check_state_files():
    """检查当前的state文件状态"""
    print("\n" + "=" * 80)
    print("检查QPS State文件")
    print("=" * 80)
    
    state_dir = Path("/tmp/qps_limiter")
    if not state_dir.exists():
        print("State目录不存在")
        return
    
    state_files = list(state_dir.glob("ideallab_qwen*.json"))
    
    if not state_files:
        print("没有找到qwen相关的state文件")
        return
    
    print(f"\n找到 {len(state_files)} 个state文件：")
    
    for f in sorted(state_files):
        try:
            with open(f, 'r') as fp:
                data = json.load(fp)
                timestamp = data.get('last_request_time', 0)
                pid = data.get('pid', 'unknown')
                age = time.time() - timestamp if timestamp > 0 else float('inf')
                
                print(f"\n{f.name}:")
                print(f"  - 最后更新: {age:.1f}秒前")
                print(f"  - 进程ID: {pid}")
                
                # 检查进程是否还在运行
                if pid != 'unknown':
                    try:
                        subprocess.run(['ps', '-p', str(pid)], 
                                     capture_output=True, check=True)
                        print(f"  - 进程状态: ✅ 运行中")
                    except:
                        print(f"  - 进程状态: ❌ 已结束")
        except Exception as e:
            print(f"  读取失败: {e}")

def simulate_concurrent_access():
    """模拟并发访问同一个key的情况"""
    print("\n" + "=" * 80)
    print("模拟并发访问冲突")
    print("=" * 80)
    
    from qps_limiter import get_qps_limiter
    
    print("\n模拟5个进程使用同一个key0：")
    print("-" * 40)
    
    results = []
    lock = threading.Lock()
    
    def worker(process_id):
        """模拟一个进程"""
        model = "qwen2.5-7b-instruct"
        limiter = get_qps_limiter(model, qps=10, key_index=0)  # 都使用key0
        
        times = []
        for i in range(3):
            start = time.time()
            limiter.acquire()
            wait = time.time() - start
            times.append(wait)
            
            with lock:
                results.append({
                    'process': process_id,
                    'request': i,
                    'wait': wait
                })
            
            if i == 0:
                print(f"进程{process_id} 第1个请求: 等待{wait:.3f}秒")
    
    # 启动5个线程模拟5个进程
    threads = []
    start_time = time.time()
    
    for i in range(5):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
        time.sleep(0.01)  # 轻微错开
    
    for t in threads:
        t.join()
    
    total_time = time.time() - start_time
    
    print(f"\n结果分析：")
    print(f"  - 5个进程，每个3个请求 = 15个请求")
    print(f"  - 总耗时: {total_time:.2f}秒")
    print(f"  - 实际QPS: {15/total_time:.1f}")
    print(f"  - 理论QPS（单key）: 10")
    
    if 15/total_time < 11:
        print(f"\n✅ 验证：多进程确实共享同一个QPS限制")
        print(f"   所有进程被串行化，总QPS仍为10")
    else:
        print(f"\n❌ 异常：QPS超过限制，可能存在问题")

def propose_solution():
    """提出解决方案"""
    print("\n" + "=" * 80)
    print("解决方案")
    print("=" * 80)
    
    print("\n问题根因：")
    print("  多个qwen模型并发运行时，每个模型都使用key0/1/2")
    print("  导致不同模型的相同key_index共享QPS限制")
    
    print("\n方案1：模型级别的key分配")
    print("  - qwen2.5-72b: 使用key0")
    print("  - qwen2.5-32b: 使用key1")
    print("  - qwen2.5-14b: 使用key2")
    print("  - qwen2.5-7b: 使用key0")
    print("  - qwen2.5-3b: 使用key1")
    
    print("\n方案2：动态key池管理")
    print("  - 创建全局key使用状态管理器")
    print("  - 动态分配未被占用的key")
    print("  - 避免key冲突")
    
    print("\n方案3：增加模型标识到state文件")
    print("  - state文件名包含模型名：ideallab_qwen_72b_key0_qps_state.json")
    print("  - 每个模型的每个key独立限流")
    print("  - 完全避免冲突")
    
    print("\n推荐：方案3（最简单有效）")
    print("修改qps_limiter.py的get_qps_limiter函数：")
    print("""
def get_qps_limiter(model: str, qps=None, key_index=None):
    if "qwen" in model.lower():
        # 提取模型规模标识（72b, 32b等）
        import re
        match = re.search(r'(\d+b)', model.lower())
        model_size = match.group(1) if match else 'unknown'
        
        if key_index is not None:
            provider = f"ideallab_qwen_{model_size}_key{key_index}"
        else:
            provider = f"ideallab_qwen_{model_size}"
    """)

if __name__ == "__main__":
    # 分析分片策略
    analyze_shard_key_distribution()
    
    # 检查state文件
    check_state_files()
    
    # 模拟并发冲突
    print("\n是否要模拟并发冲突？这会创建测试请求（y/n）: ", end="")
    import sys
    if input().lower() == 'y':
        simulate_concurrent_access()
    
    # 提出解决方案
    propose_solution()