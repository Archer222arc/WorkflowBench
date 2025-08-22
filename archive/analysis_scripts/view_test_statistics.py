#!/usr/bin/env python3
"""
查看批测试的详细统计结果
"""

import argparse
from batch_test_runner import BatchTestRunner

def view_statistics(model: str = "qwen2.5-3b-instruct"):
    """查看测试统计"""
    
    print("\n" + "=" * 80)
    print("WorkflowBench 批测试统计报告")
    print("=" * 80)
    
    # 初始化runner来访问累积数据
    runner = BatchTestRunner(debug=False, silent=True)
    runner._lazy_init()
    
    # 获取进度报告
    progress = runner.manager.get_progress_report(model)
    
    if model not in progress.get('models', {}):
        print(f"\n❌ 没有找到模型 {model} 的测试数据")
        print("\n可用的模型:")
        for m in progress.get('models', {}).keys():
            print(f"  - {m}")
        return
    
    model_data = progress['models'][model]
    total_tests = model_data['total_tests']
    total_success = model_data['total_success']
    success_rate = (total_success / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\n📊 模型: {model}")
    print(f"总测试数: {total_tests}")
    print(f"成功数: {total_success}")
    print(f"成功率: {success_rate:.1f}%")
    
    # 按任务类型统计
    print("\n📋 按任务类型:")
    print("-" * 60)
    print(f"{'任务类型':<25} {'测试数':>10} {'成功数':>10} {'成功率':>10}")
    print("-" * 60)
    for task_type, stats in sorted(model_data.get('by_task_type', {}).items()):
        rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
        print(f"{task_type:<25} {stats['total']:>10} {stats['success']:>10} {rate:>9.1f}%")
    
    # 按Prompt类型统计  
    print("\n🎯 按Prompt策略 (3种基本):")
    print("-" * 60)
    print(f"{'Prompt类型':<25} {'测试数':>10} {'成功数':>10} {'成功率':>10}")
    print("-" * 60)
    for prompt_type in ['baseline', 'optimal', 'cot']:
        stats = model_data.get('by_prompt_type', {}).get(prompt_type, {'total': 0, 'success': 0})
        if stats['total'] > 0:
            rate = (stats['success'] / stats['total'] * 100)
            print(f"{prompt_type:<25} {stats['total']:>10} {stats['success']:>10} {rate:>9.1f}%")
    
    # 按缺陷类型统计
    print("\n🔧 按缺陷类型 (7种缺陷):")
    print("-" * 60)
    print(f"{'缺陷类型':<25} {'测试数':>10} {'成功数':>10} {'成功率':>10}")
    print("-" * 60)
    flaw_types = [
        "sequence_disorder", "tool_misuse", "parameter_error",
        "missing_step", "redundant_operations", 
        "logical_inconsistency", "semantic_drift"
    ]
    for flaw_type in flaw_types:
        stats = model_data.get('by_flaw_type', {}).get(flaw_type, {'total': 0, 'success': 0})
        if stats['total'] > 0:
            rate = (stats['success'] / stats['total'] * 100)
            print(f"{flaw_type:<25} {stats['total']:>10} {stats['success']:>10} {rate:>9.1f}%")
    
    # 实验计划合规性检查
    print("\n✅ 实验计划合规性:")
    print("-" * 60)
    
    # 检查10种策略的覆盖
    strategies_covered = 0
    print("3种基本Prompt:")
    for pt in ['baseline', 'optimal', 'cot']:
        count = model_data.get('by_prompt_type', {}).get(pt, {'total': 0})['total']
        status = "✓" if count > 0 else "✗"
        print(f"  {status} {pt}: {count} 个测试")
        if count > 0:
            strategies_covered += 1
    
    print("\n7种缺陷Prompt:")
    for ft in flaw_types:
        count = model_data.get('by_flaw_type', {}).get(ft, {'total': 0})['total']
        status = "✓" if count > 0 else "✗"
        print(f"  {status} flawed_{ft}: {count} 个测试")
        if count > 0:
            strategies_covered += 1
    
    print(f"\n策略覆盖: {strategies_covered}/10")
    if strategies_covered == 10:
        print("🎉 完全符合实验计划要求！")
    else:
        print(f"⚠️ 还需要覆盖 {10 - strategies_covered} 种策略")
    
    # 均衡性分析
    print("\n📊 分配均衡性分析:")
    print("-" * 60)
    
    all_counts = []
    # 收集所有策略的测试数
    for pt in ['baseline', 'optimal', 'cot']:
        count = model_data.get('by_prompt_type', {}).get(pt, {'total': 0})['total']
        if count > 0:
            all_counts.append(count)
    
    for ft in flaw_types:
        count = model_data.get('by_flaw_type', {}).get(ft, {'total': 0})['total']
        if count > 0:
            all_counts.append(count)
    
    if all_counts:
        min_count = min(all_counts)
        max_count = max(all_counts)
        avg_count = sum(all_counts) / len(all_counts)
        
        print(f"最少测试数: {min_count}")
        print(f"最多测试数: {max_count}")
        print(f"平均测试数: {avg_count:.1f}")
        print(f"分配差异: {max_count - min_count}")
        
        if max_count - min_count <= 1:
            print("✅ 分配非常均衡")
        elif max_count - min_count <= 3:
            print("✓ 分配较为均衡")
        else:
            print("⚠️ 分配不够均衡，建议运行更多测试")
    
    print("\n" + "=" * 80)
    print("报告生成完毕")
    print("=" * 80)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='查看批测试统计')
    parser.add_argument('--model', type=str, default='qwen2.5-3b-instruct',
                       help='模型名称')
    args = parser.parse_args()
    
    view_statistics(args.model)