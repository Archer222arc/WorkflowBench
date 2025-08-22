#!/usr/bin/env python3
"""测试DeepSeek处理实际工作流prompt的问题"""

from api_client_manager import get_client_for_model
import json

model = "DeepSeek-V3-0324"
client = get_client_for_model(model)

print(f"测试模型: {model}")
print("=" * 60)

# 这是实际工作流测试中使用的prompt格式
workflow_prompt = """You are an AI assistant that helps execute workflows step by step.

## Available Tools
- data_processing_validator: Validates input data against a schema
- data_processing_transformer: Transforms data from one format to another  
- data_processing_filter: Filters data based on specified criteria

## Task
Execute a data processing workflow with the following steps:
1. Validate input data
2. Transform the data
3. Filter the results

## Required Tools
You must use these tools in order: ['data_processing_validator', 'data_processing_transformer', 'data_processing_filter']

## Instructions
For each step, respond with a tool call in this EXACT format:
[TOOL_CALL] tool_name {"param1": "value1", "param2": "value2"}

Start with the first tool."""

# 测试不同的conversation格式
test_cases = [
    {
        "name": "系统消息+用户消息",
        "messages": [
            {"role": "system", "content": workflow_prompt},
            {"role": "user", "content": "Execute the workflow"}
        ]
    },
    {
        "name": "仅用户消息",
        "messages": [
            {"role": "user", "content": workflow_prompt + "\n\nExecute the workflow"}
        ]
    },
    {
        "name": "简化的工具调用",
        "messages": [
            {"role": "user", "content": "Call this tool: [TOOL_CALL] data_processing_validator {\"data\": \"test\"}"}
        ]
    },
    {
        "name": "带搜索提示的格式",
        "messages": [
            {"role": "system", "content": workflow_prompt},
            {"role": "user", "content": "[SEARCH] Query: data validation"},
            {"role": "assistant", "content": "I'll help you execute the data validation workflow."},
            {"role": "user", "content": "Now execute the first tool"}
        ]
    }
]

for test_case in test_cases:
    print(f"\n测试: {test_case['name']}")
    print("-" * 40)
    
    # 计算总token数
    total_chars = sum(len(msg['content']) for msg in test_case['messages'])
    print(f"总字符数: {total_chars}")
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=test_case['messages'],
            temperature=0.7,
            max_tokens=200
        )
        
        content = response.choices[0].message.content
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens
        finish_reason = response.choices[0].finish_reason
        
        print(f"Prompt tokens: {prompt_tokens}")
        print(f"Completion tokens: {completion_tokens}")
        print(f"Finish reason: {finish_reason}")
        
        if not content:
            print("⚠️ 返回了空内容!")
            # 打印更多调试信息
            print(f"Full response.choices[0]: {response.choices[0]}")
        else:
            print(f"✅ 响应内容: '{content[:200]}'...")
            # 检查是否包含工具调用
            if "[TOOL_CALL]" in content:
                print("✅ 包含工具调用格式")
            else:
                print("⚠️ 未包含工具调用格式")
                
    except Exception as e:
        print(f"❌ 错误: {e}")

print("\n" + "=" * 60)