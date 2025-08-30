#!/usr/bin/env python3
"""
5.4 工具可靠性敏感性测试的优化策略分析
测试不同tool_success_rate（0.9, 0.8, 0.7, 0.6）
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from ultra_parallel_runner import UltraParallelRunner

def analyze_5_4_optimization():
    """分析5.4场景的优化策略"""
    
    print("=" * 70)
    print("5.4 工具可靠性敏感性测试 - 优化策略分析")
    print("=" * 70)
    
    runner = UltraParallelRunner()
    
    # 5.4场景：测试不同的tool_success_rate
    # 固定使用optimal prompt，但需要测试4个不同的工具成功率
    tool_success_rates = [0.9, 0.8, 0.7, 0.6]
    
    print("\n📊 5.4测试配置：")
    print("- Prompt类型: optimal（固定）")
    print("- 难度: easy")
    print("- 工具成功率: 90%, 80%, 70%, 60%")
    print("- 任务类型: 全部5种")
    print("- 每个成功率: 100个测试")
    
    print("\n🔍 当前问题：")
    print("- 所有4个tool_success_rate都使用optimal prompt")
    print("- 按原策略，都会映射到key2")
    print("- 导致key0和key1空闲，key2负载过重")
    
    print("\n💡 优化策略：")
    print("将不同的tool_success_rate分配到不同的API keys：")
    
    # 模拟分配策略
    rate_to_key = {
        0.9: 0,  # 90% -> key0
        0.8: 1,  # 80% -> key1
        0.7: 2,  # 70% -> key2
        0.6: 0   # 60% -> key0 (轮询回来)
    }
    
    for rate in tool_success_rates:
        key = rate_to_key[rate]
        print(f"  - tool_success_rate={rate:.0%} -> qwen-key{key}")
    
    print("\n📈 实际实现方案：")
    print("方案A：在创建分片时根据tool_success_rate分配")
    print("```python")
    print("# 在_create_qwen_smart_shards中添加tool_success_rate考虑")
    print("if is_single_prompt and prompt_list[0] == 'optimal':")
    print("    # 5.4场景：根据tool_success_rate分配key")
    print("    if tool_success_rate >= 0.85:  # 0.9")
    print("        key_index = 0")
    print("    elif tool_success_rate >= 0.75:  # 0.8")
    print("        key_index = 1")
    print("    elif tool_success_rate >= 0.65:  # 0.7")
    print("        key_index = 2")
    print("    else:  # 0.6")
    print("        key_index = 0  # 轮询回key0")
    print("```")
    
    print("\n方案B：并行运行不同的tool_success_rate")
    print("```bash")
    print("# 同时启动4个测试，每个使用不同的key")
    print("python ultra_parallel_runner.py --model qwen2.5-72b \\")
    print("  --prompt-types optimal --tool-success-rate 0.9 &  # 使用key0")
    print("python ultra_parallel_runner.py --model qwen2.5-72b \\")
    print("  --prompt-types optimal --tool-success-rate 0.8 &  # 使用key1")
    print("python ultra_parallel_runner.py --model qwen2.5-72b \\")
    print("  --prompt-types optimal --tool-success-rate 0.7 &  # 使用key2")
    print("```")
    
    print("\n✅ 优化效果：")
    print("- 原方案：4个tool_success_rate串行执行（都用key2）")
    print("- 优化后：3个tool_success_rate并行执行（分别用不同key）")
    print("- 性能提升：约3倍（受限于3个API keys）")
    
    # 实际测试分片创建
    print("\n\n🧪 实际测试分片创建：")
    print("-" * 50)
    
    for rate in [0.9, 0.8, 0.7, 0.6]:
        print(f"\ntool_success_rate={rate:.0%}的分片：")
        shards = runner._create_qwen_smart_shards(
            model="qwen2.5-72b-instruct",
            prompt_types="optimal",
            difficulty="easy", 
            task_types="simple_task,basic_task",
            num_instances=6,
            tool_success_rate=rate
        )
        
        for shard in shards:
            print(f"  - {shard.instance_name}: {shard.num_instances}个实例")
    
    print("\n" + "=" * 70)
    print("总结：")
    print("✅ 5.4场景可以通过tool_success_rate映射到不同keys实现并行")
    print("✅ 建议在_create_qwen_smart_shards中添加tool_success_rate分配逻辑")
    print("✅ 或者通过并行启动多个进程，每个指定不同的tool_success_rate")
    print("=" * 70)

if __name__ == "__main__":
    analyze_5_4_optimization()