#!/usr/bin/env python3
"""分析轮数使用情况和max_turns错误"""

import json
from pathlib import Path

def analyze_turns_usage():
    """分析模型的轮数使用情况和max_turns错误"""
    db_path = Path('pilot_bench_cumulative_results/master_database.json')
    with open(db_path, 'r') as f:
        db = json.load(f)

    models_to_analyze = ['DeepSeek-V3-0324', 'DeepSeek-R1-0528']
    
    print('=' * 70)
    print('🔍 DeepSeek-R1 vs V3: 轮数使用和max_turns错误分析')
    print('=' * 70)
    print()

    for model_name in models_to_analyze:
        if model_name not in db['models']:
            continue
            
        model_data = db['models'][model_name]
        print(f'📊 {model_name}:')
        print('-' * 60)
        
        for prompt_type, prompt_data in model_data.get('by_prompt_type', {}).items():
            for tool_rate, rate_data in prompt_data.get('by_tool_success_rate', {}).items():
                for diff, diff_data in rate_data.get('by_difficulty', {}).items():
                    print(f'  📈 {prompt_type} - {tool_rate} - {diff}:')
                    
                    # 汇总统计
                    total_tests = 0
                    total_success = 0
                    total_max_turns_errors = 0
                    total_format_errors = 0
                    weighted_avg_turns = 0
                    weighted_execution_time = 0
                    weighted_tool_calls = 0
                    
                    for task, task_data in diff_data.get('by_task_type', {}).items():
                        total = task_data.get('total', 0)
                        success = task_data.get('success', 0)
                        avg_turns = task_data.get('avg_turns', 0)
                        avg_time = task_data.get('avg_execution_time', 0)
                        avg_tool_calls = task_data.get('avg_tool_calls', 0)
                        max_turns_errors = task_data.get('max_turns_errors', 0)
                        format_errors = task_data.get('tool_call_format_errors', 0)
                        
                        total_tests += total
                        total_success += success
                        total_max_turns_errors += max_turns_errors
                        total_format_errors += format_errors
                        
                        # 加权平均
                        if total > 0:
                            weighted_avg_turns += avg_turns * total
                            weighted_execution_time += avg_time * total
                            weighted_tool_calls += avg_tool_calls * total
                        
                        success_rate = success / total if total > 0 else 0
                        print(f'    {task:<20}: {success:>2}/{total:<2} ({success_rate:.1%}) | '
                              f'轮数:{avg_turns:>4.1f} | 时间:{avg_time:>5.1f}s | '
                              f'工具调用:{avg_tool_calls:>4.1f} | '
                              f'max_turns错误:{max_turns_errors} | 格式错误:{format_errors}')
                    
                    # 计算汇总的加权平均
                    if total_tests > 0:
                        weighted_avg_turns /= total_tests
                        weighted_execution_time /= total_tests
                        weighted_tool_calls /= total_tests
                    
                    overall_success_rate = total_success / total_tests if total_tests > 0 else 0
                    
                    print(f'    {"="*20}')
                    print(f'    {"汇总":<20}: {total_success:>2}/{total_tests:<2} ({overall_success_rate:.1%}) | '
                          f'轮数:{weighted_avg_turns:>4.1f} | 时间:{weighted_execution_time:>5.1f}s | '
                          f'工具调用:{weighted_tool_calls:>4.1f} | '
                          f'max_turns错误:{total_max_turns_errors} | 格式错误:{total_format_errors}')
                    
                    print()
        print()

    print('=' * 70)
    print('🎯 关键洞察分析')
    print('=' * 70)
    
    # 提取关键数据进行对比
    v3_data = db['models']['DeepSeek-V3-0324']['by_prompt_type']['optimal']['by_tool_success_rate']['0.8']['by_difficulty']['easy']['by_task_type']
    r1_data = db['models']['DeepSeek-R1-0528']['by_prompt_type']['optimal']['by_tool_success_rate']['0.8']['by_difficulty']['easy']['by_task_type']
    
    print('1. 📊 轮数使用对比:')
    print(f'{"任务类型":<20} {"V3轮数":<8} {"R1轮数":<8} {"差异":<8} {"分析":<30}')
    print('-' * 75)
    
    for task in v3_data.keys():
        if task in r1_data:
            v3_turns = v3_data[task].get('avg_turns', 0)
            r1_turns = r1_data[task].get('avg_turns', 0)
            diff = r1_turns - v3_turns
            
            v3_success = v3_data[task].get('success', 0) / v3_data[task].get('total', 1)
            r1_success = r1_data[task].get('success', 0) / r1_data[task].get('total', 1)
            
            analysis = ""
            if abs(diff) < 1:
                analysis = "轮数相近"
            elif diff > 0:
                analysis = f"R1多用{diff:.1f}轮"
            else:
                analysis = f"R1少用{abs(diff):.1f}轮"
            
            # 检查是否因为轮数不够
            if r1_turns < v3_turns and r1_success < v3_success:
                analysis += " (可能轮数不够)"
            elif r1_turns > v3_turns and r1_success < v3_success:
                analysis += " (轮数多但效果差)"
                
            print(f'{task:<20} {v3_turns:<8.1f} {r1_turns:<8.1f} {diff:<8.1f} {analysis:<30}')

    print()
    print('2. 🚨 Max_turns错误分析:')
    
    # 检查max_turns错误
    v3_max_turns_total = sum(task_data.get('max_turns_errors', 0) for task_data in v3_data.values())
    r1_max_turns_total = sum(task_data.get('max_turns_errors', 0) for task_data in r1_data.values())
    
    print(f'   DeepSeek-V3-0324: {v3_max_turns_total} 个max_turns错误')
    print(f'   DeepSeek-R1-0528: {r1_max_turns_total} 个max_turns错误')
    
    if r1_max_turns_total > v3_max_turns_total:
        print(f'   ⚠️  R1确实有更多max_turns错误 (+{r1_max_turns_total - v3_max_turns_total}个)')
        print('   这支持了"R1问得太仔细导致轮数不够"的假设')
    else:
        print('   📊 两个模型的max_turns错误数量相近')
    
    print()
    print('3. 💡 结论:')
    
    # 计算整体模式
    v3_avg_turns = sum(task_data.get('avg_turns', 0) * task_data.get('total', 0) for task_data in v3_data.values()) / sum(task_data.get('total', 0) for task_data in v3_data.values())
    r1_avg_turns = sum(task_data.get('avg_turns', 0) * task_data.get('total', 0) for task_data in r1_data.values()) / sum(task_data.get('total', 0) for task_data in r1_data.values())
    
    v3_success_rate = sum(task_data.get('success', 0) for task_data in v3_data.values()) / sum(task_data.get('total', 0) for task_data in v3_data.values())
    r1_success_rate = sum(task_data.get('success', 0) for task_data in r1_data.values()) / sum(task_data.get('total', 0) for task_data in r1_data.values())
    
    if r1_max_turns_total > 0:
        print(f'   ✅ "问得太仔细导致轮数不够"的假设 **有一定道理**')
        print(f'      - R1平均使用 {r1_avg_turns:.1f} 轮 vs V3的 {v3_avg_turns:.1f} 轮')
        print(f'      - R1有 {r1_max_turns_total} 个max_turns错误 vs V3的 {v3_max_turns_total} 个')
        print(f'      - 但这只是部分原因，格式错误仍然是主要问题')
    else:
        print(f'   📊 轮数使用模式分析:')
        print(f'      - R1平均使用 {r1_avg_turns:.1f} 轮 vs V3的 {v3_avg_turns:.1f} 轮')
        print(f'      - R1成功率 {r1_success_rate:.1%} vs V3的 {v3_success_rate:.1%}')
        if r1_avg_turns < v3_avg_turns:
            print(f'      - R1实际用轮数更少，主要问题可能是格式错误导致早期失败')
        else:
            print(f'      - R1用轮数相近或更多，问题不在轮数不够')

if __name__ == "__main__":
    analyze_turns_usage()