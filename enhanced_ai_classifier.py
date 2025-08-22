#\!/usr/bin/env python3
"""
增强的AI分类器 - 使用完整交互日志进行错误分类
相比focused_ai_classifier.py，这个版本使用完整的log_data而不是有限的上下文
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


class EnhancedAIClassifier:
    """增强的AI分类器 - 使用完整交互日志"""
    
    def __init__(self, model_name: str = "gpt-5-nano", max_retries: int = 3, base_delay: float = 1.0):
        """初始化增强的AI分类器"""
        self.model_name = model_name
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.client = None
        
        try:
            from api_client_manager import get_client_for_model
            self.client = get_client_for_model(model_name)
            self.is_gpt5_nano = getattr(self.client, 'is_gpt5_nano', False)
            logger.info(f"Enhanced AI classifier initialized with {model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize enhanced AI classifier: {e}")
            self.client = None
            self.is_gpt5_nano = False
    
    def classify_error_from_log(self, log_data: Dict, error_message: str = None) -> Tuple[StandardErrorType, str, float]:
        """
        从完整交互日志分类错误
        
        Args:
            log_data: 完整的交互日志数据
            error_message: 可选的错误消息
            
        Returns:
            (错误类型, 分析原因, 置信度)
        """
        # 先进行快速规则检查
        rule_result = self._quick_rule_check_from_log(log_data, error_message)
        if rule_result:
            return rule_result
        
        # 使用AI进行深度分析
        if self.client:
            return self._ai_classify_with_full_log(log_data, error_message)
        else:
            return self._fallback_classify_from_log(log_data, error_message)
    
    def _quick_rule_check_from_log(self, log_data: Dict, error_message: str = None) -> Optional[Tuple[StandardErrorType, str, float]]:
        """基于完整日志的快速规则检查"""
        
        # 首先检查执行时间超时
        execution_time = log_data.get('execution_time', 0)
        error_type = log_data.get('error_type', '')
        
        # 检查超时情况：执行时间达到超时阈值(600秒)或error_type为timeout
        if execution_time >= 600 or error_type == 'timeout':
            return StandardErrorType.TIMEOUT, f"Test timeout - execution time: {execution_time}s", 0.98
        
        # 检查错误消息中的超时关键词
        if error_message and any(keyword in error_message.lower() for keyword in 
                               ['timeout', 'timed out', 'time limit', 'execution timeout']):
            return StandardErrorType.TIMEOUT, "Timeout detected in error message", 0.95
        
        # 检查对话历史中的格式帮助信息
        conversation = log_data.get('conversation_history', [])
        has_format_help = any(
            entry.get('type') == 'format_help' or 'format_help' in entry.get('content', '') 
            for entry in conversation
        )
        
        if has_format_help:
            return StandardErrorType.TOOL_CALL_FORMAT, "Format help provided during conversation - clear format error", 0.95
        
        # 检查是否有格式问题标记
        has_format_issue = any(
            entry.get('format_issue', False) 
            for entry in conversation
        )
        
        if has_format_issue:
            return StandardErrorType.TOOL_CALL_FORMAT, "Format issue detected in conversation history", 0.90
        
        # 分析工具调用模式
        tool_calls = [entry for entry in conversation if '<tool_call>' in entry.get('content', '')]
        if len(tool_calls) == 0:
            # 没有任何工具调用尝试
            if error_message and any(keyword in error_message.lower() for keyword in 
                                   ['connection', 'network', 'api error']):
                return StandardErrorType.OTHER, "No tool calls due to environment issue", 0.85
            else:
                # 可能是真正的格式问题，但需要AI进一步分析
                return None
        
        # 检查超时相关的明确错误
        if error_message:
            error_lower = error_message.lower()
            if ('test timeout after' in error_lower and 'seconds' in error_lower):
                return StandardErrorType.TIMEOUT, "Agent execution timeout detected", 0.98
        
        return None  # 需要AI深度分析
    
    def _ai_classify_with_full_log(self, log_data: Dict, error_message: str = None) -> Tuple[StandardErrorType, str, float]:
        """使用完整日志的AI分类"""
        
        for attempt in range(self.max_retries + 1):
            try:
                prompt = self._build_enhanced_prompt(log_data, error_message)
                
                messages = [{"role": "user", "content": prompt}]
                
                if self.is_gpt5_nano:
                    response = self.client.chat.completions.create(
                        messages=messages,
                        model=self.model_name
                    )
                else:
                    response = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=messages,
                        temperature=0.1,
                        max_tokens=500
                    )
                
                result_text = response.choices[0].message.content
                
                if not result_text or result_text.strip() == "":
                    logger.warning(f"Empty response from {self.model_name}")
                    return self._fallback_classify_from_log(log_data, error_message)
                
                return self._parse_enhanced_response(result_text)
                
            except Exception as e:
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"Enhanced AI classification attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s...")
                    time.sleep(delay)
                else:
                    logger.error(f"Enhanced AI classification failed after {self.max_retries + 1} attempts: {e}")
        
        return StandardErrorType.OTHER, "AI classification failed after retries", 0.1
    
    def _build_enhanced_prompt(self, log_data: Dict, error_message: str = None) -> str:
        """构建基于完整日志的增强提示"""
        
        task_info = log_data.get('task_instance', {})
        conversation = log_data.get('conversation_history', [])
        required_tools = task_info.get('required_tools', [])
        
        # 分析对话历史
        conversation_summary = self._analyze_conversation(conversation)
        
        # 分析工具执行情况
        execution_analysis = self._analyze_tool_execution(conversation, required_tools)
        
        # 添加执行时间和超时相关信息
        execution_time = log_data.get('execution_time', 0)
        error_type = log_data.get('error_type', '')
        
        # 构建执行时间分析
        execution_time_analysis = self._analyze_execution_time(execution_time, error_type)
        
        prompt = f"""You are an expert AI workflow analyzer. Analyze this complete interaction log to classify the PRIMARY agent error.

**TASK CONTEXT:**
- Task: {task_info.get('description', 'Unknown task')}
- Required Tools: {', '.join(required_tools)}
- Error Message: {error_message or 'No explicit error message'}

**EXECUTION TIME ANALYSIS:**
{execution_time_analysis}

**INTERACTION ANALYSIS:**
{conversation_summary}

**TOOL EXECUTION ANALYSIS:**
{execution_analysis}

**COMPLETE CONVERSATION LOG:**
```json
{json.dumps(conversation, indent=2)}
```

**CLASSIFY INTO ONE OF THESE 5 ERROR TYPES:**

1. **timeout_errors** - Test execution exceeded time limit
   - Total execution time ≥ 600 seconds (10 minutes)
   - Agent was terminated due to timeout
   - Look for execution_time ≥ 600s or error_type='timeout'

2. **tool_selection_errors** - Agent chose WRONG tool
   - Selected inappropriate tool when correct tool was available
   - Used wrong tool for the task requirements
   
3. **parameter_config_errors** - Agent provided WRONG parameters  
   - Wrong parameters or arguments by agent
   - Missing required parameters
   
4. **sequence_order_errors** - Agent executed tools in WRONG ORDER
   - Ignored logical workflow dependencies
   - Executed tools out of sequence
   
5. **dependency_errors** - Agent failed DEPENDENCY requirements
   - Used Tool B when Tool A wasn't ready
   - Workflow design ignored dependencies

**IMPORTANT RULES:**
- If the issue is environment/API problems (timeouts, network errors) → classify as "other_errors"
- If agent made correct decisions but tools failed → classify as "other_errors"  
- Only classify as agent error if the AGENT made wrong decisions
- Focus on the PRIMARY agent decision error

**Response Format (JSON only):**
{{
  "category": "exact_category_name",
  "reason": "specific agent decision error identified from the complete log analysis",
  "confidence": 0.85
}}"""
        
        return prompt
    
    def _analyze_conversation(self, conversation: List[Dict]) -> str:
        """分析对话历史"""
        if not conversation:
            return "- No conversation history available"
        
        analysis = []
        tool_calls = []
        format_issues = []
        
        for entry in conversation:
            content = entry.get('content', '')
            turn = entry.get('turn', 0)
            
            if '<tool_call>' in content:
                tool_calls.append(f"Turn {turn}: {content}")
            
            if entry.get('format_issue') or entry.get('type') == 'format_help':
                format_issues.append(f"Turn {turn}: Format issue detected")
        
        analysis.append(f"- Total conversation turns: {len(conversation)}")
        
        if tool_calls:
            analysis.append(f"- Tool call attempts: {len(tool_calls)}")
            analysis.extend(f"  {call}" for call in tool_calls[:3])  # Show first 3
        else:
            analysis.append("- No tool call attempts found")
        
        if format_issues:
            analysis.append(f"- Format issues detected: {len(format_issues)}")
            analysis.extend(f"  {issue}" for issue in format_issues)
        
        return "\n".join(analysis)
    
    def _analyze_tool_execution(self, conversation: List[Dict], required_tools: List[str]) -> str:
        """分析工具执行情况"""
        executed_tools = []
        successful_tools = []
        
        for entry in conversation:
            if entry.get('role') == 'user' and '✅' in entry.get('content', ''):
                # 成功执行的工具
                content = entry.get('content', '')
                for tool in required_tools:
                    if tool in content:
                        executed_tools.append(tool)
                        successful_tools.append(tool)
                        break
        
        analysis = []
        analysis.append(f"- Required tools: {len(required_tools)} ({', '.join(required_tools)})")
        analysis.append(f"- Successfully executed: {len(successful_tools)} ({', '.join(successful_tools)})")
        
        missing_tools = set(required_tools) - set(successful_tools)
        if missing_tools:
            analysis.append(f"- Missing tools: {', '.join(missing_tools)}")
        
        # 检查执行顺序
        if len(successful_tools) > 1:
            expected_order = required_tools[:len(successful_tools)]
            if successful_tools != expected_order:
                analysis.append(f"- Sequence issue: Expected {expected_order}, Got {successful_tools}")
        
        return "\n".join(analysis)
    
    def _analyze_execution_time(self, execution_time: float, error_type: str) -> str:
        """分析执行时间和超时情况"""
        analysis = []
        
        # 基本执行时间信息
        analysis.append(f"- Total execution time: {execution_time:.1f} seconds")
        
        if error_type:
            analysis.append(f"- Error type indicator: '{error_type}'")
        
        # 超时判断
        if execution_time >= 600:
            analysis.append(f"⚠️ TIMEOUT DETECTED: Execution time ({execution_time:.1f}s) ≥ 600s threshold")
            analysis.append("  → This strongly indicates a timeout error")
            analysis.append("  → Agent likely exceeded maximum allowed execution time")
        elif execution_time >= 500:
            analysis.append(f"⚠️ NEAR TIMEOUT: Execution time ({execution_time:.1f}s) approaching 600s limit")
            analysis.append("  → Consider if this indicates performance issues")
        elif execution_time >= 300:
            analysis.append(f"📊 LONG EXECUTION: Execution time ({execution_time:.1f}s) is relatively long")
            analysis.append("  → Check if agent had difficulty completing task")
        else:
            analysis.append(f"✅ NORMAL EXECUTION: Execution time ({execution_time:.1f}s) within normal range")
        
        # 错误类型建议
        if error_type == 'timeout' or execution_time >= 600:
            analysis.append("")
            analysis.append("🎯 CLASSIFICATION GUIDANCE:")
            analysis.append("   → Strong evidence for 'timeout_errors' classification")
            analysis.append("   → Agent was likely terminated due to time limit")
        
        return "\n".join(analysis)
    
    def _parse_enhanced_response(self, response_text: str) -> Tuple[StandardErrorType, str, float]:
        """解析增强AI响应"""
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
            
            if isinstance(result, str):
                # 文本响应处理
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
            
            if not isinstance(result, dict):
                return StandardErrorType.OTHER, "Invalid JSON structure", 0.1
            
            category_name = result.get('category', 'other_errors')
            reason = result.get('reason', 'No reason provided')
            confidence = float(result.get('confidence', 0.5))
            
            try:
                category = StandardErrorType(category_name)
            except ValueError:
                logger.warning(f"Unknown category from AI: {category_name}")
                category = StandardErrorType.OTHER
                confidence = 0.2
            
            return category, reason, confidence
            
        except Exception as e:
            logger.error(f"Failed to parse enhanced AI response: {e}")
            return StandardErrorType.OTHER, f"Parse error: {str(e)}", 0.1
    
    def _fallback_classify_from_log(self, log_data: Dict, error_message: str = None) -> Tuple[StandardErrorType, str, float]:
        """基于完整日志的后备分类"""
        conversation = log_data.get('conversation_history', [])
        task_info = log_data.get('task_instance', {})
        required_tools = task_info.get('required_tools', [])
        
        # 首先检查超时（与quick_rule_check保持一致）
        execution_time = log_data.get('execution_time', 0)
        error_type = log_data.get('error_type', '')
        
        if execution_time >= 600 or error_type == 'timeout':
            return StandardErrorType.TIMEOUT, f"Fallback: Test timeout - execution time: {execution_time}s", 0.9
        
        # 检查格式问题
        has_format_help = any(
            entry.get('type') == 'format_help' 
            for entry in conversation
        )
        
        if has_format_help:
            return StandardErrorType.TOOL_CALL_FORMAT, "Format help detected in conversation log", 0.8
        
        # 分析工具执行情况
        successful_tools = []
        for entry in conversation:
            if entry.get('role') == 'user' and '✅' in entry.get('content', ''):
                for tool in required_tools:
                    if tool in entry.get('content', ''):
                        successful_tools.append(tool)
                        break
        
        # 检查工具覆盖率
        if required_tools:
            coverage = len(set(successful_tools)) / len(required_tools)
            if coverage < 1.0:
                missing = set(required_tools) - set(successful_tools)
                return StandardErrorType.TOOL_SELECTION, f"Missing required tools: {', '.join(missing)}", 0.6
        
        # 检查执行顺序
        if len(successful_tools) > 1:
            expected_order = required_tools[:len(successful_tools)]
            if successful_tools != expected_order:
                return StandardErrorType.SEQUENCE_ORDER, f"Wrong execution order", 0.6
        
        return StandardErrorType.OTHER, "Could not classify from log analysis", 0.3


def test_enhanced_classifier():
    """测试增强的分类器"""
    classifier = EnhancedAIClassifier()
    
    # 模拟一个有格式问题的日志
    sample_log = {
        'task_instance': {
            'description': 'Process data with three tools',
            'required_tools': ['tool1', 'tool2', 'tool3']
        },
        'conversation_history': [
            {'role': 'assistant', 'content': 'I will complete the task', 'turn': 1},
            {'role': 'user', 'content': 'TOOL CALL FORMAT HELP - Use <tool_call>tool_name</tool_call>', 'turn': 1, 'type': 'format_help'},
            {'role': 'assistant', 'content': 'tool1 execute', 'turn': 2, 'format_issue': True}
        ]
    }
    
    category, reason, confidence = classifier.classify_error_from_log(sample_log)
    print(f"Test result: {category.value} - {reason} (confidence: {confidence:.2f})")


if __name__ == "__main__":
    test_enhanced_classifier()
