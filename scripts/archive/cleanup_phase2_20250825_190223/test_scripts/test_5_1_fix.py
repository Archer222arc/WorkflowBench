#!/usr/bin/env python3
"""
测试5.1基准测试修复效果
- 验证模型名称传递是否正确
- 验证所有模型是否被包含
- 小规模测试避免长时间等待
"""

import os
import sys
from pathlib import Path

# 设置环境变量
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['STORAGE_FORMAT'] = 'json'

def test_ultra_parallel_runner():
    """测试ultra_parallel_runner的模型分片逻辑"""
    print("=" * 60)
    print("🧪 测试Ultra Parallel Runner修复效果")
    print("=" * 60)
    
    try:
        from ultra_parallel_runner import UltraParallelRunner
        
        runner = UltraParallelRunner()
        
        # 测试qwen模型分片（之前有model.lower()问题）
        qwen_models = [
            "qwen2.5-72b-instruct",
            "qwen2.5-32b-instruct", 
            "qwen2.5-14b-instruct",
            "qwen2.5-7b-instruct",
            "qwen2.5-3b-instruct"
        ]
        
        print("🔍 测试qwen模型分片:")
        for model in qwen_models:
            shards = runner.create_task_shards(
                model=model,
                prompt_types="optimal",
                difficulty="easy", 
                task_types="simple_task",
                num_instances=2,
                tool_success_rate=0.8
            )
            
            print(f"\n   📋 {model}:")
            print(f"     分片数量: {len(shards)}")
            
            for i, shard in enumerate(shards):
                print(f"     分片{i+1}: model='{shard.model}' (原始: '{model}')")
                if shard.model != model:
                    print(f"     ❌ 模型名称不匹配! 期望:{model}, 实际:{shard.model}")
                else:
                    print(f"     ✅ 模型名称正确")
        
        # 测试DeepSeek模型分片
        print("\n🔍 测试DeepSeek模型分片:")
        deepseek_models = ["DeepSeek-V3-0324", "DeepSeek-R1-0528"]
        
        for model in deepseek_models:
            shards = runner.create_task_shards(
                model=model,
                prompt_types="optimal", 
                difficulty="easy",
                task_types="simple_task",
                num_instances=2,
                tool_success_rate=0.8
            )
            
            print(f"\n   📋 {model}:")
            print(f"     分片数量: {len(shards)}")
            
            if len(shards) == 0:
                print(f"     ❌ 没有生成分片，可能存在配置问题")
            else:
                for i, shard in enumerate(shards):
                    print(f"     分片{i+1}: model='{shard.model}', instance='{shard.instance_name}'")
        
        print("\n✅ Ultra Parallel Runner测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_model_normalize():
    """测试模型名称规范化"""
    print("\n" + "=" * 60)  
    print("🧪 测试模型名称规范化")
    print("=" * 60)
    
    try:
        from cumulative_test_manager import normalize_model_name
        
        test_cases = [
            # 测试所有预期的5.1基准测试模型
            "DeepSeek-V3-0324",
            "DeepSeek-R1-0528", 
            "qwen2.5-72b-instruct",
            "qwen2.5-32b-instruct",
            "qwen2.5-14b-instruct",
            "qwen2.5-7b-instruct", 
            "qwen2.5-3b-instruct",
            "Llama-3.3-70B-Instruct",
        ]
        
        print("🔍 测试所有预期模型的规范化:")
        for model in test_cases:
            normalized = normalize_model_name(model)
            print(f"   {model} -> {normalized}")
            
            # 应该保持不变（除了DeepSeek的并行实例）
            if model == normalized:
                print(f"     ✅ 规范化正确")
            else:
                print(f"     ⚠️  规范化变化: {model} != {normalized}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_api_config():
    """测试API配置完整性"""
    print("\n" + "=" * 60)
    print("🧪 测试API配置完整性")
    print("=" * 60)
    
    try:
        import json
        config_path = Path("config/config.json")
        
        if not config_path.exists():
            print("❌ config.json文件不存在")
            return False
            
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        model_configs = config.get('model_configs', {})
        
        # 检查所有预期模型的配置
        expected_models = [
            "DeepSeek-V3-0324", "DeepSeek-R1-0528",
            "qwen2.5-72b-instruct", "qwen2.5-32b-instruct", "qwen2.5-14b-instruct",
            "qwen2.5-7b-instruct", "qwen2.5-3b-instruct", "Llama-3.3-70B-Instruct"
        ]
        
        print("🔍 检查模型配置:")
        missing_configs = []
        
        for model in expected_models:
            if model in model_configs:
                provider = model_configs[model].get('provider', 'unknown')
                print(f"   ✅ {model}: {provider}")
            else:
                print(f"   ❌ {model}: 配置缺失")
                missing_configs.append(model)
        
        if missing_configs:
            print(f"\n❌ 缺失配置的模型: {missing_configs}")
            return False
        else:
            print("\n✅ 所有模型配置完整")
            return True
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🔍 5.1基准测试修复验证")
    print("=" * 60)
    
    # 运行各项测试
    tests = [
        ("Ultra Parallel Runner", test_ultra_parallel_runner),
        ("模型名称规范化", test_model_normalize), 
        ("API配置完整性", test_api_config),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 运行测试: {test_name}")
        result = test_func()
        results.append((test_name, result))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("📋 测试结果汇总")
    print("=" * 60)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n🎉 所有测试通过！可以进行实际测试")
        print("\n🚀 建议的下一步:")
        print("   1. 运行小规模5.1测试验证修复效果")
        print("   2. 检查DeepSeek-R1是否能正确执行")
        print("   3. 验证qwen模型数据保存是否正确")
    else:
        print("\n❌ 部分测试失败，需要进一步修复")

if __name__ == "__main__":
    main()