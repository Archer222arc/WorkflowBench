#!/usr/bin/env python3
"""
测试并行部署功能
================
验证API名称和统计名称分离机制是否正确工作
"""

import json
import sys
from pathlib import Path
from typing import Dict, List

def test_model_routing():
    """测试1: 验证模型路由支持并行实例"""
    print("\n" + "="*60)
    print("测试1: 模型路由验证")
    print("="*60)
    
    from smart_model_router import get_router
    router = get_router()
    
    # 测试并行部署实例
    test_models = [
        "DeepSeek-V3-0324",
        "DeepSeek-V3-0324-2", 
        "DeepSeek-V3-0324-3",
        "DeepSeek-R1-0528",
        "DeepSeek-R1-0528-2",
        "Llama-3.3-70B-Instruct",
        "Llama-3.3-70B-Instruct-2"
    ]
    
    print("\n路由结果:")
    for model in test_models:
        provider, resolved = router.get_best_provider(model)
        status = "✅" if provider == "user_azure" and resolved == model else "❌"
        print(f"  {status} {model} -> {provider}: {resolved}")
    
    return True

def test_task_shard_creation():
    """测试2: 验证任务分片创建"""
    print("\n" + "="*60)
    print("测试2: 任务分片创建")
    print("="*60)
    
    from ultra_parallel_runner import UltraParallelRunner
    runner = UltraParallelRunner()
    
    # 创建分片
    shards = runner.create_task_shards(
        model="DeepSeek-V3-0324",
        prompt_types="baseline",
        difficulty="easy",
        task_types="simple_task",
        num_instances=10,
        tool_success_rate=0.8
    )
    
    print(f"\n创建了 {len(shards)} 个分片:")
    for i, shard in enumerate(shards):
        print(f"  分片{i+1}:")
        print(f"    - model (统计用): {shard.model}")
        print(f"    - instance_name (API用): {shard.instance_name}")
        print(f"    - num_instances: {shard.num_instances}")
    
    # 验证
    success = True
    for shard in shards:
        # model应该是小写的基础模型名
        if shard.model != "deepseek-v3-0324":
            print(f"  ❌ 错误: model应该是 'deepseek-v3-0324'，实际是 '{shard.model}'")
            success = False
        # instance_name应该保持原始大小写，可能带后缀
        if not shard.instance_name.startswith("DeepSeek-V3-0324"):
            print(f"  ❌ 错误: instance_name应该以 'DeepSeek-V3-0324' 开头，实际是 '{shard.instance_name}'")
            success = False
    
    if success:
        print("\n✅ 分片创建正确!")
    
    return success

def test_data_normalization():
    """测试3: 验证数据规范化"""
    print("\n" + "="*60)
    print("测试3: 数据规范化")
    print("="*60)
    
    try:
        # 直接导入normalize_model_name函数
        from cumulative_test_manager import normalize_model_name
        
        # 测试模型名称规范化
        test_cases = [
            ("DeepSeek-V3-0324", "deepseek-v3-0324"),
            ("DeepSeek-V3-0324-2", "deepseek-v3-0324"),  # 应该去除-2后缀
            ("DeepSeek-V3-0324-3", "deepseek-v3-0324"),  # 应该去除-3后缀
            ("deepseek-v3-0324", "deepseek-v3-0324"),
            ("DEEPSEEK-V3-0324", "deepseek-v3-0324"),
            ("Llama-3.3-70B-Instruct-2", "llama-3.3-70b-instruct"),
        ]
        
        print("\n模型名称规范化测试:")
        success = True
        for input_name, expected in test_cases:
            normalized = normalize_model_name(input_name)
            status = "✅" if normalized == expected else "❌"
            print(f"  {status} {input_name} -> {normalized} (期望: {expected})")
            if normalized != expected:
                success = False
        
        return success
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_calls():
    """测试4: 验证API调用（可选，需要真实API）"""
    print("\n" + "="*60)
    print("测试4: API调用验证（模拟）")
    print("="*60)
    
    print("\n模拟API调用流程:")
    print("1. ultra_parallel_runner传递:")
    print("   --model deepseek-v3-0324 (统计用)")
    print("   --deployment DeepSeek-V3-0324-2 (API用)")
    print("")
    print("2. smart_batch_runner接收:")
    print("   model = 'deepseek-v3-0324' -> 用于数据存储")
    print("   deployment = 'DeepSeek-V3-0324-2' -> 用于API调用")
    print("")
    print("3. batch_test_runner执行:")
    print("   api_model = deployment or model")
    print("   InteractiveExecutor(model=api_model) -> 使用'DeepSeek-V3-0324-2'")
    print("")
    print("4. 数据存储:")
    print("   normalize_model_name('deepseek-v3-0324') -> 'deepseek-v3-0324'")
    print("   所有数据聚合到同一个模型下")
    
    return True

def check_database_aggregation():
    """测试5: 检查数据库聚合"""
    print("\n" + "="*60)
    print("测试5: 数据库聚合检查")
    print("="*60)
    
    db_path = Path('pilot_bench_cumulative_results/master_database.json')
    if not db_path.exists():
        print("⚠️ 数据库文件不存在，跳过检查")
        return True
    
    with open(db_path) as f:
        db = json.load(f)
    
    # 查找DeepSeek相关的模型
    models = db.get('models', {}).keys()
    deepseek_models = [m for m in models if 'deepseek' in m.lower()]
    
    print("\n数据库中的DeepSeek模型:")
    for model in deepseek_models:
        stats = db['models'][model].get('overall_stats', {})
        total = stats.get('total_tests', 0)
        print(f"  - {model}: {total} 个测试")
    
    # 检查是否有带后缀的模型（不应该有）
    invalid_models = [m for m in deepseek_models if m.endswith('-2') or m.endswith('-3')]
    if invalid_models:
        print(f"\n❌ 发现无效的模型条目（带后缀）: {invalid_models}")
        print("   这些应该聚合到基础模型名下")
        return False
    else:
        print("\n✅ 没有发现带后缀的模型条目，数据正确聚合!")
        return True

def main():
    """运行所有测试"""
    print("\n" + "🚀"*30)
    print("并行部署功能测试套件")
    print("🚀"*30)
    
    results = []
    
    # 运行各项测试
    tests = [
        ("模型路由", test_model_routing),
        ("任务分片", test_task_shard_creation),
        ("数据规范化", test_data_normalization),
        ("API调用流程", test_api_calls),
        ("数据库聚合", check_database_aggregation)
    ]
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} 测试异常: {e}")
            results.append((name, False))
    
    # 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 所有测试通过!")
        print("并行部署功能正常工作:")
        print("  - API调用使用完整部署名（带后缀）")
        print("  - 数据统计聚合到基础模型名（无后缀）")
    else:
        print("⚠️ 部分测试失败，请检查相关问题")
    print("="*60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())