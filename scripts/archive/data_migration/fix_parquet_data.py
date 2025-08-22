#!/usr/bin/env python3
"""
修复Parquet数据中的字段混乱问题
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import shutil

print("=" * 70)
print("           修复Parquet数据字段问题")
print("=" * 70)

# 路径设置
parquet_file = Path("pilot_bench_parquet_data/test_results.parquet")
backup_file = parquet_file.with_suffix('.parquet.backup_before_fix')

if not parquet_file.exists():
    print("❌ Parquet文件不存在")
    exit(1)

# 1. 备份原文件
print("\n1️⃣ 备份原文件...")
shutil.copy2(parquet_file, backup_file)
print(f"   ✅ 备份到: {backup_file.name}")

# 2. 读取数据
print("\n2️⃣ 读取并分析数据...")
df = pd.read_parquet(parquet_file)
print(f"   总记录数: {len(df)}")

# 识别真实的测试记录字段（单个测试）
test_record_fields = [
    'model', 'task_type', 'prompt_type', 'difficulty', 'tool_success_rate',
    'success', 'partial_success', 'execution_time', 'error_message', 'turns',
    'tool_calls', 'timestamp', 'test_id', 'is_flawed', 'flaw_type',
    'workflow_score', 'phase2_score', 'required_tools', 'executed_tools',
    'execution_history', 'tool_coverage_rate'  # 这个可能是单个测试的
]

# 识别汇总统计字段（不应该在单个测试记录中）
summary_fields = [
    'total', 'successful', 'partial', 'failed',
    'success_rate', 'partial_rate', 'failure_rate',
    'weighted_success_score', 'avg_execution_time', 'avg_turns', 'avg_tool_calls'
]

# 3. 分离真实测试记录和错误导入的记录
print("\n3️⃣ 分离数据...")

# 检查是否有source字段
if 'source' in df.columns:
    # 从master_database.json导入的记录（错误的）
    imported_records = df[df['source'] == 'master_database.json']
    print(f"   发现 {len(imported_records)} 条从JSON导入的记录（将删除）")
    
    # 真实的测试记录
    real_records = df[df['source'] != 'master_database.json']
    print(f"   发现 {len(real_records)} 条真实测试记录")
else:
    # 没有source字段，通过其他方式识别
    # 真实测试记录不应该有'total'字段
    if 'total' in df.columns:
        real_records = df[df['total'].isna()]
        imported_records = df[df['total'].notna()]
        print(f"   识别出 {len(imported_records)} 条疑似汇总记录（有total字段）")
        print(f"   识别出 {len(real_records)} 条疑似真实记录（无total字段）")
    else:
        real_records = df
        imported_records = pd.DataFrame()
        print(f"   所有 {len(real_records)} 条记录看起来都是真实的")

# 4. 清理真实记录中的汇总字段
print("\n4️⃣ 清理字段...")
if len(real_records) > 0:
    # 只保留真实测试记录应有的字段
    available_fields = [f for f in test_record_fields if f in real_records.columns]
    cleaned_df = real_records[available_fields].copy()
    
    # 修复数据类型
    if 'success' in cleaned_df.columns:
        cleaned_df['success'] = cleaned_df['success'].astype(bool)
    if 'partial_success' in cleaned_df.columns:
        cleaned_df['partial_success'] = cleaned_df['partial_success'].fillna(False).astype(bool)
    if 'turns' in cleaned_df.columns:
        cleaned_df['turns'] = pd.to_numeric(cleaned_df['turns'], errors='coerce')
    if 'tool_calls' in cleaned_df.columns:
        cleaned_df['tool_calls'] = pd.to_numeric(cleaned_df['tool_calls'], errors='coerce')
    
    print(f"   ✅ 保留 {len(available_fields)} 个字段")
    print(f"   字段列表: {', '.join(available_fields[:10])}...")
else:
    cleaned_df = pd.DataFrame()
    print("   ⚠️ 没有真实记录可清理")

# 5. 显示清理结果
print("\n5️⃣ 清理结果:")
print(f"   原始记录数: {len(df)}")
print(f"   清理后记录数: {len(cleaned_df)}")
print(f"   删除的错误记录: {len(df) - len(cleaned_df)}")

if len(cleaned_df) > 0:
    # 6. 保存清理后的数据
    print("\n6️⃣ 保存清理后的数据...")
    cleaned_df.to_parquet(parquet_file, index=False)
    print(f"   ✅ 已保存到: {parquet_file}")
    
    # 7. 验证
    print("\n7️⃣ 验证修复结果:")
    verify_df = pd.read_parquet(parquet_file)
    print(f"   记录数: {len(verify_df)}")
    print(f"   列数: {len(verify_df.columns)}")
    
    # 检查是否还有汇总字段
    remaining_summary_fields = [f for f in summary_fields if f in verify_df.columns]
    if remaining_summary_fields:
        print(f"   ⚠️ 仍有汇总字段: {remaining_summary_fields}")
    else:
        print(f"   ✅ 已清除所有汇总字段")
    
    # 显示示例记录
    if len(verify_df) > 0:
        print("\n   示例记录:")
        sample = verify_df.iloc[0]
        for key in ['model', 'task_type', 'success', 'execution_time', 'turns']:
            if key in sample:
                print(f"     {key}: {sample[key]}")
else:
    print("\n⚠️ 没有数据可保存")
    print("   建议：")
    print("   1. 删除当前的test_results.parquet")
    print("   2. 重新运行测试生成干净的数据")

print("\n" + "=" * 70)
print("修复完成！")
print("备份文件: " + str(backup_file))
print("=" * 70)