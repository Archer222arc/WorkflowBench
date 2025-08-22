#!/usr/bin/env python3
"""
测试单个分片，诊断失败原因
"""

import subprocess
import os

# 设置环境变量
os.environ['STORAGE_FORMAT'] = 'parquet'

# 构建测试命令
cmd = [
    "python", "smart_batch_runner.py",
    "--model", "DeepSeek-V3-0324",
    "--prompt-types", "flawed_sequence_disorder",
    "--difficulty", "easy", 
    "--task-types", "simple_task",
    "--num-instances", "1",
    "--max-workers", "5",
    "--tool-success-rate", "0.8",
    "--no-adaptive",  # 固定速率
    "--qps", "10",
    "--no-save-logs"
]

print("执行命令:")
print(" ".join(cmd))
print("\n" + "="*50)

# 运行命令
result = subprocess.run(cmd, capture_output=True, text=True)

print(f"退出码: {result.returncode}")
print("\n标准输出:")
print(result.stdout)
print("\n错误输出:")
print(result.stderr)

if result.returncode != 0:
    print(f"\n❌ 测试失败，退出码: {result.returncode}")