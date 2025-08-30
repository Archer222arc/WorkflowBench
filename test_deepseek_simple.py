#!/usr/bin/env python3
"""
最简单的DeepSeek API测试
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api_client_manager import APIClientManager
import time

def test():
    print("Testing DeepSeek-V3-0324...")
    
    # 获取客户端
    manager = APIClientManager()
    client = manager.get_client("DeepSeek-V3-0324")
    
    if not client:
        print("Failed to get client")
        return
    
    print("Got client, making API call...")
    
    # 简单调用
    try:
        start = time.time()
        response = client.chat.completions.create(
            model="DeepSeek-V3-0324",
            messages=[
                {"role": "user", "content": "Say 'Hello'"}
            ],
            max_tokens=10,
            timeout=30
        )
        elapsed = time.time() - start
        
        print(f"Response received in {elapsed:.2f}s")
        if response and response.choices:
            content = response.choices[0].message.content
            if not content and hasattr(response.choices[0].message, 'reasoning_content'):
                content = response.choices[0].message.reasoning_content
            print(f"Content: {content}")
        else:
            print("No response")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test()