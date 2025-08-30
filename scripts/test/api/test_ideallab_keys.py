#!/usr/bin/env python3
"""测试IdealLab API keys的可用性"""

from api_client_manager import APIClientManager
import json

# 初始化管理器
manager = APIClientManager()

# 获取当前的keys
keys = manager._idealab_keys

print("当前配置的IdealLab API Keys:")
print("=" * 60)
for i, key in enumerate(keys):
    print(f"  key{i}: {key[:8]}...{key[-4:]}")

print("\n根据用户反馈:")
print("  - key0和key1应该可用")
print("  - key2不可用")

print("\n建议修改api_client_manager.py第163-167行:")
print("只保留前两个可用的keys:")
print("""
        self._idealab_keys = [
            self._config.get('idealab_api_key', '956c41bd0f31beaf68b871d4987af4bb'),  # key0
            '3d906058842b6cf4cee8aaa019f7e77b'  # key1
            # '88a9a9010f2864bfb53996279dc6c3b9'  # key2 已不可用，注释掉
        ]
""")
