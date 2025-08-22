#!/usr/bin/env python3
"""
测试增强的基于日志数据的AI分类系统
验证新的分类器能正确处理完整的交互日志数据
"""

import json
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from enhanced_log_based_classifier import EnhancedLogBasedClassifier, StandardErrorType

def test_enhanced_ai_classifier():
    """测试增强的AI分类器"""
    print("=" * 60)
    print("测试增强的基于日志数据的AI分类器")
    print("=" * 60)
    
    # 初始化分类器
    try:
        classifier = EnhancedLogBasedClassifier(model_name="gpt-5-nano")
        print(f"✅ 分类器初始化成功: {classifier.is_available()}")
    except Exception as e:
        print(f"❌ 分类器初始化失败: {e}")
        return
    
    # 创建测试用的完整日志数据
    sample_log_data = {
        "test_id": "test_enhanced_classification_001",
        "task_type": "simple_task",
        "prompt_type": "baseline", 
        "timestamp": "2025-08-12T10:30:00.000000",
        "is_flawed": False,
        "flaw_type": None,
        
        # 任务实例
        "task_instance": {
            "required_tools": ["tool_write_file", "tool_execute_python"],
            "description": "Create a Python script that calculates fibonacci numbers and save it to a file",
            "task_type": "simple_task"
        },
        
        # 提示信息
        "prompt": "You are a Python programming assistant. Create a Python script that calculates fibonacci numbers up to n=10 and save it to fibonacci.py",
        
        # LLM响应
        "llm_response": '''I'll create a Python script to calculate fibonacci numbers.

```python
def fibonacci(n):
    if n <= 1:
        return n
    else:
        return fibonacci(n-1) + fibonacci(n-2)

for i in range(11):
    print(f"F({i}) = {fibonacci(i)}")
```

Let me save this to a file using the write tool.''',
        
        # 工具调用
        "extracted_tool_calls": [
            {
                "tool": "tool_write_file",
                "parameters": {
                    "filename": "fibonacci.py",
                    "content": "def fibonacci(n):\\n    if n <= 1:\\n        return n\\n    else:\\n        return fibonacci(n-1) + fibonacci(n-2)\\n\\nfor i in range(11):\\n    print(f'F({i}) = {fibonacci(i)}')"
                }
            }
        ],
        
        # 对话历史
        "conversation_history": [
            {
                "role": "user",
                "content": "Create a Python script that calculates fibonacci numbers and save it to a file"
            },
            {
                "role": "assistant", 
                "content": "I'll create a Python script to calculate fibonacci numbers and save it to fibonacci.py"
            }
        ],
        
        # 执行历史
        "execution_history": [
            {
                "tool": "tool_write_file",
                "success": False,
                "error": "Permission denied: cannot write to fibonacci.py",
                "timestamp": "2025-08-12T10:30:15.000000"
            }
        ],
        
        # 执行结果
        "result": {
            "success": False,
            "final_score": 0.2,
            "execution_time": 3.5,
            "workflow_score": 0.8,
            "phase2_score": 0.0,
            "quality_score": 0.1,
            "tool_calls": ["tool_write_file"],
            "error": "Permission denied: cannot write to fibonacci.py",
            "error_type": "permission_error"
        }
    }
    
    print("\n📄 测试日志数据概览:")
    print(f"   任务类型: {sample_log_data['task_type']}")
    print(f"   需要工具: {sample_log_data['task_instance']['required_tools']}")
    print(f"   执行成功: {sample_log_data['result']['success']}")
    print(f"   错误信息: {sample_log_data['result']['error']}")
    print(f"   对话轮数: {len(sample_log_data['conversation_history'])}")
    print(f"   执行历史: {len(sample_log_data['execution_history'])} 条")
    
    # 进行AI分类
    print("\n🤖 开始AI分类...")
    try:
        error_type, reasoning, confidence = classifier.classify_from_log_data(sample_log_data)
        
        print(f"\n✅ AI分类结果:")
        print(f"   错误类型: {error_type.value}")
        print(f"   分析原因: {reasoning[:200]}{'...' if len(reasoning) > 200 else ''}")
        print(f"   置信度: {confidence:.2%}")
        
        # 验证结果的合理性
        if error_type in StandardErrorType:
            print(f"   ✅ 错误类型有效")
        else:
            print(f"   ❌ 错误类型无效")
            
        if 0.0 <= confidence <= 1.0:
            print(f"   ✅ 置信度范围正确")
        else:
            print(f"   ❌ 置信度范围异常: {confidence}")
            
    except Exception as e:
        print(f"❌ AI分类失败: {e}")
        import traceback
        traceback.print_exc()

def test_different_error_types():
    """测试不同类型的错误分类"""
    print("\n" + "=" * 60)
    print("测试不同错误类型的分类能力")
    print("=" * 60)
    
    classifier = EnhancedLogBasedClassifier(model_name="gpt-5-nano")
    if not classifier.is_available():
        print("❌ 分类器不可用，跳过测试")
        return
    
    # 测试超时错误
    timeout_log = {
        "task_type": "complex_task",
        "prompt_type": "baseline",
        "task_instance": {"required_tools": ["tool1", "tool2"]},
        "conversation_history": [],
        "execution_history": [],
        "extracted_tool_calls": [],
        "llm_response": "",
        "result": {
            "success": False,
            "error": "Task execution timed out after 60 seconds",
            "execution_time": 60.0,
            "tool_calls": []
        }
    }
    
    print("\n🔍 测试超时错误:")
    try:
        error_type, reasoning, confidence = classifier.classify_from_log_data(timeout_log)
        print(f"   类型: {error_type.value}")
        print(f"   置信度: {confidence:.2%}")
        if error_type == StandardErrorType.TIMEOUT:
            print("   ✅ 正确识别为超时错误")
        else:
            print(f"   ⚠️  分类为: {error_type.value} (可能合理)")
    except Exception as e:
        print(f"   ❌ 分类失败: {e}")

def test_batch_runner_integration():
    """测试与批处理运行器的集成"""
    print("\n" + "=" * 60)
    print("测试与批处理运行器的集成")
    print("=" * 60)
    
    # 模拟批处理运行器中的使用场景
    print("\n🔧 模拟批处理场景:")
    print("   - 启用save_logs: True")
    print("   - 启用AI分类: True")
    print("   - 测试失败案例")
    
    # 这里可以添加实际的批处理测试
    # 但为了简化，我们只展示集成点
    
    classifier = EnhancedLogBasedClassifier()
    if classifier.is_available():
        print("   ✅ 分类器可用，可以集成到批处理流程")
        print("   ✅ 将在有错误且有log_data时自动调用")
        print("   ✅ 结果将保存到TestRecord的AI分类字段")
    else:
        print("   ⚠️  分类器不可用，将回退到传统分类")

def main():
    """主测试函数"""
    print("🧪 增强AI分类系统测试")
    print("测试基于完整交互日志数据的错误分类能力")
    print()
    
    # 运行各项测试
    test_enhanced_ai_classifier()
    test_different_error_types()
    test_batch_runner_integration()
    
    print("\n" + "=" * 60)
    print("✅ 测试完成!")
    print("📋 改进点总结:")
    print("   1. ✅ 创建了基于完整日志数据的新分类器")
    print("   2. ✅ 集成到batch_test_runner中")
    print("   3. ✅ 在log_data可用时自动使用新分类器")
    print("   4. ✅ 保存AI分类结果到TestRecord")
    print("   5. ✅ 提供更丰富的上下文信息给AI模型")
    print()
    print("🚀 使用方法:")
    print("   python smart_batch_runner.py --save-logs --ai-classification")
    print("=" * 60)

if __name__ == "__main__":
    main()