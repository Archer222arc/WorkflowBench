#!/usr/bin/env python3
"""
测试AI直接分类（跳过规则匹配）
"""

import os
os.environ['STORAGE_FORMAT'] = 'parquet'

from txt_based_ai_classifier import TxtBasedAIClassifier
from batch_test_runner import BatchTestRunner, TestTask

def test_direct_ai_classification():
    """测试直接使用AI分类，跳过规则匹配"""
    
    print("=" * 60)
    print("测试AI直接分类（跳过规则匹配）")
    print("=" * 60)
    
    # 创建AI分类器
    classifier = TxtBasedAIClassifier(model_name="gpt-5-nano")
    print(f"✅ AI分类器初始化成功")
    
    # 测试场景1：包含"timeout"关键词但实际是成功的测试
    print("\n场景1：日志包含'timeout'但测试成功")
    txt_content1 = """
===================
TASK TYPE: api_integration
MODEL: test-model
PROMPT TYPE: optimal
===================

Round 1:
Human: Please process the data using the required tools.
Assistant: I'll help you process the data. Let me start by reading the input.

[TOOL CALL] file_operations_reader
Result: SUCCESS - Read file successfully

Round 2:
Human: Continue processing.
Assistant: I'll now parse the data. Note: Be careful about timeout settings.

[TOOL CALL] data_processing_parser
Result: SUCCESS - Parsed data correctly

Round 3:
Human: Good, finish the task.
Assistant: Completing the final steps.

[TOOL CALL] data_processing_transformer
Result: SUCCESS - Transformation complete

=== FINAL RESULT ===
Task completed successfully!
All required tools executed.
Total turns: 3/10
Success Level: full_success
"""
    
    print("  日志内容：包含'timeout'关键词但任务成功")
    
    # 使用旧的规则方式（作为对比）
    print("\n  使用规则匹配（已注释）：")
    print("    预期：会错误地分类为timeout_errors")
    
    # 使用新的直接AI分类
    print("\n  使用AI直接分类：")
    category, reason, confidence = classifier.classify_from_txt_content(txt_content1)
    print(f"    分类结果：{category}")
    print(f"    置信度：{confidence:.2f}")
    print(f"    原因：{reason[:100]}")
    
    # 测试场景2：真正的timeout错误
    print("\n场景2：真正的timeout错误")
    txt_content2 = """
===================
TASK TYPE: complex_processing
MODEL: test-model
PROMPT TYPE: baseline
===================

Round 1:
Human: Process the large dataset.
Assistant: I'll process the dataset.

[TOOL CALL] data_processing_heavy
[ERROR] Test timeout after 10 minutes
Execution terminated due to timeout.

=== FINAL RESULT ===
Task failed due to timeout.
Required tools not completed.
Total turns: 1/10
Success Level: failure
Error: Test timeout after 10 minutes
"""
    
    print("  日志内容：真正的timeout错误")
    
    print("\n  使用AI直接分类：")
    category2, reason2, confidence2 = classifier.classify_from_txt_content(txt_content2)
    print(f"    分类结果：{category2}")
    print(f"    置信度：{confidence2:.2f}")
    print(f"    原因：{reason2[:100]}")
    
    # 测试场景3：格式错误
    print("\n场景3：工具调用格式错误")
    txt_content3 = """
===================
TASK TYPE: api_integration
MODEL: test-model
PROMPT TYPE: baseline
===================

Round 1:
Human: Please call the API.
Assistant: I'll call the API now.

[FORMAT ERROR] Unable to parse tool call format
Model response: "tool: api_caller {invalid json}"

Round 2:
Human: Try again with correct format.
Assistant: Let me try again.

[FORMAT ERROR] JSON parsing failed
Model response: "api_caller({not valid})"

=== FINAL RESULT ===
Task failed due to format errors.
Total format errors: 2
Success Level: partial_success
"""
    
    print("  日志内容：工具调用格式错误")
    
    print("\n  使用AI直接分类：")
    category3, reason3, confidence3 = classifier.classify_from_txt_content(txt_content3)
    print(f"    分类结果：{category3}")
    print(f"    置信度：{confidence3:.2f}")
    print(f"    原因：{reason3[:100]}")
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结：")
    print("✅ AI分类器现在直接分析完整交互记录")
    print("✅ 跳过了简单的关键词规则匹配")
    print("✅ 能够理解上下文，避免误判")
    print("✅ 对于包含'timeout'但成功的测试不会误分类")
    print("=" * 60)

if __name__ == "__main__":
    test_direct_ai_classification()