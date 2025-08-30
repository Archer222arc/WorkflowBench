#!/usr/bin/env python3
"""验证Parquet模式是否完全准备就绪"""

import os
import subprocess
from pathlib import Path

print("=" * 60)
print("Parquet模式集成验证")
print("=" * 60)

# 1. 检查脚本修改
print("\n✅ 脚本修改检查:")
script_path = Path("run_systematic_test_final.sh")
if script_path.exists():
    content = script_path.read_text()
    
    checks = [
        ("export STORAGE_FORMAT", "环境变量导出"),
        ("mkdir -p pilot_bench_cumulative_results/parquet_data", "目录创建"),
        ('STORAGE_FORMAT="${STORAGE_FORMAT}" python', "环境变量传递"),
    ]
    
    for pattern, desc in checks:
        if pattern in content:
            print(f"  ✓ {desc}")
        else:
            print(f"  ✗ {desc}")

# 2. 测试环境变量传递
print("\n✅ 环境变量传递测试:")
os.environ['STORAGE_FORMAT'] = 'parquet'

# 测试Python脚本能否接收
test_code = """
import os
print(f"  Python进程收到: STORAGE_FORMAT={os.environ.get('STORAGE_FORMAT', 'None')}")
"""

result = subprocess.run(
    ["python3", "-c", test_code],
    env={**os.environ, 'STORAGE_FORMAT': 'parquet'},
    capture_output=True,
    text=True
)
print(result.stdout.strip())

# 3. 依赖检查
print("\n✅ 依赖检查:")
try:
    import pandas
    import pyarrow
    print("  ✓ pandas 和 pyarrow 已安装")
except ImportError as e:
    print(f"  ✗ 缺少依赖: {e}")

# 4. 目录准备状态
print("\n✅ 目录准备状态:")
dirs_to_check = [
    "pilot_bench_cumulative_results/parquet_data",
    "pilot_bench_parquet_data",
]

for dir_path in dirs_to_check:
    if Path(dir_path).exists():
        print(f"  ✓ {dir_path}")
    else:
        print(f"  ✗ {dir_path} (将在运行时创建)")

print("\n" + "=" * 60)
print("总结：")
print("  1. 运行 ./run_systematic_test_final.sh")
print("  2. 选择 2 (Parquet格式)")
print("  3. 系统会自动:")
print("     - 设置STORAGE_FORMAT=parquet")
print("     - 创建必要的目录")
print("     - 传递环境变量给Python脚本")
print("=" * 60)
