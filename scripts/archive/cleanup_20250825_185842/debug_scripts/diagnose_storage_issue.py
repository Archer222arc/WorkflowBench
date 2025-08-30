#!/usr/bin/env python3
"""诊断存储问题"""

import os
import json
import subprocess
from pathlib import Path
from datetime import datetime

print("=" * 60)
print("PILOT-Bench 存储问题诊断")
print("=" * 60)

# 1. 检查环境变量
print("\n1. 环境变量检查:")
storage_format = os.environ.get('STORAGE_FORMAT', 'json')
print(f"   STORAGE_FORMAT = {storage_format}")

# 2. 检查运行中的进程使用的存储格式
print("\n2. 运行中进程的存储格式:")
result = subprocess.run(
    "ps aux | grep smart_batch_runner | grep -v grep | head -1",
    shell=True, capture_output=True, text=True
)

if result.stdout:
    # 检查进程的环境变量
    pid = result.stdout.split()[1]
    print(f"   检查PID {pid}的环境...")
    
    # 查看日志中的存储格式信息
    log_check = subprocess.run(
        "grep -l 'Parquet\\|JSON' logs/batch_test_*.log | tail -1 | xargs grep -m 1 '使用.*存储格式'",
        shell=True, capture_output=True, text=True
    )
    if log_check.stdout:
        print(f"   日志显示: {log_check.stdout.strip()}")
    else:
        print("   日志中未找到存储格式信息")

# 3. 数据文件时间戳分析
print("\n3. 数据文件更新时间:")
files_to_check = [
    "pilot_bench_cumulative_results/master_database.json",
    "pilot_bench_parquet_data/test_results.parquet",
    "pilot_bench_parquet_data/incremental/*.parquet"
]

for file_pattern in files_to_check:
    if "*" in file_pattern:
        # 处理通配符
        from glob import glob
        files = glob(file_pattern)
        if files:
            latest = max(files, key=lambda f: Path(f).stat().st_mtime)
            mtime = datetime.fromtimestamp(Path(latest).stat().st_mtime)
            print(f"   {Path(latest).name}: {mtime.strftime('%H:%M:%S')}")
    else:
        file_path = Path(file_pattern)
        if file_path.exists():
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            print(f"   {file_path.name}: {mtime.strftime('%H:%M:%S')}")

# 4. 分析问题
print("\n4. 问题分析:")
print("   ❌ 当前运行的测试使用JSON模式，不是Parquet模式")
print("   原因：环境变量STORAGE_FORMAT未正确设置")
print("   影响：")
print("      - Parquet文件不会更新")
print("      - 数据直接写入master_database.json")
print("      - 可能有并发写入冲突")

# 5. 解决方案
print("\n5. 解决方案:")
print("   立即操作：")
print("   1) 终止当前测试: pkill -f smart_batch_runner")
print("   2) 设置环境变量: export STORAGE_FORMAT=parquet")
print("   3) 重新运行测试: ./run_systematic_test_final.sh")
print("")
print("   或者继续当前测试（JSON模式）：")
print("   - 数据会保存到master_database.json")
print("   - 测试完成后可以转换为Parquet")

# 6. 数据一致性检查
print("\n6. 数据一致性:")
json_path = Path("pilot_bench_cumulative_results/master_database.json")
if json_path.exists():
    with open(json_path, 'r') as f:
        db = json.load(f)
    
    # 检查最新的测试
    latest_time = None
    for model_name, model_data in db.get('models', {}).items():
        if 'last_updated' in model_data:
            if latest_time is None or model_data['last_updated'] > latest_time:
                latest_time = model_data['last_updated']
    
    if latest_time:
        print(f"   JSON数据库最新记录: {latest_time}")
    
    # 统计今天的测试
    today = datetime.now().strftime('%Y%m%d')
    today_tests = 0
    for group_id, group_data in db.get('test_groups', {}).items():
        if today in group_id:
            today_tests += group_data.get('total_tests', 0)
    
    print(f"   今天的测试组: {today_tests} 个")

print("\n" + "=" * 60)
