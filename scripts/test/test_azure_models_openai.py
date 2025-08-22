#!/usr/bin/env python3
"""
用OpenAI客户端测试Azure模型
"""

from openai import AzureOpenAI
import time

# Azure 8540配置
client = AzureOpenAI(
    api_key="6Qc2Oxuf0oVtGutYCTSHOGbm1Dmn4kESwrDYeytkJsHWv3xqrnEMJQQJ99BHACHYHv6XJ3w3AAAAACOGXWza",
    api_version="2024-05-01-preview",
    azure_endpoint="https://85409-me3ofvov-eastus2.services.ai.azure.com"
)

# 要测试的模型列表
models_to_test = [
    "DeepSeek-V3-0324",
    "DeepSeek-V3-0324-2", 
    "DeepSeek-R1-0528",
    "DeepSeek-R1-0528-2",
    "gpt-4o",
    "gpt-4o-mini", 
    "gpt-5-mini",
    "gpt-5-nano",
    "Llama-3.3-70B-Instruct"
]

def test_azure_model(model_name):
    """测试Azure模型"""
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "1+1=?"}]
        )
        
        if response.choices and len(response.choices) > 0:
            answer = response.choices[0].message.content.strip()
            return {"success": True, "response": answer}
        else:
            return {"success": False, "error": "Empty response"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

def main():
    print("🧪 测试Azure 8540模型")
    print("=" * 40)
    
    successful_models = []
    
    for i, model in enumerate(models_to_test, 1):
        print(f"[{i}/{len(models_to_test)}] {model}: ", end="")
        
        result = test_azure_model(model)
        
        if result["success"]:
            print(f"✅ {result['response']}")
            successful_models.append(model)
        else:
            error = result["error"][:60] + "..." if len(result["error"]) > 60 else result["error"]
            print(f"❌ {error}")
    
    print("\n" + "=" * 40)
    print(f"📊 成功: {len(successful_models)}/{len(models_to_test)}")
    
    if successful_models:
        print("\n✅ 可用的Azure模型:")
        for model in successful_models:
            print(f"  • {model}")
    
    return successful_models

if __name__ == "__main__":
    main()