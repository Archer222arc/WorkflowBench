#!/usr/bin/env python3
"""
基于人类可读TXT文件的AI分类器
读取save-logs系统产生的TXT文件进行错误分类
"""

import json
import logging
import time
import random
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

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


class TxtBasedAIClassifier:
    """基于TXT文件的AI分类器"""
    
    def __init__(self, model_name: str = "gpt-5-nano", max_retries: int = 3, base_delay: float = 1.0):
        """
        初始化基于TXT的AI分类器
        
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
            
            logger.info(f"TXT-based AI classifier initialized with {model_name}" + 
                       (" (parameter-filtered)" if self.is_gpt5_nano else ""))
        except Exception as e:
            logger.error(f"Failed to initialize TXT-based AI classifier: {e}")
            self.client = None
            self.is_gpt5_nano = False
    
    def classify_from_txt_file(self, txt_file_path: Path) -> Tuple[StandardErrorType, str, float]:
        """
        基于TXT文件内容进行错误分类
        
        Args:
            txt_file_path: TXT日志文件路径
            
        Returns:
            (错误类型, 分析原因, 置信度)
        """
        if not txt_file_path.exists():
            logger.warning(f"TXT file not found: {txt_file_path}")
            return StandardErrorType.OTHER, "TXT file not found", 0.0
        
        try:
            # 读取TXT文件内容
            txt_content = txt_file_path.read_text(encoding='utf-8')
            
            # 先进行快速规则检查
            quick_result = self._quick_rule_check_from_txt(txt_content)
            if quick_result:
                return quick_result
            
            # 使用AI进行深度分析
            if self.client:
                return self._ai_classify_from_txt_with_retry(txt_content)
            else:
                return self._fallback_classify_from_txt(txt_content)
                
        except Exception as e:
            logger.error(f"Failed to read or process TXT file: {e}")
            return StandardErrorType.OTHER, f"Failed to process TXT file: {str(e)}", 0.0
    
    def classify_from_txt_content(self, txt_content: str) -> Tuple[StandardErrorType, str, float]:
        """
        print(f"[AI_CLASSIFIER_DEBUG] classify_from_txt_content called")
        print(f"  - txt_content length: {len(txt_content) if txt_content else 0}")
        print(f"  - client available: {self.client is not None}")
        
        基于TXT内容进行错误分类（不从文件读取）
        
        Args:
            txt_content: TXT格式的日志内容
            
        Returns:
            (错误类型, 分析原因, 置信度)
        """
        # 跳过快速规则检查，直接使用AI进行深度分析
        # 这样可以避免简单关键词匹配的误判
        # quick_result = self._quick_rule_check_from_txt(txt_content)
        # if quick_result:
        #     return quick_result
        
        print(f"[AI_CLASSIFIER] 直接使用AI分析完整交互记录（跳过规则匹配）")
        
        # 使用AI进行深度分析
        if self.client:
            return self._ai_classify_from_txt_with_retry(txt_content)
        else:
            return self._fallback_classify_from_txt(txt_content)
    
    def _quick_rule_check_from_txt(self, txt_content: str) -> Optional[Tuple[StandardErrorType, str, float]]:
        """基于TXT内容的快速规则检查"""
        txt_lower = txt_content.lower()
        
        # 超时错误
        if any(keyword in txt_lower for keyword in ['timeout', 'time out', 'timed out', 'execution timeout']):
            return StandardErrorType.TIMEOUT, "Timeout detected in TXT log", 0.95
        
        # 格式错误
        if any(keyword in txt_lower for keyword in ['format error', 'json parse', 'invalid syntax', 'parsing error']):
            return StandardErrorType.TOOL_CALL_FORMAT, "Format error detected in TXT log", 0.90
        
        # 最大轮次错误
        if 'max turns exceeded' in txt_lower or 'maximum iterations' in txt_lower:
            return StandardErrorType.MAX_TURNS, "Maximum turns exceeded in TXT log", 0.85
        
        return None
    
    def _ai_classify_from_txt_with_retry(self, txt_content: str) -> Tuple[StandardErrorType, str, float]:
        """基于TXT内容的AI分类（带重试）"""
        for attempt in range(self.max_retries):
            try:
                return self._ai_classify_from_txt(txt_content)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"AI classification failed after {self.max_retries} attempts: {e}")
                    return self._fallback_classify_from_txt(txt_content)
                else:
                    delay = self.base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"AI classification attempt {attempt + 1} failed, retrying in {delay:.2f}s: {e}")
                    time.sleep(delay)
    
    def _ai_classify_from_txt(self, txt_content: str) -> Tuple[StandardErrorType, str, float]:
        """基于TXT内容的AI分类"""
        
        # 截取关键部分（避免内容过长）
        # 优先保留错误信息、执行结果、最后的对话轮次
        lines = txt_content.split('\n')
        
        # 提取关键部分
        error_section = []
        result_section = []
        conversation_section = []
        
        for i, line in enumerate(lines):
            if 'ERROR' in line or 'Error' in line or 'error' in line:
                # 包含错误行及其前后各2行
                start = max(0, i-2)
                end = min(len(lines), i+3)
                error_section.extend(lines[start:end])
            elif 'Execution Result' in line or 'Final Score' in line:
                # 包含结果部分
                start = i
                end = min(len(lines), i+10)
                result_section = lines[start:end]
            elif 'Round' in line and 'Human:' in line:
                # 保留最后的几轮对话
                start = i
                end = min(len(lines), i+20)
                conversation_section = lines[start:end]
        
        # 组合关键内容（限制总长度）
        key_content = []
        
        # 添加头部信息（前20行）
        key_content.extend(lines[:20])
        key_content.append("\n[...]\n")
        
        # 添加错误相关内容
        if error_section:
            key_content.append("\n=== Error Context ===")
            key_content.extend(error_section[-30:])  # 最多30行错误相关内容
        
        # 添加结果部分
        if result_section:
            key_content.append("\n=== Execution Result ===")
            key_content.extend(result_section)
        
        # 添加最后的对话
        if conversation_section:
            key_content.append("\n=== Last Conversation ===")
            key_content.extend(conversation_section[-30:])  # 最后30行对话
        
        # 不限制内容长度 - 使用完整内容
        condensed_content = txt_content  # 直接使用完整的原始TXT内容
        
        # 构建分析提示
        analysis_prompt = f"""
作为工作流测试专家，请分析以下测试日志，识别被测试模型（AI）的错误行为并分类。

## 极其重要的区分
1. **工具返回的TIMEOUT/错误**（如"Result: FAILED - TIMEOUT: Operation timed out"）
   - 这是测试环境模拟的工具失败，不是AI的timeout错误
   - 工具返回TIMEOUT是对AI的挑战，看AI如何处理
   - 如果AI没有正确处理这种工具失败 → tool_selection_errors或sequence_order_errors

2. **AI模型本身的超时**（真正的timeout_errors）
   - "Test timeout after 10 minutes" - 整个测试超时
   - "API timeout after 120 seconds" - API调用超时
   - "No response - timeout after X minutes" - AI无响应超时
   - 只有这些才应该分类为timeout_errors

## 日志内容
{condensed_content}

## 标准错误类型定义（针对AI模型的行为）
1. tool_call_format_errors - AI生成的工具调用格式错误、JSON解析失败、参数格式不正确
2. timeout_errors - **仅限AI模型本身超时**：API调用超时、测试执行超时、AI无响应
3. max_turns_errors - AI使用了过多交互轮次（超过10轮）
4. tool_selection_errors - AI选择了错误/不合适的工具，或在工具失败后没有选择合适的替代方案
5. parameter_config_errors - AI提供了错误的工具参数值或配置
6. sequence_order_errors - AI的工具执行顺序错误，或没有正确处理前序工具的失败
7. dependency_errors - AI没有正确处理工具间的依赖关系
8. other_errors - AI的其他错误行为（无法归类到上述类别）

## 关键判断规则
- 看到"Result: FAILED - TIMEOUT"等工具返回的错误 → 检查AI是否正确处理了工具失败
- 看到"Test timeout"、"API timeout"、"No response"等 → 这才是timeout_errors
- 工具返回PERMISSION_DENIED后AI没有重试或选择替代方案 → tool_selection_errors
- AI在依赖工具失败后继续执行后续工具 → sequence_order_errors
- AI重复执行相同的失败操作 → tool_selection_errors
- AI成功完成了任务（即使有工具失败） → 不应该有错误分类

## 特别注意
- 如果最终结果是"[ASSISTED] Task received X format helps, final result: full_success"
  说明AI在辅助下成功完成了任务，主要问题是格式错误 → tool_call_format_errors
- 如果看到多次"[FORMAT_ERROR]" → tool_call_format_errors
- 如果看到"[COMPLETION] Task marked as completed" → AI成功完成，检查是否有格式问题

请仔细分析AI模型的行为（不是工具的错误），返回JSON格式:
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
                # gpt-5-nano的请求格式（不支持temperature参数）
                # 注意：gpt-5-nano会使用一部分tokens进行内部推理(reasoning_tokens)
                # 不设置max_completion_tokens限制，让模型自由使用所需的tokens
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": analysis_prompt}]
                    # 不设置max_completion_tokens，不限制token数量
                    # temperature参数已移除 - gpt-5-nano只支持默认值1
                )
            else:
                # 标准API格式
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": analysis_prompt}],
                    max_tokens=500,
                    temperature=0.1
                )
            
            response_text = response.choices[0].message.content.strip() if response.choices[0].message.content else ""
            
            # 解析AI响应
            return self._parse_ai_response(response_text, txt_content)
            
        except Exception as e:
            logger.error(f"AI model call failed: {e}")
            return self._fallback_classify_from_txt(txt_content)
    
    def _parse_ai_response(self, response_text: str, txt_content: str) -> Tuple[StandardErrorType, str, float]:
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
                        # 返回标准错误类型名称，而不是reasoning文本
                        return error_type, error_type.value, min(max(confidence, 0.1), 1.0)
                
                # 如果没有匹配到，返回other_errors
                return StandardErrorType.OTHER, StandardErrorType.OTHER.value, confidence
            else:
                # 处理非JSON响应
                return self._extract_from_text_response(response_text, txt_content)
                
        except json.JSONDecodeError:
            return self._extract_from_text_response(response_text, txt_content)
        except Exception as e:
            logger.warning(f"Failed to parse AI response: {e}")
            return self._fallback_classify_from_txt(txt_content)
    
    def _extract_from_text_response(self, text: str, txt_content: str) -> Tuple[StandardErrorType, str, float]:
        """从文本响应中提取分类结果"""
        text_lower = text.lower()
        
        # 基于关键词匹配 - 返回标准错误类型名称
        if any(keyword in text_lower for keyword in ['format', 'json', 'parse']):
            return StandardErrorType.TOOL_CALL_FORMAT, StandardErrorType.TOOL_CALL_FORMAT.value, 0.7
        elif any(keyword in text_lower for keyword in ['timeout', 'time']):
            return StandardErrorType.TIMEOUT, StandardErrorType.TIMEOUT.value, 0.7
        elif any(keyword in text_lower for keyword in ['turns', 'max', 'limit']):
            return StandardErrorType.MAX_TURNS, StandardErrorType.MAX_TURNS.value, 0.7
        elif any(keyword in text_lower for keyword in ['tool', 'selection', 'wrong']):
            return StandardErrorType.TOOL_SELECTION, StandardErrorType.TOOL_SELECTION.value, 0.7
        elif any(keyword in text_lower for keyword in ['parameter', 'config', 'argument']):
            return StandardErrorType.PARAMETER_CONFIG, StandardErrorType.PARAMETER_CONFIG.value, 0.7
        elif any(keyword in text_lower for keyword in ['sequence', 'order']):
            return StandardErrorType.SEQUENCE_ORDER, StandardErrorType.SEQUENCE_ORDER.value, 0.7
        elif any(keyword in text_lower for keyword in ['dependency', 'depend']):
            return StandardErrorType.DEPENDENCY, StandardErrorType.DEPENDENCY.value, 0.7
        else:
            return StandardErrorType.OTHER, StandardErrorType.OTHER.value, 0.5
    
    def _fallback_classify_from_txt(self, txt_content: str) -> Tuple[StandardErrorType, str, float]:
        """基于TXT内容的回退分类逻辑"""
        txt_lower = txt_content.lower()
        
        # 基于内容的简单分类
        if 'timeout' in txt_lower:
            return StandardErrorType.TIMEOUT, "Fallback: timeout detected in TXT", 0.6
        elif any(keyword in txt_lower for keyword in ['format', 'json', 'parse']):
            return StandardErrorType.TOOL_CALL_FORMAT, "Fallback: format error detected", 0.6
        elif 'max turns' in txt_lower or 'maximum' in txt_lower:
            return StandardErrorType.MAX_TURNS, "Fallback: max turns exceeded", 0.5
        else:
            return StandardErrorType.OTHER, "Fallback: could not determine specific error type", 0.4
    
    def is_available(self) -> bool:
        """检查分类器是否可用"""
        return self.client is not None