#!/usr/bin/env python3
"""
测试Azure 8540 endpoint的模型
"""

import time
from openai import AzureOpenAI

# Azure 8540 配置
AZURE_ENDPOINT = "https://85409-me3ofvov-eastus2.cognitiveservices.azure.com/"
API_KEY = "6Qc2Oxuf0oVtGutYCTSHOGbm1Dmn4kESwrDYeytkJsHWv3xqrnEMJQQJ99BHACHYHv6XJ3w3AAAAACOGXWza"
API_VERSION = "2024-12-01-preview"

# 根据你提供的deployment信息
AZURE_MODELS = {
    "DeepSeek-R1-0528": "DeepSeek-R1-0528",
    "DeepSeek-V3-0324": "DeepSeek-V3-0324", 
    "gpt-4o": "gpt-4o",
    "gpt-4o-mini": "gpt-4o-mini",
    "gpt-5-mini": "gpt-5-mini",
    "gpt-5-nano": "gpt-5-nano",
    "gpt-oss-120b": "gpt-oss-120b",
    "grok-3": "grok-3",
    "Llama-3.3-70B-Instruct": "Llama-3.3-70B-Instruct"
}

def test_azure_model(deployment_name, model_name):
    """测试单个Azure模型"""
    try:
        client = AzureOpenAI(
            api_key=API_KEY,
            api_version=API_VERSION,
            azure_endpoint=AZURE_ENDPOINT
        )
        
        start = time.time()
        response = client.chat.completions.create(
            model=deployment_name,  # 使用deployment name
            messages=[{"role": "user", "content": "1+1等于几？请简短回答。"}],
            max_tokens=20,
            temperature=0.1
        )
        
        response_time = time.time() - start
        answer = response.choices[0].message.content.strip()
        
        return {
            'success': True,
            'response': answer,
            'time': response_time,
            'model': model_name,
            'deployment': deployment_name
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'time': time.time() - start,
            'model': model_name,
            'deployment': deployment_name
        }

def main():
    print("🧪 测试Azure 8540 Endpoint的所有模型")
    print("=" * 60)
    print(f"Endpoint: {AZURE_ENDPOINT}")
    print(f"API Version: {API_VERSION}")
    print(f"模型数量: {len(AZURE_MODELS)}")
    print("=" * 60)
    
    results = []
    
    for model_name, deployment_name in AZURE_MODELS.items():
        print(f"\n[{len(results)+1}/{len(AZURE_MODELS)}] 测试: {model_name}")
        print(f"Deployment: {deployment_name}")
        print("-" * 40)
        
        result = test_azure_model(deployment_name, model_name)
        results.append(result)
        
        if result['success']:
            print(f"✅ {model_name}: 连接成功 ({result['time']:.2f}s)")
            print(f"   响应: {result['response'][:50]}...")
        else:
            print(f"❌ {model_name}: 连接失败")
            print(f"   错误: {result['error'][:100]}...")
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("📊 测试汇总")
    print("=" * 60)
    
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    print(f"✅ 成功: {len(successful)}/{len(results)} 个模型")
    print(f"❌ 失败: {len(failed)}/{len(results)} 个模型")
    
    if successful:
        print("\n✅ 可用模型:")
        for result in successful:
            print(f"  • {result['model']} ({result['time']:.2f}s)")
    
    if failed:
        print("\n❌ 不可用模型:")
        for result in failed:
            error_short = result['error'][:50] + "..." if len(result['error']) > 50 else result['error']
            print(f"  • {result['model']}: {error_short}")
    
    return results

if __name__ == "__main__":
    results = main()