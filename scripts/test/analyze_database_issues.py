#!/usr/bin/env python3
"""分析数据库中的统计问题"""

import json
from pathlib import Path

def analyze_database_issues():
    """分析数据库中的具体问题"""
    # Load database
    db_path = Path('pilot_bench_cumulative_results/master_database.json')
    with open(db_path, 'r') as f:
        db = json.load(f)

    print('=== 数据库统计问题分析 ===')
    print()

    issues_found = []

    for model_name, model_data in db.get('models', {}).items():
        print(f'模型: {model_name}')
        
        # Issue 1: Check overall_stats 
        overall = model_data.get('overall_stats', {})
        if not overall or overall.get('total', 0) == 0:
            issues_found.append(f'{model_name}: overall_stats 缺失或为空')
            print(f'  ❌ overall_stats 缺失或为空: {overall}')
        
        # Issue 2: Check error rate calculations in task-level data
        for prompt_type, prompt_data in model_data.get('by_prompt_type', {}).items():
            for tool_rate, rate_data in prompt_data.get('by_tool_success_rate', {}).items():
                for diff, diff_data in rate_data.get('by_difficulty', {}).items():
                    for task, task_data in diff_data.get('by_task_type', {}).items():
                        total_errors_task = task_data.get('total_errors', 0)
                        
                        if total_errors_task == 0:
                            # When there are no errors, all error rates should be 0
                            error_types = [
                                'tool_selection_errors', 'parameter_config_errors', 
                                'sequence_order_errors', 'dependency_errors',
                                'timeout_errors', 'tool_call_format_errors',
                                'max_turns_errors', 'other_errors'
                            ]
                            
                            # Check if all error rates are properly 0
                            for error_type in error_types:
                                rate_key = error_type.replace('_errors', '_error_rate')
                                rate = task_data.get(rate_key, 0)
                                if rate != 0:
                                    issues_found.append(f'{model_name} {tool_rate}->{diff}->{task}: {rate_key} 应该为0但是是{rate}')
                                    print(f'  ❌ {tool_rate}->{diff}->{task}: {rate_key} 应该为0但是是{rate} (总错误数=0)')
                        
                        elif total_errors_task > 0:
                            # When there are errors, check if rates sum to 1
                            error_rate_sum = 0
                            for error_type in ['tool_selection_errors', 'parameter_config_errors', 
                                             'sequence_order_errors', 'dependency_errors',
                                             'timeout_errors', 'tool_call_format_errors',
                                             'max_turns_errors', 'other_errors']:
                                rate_key = error_type.replace('_errors', '_error_rate')
                                rate = task_data.get(rate_key, 0)
                                error_rate_sum += rate
                            
                            if abs(error_rate_sum - 1.0) > 0.01:
                                issues_found.append(f'{model_name} {tool_rate}->{diff}->{task}: 错误率总和 {error_rate_sum:.3f} != 1.0')
                                print(f'  ❌ {tool_rate}->{diff}->{task}: 错误率总和 {error_rate_sum:.3f} != 1.0 (总错误数={total_errors_task})')
                                
                                # Show individual rates
                                print('      错误率分解:')
                                for error_type in ['tool_selection_errors', 'parameter_config_errors', 
                                                 'sequence_order_errors', 'dependency_errors',
                                                 'timeout_errors', 'tool_call_format_errors',
                                                 'max_turns_errors', 'other_errors']:
                                    rate_key = error_type.replace('_errors', '_error_rate')
                                    rate = task_data.get(rate_key, 0)
                                    count = task_data.get(error_type, 0)
                                    if rate > 0 or count > 0:
                                        print(f'        {rate_key}: {rate:.3f} (count: {count})')
        print()

    print(f'\n=== 问题总结 ===')
    print(f'共发现 {len(issues_found)} 个问题:')
    for i, issue in enumerate(issues_found, 1):
        print(f'{i}. {issue}')
    
    return issues_found

if __name__ == "__main__":
    analyze_database_issues()