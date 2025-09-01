#!/usr/bin/env python3
"""
测试IdealLab闭源模型key选择逻辑
"""

from api_client_manager import APIClientManager

def test_key_selection():
    print("🧪 测试IdealLab闭源模型Key选择逻辑")
    print("="*50)
    
    # 创建API客户端管理器
    manager = APIClientManager()
    
    # 测试模型列表
    test_models = [
        ("claude-sonnet-4-20250514", "闭源模型"),
        ("o3-0416-global", "闭源模型"),
        ("gemini-2.5-flash-06-17", "闭源模型"), 
        ("kimi-k2", "闭源模型"),
        ("qwen2.5-72b-instruct", "开源模型"),
        ("qwen2.5-7b-instruct", "开源模型")
    ]
    
    for model, model_type in test_models:
        try:
            # 测试不同prompt类型
            for prompt_type in ["baseline", "optimal", "cot"]:
                client = manager._get_ideallab_client(model, prompt_type)
                api_key_used = client.api_key_used
                
                # 检查是否使用key 0
                key_index = manager._idealab_keys.index(api_key_used) if api_key_used in manager._idealab_keys else -1
                
                print(f"📊 {model} ({model_type}) + {prompt_type}: Key索引 = {key_index}")
                
                # 验证闭源模型是否都使用key 0
                if model_type == "闭源模型" and key_index != 0:
                    print(f"❌ 错误：{model} 应该使用Key 0，但实际使用Key {key_index}")
                elif model_type == "闭源模型" and key_index == 0:
                    print(f"✅ 正确：{model} 使用Key 0")
                    
        except Exception as e:
            print(f"❌ 测试 {model} 时出错: {e}")
    
    print("="*50)
    print("🎯 测试完成！")

if __name__ == "__main__":
    test_key_selection()