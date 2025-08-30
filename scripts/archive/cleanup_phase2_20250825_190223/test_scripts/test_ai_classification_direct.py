#!/usr/bin/env python3
"""
直接测试AI分类并追踪数据流
"""

import os
os.environ['STORAGE_FORMAT'] = 'parquet'

# 1. 测试AI分类器是否工作
from txt_based_ai_classifier import TxtBasedAIClassifier

classifier = TxtBasedAIClassifier(model_name="gpt-5-nano")

# 创建一个失败的测试日志
test_log = """
Test Log: simple_task_test
================================================================================

Round 1:
Human: Execute the simple task. Read the file first.
Assistant: I'll read the file using file_operations_reader.

<tool_call>file_operations_reader</tool_call>

Round 2:
Human: ❌ file_operations_reader failed.
Error: PERMISSION_DENIED: Insufficient permissions

Round 3:
Assistant: The file reader failed. I'll stop here.

=== FINAL RESULT ===
Task failed.
The AI didn't retry or use alternative tools after the permission error.
Success Level: failure
"""

print("测试AI分类器...")
category, reason, confidence = classifier.classify_from_txt_content(test_log)
print(f"分类结果: {category}")
print(f"置信度: {confidence}")
print(f"原因: {reason[:100]}...")

# 2. 测试数据流到Parquet
from cumulative_test_manager import TestRecord
from parquet_cumulative_manager import ParquetCumulativeManager

manager = ParquetCumulativeManager()

# 创建测试记录
record = TestRecord(
    model='test-model',
    task_type='simple_task',
    prompt_type='baseline',
    difficulty='easy'
)
record.tool_success_rate = 0.8
record.success = False
record.execution_time = 10.0
record.turns = 3
record.tool_calls = 1
record.success_level = 'failure'
record.execution_status = 'failure'

# 关键：设置AI分类结果
record.ai_error_category = category.value if hasattr(category, 'value') else str(category)
record.ai_error_reason = reason
record.ai_confidence = confidence

print(f"\n设置的ai_error_category: {record.ai_error_category}")

# 添加到管理器
success = manager.add_test_result_with_classification(record)
print(f"添加到管理器: {'成功' if success else '失败'}")

# 刷新缓冲区
manager._flush_buffer()

# 检查Parquet文件
import pandas as pd
from pathlib import Path

parquet_file = Path('pilot_bench_parquet_data/test_results.parquet')
if parquet_file.exists():
    df = pd.read_parquet(parquet_file)
    test_df = df[df['model'] == 'test-model']
    if len(test_df) > 0:
        latest = test_df.iloc[-1]
        print(f"\nParquet中的记录:")
        print(f"  total_errors: {latest.get('total_errors', 0)}")
        print(f"  other_errors: {latest.get('other_errors', 0)}")
        print(f"  tool_selection_errors: {latest.get('tool_selection_errors', 0)}")
        
        # 调试：检查错误分类逻辑
        print(f"\n调试信息:")
        print(f"  ai_error_category传入值: '{record.ai_error_category}'")
        print(f"  转换为小写: '{record.ai_error_category.lower()}'")
        print(f"  包含'tool_selection': {'tool_selection' in record.ai_error_category.lower()}")
