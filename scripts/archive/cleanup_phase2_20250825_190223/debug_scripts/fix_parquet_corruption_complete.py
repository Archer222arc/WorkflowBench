#!/usr/bin/env python3
"""
完整修复 Parquet 文件损坏问题
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime
import pandas as pd

def fix_parquet_corruption():
    """修复 Parquet 文件损坏"""
    
    print("=" * 60)
    print("修复 Parquet 文件损坏问题")
    print("=" * 60)
    
    base_dir = Path("pilot_bench_parquet_data")
    test_results_path = base_dir / "test_results.parquet"
    
    # 1. 备份现有目录
    if base_dir.exists():
        backup_name = f"pilot_bench_parquet_data.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        print(f"\n1. 备份现有数据到 {backup_name}...")
        shutil.copytree(base_dir, backup_name)
        print("   ✅ 备份完成")
    
    # 2. 尝试恢复数据
    recovered_data = []
    
    # 尝试从备份文件恢复
    if base_dir.exists():
        backup_files = sorted(base_dir.glob("test_results_backup_*.parquet"))
        for backup_file in backup_files:
            try:
                df = pd.read_parquet(backup_file)
                print(f"   ✅ 从 {backup_file.name} 恢复了 {len(df)} 条记录")
                recovered_data.append(df)
            except Exception as e:
                print(f"   ❌ 无法读取 {backup_file.name}: {e}")
    
    # 3. 尝试从 JSON 恢复
    json_file = base_dir / "test_results.parquet.as.json"
    if json_file.exists():
        try:
            df = pd.read_json(json_file)
            print(f"   ✅ 从 JSON 文件恢复了 {len(df)} 条记录")
            recovered_data.append(df)
        except Exception as e:
            print(f"   ❌ 无法读取 JSON 文件: {e}")
    
    # 4. 合并恢复的数据
    if recovered_data:
        print("\n2. 合并恢复的数据...")
        all_data = pd.concat(recovered_data, ignore_index=True)
        
        # 去重
        key_cols = ['model', 'prompt_type', 'tool_success_rate', 'difficulty', 'task_type']
        key_cols = [col for col in key_cols if col in all_data.columns]
        
        if key_cols:
            all_data = all_data.drop_duplicates(subset=key_cols, keep='last')
        
        print(f"   ✅ 合并后有 {len(all_data)} 条唯一记录")
        
        # 5. 保存新的 Parquet 文件
        print("\n3. 创建新的 Parquet 文件...")
        
        # 确保目录存在
        base_dir.mkdir(parents=True, exist_ok=True)
        incremental_dir = base_dir / "incremental"
        incremental_dir.mkdir(exist_ok=True)
        
        # 保存主文件
        all_data.to_parquet(test_results_path, index=False)
        print(f"   ✅ 保存了 {len(all_data)} 条记录到 test_results.parquet")
        
        # 验证文件可读
        try:
            df_verify = pd.read_parquet(test_results_path)
            print(f"   ✅ 验证成功：文件包含 {len(df_verify)} 条记录")
        except Exception as e:
            print(f"   ❌ 验证失败: {e}")
            return False
            
    else:
        # 没有可恢复的数据，创建空文件
        print("\n2. 没有可恢复的数据，创建空的 Parquet 结构...")
        
        # 创建目录
        base_dir.mkdir(parents=True, exist_ok=True)
        incremental_dir = base_dir / "incremental"
        incremental_dir.mkdir(exist_ok=True)
        
        # 创建空 DataFrame 有正确的结构
        columns = [
            'model', 'prompt_type', 'tool_success_rate', 'difficulty', 'task_type',
            'total', 'successful', 'partial', 'failed',
            'success_rate', 'partial_rate', 'failure_rate',
            'avg_execution_time', 'avg_turns', 'tool_coverage_rate',
            'last_updated'
        ]
        
        empty_df = pd.DataFrame(columns=columns)
        empty_df.to_parquet(test_results_path, index=False)
        print("   ✅ 创建了空的 Parquet 文件")
    
    # 6. 清理锁文件
    lock_file = Path(str(test_results_path) + '.lock')
    if lock_file.exists():
        lock_file.unlink()
        print("\n4. 清理了遗留的锁文件")
    
    print("\n" + "=" * 60)
    print("✅ Parquet 文件修复完成！")
    print("=" * 60)
    print("\n建议：")
    print("1. 文件锁机制已添加，避免并发写入损坏")
    print("2. 自动备份机制已启用")
    print("3. 如需恢复旧数据，查看 pilot_bench_parquet_data.backup.* 目录")
    
    return True

if __name__ == "__main__":
    success = fix_parquet_corruption()
    sys.exit(0 if success else 1)