#!/usr/bin/env python3
"""
基于完整交互日志的AI分类器
直接使用save-logs系统产生的完整日志数据进行错误分类
"""

import json
import logging
import time
import random
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class StandardErrorType(Enum):
    """标准的7种错误类型"""
    TOOL_CALL_FORMAT = "tool_call_format_errors"
    TIMEOUT = "timeout_errors" 
    MAX_TURNS = "max_turns_errors"
    TOOL_SELECTION = "tool_selection_errors"
    PARAMETER_CONFIG = "parameter_config_errors"
    SEQUENCE_ORDER = "sequence_order_errors"
    DEPENDENCY = "dependency_errors"
    OTHER = "other_errors"


class EnhancedLogBasedClassifier:
    """基于完整交互日志的AI分类器"""
    
    def __init__(self, model_name: str = "gpt-5-nano", max_retries: int = 3, base_delay: float = 1.0):
        """
        初始化基于日志的AI分类器
        
        Args:
            model_name: 分类模型名称
            max_retries: API调用最大重试次数
            base_delay: 基础重试延迟
        """
        self.model_name = model_name
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.client = None
        
        try:
            from api_client_manager import get_client_for_model
            self.client = get_client_for_model(model_name)
            self.is_gpt5_nano = getattr(self.client, 'is_gpt5_nano', False)
            
            logger.info(f"Enhanced log-based AI classifier initialized with {model_name}" + 
                       (" (parameter-filtered)" if self.is_gpt5_nano else ""))
        except Exception as e:
            logger.error(f"Failed to initialize enhanced log-based AI classifier: {e}")
            self.client = None
            self.is_gpt5_nano = False
    
    def classify_from_log_data(self, log_data: Dict[str, Any]) -> Tuple[StandardErrorType, str, float]:
        """
        基于完整的日志数据进行错误分类
        
        Args:
            log_data: 完整的交互日志数据（来自save-logs系统）
            
        Returns:
            (错误类型, 分析原因, 置信度)
        """
        # 先进行快速规则检查
        quick_result = self._quick_rule_check_from_log(log_data)
        if quick_result:
            return quick_result
        
        # 使用AI进行深度分析
        if self.client:
            return self._ai_classify_from_log_with_retry(log_data)
        else:
            return self._fallback_classify_from_log(log_data)
    
    def _quick_rule_check_from_log(self, log_data: Dict[str, Any]) -> Optional[Tuple[StandardErrorType, str, float]]:
        """基于日志数据的快速规则检查"""
        result = log_data.get('result', {})
        error_msg = result.get('error', '')
        
        if not error_msg:
            return None
        
        error_lower = error_msg.lower()
        
        # 超时错误
        if any(keyword in error_lower for keyword in ['timeout', 'time out', 'timed out']):
            return StandardErrorType.TIMEOUT, f"Timeout detected: {error_msg[:100]}", 0.95
        
        # 格式错误
        if any(keyword in error_lower for keyword in ['format', 'json', 'parse', 'invalid syntax']):
            return StandardErrorType.TOOL_CALL_FORMAT, f"Format error detected: {error_msg[:100]}", 0.90
        
        # 最大轮次错误
        execution_history = log_data.get('execution_history', [])
        conversation_history = log_data.get('conversation_history', [])
        if len(execution_history) >= 10 or len(conversation_history) >= 20:
            return StandardErrorType.MAX_TURNS, "Maximum turns/interactions exceeded", 0.85
        
        return None
    
    def _ai_classify_from_log_with_retry(self, log_data: Dict[str, Any]) -> Tuple[StandardErrorType, str, float]:
        """基于日志数据的AI分类（带重试）"""
        for attempt in range(self.max_retries):
            try:
                return self._ai_classify_from_log(log_data)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"AI classification failed after {self.max_retries} attempts: {e}")
                    return self._fallback_classify_from_log(log_data)
                else:
                    delay = self.base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"AI classification attempt {attempt + 1} failed, retrying in {delay:.2f}s: {e}")
                    time.sleep(delay)
    
    def _ai_classify_from_log(self, log_data: Dict[str, Any]) -> Tuple[StandardErrorType, str, float]:
        """基于完整日志数据的AI分类"""
        
        # 提取关键信息
        task_info = log_data.get('task_instance', {})
        result_info = log_data.get('result', {})
        conversation_history = log_data.get('conversation_history', [])
        execution_history = log_data.get('execution_history', [])
        extracted_tool_calls = log_data.get('extracted_tool_calls', [])
        llm_response = log_data.get('llm_response', '')
        
        # 构建分析提示
        analysis_prompt = f"""
作为工作流测试专家，请分析以下完整的测试交互日志，将错误精确分类到7种标准类型之一。

## 任务信息
- 任务类型: {log_data.get('task_type', 'Unknown')}
- 提示类型: {log_data.get('prompt_type', 'Unknown')} 
- 是否缺陷测试: {log_data.get('is_flawed', False)}
- 缺陷类型: {log_data.get('flaw_type', 'None')}
- 需要工具: {task_info.get('required_tools', [])}
- 任务描述: {task_info.get('description', 'N/A')[:200]}

## 执行结果概览
- 成功状态: {result_info.get('success', False)}
- 最终得分: {result_info.get('final_score', 0)}
- 执行时间: {result_info.get('execution_time', 0)}s
- 工作流得分: {result_info.get('workflow_score', 0)}
- Phase2得分: {result_info.get('phase2_score', 0)}
- 错误信息: {result_info.get('error', 'None')[:300]}

## 对话历史 ({len(conversation_history)} 轮)
{json.dumps(conversation_history[-3:], indent=2, ensure_ascii=False)[:1000] if conversation_history else "无对话历史"}

## 工具调用序列
提取的工具调用: {extracted_tool_calls[:5]}  
执行历史条数: {len(execution_history)}

## LLM响应样本
{str(llm_response)[:500] if llm_response else "无LLM响应"}

## 标准错误类型定义
1. tool_call_format_errors - 工具调用格式错误、JSON解析失败
2. timeout_errors - 执行超时
3. max_turns_errors - 超过最大交互轮次 
4. tool_selection_errors - 选择了错误的工具或不存在的工具
5. parameter_config_errors - 工具参数配置错误
6. sequence_order_errors - 工具执行顺序错误
7. dependency_errors - 工具间依赖关系错误
8. other_errors - 无法归类的其他错误

请基于完整的交互上下文分析，返回JSON格式:
{{
    "error_type": "具体的错误类型名",
    "reasoning": "详细的分析过程，解释为什么是这种错误类型",
    "confidence": 0.85,
    "key_evidence": ["关键证据1", "关键证据2"]
}}
"""

        # 调用AI模型
        try:
            if self.is_gpt5_nano:
                # gpt-5-nano的请求格式（使用max_completion_tokens）
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": analysis_prompt}],
                    max_completion_tokens=500,
                    temperature=0.1
                )
            else:
                # 标准API格式
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": analysis_prompt}],
                    max_tokens=500,
                    temperature=0.1
                )
            
            response_text = response.choices[0].message.content.strip()
            
            # 解析AI响应
            return self._parse_ai_response(response_text, log_data)
            
        except Exception as e:
            logger.error(f"AI model call failed: {e}")
            return self._fallback_classify_from_log(log_data)
    
    def _parse_ai_response(self, response_text: str, log_data: Dict[str, Any]) -> Tuple[StandardErrorType, str, float]:
        """解析AI响应"""
        try:
            # 尝试解析JSON响应
            if '{' in response_text and '}' in response_text:
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                json_part = response_text[start:end]
                parsed = json.loads(json_part)
                
                error_type_str = parsed.get('error_type', '').lower()
                reasoning = parsed.get('reasoning', 'AI classification')
                confidence = parsed.get('confidence', 0.7)
                
                # 映射错误类型
                for error_type in StandardErrorType:
                    if error_type.value.lower() in error_type_str or error_type.name.lower() in error_type_str:
                        return error_type, reasoning[:200], min(max(confidence, 0.1), 1.0)
                
                return StandardErrorType.OTHER, reasoning[:200], confidence
            else:
                # 处理非JSON响应
                return self._extract_from_text_response(response_text, log_data)
                
        except json.JSONDecodeError:
            return self._extract_from_text_response(response_text, log_data)
        except Exception as e:
            logger.warning(f"Failed to parse AI response: {e}")
            return self._fallback_classify_from_log(log_data)
    
    def _extract_from_text_response(self, text: str, log_data: Dict[str, Any]) -> Tuple[StandardErrorType, str, float]:
        """从文本响应中提取分类结果"""
        text_lower = text.lower()
        
        # 基于关键词匹配
        if any(keyword in text_lower for keyword in ['format', 'json', 'parse']):
            return StandardErrorType.TOOL_CALL_FORMAT, text[:200], 0.7
        elif any(keyword in text_lower for keyword in ['timeout', 'time']):
            return StandardErrorType.TIMEOUT, text[:200], 0.7
        elif any(keyword in text_lower for keyword in ['turns', 'max', 'limit']):
            return StandardErrorType.MAX_TURNS, text[:200], 0.7
        elif any(keyword in text_lower for keyword in ['tool', 'selection', 'wrong']):
            return StandardErrorType.TOOL_SELECTION, text[:200], 0.7
        elif any(keyword in text_lower for keyword in ['parameter', 'config', 'argument']):
            return StandardErrorType.PARAMETER_CONFIG, text[:200], 0.7
        elif any(keyword in text_lower for keyword in ['sequence', 'order']):
            return StandardErrorType.SEQUENCE_ORDER, text[:200], 0.7
        elif any(keyword in text_lower for keyword in ['dependency', 'depend']):
            return StandardErrorType.DEPENDENCY, text[:200], 0.7
        else:
            return StandardErrorType.OTHER, text[:200], 0.5
    
    def _fallback_classify_from_log(self, log_data: Dict[str, Any]) -> Tuple[StandardErrorType, str, float]:
        """基于日志数据的回退分类逻辑"""
        result_info = log_data.get('result', {})
        error_msg = result_info.get('error', '').lower()
        
        # 基于错误消息的简单分类
        if 'timeout' in error_msg:
            return StandardErrorType.TIMEOUT, "Fallback: timeout detected in error message", 0.6
        elif any(keyword in error_msg for keyword in ['format', 'json', 'parse']):
            return StandardErrorType.TOOL_CALL_FORMAT, "Fallback: format error detected", 0.6
        elif result_info.get('execution_time', 0) > 50:
            return StandardErrorType.TIMEOUT, "Fallback: execution time suggests timeout", 0.5
        else:
            return StandardErrorType.OTHER, "Fallback: could not determine specific error type", 0.4
    
    def is_available(self) -> bool:
        """检查分类器是否可用"""
        return self.client is not None