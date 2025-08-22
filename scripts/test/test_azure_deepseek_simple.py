#!/usr/bin/env python3
"""
测试Azure DeepSeek模型 - 最基本配置
"""

from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential

# Azure配置
endpoint = "https://85409-me3ofvov-eastus2.services.ai.azure.com/models"
api_key = "6Qc2Oxuf0oVtGutYCTSHOGbm1Dmn4kESwrDYeytkJsHWv3xqrnEMJQQJ99BHACHYHv6XJ3w3AAAAACOGXWza"

# 根据你的deployment列表
models_to_test = [
    "DeepSeek-V3-0324",
    "DeepSeek-V3-0324-2", 
    "DeepSeek-V3-0324-3",
    "DeepSeek-R1-0528",
    "DeepSeek-R1-0528-2",
    "DeepSeek-R1-0528-3",
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-5-mini",
    "gpt-5-nano",
    "gpt-oss-120b",
    "grok-3",
    "Llama-3.3-70B-Instruct",
    "Llama-3.3-70B-Instruct-2",
    "Llama-3.3-70B-Instruct-3"
]

def test_model(model_name):
    """测试单个模型 - 最基本配置"""
    try:
        client = ChatCompletionsClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(api_key),
            api_version="2024-05-01-preview"
        )
        
        response = client.complete({
            "messages": [
                {"role": "user", "content": "1+1等于几？"}
            ],
            "model": model_name
        })
        
        if response and response.choices and len(response.choices) > 0:
            answer = response.choices[0].message.content.strip()
            return {"success": True, "response": answer}
        else:
            return {"success": False, "error": "Empty response"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

def main():
    print("🧪 测试Azure DeepSeek等模型 (最基本配置)")
    print("=" * 50)
    
    results = {}
    
    for i, model in enumerate(models_to_test, 1):
        print(f"[{i}/{len(models_to_test)}] 测试: {model}")
        
        result = test_model(model)
        results[model] = result
        
        if result["success"]:
            print(f"✅ {model}: {result['response'][:30]}...")
        else:
            error_msg = result["error"][:50] + "..." if len(result["error"]) > 50 else result["error"]
            print(f"❌ {model}: {error_msg}")
        print()
    
    # 汇总
    success_count = sum(1 for r in results.values() if r["success"])
    print("=" * 50)
    print(f"📊 成功: {success_count}/{len(models_to_test)} 个模型")
    
    print("\n✅ 可用模型:")
    for model, result in results.items():
        if result["success"]:
            print(f"  • {model}")
    
    return results

if __name__ == "__main__":
    main()