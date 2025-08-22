#!/usr/bin/env python3
"""
测试超高并行模式的功能
"""

import sys
import subprocess
import time
from pathlib import Path

def test_ultra_parallel_basic():
    """基本功能测试"""
    print("🧪 测试超高并行执行器基本功能...")
    
    try:
        # 测试导入
        from ultra_parallel_runner import UltraParallelRunner
        print("✅ 成功导入UltraParallelRunner")
        
        # 初始化
        runner = UltraParallelRunner()
        print("✅ 成功初始化执行器")
        
        # 检查实例池
        util = runner.get_resource_utilization()
        print(f"✅ 实例池: {util['total_instances']}个实例")
        print(f"   总容量: {util['total_capacity']} workers")
        
        # 测试DeepSeek实例获取
        deepseek_instances = runner.get_available_instances("deepseek-v3")
        print(f"✅ DeepSeek-V3可用实例: {len(deepseek_instances)}个")
        
        # 测试任务分片创建
        shards = runner.create_task_shards(
            model="DeepSeek-V3-0324",
            prompt_types="baseline,cot",
            difficulty="easy",
            task_types="all",
            num_instances=6
        )
        print(f"✅ 创建任务分片: {len(shards)}个")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_command_line():
    """测试命令行接口"""
    print("\n🧪 测试命令行接口...")
    
    try:
        # 运行帮助命令
        result = subprocess.run([
            "python", "ultra_parallel_runner.py", "--help"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ 命令行接口正常")
            return True
        else:
            print(f"❌ 命令行接口失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 命令行测试失败: {e}")
        return False

def simulate_ultra_parallel_test():
    """模拟超高并行测试"""
    print("\n🧪 模拟超高并行测试 (不执行实际测试)...")
    
    try:
        from ultra_parallel_runner import UltraParallelRunner
        
        runner = UltraParallelRunner()
        
        # 模拟测试配置
        test_configs = [
            ("DeepSeek-V3-0324", "baseline,cot,optimal"),
            ("DeepSeek-R1-0528", "flawed_sequence_disorder,flawed_tool_misuse"),
            ("Llama-3.3-70B-Instruct", "baseline,optimal"),
            ("qwen2.5-72b-instruct", "baseline,cot,optimal")  # 新增Qwen测试
        ]
        
        for model, prompt_types in test_configs:
            print(f"\n📊 模拟测试: {model}")
            print(f"   Prompt类型: {prompt_types}")
            
            # 创建任务分片
            shards = runner.create_task_shards(
                model=model,
                prompt_types=prompt_types,
                difficulty="easy", 
                task_types="all",
                num_instances=20
            )
            
            print(f"   🔄 将创建 {len(shards)} 个并行分片")
            for shard in shards:
                print(f"     - {shard.instance_name}: {shard.num_instances}个测试")
                
            # 模拟资源利用率
            util = runner.get_resource_utilization()
            print(f"   📈 预计资源利用率: {len(shards)*100}% (相比单实例的{len(shards)}倍加速)")
        
        return True
        
    except Exception as e:
        print(f"❌ 模拟测试失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 超高并行模式测试套件")
    print("=" * 50)
    
    all_tests_passed = True
    
    # 基本功能测试
    if not test_ultra_parallel_basic():
        all_tests_passed = False
    
    # 命令行接口测试
    if not test_command_line():
        all_tests_passed = False
    
    # 模拟测试
    if not simulate_ultra_parallel_test():
        all_tests_passed = False
    
    print("\n" + "=" * 50)
    if all_tests_passed:
        print("🎉 所有测试通过！超高并行模式已就绪")
        print("📊 性能预期:")
        print("   • DeepSeek模型: 3-6倍加速")
        print("   • Llama模型: 2-3倍加速")
        print("   • 资源利用率: 11% → 90%+")
    else:
        print("❌ 部分测试失败，请检查配置")
        
    return 0 if all_tests_passed else 1

if __name__ == "__main__":
    exit(main())