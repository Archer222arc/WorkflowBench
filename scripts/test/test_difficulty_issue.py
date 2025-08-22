#\!/usr/bin/env python3
"""测试难度参数问题"""

# 模拟测试三种难度
difficulties = ["very_easy", "easy", "medium"]

print("测试难度参数处理:")
print("="*50)

# 检查是否有难度标准化
for diff in difficulties:
    # 这是可能的问题：某处把所有难度都标准化为easy了
    normalized = diff
    
    # 检查是否有错误的标准化逻辑
    if "easy" in diff:
        normalized = "easy"  # 这可能是问题所在！
    
    print(f"{diff} -> {normalized}")

print("\n如果very_easy和medium都被转换为easy，就会导致数据合并")

# 检查实际的bash脚本调用
print("\n检查bash脚本调用:")
print("-"*50)

import subprocess
import re

# 查看最近的测试日志
result = subprocess.run(
    ["grep", "-h", "python smart_batch_runner", "logs/batch_test_20250812*.log"],
    capture_output=True,
    text=True,
    cwd="/Users/ruichengao/WorkflowBench/scale_up/scale_up"
)

if result.stdout:
    lines = result.stdout.strip().split('\n')[:5]  # 只看前5行
    for line in lines:
        # 提取difficulty参数
        match = re.search(r'--difficulty\s+(\S+)', line)
        if match:
            print(f"发现调用: --difficulty {match.group(1)}")
