#!/usr/bin/env python3
"""修复错误率计算"""

import pandas as pd
from pathlib import Path

parquet_path = Path('pilot_bench_parquet_data/test_results.parquet')
if parquet_path.exists():
    df = pd.read_parquet(parquet_path)
    
    # 重新计算错误率
    for idx, row in df.iterrows():
        total_errors = row['total_errors']
        if total_errors > 0:
            # 重新计算各种错误率
            df.at[idx, 'tool_selection_error_rate'] = row.get('tool_selection_errors', 0) / total_errors
            df.at[idx, 'parameter_error_rate'] = row.get('parameter_config_errors', 0) / total_errors
            df.at[idx, 'sequence_error_rate'] = row.get('sequence_order_errors', 0) / total_errors
            df.at[idx, 'dependency_error_rate'] = row.get('dependency_errors', 0) / total_errors
            df.at[idx, 'timeout_error_rate'] = row.get('timeout_errors', 0) / total_errors
            df.at[idx, 'format_error_rate'] = row.get('tool_call_format_errors', 0) / total_errors
            df.at[idx, 'max_turns_error_rate'] = row.get('max_turns_errors', 0) / total_errors
            df.at[idx, 'other_error_rate'] = row.get('other_errors', 0) / total_errors
    
    # 保存
    df.to_parquet(parquet_path, index=False)
    print("错误率已重新计算")
    
    # 验证
    for idx, row in df.iterrows():
        if row['total_errors'] > 0:
            print(f"\n{row['model']}/{row['task_type']}:")
            print(f"  total_errors: {row['total_errors']}")
            print(f"  other_errors: {row['other_errors']}")
            print(f"  other_error_rate: {row['other_error_rate']:.2%}")

