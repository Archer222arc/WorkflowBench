#\!/usr/bin/env python3
"""测试不同模型使用AI分类时的表现"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from focused_ai_classifier import FocusedAIClassifier, ErrorContext

def test_different_models():
    """测试不同模型的AI分类器表现"""
    
    # 测试不同的分类器模型
    test_models = [
        "gpt-4o-mini",    # 通用模型
        "gpt-5-nano",     # 专门的GPT-5 nano
    ]
    
    # 创建测试用例
    test_context = ErrorContext(
        task_description="Process data file and generate report",
        task_type="simple_task", 
        required_tools=["data_loader", "processor", "report_generator"],
        executed_tools=["data_loader", "processor"],
        is_partial_success=True,
        tool_execution_results=[
            {"tool": "data_loader", "success": True, "error": None},
            {"tool": "processor", "success": True, "error": None}, 
            {"tool": "report_generator", "success": False, "error": "Missing data format specification"}
        ],
        execution_time=25.0,
        total_turns=8,
        error_message="Report generation failed - agent provided wrong format parameters"
    )
    
    print("🔍 测试不同模型的AI分类器...")
    print("=" * 60)
    
    for model in test_models:
        print(f"\n📊 测试模型: {model}")
        print("-" * 40)
        
        try:
            # 创建分类器
            classifier = FocusedAIClassifier(model_name=model)
            
            if classifier.client is None:
                print(f"  ❌ 无法初始化 {model} 客户端")
                continue
                
            print(f"  ✅ 分类器初始化成功")
            print(f"  📝 是否为GPT-5 nano: {getattr(classifier, 'is_gpt5_nano', False)}")
            
            # 测试分类（但不实际调用API，只测试参数准备）
            try:
                # 测试prompt构建
                prompt = classifier._build_focused_prompt(test_context)
                print(f"  ✅ Prompt构建成功 (长度: {len(prompt)} 字符)")
                
                # 测试快速规则检查
                rule_result = classifier._quick_rule_check(test_context)
                if rule_result:
                    category, reason, confidence = rule_result
                    print(f"  🎯 规则预筛选: {category.value} (置信度: {confidence:.2f})")
                    print(f"     原因: {reason}")
                else:
                    print(f"  🔄 需要AI分类 (规则预筛选未匹配)")
                
                # 测试后备分类
                fallback_result = classifier._fallback_classify(test_context)
                category, reason, confidence = fallback_result
                print(f"  🔒 后备分类: {category.value} (置信度: {confidence:.2f})")
                print(f"     原因: {reason}")
                
            except Exception as e:
                print(f"  ❌ 分类过程出错: {e}")
                import traceback
                print(f"     错误详情: {traceback.format_exc()}")
                
        except Exception as e:
            print(f"  ❌ 分类器创建失败: {e}")
    
    print(f"\n" + "=" * 60)
    print("💡 结论:")
    print("- 如果某个模型显示创建失败，说明该模型的API配置有问题")
    print("- 如果分类过程出错，可能是该模型特有的参数或响应格式问题") 
    print("- 规则预筛选和后备分类应该对所有模型都正常工作")

if __name__ == "__main__":
    test_different_models()
