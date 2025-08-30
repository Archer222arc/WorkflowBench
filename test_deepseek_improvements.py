#!/usr/bin/env python3
"""
测试DeepSeek改进效果
验证interactive_executor的改进是否解决了DeepSeek的超时问题
"""

import sys
import os
import json
import time
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from interactive_executor import InteractiveExecutor
from api_client_manager import APIClientManager

def test_deepseek_with_workflow():
    """测试DeepSeek处理工作流的能力"""
    print("\n" + "="*80)
    print("DeepSeek工作流测试 - 验证改进效果")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # 创建一个简单的测试工作流
    test_task = {
        "id": "test_deepseek_001",
        "type": "api_integration", 
        "description": "Fetch data from API, validate it, and post results",
        "required_tools": ["network_fetcher", "data_processing_validator", "network_poster"],
        "prompt_type": "optimal"
    }
    
    # 测试的DeepSeek模型
    models_to_test = [
        "DeepSeek-V3-0324",
        "DeepSeek-R1-0528"
    ]
    
    results = []
    
    for model_name in models_to_test:
        print(f"\n{'='*60}")
        print(f"测试模型: {model_name}")
        print(f"{'='*60}")
        
        # 初始化API客户端
        client_manager = APIClientManager()
        llm_client = client_manager.get_client(model_name)
        
        if not llm_client:
            print(f"❌ 无法获取{model_name}的客户端")
            continue
        
        # 创建执行器
        executor = InteractiveExecutor(
            llm_client=llm_client,
            model_name=model_name,
            tool_registry={
                "network_fetcher": lambda: {"success": True, "data": "test_data"},
                "data_processing_validator": lambda: {"success": True, "valid": True},
                "network_poster": lambda: {"success": True, "posted": True}
            },
            max_turns=10,
            silent=False
        )
        
        # 构建提示
        prompt = f"""Execute an api integration task.

Task: {test_task['description']}

Tool Search Available:
You have access to a comprehensive tool library.
To find tools, use: <tool_search>your query</tool_search>
After finding tools, execute them using: <tool_call>tool_name</tool_call>

Required tools for this task: {', '.join(test_task['required_tools'])}

IMPORTANT: 
1. Search for tools first if needed
2. Then execute them one by one using <tool_call>tool_name</tool_call>
3. Start with the first tool: network_fetcher

Begin by executing the first tool."""
        
        print(f"\n开始测试...")
        start_time = time.time()
        
        try:
            # 执行任务
            result = executor.execute_with_tools(
                prompt=prompt,
                required_tools=test_task['required_tools'],
                task_type=test_task['type']
            )
            
            elapsed = time.time() - start_time
            
            # 分析结果
            success = result.get('success', False)
            format_errors = result.get('format_error_count', 0)
            api_issues = result.get('api_issues', [])
            execution_history = result.get('execution_history', [])
            
            print(f"\n测试结果:")
            print(f"  ✅ 成功: {success}")
            print(f"  ⏱️ 执行时间: {elapsed:.2f}秒")
            print(f"  📝 格式错误次数: {format_errors}")
            print(f"  🔧 执行的工具: {len(execution_history)}")
            print(f"  ⚠️ API问题: {len(api_issues)}")
            
            if api_issues:
                print(f"\n  API问题详情:")
                for issue in api_issues[:3]:  # 显示前3个问题
                    print(f"    - Turn {issue.get('turn', '?')}: {issue.get('issue', 'Unknown')}")
            
            results.append({
                "model": model_name,
                "success": success,
                "execution_time": elapsed,
                "format_errors": format_errors,
                "tools_executed": len(execution_history),
                "api_issues": len(api_issues)
            })
            
        except Exception as e:
            print(f"❌ 测试失败: {str(e)[:200]}")
            results.append({
                "model": model_name,
                "success": False,
                "error": str(e)[:200]
            })
        
        # 等待一下避免rate limit
        time.sleep(3)
    
    # 总结结果
    print("\n" + "="*80)
    print("测试总结")
    print("="*80)
    
    for result in results:
        model = result['model']
        if result.get('success'):
            print(f"\n✅ {model}:")
            print(f"   执行时间: {result['execution_time']:.2f}秒")
            print(f"   格式错误: {result['format_errors']}次")
            print(f"   工具执行: {result['tools_executed']}个")
        else:
            print(f"\n❌ {model}:")
            print(f"   错误: {result.get('error', 'Unknown error')}")
    
    # 保存结果
    result_file = f"deepseek_improvement_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump({
            "test_time": datetime.now().isoformat(),
            "improvements": [
                "早期格式检测 (turn >= 1 for DeepSeek)",
                "明确的格式错误提示",
                "增加超时时间 (180s for R1, 150s for V3)",
                "检测tool_search后未执行tool_call"
            ],
            "results": results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n结果已保存到: {result_file}")
    
    # 分析改进效果
    print("\n" + "="*80)
    print("改进效果分析")
    print("="*80)
    
    if any(r.get('success') for r in results):
        print("✅ 改进有效！至少有一个DeepSeek模型成功完成任务")
    else:
        print("⚠️ 需要进一步改进，所有模型仍然失败")
    
    avg_format_errors = sum(r.get('format_errors', 0) for r in results) / len(results) if results else 0
    if avg_format_errors < 3:
        print(f"✅ 格式错误减少到平均{avg_format_errors:.1f}次")
    else:
        print(f"⚠️ 格式错误仍然较多：平均{avg_format_errors:.1f}次")

if __name__ == "__main__":
    test_deepseek_with_workflow()