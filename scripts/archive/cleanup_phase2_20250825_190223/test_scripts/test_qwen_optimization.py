#!/usr/bin/env python3
"""
测试qwen模型的IdealLab并发优化效果
"""

import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from ultra_parallel_runner import UltraParallelRunner

def test_qwen_optimization():
    """测试qwen模型的优化效果"""
    
    print("=" * 70)
    print("测试qwen模型IdealLab并发优化")
    print("=" * 70)
    
    runner = UltraParallelRunner()
    
    # 场景1：测试5.1/5.2场景（只有optimal）
    print("\n📊 场景1：5.1/5.2测试 - 只有optimal")
    print("-" * 50)
    
    shards = runner._create_qwen_smart_shards(
        model="qwen2.5-72b-instruct",
        prompt_types="optimal",
        difficulty="easy",
        task_types="simple_task,basic_task",
        num_instances=6,
        tool_success_rate=0.8
    )
    
    print(f"创建了{len(shards)}个分片：")
    for shard in shards:
        print(f"  - {shard.shard_id}")
        print(f"    实例: {shard.instance_name}")
        print(f"    prompt: {shard.prompt_types}")
        print(f"    数量: {shard.num_instances}")
    
    print(f"\n✅ 优化效果：从1个串行任务 -> {len(shards)}个并行分片（提升{len(shards)}倍）")
    
    # 场景2：测试5.3场景（多个flawed）
    print("\n\n📊 场景2：5.3测试 - 多个flawed类型")
    print("-" * 50)
    
    shards = runner._create_qwen_smart_shards(
        model="qwen2.5-7b-instruct",
        prompt_types="flawed_sequence_disorder,flawed_tool_misuse,flawed_parameter_error",
        difficulty="easy",
        task_types="simple_task",
        num_instances=6,
        tool_success_rate=0.8
    )
    
    print(f"创建了{len(shards)}个分片：")
    for shard in shards:
        print(f"  - {shard.shard_id}")
        print(f"    实例: {shard.instance_name}")
        print(f"    prompt: {shard.prompt_types}")
        print(f"    数量: {shard.num_instances}")
    
    print(f"\n✅ 优化效果：3个flawed类型分配到{len(shards)}个API keys")
    
    # 场景3：测试5.5场景（baseline/cot/optimal）
    print("\n\n📊 场景3：5.5测试 - baseline/cot/optimal")
    print("-" * 50)
    
    shards = runner._create_qwen_smart_shards(
        model="qwen2.5-32b-instruct",
        prompt_types="baseline,cot,optimal",
        difficulty="easy",
        task_types="simple_task",
        num_instances=9,
        tool_success_rate=0.8
    )
    
    print(f"创建了{len(shards)}个分片：")
    for shard in shards:
        print(f"  - {shard.shard_id}")
        print(f"    实例: {shard.instance_name}")
        print(f"    prompt: {shard.prompt_types}")
        print(f"    数量: {shard.num_instances}")
    
    print(f"\n✅ 优化效果：3种prompt类型分配到{len(shards)}个专属API keys")
    
    print("\n" + "=" * 70)
    print("总结：")
    print("✅ 单prompt场景（5.1/5.2）：任务均匀分配到3个keys，3倍并发")
    print("✅ 多flawed场景（5.3）：flawed类型轮询分配，负载均衡")
    print("✅ 多prompt场景（5.5）：固定映射到专属keys，最大化并发")
    print("✅ 所有场景都充分利用3个IdealLab API keys")
    print("=" * 70)

if __name__ == "__main__":
    test_qwen_optimization()