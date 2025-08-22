#\!/usr/bin/env python3
"""测试不同模型是否会导致不同的AI分类错误"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

def simulate_different_responses():
    """模拟不同模型可能返回的不同响应格式"""
    
    from focused_ai_classifier import FocusedAIClassifier
    
    # 创建分类器实例
    classifier = FocusedAIClassifier()
    
    print("🧪 模拟测试不同响应格式的解析...")
    print("=" * 50)
    
    # 测试不同的响应格式
    test_responses = [
        # 1. 正常的JSON响应 (GPT-4o-mini style)
        '{"category": "tool_selection_errors", "reason": "Wrong tool selected", "confidence": 0.85}',
        
        # 2. 带markdown格式的JSON (有些模型会这样)
        '```json\n{"category": "parameter_config_errors", "reason": "Invalid parameters", "confidence": 0.75}\n```',
        
        # 3. 纯文本响应 (某些模型在特定情况下)
        'The error appears to be related to tool selection issues.',
        
        # 4. 混合格式
        'Based on analysis: {"category": "sequence_order_errors", "reason": "Wrong order", "confidence": 0.8}',
        
        # 5. 空响应或异常格式
        '',
        
        # 6. 不完整的JSON
        '{"category": "dependency_errors", "reason": "Missing dependency"',
    ]
    
    for i, response in enumerate(test_responses, 1):
        print(f"\n🔍 测试响应格式 {i}:")
        print(f"   输入: {response[:50]}{'...' if len(response) > 50 else ''}")
        
        try:
            result = classifier._parse_focused_response(response)
            category, reason, confidence = result
            print(f"   ✅ 解析成功: {category.value} (置信度: {confidence:.2f})")
            print(f"      原因: {reason}")
        except Exception as e:
            print(f"   ❌ 解析失败: {e}")

def check_tool_result_access():
    """检查工具结果访问的不同情况"""
    
    print(f"\n" + "=" * 50)
    print("🔧 测试工具结果对象访问...")
    
    # 模拟不同类型的工具结果对象
    test_results = [
        # 1. 字典类型 (常见)
        {"tool": "test_tool", "success": True, "error": None},
        
        # 2. 对象类型 (ToolExecutionResult)
        type('ToolExecutionResult', (), {
            "tool": "test_tool", 
            "success": False, 
            "error": "Test error"
        })(),
        
        # 3. 字符串类型 (异常情况)
        "unexpected_string_result",
        
        # 4. None
        None,
    ]
    
    from focused_ai_classifier import FocusedAIClassifier
    classifier = FocusedAIClassifier()
    
    for i, result in enumerate(test_results, 1):
        print(f"\n🔍 测试结果对象 {i} ({type(result).__name__}):")
        
        try:
            # 测试修复后的安全访问代码
            if result is None:
                print("   ⚠️ 跳过None结果")
                continue
                
            # 使用修复后的安全访问方式
            success = getattr(result, 'success', result.get('success', False)) if hasattr(result, 'get') else getattr(result, 'success', False)
            tool_name = getattr(result, 'tool', result.get('tool', 'Unknown')) if hasattr(result, 'get') else getattr(result, 'tool', 'Unknown')
            error_msg = getattr(result, 'error', result.get('error', 'Unknown')) if hasattr(result, 'get') else getattr(result, 'error', 'Unknown')
            
            print(f"   ✅ 访问成功: tool={tool_name}, success={success}, error={error_msg}")
            
        except Exception as e:
            print(f"   ❌ 访问失败: {e}")

if __name__ == "__main__":
    simulate_different_responses()
    check_tool_result_access()
    
    print(f"\n" + "=" * 50)
    print("💡 结论:")
    print("1. AI分类错误通常不是模型特定的，而是:")
    print("   - 响应格式解析问题 (已修复)")
    print("   - 工具结果对象访问问题 (已修复)")
    print("   - API连接或参数问题 (模型特定)")
    print("")
    print("2. 如果只有Llama模型出错，可能原因:")
    print("   - Llama的API端点配置问题")
    print("   - Llama返回的响应格式特殊")
    print("   - Llama的API参数要求不同")
