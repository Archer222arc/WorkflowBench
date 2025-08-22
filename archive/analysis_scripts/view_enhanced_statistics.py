#!/usr/bin/env python3
"""
增强版测试统计查看器 - 包含详细的score统计
"""

import argparse
import json
from pathlib import Path
from batch_test_runner import BatchTestRunner
from cumulative_data_structure import ModelStatistics

def view_enhanced_statistics(model: str = "qwen2.5-3b-instruct", detailed: bool = False):
    """查看增强测试统计，包含scores"""
    
    print("\n" + "=" * 80)
    print("WorkflowBench 增强统计报告")
    print("=" * 80)
    
    # 初始化runner来访问累积数据
    runner = BatchTestRunner(debug=False, silent=True)
    runner._lazy_init()
    
    # 直接访问数据库
    if model not in runner.manager.database.get('models', {}):
        print(f"\n❌ 没有找到模型 {model} 的测试数据")
        print("\n可用的模型:")
        for m in runner.manager.database.get('models', {}).keys():
            print(f"  - {m}")
        return
    
    model_stats = runner.manager.database['models'][model]
    
    # 如果是字典，需要转换为ModelStatistics对象
    if isinstance(model_stats, dict):
        # 这是旧格式，需要兼容
        print("\n⚠️ 检测到旧格式数据，显示基本统计")
        total_tests = model_stats.get('total_tests', 0)
        total_success = model_stats.get('total_success', 0)
        success_rate = (total_success / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n📊 模型: {model}")
        print(f"总测试数: {total_tests}")
        print(f"成功数: {total_success}")
        print(f"成功率: {success_rate:.1f}%")
        return
    
    # 新格式 - ModelStatistics对象
    print(f"\n📊 模型: {model}")
    print(f"首次测试: {model_stats.first_test_time}")
    print(f"最后测试: {model_stats.last_test_time}")
    
    # 成功率统计
    print("\n📈 成功率统计:")
    print("-" * 60)
    print(f"总测试数: {model_stats.overall_success.total_tests}")
    print(f"完全成功: {model_stats.overall_success.full_success} ({model_stats.overall_success.full_success_rate*100:.1f}%)")
    print(f"部分成功: {model_stats.overall_success.partial_success} ({model_stats.overall_success.partial_success_rate*100:.1f}%)")
    print(f"失败: {model_stats.overall_success.failure} ({model_stats.overall_success.failure_rate*100:.1f}%)")
    print(f"总成功率: {model_stats.overall_success.success_rate*100:.1f}%")
    print(f"加权成功分数: {model_stats.overall_success.weighted_success_score:.3f}")
    
    # Score统计
    print("\n🎯 Score统计:")
    print("-" * 60)
    
    # Workflow Score
    ws = model_stats.overall_scores.workflow_scores
    if ws.count > 0:
        print(f"Workflow Score:")
        print(f"  平均: {ws.mean:.3f}")
        print(f"  最小: {ws.min:.3f}")
        print(f"  最大: {ws.max:.3f}")
        print(f"  样本数: {ws.count}")
    else:
        print("Workflow Score: 无数据")
    
    # Phase2 Score
    ps = model_stats.overall_scores.phase2_scores
    if ps.count > 0:
        print(f"Phase2 Score:")
        print(f"  平均: {ps.mean:.3f}")
        print(f"  最小: {ps.min:.3f}")
        print(f"  最大: {ps.max:.3f}")
        print(f"  样本数: {ps.count}")
    else:
        print("Phase2 Score: 无数据")
    
    # Quality Score
    qs = model_stats.overall_scores.quality_scores
    if qs.count > 0:
        print(f"Quality Score:")
        print(f"  平均: {qs.mean:.3f}")
        print(f"  最小: {qs.min:.3f}")
        print(f"  最大: {qs.max:.3f}")
        print(f"  样本数: {qs.count}")
    else:
        print("Quality Score: 无数据")
    
    # Final Score
    fs = model_stats.overall_scores.final_scores
    if fs.count > 0:
        print(f"Final Score:")
        print(f"  平均: {fs.mean:.3f}")
        print(f"  最小: {fs.min:.3f}")
        print(f"  最大: {fs.max:.3f}")
        print(f"  样本数: {fs.count}")
    else:
        print("Final Score: 无数据")
    
    # 执行统计
    print("\n⚡ 执行统计:")
    print("-" * 60)
    et = model_stats.overall_execution.execution_times
    if et.count > 0:
        print(f"执行时间: 平均 {et.mean:.2f}s (最小 {et.min:.2f}s, 最大 {et.max:.2f}s)")
    
    turns = model_stats.overall_execution.turns_used
    if turns.count > 0:
        print(f"执行轮数: 平均 {turns.mean:.1f} (最小 {int(turns.min)}, 最大 {int(turns.max)})")
    
    tc = model_stats.overall_execution.tool_calls
    if tc.count > 0:
        print(f"工具调用: 平均 {tc.mean:.1f} (最小 {int(tc.min)}, 最大 {int(tc.max)})")
    
    print(f"独特工具数: {model_stats.overall_execution.unique_tools_count}")
    print(f"总工具调用: {model_stats.overall_execution.total_tool_invocations}")
    
    # 按任务类型统计
    if model_stats.by_task_type:
        print("\n📋 按任务类型统计:")
        print("-" * 60)
        print(f"{'任务类型':<25} {'测试数':>8} {'成功率':>10} {'Avg Score':>10}")
        print("-" * 60)
        for task_type, stats in sorted(model_stats.by_task_type.items()):
            success_rate = stats.success_metrics.success_rate * 100
            avg_score = stats.score_metrics.final_scores.mean if stats.score_metrics.final_scores.count > 0 else 0
            print(f"{task_type:<25} {stats.success_metrics.total_tests:>8} {success_rate:>9.1f}% {avg_score:>10.3f}")
    
    # 按Prompt类型统计
    if model_stats.by_prompt_type:
        print("\n🎯 按Prompt策略统计:")
        print("-" * 60)
        
        # 基本prompt
        print("基本Prompt策略:")
        print(f"{'Prompt类型':<25} {'测试数':>8} {'成功率':>10} {'Avg Score':>10}")
        print("-" * 60)
        for prompt_type in ['baseline', 'optimal', 'cot']:
            if prompt_type in model_stats.by_prompt_type:
                stats = model_stats.by_prompt_type[prompt_type]
                success_rate = stats.success_metrics.success_rate * 100
                avg_score = stats.score_metrics.final_scores.mean if stats.score_metrics.final_scores.count > 0 else 0
                print(f"{prompt_type:<25} {stats.success_metrics.total_tests:>8} {success_rate:>9.1f}% {avg_score:>10.3f}")
        
        # Flawed prompts (如果有)
        if 'flawed' in model_stats.by_prompt_type:
            print("\nFlawed Prompt策略:")
            stats = model_stats.by_prompt_type['flawed']
            success_rate = stats.success_metrics.success_rate * 100
            avg_score = stats.score_metrics.final_scores.mean if stats.score_metrics.final_scores.count > 0 else 0
            print(f"{'flawed (all)':<25} {stats.success_metrics.total_tests:>8} {success_rate:>9.1f}% {avg_score:>10.3f}")
    
    # 按缺陷类型统计
    if model_stats.by_flaw_type:
        print("\n🔧 按缺陷类型统计:")
        print("-" * 60)
        print(f"{'缺陷类型':<25} {'测试数':>8} {'成功率':>10} {'Avg Score':>10}")
        print("-" * 60)
        flaw_types = [
            "sequence_disorder", "tool_misuse", "parameter_error",
            "missing_step", "redundant_operations", 
            "logical_inconsistency", "semantic_drift"
        ]
        for flaw_type in flaw_types:
            if flaw_type in model_stats.by_flaw_type:
                stats = model_stats.by_flaw_type[flaw_type]
                success_rate = stats.success_metrics.success_rate * 100
                avg_score = stats.score_metrics.final_scores.mean if stats.score_metrics.final_scores.count > 0 else 0
                print(f"{flaw_type:<25} {stats.success_metrics.total_tests:>8} {success_rate:>9.1f}% {avg_score:>10.3f}")
    
    # 测试均衡性分析
    print("\n📊 测试均衡性分析:")
    print("-" * 60)
    
    # 收集所有测试数量
    all_counts = []
    
    # 从prompt type收集
    for pt in ['baseline', 'optimal', 'cot']:
        if pt in model_stats.by_prompt_type:
            all_counts.append(model_stats.by_prompt_type[pt].success_metrics.total_tests)
    
    # 从flaw type收集
    for ft in model_stats.by_flaw_type.keys():
        all_counts.append(model_stats.by_flaw_type[ft].success_metrics.total_tests)
    
    if all_counts:
        min_count = min(all_counts)
        max_count = max(all_counts)
        avg_count = sum(all_counts) / len(all_counts)
        
        print(f"策略数量: {len(all_counts)}")
        print(f"最少测试: {min_count}")
        print(f"最多测试: {max_count}")
        print(f"平均测试: {avg_count:.1f}")
        print(f"差异: {max_count - min_count}")
        
        if max_count - min_count <= avg_count * 0.1:  # 10%以内
            print("✅ 分配非常均衡")
        elif max_count - min_count <= avg_count * 0.2:  # 20%以内
            print("✓ 分配较为均衡")
        else:
            print("⚠️ 分配不够均衡")
    
    # 工具可靠性敏感度（如果有数据）
    if model_stats.by_tool_reliability:
        print("\n🔧 工具可靠性敏感度:")
        print("-" * 60)
        print(f"{'可靠性':<10} {'测试数':>8} {'成功率':>10}")
        print("-" * 60)
        for reliability, metrics in sorted(model_stats.by_tool_reliability.items()):
            success_rate = metrics.success_rate * 100
            print(f"{reliability:<10.1f} {metrics.total_tests:>8} {success_rate:>9.1f}%")
    
    if detailed:
        # 显示更详细的信息
        print("\n📝 详细工具使用统计:")
        print("-" * 60)
        if model_stats.overall_execution.tools_used:
            sorted_tools = sorted(model_stats.overall_execution.tools_used.items(), 
                                key=lambda x: x[1], reverse=True)[:10]
            print("Top 10 使用最多的工具:")
            for tool, count in sorted_tools:
                print(f"  {tool}: {count}次")
    
    print("\n" + "=" * 80)
    print("报告生成完毕")
    print("=" * 80)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='查看增强批测试统计')
    parser.add_argument('--model', type=str, default='qwen2.5-3b-instruct',
                       help='模型名称')
    parser.add_argument('--detailed', action='store_true',
                       help='显示详细信息')
    args = parser.parse_args()
    
    view_enhanced_statistics(args.model, args.detailed)