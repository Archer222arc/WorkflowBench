#!/usr/bin/env python3
"""
模糊错误类型匹配器
支持多种变体和拼写错误的容错匹配
"""

import re
from typing import Optional, Tuple
from difflib import SequenceMatcher

class FuzzyErrorMatcher:
    """模糊匹配错误类型，提高容错性"""
    
    # 定义每个错误类型的所有可能变体
    ERROR_PATTERNS = {
        'timeout_errors': [
            'timeout', 'time_out', 'timed_out', 'time-out',
            'timeout_error', 'timeout_errors', 'timeouts',
            'execution_timeout', 'api_timeout', 'model_timeout',
            'response_timeout', 'task_timeout'
        ],
        'tool_selection_errors': [
            'tool_selection', 'tool-selection', 'tool selection',
            'tool_select', 'tool_choice', 'tool-choice',
            'wrong_tool', 'incorrect_tool', 'tool_error',
            'tool_selection_error', 'tool_selection_errors'
        ],
        'parameter_config_errors': [
            'parameter', 'param', 'params', 'parameter_error',
            'parameter_config', 'param_config', 'parameter-config',
            'config_error', 'configuration_error', 'arg_error',
            'argument_error', 'parameter_missing', 'param_missing',
            'parameter_config_error', 'parameter_config_errors'
        ],
        'sequence_order_errors': [
            'sequence', 'sequence_order', 'sequence-order',
            'order_error', 'ordering_error', 'step_order',
            'execution_order', 'workflow_order', 'sequence_error',
            'sequence_order_error', 'sequence_order_errors',
            'out_of_order', 'wrong_order'
        ],
        'dependency_errors': [
            'dependency', 'dependencies', 'depend', 'deps',
            'dependency_error', 'dependency_errors',
            'missing_dependency', 'unmet_dependency',
            'prerequisite_error', 'requirement_error'
        ],
        'tool_call_format_errors': [
            'format', 'formatting', 'format_error', 'format_errors',
            'tool_call_format', 'tool-call-format', 'call_format',
            'malformed', 'invalid_format', 'json_error',
            'syntax_error', 'tool_call_format_error',
            'tool_call_format_errors'
        ],
        'max_turns_errors': [
            'max_turns', 'max-turns', 'max turns',
            'turn_limit', 'turns_exceeded', 'too_many_turns',
            'max_iterations', 'iteration_limit', 'max_steps',
            'max_turns_error', 'max_turns_errors'
        ]
    }
    
    # 常见的拼写错误映射
    TYPO_CORRECTIONS = {
        'timout': 'timeout',
        'tmeout': 'timeout',
        'paramter': 'parameter',
        'paramater': 'parameter',
        'sequnce': 'sequence',
        'sequece': 'sequence',
        'dependancy': 'dependency',
        'dependecy': 'dependency',
        'formating': 'formatting',
        'formatt': 'format'
    }
    
    @classmethod
    def normalize_error_type(cls, error_type: str) -> str:
        """标准化错误类型字符串"""
        if not error_type:
            return ''
        
        # 转换为小写
        normalized = error_type.lower().strip()
        
        # 替换常见分隔符为下划线
        normalized = re.sub(r'[-\s]+', '_', normalized)
        
        # 纠正常见拼写错误
        for typo, correct in cls.TYPO_CORRECTIONS.items():
            if typo in normalized:
                normalized = normalized.replace(typo, correct)
        
        return normalized
    
    @classmethod
    def fuzzy_match(cls, error_type: str, threshold: float = 0.7) -> Tuple[Optional[str], float]:
        """
        模糊匹配错误类型
        
        Args:
            error_type: 输入的错误类型字符串
            threshold: 相似度阈值（0-1），默认0.7
            
        Returns:
            (匹配的标准错误类型, 相似度分数) 或 (None, 0) 如果没有匹配
        """
        if not error_type:
            return None, 0
        
        # 标准化输入
        normalized = cls.normalize_error_type(error_type)
        
        # 首先尝试精确匹配
        for standard_error, patterns in cls.ERROR_PATTERNS.items():
            for pattern in patterns:
                if pattern in normalized or normalized in pattern:
                    return standard_error, 1.0
        
        # 如果没有精确匹配，尝试模糊匹配
        best_match = None
        best_score = 0
        
        for standard_error, patterns in cls.ERROR_PATTERNS.items():
            for pattern in patterns:
                # 使用SequenceMatcher计算相似度
                score = SequenceMatcher(None, normalized, pattern).ratio()
                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = standard_error
        
        return best_match, best_score
    
    @classmethod
    def match_error_category(cls, ai_category: str, threshold: float = 0.7) -> Optional[str]:
        """
        匹配AI分类结果到标准错误类型
        
        Args:
            ai_category: AI分类器返回的错误类别
            threshold: 匹配阈值
            
        Returns:
            标准错误类型名称，如果无法匹配返回None
        """
        if not ai_category:
            return None
        
        # 尝试模糊匹配
        matched_type, score = cls.fuzzy_match(ai_category, threshold)
        
        if matched_type:
            print(f"[FUZZY_MATCH] '{ai_category}' -> '{matched_type}' (score: {score:.2f})")
            return matched_type
        else:
            print(f"[FUZZY_MATCH] No match for '{ai_category}' (best score below threshold)")
            return None
    
    @classmethod
    def extract_error_from_text(cls, text: str) -> Optional[str]:
        """
        从自由文本中提取错误类型
        例如：从"The error is a timeout issue"提取"timeout"
        """
        if not text:
            return None
        
        normalized = cls.normalize_error_type(text)
        
        # 查找所有可能的错误关键词
        for standard_error, patterns in cls.ERROR_PATTERNS.items():
            for pattern in patterns:
                if pattern in normalized:
                    print(f"[FUZZY_MATCH] Extracted '{standard_error}' from text")
                    return standard_error
        
        return None


# 测试函数
def test_fuzzy_matcher():
    """测试模糊匹配器"""
    test_cases = [
        # 精确匹配
        ("timeout_errors", "timeout_errors"),
        ("parameter_config_errors", "parameter_config_errors"),
        
        # 变体匹配
        ("timeout", "timeout_errors"),
        ("time-out", "timeout_errors"),
        ("param error", "parameter_config_errors"),
        
        # 拼写错误
        ("timout error", "timeout_errors"),
        ("paramter config", "parameter_config_errors"),
        ("sequnce order", "sequence_order_errors"),
        
        # 描述性文本
        ("The model timed out", "timeout_errors"),
        ("Wrong tool selection", "tool_selection_errors"),
        ("Missing parameter", "parameter_config_errors"),
        
        # 无法匹配
        ("random error", None),
        ("unknown issue", None)
    ]
    
    print("Testing Fuzzy Error Matcher:")
    print("-" * 50)
    
    for test_input, expected in test_cases:
        result = FuzzyErrorMatcher.match_error_category(test_input)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{test_input}' -> {result} (expected: {expected})")


if __name__ == "__main__":
    test_fuzzy_matcher()