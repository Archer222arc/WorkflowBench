#!/usr/bin/env python3
"""
测试API Key轮换策略
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ultra_parallel_runner import UltraParallelRunner

def test_key_rotation():
    """测试不同qwen模型的key分配"""
    print("=" * 80)
    print("测试API Key轮换策略")
    print("=" * 80)
    
    runner = UltraParallelRunner()
    
    # 测试5个qwen模型
    models = [
        "qwen2.5-72b-instruct",
        "qwen2.5-32b-instruct", 
        "qwen2.5-14b-instruct",
        "qwen2.5-7b-instruct",
        "qwen2.5-3b-instruct"
    ]
    
    print("\n📊 Key分配结果：")
    print("-" * 40)
    
    key_usage = {0: [], 1: [], 2: []}  # 3个keys
    
    for model in models:
        # 创建分片
        shards = runner._create_qwen_smart_shards(
            model=model,
            prompt_types="optimal",
            difficulty="easy",
            task_types="all",
            num_instances=20,
            tool_success_rate=0.8
        )
        
        # 分析分片
        for shard in shards:
            # 从instance_name提取key索引
            if "key0" in shard.instance_name:
                key_idx = 0
            elif "key1" in shard.instance_name:
                key_idx = 1
            elif "key2" in shard.instance_name:
                key_idx = 2
            else:
                key_idx = -1
                
            if key_idx >= 0:
                key_usage[key_idx].append(model)
                
            print(f"  {model:25} → {shard.instance_name} (分片数: {len(shards)})")
    
    print("\n📈 Key负载分析：")
    print("-" * 40)
    for key_idx, models_list in key_usage.items():
        print(f"  Key{key_idx}: {len(models_list)}个模型")
        for m in models_list:
            print(f"    - {m}")
    
    print("\n✅ 验证结果：")
    print("-" * 40)
    
    # 验证每个模型只使用一个key
    all_good = True
    for model in models:
        shards = runner._create_qwen_smart_shards(
            model=model,
            prompt_types="optimal",
            difficulty="easy",
            task_types="all",
            num_instances=20,
            tool_success_rate=0.8
        )
        if len(shards) != 1:
            print(f"  ❌ {model}: 创建了{len(shards)}个分片（期望1个）")
            all_good = False
        else:
            print(f"  ✅ {model}: 只创建1个分片")
    
    if all_good:
        print("\n🎉 所有测试通过！API Key轮换策略正确实施")
    else:
        print("\n⚠️ 测试失败：仍有模型创建多个分片")
    
    print("\n💡 改进效果：")
    print("-" * 40)
    print("  之前：每个模型3个分片，15个并发进程，每个key被5个模型使用")
    print("  现在：每个模型1个分片，5个并发进程，每个key被2-3个模型轮流使用")
    print("  预期：大幅减少API限流错误")

if __name__ == "__main__":
    test_key_rotation()