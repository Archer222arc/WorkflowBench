#!/usr/bin/env python3
"""检查数据库统计一致性"""

import json
from pathlib import Path

def check_statistics_consistency():
    """检查数据库统计的一致性"""
    # Load database
    db_path = Path('pilot_bench_cumulative_results/master_database.json')
    with open(db_path, 'r') as f:
        db = json.load(f)

    print('=== 数据库统计一致性检查 ===')
    print()

    # Check each model's statistics
    for model_name, model_data in db.get('models', {}).items():
        print(f'模型: {model_name}')
        
        # Check overall statistics
        overall = model_data.get('overall_stats', {})
        total = overall.get('total', 0)
        success = overall.get('success', 0)
        full_success = overall.get('full_success', 0)
        partial_success = overall.get('partial_success', 0)
        total_errors = overall.get('total_errors', 0)
        
        print(f'  总体统计: total={total}, success={success}, full_success={full_success}, partial_success={partial_success}')
        print(f'  错误统计: total_errors={total_errors}')
        
        # Check if statistics are consistent
        if total > 0:
            calculated_errors = total - success
            if calculated_errors != total_errors:
                print(f'  ❌ 错误数不一致: 计算出的错误数({calculated_errors}) != 记录的错误数({total_errors})')
            else:
                print(f'  ✅ 错误数一致')
                
            if success != (full_success + partial_success):
                print(f'  ❌ 成功数不一致: success({success}) != full_success({full_success}) + partial_success({partial_success})')
            else:
                print(f'  ✅ 成功数一致')
        
        # Check error breakdown for prompt types
        for prompt_type, prompt_data in model_data.get('by_prompt_type', {}).items():
            print(f'    提示类型: {prompt_type}')
            
            # Check tool_success_rate breakdown
            for tool_rate, rate_data in prompt_data.get('by_tool_success_rate', {}).items():
                for diff, diff_data in rate_data.get('by_difficulty', {}).items():
                    for task, task_data in diff_data.get('by_task_type', {}).items():
                        total_task = task_data.get('total', 0)
                        success_task = task_data.get('success', 0)
                        total_errors_task = task_data.get('total_errors', 0)
                        
                        # Check individual error types
                        error_types = [
                            'tool_selection_errors', 'parameter_config_errors', 
                            'sequence_order_errors', 'dependency_errors',
                            'timeout_errors', 'tool_call_format_errors',
                            'max_turns_errors', 'other_errors'
                        ]
                        
                        total_classified_errors = sum(task_data.get(error_type, 0) for error_type in error_types)
                        
                        if total_errors_task > 0 and total_classified_errors != total_errors_task:
                            print(f'      ❌ {tool_rate}->{diff}->{task}: 分类错误数({total_classified_errors}) != 总错误数({total_errors_task})')
                            
                            # Show breakdown
                            print(f'        错误分解:')
                            for error_type in error_types:
                                count = task_data.get(error_type, 0)
                                if count > 0:
                                    print(f'          {error_type}: {count}')
                        elif total_errors_task > 0:
                            print(f'      ✅ {tool_rate}->{diff}->{task}: 错误分类一致({total_classified_errors}={total_errors_task})')
                            
                            # Check error rates using correct field names
                            error_rate_sum = 0
                            rate_fields = [
                                'tool_selection_error_rate', 'parameter_error_rate',
                                'sequence_error_rate', 'dependency_error_rate', 
                                'timeout_error_rate', 'format_error_rate',
                                'max_turns_error_rate', 'other_error_rate'
                            ]
                            for rate_field in rate_fields:
                                rate = task_data.get(rate_field, 0)
                                error_rate_sum += rate
                                
                            if abs(error_rate_sum - 1.0) > 0.01:  # Allow small floating point errors
                                print(f'        ❌ 错误率总和不等于1: {error_rate_sum:.3f}')
                            else:
                                print(f'        ✅ 错误率总和正确: {error_rate_sum:.3f}')
        
        print()

if __name__ == "__main__":
    check_statistics_consistency()