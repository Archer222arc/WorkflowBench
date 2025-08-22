#!/usr/bin/env python3
"""测试自动合并功能"""

import os
import subprocess
from pathlib import Path
import time

print("=" * 70)
print("          测试Parquet自动合并功能")
print("=" * 70)

# 设置环境变量
os.environ['STORAGE_FORMAT'] = 'parquet'

# 记录初始状态
data_dir = Path("pilot_bench_parquet_data")
incremental_dir = data_dir / "incremental"
main_file = data_dir / "test_results.parquet"

print("\n📊 初始状态:")
before_incremental = len(list(incremental_dir.glob("*.parquet")))
before_main_time = main_file.stat().st_mtime if main_file.exists() else 0
print(f"   增量文件数: {before_incremental}")

# 运行测试（会在结束时调用_flush_buffer）
print("\n🚀 运行测试（将触发自动合并）...")
cmd = [
    "env", "STORAGE_FORMAT=parquet",
    "python", "smart_batch_runner.py",
    "--model", "gpt-4o-mini",
    "--prompt-types", "baseline",
    "--difficulty", "easy",
    "--task-types", "simple_task",
    "--num-instances", "1",
    "--tool-success-rate", "0.8",
    "--max-workers", "5",
    "--no-adaptive",
    "--qps", "5",
    "--silent",
    "--no-save-logs"
]

result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)

# 查找关键输出
if "Parquet增量数据已合并到主文件" in result.stdout or "Parquet增量数据已合并到主文件" in result.stderr:
    print("   ✅ 检测到自动合并消息")
else:
    print("   ⚠️ 未检测到自动合并消息")

# 检查结果
print("\n📊 测试后状态:")
after_incremental = len(list(incremental_dir.glob("*.parquet")))
after_main_time = main_file.stat().st_mtime if main_file.exists() else 0
print(f"   增量文件数: {after_incremental}")

# 分析结果
print("\n🔍 分析:")
if after_main_time > before_main_time:
    print("   ✅ 主文件已更新（自动合并成功）")
    
    # 检查增量文件是否被清理
    if after_incremental < before_incremental:
        print(f"   ✅ 增量文件已清理（{before_incremental} -> {after_incremental}）")
    elif after_incremental == before_incremental + 1:
        print("   ℹ️ 新增了一个增量文件（测试本身产生）")
        print("   ℹ️ 可能需要再次运行以触发合并")
    else:
        print(f"   ⚠️ 增量文件数变化异常（{before_incremental} -> {after_incremental}）")
else:
    print("   ❌ 主文件未更新")
    
    if after_incremental > before_incremental:
        print(f"   ℹ️ 新增了{after_incremental - before_incremental}个增量文件")
        print("   ℹ️ 数据已保存到增量文件，但未触发自动合并")
        print("   ℹ️ 可能是因为增量文件数量未达到合并阈值")

print("\n" + "=" * 70)
print("结论:")
if after_main_time > before_main_time:
    print("✅ 自动合并功能正常工作！")
    print("   smart_batch_runner会在批次结束时调用_flush_buffer()")
    print("   _flush_buffer()会触发consolidate_incremental_data()")
else:
    print("ℹ️ 本次测试未触发自动合并")
    print("   可能原因：")
    print("   1. 只有一个新文件，未达到合并阈值")
    print("   2. 可以手动运行 python consolidate_parquet.py 来合并")
print("=" * 70)