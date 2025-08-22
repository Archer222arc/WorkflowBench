#!/usr/bin/env python3
"""
测试DeepSeek API连接
"""

import os
import json
from openai import OpenAI
from smart_model_router import SmartModelRouter

# 测试模型路由
router = SmartModelRouter()
print(f"Testing DeepSeek-V3-0324 routing...")

# 获取客户端
client_info = router.get_client("DeepSeek-V3-0324")
print(f"Provider: {client_info['provider']}")
print(f"Client type: {type(client_info['client'])}")

# 尝试一个简单的API调用
client = client_info['client']
model = client_info['model']

print(f"\nTesting API call to {model}...")
try:
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Hello, respond with 'OK' only"}],
        max_tokens=10,
        temperature=0.1,
        timeout=10  # 10秒超时
    )
    print(f"✅ API call successful!")
    print(f"Response: {response.choices[0].message.content}")
except Exception as e:
    print(f"❌ API call failed: {e}")
    print(f"Error type: {type(e).__name__}")
    
# 检查配置
print("\n检查配置文件...")
with open("config/config.json", "r") as f:
    config = json.load(f)
    
if "DeepSeek-V3-0324" in config.get("model_configs", {}):
    print(f"DeepSeek-V3-0324 配置: {config['model_configs']['DeepSeek-V3-0324']}")
else:
    print("⚠️  DeepSeek-V3-0324 没有在config.json中配置")
    
# 检查环境变量
print("\n检查环境变量...")
print(f"AZURE_OPENAI_API_KEY_USER: {'已设置' if os.environ.get('AZURE_OPENAI_API_KEY_USER') else '未设置'}")
print(f"AZURE_OPENAI_ENDPOINT_USER: {os.environ.get('AZURE_OPENAI_ENDPOINT_USER', '未设置')}")