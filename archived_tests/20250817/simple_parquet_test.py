#!/usr/bin/env python3
"""简单的Parquet测试，跟踪每一步"""

import os
import sys
from pathlib import Path

# 确保环境变量设置
os.environ['STORAGE_FORMAT'] = 'parquet'
print(f"✅ 设置STORAGE_FORMAT=parquet")

# 模拟smart_batch_runner的导入逻辑
storage_format = os.environ.get('STORAGE_FORMAT', 'json').lower()
print(f"storage_format = '{storage_format}'")

if storage_format == 'parquet':
    print("进入parquet分支...")
    try:
        from parquet_cumulative_manager import ParquetCumulativeManager as EnhancedCumulativeManager
        print(f"✅ 成功导入ParquetCumulativeManager")
        manager_type = "Parquet"
    except ImportError as e:
        print(f"❌ Parquet导入失败: {e}")
        from enhanced_cumulative_manager import EnhancedCumulativeManager
        print(f"回退到JSON存储格式")
        manager_type = "JSON"
else:
    from enhanced_cumulative_manager import EnhancedCumulativeManager
    print(f"使用JSON存储格式")
    manager_type = "JSON"

# 创建manager实例
print(f"\n创建{manager_type} manager实例...")
manager = EnhancedCumulativeManager()
print(f"✅ 成功创建manager: {type(manager).__name__}")

# 检查manager类型
if hasattr(manager, 'manager') and hasattr(manager.manager, 'data_dir'):
    print(f"数据目录: {manager.manager.data_dir}")
    print(f"增量目录: {manager.manager.incremental_dir}")

# 创建测试记录
from cumulative_test_manager import TestRecord
record = TestRecord(
    model='test-simple',
    task_type='simple_task',
    prompt_type='baseline'
)
record.success = True
record.execution_time = 1.0

# 记录前状态
parquet_dir = Path("pilot_bench_parquet_data/incremental")
json_file = Path("pilot_bench_cumulative_results/master_database.json")

before_parquet = len(list(parquet_dir.glob("*.parquet"))) if parquet_dir.exists() else 0
before_json_time = json_file.stat().st_mtime if json_file.exists() else 0

print(f"\n测试前:")
print(f"  Parquet文件数: {before_parquet}")

# 调用add_test_result_with_classification
print(f"\n调用add_test_result_with_classification...")
try:
    result = manager.add_test_result_with_classification(record)
    print(f"✅ 返回: {result}")
except Exception as e:
    print(f"❌ 调用失败: {e}")
    import traceback
    traceback.print_exc()

# 检查后状态
after_parquet = len(list(parquet_dir.glob("*.parquet"))) if parquet_dir.exists() else 0
after_json_time = json_file.stat().st_mtime if json_file.exists() else 0

print(f"\n测试后:")
print(f"  Parquet文件数: {after_parquet}")
if after_parquet > before_parquet:
    print(f"  ✅ 创建了{after_parquet - before_parquet}个新Parquet文件")
else:
    print(f"  ❌ 没有创建新Parquet文件")

if after_json_time > before_json_time:
    print(f"  ⚠️ JSON文件被更新了（不应该）")

print(f"\n结论:")
if manager_type == "Parquet" and after_parquet > before_parquet:
    print("✅ Parquet存储正常工作！")
elif manager_type == "JSON" and after_json_time > before_json_time:
    print("⚠️ 使用了JSON存储（环境变量未生效）")
else:
    print("❌ 数据没有被保存")