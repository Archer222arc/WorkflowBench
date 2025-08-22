#!/usr/bin/env python3
"""测试gpt-5-mini模型的可用性"""

import sys
from api_client_manager import MultiModelAPIManager
import logging

logging.basicConfig(level=logging.INFO)

def test_gpt5_mini():
    """测试gpt-5-mini的API调用"""
    manager = MultiModelAPIManager()
    
    print("\n========== 测试 gpt-5-mini ==========")
    
    try:
        # 获取客户端
        client = manager.get_client_for_model("gpt-5-mini")
        print(f"✅ 成功获取客户端")
        
        # 获取API模型名
        api_model_name = manager.get_model_name_for_api("gpt-5-mini")
        print(f"📝 API模型名: {api_model_name}")
        
        # 测试简单的API调用（不带参数）
        print("\n测试API调用（不带max_tokens和temperature）...")
        response = client.chat.completions.create(
            model=api_model_name,
            messages=[
                {"role": "user", "content": "Say 'Hello, I am working!' in exactly 5 words."}
            ],
            timeout=30
        )
        
        if response and response.choices:
            content = response.choices[0].message.content
            print(f"✅ API响应成功")
            print(f"   响应内容: {content}")
            return True
        else:
            print(f"❌ 空响应")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_gpt5_mini()
    
    if success:
        print("\n✅ gpt-5-mini 模型可用！")
        print("   可以将其加入闭源模型列表进行测试")
    else:
        print("\n❌ gpt-5-mini 模型不可用")
        print("   建议暂时不将其加入测试列表")
    
    sys.exit(0 if success else 1)