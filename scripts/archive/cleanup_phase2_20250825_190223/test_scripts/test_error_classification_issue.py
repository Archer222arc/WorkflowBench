#!/usr/bin/env python3
"""
测试错误分类问题：为什么dependency_errors被归入other_errors
"""

import json
from pathlib import Path
import pandas as pd

def analyze_error_classification():
    """分析错误分类问题"""
    
    # 1. 检查JSON数据库
    json_path = Path('pilot_bench_cumulative_results/master_database.json')
    if json_path.exists():
        with open(json_path, 'r') as f:
            json_db = json.load(f)
        
        # 查找DeepSeek-V3-0324的数据
        if 'models' in json_db and 'DeepSeek-V3-0324' in json_db['models']:
            model_data = json_db['models']['DeepSeek-V3-0324']
            
            # 检查by_prompt_type -> optimal -> by_tool_success_rate -> 0.8 -> by_difficulty -> easy
            if 'by_prompt_type' in model_data and 'optimal' in model_data['by_prompt_type']:
                optimal_data = model_data['by_prompt_type']['optimal']
                
                print("=== DeepSeek-V3-0324 optimal 错误分类统计 ===")
                print(f"Total errors: {optimal_data.get('total_errors', 0)}")
                print(f"Timeout errors: {optimal_data.get('timeout_errors', 0)}")
                print(f"Dependency errors: {optimal_data.get('dependency_errors', 0)}")
                print(f"Tool selection errors: {optimal_data.get('tool_selection_errors', 0)}")
                print(f"Sequence order errors: {optimal_data.get('sequence_order_errors', 0)}")
                print(f"Parameter config errors: {optimal_data.get('parameter_config_errors', 0)}")
                print(f"Tool call format errors: {optimal_data.get('tool_call_format_errors', 0)}")
                print(f"Max turns errors: {optimal_data.get('max_turns_errors', 0)}")
                print(f"Other errors: {optimal_data.get('other_errors', 0)}")
                
                # 深入检查各个层级
                if 'by_tool_success_rate' in optimal_data:
                    for rate in optimal_data['by_tool_success_rate']:
                        rate_data = optimal_data['by_tool_success_rate'][rate]
                        if 'by_difficulty' in rate_data:
                            for difficulty in rate_data['by_difficulty']:
                                diff_data = rate_data['by_difficulty'][difficulty]
                                if 'by_task_type' in diff_data:
                                    for task_type in diff_data['by_task_type']:
                                        task_data = diff_data['by_task_type'][task_type]
                                        if task_data.get('other_errors', 0) > 0:
                                            print(f"\n找到other_errors: rate={rate}, difficulty={difficulty}, task_type={task_type}")
                                            print(f"  Other errors: {task_data.get('other_errors', 0)}")
                                            print(f"  Dependency errors: {task_data.get('dependency_errors', 0)}")
                                            print(f"  Total errors: {task_data.get('total_errors', 0)}")
    
    # 2. 检查Parquet数据
    parquet_path = Path('pilot_bench_parquet_data/test_results.parquet')
    if parquet_path.exists():
        df = pd.read_parquet(parquet_path)
        
        # 筛选DeepSeek-V3-0324的数据
        deepseek_df = df[df['model'] == 'DeepSeek-V3-0324']
        if len(deepseek_df) > 0:
            print("\n=== Parquet中DeepSeek-V3-0324的错误分类 ===")
            
            # 查看optimal prompt的数据
            optimal_df = deepseek_df[deepseek_df['prompt_type'] == 'optimal']
            if len(optimal_df) > 0:
                print(f"Optimal数据条数: {len(optimal_df)}")
                
                # 统计各种错误
                for _, row in optimal_df.iterrows():
                    if row.get('other_errors', 0) > 0:
                        print(f"\n发现other_errors记录:")
                        print(f"  Task type: {row.get('task_type')}")
                        print(f"  Difficulty: {row.get('difficulty')}")
                        print(f"  Tool success rate: {row.get('tool_success_rate')}")
                        print(f"  Other errors: {row.get('other_errors', 0)}")
                        print(f"  Dependency errors: {row.get('dependency_errors', 0)}")
                        print(f"  Total errors: {row.get('total_errors', 0)}")
                        
                        # 检查是否有ai_error_category字段
                        if 'ai_error_category' in row:
                            print(f"  AI error category: {row['ai_error_category']}")

if __name__ == "__main__":
    analyze_error_classification()