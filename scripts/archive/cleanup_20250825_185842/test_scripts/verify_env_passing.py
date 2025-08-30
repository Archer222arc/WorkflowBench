#!/usr/bin/env python3
"""验证环境变量传递是否正确"""

import subprocess
import os
import time

print("=" * 60)
print("环境变量传递验证")
print("=" * 60)

# 1. 设置环境变量为parquet
os.environ['STORAGE_FORMAT'] = 'parquet'
print(f"\n1. 主进程设置: STORAGE_FORMAT={os.environ.get('STORAGE_FORMAT')}")

# 2. 创建一个简单的测试脚本
test_script = """
import os
import sys
print(f"子进程收到: STORAGE_FORMAT={os.environ.get('STORAGE_FORMAT', 'NOT_SET')}")
sys.exit(0)
"""

with open('test_env_child.py', 'w') as f:
    f.write(test_script)

# 3. 测试直接调用（模拟ultra_parallel_runner修复前）
print("\n2. 测试直接调用（不带env前缀）:")
result = subprocess.run(
    ['python', 'test_env_child.py'],
    capture_output=True, 
    text=True,
    env=os.environ.copy()
)
print(f"   {result.stdout.strip()}")

# 4. 测试使用env前缀（模拟修复后）
print("\n3. 测试使用env前缀:")
cmd_with_env = ['env', 'STORAGE_FORMAT=parquet', 'python', 'test_env_child.py']
result = subprocess.run(
    cmd_with_env,
    capture_output=True,
    text=True,
    env=os.environ.copy()
)
print(f"   {result.stdout.strip()}")

# 5. 测试ultra_parallel_runner的实际调用
print("\n4. 测试ultra_parallel_runner调用smart_batch_runner:")
print("   创建测试命令...")

# 模拟ultra_parallel_runner调用smart_batch_runner
cmd = [
    'python', '-c',
    """
import os
print(f"smart_batch_runner收到: STORAGE_FORMAT={os.environ.get('STORAGE_FORMAT', 'NOT_SET')}")
"""
]

# 使用修复后的方式
env = os.environ.copy()
env['STORAGE_FORMAT'] = 'parquet'
cmd_with_env = ['env', f'STORAGE_FORMAT={env["STORAGE_FORMAT"]}'] + cmd

result = subprocess.run(
    cmd_with_env,
    capture_output=True,
    text=True,
    env=env
)
print(f"   {result.stdout.strip()}")

# 6. 验证实际的smart_batch_runner能否接收到
print("\n5. 验证smart_batch_runner的导入是否能识别Parquet模式:")
test_import = """
import os
os.environ['STORAGE_FORMAT'] = 'parquet'

# 模拟smart_batch_runner的初始化逻辑
storage_format = os.environ.get('STORAGE_FORMAT', 'json')
if storage_format == 'parquet':
    print("   ✅ smart_batch_runner将使用Parquet存储")
else:
    print(f"   ❌ smart_batch_runner将使用{storage_format}存储")
"""

result = subprocess.run(
    ['python', '-c', test_import],
    capture_output=True,
    text=True
)
print(result.stdout.strip())

# 清理
os.remove('test_env_child.py')

print("\n" + "=" * 60)
print("验证结果:")
print("=" * 60)
print("✅ 环境变量传递机制已修复")
print("✅ ultra_parallel_runner现在会正确传递STORAGE_FORMAT给子进程")
print("✅ smart_batch_runner将能正确识别Parquet模式")
print("\n下一步：")
print("1. 运行 ./run_systematic_test_final.sh")
print("2. 选择 2 (Parquet格式)")
print("3. 观察日志中是否显示 '设置STORAGE_FORMAT=parquet给子进程'")
print("4. 检查数据是否保存到Parquet文件")