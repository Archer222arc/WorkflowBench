#!/usr/bin/env python3
"""
实时监控Parquet数据更新
"""

import time
import pandas as pd
from pathlib import Path
from datetime import datetime

def monitor_parquet_realtime():
    """实时监控Parquet文件更新"""
    parquet_file = Path('pilot_bench_parquet_data/test_results.parquet')
    json_file = Path('pilot_bench_cumulative_results/master_database.json')
    
    print("=" * 60)
    print("📊 Parquet实时监控")
    print("=" * 60)
    
    last_parquet_mtime = 0
    last_json_mtime = 0
    last_parquet_count = 0
    
    try:
        while True:
            # 检查Parquet文件
            if parquet_file.exists():
                current_mtime = parquet_file.stat().st_mtime
                if current_mtime != last_parquet_mtime:
                    df = pd.read_parquet(parquet_file)
                    current_count = len(df)
                    
                    if current_count != last_parquet_count:
                        print(f"\n🚀 [Parquet更新] {datetime.now().strftime('%H:%M:%S')}")
                        print(f"   记录数: {last_parquet_count} → {current_count} (+{current_count - last_parquet_count})")
                        
                        # 显示新增的记录
                        if last_parquet_count > 0:
                            new_records = df.iloc[last_parquet_count:]
                            for _, row in new_records.iterrows():
                                print(f"   新记录: {row['model']} / {row['prompt_type']} / {row['task_type']}")
                        
                        last_parquet_count = current_count
                    
                    last_parquet_mtime = current_mtime
            
            # 检查JSON文件
            if json_file.exists():
                current_json_mtime = json_file.stat().st_mtime
                if current_json_mtime != last_json_mtime:
                    print(f"📄 [JSON更新] {datetime.now().strftime('%H:%M:%S')}")
                    last_json_mtime = current_json_mtime
            
            # 显示运行中的进程数
            import subprocess
            result = subprocess.run(['pgrep', '-f', 'smart_batch_runner'], capture_output=True, text=True)
            process_count = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
            
            print(f"\r⏳ 监控中... 进程数: {process_count} | Parquet记录: {last_parquet_count} | {datetime.now().strftime('%H:%M:%S')}", end="", flush=True)
            
            time.sleep(5)  # 每5秒检查一次
            
    except KeyboardInterrupt:
        print("\n\n监控结束")

if __name__ == "__main__":
    monitor_parquet_realtime()