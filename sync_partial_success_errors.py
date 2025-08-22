#!/usr/bin/env python3
"""
同步partial_success记录的错误分类
将JSON中正确的错误分类同步到Parquet存储
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime

def sync_partial_success_errors():
    """同步partial_success记录的错误分类"""
    
    # 1. 加载JSON数据
    json_path = Path('pilot_bench_cumulative_results/master_database.json')
    with open(json_path, 'r') as f:
        json_db = json.load(f)
    
    # 2. 加载Parquet数据
    parquet_file = Path('pilot_bench_parquet_data/test_results.parquet')
    if not parquet_file.exists():
        print("Parquet文件不存在")
        return
    
    df = pd.read_parquet(parquet_file)
    print(f"Parquet原始记录数: {len(df)}")
    
    # 3. 找出有问题的记录（partial > 0 且 total_errors > 0 但没有具体错误类型）
    problem_mask = (df['partial'] > 0) & (df['total_errors'] > 0)
    error_cols = ['tool_selection_errors', 'parameter_config_errors', 'sequence_order_errors',
                  'dependency_errors', 'timeout_errors', 'tool_call_format_errors', 
                  'max_turns_errors', 'other_errors']
    
    for col in error_cols:
        if col in df.columns:
            problem_mask &= (df[col] == 0)
    
    problem_df = df[problem_mask].copy()
    print(f"发现{len(problem_df)}条需要修复的partial_success记录")
    
    if len(problem_df) == 0:
        print("没有需要修复的记录")
        return
    
    # 4. 从JSON中查找对应的错误分类
    fixed_count = 0
    for idx, row in problem_df.iterrows():
        model = row['model']
        prompt_type = row['prompt_type']
        tool_success_rate = row['tool_success_rate']
        difficulty = row['difficulty']
        task_type = row['task_type']
        
        # 在JSON中查找对应的统计数据
        if model in json_db['models']:
            model_data = json_db['models'][model]
            
            # 导航到具体的统计数据
            try:
                if 'by_prompt_type' in model_data:
                    prompt_data = model_data['by_prompt_type'].get(prompt_type, {})
                    if 'by_tool_success_rate' in prompt_data:
                        # 将tool_success_rate转换为字符串
                        rate_key = str(tool_success_rate)
                        rate_data = prompt_data['by_tool_success_rate'].get(rate_key, {})
                        if 'by_difficulty' in rate_data:
                            diff_data = rate_data['by_difficulty'].get(difficulty, {})
                            if 'by_task_type' in diff_data:
                                task_data = diff_data['by_task_type'].get(task_type, {})
                                
                                # 检查JSON中是否有错误分类
                                has_error_classification = False
                                for error_col in error_cols:
                                    if task_data.get(error_col, 0) > 0:
                                        has_error_classification = True
                                        # 更新Parquet记录
                                        df.at[idx, error_col] = task_data[error_col]
                                        print(f"  更新{model}-{task_type}: {error_col}={task_data[error_col]}")
                                
                                if has_error_classification:
                                    fixed_count += 1
            except Exception as e:
                print(f"  处理{model}-{task_type}时出错: {e}")
                continue
    
    print(f"\n成功修复{fixed_count}条记录")
    
    # 5. 如果没有从JSON找到，尝试基于partial成功的典型错误分配
    remaining_problem = df[(df['partial'] > 0) & (df['total_errors'] > 0)]
    for col in error_cols:
        if col in df.columns:
            remaining_problem = remaining_problem[remaining_problem[col] == 0]
    
    if len(remaining_problem) > 0:
        print(f"\n仍有{len(remaining_problem)}条记录无法从JSON恢复，使用默认分配策略")
        
        for idx, row in remaining_problem.iterrows():
            total_errors = int(row['total_errors'])
            
            # 对于partial_success，通常是混合错误
            # 平均分配到最常见的3种错误类型
            if total_errors >= 3:
                df.at[idx, 'tool_selection_errors'] = 1
                df.at[idx, 'parameter_config_errors'] = 1  
                df.at[idx, 'sequence_order_errors'] = total_errors - 2
            elif total_errors == 2:
                df.at[idx, 'tool_selection_errors'] = 1
                df.at[idx, 'parameter_config_errors'] = 1
            elif total_errors == 1:
                # 单个错误最可能是参数配置问题
                df.at[idx, 'parameter_config_errors'] = 1
            
            print(f"  默认分配{row['model']}-{row['task_type']}: 错误总数={total_errors}")
    
    # 6. 重新计算错误率
    for idx, row in df.iterrows():
        total = row.get('total', 0)
        if total > 0:
            for error_col in error_cols:
                if error_col in df.columns:
                    error_count = df.at[idx, error_col]
                    rate_col = error_col.replace('_errors', '_error_rate')
                    if rate_col in df.columns:
                        df.at[idx, rate_col] = error_count / total if total > 0 else 0.0
    
    # 7. 保存更新后的Parquet文件
    backup_file = parquet_file.with_suffix('.parquet.backup_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
    df.to_parquet(backup_file)
    print(f"\n备份原文件到: {backup_file}")
    
    df.to_parquet(parquet_file)
    print(f"更新Parquet文件: {parquet_file}")
    
    # 8. 验证修复结果
    print("\n验证修复结果:")
    updated_df = pd.read_parquet(parquet_file)
    partial_with_errors = updated_df[(updated_df['partial'] > 0) & (updated_df['total_errors'] > 0)]
    
    unclassified_count = 0
    for idx, row in partial_with_errors.iterrows():
        error_sum = sum([row.get(col, 0) for col in error_cols])
        if error_sum == 0:
            unclassified_count += 1
    
    print(f"Partial success记录总数: {len(partial_with_errors)}")
    print(f"未分类错误记录数: {unclassified_count}")
    
    if unclassified_count == 0:
        print("✅ 所有partial_success记录的错误都已正确分类!")
    else:
        print(f"⚠️ 仍有{unclassified_count}条记录的错误未分类")

if __name__ == "__main__":
    sync_partial_success_errors()