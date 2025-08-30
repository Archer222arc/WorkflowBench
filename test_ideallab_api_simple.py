#!/usr/bin/env python3
"""简单测试IdealLab API可用性 - 不依赖openai库"""

import json
import subprocess
import sys

def test_api_key(key_name, api_key, model="qwen2.5-3b-instruct"):
    """测试单个API key"""
    print(f"\n测试 {key_name}: {api_key[:8]}...{api_key[-4:]}")
    print("-" * 40)
    
    # 使用curl测试API
    curl_cmd = f"""curl -s -X POST https://open.xiaowenai.com/v1/chat/completions \
        -H "Content-Type: application/json" \
        -H "Authorization: {api_key}" \
        -d '{{"model": "{model}", "messages": [{{"role": "user", "content": "Hi"}}], "max_tokens": 5}}'"""
    
    try:
        result = subprocess.run(curl_cmd, shell=True, capture_output=True, text=True, timeout=10)
        response = json.loads(result.stdout) if result.stdout else {}
        
        if response.get('success') == False:
            print(f"  ❌ 失败: {response.get('message', '未知错误')}")
            if 'code' in response:
                print(f"  错误代码: {response['code']}")
            if 'detailMessage' in response:
                print(f"  详细信息: {response['detailMessage']}")
            return False
        elif 'choices' in response:
            print(f"  ✅ 成功!")
            if 'usage' in response:
                print(f"  Token使用: {response['usage'].get('total_tokens', 'N/A')}")
            return True
        else:
            print(f"  ⚠️ 未知响应格式")
            print(f"  响应: {json.dumps(response, indent=2)[:200]}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"  ❌ 超时")
        return False
    except json.JSONDecodeError as e:
        print(f"  ❌ JSON解析错误: {e}")
        if result.stdout:
            print(f"  原始响应: {result.stdout[:200]}")
        return False
    except Exception as e:
        print(f"  ❌ 异常: {e}")
        return False

def main():
    print("=" * 60)
    print("IdealLab API Keys 可用性测试")
    print("=" * 60)
    
    # 定义要测试的keys
    keys = [
        ("key0", "956c41bd0f31beaf68b871d4987af4bb"),
        ("key1", "3d906058842b6cf4cee8aaa019f7e77b"),
        # ("key2", "88a9a9010f2864bfb53996279dc6c3b9")  # 已知不可用
    ]
    
    # 测试每个模型
    models_to_test = [
        "qwen2.5-3b-instruct",
        "qwen2.5-7b-instruct",
        "qwen2.5-32b-instruct"
    ]
    
    results = {}
    
    for model in models_to_test:
        print(f"\n\n🤖 测试模型: {model}")
        print("=" * 60)
        
        for key_name, api_key in keys:
            success = test_api_key(key_name, api_key, model)
            results[f"{model}_{key_name}"] = success
    
    # 总结
    print("\n\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    
    working_keys = set()
    failed_keys = set()
    
    for test, success in results.items():
        model, key = test.rsplit('_', 1)
        if success:
            working_keys.add(key)
            print(f"  ✅ {model} + {key}")
        else:
            failed_keys.add(key)
            print(f"  ❌ {model} + {key}")
    
    print("\n结论:")
    if working_keys:
        print(f"  可用的keys: {', '.join(sorted(working_keys))}")
    if failed_keys - working_keys:
        print(f"  完全不可用的keys: {', '.join(sorted(failed_keys - working_keys))}")
    
    if not working_keys:
        print("\n⚠️ 警告: 没有任何API key可用!")
        print("\n可能的原因:")
        print("  1. API keys已过期或被禁用")
        print("  2. IP地址被限制")
        print("  3. 账户余额不足")
        print("  4. API服务暂时不可用")
        
        print("\n建议:")
        print("  1. 联系IdealLab支持确认API key状态")
        print("  2. 检查账户余额和配额")
        print("  3. 尝试从不同的网络环境测试")
        print("  4. 考虑申请新的API keys")

if __name__ == "__main__":
    main()
