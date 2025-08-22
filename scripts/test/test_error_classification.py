#!/usr/bin/env python3
"""
测试错误分类系统对各种错误的识别能力
"""

from focused_ai_classifier import FocusedAIClassifier, ErrorContext, StandardErrorType

# 创建分类器实例
classifier = FocusedAIClassifier(model_name="gpt-5-nano")

# 测试用例
test_cases = [
    {
        "name": "Agent超时",
        "error_message": "Test timeout after 60 seconds",
        "expected": StandardErrorType.TIMEOUT
    },
    {
        "name": "执行超时",
        "error_message": "Execution timeout: Agent failed to complete in 120 seconds",
        "expected": StandardErrorType.TIMEOUT
    },
    {
        "name": "429限流错误",
        "error_message": "Error: 429 Too Many Requests - Rate limit exceeded. TPM/RPM限流",
        "expected": StandardErrorType.OTHER  # 工具级错误，不是Agent决策错误
    },
    {
        "name": "API限流",
        "error_message": "API error: Rate limit hit, please retry after 60 seconds",
        "expected": StandardErrorType.OTHER
    },
    {
        "name": "400错误",
        "error_message": "400 Bad Request: Invalid parameters",
        "expected": StandardErrorType.OTHER  # 可能需要进一步分析
    },
    {
        "name": "网络超时",
        "error_message": "Network timeout: Connection timed out after 30 seconds",
        "expected": StandardErrorType.OTHER  # 工具级错误
    },
    {
        "name": "请求超时",
        "error_message": "Request timeout: No response from server",
        "expected": StandardErrorType.OTHER
    },
    {
        "name": "工具格式错误",
        "error_message": "Tool call format error: Unable to parse JSON response",
        "expected": StandardErrorType.TOOL_CALL_FORMAT
    },
    {
        "name": "最大轮次",
        "error_message": "Max turns reached: Agent exceeded 50 turns limit",
        "expected": StandardErrorType.MAX_TURNS
    },
    {
        "name": "连接超时",
        "error_message": "Connection timeout while calling API",
        "expected": StandardErrorType.OTHER
    },
    {
        "name": "服务不可用",
        "error_message": "Service unavailable: 503 error from backend",
        "expected": StandardErrorType.OTHER
    }
]

print("="*70)
print("测试错误分类系统")
print("="*70)

# 运行测试
passed = 0
failed = 0

for test in test_cases:
    # 创建错误上下文
    context = ErrorContext(
        task_description="Test task",
        task_type="test",
        required_tools=["tool1", "tool2"],
        executed_tools=["tool1"],
        is_partial_success=False,
        tool_execution_results=[],
        execution_time=10.0,
        total_turns=5,
        error_message=test["error_message"]
    )
    
    # 分类错误
    error_type, reason, confidence = classifier.classify_error(context)
    
    # 检查结果
    is_correct = error_type == test["expected"]
    status = "✅" if is_correct else "❌"
    
    if is_correct:
        passed += 1
    else:
        failed += 1
    
    print(f"\n{status} 测试: {test['name']}")
    print(f"   错误消息: {test['error_message'][:60]}...")
    print(f"   预期类型: {test['expected'].value}")
    print(f"   实际类型: {error_type.value}")
    print(f"   分析原因: {reason}")
    print(f"   置信度: {confidence:.2f}")

print("\n" + "="*70)
print(f"测试结果: {passed}/{len(test_cases)} 通过")
print(f"通过率: {passed/len(test_cases)*100:.1f}%")

# 特别说明
print("\n" + "="*70)
print("重要说明:")
print("-"*70)
print("1. Agent超时（execution timeout）会被正确分类为 TIMEOUT_ERRORS")
print("2. 429限流、400错误等API/工具级问题会被分类为 OTHER_ERRORS")
print("3. 网络超时、连接超时等工具问题也会被分类为 OTHER_ERRORS")
print("4. 这是正确的，因为这些不是Agent的决策错误，而是外部系统问题")
print("5. 系统会在重试机制中处理这些瞬时错误，不影响最终测试结果")