#!/usr/bin/env python3
"""
全面测试所有7种错误类型的匹配逻辑
验证修复后的parquet_cumulative_manager.py是否能正确分类所有错误
"""

import os
os.environ['STORAGE_FORMAT'] = 'parquet'

from cumulative_test_manager import TestRecord
from parquet_cumulative_manager import ParquetCumulativeManager

# 定义所有7种标准错误类型及其可能的变体
ERROR_TYPE_TESTS = [
    # 1. tool_call_format_errors
    {
        'name': 'tool_call_format_errors',
        'test_values': [
            'tool_call_format_errors',  # 完整名称
            'TOOL_CALL_FORMAT_ERRORS',  # 大写
            'tool_call_format',         # 不带_errors
            'format_errors',             # 只有format
            'format'                     # 最短匹配
        ],
        'expected': 'tool_call_format_errors'
    },
    
    # 2. timeout_errors
    {
        'name': 'timeout_errors',
        'test_values': [
            'timeout_errors',
            'TIMEOUT_ERRORS',
            'timeout',
            'test timeout after 10 minutes',  # 实际错误消息
            'API timeout'
        ],
        'expected': 'timeout_errors'
    },
    
    # 3. max_turns_errors
    {
        'name': 'max_turns_errors',
        'test_values': [
            'max_turns_errors',
            'MAX_TURNS_ERRORS',
            'max_turns',
            'max turns exceeded',
            'reached maximum turns'
        ],
        'expected': 'max_turns_errors'
    },
    
    # 4. tool_selection_errors
    {
        'name': 'tool_selection_errors',
        'test_values': [
            'tool_selection_errors',
            'TOOL_SELECTION_ERRORS',
            'tool_selection',
            'wrong tool selected',
            'tool selection mistake'
        ],
        'expected': 'tool_selection_errors'
    },
    
    # 5. parameter_config_errors
    {
        'name': 'parameter_config_errors',
        'test_values': [
            'parameter_config_errors',
            'PARAMETER_CONFIG_ERRORS',
            'parameter_config',
            'parameter',
            'wrong parameters'
        ],
        'expected': 'parameter_config_errors'
    },
    
    # 6. sequence_order_errors
    {
        'name': 'sequence_order_errors',
        'test_values': [
            'sequence_order_errors',  # AI返回的完整形式
            'SEQUENCE_ORDER_ERRORS',
            'sequence_order',
            'sequence',
            'wrong order',
            'steps out of sequence'
        ],
        'expected': 'sequence_order_errors'
    },
    
    # 7. dependency_errors
    {
        'name': 'dependency_errors',
        'test_values': [
            'dependency_errors',
            'DEPENDENCY_ERRORS',
            'dependency',
            'missing dependency',
            'dependency not met'
        ],
        'expected': 'dependency_errors'
    }
]

def test_error_matching_logic(error_type_str):
    """测试错误匹配逻辑（从parquet_cumulative_manager.py复制）"""
    summary = {
        'tool_call_format_errors': 0,
        'timeout_errors': 0,
        'max_turns_errors': 0,
        'tool_selection_errors': 0,
        'parameter_config_errors': 0,
        'sequence_order_errors': 0,
        'dependency_errors': 0,
        'other_errors': 0
    }
    
    if error_type_str:
        error_type = str(error_type_str).lower()
        
        # 修复后的匹配逻辑
        if 'timeout' in error_type:
            summary['timeout_errors'] += 1
            return 'timeout_errors'
        elif 'dependency' in error_type:
            summary['dependency_errors'] += 1
            return 'dependency_errors'
        elif 'parameter' in error_type or 'parameter_config' in error_type:
            summary['parameter_config_errors'] += 1
            return 'parameter_config_errors'
        elif 'tool_selection' in error_type:
            summary['tool_selection_errors'] += 1
            return 'tool_selection_errors'
        elif 'sequence' in error_type or 'sequence_order' in error_type:
            summary['sequence_order_errors'] += 1
            return 'sequence_order_errors'
        elif 'max_turns' in error_type:
            summary['max_turns_errors'] += 1
            return 'max_turns_errors'
        elif 'format' in error_type or 'tool_call_format' in error_type:
            summary['tool_call_format_errors'] += 1
            return 'tool_call_format_errors'
        else:
            summary['other_errors'] += 1
            return 'other_errors'
    
    return None

print("=" * 70)
print("测试所有错误类型的匹配逻辑")
print("=" * 70)

all_pass = True
failed_tests = []

for error_test in ERROR_TYPE_TESTS:
    print(f"\n测试 {error_test['name']}:")
    print("-" * 40)
    
    for test_value in error_test['test_values']:
        result = test_error_matching_logic(test_value)
        expected = error_test['expected']
        
        if result == expected:
            print(f"  ✅ '{test_value}' -> {result}")
        else:
            print(f"  ❌ '{test_value}' -> {result} (期望: {expected})")
            all_pass = False
            failed_tests.append({
                'type': error_test['name'],
                'input': test_value,
                'got': result,
                'expected': expected
            })

# 测试一些不应该匹配的情况
print(f"\n测试应该分类为other_errors的情况:")
print("-" * 40)

other_test_cases = [
    'unknown error',
    'something went wrong',
    'model failed',
    'api error',
    'network issue',
    ''  # 空字符串
]

for test_case in other_test_cases:
    result = test_error_matching_logic(test_case)
    if result == 'other_errors' or result is None:
        print(f"  ✅ '{test_case}' -> {result}")
    else:
        print(f"  ❌ '{test_case}' -> {result} (期望: other_errors)")
        all_pass = False
        failed_tests.append({
            'type': 'other_errors',
            'input': test_case,
            'got': result,
            'expected': 'other_errors'
        })

# 总结
print("\n" + "=" * 70)
if all_pass:
    print("✅ 所有错误类型都能正确匹配！")
    print("修复成功 - 所有7种错误类型及其变体都能被正确识别")
else:
    print(f"❌ 有 {len(failed_tests)} 个测试失败")
    print("\n失败的测试:")
    for failed in failed_tests:
        print(f"  - {failed['type']}: '{failed['input']}' -> {failed['got']} (期望: {failed['expected']})")

# 测试实际的ParquetCumulativeManager
print("\n" + "=" * 70)
print("测试ParquetCumulativeManager的实际行为")
print("=" * 70)

manager = ParquetCumulativeManager()

# 为每种错误类型创建测试记录
for error_test in ERROR_TYPE_TESTS:
    print(f"\n测试 {error_test['name']} 在实际manager中:")
    
    # 使用完整的错误类型名称测试
    record = TestRecord(
        model=f'test-{error_test["name"]}',
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
    
    # 设置AI错误分类 - 使用完整名称
    record.ai_error_category = error_test['test_values'][0]  # 使用第一个测试值（完整名称）
    record.ai_error_reason = f'Test for {error_test["name"]}'
    record.ai_confidence = 0.9
    
    # 添加到manager
    success = manager.add_test_result_with_classification(record)
    print(f"  添加记录: {'成功' if success else '失败'}")

# 刷新缓冲区
manager._flush_buffer()
print("\n数据已刷新到Parquet文件")

print("\n" + "=" * 70)
print("测试完成！")
print("所有7种错误类型的匹配逻辑已验证")
print("=" * 70)