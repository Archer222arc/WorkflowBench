#!/usr/bin/env python3
"""
修复DeepSeek超时问题的改进方案

问题分析：
1. DeepSeek能正确使用<tool_search>但在需要<tool_call>时超时
2. 格式检测在turn<3时不触发，导致DeepSeek在第2轮就超时
3. 超时设置为120秒对DeepSeek-R1可能不够（实际测试显示可能需要更长时间）

改进方案：
1. 更早触发格式检测（从turn 1开始）
2. 为DeepSeek模型增加专门的超时配置
3. 改进错误反馈信息，明确指出格式要求
"""

def fix_interactive_executor():
    """修复interactive_executor.py中的问题"""
    
    print("修复方案：interactive_executor.py")
    print("="*60)
    
    print("\n1. 修改格式检测触发条件（第633行）：")
    print("""
原代码（第639-641行）：
        # 跳过前3轮，给模型一些学习时间
        if turn < 3:
            return False

修改为：
        # 对于DeepSeek模型，立即检测格式问题（因为容易超时）
        model_name = getattr(state, 'model_name', '').lower()
        if 'deepseek' in model_name:
            # DeepSeek从第1轮就开始检测
            if turn < 1:
                return False
        else:
            # 其他模型保持原逻辑
            if turn < 3:
                return False
    """)
    
    print("\n2. 增加更明确的格式提示（第728行）：")
    print("""
原代码（第728-731行）：
        help_msg += "I noticed you might be trying to use tools, but the format isn't correct.\\n\\n"
        help_msg += "CORRECT FORMAT for tool calls:\\n"
        help_msg += "<tool_call>tool_name</tool_call>\\n\\n"

修改为：
        help_msg += "⚠️ FORMAT ERROR: Tool call not detected.\\n\\n"
        help_msg += "You used <tool_search> correctly, but to EXECUTE tools you must use:\\n"
        help_msg += "<tool_call>tool_name</tool_call>\\n\\n"
        help_msg += "IMPORTANT: After searching for tools, you need to EXECUTE them.\\n"
        help_msg += "Example workflow:\\n"
        help_msg += "1. <tool_search>query</tool_search> - Find tools (you did this ✓)\\n"
        help_msg += "2. <tool_call>tool_name</tool_call> - Execute tool (you need to do this)\\n\\n"
    """)
    
    print("\n3. 增加DeepSeek专门的超时配置（第1200行）：")
    print("""
原代码（第1200行）：
                response = self.llm_client.chat.completions.create(**create_params, timeout=120)

修改为：
                # DeepSeek模型需要更长的超时时间
                model_name = api_model_name.lower()
                if 'deepseek-r1' in model_name:
                    timeout_seconds = 180  # DeepSeek-R1需要更长时间
                elif 'deepseek' in model_name:
                    timeout_seconds = 150  # 其他DeepSeek模型
                else:
                    timeout_seconds = 120  # 默认超时
                
                response = self.llm_client.chat.completions.create(**create_params, timeout=timeout_seconds)
                
                if 'deepseek' in model_name:
                    print(f"[INFO] Using {timeout_seconds}s timeout for {api_model_name}")
    """)
    
    print("\n4. 添加早期格式问题检测（新增函数）：")
    print("""
在第690行后添加新函数：

    def _detect_early_format_issues(self, response: str, model_name: str) -> bool:
        \"\"\"针对特定模型的早期格式问题检测\"\"\"
        if 'deepseek' not in model_name.lower():
            return False
            
        # DeepSeek特定检测
        has_tool_search = '<tool_search>' in response
        has_tool_call = '<tool_call>' in response
        
        # 如果使用了tool_search但没有tool_call，且response较长
        if has_tool_search and not has_tool_call and len(response) > 200:
            # 检查是否在描述要执行工具但没有实际调用
            execution_hints = [
                'now i will', 'next step', 'execute', 'let me use',
                'i need to', 'proceeding with', 'calling'
            ]
            
            response_lower = response.lower()
            for hint in execution_hints:
                if hint in response_lower:
                    print(f"  [EARLY_WARNING] DeepSeek may be struggling with tool_call format")
                    return True
                    
        return False
    """)
    
    print("\n5. 修改工具调用解析，增加更多格式兼容（第595行）：")
    print("""
在_parse_tool_calls函数中添加DeepSeek特殊处理：

        # 原有的正则匹配
        pattern = r'<tool_call>(.*?)</tool_call>'
        matches = re.findall(pattern, response, re.DOTALL)
        
        # 新增：对DeepSeek的特殊处理
        if not matches and 'deepseek' in getattr(self, 'current_model', '').lower():
            # 尝试其他可能的格式
            alt_patterns = [
                r'Execute: (\\w+)',  # Execute: tool_name
                r'Calling (\\w+)',   # Calling tool_name
                r'Using (\\w+) tool', # Using tool_name tool
            ]
            for alt_pattern in alt_patterns:
                alt_matches = re.findall(alt_pattern, response, re.IGNORECASE)
                if alt_matches:
                    print(f"  [INFO] DeepSeek using alternative format: {alt_pattern}")
                    matches.extend(alt_matches)
                    break
    """)

def create_improved_executor():
    """创建改进后的interactive_executor.py"""
    
    # 这里应该读取原文件并应用修改
    # 为了演示，只打印关键修改点
    
    print("\n\n完整修改文件内容：")
    print("="*60)
    print("请使用以上修改建议更新interactive_executor.py")
    print("\n关键改进点：")
    print("1. ✅ 为DeepSeek提前触发格式检测（turn >= 1）")
    print("2. ✅ 提供更明确的格式错误提示")
    print("3. ✅ 增加DeepSeek专门的超时配置（180秒）")
    print("4. ✅ 添加早期格式问题预警")
    print("5. ✅ 兼容更多工具调用格式")

if __name__ == "__main__":
    fix_interactive_executor()
    create_improved_executor()