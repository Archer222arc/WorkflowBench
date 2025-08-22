#!/usr/bin/env python3
"""测试kimi-k2模型的可用性"""

import sys
from api_client_manager import MultiModelAPIManager
import logging

logging.basicConfig(level=logging.INFO)

def test_kimi_k2():
    """测试kimi-k2的API调用"""
    manager = MultiModelAPIManager()
    
    print("\n========== 测试 kimi-k2 ==========")
    
    try:
        # 获取客户端
        client = manager.get_client_for_model("kimi-k2")
        print(f"✅ 成功获取客户端")
        
        # 获取API模型名
        api_model_name = manager.get_model_name_for_api("kimi-k2")
        print(f"📝 API模型名: {api_model_name}")
        
        # 测试简单的API调用（不带参数）
        print("\n测试API调用（不带max_tokens和temperature）...")
        response = client.chat.completions.create(
            model=api_model_name,
            messages=[
                {"role": "user", "content": "回答：1+1等于几？只说数字。"}
            ],
            timeout=60  # kimi可能响应较慢，给60秒
        )
        
        if response and response.choices:
            content = response.choices[0].message.content
            print(f"✅ API响应成功")
            print(f"   响应内容: {content}")
            
            # 测试第二个请求，确保稳定性
            print("\n测试第二个请求...")
            response2 = client.chat.completions.create(
                model=api_model_name,
                messages=[
                    {"role": "user", "content": "What is 2+2? Answer with just the number."}
                ],
                timeout=60
            )
            
            if response2 and response2.choices:
                content2 = response2.choices[0].message.content
                print(f"✅ 第二次响应成功")
                print(f"   响应内容: {content2}")
                return True
            else:
                print(f"❌ 第二次请求空响应")
                return False
                
        else:
            print(f"❌ 空响应")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        
        # 显示更详细的错误信息
        if "Error code:" in str(e):
            print(f"   错误代码: {str(e)}")
        
        # 尝试解析错误类型
        error_str = str(e).lower()
        if "permission" in error_str or "irc-001" in error_str:
            print("   💡 可能是权限问题，IdealLab个人AK可能无权限访问此模型")
        elif "not found" in error_str or "404" in error_str:
            print("   💡 模型不存在或名称错误")
        elif "timeout" in error_str:
            print("   💡 请求超时，模型响应太慢")
        elif "rate" in error_str:
            print("   💡 可能触发了限流")
        
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_kimi_k2()
    
    print("\n" + "="*50)
    if success:
        print("✅ kimi-k2 模型可用！")
        print("   可以将其加入测试列表")
        print("   建议分类：闭源模型（商业API）")
    else:
        print("❌ kimi-k2 模型不可用")
        print("   建议暂时不将其加入测试列表")
        print("\n可能的解决方案：")
        print("   1. 检查IdealLab是否有该模型权限")
        print("   2. 确认模型名称是否正确")
        print("   3. 尝试使用其他API key")
    print("="*50)
    
    sys.exit(0 if success else 1)