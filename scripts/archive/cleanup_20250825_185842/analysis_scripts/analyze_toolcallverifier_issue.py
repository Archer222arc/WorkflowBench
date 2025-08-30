#!/usr/bin/env python3
"""分析为什么ToolCallVerifier识别了0个输出工具"""

import json
from pathlib import Path

# 1. 检查tool_registry文件
tool_registry_path = Path("mcp_generated_library/tool_registry_consolidated.json")
print("="*60)
print("分析ToolCallVerifier问题")
print("="*60)

if tool_registry_path.exists():
    with open(tool_registry_path, 'r') as f:
        tool_data = json.load(f)
        
    print(f"\n1. Tool Registry结构分析：")
    print(f"   顶层键: {list(tool_data.keys())}")
    
    if 'tools' in tool_data:
        tools = tool_data['tools']
        print(f"   工具数量: {len(tools)}")
        
        # 检查工具格式
        if tools:
            first_tool = tools[0]
            print(f"   第一个工具的键: {list(first_tool.keys())}")
            print(f"   第一个工具名: {first_tool.get('name', 'N/A')}")
            
            # 查找包含输出关键词的工具
            output_keywords = ['write', 'export', 'save', 'output', 'generate', 'create']
            output_tools = []
            
            for tool in tools:
                tool_name = tool.get('name', '').lower()
                if any(keyword in tool_name for keyword in output_keywords):
                    output_tools.append(tool['name'])
            
            print(f"\n2. 通过关键词匹配找到的输出工具:")
            print(f"   数量: {len(output_tools)}")
            if output_tools:
                print(f"   示例: {output_tools[:10]}")
    else:
        print("   ❌ 'tools'键不存在")

# 2. 测试ToolCallVerifier
print("\n3. 测试ToolCallVerifier初始化：")

# 创建正确的tool_capabilities字典
if 'tools' in tool_data:
    # 转换为字典格式
    tool_capabilities = {tool['name']: tool for tool in tool_data['tools']}
    print(f"   创建tool_capabilities字典: {len(tool_capabilities)}个工具")
    
    # 导入并测试
    try:
        from workflow_quality_test_flawed import ToolCallVerifier
        from mcp_embedding_manager import get_embedding_manager
        
        embedding_manager = get_embedding_manager()
        
        # 创建verifier
        verifier = ToolCallVerifier(
            tool_capabilities=tool_capabilities,
            embedding_manager=embedding_manager
        )
        
        print(f"   ✅ ToolCallVerifier创建成功")
        print(f"   识别的输出工具数量: {len(verifier.output_tools)}")
        if verifier.output_tools:
            print(f"   输出工具示例: {list(verifier.output_tools)[:10]}")
        
        # 分析为什么没有识别到输出工具
        if len(verifier.output_tools) == 0:
            print("\n4. 分析为什么没有识别到输出工具：")
            
            # 检查embedding_manager
            print(f"   embedding_manager存在: {embedding_manager is not None}")
            if embedding_manager:
                print(f"   embedding_manager类型: {type(embedding_manager).__name__}")
                
                # 尝试手动搜索
                try:
                    results = embedding_manager.search("write data to file", k=5)
                    print(f"   语义搜索测试: {results}")
                except Exception as e:
                    print(f"   语义搜索失败: {e}")
            
            # 检查关键词匹配
            print("\n   手动检查关键词匹配：")
            output_keywords = ['write', 'export', 'save', 'output', 'generate', 'create']
            matched = 0
            for tool_name in tool_capabilities.keys():
                if any(keyword in tool_name.lower() for keyword in output_keywords):
                    matched += 1
                    if matched <= 5:
                        print(f"     - {tool_name}")
            print(f"   总共匹配: {matched}个工具")
            
    except Exception as e:
        print(f"   ❌ 错误: {e}")
        import traceback
        traceback.print_exc()