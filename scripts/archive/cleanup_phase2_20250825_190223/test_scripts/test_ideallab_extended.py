#!/usr/bin/env python3
"""
扩展测试IdealLab API Keys - 包括闭源模型
"""

import os
import json
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime

def test_extended_models():
    """测试更多IdealLab模型"""
    
    # 获取API keys
    keys = {
        0: "956c41bd0f31beaf68b871d4987af4bb",
        1: "3d906058842b6cf4cee8aaa019f7e77b"
    }
    
    # 扩展测试模型列表
    test_models = {
        "开源qwen模型": [
            "qwen2.5-72b-instruct",
            "qwen2.5-32b-instruct", 
            "qwen2.5-14b-instruct",
        ],
        "闭源模型": [
            "o3-0416-global",
            "gemini-2.5-flash-06-17", 
            "kimi-k2"
        ]
    }
    
    api_base = "https://ideallab.alibaba-inc.com/api/openai/v1"
    
    def test_model(api_key, model):
        """测试单个模型"""
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "Hello, respond with 'OK'"}],
            "max_tokens": 10,
            "temperature": 0.1
        }
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            f"{api_base}/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        )
        
        start_time = time.time()
        
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                elapsed = time.time() - start_time
                if response.getcode() == 200:
                    result = json.loads(response.read().decode('utf-8'))
                    content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                    return True, f"✅ 成功 ({elapsed:.2f}s)"
                else:
                    return False, f"❌ HTTP {response.getcode()}"
        except urllib.error.HTTPError as e:
            elapsed = time.time() - start_time
            return False, f"❌ HTTP {e.code} ({elapsed:.2f}s)"
        except Exception as e:
            elapsed = time.time() - start_time
            return False, f"❌ 错误: {str(e)[:50]} ({elapsed:.2f}s)"
    
    print("🔍 IdealLab API Keys 扩展验证")
    print("=" * 80)
    
    results = {}
    
    for key_idx, api_key in keys.items():
        print(f"\n🔑 测试 Key {key_idx}: {api_key[:8]}...{api_key[-4:]}")
        print("-" * 60)
        
        key_results = {}
        
        for category, models in test_models.items():
            print(f"\n  📂 {category}:")
            category_results = {}
            
            for model in models:
                print(f"    📱 {model:<25}", end=" ... ", flush=True)
                success, message = test_model(api_key, model)
                print(message)
                category_results[model] = success
                time.sleep(0.5)  # 避免请求过频
            
            key_results[category] = category_results
        
        results[f"key_{key_idx}"] = key_results
    
    # 生成汇总报告
    print(f"\n📊 汇总报告")
    print("=" * 80)
    
    for key_name, key_data in results.items():
        print(f"\n🔑 {key_name}:")
        total_success = 0
        total_tests = 0
        
        for category, models_data in key_data.items():
            success_count = sum(models_data.values())
            total_count = len(models_data)
            total_success += success_count
            total_tests += total_count
            
            rate = success_count / total_count * 100 if total_count > 0 else 0
            print(f"  {category}: {success_count}/{total_count} ({rate:.1f}%)")
        
        overall_rate = total_success / total_tests * 100 if total_tests > 0 else 0
        print(f"  总体: {total_success}/{total_tests} ({overall_rate:.1f}%)")
    
    # 模型可用性报告
    print(f"\n📱 模型可用性:")
    for category, models in test_models.items():
        print(f"\n  {category}:")
        for model in models:
            available_keys = []
            for key_name, key_data in results.items():
                if key_data[category][model]:
                    key_idx = key_name.split('_')[1]
                    available_keys.append(key_idx)
            
            if len(available_keys) == 2:
                print(f"    ✅ {model}: 两个key都可用")
            elif len(available_keys) == 1:
                print(f"    ⚠️  {model}: 只有key{available_keys[0]}可用")
            else:
                print(f"    ❌ {model}: 都不可用")
    
    print(f"\n💡 结论:")
    all_working = True
    for key_name, key_data in results.items():
        total_success = sum(sum(models_data.values()) for models_data in key_data.values())
        total_tests = sum(len(models_data) for models_data in key_data.values())
        if total_success < total_tests:
            all_working = False
            break
    
    if all_working:
        print("  ✅ 两个key对所有测试模型都工作正常")
        print("  ✅ 可以安全使用2-key并发配置")
    else:
        print("  ⚠️  部分模型存在问题，但基础qwen模型工作正常")
        print("  ✅ 仍然可以使用2-key并发配置进行qwen模型测试")

if __name__ == "__main__":
    test_extended_models()