#!/usr/bin/env python3
"""
测试IdealLab API key轮换机制
验证不同prompt_type是否使用不同的API key
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from api_client_manager import APIClientManager, get_client_for_model

def test_key_rotation():
    """测试API key轮换"""
    
    print("=" * 60)
    print("IdealLab API Key 轮换测试")
    print("=" * 60)
    
    # 创建manager实例
    manager = APIClientManager()
    
    # 测试的prompt类型
    prompt_types = [
        'baseline',      # 应该使用key0
        'cot',          # 应该使用key1  
        'optimal',      # 应该使用key2
        'flawed_sequence_disorder',  # 应该轮询
        'flawed_tool_misuse',        # 应该轮询
        'flawed_parameter_error',    # 应该轮询
        None            # 默认轮询
    ]
    
    # 测试qwen模型的key选择
    model = "qwen2.5-7b-instruct"
    
    print(f"\n测试模型: {model}")
    print("-" * 40)
    
    for prompt_type in prompt_types:
        try:
            # 获取客户端
            client = get_client_for_model(model, prompt_type)
            
            # 检查使用的API key
            if hasattr(client, 'api_key_used'):
                api_key = client.api_key_used
                # 隐藏部分key显示
                key_display = api_key[:8] + "..." + api_key[-4:]
            else:
                api_key = "未记录"
                key_display = "未记录"
            
            prompt_str = str(prompt_type) if prompt_type else "None"
            print(f"Prompt类型: {prompt_str:30} -> API Key: {key_display}")
            
        except Exception as e:
            prompt_str = str(prompt_type) if prompt_type else "None"
            print(f"Prompt类型: {prompt_str:30} -> 错误: {e}")
    
    # 检查key池配置
    print("\n" + "=" * 60)
    print("API Key池配置")
    print("-" * 40)
    
    if hasattr(manager, '_idealab_keys'):
        print(f"可用的IdealLab API keys数量: {len(manager._idealab_keys)}")
        for i, key in enumerate(manager._idealab_keys):
            key_display = key[:8] + "..." + key[-4:]
            print(f"  Key {i}: {key_display}")
    else:
        print("未找到IdealLab key池配置")
    
    # 检查prompt到key的映射策略
    if hasattr(manager, '_prompt_key_strategy'):
        print("\nPrompt类型到Key的映射策略:")
        for prompt_type, key_index in manager._prompt_key_strategy.items():
            if key_index >= 0:
                print(f"  {prompt_type:10} -> 固定使用 Key {key_index}")
            else:
                print(f"  {prompt_type:10} -> 轮询使用")
    
    # 测试多次调用flawed类型看是否轮询
    print("\n" + "=" * 60)
    print("测试flawed类型的轮询机制")
    print("-" * 40)
    
    flawed_type = 'flawed_sequence_disorder'
    print(f"连续3次调用 {flawed_type}:")
    
    for i in range(3):
        client = get_client_for_model(model, flawed_type)
        if hasattr(client, 'api_key_used'):
            api_key = client.api_key_used
            key_display = api_key[:8] + "..." + api_key[-4:]
            print(f"  第{i+1}次: {key_display}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_key_rotation()