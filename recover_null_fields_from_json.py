#!/usr/bin/env python3
"""
从JSON数据库恢复Parquet中的null字段
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import numpy as np

def recover_null_fields():
    """从JSON恢复Parquet中的null字段"""
    
    print("=" * 60)
    print("从JSON恢复Parquet中的null字段")
    print("=" * 60)
    
    # 1. 读取数据
    print("\n1. 读取数据...")
    json_path = Path('pilot_bench_cumulative_results/master_database.json')
    with open(json_path, 'r') as f:
        json_db = json.load(f)
    
    parquet_file = Path('pilot_bench_parquet_data/test_results.parquet')
    df = pd.read_parquet(parquet_file)
    
    # 备份原始Parquet文件
    backup_path = parquet_file.parent / f"test_results_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
    df.to_parquet(backup_path, index=False)
    print(f"   ✅ 已备份到 {backup_path.name}")
    
    # 2. 统计null值
    null_mask = df['avg_workflow_score'].isnull()
    null_count = null_mask.sum()
    print(f"\n2. 发现 {null_count} 条记录有null值")
    
    # 3. 恢复数据
    recovered_count = 0
    failed_count = 0
    deleted_indices = []
    
    print("\n3. 开始恢复数据...")
    
    for idx in df[null_mask].index:
        row = df.loc[idx]
        model = row['model']
        prompt_type = row['prompt_type']
        tool_success_rate = str(row['tool_success_rate'])
        difficulty = row['difficulty']
        task_type = row['task_type']
        
        # 在JSON中查找对应数据
        try:
            if model in json_db.get('models', {}):
                model_data = json_db['models'][model]
                
                # 导航到具体的任务数据
                if 'by_prompt_type' in model_data and prompt_type in model_data['by_prompt_type']:
                    prompt_data = model_data['by_prompt_type'][prompt_type]
                    
                    if 'by_tool_success_rate' in prompt_data and tool_success_rate in prompt_data['by_tool_success_rate']:
                        rate_data = prompt_data['by_tool_success_rate'][tool_success_rate]
                        
                        if 'by_difficulty' in rate_data and difficulty in rate_data['by_difficulty']:
                            diff_data = rate_data['by_difficulty'][difficulty]
                            
                            if 'by_task_type' in diff_data and task_type in diff_data['by_task_type']:
                                task_data = diff_data['by_task_type'][task_type]
                                
                                # 恢复所有缺失的字段
                                fields_to_recover = [
                                    'avg_workflow_score', 'avg_phase2_score', 'avg_quality_score', 'avg_final_score',
                                    'total_errors', 'tool_call_format_errors', 'timeout_errors', 'dependency_errors',
                                    'parameter_config_errors', 'tool_selection_errors', 'sequence_order_errors',
                                    'max_turns_errors', 'other_errors', 'tool_selection_error_rate',
                                    'parameter_error_rate', 'sequence_error_rate', 'dependency_error_rate',
                                    'timeout_error_rate', 'format_error_rate', 'max_turns_error_rate',
                                    'other_error_rate', 'assisted_failure', 'assisted_success',
                                    'total_assisted_turns', 'tests_with_assistance', 'avg_assisted_turns',
                                    'assisted_success_rate', 'assistance_rate', 'full_success',
                                    'partial_success', 'successful', 'full_success_rate', 'partial_success_rate'
                                ]
                                
                                recovered = False
                                for field in fields_to_recover:
                                    if field in task_data and pd.isna(df.loc[idx, field]):
                                        df.loc[idx, field] = task_data[field]
                                        recovered = True
                                
                                if recovered:
                                    recovered_count += 1
                                    if recovered_count % 10 == 0:
                                        print(f"   已恢复 {recovered_count} 条记录...")
                                else:
                                    # JSON中也没有完整数据，标记为删除
                                    deleted_indices.append(idx)
                                    failed_count += 1
                            else:
                                deleted_indices.append(idx)
                                failed_count += 1
                        else:
                            deleted_indices.append(idx)
                            failed_count += 1
                    else:
                        deleted_indices.append(idx)
                        failed_count += 1
                else:
                    deleted_indices.append(idx)
                    failed_count += 1
            else:
                deleted_indices.append(idx)
                failed_count += 1
                
        except Exception as e:
            print(f"   ⚠️ 处理记录 {idx} 时出错: {e}")
            deleted_indices.append(idx)
            failed_count += 1
    
    print(f"\n   ✅ 成功恢复 {recovered_count} 条记录")
    print(f"   ❌ 无法恢复 {failed_count} 条记录（将被删除）")
    
    # 4. 删除无法恢复的记录
    if deleted_indices:
        print(f"\n4. 删除 {len(deleted_indices)} 条无法恢复的记录...")
        df_cleaned = df.drop(deleted_indices)
    else:
        df_cleaned = df
    
    # 5. 保存清理后的数据
    print("\n5. 保存清理后的数据...")
    df_cleaned.to_parquet(parquet_file, index=False)
    print(f"   ✅ 已保存 {len(df_cleaned)} 条记录到 test_results.parquet")
    
    # 6. 验证结果
    print("\n6. 验证结果...")
    df_verify = pd.read_parquet(parquet_file)
    remaining_nulls = df_verify['avg_workflow_score'].isnull().sum()
    
    if remaining_nulls == 0:
        print("   ✅ 所有null值已成功处理！")
    else:
        print(f"   ⚠️ 仍有 {remaining_nulls} 条记录包含null值")
    
    # 7. 生成报告
    print("\n" + "=" * 60)
    print("恢复报告")
    print("=" * 60)
    print(f"原始记录数: {len(df)}")
    print(f"null值记录数: {null_count}")
    print(f"成功恢复: {recovered_count}")
    print(f"删除记录: {failed_count}")
    print(f"最终记录数: {len(df_cleaned)}")
    print(f"数据完整率: {(len(df_cleaned) - remaining_nulls) / len(df_cleaned) * 100:.1f}%")
    
    return recovered_count, failed_count

if __name__ == "__main__":
    recovered, failed = recover_null_fields()
    print(f"\n✅ 处理完成！恢复 {recovered} 条，删除 {failed} 条。")