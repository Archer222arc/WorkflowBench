#!/usr/bin/env python3
"""测试新的IdealLab API配置"""

import sys
import time
from openai import OpenAI

def test_api_key(key, base_url, model="qwen2.5-3b-instruct"):
    """测试单个API key的可用性"""
    try:
        client = OpenAI(
            api_key=key,
            base_url=base_url,
            timeout=30.0  # 增加超时时间到30秒
        )
        
        start_time = time.time()
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hello, please respond with 'OK'"}]
            # max_tokens=10,
            # temperature=0.1
        )
        end_time = time.time()
        
        content = response.choices[0].message.content if response.choices else None
        if content:
            return True, f"成功 (响应时间: {end_time - start_time:.2f}秒)"
        else:
            return False, "响应内容为空"
    except Exception as e:
        return False, f"错误: {str(e)}"

def main():
    # 测试配置
    keys_config = [
        {
            "name": "key0 (新key，新URL)",
            "key": "3ddb1451943548a2a1f69fa2ab5a8d1f",
            "base_url": "http://39.96.211.155:8000/proxy/api/openai/v1/"
        },
        {
            "name": "key1 (原key，原URL)",
            "key": "3d906058842b6cf4cee8aaa019f7e77b",
            "base_url": "https://idealab.alibaba-inc.com/api/openai/v1"
        },
        {
            "name": "key2 (原key，原URL)",
            "key": "88a9a9010f2864bfb53996279dc6c3b9",
            "base_url": "https://idealab.alibaba-inc.com/api/openai/v1"
        }
    ]
    
    print("=" * 60)
    print("IdealLab API Keys验证测试")
    print("=" * 60)
    print()
    
    # 测试每个key
    success_count = 0
    for config in keys_config:
        print(f"测试 {config['name']}...")
        print(f"  Key: {config['key'][:10]}...")
        print(f"  URL: {config['base_url']}")
        
        success, message = test_api_key(config['key'], config['base_url'])
        
        if success:
            print(f"  ✅ {message}")
            success_count += 1
        else:
            print(f"  ❌ {message}")
        print()
    
    # 总结
    print("=" * 60)
    print(f"测试结果: {success_count}/3 keys可用")
    
    if success_count == 3:
        print("✅ 所有API keys都可用！")
        return 0
    else:
        print("⚠️ 部分API keys不可用，请检查配置")
        return 1

if __name__ == "__main__":
    sys.exit(main())