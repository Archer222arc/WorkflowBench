#!/usr/bin/env python3
"""分析DeepSeek-R1-0528性能较低的原因"""

import json
from pathlib import Path

def analyze_r1_vs_v3():
    """对比分析DeepSeek-R1-0528 vs DeepSeek-V3-0324的性能差异"""
    db_path = Path('pilot_bench_cumulative_results/master_database.json')
    with open(db_path, 'r') as f:
        db = json.load(f)

    models = {
        'DeepSeek-V3-0324': db['models']['DeepSeek-V3-0324'],
        'DeepSeek-R1-0528': db['models']['DeepSeek-R1-0528']
    }

    print('=' * 60)
    print('🔍 DeepSeek-R1-0528 vs DeepSeek-V3-0324 性能对比分析')
    print('=' * 60)
    print()

    # 分析每个任务类型的详细表现
    for model_name, model_data in models.items():
        print(f'📊 {model_name}:')
        print('-' * 50)
        
        for prompt_type, prompt_data in model_data.get('by_prompt_type', {}).items():
            for tool_rate, rate_data in prompt_data.get('by_tool_success_rate', {}).items():
                for diff, diff_data in rate_data.get('by_difficulty', {}).items():
                    print(f'  📈 {prompt_type} - {tool_rate} - {diff}:')
                    
                    for task, task_data in diff_data.get('by_task_type', {}).items():
                        total = task_data.get('total', 0)
                        success = task_data.get('success', 0)
                        partial = task_data.get('partial_success', 0) 
                        full = success - partial
                        total_errors = task_data.get('total_errors', 0)
                        success_rate = success / total if total > 0 else 0
                        
                        # 详细错误分析
                        format_errors = task_data.get('tool_call_format_errors', 0)
                        timeout_errors = task_data.get('timeout_errors', 0)
                        parameter_errors = task_data.get('parameter_config_errors', 0)
                        tool_selection_errors = task_data.get('tool_selection_errors', 0)
                        sequence_errors = task_data.get('sequence_order_errors', 0)
                        dependency_errors = task_data.get('dependency_errors', 0)
                        max_turns_errors = task_data.get('max_turns_errors', 0)
                        other_errors = task_data.get('other_errors', 0)
                        
                        # 执行指标
                        avg_time = task_data.get('avg_execution_time', 0)
                        avg_turns = task_data.get('avg_turns', 0)
                        avg_tool_calls = task_data.get('avg_tool_calls', 0)
                        tool_coverage = task_data.get('tool_coverage_rate', 0)
                        
                        print(f'    {task}: {success}/{total} ({success_rate:.1%}) [完全:{full}, 部分:{partial}]')
                        
                        # 显示主要错误类型
                        if total_errors > 0:
                            error_details = []
                            if format_errors > 0:
                                error_details.append(f'格式:{format_errors}')
                            if timeout_errors > 0:
                                error_details.append(f'超时:{timeout_errors}')
                            if parameter_errors > 0:
                                error_details.append(f'参数:{parameter_errors}')
                            if tool_selection_errors > 0:
                                error_details.append(f'工具选择:{tool_selection_errors}')
                            if sequence_errors > 0:
                                error_details.append(f'顺序:{sequence_errors}')
                            if dependency_errors > 0:
                                error_details.append(f'依赖:{dependency_errors}')
                            if max_turns_errors > 0:
                                error_details.append(f'轮次:{max_turns_errors}')
                            if other_errors > 0:
                                error_details.append(f'其他:{other_errors}')
                            
                            if error_details:
                                print(f'      错误: {", ".join(error_details)}')
                        
                        # 显示执行指标
                        print(f'      执行: 时间{avg_time:.1f}s, 轮次{avg_turns:.1f}, 工具调用{avg_tool_calls:.1f}, 覆盖率{tool_coverage:.1%}')
        print()

    print('=' * 60)
    print('📋 关键差异分析')
    print('=' * 60)
    
    # 对比分析
    v3_data = models['DeepSeek-V3-0324']['by_prompt_type']['optimal']['by_tool_success_rate']['0.8']['by_difficulty']['easy']['by_task_type']
    r1_data = models['DeepSeek-R1-0528']['by_prompt_type']['optimal']['by_tool_success_rate']['0.8']['by_difficulty']['easy']['by_task_type']
    
    print('任务类型对比:')
    print(f'{"任务类型":<20} {"V3成功率":<10} {"R1成功率":<10} {"差异":<10} {"主要问题(R1)":<25}')
    print('-' * 75)
    
    for task in v3_data.keys():
        if task in r1_data:
            v3_success = v3_data[task].get('success', 0) / v3_data[task].get('total', 1)
            r1_success = r1_data[task].get('success', 0) / r1_data[task].get('total', 1)
            diff = v3_success - r1_success
            
            # 找出R1的主要问题
            r1_task = r1_data[task]
            main_issues = []
            if r1_task.get('tool_call_format_errors', 0) > 0:
                main_issues.append(f"格式:{r1_task['tool_call_format_errors']}")
            if r1_task.get('timeout_errors', 0) > 0:
                main_issues.append(f"超时:{r1_task['timeout_errors']}")
            if r1_task.get('other_errors', 0) > 0:
                main_issues.append(f"其他:{r1_task['other_errors']}")
            
            main_issue_str = ", ".join(main_issues[:2]) if main_issues else "无明显问题"
            
            print(f'{task:<20} {v3_success:<10.1%} {r1_success:<10.1%} {diff:<10.1%} {main_issue_str:<25}')

    print()
    print('💡 总结:')
    
    # 计算整体指标对比
    v3_total = sum(task_data.get('success', 0) for task_data in v3_data.values())
    v3_tests = sum(task_data.get('total', 0) for task_data in v3_data.values())
    r1_total = sum(task_data.get('success', 0) for task_data in r1_data.values())
    r1_tests = sum(task_data.get('total', 0) for task_data in r1_data.values())
    
    v3_format_errors = sum(task_data.get('tool_call_format_errors', 0) for task_data in v3_data.values())
    r1_format_errors = sum(task_data.get('tool_call_format_errors', 0) for task_data in r1_data.values())
    
    v3_timeout_errors = sum(task_data.get('timeout_errors', 0) for task_data in v3_data.values())
    r1_timeout_errors = sum(task_data.get('timeout_errors', 0) for task_data in r1_data.values())
    
    v3_other_errors = sum(task_data.get('other_errors', 0) for task_data in v3_data.values())
    r1_other_errors = sum(task_data.get('other_errors', 0) for task_data in r1_data.values())
    
    print(f'- DeepSeek-V3-0324: {v3_total}/{v3_tests} = {v3_total/v3_tests:.1%} 成功率')
    print(f'- DeepSeek-R1-0528: {r1_total}/{r1_tests} = {r1_total/r1_tests:.1%} 成功率')
    print(f'- 成功率差异: {(v3_total/v3_tests) - (r1_total/r1_tests):.1%}')
    print()
    
    print('错误类型对比:')
    print(f'- 格式错误: V3={v3_format_errors}, R1={r1_format_errors} (多{r1_format_errors-v3_format_errors}个)')
    print(f'- 超时错误: V3={v3_timeout_errors}, R1={r1_timeout_errors} (多{r1_timeout_errors-v3_timeout_errors}个)')  
    print(f'- 其他错误: V3={v3_other_errors}, R1={r1_other_errors} (多{r1_other_errors-v3_other_errors}个)')
    
    if r1_format_errors > v3_format_errors:
        print(f'\n🔍 主要问题: R1模型有更多格式错误 ({r1_format_errors-v3_format_errors}个额外)')
        print('   这可能是因为R1模型在工具调用格式方面不如V3模型稳定')
    
    if r1_timeout_errors > v3_timeout_errors:
        print(f'\n⏰ 超时问题: R1模型有更多超时 ({r1_timeout_errors-v3_timeout_errors}个额外)')
        print('   这表明R1模型执行速度可能较慢或陷入死循环')

if __name__ == "__main__":
    analyze_r1_vs_v3()