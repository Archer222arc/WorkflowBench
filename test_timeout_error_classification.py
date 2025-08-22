#!/usr/bin/env python3
"""
测试timeout_errors被错误分类为other_errors的问题
"""

import os
os.environ['STORAGE_FORMAT'] = 'parquet'

from cumulative_test_manager import TestRecord
from parquet_cumulative_manager import ParquetCumulativeManager

print("=" * 70)
print("测试timeout_errors分类问题")
print("=" * 70)

# 创建管理器
manager = ParquetCumulativeManager()

# 创建一个模拟DeepSeek V3超时的测试记录
record = TestRecord(
    model='DeepSeek-V3-0324-test',
    task_type='api_integration',
    prompt_type='optimal',
    difficulty='easy'
)

# 设置测试结果 - 模拟超时失败的情况
record.tool_success_rate = 0.8
record.success = False
record.partial_success = False
record.execution_time = 120.0  # 超时
record.turns = 1
record.tool_calls = 0  # 没有工具调用（因为超时了）
record.success_level = 'failure'
record.execution_status = 'failure'
record.error_message = "Test timeout after 10 minutes"

# 动态添加AI分类字段（模拟batch_test_runner的行为）
record.ai_error_category = 'timeout_errors'  # AI正确分类为timeout_errors
record.ai_error_reason = 'The test timed out after 10 minutes'
record.ai_confidence = 0.95

print(f"\n测试记录:")
print(f"  模型: {record.model}")
print(f"  任务类型: {record.task_type}")
print(f"  成功级别: {record.success_level}")
print(f"  工具调用数: {record.tool_calls}")
print(f"  错误消息: {record.error_message}")
print(f"  AI分类: {record.ai_error_category}")

# 添加到manager
success = manager.add_test_result_with_classification(record)
print(f"\n添加记录: {'成功' if success else '失败'}")

# 刷新缓冲区
manager._flush_buffer()
print("数据已刷新")

# 检查Parquet数据
import pandas as pd
from pathlib import Path

parquet_file = Path('pilot_bench_parquet_data/test_results.parquet')
if parquet_file.exists():
    df = pd.read_parquet(parquet_file)
    
    # 找到刚才添加的记录
    test_df = df[df['model'] == 'DeepSeek-V3-0324-test']
    
    if len(test_df) > 0:
        latest = test_df.iloc[-1]
        print(f"\nParquet中的记录:")
        print(f"  模型: {latest.get('model', 'N/A')}")
        print(f"  任务类型: {latest.get('task_type', 'N/A')}")
        print(f"  总测试数: {latest.get('total', 0)}")
        print(f"  失败数: {latest.get('failed', 0)}")
        print(f"  总错误数: {latest.get('total_errors', 0)}")
        
        # 检查各种错误类型
        error_types = [
            'tool_call_format_errors', 'timeout_errors', 'max_turns_errors',
            'tool_selection_errors', 'parameter_config_errors', 
            'sequence_order_errors', 'dependency_errors', 'other_errors'
        ]
        
        print(f"\n错误分类统计:")
        for error_type in error_types:
            count = latest.get(error_type, 0)
            if count > 0:
                print(f"  {error_type}: {count}")
        
        # 诊断问题
        if latest.get('timeout_errors', 0) == 0 and latest.get('other_errors', 0) > 0:
            print("\n❌ 问题确认: timeout_errors被错误分类为other_errors!")
        elif latest.get('timeout_errors', 0) > 0:
            print("\n✅ 正确: timeout_errors被正确分类!")
    else:
        print("\n未找到测试记录")
else:
    print("\nParquet文件不存在")

print("\n" + "=" * 70)
print("测试完成")