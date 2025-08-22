#!/usr/bin/env python3
"""
查看累积测试进度工具
显示每个模型的测试完成情况和统计信息
"""
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import argparse

def load_cumulative_results():
    """加载累积结果数据库"""
    db_path = Path("cumulative_test_results/results_database.json")
    if not db_path.exists():
        print("累积结果数据库不存在")
        return {}
    
    with open(db_path, 'r') as f:
        return json.load(f)

def analyze_progress(database, target_model=None):
    """分析测试进度"""
    # 统计每个模型的进度
    model_stats = defaultdict(lambda: {
        'total_tests': 0,
        'completed_tests': 0,
        'success_count': 0,
        'partial_success_count': 0,
        'by_task_type': defaultdict(lambda: {'total': 0, 'success': 0}),
        'by_prompt_type': defaultdict(lambda: {'total': 0, 'success': 0}),
        'by_flaw_type': defaultdict(lambda: {'total': 0, 'success': 0})
    })
    
    # 解析数据库
    for key, stats in database.items():
        parts = key.split('_')
        if len(parts) >= 3:
            model = parts[0]
            task_type = parts[1]
            prompt_type = parts[2]
            flaw_type = parts[3] if len(parts) > 3 else None
            
            if target_model and model != target_model:
                continue
            
            total = stats['total']
            success = stats['success']
            partial = stats.get('partial_success', 0)
            
            # 更新统计
            model_stats[model]['total_tests'] += total
            model_stats[model]['completed_tests'] += total
            model_stats[model]['success_count'] += success
            model_stats[model]['partial_success_count'] += partial
            
            # 按任务类型统计
            model_stats[model]['by_task_type'][task_type]['total'] += total
            model_stats[model]['by_task_type'][task_type]['success'] += success
            
            # 按提示类型统计
            model_stats[model]['by_prompt_type'][prompt_type]['total'] += total
            model_stats[model]['by_prompt_type'][prompt_type]['success'] += success
            
            # 按缺陷类型统计
            if flaw_type:
                model_stats[model]['by_flaw_type'][flaw_type]['total'] += total
                model_stats[model]['by_flaw_type'][flaw_type]['success'] += success
    
    return dict(model_stats)

def print_progress_report(model_stats):
    """打印进度报告"""
    print("\n" + "="*80)
    print("PILOT-Bench 累积测试进度报告")
    print("="*80)
    print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    if not model_stats:
        print("\n暂无测试数据")
        return
    
    # 按模型打印详细信息
    for model, stats in sorted(model_stats.items()):
        print(f"\n## 模型: {model}")
        print("-" * 60)
        
        # 整体统计
        total = stats['total_tests']
        if total > 0:
            success_rate = stats['success_count'] / total * 100
            partial_rate = stats['partial_success_count'] / total * 100
            print(f"总测试数: {total}")
            print(f"成功数: {stats['success_count']} ({success_rate:.1f}%)")
            print(f"部分成功: {stats['partial_success_count']} ({partial_rate:.1f}%)")
            print(f"失败数: {total - stats['success_count']} ({100 - success_rate:.1f}%)")
        
        # 按任务类型统计
        print("\n### 任务类型分解:")
        task_types = ['simple_task', 'basic_task', 'data_pipeline', 'api_integration', 'multi_stage_pipeline']
        for task_type in task_types:
            if task_type in stats['by_task_type']:
                t_stats = stats['by_task_type'][task_type]
                if t_stats['total'] > 0:
                    rate = t_stats['success'] / t_stats['total'] * 100
                    print(f"  {task_type:20s}: {t_stats['success']:3d}/{t_stats['total']:3d} ({rate:5.1f}%)")
        
        # 按提示类型统计
        print("\n### 提示类型分解:")
        prompt_types = ['baseline', 'optimal', 'cot', 'expert', 'creative']
        for prompt_type in prompt_types:
            if prompt_type in stats['by_prompt_type']:
                p_stats = stats['by_prompt_type'][prompt_type]
                if p_stats['total'] > 0:
                    rate = p_stats['success'] / p_stats['total'] * 100
                    print(f"  {prompt_type:20s}: {p_stats['success']:3d}/{p_stats['total']:3d} ({rate:5.1f}%)")
        
        # 按缺陷类型统计（如果有）
        if stats['by_flaw_type']:
            print("\n### 缺陷类型分解:")
            for flaw_type, f_stats in sorted(stats['by_flaw_type'].items()):
                if f_stats['total'] > 0:
                    rate = f_stats['success'] / f_stats['total'] * 100
                    print(f"  {flaw_type:20s}: {f_stats['success']:3d}/{f_stats['total']:3d} ({rate:5.1f}%)")

def estimate_completion_target(model_stats, target_per_combo=100):
    """估算完成目标所需的测试数"""
    print("\n" + "="*80)
    print("测试完成度分析（目标：每个组合100次）")
    print("="*80)
    
    # 预期的测试组合
    task_types = ['simple_task', 'basic_task', 'data_pipeline', 'api_integration', 'multi_stage_pipeline']
    prompt_types = ['baseline', 'optimal', 'cot']
    flaw_types = ['sequence_disorder', 'tool_misuse', 'parameter_error', 'missing_step', 
                  'redundant_operations', 'logical_inconsistency', 'semantic_drift']
    
    for model in sorted(model_stats.keys()):
        print(f"\n## {model}")
        
        # 计算正常测试的完成度
        normal_combos = len(task_types) * len(prompt_types)
        expected_normal = normal_combos * target_per_combo
        
        # 计算缺陷测试的完成度
        flawed_combos = len(task_types) * len(flaw_types)
        expected_flawed = flawed_combos * target_per_combo
        
        current_total = model_stats[model]['total_tests']
        expected_total = expected_normal + expected_flawed
        
        completion_rate = current_total / expected_total * 100 if expected_total > 0 else 0
        
        print(f"  当前进度: {current_total}/{expected_total} ({completion_rate:.1f}%)")
        print(f"  - 正常测试: 预期 {expected_normal} 个")
        print(f"  - 缺陷测试: 预期 {expected_flawed} 个")
        print(f"  - 剩余测试: {max(0, expected_total - current_total)} 个")

def main():
    parser = argparse.ArgumentParser(description="查看累积测试进度")
    parser.add_argument('--model', type=str, help='只查看特定模型的进度')
    parser.add_argument('--target', type=int, default=100, help='每个组合的目标测试次数')
    parser.add_argument('--export', type=str, help='导出进度报告到文件')
    args = parser.parse_args()
    
    # 加载数据
    database = load_cumulative_results()
    if not database:
        return
    
    # 分析进度
    model_stats = analyze_progress(database, args.model)
    
    # 打印报告
    print_progress_report(model_stats)
    
    # 估算完成度
    estimate_completion_target(model_stats, args.target)
    
    # 导出报告
    if args.export:
        with open(args.export, 'w') as f:
            # 重定向打印到文件
            import sys
            old_stdout = sys.stdout
            sys.stdout = f
            print_progress_report(model_stats)
            estimate_completion_target(model_stats, args.target)
            sys.stdout = old_stdout
        print(f"\n报告已导出到: {args.export}")

if __name__ == "__main__":
    main()