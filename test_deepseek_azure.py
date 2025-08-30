#!/usr/bin/env python3
"""
测试DeepSeek Azure API端点的可用性和响应时间
"""

import os
import sys
import time
import json
from datetime import datetime
from openai import AzureOpenAI

def test_deepseek_model(model_name, deployment_name):
    """测试单个DeepSeek模型"""
    print(f"\n{'='*60}")
    print(f"测试模型: {model_name} (部署: {deployment_name})")
    print(f"{'='*60}")
    
    # Azure配置（从config.json提取）
    azure_config = {
        "api_key": "6Qc2Oxuf0oVtGutYCTSHOGbm1Dmn4kESwrDYeytkJsHWv3xqrnEMJQQJ99BHACHYHv6XJ3w3AAAAACOGXWza",
        "azure_endpoint": "https://85409-me3ofvov-eastus2.services.ai.azure.com",
        "api_version": "2024-02-15-preview"
    }
    
    try:
        # 创建Azure客户端
        client = AzureOpenAI(
            api_key=azure_config["api_key"],
            azure_endpoint=azure_config["azure_endpoint"],
            api_version=azure_config["api_version"]
        )
        
        # 简单的测试消息
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Hello, I am working!' in exactly 5 words."}
        ]
        
        print(f"发送测试请求...")
        start_time = time.time()
        
        # 设置不同的超时值测试
        timeout_values = [30, 60, 120]
        
        for timeout in timeout_values:
            print(f"\n尝试 {timeout} 秒超时...")
            try:
                response = client.chat.completions.create(
                    model=deployment_name,
                    messages=messages,
                    max_tokens=50,
                    temperature=0.1,
                    timeout=timeout
                )
                
                elapsed = time.time() - start_time
                print(f"✅ 成功! 响应时间: {elapsed:.2f}秒")
                
                # 显示响应内容
                content = response.choices[0].message.content
                print(f"响应内容: {content}")
                
                # 检查是否使用了reasoning_content
                if hasattr(response.choices[0].message, 'reasoning_content'):
                    reasoning = response.choices[0].message.reasoning_content
                    if reasoning:
                        print(f"推理内容: {reasoning[:100]}...")
                
                return True, elapsed
                
            except Exception as timeout_error:
                elapsed = time.time() - start_time
                if "timeout" in str(timeout_error).lower():
                    print(f"⏱️ {timeout}秒超时: {elapsed:.2f}秒后超时")
                    if timeout == timeout_values[-1]:
                        print(f"❌ 所有超时值都失败了")
                        return False, elapsed
                else:
                    print(f"❌ 其他错误: {str(timeout_error)[:200]}")
                    return False, elapsed
                    
    except Exception as e:
        print(f"❌ 初始化失败: {str(e)[:200]}")
        return False, 0

def main():
    """主测试函数"""
    print("\n" + "="*80)
    print("DeepSeek Azure API 可用性测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # 要测试的DeepSeek模型
    deepseek_models = [
        ("DeepSeek-V3-0324", "DeepSeek-V3-0324"),
        ("DeepSeek-R1-0528", "DeepSeek-R1-0528"),
        ("DeepSeek-V3-0324-2", "DeepSeek-V3-0324-2"),
        ("DeepSeek-R1-0528-2", "DeepSeek-R1-0528-2"),
    ]
    
    results = []
    
    for model_name, deployment_name in deepseek_models:
        success, response_time = test_deepseek_model(model_name, deployment_name)
        results.append({
            "model": model_name,
            "deployment": deployment_name,
            "success": success,
            "response_time": response_time
        })
        
        # 等待一下避免rate limit
        time.sleep(2)
    
    # 总结结果
    print("\n" + "="*80)
    print("测试结果总结")
    print("="*80)
    
    success_count = sum(1 for r in results if r["success"])
    total_count = len(results)
    
    print(f"\n成功率: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
    
    print("\n详细结果:")
    for result in results:
        status = "✅ 成功" if result["success"] else "❌ 失败"
        print(f"  {result['model']:25} {status} (响应时间: {result['response_time']:.2f}秒)")
    
    # 分析超时问题
    timeout_models = [r for r in results if not r["success"] and r["response_time"] > 100]
    if timeout_models:
        print(f"\n⚠️ 警告: {len(timeout_models)}个模型存在超时问题:")
        for model in timeout_models:
            print(f"  - {model['model']}: 超时 {model['response_time']:.2f}秒")
        print("\n建议:")
        print("  1. 增加超时时间到180秒或更长")
        print("  2. 检查Azure部署状态")
        print("  3. 考虑使用其他部署实例")
    
    # 保存结果到文件
    result_file = f"deepseek_azure_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump({
            "test_time": datetime.now().isoformat(),
            "results": results,
            "summary": {
                "success_count": success_count,
                "total_count": total_count,
                "success_rate": f"{success_count/total_count*100:.1f}%"
            }
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n结果已保存到: {result_file}")

if __name__ == "__main__":
    main()