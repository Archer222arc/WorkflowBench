#!/usr/bin/env python3
"""
合并Parquet增量数据到主文件
"""

import os
from pathlib import Path
from datetime import datetime
import pandas as pd

print("=" * 70)
print("              Parquet数据合并工具")
print("=" * 70)

# 设置路径
data_dir = Path("pilot_bench_parquet_data")
incremental_dir = data_dir / "incremental"
test_results_path = data_dir / "test_results.parquet"

# 1. 检查当前状态
print("\n📊 当前状态：")
incremental_files = list(incremental_dir.glob("increment_*.parquet"))
print(f"   增量文件数: {len(incremental_files)}")

if test_results_path.exists():
    main_df = pd.read_parquet(test_results_path)
    print(f"   主文件记录数: {len(main_df)}")
    if 'timestamp' in main_df.columns and len(main_df) > 0:
        last_update = main_df['timestamp'].max()
        print(f"   主文件最后更新: {last_update}")
else:
    print("   主文件不存在")
    main_df = pd.DataFrame()

# 2. 读取增量文件
if incremental_files:
    print(f"\n📂 读取 {len(incremental_files)} 个增量文件...")
    
    dfs = []
    total_new_records = 0
    
    for file in incremental_files:
        try:
            df = pd.read_parquet(file)
            dfs.append(df)
            total_new_records += len(df)
            print(f"   ✅ {file.name}: {len(df)} 条记录")
        except Exception as e:
            print(f"   ❌ 读取失败 {file.name}: {e}")
    
    if dfs:
        print(f"\n   总计: {total_new_records} 条新记录")
        
        # 3. 合并数据
        print("\n🔄 合并数据...")
        incremental_df = pd.concat(dfs, ignore_index=True)
        
        if not main_df.empty:
            combined_df = pd.concat([main_df, incremental_df], ignore_index=True)
            print(f"   合并前: {len(main_df)} + {len(incremental_df)} = {len(combined_df)} 条")
        else:
            combined_df = incremental_df
            print(f"   创建新主文件: {len(combined_df)} 条")
        
        # 去重（基于test_id）
        if 'test_id' in combined_df.columns:
            before_dedup = len(combined_df)
            combined_df = combined_df.drop_duplicates(subset=['test_id'], keep='last')
            after_dedup = len(combined_df)
            if before_dedup != after_dedup:
                print(f"   去重: {before_dedup} -> {after_dedup} 条")
        
        # 4. 备份主文件
        if test_results_path.exists():
            backup_path = test_results_path.with_suffix('.parquet.backup')
            print(f"\n💾 备份主文件到: {backup_path.name}")
            import shutil
            shutil.copy2(test_results_path, backup_path)
        
        # 5. 保存合并后的数据
        print(f"\n💾 保存合并后的数据...")
        combined_df.to_parquet(test_results_path, index=False)
        print(f"   ✅ 已保存 {len(combined_df)} 条记录到主文件")
        
        # 6. 清理增量文件
        print(f"\n🗑️ 清理增量文件...")
        cleaned = 0
        for file in incremental_files:
            try:
                file.unlink()
                cleaned += 1
            except Exception as e:
                print(f"   ⚠️ 无法删除 {file.name}: {e}")
        print(f"   ✅ 已清理 {cleaned}/{len(incremental_files)} 个文件")
        
        # 7. 验证结果
        print(f"\n✅ 合并完成！")
        final_df = pd.read_parquet(test_results_path)
        print(f"   最终记录数: {len(final_df)}")
        if 'timestamp' in final_df.columns and len(final_df) > 0:
            print(f"   最新记录时间: {final_df['timestamp'].max()}")
            
        # 显示一些统计
        if 'model' in final_df.columns:
            model_counts = final_df['model'].value_counts()
            print(f"\n   模型分布:")
            for model, count in model_counts.head(5).items():
                print(f"     - {model}: {count} 条")
    else:
        print("\n⚠️ 没有成功读取任何增量文件")
else:
    print("\n✅ 没有需要合并的增量文件")

print("\n" + "=" * 70)
print("提示：")
print("  - 合并操作会将所有增量文件的数据添加到主文件")
print("  - 主文件路径: pilot_bench_parquet_data/test_results.parquet")
print("  - 可以定期运行此脚本以保持主文件最新")
print("  - 也可以在 smart_batch_runner 中调用 finalize() 来触发合并")
print("=" * 70)