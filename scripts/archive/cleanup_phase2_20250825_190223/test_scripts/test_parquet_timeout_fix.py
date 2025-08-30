#!/usr/bin/env python3
"""
直接测试Parquet manager的timeout_errors修复
"""

import os
os.environ['STORAGE_FORMAT'] = 'parquet'

from cumulative_test_manager import TestRecord
from parquet_cumulative_manager import ParquetCumulativeManager

print("=" * 70)
print("测试Parquet Manager的timeout_errors分类修复")
print("=" * 70)

# 直接测试_update_summary方法
manager = ParquetCumulativeManager()

# 创建一个测试记录
record = TestRecord(
    model='test-timeout',
    task_type='api_integration',
    prompt_type='optimal',
    difficulty='easy'
)

record.tool_success_rate = 0.8
record.success = False
record.execution_time = 120.0
record.turns = 1
record.tool_calls = 0  # 没有工具调用
record.success_level = 'failure'
record.execution_status = 'failure'
record.error_message = "Test timeout after 10 minutes"

# 关键：添加AI分类
setattr(record, 'ai_error_category', 'timeout_errors')

# 创建一个空的summary
summary = {
    'total': 0,
    'success': 0,
    'full_success': 0,
    'partial_success': 0,
    'partial': 0,
    'failed': 0,
    'total_errors': 0,
    'tool_call_format_errors': 0,
    'timeout_errors': 0,
    'dependency_errors': 0,
    'parameter_config_errors': 0,
    'tool_selection_errors': 0,
    'sequence_order_errors': 0,
    'max_turns_errors': 0,
    'other_errors': 0,
    'assisted_failure': 0,
    'assisted_success': 0,
    'total_assisted_turns': 0,
    'tests_with_assistance': 0,
}

print("\n测试场景:")
print(f"  工具调用数: {record.tool_calls} (0表示没有工具调用)")
print(f"  成功级别: {record.success_level}")
print(f"  AI分类: {getattr(record, 'ai_error_category', 'N/A')}")

# 调用_update_summary
manager._update_summary(summary, record)

print("\n更新后的统计:")
print(f"  total_errors: {summary['total_errors']}")
print(f"  timeout_errors: {summary['timeout_errors']}")
print(f"  tool_call_format_errors: {summary['tool_call_format_errors']}")
print(f"  other_errors: {summary['other_errors']}")

if summary['timeout_errors'] > 0:
    print("\n✅ 成功: timeout_errors被正确分类!")
    print("   修复生效：AI分类优先于默认format分类")
elif summary['tool_call_format_errors'] > 0:
    print("\n❌ 失败: timeout_errors被错误分类为format错误")
    print("   问题：没有工具调用时的默认分类覆盖了AI分类")
elif summary['other_errors'] > 0:
    print("\n❌ 失败: timeout_errors被分类为other_errors")
else:
    print("\n❌ 失败: 没有错误被记录")

print("\n" + "=" * 70)
print("测试完成")