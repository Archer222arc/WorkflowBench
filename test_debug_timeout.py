#!/usr/bin/env python3
"""
测试timeout_errors分类的调试版本
"""

import os
os.environ['STORAGE_FORMAT'] = 'parquet'

from cumulative_test_manager import TestRecord
from parquet_cumulative_manager import ParquetCumulativeManager

print("=" * 70)
print("测试timeout_errors分类（带调试）")
print("=" * 70)

# 创建管理器
manager = ParquetCumulativeManager()

# 创建测试记录
record = TestRecord(
    model='debug-timeout-test',
    task_type='test_task',
    prompt_type='optimal',
    difficulty='easy'
)

record.tool_success_rate = 0.8
record.success = False
record.execution_time = 600.0  # 超时
record.turns = 1
record.tool_calls = 0  # 没有工具调用
record.success_level = 'failure'
record.execution_status = 'failure'
record.error_message = "Test timeout after 10 minutes"

# 关键：动态添加AI分类字段
print("\n设置AI分类字段...")
setattr(record, 'ai_error_category', 'timeout_errors')
print(f"  ai_error_category = {getattr(record, 'ai_error_category')}")
print(f"  hasattr(record, 'ai_error_category') = {hasattr(record, 'ai_error_category')}")

# 添加到manager
print("\n添加记录到Parquet manager...")
success = manager.add_test_result_with_classification(record)
print(f"\n添加结果: {'成功' if success else '失败'}")

# 刷新
manager._flush_buffer()
print("\n数据已刷新")

print("\n" + "=" * 70)
print("测试完成")