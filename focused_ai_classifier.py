#!/usr/bin/env python3
"""
专注于现有7种错误类型的AI分类器
将未分类错误准确归类到标准错误类型中
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
    OTHER = "other_errors"  # 实在无法分类的


@dataclass
class ErrorContext:
    """错误分类上下文"""
    task_description: str
    task_type: str
    required_tools: List[str]
    executed_tools: List[str]
    is_partial_success: bool
    tool_execution_results: List[Dict[str, Any]]
    execution_time: float
    total_turns: int
    error_message: Optional[str] = None


class FocusedAIClassifier:
    """专注于标准7种错误类型的AI分类器"""
    
    def __init__(self, model_name: str = "gpt-5-nano", max_retries: int = 3, base_delay: float = 1.0):
        """
        初始化专注的AI分类器
        
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
            # 使用统一的API管理器
            from api_client_manager import get_client_for_model
            self.client = get_client_for_model(model_name)
            
            # 检查是否为gpt-5-nano (由API管理器标记)
            self.is_gpt5_nano = getattr(self.client, 'is_gpt5_nano', False)
            
            logger.info(f"Focused AI classifier initialized with {model_name}" + 
                       (" (parameter-filtered)" if self.is_gpt5_nano else ""))
        except Exception as e:
            logger.error(f"Failed to initialize focused AI classifier: {e}")
            self.client = None
            self.is_gpt5_nano = False
    
    def classify_error(self, context: ErrorContext) -> Tuple[StandardErrorType, str, float]:
        """
        分类错误到7种标准类型之一
        
        Args:
            context: 错误上下文信息
            
        Returns:
            (错误类型, 分析原因, 置信度)
        """
        # 先进行简单的规则预筛选
        if self._quick_rule_check(context):
            return self._quick_rule_check(context)
        
        # 使用AI进行细致分类
        if self.client:
            return self._ai_classify_with_retry(context)
        else:
            return self._fallback_classify(context)
    
    def _quick_rule_check(self, context: ErrorContext) -> Optional[Tuple[StandardErrorType, str, float]]:
        """快速规则检查，处理不需要AI的明确错误类型"""
        if not context.error_message:
            return None
            
        error_lower = context.error_message.lower()
        
        # 这些错误类型自动判断，不需要AI分类
        
        # 1. Agent层面的超时错误 - 只有真正的Agent超时才算
        # 注意：工具返回TIMEOUT不算Agent超时，需要AI分析
        if ('test timeout after' in error_lower and 'seconds' in error_lower) or \
           ('agent timeout' in error_lower) or \
           ('execution timeout' in error_lower):
            return StandardErrorType.TIMEOUT, "Agent timeout detected automatically", 0.98
        
        # 2. 格式错误 - 比较明确的Agent格式问题
        if any(phrase in error_lower for phrase in ['tool call format', 'unable to parse', 'format errors detected', 'invalid json', 'malformed']):
            return StandardErrorType.TOOL_CALL_FORMAT, "Tool call format issue detected automatically", 0.95
        
        # 3. 最大轮次错误 - Agent达到最大轮次限制
        if 'max turns' in error_lower and 'reached' in error_lower:
            return StandardErrorType.MAX_TURNS, "Maximum turns reached automatically", 0.95
        
        # 4. 明显的工具级错误 - 不是Agent决策错误
        tool_error_patterns = [
            'network error', 'connection timeout', 'service unavailable', 
            'api error', 'server error', 'connection refused',
            'timeout error', 'network timeout', 'request timeout'
        ]
        if any(pattern in error_lower for pattern in tool_error_patterns):
            return StandardErrorType.OTHER, "Tool-level failure, not agent decision error", 0.90
        
        return None  # 需要AI分类的复杂Agent决策错误情况
    
    def _ai_classify_with_retry(self, context: ErrorContext) -> Tuple[StandardErrorType, str, float]:
        """使用AI进行分类，带重试机制"""
        for attempt in range(self.max_retries + 1):
            try:
                # 构建专门的分类提示
                prompt = self._build_focused_prompt(context)
                
                # 构建API调用参数
                messages = [{"role": "user", "content": prompt}]
                
                if self.is_gpt5_nano:
                    # gpt-5-nano：只使用基本参数
                    response = self.client.chat.completions.create(
                        messages=messages,
                        model=self.model_name
                    )
                else:
                    # 其他模型：使用完整参数
                    response = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=messages,
                        temperature=0.1,
                        max_tokens=300
                    )
                
                result_text = response.choices[0].message.content
                
                # 检查空响应
                if not result_text or result_text.strip() == "":
                    logger.warning(f"Empty response from {self.model_name}, trying fallback classification")
                    return self._fallback_classify(context)
                
                # 调试输出：记录原始响应
                logger.info(f"Raw AI response (first 200 chars): {result_text[:200]}")
                
                return self._parse_focused_response(result_text)
                
            except Exception as e:
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"AI classification attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s...")
                    time.sleep(delay)
                else:
                    logger.error(f"AI classification failed after {self.max_retries + 1} attempts: {e}")
        
        # 所有重试失败，归类为other
        return StandardErrorType.OTHER, "AI classification failed after retries", 0.1
    
    def _build_focused_prompt(self, context: ErrorContext) -> str:
        """构建包含full_success标准的专门分类提示"""
        
        # 分析工具执行情况
        tool_summary = []
        successful_required = []
        for result in context.tool_execution_results:
            # 安全访问结果对象，无论是字典还是对象
            success = getattr(result, 'success', result.get('success', False)) if hasattr(result, 'get') else getattr(result, 'success', False)
            tool_name = getattr(result, 'tool', result.get('tool', 'Unknown')) if hasattr(result, 'get') else getattr(result, 'tool', 'Unknown')
            error_msg = getattr(result, 'error', result.get('error', 'Unknown')) if hasattr(result, 'get') else getattr(result, 'error', 'Unknown')
            
            status = "✓" if success else "✗"
            error_info = f" (Error: {error_msg})" if not success else ""
            tool_summary.append(f"  {status} {tool_name}{error_info}")
            
            # 记录成功的required tools
            if success and tool_name in context.required_tools:
                successful_required.append(tool_name)
        
        # 计算完成状态
        required_coverage = len(set(successful_required)) / len(context.required_tools) if context.required_tools else 0
        sequence_analysis = ""
        if context.required_tools:
            executed_required = [tool for tool in context.executed_tools if tool in context.required_tools]
            sequence_match = executed_required == context.required_tools[:len(executed_required)]
            sequence_analysis = f"\n- Sequence Match: {'Yes' if sequence_match else 'No'} (Expected: {' → '.join(context.required_tools)}, Got: {' → '.join(executed_required)})"
        
        # 判断为什么没达到full_success
        success_analysis = f"""
**Success Analysis:**
- Required Tools Coverage: {required_coverage:.0%} ({len(set(successful_required))}/{len(context.required_tools) if context.required_tools else 0}){sequence_analysis}
- Full Success Standard: 100% coverage + correct sequence
- Current Result: {"Partial Success" if context.is_partial_success else "Complete Failure"}"""
        
        prompt = f"""You are a workflow error classifier. Analyze why this task didn't achieve FULL SUCCESS and classify the PRIMARY AGENT decision error.

**CRITICAL DISTINCTION:**
- TOOL FAILURES (timeout, network error, API failure) are NORMAL and not agent errors
- AGENT ERRORS are wrong decisions: wrong tool choice, wrong parameters, wrong sequence, missing dependencies

**Task Context:**
- Task: {context.task_description}
- Type: {context.task_type}
- Required Tools: {', '.join(context.required_tools)}
- Executed Tools: {', '.join(context.executed_tools)}
- Error Message: {context.error_message or "No explicit error message"}

{success_analysis}

**Tool Execution Details:**
{chr(10).join(tool_summary)}

**ANALYZE FOR THESE 4 AGENT ERROR TYPES:**

1. **tool_selection_errors** - Agent chose WRONG tool for the task
   - Used image_analyzer instead of required pdf_reader
   - Used text_summarizer for numerical data analysis task
   - Selected inappropriate tool when correct tool was available
   - Example: Task needs "data_loader" but agent chose "file_reader"

2. **parameter_config_errors** - Agent provided WRONG parameters
   - Wrong file paths, invalid arguments by agent
   - Incorrect settings/configuration by agent decision
   - Agent missed required parameters for tool
   - Example: Agent called tool with wrong format specification

3. **sequence_order_errors** - Agent executed tools in WRONG ORDER
   - Agent used report_generator before data_analyzer
   - Agent processed data before loading it
   - Agent ignored logical workflow dependencies
   - Example: Required sequence "A→B→C" but agent did "A→C→B"

4. **dependency_errors** - Agent failed to handle TOOL DEPENDENCIES
   - Agent used Tool B when Tool A's output wasn't ready
   - Agent didn't wait for prerequisites
   - Agent workflow design ignored dependency requirements
   - Example: Agent called analyzer before loader completed

**IMPORTANT RULES:**
- If tools failed due to timeout/network/API issues BUT agent made correct decisions → classify as "other_errors"
- Only classify as agent error if the AGENT made a wrong decision
- Focus on WHY full success wasn't achieved due to agent choices
- Tool execution failures are not agent errors unless caused by wrong agent parameters/choices

**Response Format (JSON only):**
{{
  "category": "exact_category_name",
  "reason": "specific agent decision error identified",
  "confidence": 0.85
}}"""
        
        return prompt
    
    def _parse_focused_response(self, response_text: str) -> Tuple[StandardErrorType, str, float]:
        """解析AI响应"""
        try:
            # 提取JSON
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "{" in response_text and "}" in response_text:
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                json_str = response_text[start:end]
            else:
                json_str = response_text.strip()
            
            result = json.loads(json_str)
            
            # 确保result是字典类型 - 这里是问题的根源
            if isinstance(result, str):
                # 有时GPT-5-nano返回纯文本而不是JSON
                logger.warning(f"Got string response instead of JSON: {result[:200]}...")
                # 尝试从字符串中提取信息
                if "tool_selection" in result.lower():
                    return StandardErrorType.TOOL_SELECTION, "Inferred from text response", 0.6
                elif "parameter" in result.lower():
                    return StandardErrorType.PARAMETER_CONFIG, "Inferred from text response", 0.6
                elif "sequence" in result.lower():
                    return StandardErrorType.SEQUENCE_ORDER, "Inferred from text response", 0.6
                elif "dependency" in result.lower():
                    return StandardErrorType.DEPENDENCY, "Inferred from text response", 0.6
                else:
                    return StandardErrorType.OTHER, "Text response - could not classify", 0.3
            elif not isinstance(result, dict):
                logger.error(f"Expected dict from JSON parsing, got {type(result)}: {result}")
                return StandardErrorType.OTHER, "Invalid JSON structure - not a dict", 0.1
            
            # 安全地获取字段，避免 'str' object has no attribute 'get' 错误
            try:
                if isinstance(result, dict):
                    category_name = result.get('category', 'other_errors')
                    reason = result.get('reason', 'No reason provided')
                    confidence_raw = result.get('confidence', 0.5)
                elif isinstance(result, str):
                    logger.error(f"JSON parsing returned string instead of dict: {result[:100]}...")
                    return StandardErrorType.OTHER, "JSON parsing error - got string", 0.1
                else:
                    logger.error(f"Unexpected result type: {type(result)}, value: {result}")
                    return StandardErrorType.OTHER, "Unexpected JSON structure", 0.1
            except AttributeError as attr_e:
                logger.error(f"AttributeError accessing result fields: {attr_e}, result type: {type(result)}")
                return StandardErrorType.OTHER, f"Field access error: {str(attr_e)}", 0.1
            
            # 安全处理confidence字段
            try:
                confidence = float(confidence_raw)
            except (ValueError, TypeError):
                confidence = 0.5
            
            # 转换为StandardErrorType
            try:
                category = StandardErrorType(category_name)
            except ValueError:
                logger.warning(f"Unknown category from AI: {category_name}, defaulting to OTHER")
                category = StandardErrorType.OTHER
                confidence = 0.2
            
            return category, reason, confidence
            
        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            logger.error(f"Raw response was: {response_text}")
            return StandardErrorType.OTHER, f"Parse error: {str(e)}", 0.1
    
    def _fallback_classify(self, context: ErrorContext) -> Tuple[StandardErrorType, str, float]:
        """后备分类逻辑，理解full_success标准"""
        if not context.error_message:
            # 分析为什么没有达到full_success
            if context.required_tools:
                successful_required = []
                for result in context.tool_execution_results:
                    if result.get('success', False) and result.get('tool') in context.required_tools:
                        successful_required.append(result.get('tool'))
                
                coverage = len(set(successful_required)) / len(context.required_tools)
                
                # 检查顺序
                executed_required = [tool for tool in context.executed_tools if tool in context.required_tools]
                sequence_match = executed_required == context.required_tools[:len(executed_required)]
                
                if coverage < 1.0:
                    missing_tools = set(context.required_tools) - set(successful_required)
                    return StandardErrorType.TOOL_SELECTION, f"Missing required tools: {', '.join(missing_tools)}", 0.6
                elif not sequence_match:
                    return StandardErrorType.SEQUENCE_ORDER, f"Wrong execution order: expected {context.required_tools}, got {executed_required}", 0.6
            
            return StandardErrorType.OTHER, "No clear agent error detected", 0.2
        
        error_lower = context.error_message.lower()
        
        # 区分工具错误 vs Agent错误
        tool_error_indicators = ['timeout', 'network error', 'connection failed', 'api error', 'service unavailable']
        if any(indicator in error_lower for indicator in tool_error_indicators):
            return StandardErrorType.OTHER, "Tool execution failure, not agent decision error", 0.8
        
        # Agent决策错误匹配
        if 'parameter' in error_lower or 'argument' in error_lower:
            return StandardErrorType.PARAMETER_CONFIG, "Agent parameter configuration error detected", 0.7
        elif 'sequence' in error_lower or 'order' in error_lower:
            return StandardErrorType.SEQUENCE_ORDER, "Agent sequence order error detected", 0.7
        elif 'dependency' in error_lower or 'depend' in error_lower:
            return StandardErrorType.DEPENDENCY, "Agent dependency handling error detected", 0.7
        elif 'tool' in error_lower and ('select' in error_lower or 'wrong' in error_lower or 'choice' in error_lower):
            return StandardErrorType.TOOL_SELECTION, "Agent tool selection error detected", 0.7
        else:
            return StandardErrorType.OTHER, "Could not classify with available rules", 0.3


def test_focused_classifier():
    """测试专注的分类器"""
    classifier = FocusedAIClassifier()
    
    # 测试用例1：工具选择错误 - Agent选择了错误的工具
    context1 = ErrorContext(
        task_description="Extract text from PDF document",
        task_type="document_processing",
        required_tools=["pdf_reader", "text_extractor"],
        executed_tools=["image_analyzer", "text_extractor"],
        is_partial_success=False,
        tool_execution_results=[
            {"tool": "image_analyzer", "success": False, "error": "Cannot process PDF - expected image input"},
            {"tool": "text_extractor", "success": False, "error": "No text data available"}
        ],
        execution_time=15.2,
        total_turns=5,
        error_message="Wrong tool selection - used image_analyzer instead of pdf_reader"
    )
    
    category1, reason1, confidence1 = classifier.classify_error(context1)
    print(f"测试1 - Agent工具选择错误:")
    print(f"  分类: {category1.value}")
    print(f"  原因: {reason1}")
    print(f"  置信度: {confidence1:.2f}\n")
    
    # 测试用例2：依赖关系错误 (partial success) - 没达到full_success
    context2 = ErrorContext(
        task_description="Generate analysis report from customer data",
        task_type="data_analysis",
        required_tools=["data_loader", "analyzer", "report_generator"],
        executed_tools=["data_loader", "analyzer", "report_generator"],
        is_partial_success=True,
        tool_execution_results=[
            {"tool": "data_loader", "success": True, "error": None},
            {"tool": "analyzer", "success": True, "error": None},
            {"tool": "report_generator", "success": False, "error": "Missing analysis results - expected processed data"}
        ],
        execution_time=45.8,
        total_turns=10,
        error_message="Report generation failed: Missing analysis results from analyzer"
    )
    
    category2, reason2, confidence2 = classifier.classify_error(context2)
    print(f"测试2 - Agent依赖关系错误 (未达到full_success):")
    print(f"  分类: {category2.value}")
    print(f"  原因: {reason2}")
    print(f"  置信度: {confidence2:.2f}\n")
    
    # 测试用例3：工具失败但Agent决策正确 - 应该归类为other_errors
    context3 = ErrorContext(
        task_description="Load and process data file",
        task_type="simple_task",
        required_tools=["file_reader", "data_processor"],
        executed_tools=["file_reader", "data_processor"],
        is_partial_success=True,
        tool_execution_results=[
            {"tool": "file_reader", "success": True, "error": None},
            {"tool": "data_processor", "success": False, "error": "TIMEOUT - Service temporarily unavailable"}
        ],
        execution_time=25.3,
        total_turns=6,
        error_message="Data processing failed due to service timeout"
    )
    
    category3, reason3, confidence3 = classifier.classify_error(context3)
    print(f"测试3 - 工具失败非Agent错误 (应该是other_errors):")
    print(f"  分类: {category3.value}")
    print(f"  原因: {reason3}")
    print(f"  置信度: {confidence3:.2f}")


if __name__ == "__main__":
    test_focused_classifier()