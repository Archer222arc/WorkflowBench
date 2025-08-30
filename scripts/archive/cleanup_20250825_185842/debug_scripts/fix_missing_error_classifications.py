#!/usr/bin/env python3
"""修复Parquet中缺失的错误分类"""

import pandas as pd
from pathlib import Path

def fix_missing_classifications():
    parquet_path = Path('pilot_bench_parquet_data/test_results.parquet')
    if not parquet_path.exists():
        print("Parquet文件不存在")
        return
    
    df = pd.read_parquet(parquet_path)
    print(f"加载了 {len(df)} 条记录")
    
    # 找出有错误但没有分类的记录
    problem_mask = (
        (df['total_errors'] > 0) & 
        (df['tool_selection_errors'] == 0) &
        (df['parameter_config_errors'] == 0) &
        (df['sequence_order_errors'] == 0) &
        (df['dependency_errors'] == 0) &
        (df['timeout_errors'] == 0) &
        (df['other_errors'] == 0)
    )
    
    problem_records = df[problem_mask]
    print(f"\n发现 {len(problem_records)} 条有错误但没有分类的记录")
    
    if len(problem_records) > 0:
        # 对于这些记录，暂时将错误归类为other_errors
        # 因为没有原始的AI分类数据，无法准确分类
        df.loc[problem_mask, 'other_errors'] = df.loc[problem_mask, 'total_errors']
        print(f"已将这些记录的错误暂时归类为other_errors")
        
        # 保存修复后的数据
        df.to_parquet(parquet_path, index=False)
        print(f"已保存修复后的数据")
        
        # 验证
        df_new = pd.read_parquet(parquet_path)
        problem_mask_new = (
            (df_new['total_errors'] > 0) & 
            (df_new['tool_selection_errors'] == 0) &
            (df_new['parameter_config_errors'] == 0) &
            (df_new['sequence_order_errors'] == 0) &
            (df_new['dependency_errors'] == 0) &
            (df_new['timeout_errors'] == 0) &
            (df_new['other_errors'] == 0)
        )
        remaining = df_new[problem_mask_new]
        print(f"\n验证：剩余未分类的错误记录: {len(remaining)}")

if __name__ == '__main__':
    fix_missing_classifications()
