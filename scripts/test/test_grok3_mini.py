#!/usr/bin/env python3
"""
测试Azure新部署的grok-3-mini模型
"""

from openai import AzureOpenAI

# Azure 8540配置
client = AzureOpenAI(
    api_key="6Qc2Oxuf0oVtGutYCTSHOGbm1Dmn4kESwrDYeytkJsHWv3xqrnEMJQQJ99BHACHYHv6XJ3w3AAAAACOGXWza",
    api_version="2024-05-01-preview",
    azure_endpoint="https://85409-me3ofvov-eastus2.services.ai.azure.com"
)

def test_grok3_mini():
    """测试grok-3-mini模型 - 最基本配置"""
    try:
        print("🧪 测试 grok-3-mini...")
        
        response = client.chat.completions.create(
            model="grok-3-mini",
            messages=[{"role": "user", "content": "1+1=?"}]
        )
        
        if response.choices and len(response.choices) > 0:
            answer = response.choices[0].message.content.strip()
            print(f"✅ grok-3-mini: {answer}")
            return True
        else:
            print("❌ grok-3-mini: Empty response")
            return False
            
    except Exception as e:
        print(f"❌ grok-3-mini: {str(e)}")
        return False

def test_all_azure_models():
    """测试所有Azure模型"""
    models = [
        "DeepSeek-V3-0324",
        "DeepSeek-R1-0528", 
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-5-mini",
        "gpt-5-nano",
        "grok-3",
        "grok-3-mini",  # 新增
        "Llama-3.3-70B-Instruct"
    ]
    
    print("🧪 测试所有Azure模型")
    print("=" * 40)
    
    successful = []
    
    for model in models:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "1+1=?"}]
            )
            
            if response.choices and len(response.choices) > 0:
                answer = response.choices[0].message.content.strip()
                print(f"✅ {model}: {answer[:30]}...")
                successful.append(model)
            else:
                print(f"❌ {model}: Empty response")
        
        except Exception as e:
            error = str(e)[:50] + "..." if len(str(e)) > 50 else str(e)
            print(f"❌ {model}: {error}")
    
    print("\n" + "=" * 40)
    print(f"📊 成功: {len(successful)}/{len(models)}")
    
    if successful:
        print("\n✅ 可用的Azure模型:")
        for model in successful:
            print(f"  • {model}")
    
    return successful

if __name__ == "__main__":
    # 先单独测试grok-3-mini
    print("🎯 重点测试新部署的grok-3-mini")
    print("=" * 40)
    grok_result = test_grok3_mini()
    
    print("\n" * 2)
    
    # 然后测试所有模型
    all_results = test_all_azure_models()
    
    if grok_result:
        print(f"\n🎉 新模型grok-3-mini部署成功！")
        print(f"🏆 Azure现在有{len(all_results)}个可用模型")