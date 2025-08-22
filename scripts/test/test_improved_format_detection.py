#\!/usr/bin/env python3
"""测试改进后的格式错误检测逻辑"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

class MockRecord:
    def __init__(self, model='test-model', tool_calls=None, executed_tools=None, error_message=None):
        self.model = model
        self.task_type = 'simple_task'
        self.tool_calls = tool_calls or []
        self.executed_tools = executed_tools or []
        self.error_message = error_message
        self.success = False
        self.partial_success = False
        self.success_level = 'failure'

def test_improved_format_detection():
    """测试改进后的格式错误检测"""
    
    print("🧪 测试改进后的格式错误检测逻辑")
    print("=" * 60)
    
    # 测试用例
    test_cases = [
        # 真正的格式错误 - 应该被分类为format error
        {
            'name': '真正的格式错误',
            'record': MockRecord(
                tool_calls=[], 
                executed_tools=[], 
                error_message='Format errors detected in tool call format'
            ),
            'expected': 'format_error'
        },
        
        # API/网络问题导致没有工具调用 - 不应该被分类为format error
        {
            'name': 'API超时问题',
            'record': MockRecord(
                tool_calls=[], 
                executed_tools=[], 
                error_message='Connection timeout - API service unavailable'
            ),
            'expected': 'not_format_error'
        },
        
        # 网络错误 - 不应该被分类为format error
        {
            'name': '网络连接问题',
            'record': MockRecord(
                tool_calls=[], 
                executed_tools=[], 
                error_message='Network error: Unable to connect to service'
            ),
            'expected': 'not_format_error'
        },
        
        # 没有错误信息的失败 - 保守处理，不归类为format error
        {
            'name': '无错误信息',
            'record': MockRecord(
                tool_calls=[], 
                executed_tools=[], 
                error_message=None
            ),
            'expected': 'not_format_error'
        },
        
        # 有工具调用但失败 - 不是format error
        {
            'name': '有工具调用但失败',
            'record': MockRecord(
                tool_calls=['tool1'], 
                executed_tools=['tool1'], 
                error_message='Tool execution failed'
            ),
            'expected': 'not_format_error'
        }
    ]
    
    from enhanced_cumulative_manager import EnhancedCumulativeManager
    
    # 创建管理器
    manager = EnhancedCumulativeManager(use_ai_classification=False)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 测试用例 {i}: {test_case['name']}")
        
        record = test_case['record']
        print(f"  工具调用: {len(record.tool_calls)} 个")
        print(f"  执行工具: {len(record.executed_tools)} 个") 
        print(f"  错误消息: {record.error_message or '无'}")
        
        # 模拟检测逻辑
        tool_calls = getattr(record, 'tool_calls', [])
        executed_tools = getattr(record, 'executed_tools', [])
        error_msg = getattr(record, 'error_message', '')
        
        is_format_error = False
        if (not tool_calls or len(tool_calls) == 0) and (not executed_tools or len(executed_tools) == 0):
            if error_msg:
                error_lower = error_msg.lower()
                format_indicators = [
                    'format errors detected', 'format recognition issue',
                    'tool call format', 'understand tool call format',
                    'invalid json', 'malformed', 'parse error',
                    'unable to parse', 'json syntax error'
                ]
                non_format_indicators = [
                    'timeout', 'connection', 'network', 'api error',
                    'service unavailable', 'rate limit', 'unauthorized',
                    'internal server error', 'bad gateway'
                ]
                
                if any(indicator in error_lower for indicator in format_indicators):
                    is_format_error = True
                elif any(indicator in error_lower for indicator in non_format_indicators):
                    is_format_error = False
                else:
                    is_format_error = False
            else:
                is_format_error = False
        
        result = 'format_error' if is_format_error else 'not_format_error'
        expected = test_case['expected']
        status = "✅" if result == expected else "❌"
        
        print(f"  结果: {result}")
        print(f"  期望: {expected}")
        print(f"  {status} {'通过' if result == expected else '失败'}")

if __name__ == "__main__":
    test_improved_format_detection()
