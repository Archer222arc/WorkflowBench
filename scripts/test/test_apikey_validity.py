#!/usr/bin/env python3
"""
测试IdealLab API Keys的有效性
==============================
"""

import time
from openai import OpenAI

IDEALAB_KEYS = [
    ("956c41bd0f31beaf68b871d4987af4bb", "原始Key"),
    ("3d906058842b6cf4cee8aaa019f7e77b", "新Key 1"),
    ("88a9a9010f2864bfb53996279dc6c3b9", "新Key 2")
]

IDEALAB_BASE = "https://idealab.alibaba-inc.com/api/openai/v1"

def test_api_key(api_key: str, name: str):
    """测试单个API key"""
    print(f"\n测试 {name} (...{api_key[-8:]})")
    print("-" * 40)
    
    try:
        client = OpenAI(
            api_key=api_key,
            base_url=IDEALAB_BASE
        )
        
        # 简单测试
        start = time.time()
        response = client.chat.completions.create(
            model="qwen2.5-3b-instruct",
            messages=[{"role": "user", "content": "Say 'ok'"}],
            max_tokens=5,
            temperature=0
        )
        elapsed = time.time() - start
        
        print(f"✅ 成功!")
        print(f"   响应时间: {elapsed:.2f}s")
        print(f"   响应内容: {response.choices[0].message.content}")
        
        # 测试并发能力
        print(f"\n   测试并发能力（5个请求）...")
        success = 0
        for i in range(5):
            try:
                response = client.chat.completions.create(
                    model="qwen2.5-3b-instruct",
                    messages=[{"role": "user", "content": f"Say {i}"}],
                    max_tokens=5,
                    temperature=0
                )
                success += 1
                print(f"   请求{i}: ✓")
            except Exception as e:
                print(f"   请求{i}: ✗ {str(e)[:50]}")
            time.sleep(0.2)  # 小延迟
        
        print(f"   并发测试: {success}/5 成功")
        return True
        
    except Exception as e:
        print(f"❌ 失败!")
        print(f"   错误: {str(e)}")
        return False

def main():
    print("="*60)
    print("IdealLab API Keys 有效性测试")
    print("="*60)
    
    valid_keys = []
    
    for api_key, name in IDEALAB_KEYS:
        if test_api_key(api_key, name):
            valid_keys.append((api_key, name))
    
    print("\n" + "="*60)
    print("测试结果总结")
    print("="*60)
    
    print(f"\n有效的API Keys: {len(valid_keys)}/{len(IDEALAB_KEYS)}")
    for api_key, name in valid_keys:
        print(f"  ✅ {name} (...{api_key[-8:]})")
    
    invalid_keys = [name for key, name in IDEALAB_KEYS if (key, name) not in valid_keys]
    if invalid_keys:
        print(f"\n无效的API Keys:")
        for name in invalid_keys:
            print(f"  ❌ {name}")

if __name__ == "__main__":
    main()