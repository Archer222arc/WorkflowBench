#!/usr/bin/env python3
"""诊断数据保存问题"""

import os
import json
from pathlib import Path
from datetime import datetime

print("=" * 60)
print("数据保存问题诊断")
print("=" * 60)

# 1. 环境变量
print("\n1. 环境变量:")
storage_format = os.environ.get('STORAGE_FORMAT', 'json')
print(f"   STORAGE_FORMAT = {storage_format}")

# 2. 检查运行的脚本是否收到环境变量
print("\n2. 运行中的脚本环境:")
import subprocess
result = subprocess.run(
    "ps aux | grep smart_batch_runner | grep -v grep | head -1",
    shell=True, capture_output=True, text=True
)
if result.stdout:
    # 检查命令行中是否有STORAGE_FORMAT
    if "STORAGE_FORMAT" in result.stdout:
        print("   ✅ 命令行包含STORAGE_FORMAT")
    else:
        print("   ❌ 命令行没有STORAGE_FORMAT")

# 3. 检查日志文件
print("\n3. 最新日志（检查存储格式）:")
log_dir = Path("logs")
if log_dir.exists():
    logs = list(log_dir.glob("batch_test_*.log"))
    if logs:
        latest_log = max(logs, key=lambda p: p.stat().st_mtime)
        
        # 读取最后100行
        with open(latest_log, 'r') as f:
            lines = f.readlines()
            
        # 查找存储格式相关日志
        storage_lines = [l for l in lines[-100:] if 'storage' in l.lower() or 'parquet' in l.lower() or 'json' in l.lower()]
        
        if storage_lines:
            print(f"   最新日志: {latest_log.name}")
            for line in storage_lines[:5]:
                print(f"   {line.strip()}")
        else:
            print(f"   日志中未找到存储格式信息")

# 4. 检查数据文件更新
print("\n4. 数据文件更新时间:")
files_to_check = [
    ("pilot_bench_cumulative_results/master_database.json", "JSON数据库"),
    ("pilot_bench_parquet_data/test_results.parquet", "Parquet主文件"),
    ("pilot_bench_parquet_data/incremental/*.parquet", "增量Parquet"),
]

now = datetime.now()
for file_path, desc in files_to_check:
    if "*" in file_path:
        from glob import glob
        files = glob(file_path)
        if files:
            latest = max(files, key=lambda f: Path(f).stat().st_mtime)
            mtime = datetime.fromtimestamp(Path(latest).stat().st_mtime)
            age = now - mtime
            print(f"   {desc}: {age.total_seconds()/60:.1f}分钟前")
    else:
        path = Path(file_path)
        if path.exists():
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
            age = now - mtime
            print(f"   {desc}: {age.total_seconds()/60:.1f}分钟前")

# 5. 检查smart_batch_runner的输出
print("\n5. 检查测试输出:")
# 查看一个运行中的日志
result = subprocess.run(
    "tail -100 logs/batch_test_*.log 2>/dev/null | grep -E '(成功|失败|完成|保存|checkpoint|finalize)' | tail -10",
    shell=True, capture_output=True, text=True
)
if result.stdout:
    print("   最近的测试输出:")
    for line in result.stdout.strip().split('\n'):
        print(f"   {line}")

print("\n" + "=" * 60)
print("诊断结果:")
print("=" * 60)

# 分析问题
problems = []

if storage_format != 'parquet':
    problems.append("❌ 环境变量未设置为parquet")

# 检查是否有新数据
parquet_path = Path("pilot_bench_parquet_data/incremental")
if parquet_path.exists():
    recent_files = list(parquet_path.glob("*.parquet"))
    if recent_files:
        latest = max(recent_files, key=lambda f: f.stat().st_mtime)
        age = (now - datetime.fromtimestamp(latest.stat().st_mtime)).total_seconds() / 60
        if age > 30:
            problems.append(f"⚠️ Parquet文件已{age:.0f}分钟未更新")
    else:
        problems.append("❌ 没有增量Parquet文件")

if problems:
    print("发现的问题:")
    for p in problems:
        print(f"  {p}")
else:
    print("  ✅ 配置看起来正常")

print("\n可能的原因:")
print("  1. ultra_parallel_runner没有正确传递环境变量给smart_batch_runner")
print("  2. 测试实际上还在运行中（工作流生成需要时间）")
print("  3. 数据会在测试完成后批量保存")
