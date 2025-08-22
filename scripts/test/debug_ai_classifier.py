#!/usr/bin/env python3
"""Debug AI classifier directly"""

from focused_ai_classifier import FocusedAIClassifier, ErrorContext

# 创建AI分类器
classifier = FocusedAIClassifier(model_name="gpt-5-nano")

# 创建一个测试错误上下文
context = ErrorContext(
    task_description="Simple file processing task",
    task_type="simple_task",
    required_tools=["read_file", "process_data", "write_file"],
    executed_tools=["read_file", "write_file"],
    is_partial_success=True,
    tool_execution_results=[
        {"tool": "read_file", "success": True},
        {"tool": "process_data", "success": False, "error": "Invalid parameter"},
        {"tool": "write_file", "success": True}
    ],
    execution_time=5.0,
    total_turns=8,
    error_message="Format issues detected: 2 format helps needed"
)

print("Testing AI classifier...")
try:
    category, reason, confidence = classifier.classify_error(context)
    print(f"✅ Result: {category.value}, {reason}, confidence={confidence}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()