#!/usr/bin/env python3
"""
分析什么样的错误会被分类为other_errors
"""

import os
os.environ['STORAGE_FORMAT'] = 'parquet'

from txt_based_ai_classifier import TxtBasedAIClassifier

def analyze_other_errors():
    """分析other_errors的分类模式"""
    
    print("=" * 60)
    print("分析other_errors分类模式")
    print("=" * 60)
    
    # 创建AI分类器
    classifier = TxtBasedAIClassifier(model_name="gpt-5-nano")
    
    # 测试更多边界情况
    edge_cases = [
        {
            "name": "场景A：空指针异常",
            "content": """
Round 1:
[TOOL CALL] data_processor
[ERROR] NullPointerException: Cannot read property 'length' of null
Task failed with null pointer exception.
Success Level: failure
"""
        },
        {
            "name": "场景B：除零错误",
            "content": """
Round 1:
[TOOL CALL] calculator
[ERROR] Division by zero error
Task failed due to arithmetic error.
Success Level: failure
"""
        },
        {
            "name": "场景C：递归深度超限",
            "content": """
Round 1:
[TOOL CALL] recursive_processor
[ERROR] Maximum recursion depth exceeded
Stack overflow error.
Success Level: failure
"""
        },
        {
            "name": "场景D：类型转换错误",
            "content": """
Round 1:
[TOOL CALL] type_converter
[ERROR] TypeError: Cannot convert string to integer
Invalid type conversion.
Success Level: failure
"""
        },
        {
            "name": "场景E：断言失败",
            "content": """
Round 1:
[TOOL CALL] validator
[ERROR] AssertionError: Expected value > 0, got -1
Assertion failed.
Success Level: failure
"""
        },
        {
            "name": "场景F：编码错误",
            "content": """
Round 1:
[TOOL CALL] text_processor
[ERROR] UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff
Encoding error.
Success Level: failure
"""
        },
        {
            "name": "场景G：索引越界",
            "content": """
Round 1:
[TOOL CALL] array_processor
[ERROR] IndexError: list index out of range
Array access error.
Success Level: failure
"""
        },
        {
            "name": "场景H：键不存在",
            "content": """
Round 1:
[TOOL CALL] dict_processor
[ERROR] KeyError: 'required_key'
Missing dictionary key.
Success Level: failure
"""
        }
    ]
    
    # 测试并统计
    other_errors_count = 0
    categorized_errors = {}
    
    print("\n各种异常的分类结果：")
    print("-" * 60)
    
    for case in edge_cases:
        print(f"\n{case['name']}")
        category, reason, confidence = classifier.classify_from_txt_content(case['content'])
        
        print(f"  分类：{category.value}")
        print(f"  原因：{reason[:80]}...")
        
        if category.value == "other_errors":
            other_errors_count += 1
            print("  ⚠️ 归为other_errors")
        
        # 统计各类别
        if category.value not in categorized_errors:
            categorized_errors[category.value] = []
        categorized_errors[category.value].append(case['name'])
    
    # 汇总分析
    print("\n" + "=" * 60)
    print("分类统计：")
    print("-" * 60)
    for error_type, cases in categorized_errors.items():
        print(f"{error_type}: {len(cases)}个")
        for case in cases:
            print(f"  - {case}")
    
    print("\n" + "=" * 60)
    print("结论：")
    print(f"- {other_errors_count}/{len(edge_cases)} 个异常被分类为other_errors")
    print("\n通常被分类为other_errors的错误类型：")
    print("1. 运行时异常（NullPointer, TypeError, IndexError等）")
    print("2. 系统资源错误（内存溢出、栈溢出等）")
    print("3. 权限和访问控制错误")
    print("4. 未预期的内部错误")
    print("5. 编程错误（断言失败、类型错误等）")
    print("\n不会被分类为other_errors的：")
    print("1. 明确的超时错误 → timeout_errors")
    print("2. 工具调用格式问题 → tool_call_format_errors")
    print("3. 超过最大轮次 → max_turns_errors")
    print("4. 工具选择错误 → tool_selection_errors")
    print("5. 参数配置问题 → parameter_config_errors")
    print("6. 执行顺序错误 → sequence_order_errors")
    print("7. 外部依赖问题 → dependency_errors")
    print("=" * 60)

if __name__ == "__main__":
    analyze_other_errors()
