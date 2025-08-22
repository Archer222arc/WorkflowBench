#!/usr/bin/env python3
"""测试Parquet修复是否生效"""

import os
import subprocess
import time
from pathlib import Path
from datetime import datetime

print("=" * 60)
print("测试Parquet存储修复")
print("=" * 60)

# 设置环境变量
os.environ['STORAGE_FORMAT'] = 'parquet'
print(f"\n✅ 设置环境变量: STORAGE_FORMAT=parquet")

# 记录测试前的文件状态
parquet_dir = Path("pilot_bench_parquet_data/incremental")
json_file = Path("pilot_bench_cumulative_results/master_database.json")

print("\n📊 测试前文件状态:")
if parquet_dir.exists():
    parquet_files = list(parquet_dir.glob("*.parquet"))
    if parquet_files:
        latest = max(parquet_files, key=lambda f: f.stat().st_mtime)
        mtime = datetime.fromtimestamp(latest.stat().st_mtime)
        print(f"   最新Parquet: {latest.name} ({(datetime.now() - mtime).total_seconds()/60:.1f}分钟前)")
    else:
        print("   无Parquet文件")
else:
    print("   Parquet目录不存在")

if json_file.exists():
    mtime = datetime.fromtimestamp(json_file.stat().st_mtime)
    print(f"   JSON数据库: {(datetime.now() - mtime).total_seconds()/60:.1f}分钟前")

# 运行一个小测试
print("\n🚀 运行测试 (gpt-4o-mini, 1个实例)...")
print("   使用ultra_parallel_runner...")

cmd = [
    "python", "ultra_parallel_runner.py",
    "--model", "gpt-4o-mini",
    "--prompt-types", "baseline",
    "--difficulty", "easy",
    "--task-types", "simple_task",
    "--num-instances", "1",
    "--rate-mode", "fixed",
    "--silent",
    "--tool-success-rate", "0.8"
]

# 使用timeout避免长时间等待
print("   执行命令...")
process = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    env=os.environ.copy()
)

# 等待一段时间观察输出
timeout = 120  # 2分钟超时
start_time = time.time()
output_lines = []
error_lines = []

print(f"   等待测试运行（最多{timeout}秒）...")

while time.time() - start_time < timeout:
    # 检查进程是否结束
    poll_result = process.poll()
    if poll_result is not None:
        # 进程已结束，读取所有输出
        stdout, stderr = process.communicate()
        if stdout:
            output_lines.extend(stdout.strip().split('\n'))
        if stderr:
            error_lines.extend(stderr.strip().split('\n'))
        break
    
    # 还在运行，等待
    time.sleep(5)
    elapsed = time.time() - start_time
    print(f"   运行中... ({elapsed:.0f}秒)")
    
    # 检查是否有新的Parquet文件
    if parquet_dir.exists():
        new_files = list(parquet_dir.glob("*.parquet"))
        if len(new_files) > len(parquet_files) if 'parquet_files' in locals() else 0:
            print(f"   ✅ 发现新的Parquet文件！")
            break

# 如果还在运行，终止进程
if process.poll() is None:
    print("   超时，终止进程...")
    process.terminate()
    time.sleep(2)
    if process.poll() is None:
        process.kill()
    stdout, stderr = process.communicate()

# 显示关键输出
print("\n📝 关键输出:")
if error_lines:
    # 查找STORAGE_FORMAT相关的日志
    for line in error_lines:
        if "STORAGE_FORMAT" in line or "parquet" in line.lower():
            print(f"   {line}")

# 检查测试后的文件状态
print("\n📊 测试后文件状态:")
if parquet_dir.exists():
    new_parquet_files = list(parquet_dir.glob("*.parquet"))
    if new_parquet_files:
        latest = max(new_parquet_files, key=lambda f: f.stat().st_mtime)
        mtime = datetime.fromtimestamp(latest.stat().st_mtime)
        age = (datetime.now() - mtime).total_seconds()
        if age < 180:  # 3分钟内
            print(f"   ✅ 新Parquet文件: {latest.name} ({age:.0f}秒前)")
        else:
            print(f"   ⚠️ 最新Parquet: {latest.name} ({age/60:.1f}分钟前)")
    else:
        print("   ❌ 仍无Parquet文件")

if json_file.exists():
    mtime = datetime.fromtimestamp(json_file.stat().st_mtime)
    age = (datetime.now() - mtime).total_seconds()
    if age < 180:
        print(f"   ⚠️ JSON也更新了: ({age:.0f}秒前) - 可能仍在JSON模式")

print("\n" + "=" * 60)
print("测试结果:")
print("=" * 60)

# 判断是否成功
success = False
if parquet_dir.exists():
    new_files = list(parquet_dir.glob("*.parquet"))
    for f in new_files:
        age = (datetime.now() - datetime.fromtimestamp(f.stat().st_mtime)).total_seconds()
        if age < 180:  # 3分钟内的文件
            success = True
            break

if success:
    print("✅ Parquet存储修复成功！")
    print("   - 环境变量正确传递")
    print("   - 数据成功保存到Parquet格式")
else:
    print("⚠️ 可能需要更多时间或进一步调试")
    print("   建议：")
    print("   1. 检查logs/目录下的最新日志")
    print("   2. 确认测试实际运行了")
    print("   3. 可能需要等待更长时间（工作流生成需要时间）")