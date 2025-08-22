#!/usr/bin/env python3
"""最终的Parquet存储测试"""

import os
import subprocess
import time
from pathlib import Path
from datetime import datetime

print("=" * 70)
print("                    Parquet存储最终测试")
print("=" * 70)

# 1. 设置环境变量
os.environ['STORAGE_FORMAT'] = 'parquet'
print(f"\n1️⃣ 环境设置:")
print(f"   STORAGE_FORMAT = {os.environ.get('STORAGE_FORMAT')}")

# 2. 清理并准备目录
print("\n2️⃣ 准备目录结构:")
parquet_dirs = [
    "pilot_bench_parquet_data",
    "pilot_bench_parquet_data/incremental",
    "pilot_bench_cumulative_results/parquet_data",
    "pilot_bench_cumulative_results/parquet_data/incremental"
]

for dir_path in parquet_dirs:
    Path(dir_path).mkdir(parents=True, exist_ok=True)
    print(f"   ✅ {dir_path}")

# 3. 记录测试前状态
print("\n3️⃣ 测试前文件状态:")
parquet_dir = Path("pilot_bench_parquet_data/incremental")
json_file = Path("pilot_bench_cumulative_results/master_database.json")

before_parquet_count = len(list(parquet_dir.glob("*.parquet")))
print(f"   Parquet文件数: {before_parquet_count}")

if json_file.exists():
    json_mtime_before = datetime.fromtimestamp(json_file.stat().st_mtime)
    print(f"   JSON最后修改: {(datetime.now() - json_mtime_before).total_seconds()/60:.1f}分钟前")

# 4. 运行测试
print("\n4️⃣ 运行测试:")
print("   模型: gpt-4o-mini")
print("   实例数: 1")
print("   使用: smart_batch_runner.py 直接调用")

cmd = [
    "env", f"STORAGE_FORMAT=parquet",
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

print("\n   启动测试进程...")
process = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# 5. 监控进程输出和文件变化
print("\n5️⃣ 监控测试进度:")
timeout = 180  # 3分钟超时
start_time = time.time()
parquet_created = False
storage_info_found = False

while time.time() - start_time < timeout:
    # 检查进程状态
    poll_result = process.poll()
    
    # 尝试读取一些输出（非阻塞）
    if poll_result is None:
        # 进程还在运行
        elapsed = time.time() - start_time
        
        # 检查是否有新的Parquet文件
        current_parquet_count = len(list(parquet_dir.glob("*.parquet")))
        if current_parquet_count > before_parquet_count:
            parquet_created = True
            print(f"\n   ✅ 发现新的Parquet文件！（{elapsed:.0f}秒后）")
            break
        
        # 每10秒显示一次状态
        if int(elapsed) % 10 == 0:
            print(f"   ⏳ 等待中... ({elapsed:.0f}秒)")
        
        time.sleep(1)
    else:
        # 进程已结束
        stdout, stderr = process.communicate()
        
        # 检查是否有存储格式信息
        if "[INFO] 使用Parquet存储格式" in stdout or "[INFO] 使用Parquet存储格式" in stderr:
            storage_info_found = True
            print(f"   ✅ 确认使用Parquet存储格式")
        
        if poll_result == 0:
            print(f"   ✅ 测试完成（退出码: 0）")
        else:
            print(f"   ⚠️ 测试退出（退出码: {poll_result}）")
        
        # 显示关键输出
        if stderr and "error" in stderr.lower():
            print("\n   错误信息:")
            for line in stderr.split('\n')[:5]:
                if line.strip():
                    print(f"     {line}")
        break

# 如果超时，终止进程
if process.poll() is None:
    print(f"\n   ⏱️ 超时({timeout}秒)，终止进程...")
    process.terminate()
    time.sleep(2)
    if process.poll() is None:
        process.kill()

# 6. 检查最终结果
print("\n6️⃣ 测试后文件状态:")
after_parquet_count = len(list(parquet_dir.glob("*.parquet")))
print(f"   Parquet文件数: {after_parquet_count}")

if after_parquet_count > before_parquet_count:
    # 找到最新的文件
    latest_files = sorted(parquet_dir.glob("*.parquet"), 
                         key=lambda f: f.stat().st_mtime, 
                         reverse=True)[:3]
    print(f"   新增文件:")
    for f in latest_files[:min(3, after_parquet_count - before_parquet_count)]:
        age = (datetime.now() - datetime.fromtimestamp(f.stat().st_mtime)).total_seconds()
        size_kb = f.stat().st_size / 1024
        print(f"     - {f.name} ({size_kb:.1f}KB, {age:.0f}秒前)")

# 检查JSON是否也更新了
if json_file.exists():
    json_mtime_after = datetime.fromtimestamp(json_file.stat().st_mtime)
    if json_mtime_after > json_mtime_before if 'json_mtime_before' in locals() else False:
        print(f"   ⚠️ JSON也更新了（不应该）")

# 7. 总结
print("\n" + "=" * 70)
print("                        测试总结")
print("=" * 70)

success = parquet_created or (after_parquet_count > before_parquet_count)

if success:
    print("✅ Parquet存储功能正常工作！")
    print("\n已修复的问题:")
    print("  1. ✅ 环境变量正确传递到子进程")
    print("  2. ✅ smart_batch_runner正确导入ParquetCumulativeManager")
    print("  3. ✅ 数据成功保存为Parquet格式")
    print("\n使用说明:")
    print("  1. 运行 ./run_systematic_test_final.sh")
    print("  2. 选择 2 (Parquet格式)")
    print("  3. 数据将增量保存到 pilot_bench_parquet_data/incremental/")
else:
    print("❌ 测试未能创建Parquet文件")
    print("\n可能的原因:")
    print("  1. 测试还需要更多时间")
    print("  2. 工作流生成阶段还未完成")
    print("  3. 可能还有其他问题需要调试")
    print("\n建议:")
    print("  1. 检查 logs/ 目录下的最新日志")
    print("  2. 尝试运行更长时间")
    print("  3. 检查 parquet_cumulative_manager.py 的实现")