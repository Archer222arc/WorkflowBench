#!/usr/bin/env python3
"""
监控Parquet数据更新
"""

import time
import pandas as pd
from pathlib import Path
from datetime import datetime

def monitor_parquet():
    """监控Parquet文件更新"""
    parquet_file = Path('pilot_bench_parquet_data/test_results.parquet')
    incremental_dir = Path('pilot_bench_parquet_data/incremental')
    
    print("=" * 60)
    print("Parquet数据监控")
    print("=" * 60)
    
    # 检查主文件
    if parquet_file.exists():
        df = pd.read_parquet(parquet_file)
        print(f"\n📊 主文件状态:")
        print(f"   记录数: {len(df)}")
        print(f"   文件大小: {parquet_file.stat().st_size / 1024:.1f} KB")
        print(f"   最后修改: {datetime.fromtimestamp(parquet_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
        
        if len(df) > 0:
            # 显示最新的几条记录
            print(f"\n   最新记录:")
            latest = df.tail(3)[['model', 'prompt_type', 'difficulty', 'task_type', 'total', 'success_rate']]
            for _, row in latest.iterrows():
                print(f"     - {row['model']}: {row['prompt_type']}/{row['difficulty']}/{row['task_type']} - "
                      f"总数:{row['total']}, 成功率:{row['success_rate']:.1%}")
    else:
        print("❌ 主文件不存在")
    
    # 检查增量文件
    if incremental_dir.exists():
        inc_files = list(incremental_dir.glob('*.parquet'))
        print(f"\n📂 增量文件:")
        print(f"   文件数: {len(inc_files)}")
        
        if inc_files:
            # 显示最新的增量文件
            latest_inc = max(inc_files, key=lambda f: f.stat().st_mtime)
            print(f"   最新文件: {latest_inc.name}")
            print(f"   最后修改: {datetime.fromtimestamp(latest_inc.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
            
            df_inc = pd.read_parquet(latest_inc)
            print(f"   记录数: {len(df_inc)}")
    else:
        print("📂 增量目录不存在")
    
    # 检查JSON数据对比
    json_file = Path('pilot_bench_cumulative_results/master_database.json')
    if json_file.exists():
        print(f"\n📄 JSON文件对比:")
        print(f"   最后修改: {datetime.fromtimestamp(json_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   文件大小: {json_file.stat().st_size / 1024:.1f} KB")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    monitor_parquet()