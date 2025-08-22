#!/usr/bin/env python3
"""分析错误计数差异"""

import json
from pathlib import Path

def analyze_error_discrepancy():
    """分析错误计数差异的根本原因"""
    db_path = Path('pilot_bench_cumulative_results/master_database.json')
    with open(db_path, 'r') as f:
        db = json.load(f)

    print('=== 分析错误计数差异 ===')
    print()

    # Check first model in detail
    model_name = 'DeepSeek-V3-0324'
    model_data = db['models'][model_name]

    print(f'模型: {model_name}')

    total_tests = 0
    total_success = 0
    total_full_success = 0
    total_partial_success = 0
    total_errors_from_tasks = 0

    print('任务级别详细统计:')
    for prompt_type, prompt_data in model_data.get('by_prompt_type', {}).items():
        for tool_rate, rate_data in prompt_data.get('by_tool_success_rate', {}).items():
            for diff, diff_data in rate_data.get('by_difficulty', {}).items():
                for task, task_data in diff_data.get('by_task_type', {}).items():
                    task_total = task_data.get('total', 0)
                    task_success = task_data.get('success', 0)
                    task_partial = task_data.get('partial_success', 0)
                    task_full = task_success - task_partial  # full = success - partial
                    task_errors = task_data.get('total_errors', 0)
                    task_failures = task_total - task_success  # failures = total - success
                    
                    total_tests += task_total
                    total_success += task_success
                    total_partial_success += task_partial
                    total_full_success += task_full
                    total_errors_from_tasks += task_errors
                    
                    print(f'  {task}: total={task_total}, success={task_success} (full={task_full}, partial={task_partial}), failures={task_failures}, errors={task_errors}')
                    
                    # The key insight: partial_success can still have errors!
                    # A test can be partial_success AND have errors
                    if task_errors != task_failures and task_partial > 0:
                        print(f'    ⚠️  注意: errors({task_errors}) != failures({task_failures}), partial_success({task_partial}) > 0')
                        print(f'    这意味着一些partial success的测试仍然记录了错误')

    print(f'\n汇总:')
    print(f'  total_tests: {total_tests}')
    print(f'  total_success: {total_success} (full: {total_full_success}, partial: {total_partial_success})')
    print(f'  total_failures: {total_tests - total_success}')  
    print(f'  total_errors_from_tasks: {total_errors_from_tasks}')

    print(f'\n关键理解:')
    print(f'  - success = full_success + partial_success')
    print(f'  - failure = total - success') 
    print(f'  - 但是 errors 可能 > failures，因为 partial success 也可能有错误')
    print(f'  - partial success 意味着测试部分成功，但过程中可能仍有错误')
    
    # Check if this interpretation is correct
    expected_relationship = f'errors >= failures (因为partial success可能有错误)'
    actual_relationship = f'errors({total_errors_from_tasks}) vs failures({total_tests - total_success})'
    print(f'  - 预期关系: {expected_relationship}')
    print(f'  - 实际情况: {actual_relationship}')
    
    if total_errors_from_tasks >= (total_tests - total_success):
        print(f'  ✅ 这解释了为什么错误数大于失败数')
    else:
        print(f'  ❌ 这不能解释差异，需要进一步调查')

if __name__ == "__main__":
    analyze_error_discrepancy()