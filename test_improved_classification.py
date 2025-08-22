#!/usr/bin/env python3
"""
测试改进后的AI错误分类
"""

import os
os.environ['STORAGE_FORMAT'] = 'parquet'

from txt_based_ai_classifier import TxtBasedAIClassifier

def test_improved_classification():
    """测试改进后的分类是否正确理解AI的错误"""
    
    print("=" * 60)
    print("测试改进后的AI错误分类")
    print("=" * 60)
    
    # 创建AI分类器
    classifier = TxtBasedAIClassifier(model_name="gpt-5-nano")
    
    # 场景1：工具失败后AI没有重试或选择替代方案
    scenario1 = """
Test Log: data_pipeline_test
================================================================================

Round 1:
Human: Execute the data pipeline task. You need to read data first.
Assistant: I'll read the data using file_operations_reader.

<tool_call>file_operations_reader</tool_call>

Round 2:
Human: ❌ file_operations_reader failed.
Error: PERMISSION_DENIED: Insufficient permissions (required permission: read)

Current progress: 1 tools executed. Continue with the pipeline execution.

Round 3:
Assistant: The file_operations_reader failed. Let me try data_processing_parser instead.

<tool_call>data_processing_parser</tool_call>

Round 4:
Human: ✅ data_processing_parser executed successfully.

Round 5:
Assistant: Now I'll continue with the next step.

<tool_call>data_processing_transformer</tool_call>

=== FINAL RESULT ===
Task partially completed.
Required tool file_operations_reader was not successfully executed.
The AI failed to properly handle the permission error by not retrying or finding a proper alternative for reading.
Success Level: partial_success
"""
    
    print("\n场景1：工具失败后AI没有正确处理")
    print("期望：应该被分类为tool_selection_errors")
    print("-" * 40)
    
    category1, reason1, confidence1 = classifier.classify_from_txt_content(scenario1)
    print(f"分类结果：{category1.value}")
    print(f"原因：{reason1[:150]}...")
    
    # 场景2：AI选择了错误的工具
    scenario2 = """
Test Log: api_integration_test
================================================================================

Round 1:
Human: Call the external API to fetch data.
Assistant: I'll use the file_operations_reader to get the API data.

<tool_call>file_operations_reader</tool_call>

Round 2:
Human: ❌ file_operations_reader failed.
Error: FILE_NOT_FOUND: This is not the right tool for API calls

Round 3:
Assistant: Let me try file_operations_writer instead.

<tool_call>file_operations_writer</tool_call>

Round 4:
Human: ❌ file_operations_writer failed.
Error: INVALID_OPERATION: Writing won't help with API calls

=== FINAL RESULT ===
Task failed.
The AI consistently chose file operations tools instead of network/API tools.
Success Level: failure
"""
    
    print("\n场景2：AI选择了完全错误的工具类型")
    print("期望：应该被分类为tool_selection_errors")
    print("-" * 40)
    
    category2, reason2, confidence2 = classifier.classify_from_txt_content(scenario2)
    print(f"分类结果：{category2.value}")
    print(f"原因：{reason2[:150]}...")
    
    # 场景3：AI没有处理依赖关系
    scenario3 = """
Test Log: data_pipeline_test
================================================================================

Round 1:
Human: Process the data through the pipeline. Note: transformer requires parser to run first.
Assistant: I'll start with the transformer.

<tool_call>data_processing_transformer</tool_call>

Round 2:
Human: ❌ data_processing_transformer failed.
Error: DEPENDENCY_NOT_MET: Required tool 'data_processing_parser' must be executed first

Round 3:
Assistant: Let me try the validator instead.

<tool_call>data_processing_validator</tool_call>

Round 4:
Human: ❌ data_processing_validator failed.
Error: DEPENDENCY_NOT_MET: Required tool 'data_processing_parser' must be executed first

=== FINAL RESULT ===
Task failed.
The AI ignored dependency requirements and didn't execute parser first.
Success Level: failure
"""
    
    print("\n场景3：AI没有正确处理工具依赖")
    print("期望：应该被分类为dependency_errors或sequence_order_errors")
    print("-" * 40)
    
    category3, reason3, confidence3 = classifier.classify_from_txt_content(scenario3)
    print(f"分类结果：{category3.value}")
    print(f"原因：{reason3[:150]}...")
    
    print("\n" + "=" * 60)
    print("总结：")
    print("改进后的分类器应该能够：")
    print("1. 理解工具返回的错误是测试挑战，不是AI的错误")
    print("2. 识别AI在处理这些挑战时的错误行为")
    print("3. 正确分类AI的错误（而不是工具的错误）")
    print("=" * 60)

if __name__ == "__main__":
    test_improved_classification()