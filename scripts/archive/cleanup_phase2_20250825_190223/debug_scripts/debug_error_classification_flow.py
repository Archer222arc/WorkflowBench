#!/usr/bin/env python3
"""
调试AI分类到Parquet统计的完整数据流
"""

import os
os.environ['STORAGE_FORMAT'] = 'parquet'

from cumulative_test_manager import TestRecord
from parquet_cumulative_manager import ParquetCumulativeManager

# 创建管理器
manager = ParquetCumulativeManager()

# 模拟一个测试记录，带有AI分类结果
record = TestRecord(
    model='debug-test-model',
    task_type='simple_task',
    prompt_type='baseline',
    difficulty='easy'
)

# 设置测试结果
record.tool_success_rate = 0.8
record.success = False
record.execution_time = 10.0
record.turns = 5
record.tool_calls = 3
record.success_level = 'partial_success'  # partial_success应该触发错误统计
record.execution_status = 'partial_success'

# 关键：设置AI分类结果为sequence_order_errors
record.ai_error_category = 'sequence_order_errors'  # 直接设置字符串
record.ai_error_reason = 'Test: Steps executed in wrong order'
record.ai_confidence = 0.75

print("=" * 60)
print("测试数据流：AI分类 -> Parquet统计")
print("=" * 60)

print(f"\n1. 输入记录:")
print(f"   model: {record.model}")
print(f"   success_level: {record.success_level}")
print(f"   ai_error_category: {record.ai_error_category}")
print(f"   ai_error_reason: {record.ai_error_reason}")

# 调用内部方法来测试统计逻辑
print(f"\n2. 测试_update_summary逻辑:")

# 创建一个测试summary
test_summary = {
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
}

# 模拟_update_summary的核心逻辑
print(f"\n   检查错误分类逻辑:")
error_type = record.ai_error_category
print(f"   - 原始error_type: '{error_type}'")

if error_type:
    error_type = str(error_type).lower()
    print(f"   - 转换为小写: '{error_type}'")
    
    # 测试每个条件
    print(f"\n   条件检查:")
    print(f"   - 'timeout' in error_type: {'timeout' in error_type}")
    print(f"   - 'dependency' in error_type: {'dependency' in error_type}")
    print(f"   - 'parameter' in error_type: {'parameter' in error_type}")
    print(f"   - 'tool_selection' in error_type: {'tool_selection' in error_type}")
    print(f"   - 'sequence' in error_type: {'sequence' in error_type}")
    print(f"   - 'max_turns' in error_type: {'max_turns' in error_type}")
    print(f"   - 'format' in error_type: {'format' in error_type}")
    
    # 执行分类逻辑
    if 'timeout' in error_type:
        test_summary['timeout_errors'] += 1
        classified_as = 'timeout_errors'
    elif 'dependency' in error_type:
        test_summary['dependency_errors'] += 1
        classified_as = 'dependency_errors'
    elif 'parameter' in error_type:
        test_summary['parameter_config_errors'] += 1
        classified_as = 'parameter_config_errors'
    elif 'tool_selection' in error_type:
        test_summary['tool_selection_errors'] += 1
        classified_as = 'tool_selection_errors'
    elif 'sequence' in error_type:
        test_summary['sequence_order_errors'] += 1
        classified_as = 'sequence_order_errors'
    elif 'max_turns' in error_type:
        test_summary['max_turns_errors'] += 1
        classified_as = 'max_turns_errors'
    elif 'format' in error_type:
        test_summary['tool_call_format_errors'] += 1
        classified_as = 'tool_call_format_errors'
    else:
        test_summary['other_errors'] += 1
        classified_as = 'other_errors'
    
    print(f"\n   ✅ 分类结果: {classified_as}")
    print(f"   - sequence_order_errors: {test_summary['sequence_order_errors']}")
    print(f"   - other_errors: {test_summary['other_errors']}")

# 实际添加到管理器
print(f"\n3. 添加到ParquetCumulativeManager:")
success = manager.add_test_result_with_classification(record)
print(f"   添加结果: {'成功' if success else '失败'}")

# 刷新并检查
manager._flush_buffer()

# 检查Parquet文件
print(f"\n4. 检查Parquet数据:")
import pandas as pd
from pathlib import Path

parquet_file = Path('pilot_bench_parquet_data/test_results.parquet')
if parquet_file.exists():
    df = pd.read_parquet(parquet_file)
    test_df = df[df['model'] == 'debug-test-model']
    
    if len(test_df) > 0:
        latest = test_df.iloc[-1]
        print(f"   找到记录:")
        print(f"   - total_errors: {latest.get('total_errors', 0)}")
        print(f"   - sequence_order_errors: {latest.get('sequence_order_errors', 0)}")
        print(f"   - other_errors: {latest.get('other_errors', 0)}")
        
        if latest.get('sequence_order_errors', 0) > 0:
            print(f"   ✅ 正确分类为sequence_order_errors!")
        elif latest.get('other_errors', 0) > 0:
            print(f"   ❌ 错误地分类为other_errors!")
    else:
        print(f"   ❌ 未找到debug-test-model的记录")