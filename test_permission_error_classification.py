#!/usr/bin/env python3
"""
测试权限错误的分类
"""

import os
os.environ['STORAGE_FORMAT'] = 'parquet'

from txt_based_ai_classifier import TxtBasedAIClassifier

def test_permission_error():
    """测试权限错误是否被正确分类"""
    
    print("=" * 60)
    print("测试权限错误分类")
    print("=" * 60)
    
    # 创建AI分类器
    classifier = TxtBasedAIClassifier(model_name="gpt-5-nano")
    
    # 模拟日志中的权限错误
    test_content = """
Test Log: data_pipeline_test
================================================================================

Task Type: data_pipeline
Prompt Type: optimal

Round 1:
Human: Execute the data pipeline task
Assistant: I'll execute the file_operations_reader tool.

<tool_call>file_operations_reader</tool_call>

Round 2:
Human: ❌ file_operations_reader failed.
Error: PERMISSION_DENIED: Insufficient permissions (required permission: read)

Current progress: 1 tools executed. Continue with the pipeline execution.

Round 3:
Assistant: The file_operations_reader failed due to insufficient permissions. I'll try data_processing_parser instead.

<tool_call>data_processing_parser</tool_call>

Round 4:
Human: ✅ data_processing_parser executed successfully.
Output: {"status": "completed"}

=== FINAL RESULT ===
Task partially completed.
Some tools failed but alternatives succeeded.
Success Level: partial_success
Error: PERMISSION_DENIED: Insufficient permissions (required permission: read)
"""
    
    print("测试内容：包含PERMISSION_DENIED错误")
    print("-" * 40)
    
    # 使用AI分类
    category, reason, confidence = classifier.classify_from_txt_content(test_content)
    
    print(f"分类结果：{category.value}")
    print(f"置信度：{confidence:.2f}")
    print(f"原因：{reason[:200]}")
    
    if category.value == "other_errors":
        print("\n✅ 权限错误被正确分类为other_errors")
    else:
        print(f"\n⚠️ 权限错误被分类为{category.value}而不是other_errors")
    
    # 测试实际的日志文件
    print("\n" + "=" * 60)
    print("测试实际的日志文件")
    print("=" * 60)
    
    log_file = "/Users/ruichengao/WorkflowBench/scale_up/scale_up/workflow_quality_results/test_logs/data_pipeline_insttask_3c17b055_test133_optimal_log.txt"
    
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            actual_content = f.read()
        
        # 提取关键部分
        if "PERMISSION_DENIED" in actual_content:
            print("日志中发现PERMISSION_DENIED错误")
            
            # 使用AI分类实际日志
            actual_category, actual_reason, actual_confidence = classifier.classify_from_txt_content(actual_content)
            
            print(f"\n实际日志分类结果：{actual_category.value}")
            print(f"置信度：{actual_confidence:.2f}")
            print(f"原因：{actual_reason[:200]}")
            
            if actual_category.value == "other_errors":
                print("\n✅ 实际日志权限错误被正确分类为other_errors")
            else:
                print(f"\n⚠️ 实际日志权限错误被分类为{actual_category.value}")
    else:
        print("日志文件不存在")
    
    print("\n" + "=" * 60)
    print("结论：")
    print("- 权限错误(PERMISSION_DENIED)应该被分类为other_errors")
    print("- 如果Error Type是None，说明AI分类器可能没有被调用")
    print("- 需要检查partial_success场景是否触发了AI分类")
    print("=" * 60)

if __name__ == "__main__":
    test_permission_error()