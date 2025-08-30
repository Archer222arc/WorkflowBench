#!/usr/bin/env python3
"""
测试gpt-5-nano对错误类别的理解
"""

import os
os.environ['STORAGE_FORMAT'] = 'parquet'

from txt_based_ai_classifier import TxtBasedAIClassifier

def test_error_category_knowledge():
    """测试AI分类器对错误类别的认知"""
    
    print("=" * 60)
    print("测试GPT-5-nano错误分类器的知识")
    print("=" * 60)
    
    # 创建AI分类器
    classifier = TxtBasedAIClassifier(model_name="gpt-5-nano")
    print(f"✅ AI分类器初始化成功\n")
    
    # 测试各种边界情况
    test_cases = [
        {
            "name": "场景1：网络连接错误",
            "content": """
===================
TASK TYPE: api_integration
MODEL: test-model
===================

Round 1:
Human: Call the external API
Assistant: I'll call the API now.

[TOOL CALL] external_api_caller
[ERROR] Connection refused: Unable to connect to https://api.example.com
Network error: Connection timeout

=== FINAL RESULT ===
Task failed due to network connection error.
Success Level: failure
Error: Connection refused
"""
        },
        {
            "name": "场景2：认证失败",
            "content": """
===================
TASK TYPE: api_integration
===================

Round 1:
Human: Access the protected resource
Assistant: I'll access the resource.

[TOOL CALL] auth_api_caller
[ERROR] Authentication failed: Invalid API key
HTTP 401: Unauthorized

=== FINAL RESULT ===
Task failed due to authentication error.
Success Level: failure
Error: Invalid credentials
"""
        },
        {
            "name": "场景3：资源不存在",
            "content": """
===================
TASK TYPE: file_processing
===================

Round 1:
Human: Process the file data.txt
Assistant: I'll process the file.

[TOOL CALL] file_reader
[ERROR] File not found: data.txt does not exist
No such file or directory

=== FINAL RESULT ===
Task failed because required file doesn't exist.
Success Level: failure
Error: File not found
"""
        },
        {
            "name": "场景4：权限不足",
            "content": """
===================
TASK TYPE: system_operation
===================

Round 1:
Human: Delete system files
Assistant: I'll delete the files.

[TOOL CALL] file_operations_delete
[ERROR] Permission denied: Cannot delete /system/critical.conf
Insufficient privileges

=== FINAL RESULT ===
Task failed due to permission error.
Success Level: failure
Error: Permission denied
"""
        },
        {
            "name": "场景5：内存溢出",
            "content": """
===================
TASK TYPE: data_processing
===================

Round 1:
Human: Process the large dataset
Assistant: I'll process the dataset.

[TOOL CALL] data_processing_heavy
[ERROR] Out of memory error
Java heap space exhausted
MemoryError: Unable to allocate array

=== FINAL RESULT ===
Task failed due to memory overflow.
Success Level: failure
Error: Out of memory
"""
        },
        {
            "name": "场景6：业务逻辑错误",
            "content": """
===================
TASK TYPE: business_logic
===================

Round 1:
Human: Calculate the discount
Assistant: I'll calculate the discount.

[TOOL CALL] discount_calculator
[ERROR] Business rule violation: Discount cannot exceed 100%
Invalid discount rate: 150%

=== FINAL RESULT ===
Task failed due to business logic error.
Success Level: failure
Error: Invalid business rule
"""
        },
        {
            "name": "场景7：数据验证失败",
            "content": """
===================
TASK TYPE: data_validation
===================

Round 1:
Human: Validate the email addresses
Assistant: I'll validate the emails.

[TOOL CALL] email_validator
[ERROR] Validation failed: Invalid email format
"not-an-email" is not a valid email address

=== FINAL RESULT ===
Task failed due to data validation error.
Success Level: failure
Error: Invalid data format
"""
        },
        {
            "name": "场景8：未知工具错误",
            "content": """
===================
TASK TYPE: unknown_operation
===================

Round 1:
Human: Use the special tool
Assistant: I'll use the tool.

[TOOL CALL] special_tool
[ERROR] An unexpected error occurred
Unknown error code: -99999
Stack trace: [internal error]

=== FINAL RESULT ===
Task failed with unknown error.
Success Level: failure
Error: Unknown error
"""
        }
    ]
    
    # 先询问AI分类器它知道哪些错误类别
    print("询问AI分类器关于错误类别的知识：")
    print("-" * 40)
    
    knowledge_prompt = """
作为工作流测试错误分类专家，请列出你知道的所有标准错误类型。

你被训练识别以下7种标准错误类型：
1. tool_call_format_errors
2. timeout_errors
3. max_turns_errors
4. tool_selection_errors
5. parameter_config_errors
6. sequence_order_errors
7. dependency_errors
8. other_errors

请说明：
1. 每种错误类型的典型特征
2. 什么样的错误会被归类为other_errors
3. 对于网络错误、认证错误、权限错误、内存错误等，你会如何分类？

请以JSON格式回答。
"""
    
    # 直接调用AI询问其知识
    from api_client_manager import get_client_for_model
    client = get_client_for_model("gpt-5-nano")
    
    response = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[{"role": "user", "content": knowledge_prompt}]
    )
    
    print("AI分类器的回答：")
    print(response.choices[0].message.content)
    print("\n" + "=" * 60)
    
    # 测试各种错误场景
    print("\n测试各种错误场景的分类：")
    print("=" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{test_case['name']}")
        print("-" * 40)
        
        category, reason, confidence = classifier.classify_from_txt_content(test_case['content'])
        
        print(f"分类结果：{category.value}")
        print(f"置信度：{confidence:.2f}")
        print(f"原因：{reason[:150]}...")
        
        # 判断是否被分类为other_errors
        if category.value == "other_errors":
            print("⚠️ 被分类为other_errors")
    
    print("\n" + "=" * 60)
    print("总结：")
    print("- GPT-5-nano理解7种标准错误类型")
    print("- 非标准错误（网络、认证、权限、内存等）通常被归为other_errors")
    print("- other_errors是一个兜底分类，用于无法明确归类的错误")
    print("=" * 60)

if __name__ == "__main__":
    test_error_category_knowledge()
