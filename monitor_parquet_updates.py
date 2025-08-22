#!/usr/bin/env python3
"""
实时监控Parquet数据更新情况
"""
import os
import time
import pandas as pd
from pathlib import Path
from datetime import datetime

os.environ['STORAGE_FORMAT'] = 'parquet'

def monitor_updates():
    """监控Parquet数据更新"""
    parquet_file = Path('pilot_bench_parquet_data/test_results.parquet')
    
    if not parquet_file.exists():
        print("❌ Parquet文件不存在")
        return
    
    print("=" * 60)
    print("📊 Parquet数据监控")
    print("=" * 60)
    
    # 读取当前数据
    df = pd.read_parquet(parquet_file)
    today = datetime.now().date().isoformat()
    
    print(f"📅 日期: {today}")
    print(f"📁 文件: {parquet_file}")
    print(f"📊 总记录数: {len(df)}")
    
    # 今天的记录
    if 'last_updated' in df.columns:
        today_df = df[df['last_updated'].str.contains(today)]
        print(f"🆕 今天的记录: {len(today_df)}")
        
        # 按模型统计
        print("\n按模型统计今天的更新:")
        if len(today_df) > 0:
            model_counts = today_df['model'].value_counts()
            for model, count in model_counts.items():
                print(f"  • {model}: {count}")
    
    # 缺陷测试统计
    print("\n缺陷测试统计:")
    flawed_df = df[df['prompt_type'].str.contains('flawed')]
    print(f"  总缺陷记录: {len(flawed_df)}")
    
    # 今天的缺陷测试
    today_flawed = flawed_df[flawed_df['last_updated'].str.contains(today)]
    print(f"  今天新增: {len(today_flawed)}")
    
    if len(today_flawed) > 0:
        print("\n  今天的缺陷测试分布:")
        for _, row in today_flawed.iterrows():
            print(f"    • {row['model']} | {row['prompt_type']} | {row['task_type']} | total={row.get('total', 0)}")
    
    # 文件修改时间
    mtime = datetime.fromtimestamp(parquet_file.stat().st_mtime)
    print(f"\n⏰ 文件最后修改: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 计算距离上次修改的时间
    time_diff = datetime.now() - mtime
    minutes = int(time_diff.total_seconds() / 60)
    seconds = int(time_diff.total_seconds() % 60)
    
    if minutes > 0:
        print(f"   距今: {minutes}分{seconds}秒")
    else:
        print(f"   距今: {seconds}秒")
    
    # 检查运行中的测试
    import subprocess
    result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
    test_processes = [line for line in result.stdout.split('\n') if 'smart_batch_runner' in line and 'grep' not in line]
    print(f"\n🔄 运行中的测试进程: {len(test_processes)}")
    
    # 显示正在测试的模型
    if test_processes:
        print("  正在测试的模型:")
        models_testing = set()
        for proc in test_processes:
            if '--model' in proc:
                parts = proc.split('--model')
                if len(parts) > 1:
                    model = parts[1].split()[0]
                    models_testing.add(model)
        
        for model in sorted(models_testing):
            print(f"    • {model}")

if __name__ == "__main__":
    monitor_updates()