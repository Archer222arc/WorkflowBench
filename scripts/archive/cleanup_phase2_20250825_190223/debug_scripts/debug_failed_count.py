#!/usr/bin/env python3
"""调试failed计数问题"""

import os
os.environ['STORAGE_FORMAT'] = 'parquet'

from parquet_cumulative_manager import ParquetCumulativeManager
from cumulative_test_manager import TestRecord

# 创建管理器
manager = ParquetCumulativeManager()

# 创建失败的记录
record = TestRecord(
    model='test-failed',
    task_type='simple_task',
    prompt_type='baseline',
    difficulty='easy'
)
record.tool_success_rate = 0.8
record.success = False
record.partial_success = False
record.execution_time = 10.0
record.turns = 10
record.tool_calls = 1
record.error_message = "Test failed"

print(f"Record success: {record.success}")
print(f"Record partial_success: {getattr(record, 'partial_success', 'NOT SET')}")

# 添加记录
success = manager.add_test_result_with_classification(record)
print(f"Add result: {success}")

# 检查缓存
if hasattr(manager, '_summary_cache'):
    for key, summary in manager._summary_cache.items():
        print(f"\nCache key: {key}")
        print(f"  total: {summary.get('total', 0)}")
        print(f"  success: {summary.get('success', 0)}")
        print(f"  failed: {summary.get('failed', 0)}")
        print(f"  partial: {summary.get('partial', 0)}")

# 刷新
manager._flush_buffer()

# 查询结果
from parquet_data_manager import ParquetDataManager
pdm = ParquetDataManager()
df = pdm.query_model_stats(model_name='test-failed')

if not df.empty:
    latest = df.iloc[-1]
    print(f"\nFinal result:")
    print(f"  total: {latest.get('total', 0)}")
    print(f"  success: {latest.get('success', 0)}")
    print(f"  failed: {latest.get('failed', 0)}")
    print(f"  partial: {latest.get('partial', 0)}")