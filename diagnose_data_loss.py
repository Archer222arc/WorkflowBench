#!/usr/bin/env python3
"""诊断数据丢失问题"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime

def diagnose():
    print("=" * 60)
    print("数据诊断报告")
    print("=" * 60)
    
    # 1. 检查JSON数据库
    json_path = Path('pilot_bench_cumulative_results/master_database.json')
    if json_path.exists():
        with open(json_path, 'r') as f:
            json_db = json.load(f)
        
        print("\n1. JSON数据库状态:")
        print(f"   文件大小: {json_path.stat().st_size / 1024:.1f} KB")
        print(f"   最后修改: {datetime.fromtimestamp(json_path.stat().st_mtime)}")
        
        # 统计模型数据
        if 'models' in json_db:
            total_tests = 0
            for model, data in json_db['models'].items():
                tests = data.get('overall_stats', {}).get('total_tests', 0)
                total_tests += tests
                if tests > 0:
                    print(f"   {model}: {tests} tests")
            print(f"   总计: {total_tests} tests")
        
        # 检查test_groups
        if 'test_groups' in json_db:
            print(f"   test_groups数量: {len(json_db['test_groups'])}")
    
    # 2. 检查Parquet数据
    parquet_path = Path('pilot_bench_parquet_data/test_results.parquet')
    if parquet_path.exists():
        print("\n2. Parquet数据库状态:")
        print(f"   文件大小: {parquet_path.stat().st_size / 1024:.1f} KB")
        print(f"   最后修改: {datetime.fromtimestamp(parquet_path.stat().st_mtime)}")
        
        df = pd.read_parquet(parquet_path)
        print(f"   总记录数: {len(df)}")
        print(f"   模型数: {df['model'].nunique() if 'model' in df.columns else 0}")
        
        if 'model' in df.columns:
            model_counts = df['model'].value_counts()
            for model, count in model_counts.items():
                print(f"   {model}: {count} records")
    
    # 3. 检查增量文件
    inc_dir = Path('pilot_bench_parquet_data/incremental')
    if inc_dir.exists():
        print("\n3. 增量文件状态:")
        inc_files = list(inc_dir.glob('*.parquet'))
        print(f"   增量文件数: {len(inc_files)}")
        if inc_files:
            for f in sorted(inc_files)[-5:]:
                print(f"   {f.name}: {f.stat().st_size / 1024:.1f} KB")
    
    # 4. 检查备份文件
    backup_dir = Path('pilot_bench_parquet_data/backups')
    if backup_dir.exists():
        print("\n4. 备份文件状态:")
        backup_files = list(backup_dir.glob('*.parquet'))
        print(f"   备份文件数: {len(backup_files)}")
        if backup_files:
            latest = max(backup_files, key=lambda f: f.stat().st_mtime)
            print(f"   最新备份: {latest.name}")
            print(f"   备份时间: {datetime.fromtimestamp(latest.stat().st_mtime)}")
    
    # 5. 检查日志文件中的错误
    log_dir = Path('logs')
    if log_dir.exists():
        print("\n5. 最近日志状态:")
        log_files = sorted(log_dir.glob('batch_test_*.log'), 
                          key=lambda f: f.stat().st_mtime, 
                          reverse=True)[:5]
        
        for log_file in log_files:
            errors = 0
            warnings = 0
            with open(log_file, 'r') as f:
                for line in f:
                    if 'ERROR' in line:
                        errors += 1
                    if 'WARNING' in line:
                        warnings += 1
            print(f"   {log_file.name}: {errors} errors, {warnings} warnings")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    diagnose()