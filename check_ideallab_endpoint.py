#!/usr/bin/env python3
"""检查IdealLab API endpoint配置"""

import json
from pathlib import Path

print("IdealLab API配置问题诊断")
print("=" * 60)

# 1. 检查config.json
config_path = Path('config/config.json')
with open(config_path) as f:
    config = json.load(f)

current_base = config.get('idealab_api_base', '未找到')
print(f"当前配置的API Base URL: {current_base}")
print()

# 2. 分析问题
if 'alibaba-inc.com' in current_base:
    print("❌ 问题发现：使用的是阿里内网地址")
    print("   这个地址只能在阿里内网访问，外网无法连接")
else:
    print("⚠️ 当前URL可能有问题")

print()
print("建议修改:")
print("-" * 40)
print("正确的IdealLab公网API地址应该是:")
print("  https://open.xiaowenai.com/v1")
print()
print("修改方法:")
print("1. 编辑 config/config.json")
print("2. 将 'idealab_api_base' 改为:")
print('   "idealab_api_base": "https://open.xiaowenai.com/v1"')
print()
print("或者直接运行以下命令自动修复:")
print("python3 -c \"import json; p='config/config.json'; d=json.load(open(p)); d['idealab_api_base']='https://open.xiaowenai.com/v1'; json.dump(d,open(p,'w'),indent=2)\"")
