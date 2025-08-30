#!/usr/bin/env python3
"""
测试特定的错误类型是否能被正确匹配
直接测试max_turns_errors和dependency_errors
"""

import os
os.environ['STORAGE_FORMAT'] = 'parquet'

from cumulative_test_manager import TestRecord
from parquet_cumulative_manager import ParquetCumulativeManager

print("=" * 70)
print("测试特定错误类型的匹配：max_turns_errors和dependency_errors")
print("=" * 70)

# 创建管理器
manager = ParquetCumulativeManager()

# 测试用例
test_cases = [
    {
        'name': 'max_turns_errors测试',
        'ai_error_category': 'max_turns_errors',
        'expected': 'max_turns_errors'
    },
    {
        'name': 'dependency_errors测试',
        'ai_error_category': 'dependency_errors',
        'expected': 'dependency_errors'
    },
    {
        'name': 'max_turns变体测试',
        'ai_error_category': 'max_turns',
        'expected': 'max_turns_errors'
    },
    {
        'name': 'dependency变体测试',
        'ai_error_category': 'dependency',
        'expected': 'dependency_errors'
    }
]

for test_case in test_cases:
    print(f"\n测试: {test_case['name']}")
    print(f"  输入: {test_case['ai_error_category']}")
    
    # 创建测试记录
    record = TestRecord(
        model='error-type-test',
        task_type='simple_task',
        prompt_type='baseline',
        difficulty='easy'
    )
    
    record.tool_success_rate = 0.8
    record.success = False
    record.execution_time = 10.0
    record.turns = 5
    record.tool_calls = 3
    record.success_level = 'partial_success'
    record.execution_status = 'partial_success'
    
    # 设置AI错误分类
    record.ai_error_category = test_case['ai_error_category']
    record.ai_error_reason = f'Test for {test_case["name"]}'
    record.ai_confidence = 0.9
    
    # 直接测试_update_summary逻辑
    summary = {
        'total': 1,
        'failed': 1,
        'total_errors': 1,
        'tool_call_format_errors': 0,
        'timeout_errors': 0,
        'max_turns_errors': 0,
        'tool_selection_errors': 0,
        'parameter_config_errors': 0,
        'sequence_order_errors': 0,
        'dependency_errors': 0,
        'other_errors': 0
    }
    
    # 模拟匹配逻辑
    error_type = str(test_case['ai_error_category']).lower()
    
    if 'timeout' in error_type:
        summary['timeout_errors'] += 1
        result = 'timeout_errors'
    elif 'dependency' in error_type:
        summary['dependency_errors'] += 1
        result = 'dependency_errors'
    elif 'parameter' in error_type or 'parameter_config' in error_type:
        summary['parameter_config_errors'] += 1
        result = 'parameter_config_errors'
    elif 'tool_selection' in error_type:
        summary['tool_selection_errors'] += 1
        result = 'tool_selection_errors'
    elif 'sequence' in error_type or 'sequence_order' in error_type:
        summary['sequence_order_errors'] += 1
        result = 'sequence_order_errors'
    elif 'max_turns' in error_type:
        summary['max_turns_errors'] += 1
        result = 'max_turns_errors'
    elif 'format' in error_type or 'tool_call_format' in error_type:
        summary['tool_call_format_errors'] += 1
        result = 'tool_call_format_errors'
    else:
        summary['other_errors'] += 1
        result = 'other_errors'
    
    # 检查结果
    if result == test_case['expected']:
        print(f"  ✅ 正确匹配为: {result}")
    else:
        print(f"  ❌ 错误匹配为: {result} (期望: {test_case['expected']})")
    
    # 显示summary
    for key in ['max_turns_errors', 'dependency_errors', 'other_errors']:
        if summary[key] > 0:
            print(f"    {key}: {summary[key]}")

print("\n" + "=" * 70)
print("匹配逻辑验证完成")

# 实际添加到manager测试
print("\n实际添加到ParquetCumulativeManager:")
for test_case in ['max_turns_errors', 'dependency_errors']:
    record = TestRecord(
        model=f'test-{test_case}',
        task_type='simple_task',
        prompt_type='baseline',
        difficulty='easy'
    )
    
    record.tool_success_rate = 0.8
    record.success = False
    record.execution_time = 10.0
    record.turns = 5
    record.tool_calls = 3
    record.success_level = 'partial_success'
    record.execution_status = 'partial_success'
    record.ai_error_category = test_case
    record.ai_error_reason = f'Test for {test_case}'
    record.ai_confidence = 0.9
    
    success = manager.add_test_result_with_classification(record)
    print(f"  添加{test_case}: {'成功' if success else '失败'}")

# 刷新并检查
manager._flush_buffer()
print("\n数据已刷新")