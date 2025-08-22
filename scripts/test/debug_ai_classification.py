#\!/usr/bin/env python3
"""Debug AI分类器的JSON解析问题"""

import logging
from focused_ai_classifier import FocusedAIClassifier, ErrorContext

# 设置详细日志
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s')

# 创建分类器
classifier = FocusedAIClassifier()

# 模拟一个可能导致JSON解析失败的复杂case
context = ErrorContext(
    task_description="Process unspecified input data through three tools: validate structure, transform format, and parse for extraction",
    task_type="simple_task", 
    required_tools=["data_processing_validator", "data_processing_transformer", "data_processing_parser"],
    executed_tools=["data_processing_validator", "data_processing_transformer"],
    is_partial_success=True,
    tool_execution_results=[
        {"tool": "data_processing_validator", "success": True, "error": None},
        {"tool": "data_processing_transformer", "success": True, "error": None}, 
        {"tool": "data_processing_parser", "success": False, "error": "OPERATION_FAILED: Operation could not be completed"}
    ],
    execution_time=15.0,
    total_turns=8,
    error_message="Partial success - some tools failed"
)

print("开始AI分类测试...")

try:
    result = classifier.classify_error(context)
    print(f"\n✅ 分类成功: {result}")
except Exception as e:
    print(f"\n❌ 分类失败: {e}")
    import traceback
    traceback.print_exc()
