#!/usr/bin/env python3
"""
直接测试DeepSeek模型的调用
验证整个调用链是否正常工作
"""

import sys
import os
import json
import time
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api_client_manager import APIClientManager
from interactive_executor import InteractiveExecutor
from mdp_workflow_generator import MDPWorkflowGenerator

def test_deepseek_direct():
    """直接测试DeepSeek调用"""
    print("\n" + "="*80)
    print("DeepSeek直接调用测试")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    models_to_test = ["DeepSeek-V3-0324", "DeepSeek-R1-0528"]
    
    for model_name in models_to_test:
        print(f"\n{'='*60}")
        print(f"测试模型: {model_name}")
        print(f"{'='*60}")
        
        # Step 1: 获取API客户端
        print("\n1. 获取API客户端...")
        client_manager = APIClientManager()
        
        # 检查模型路由
        print(f"   检查模型路由...")
        
        llm_client = client_manager.get_client(model_name)
        if llm_client:
            print(f"   ✓ 客户端获取成功")
        else:
            print(f"   ✗ 客户端获取失败")
            continue
        
        # Step 2: 测试简单API调用
        print("\n2. 测试简单API调用...")
        try:
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Reply with exactly: Hello World"}
            ]
            
            start_time = time.time()
            response = llm_client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=50,
                temperature=0.1,
                timeout=60
            )
            elapsed = time.time() - start_time
            
            if response and response.choices:
                content = response.choices[0].message.content
                # 检查reasoning_content（DeepSeek特性）
                if not content and hasattr(response.choices[0].message, 'reasoning_content'):
                    content = response.choices[0].message.reasoning_content
                    print(f"   ✓ API响应成功 (使用reasoning_content)")
                else:
                    print(f"   ✓ API响应成功")
                print(f"   响应时间: {elapsed:.2f}秒")
                print(f"   响应内容: {content[:100] if content else 'None'}")
            else:
                print(f"   ✗ API响应为空")
        except Exception as e:
            print(f"   ✗ API调用失败: {str(e)[:200]}")
            continue
        
        # Step 3: 测试工具调用格式
        print("\n3. 测试工具调用格式...")
        try:
            # 创建一个简单的工作流生成器
            generator = MDPWorkflowGenerator()
            task_instance = generator.generate_instance(
                task_type="simple_task",
                difficulty="easy",
                tool_success_rate=0.8
            )
            
            print(f"   生成的任务: {task_instance['description'][:100]}...")
            print(f"   需要的工具: {task_instance['required_tools']}")
            
            # 创建执行器
            executor = InteractiveExecutor(
                llm_client=llm_client,
                model_name=model_name,
                tool_registry=generator.get_all_tools(),
                max_turns=5,  # 减少轮数快速测试
                silent=False
            )
            
            # 构建提示
            prompt = f"""Execute a simple task.

Task: {task_instance['description']}

You have access to tools. Use these formats:
- Search for tools: <tool_search>query</tool_search>
- Execute a tool: <tool_call>tool_name</tool_call>

Required tools: {', '.join(task_instance['required_tools'])}

Start by executing the first tool: <tool_call>{task_instance['required_tools'][0]}</tool_call>"""
            
            print("\n   执行任务...")
            start_time = time.time()
            result = executor.execute_with_tools(
                prompt=prompt,
                required_tools=task_instance['required_tools'],
                task_type="simple_task"
            )
            elapsed = time.time() - start_time
            
            print(f"\n   结果:")
            print(f"   - 成功: {result.get('success', False)}")
            print(f"   - 执行时间: {elapsed:.2f}秒")
            print(f"   - 格式错误: {result.get('format_error_count', 0)}次")
            print(f"   - 执行的工具: {len(result.get('execution_history', []))}个")
            
            if result.get('api_issues'):
                print(f"   - API问题:")
                for issue in result['api_issues'][:2]:
                    print(f"     • {issue.get('issue', 'Unknown')}")
            
        except Exception as e:
            print(f"   ✗ 工具测试失败: {str(e)[:200]}")
        
        print("\n" + "-"*60)
        time.sleep(2)  # 避免rate limit
    
    print("\n" + "="*80)
    print("测试完成")
    print("="*80)

if __name__ == "__main__":
    test_deepseek_direct()