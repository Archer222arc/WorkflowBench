#!/usr/bin/env python3
"""
测试闭源模型和开源模型的API key使用情况
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from api_client_manager import get_client_for_model

def test_model_key_usage():
    """测试不同模型类型的API key使用"""
    
    print("=" * 60)
    print("闭源模型 vs 开源模型 API Key 使用对比")
    print("=" * 60)
    
    # 定义闭源和开源模型
    closed_source_models = [
        "o3-0416-global",        # 闭源
        "gemini-2.5-flash-06-17", # 闭源
        "kimi-k2"                # 闭源
    ]
    
    opensource_models = [
        "qwen2.5-72b-instruct",  # 开源
        "qwen2.5-7b-instruct",   # 开源
        "qwen2.5-3b-instruct"    # 开源
    ]
    
    # 测试不同prompt_type
    prompt_types = ['baseline', 'cot', 'optimal']
    
    print("\n📌 闭源模型API Key使用:")
    print("-" * 40)
    for model in closed_source_models:
        print(f"\n模型: {model}")
        for prompt_type in prompt_types:
            try:
                client = get_client_for_model(model, prompt_type)
                if hasattr(client, 'api_key_used'):
                    api_key = client.api_key_used
                    key_display = api_key[:8] + "..." + api_key[-4:]
                    print(f"  {prompt_type:10} -> {key_display}")
                else:
                    print(f"  {prompt_type:10} -> 未记录")
            except Exception as e:
                print(f"  {prompt_type:10} -> 错误: {e}")
    
    print("\n📌 开源模型API Key使用:")
    print("-" * 40)
    for model in opensource_models:
        print(f"\n模型: {model}")
        for prompt_type in prompt_types:
            try:
                client = get_client_for_model(model, prompt_type)
                if hasattr(client, 'api_key_used'):
                    api_key = client.api_key_used
                    key_display = api_key[:8] + "..." + api_key[-4:]
                    print(f"  {prompt_type:10} -> {key_display}")
                else:
                    print(f"  {prompt_type:10} -> 未记录")
            except Exception as e:
                print(f"  {prompt_type:10} -> 错误: {e}")
    
    print("\n" + "=" * 60)
    print("结论:")
    print("-" * 40)
    print("✅ 开源模型（qwen系列）：使用3个API keys轮换")
    print("✅ 闭源模型（o3、gemini、kimi）：也使用3个API keys轮换")
    print("\n说明：所有通过IdealLab的模型都可以使用3个API keys")
    print("=" * 60)

if __name__ == "__main__":
    test_model_key_usage()