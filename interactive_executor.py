#!/usr/bin/env python3
"""
Interactive Execution Environment for MCP Workflow System
========================================================
Enables multi-turn interaction between LLM and tools
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcp_embedding_manager import MCPEmbeddingManager
import json
import random
import time
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging
from enum import Enum

from tool_capability_manager import ToolCapabilityManager  # <- 新增这一行


logger = logging.getLogger(__name__)


class SuccessLevel(Enum):
    """任务成功级别"""
    FULL_SUCCESS = "full_success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    
    @property
    def is_success(self):
        """是否算作某种程度的成功"""
        return self in (SuccessLevel.FULL_SUCCESS, SuccessLevel.PARTIAL_SUCCESS)
    
    @property
    def score_multiplier(self):
        """评分乘数"""
        if self == SuccessLevel.FULL_SUCCESS:
            return 1.0
        elif self == SuccessLevel.PARTIAL_SUCCESS:
            return 0.6
        else:
            return 0.0

@dataclass
class ToolExecutionResult:
    """单个工具执行的结果"""
    tool_name: str
    success: bool
    output: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionState:
    """执行状态管理"""
    task_id: str
    task_type: str
    required_tools: List[str]
    executed_tools: List[str] = field(default_factory=list)
    execution_history: List[ToolExecutionResult] = field(default_factory=list)
    current_step: int = 0
    task_completed: bool = False
    total_tokens_used: int = 0
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    
    def get_progress_summary(self) -> str:
        """获取当前执行进度摘要"""
        return f"Progress: {len(self.executed_tools)} tools executed, {self.current_step} steps completed"


class InteractiveExecutor:
    """交互式执行器，支持工具搜索"""
    def __init__(self, tool_registry: Dict[str, Any], llm_client: Any = None,
                 max_turns: int = 10, success_rate: float = 0.8,
                 model: str = None, prompt_type: str = None, silent: bool = False,
                 idealab_key_index: Optional[int] = None):
        """初始化执行器
        
        Args:
            tool_registry: 工具注册表
            llm_client: LLM客户端（可选，不提供时自动获取）
            max_turns: 最大交互轮数
            success_rate: 工具执行成功率
            model: 模型名称（可选，不提供时自动获取）
            prompt_type: 提示类型（用于IdealLab API key选择）
            silent: 静默模式，禁用调试输出
            idealab_key_index: IdealLab API key索引（0-2）
        """
        self.tool_registry = tool_registry
        self.max_turns = max_turns
        self.success_rate = success_rate
        self.silent = silent
        
        # 使用api_client_manager获取客户端和模型
        if llm_client is None:
            if not self.silent:
                print("[InteractiveExecutor] No LLM client provided, initializing from api_client_manager")
            from api_client_manager import get_client_for_model, get_api_model_name
            self.model = model or "gpt-4o-mini"
            self.prompt_type = prompt_type  # 保存prompt_type
            self.llm_client = get_client_for_model(self.model, prompt_type, idealab_key_index)
            if not self.silent:
                print(f"[InteractiveExecutor] Initialized client with model: {self.model}")
                if prompt_type:
                    print(f"[InteractiveExecutor] Using prompt type: {prompt_type} for API key selection")
                print(f"[InteractiveExecutor] API model name: {get_api_model_name(self.model)}")
        else:
            # 保持向后兼容
            self.llm_client = llm_client
            if model is None:
                # 尝试从客户端获取模型名称
                from api_client_manager import APIClientManager
                manager = APIClientManager()
                manager._client = llm_client  # 临时设置客户端以获取模型名
                self.model = manager.get_model_name("gpt-4o-mini")
            else:
                self.model = model
        
        # 初始化模拟器
        self.tool_simulators = self._initialize_simulators()
        
        # 初始化嵌入管理器用于工具搜索
        self.embedding_manager = None
        self._initialize_embedding_manager()
        
        # 跟踪搜索历史
        self.search_history = []
        
        # 加载完整的工具定义（包含错误信息）
        self.full_tool_registry = self._load_full_tool_registry() 
        self.tool_capability_manager = ToolCapabilityManager()
    
    def _load_full_tool_registry(self) -> Dict[str, Any]: 
        """加载包含完整MCP protocol定义的工具注册表"""
        import json
        from pathlib import Path
        
        # 尝试多个可能的路径
        possible_paths = [
            Path("mcp_generated_library/tool_registry_consolidated.json"),
            Path("mcp_generated_library/tool_registry.json"),
            Path("tool_registry_consolidated.json"),
            Path("tool_registry.json")
        ]
        
        for path in possible_paths:
            if path.exists():
                try:
                    with open(path, 'r') as f:
                        registry = json.load(f)
                        if not self.silent:
                            print(f"[INFO] Loaded full tool registry from {path}")
                        return registry
                except Exception as e:
                    if not self.silent:
                        print(f"[WARNING] Failed to load {path}: {e}")
        
        if not self.silent:
            print("[WARNING] Could not load full tool registry, using provided registry")
        return self.tool_registry

    def _initialize_simulators(self) -> Dict[str, callable]:
        """为每类工具初始化模拟器"""
        return {
            'file_operations': self._simulate_file_operation,
            'data_processing': self._simulate_data_processing,
            'network': self._simulate_network_operation,
            'computation': self._simulate_computation,
            'integration': self._simulate_integration,
            'utility': self._simulate_utility
        }


    def _initialize_embedding_manager(self):
        """初始化嵌入管理器"""
        # 使用单例模式获取MCPEmbeddingManager
        from mcp_embedding_manager import get_embedding_manager
        self.embedding_manager = get_embedding_manager()
        
        # 尝试加载现有索引
        index_path = ".mcp_embedding_cache/tool_index.pkl"
        if os.path.exists(index_path):
            self.embedding_manager.load_index(index_path)
            if not self.silent:
                print("[INFO] Tool embedding index loaded successfully")
        else:
            if not self.silent:
                print("[WARNING] Tool embedding index not found. Tool search will be limited.")

    def _get_tool_attribute(self, tool_info: Any, attr: str, default: Any = None) -> Any:
        """
        安全地获取工具属性，兼容字典和 ToolCapability 对象

        Args:
            tool_info: 工具信息（字典或 ToolCapability 对象）
            attr: 属性名
            default: 默认值

        Returns:
            属性值或默认值
        """
        # 如果是对象，使用 getattr
        if hasattr(tool_info, attr):
            return getattr(tool_info, attr, default)
        # 如果是字典，使用 get
        elif isinstance(tool_info, dict):
            return tool_info.get(attr, default)
        else:
            return default
    
    def _evaluate_success_detailed(self, state: ExecutionState) -> Tuple[str, Dict[str, Any]]:
        """评估任务成功级别 - 详细版本"""
        
        evaluation_details = {
            'required_tools_coverage': 0.0,
            'sequence_correctness': 0.0,
            'has_output': False,
            'success_reasons': [],
            'failure_reasons': []
        }
        
        # 1. 严格检查required_tools的完成情况和顺序
        if state.required_tools:
            # 检查哪些required_tools被成功执行
            successful_required = []
            required_execution_order = []
            
            for exec_result in state.execution_history:
                if exec_result.success and exec_result.tool_name in state.required_tools:
                    successful_required.append(exec_result.tool_name)
                    if exec_result.tool_name not in required_execution_order:
                        required_execution_order.append(exec_result.tool_name)
            
            # 计算覆盖率
            coverage = len(set(successful_required)) / len(state.required_tools)
            evaluation_details['required_tools_coverage'] = coverage
            
            # 检查顺序正确性
            if len(required_execution_order) == len(state.required_tools):
                # 检查顺序是否与required_tools列表一致
                sequence_correct = required_execution_order == state.required_tools
                evaluation_details['sequence_correctness'] = 1.0 if sequence_correct else 0.0
                
                # 完全成功：所有工具成功且顺序正确
                if coverage == 1.0 and sequence_correct:
                    state.task_completed = True
                    evaluation_details['success_reasons'].append("All required tools executed in correct order")
                    return "full_success", evaluation_details
            else:
                evaluation_details['sequence_correctness'] = 0.0
        else: 
            print(state)
            raise ValueError("Execution state has no required tools defined.")
        
        # 2. 检查输出生成
        output_keywords = [
            'writer', 'export', 'save', 'output', 'post', 
            'publish', 'store', 'emit', 'notify', 'report', 
            'generate', 'filter', 'aggregator', 'compressor'
        ]
        
        for exec_result in state.execution_history:
            if exec_result.success:
                tool_lower = exec_result.tool_name.lower()
                if any(keyword in tool_lower for keyword in output_keywords):
                    evaluation_details['has_output'] = True
                    break
        
        # 3. 部分成功判定条件
        partial_success_conditions = []
        
        # 条件A：完成了大部分required_tools（>=60%）
        if state.required_tools and evaluation_details['required_tools_coverage'] >= 0.6:
            partial_success_conditions.append("Completed 60%+ of required tools")
        
        # 条件B：有输出生成
        if evaluation_details['has_output']:
            partial_success_conditions.append("Generated output")
        
        # 条件C：达到了特定任务类型的最低要求
        successful_count = sum(1 for r in state.execution_history if r.success)
        task_min_requirements = {
            'simple_task': 1,
            'basic_task': 2,
            'data_pipeline': 2,
            'api_integration': 2,
            'multi_stage_pipeline': 3
        }
        
        min_required = task_min_requirements.get(state.task_type, 2)
        if successful_count >= min_required:
            partial_success_conditions.append(f"Met minimum tool requirement ({successful_count}/{min_required})")
        
        # 条件D：有明确的完成信号
        has_completion_signal = False
        for conv in state.conversation_history:
            if conv['role'] == 'assistant' and self._check_completion_signal(conv['content']):
                has_completion_signal = True
                partial_success_conditions.append("Explicit completion signal")
                break
        
        # 判定部分成功
        if len(partial_success_conditions) >= 2:  # 至少满足2个条件
            state.task_completed = True
            evaluation_details['success_reasons'] = partial_success_conditions
            return "partial_success", evaluation_details
        
        # 4. 失败判定
        failure_reasons = []
        
        if state.required_tools:
            if evaluation_details['required_tools_coverage'] < 0.5:
                failure_reasons.append(f"Low required tools coverage: {evaluation_details['required_tools_coverage']:.0%}")
        
        if successful_count < min_required:
            failure_reasons.append(f"Insufficient tools executed: {successful_count} < {min_required}")
        
        if not evaluation_details['has_output'] and state.task_type in ['data_pipeline', 'multi_stage_pipeline']:
            failure_reasons.append("No output generated for pipeline task")
        
        evaluation_details['failure_reasons'] = failure_reasons
        return "failure", evaluation_details



    def _get_system_prompt(self) -> str:
        """获取系统提示，包含工具搜索和详情查询说明"""
        base_prompt = """You are an AI assistant executing workflow tasks in an automated testing environment. 
    Your goal is to complete the given task by using appropriate tools.

    IMPORTANT TEST ENVIRONMENT RULES:
    - This is an automated test environment with no human interaction
    - When tools require parameters, use reasonable default values
    - NEVER ask the user for input, file paths, or clarification
    - For file paths, use generic defaults like "data/input.json" or "data/output.json"
    - For URLs, use example URLs like "https://api.example.com/data"
    - For any options or formats, use sensible defaults (e.g., JSON format)

    CRITICAL EXECUTION MODE:
    - Execute ONE tool at a time
    - Wait for feedback after each tool execution before proceeding
    - Do NOT list multiple tool calls in a single response
    - After receiving feedback, decide the next action based on the results

    Tool Discovery:
    - Search for tools: <tool_search>your search query</tool_search>
    - Get tool details: <tool_info>tool_name</tool_info>

    Examples:
    - <tool_search>file reader writer</tool_search>
    - <tool_info>data_processing_aggregator</tool_info>

    Tool Execution:
    After understanding the tools, execute them using: <tool_call>tool_name</tool_call>

    IMPORTANT: Only include ONE <tool_call> per response. Wait for the execution result before proceeding.

    Guidelines:
    1. Analyze the task to understand what tools you need
    2. Search for relevant tools using descriptive queries
    3. Use tool_info to understand parameters, dependencies, and error handling
    4. Execute tools ONE AT A TIME in the logical order required by the task
    5. WAIT for feedback after each tool execution
    6. Pay attention to tool dependencies - execute dependent tools first
    7. Handle errors based on the error codes in tool info
    8. Use default values for all parameters - do not ask for user input
    9. Complete the task and indicate when finished

    Available tool categories: file_operations, data_processing, network, computation, integration, utility"""
        
        return base_prompt
    
    def execute_interactive(self, initial_prompt: str, task_instance: Dict,
                        workflow: Optional[Dict] = None, prompt_type: str = "baseline") -> Dict:
        """执行交互式工作流，支持工具搜索和详情查询"""
        # 重置搜索历史
        self.search_history = []
        
        # 创建执行状态
        state = ExecutionState(
            task_id=task_instance.get('id', 'unknown'),
            task_type=task_instance.get('task_type', 'general'),
            required_tools=task_instance.get('required_tools', [])
        )
        
        # 修改初始prompt，添加工具搜索和详情查询说明
        enhanced_prompt = self._enhance_prompt_with_search_info(initial_prompt, prompt_type)
        
        # 开始交互循环
        conversation = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": enhanced_prompt}
        ]
        
        start_time = time.time()
        
        for turn in range(self.max_turns):
            if not self.silent:
                print(f"\n[TURN {turn+1}/{self.max_turns}]")
            
            # 1. 获取LLM响应
            response = self._get_llm_response(conversation, state)
            if response is None:
                # API失败后无法继续，记录API问题并结束
                if not self.silent:
                    print(f"  [API_FAILURE] API failed (timeout or max retries)")
                if not hasattr(state, 'api_issues'):
                    state.api_issues = []
                
                # 检查state中是否有超时标记
                if hasattr(state, 'timeout_occurred') and state.timeout_occurred:
                    issue_type = 'API timeout after 120 seconds'
                    state.error_type = 'timeout'  # 设置错误类型为timeout
                else:
                    issue_type = 'API failed after max retries'
                    
                state.api_issues.append({
                    'turn': turn + 1,
                    'issue': issue_type,
                    'timestamp': datetime.now().isoformat()
                })
                break  # 结束执行，但不会被分类为工作流错误
            
            # 2. 检查是否有工具搜索请求
            search_queries = self._extract_tool_searches(response)
            if search_queries:
                # 处理工具搜索
                search_results = self._handle_tool_searches(search_queries, state)
                search_feedback = self._format_search_results(search_results)
                
                # 添加搜索结果到对话
                conversation.append({"role": "assistant", "content": response})
                conversation.append({"role": "user", "content": search_feedback})
                
                state.conversation_history.append({
                    "role": "assistant",
                    "content": response,
                    "turn": turn + 1,
                    "action": "search"
                })
                state.conversation_history.append({
                    "role": "user",
                    "content": search_feedback,
                    "turn": turn + 1
                })
                
                continue
            
            # 3. 检查是否有工具详情请求（新增）
            info_requests = self._extract_tool_info_requests(response)
            if info_requests:
                # 处理工具详情查询
                info_feedback = self._get_tool_details(info_requests, state)
                
                # 添加详情结果到对话
                conversation.append({"role": "assistant", "content": response})
                conversation.append({"role": "user", "content": info_feedback})
                
                state.conversation_history.append({
                    "role": "assistant",
                    "content": response,
                    "turn": turn + 1,
                    "action": "tool_info"
                })
                state.conversation_history.append({
                    "role": "user",
                    "content": info_feedback,
                    "turn": turn + 1
                })
                
                continue
            
            state.conversation_history.append({
                "role": "assistant",
                "content": response,
                "turn": turn + 1
            })
            
            # 4. 解析工具调用和智能格式检查
            tool_calls = self._parse_tool_calls(response)
            format_issue_detected = self._detect_tool_call_format_issues(response, tool_calls, turn, state)
            
            # 如果检测到格式问题，提供帮助并继续对话
            if format_issue_detected:
                format_help = self._generate_format_help_message(state)
                conversation.append({"role": "assistant", "content": response})
                conversation.append({"role": "user", "content": format_help})
                
                state.conversation_history.append({
                    "role": "assistant",
                    "content": response,
                    "turn": turn + 1,
                    "format_issue": True
                })
                state.conversation_history.append({
                    "role": "user",
                    "content": format_help,
                    "turn": turn + 1,
                    "type": "format_help"
                })
                
                # 记录格式错误统计
                if not hasattr(state, 'format_error_count'):
                    state.format_error_count = 0
                state.format_error_count += 1
                
                continue
            
            # 5. 检查是否完成 - 只有在执行了所有必需工具后才允许完成
            required_tools_completed = all(tool in [r.tool_name for r in state.execution_history if r.success] 
                                         for tool in state.required_tools) if state.required_tools else False
            
            if required_tools_completed and self._check_completion_signal(response):
                state.task_completed = True
                if not self.silent:
                    print(f"  [COMPLETION] Task marked as completed - all required tools executed")
                break
            elif not tool_calls and not search_queries and not info_requests and len(state.execution_history) == 0:
                # 只有在完全没有任何行动时才提前终止
                state.task_completed = False
                if not self.silent:
                    print(f"  [EARLY_EXIT] No actions taken, continuing...")
                # 不要break，继续执行
            
            # 6. 执行工具并生成反馈
            if tool_calls:
                feedback = self._execute_tools_with_feedback(tool_calls, state)
                conversation.append({"role": "assistant", "content": response})
                conversation.append({"role": "user", "content": feedback})
                
                state.conversation_history.append({
                    "role": "user", 
                    "content": feedback,
                    "turn": turn + 1
                })
            
            # 7. 检查是否应该终止
            if self._should_terminate(state):
                if not self.silent:
                    print(f"  [TERMINATION] Execution terminated (criteria met)")
                break
        
        # 评估成功（使用原有方法）
        success = self._evaluate_success(state)
        success_level, evaluation_details = self._evaluate_success_detailed(state)
        
        # 记录帮助信息用于统计（但不改变success_level）
        if hasattr(state, 'format_error_count') and state.format_error_count > 0 and not self.silent:
            print(f"[ASSISTED] Task received {state.format_error_count} format helps, final result: {success_level}")
        
        # 生成更智能的错误消息
        error_message = self._generate_intelligent_error_message(state, success_level, turn + 1)
        
        # 生成最终结果
        execution_time = time.time() - start_time
        
        return {
            'state': state,
            'success': success,  # 保持向后兼容
            'success_level': success_level,  # 新的详细级别
            'evaluation_details': evaluation_details,  # 评估细节
            'tool_calls': state.executed_tools,
            'execution_time': execution_time,
            'conversation_history': state.conversation_history,
            'execution_history': state.execution_history,
            'search_history': self.search_history,  # 添加搜索历史
            'final_outputs': self._extract_final_outputs(state),
            'output_generated': evaluation_details.get('has_output', False),
            'prompt_type': prompt_type,
            'task_id': state.task_id,
            'executed_tools': state.executed_tools,
            'turns': turn + 1,
            'task_completed': state.task_completed,
            'execution_status': success_level,  # 用success_level代替execution_status
            'evaluation': evaluation_details,  # 用evaluation_details代替evaluation
            'error_message': error_message,  # 添加智能错误消息
            'error_type': getattr(state, 'error_type', None),  # 错误类型（如timeout）
            'format_error_count': getattr(state, 'format_error_count', 0),  # 格式错误计数
            'format_issues': getattr(state, 'format_issues', []),  # 格式问题列表
            'api_issues': getattr(state, 'api_issues', [])  # API问题列表
        }
    

    def _parse_tool_calls(self, response: str) -> List[str]:
        """解析工具调用"""
        tool_calls = []
        
        # 匹配 <tool_call>...</tool_call> 格式
        pattern = r'<tool_call>(.*?)</tool_call>'
        matches = re.findall(pattern, response, re.DOTALL)
        
        for match in matches:
            tool_name = match.strip()
            if tool_name in self.tool_registry:
                tool_calls.append(tool_name)
                if not self.silent:
                    print(f"  [PARSE] Found tool call: {tool_name}")
            else:
                # 尝试模糊匹配
                matched_tool = self._fuzzy_match_tool(tool_name)
                if matched_tool:
                    tool_calls.append(matched_tool)
                    if not self.silent:
                        print(f"  [PARSE] Fuzzy matched '{tool_name}' to '{matched_tool}'")
                else:
                    if not self.silent:
                        print(f"  [PARSE] Unknown tool: {tool_name}")
        
        return tool_calls

    def _fuzzy_match_tool(self, tool_name: str) -> Optional[str]:
        """模糊匹配工具名"""
        tool_lower = tool_name.lower()
        
        # 精确匹配（忽略大小写）
        for registered_tool in self.tool_registry:
            if registered_tool.lower() == tool_lower:
                return registered_tool
        
        # 部分匹配
        for registered_tool in self.tool_registry:
            if tool_lower in registered_tool.lower() or registered_tool.lower() in tool_lower:
                return registered_tool
        
        return None
    
    def _detect_tool_call_format_issues(self, response: str, parsed_tools: List[str], turn: int, state) -> bool:
        """智能检测工具调用格式问题"""
        # 如果已经解析到工具调用，说明格式正确
        if parsed_tools:
            return False
        
        # 跳过前3轮，给模型一些学习时间
        if turn < 3:
            return False
        
        # 检测常见的错误格式模式
        format_issues = []
        
        # 1. 检测是否尝试使用工具但格式不对
        potential_tool_patterns = [
            r'use[\s\w]*tool[\s\w]*([a-zA-Z_]+)',  # "use tool xyz" or "using tool xyz"
            r'call[\s\w]*([a-zA-Z_]+)',  # "call xyz" or "calling xyz"
            r'execute[\s\w]*([a-zA-Z_]+)',  # "execute xyz"
            r'run[\s\w]*([a-zA-Z_]+)',  # "run xyz"
            r'invoke[\s\w]*([a-zA-Z_]+)',  # "invoke xyz"
            r'\b([a-zA-Z_]+)\(.*\)',  # "tool_name(params)" function call style
            r'<([a-zA-Z_]+)>',  # "<tool_name>" simple bracket style
            r'\[([a-zA-Z_]+)\]',  # "[tool_name]" square bracket style
        ]
        
        potential_tools = []
        for pattern in potential_tool_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            for match in matches:
                # 检查是否是已知工具
                tool_name = match.strip()
                if self._is_likely_tool_name(tool_name):
                    potential_tools.append(tool_name)
                    format_issues.append(f"Detected potential tool '{tool_name}' in incorrect format")
        
        # 2. 检测是否在描述工具使用但没有实际调用
        action_keywords = ['need to', 'will use', 'should use', 'let me', 'i will', 'going to']
        tool_keywords = list(self.tool_registry.keys())[:20]  # 取前20个常用工具名
        
        for action in action_keywords:
            for tool in tool_keywords:
                if action in response.lower() and tool.lower() in response.lower():
                    format_issues.append(f"Mentioned using '{tool}' but no proper tool call found")
                    potential_tools.append(tool)
                    break
        
        # 3. 如果执行历史为空且轮数较多，可能是格式问题
        if len(state.execution_history) == 0 and turn >= 5:
            format_issues.append("No tools executed after multiple turns")
        
        # 记录格式问题到状态
        if format_issues:
            if not hasattr(state, 'format_issues'):
                state.format_issues = []
            state.format_issues.extend(format_issues)
            
            print(f"  [FORMAT_ISSUE] Turn {turn+1}: {'; '.join(format_issues)}")
            if potential_tools:
                print(f"  [FORMAT_ISSUE] Potential tools detected: {potential_tools}")
            
            return True
        
        return False
    
    def _is_likely_tool_name(self, name: str) -> bool:
        """判断是否可能是工具名"""
        # 检查是否在工具注册表中
        if name in self.tool_registry:
            return True
        
        # 模糊匹配
        if self._fuzzy_match_tool(name):
            return True
        
        # 检查是否符合工具名命名规范
        if re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', name) and len(name) > 2:
            # 检查是否包含常见工具词汇
            tool_suffixes = ['er', 'or', 'manager', 'handler', 'service', 'client', 'api', 'tool']
            tool_prefixes = ['get', 'set', 'create', 'delete', 'update', 'send', 'fetch', 'parse']
            
            name_lower = name.lower()
            for suffix in tool_suffixes:
                if name_lower.endswith(suffix):
                    return True
            for prefix in tool_prefixes:
                if name_lower.startswith(prefix):
                    return True
        
        return False
    
    def _generate_format_help_message(self, state) -> str:
        """生成格式帮助消息"""
        required_tools = state.required_tools if state.required_tools else []
        
        help_msg = "\n=== TOOL CALL FORMAT HELP ===\n"
        help_msg += "I noticed you might be trying to use tools, but the format isn't correct.\n\n"
        help_msg += "CORRECT FORMAT for tool calls:\n"
        help_msg += "<tool_call>tool_name</tool_call>\n\n"
        
        if required_tools:
            help_msg += f"For this task, you need to use these tools: {', '.join(required_tools)}\n\n"
            help_msg += "EXAMPLES:\n"
            for tool in required_tools[:3]:  # Show examples for first 3 tools
                help_msg += f"<tool_call>{tool}</tool_call>\n"
        else:
            help_msg += "EXAMPLES:\n"
            sample_tools = list(self.tool_registry.keys())[:3]
            for tool in sample_tools:
                help_msg += f"<tool_call>{tool}</tool_call>\n"
        
        help_msg += "\nIMPORTANT: Use the EXACT format with angle brackets and 'tool_call' tags.\n"
        help_msg += "Please try again with the correct format.\n"
        help_msg += "=============================\n"
        
        return help_msg
    
    def _generate_intelligent_error_message(self, state, success_level: str, total_turns: int) -> Optional[str]:
        """生成智能的错误消息"""
        if success_level in ['full_success', 'partial_success']:
            return None
        
        # 如果只是遇到了API问题，不生成工作流错误消息
        if hasattr(state, 'api_issues') and state.api_issues:
            # 如果所有的失败都是由于API问题，不生成工作流错误消息
            if len(state.execution_history) == 0:
                # 没有执行任何工具且是因为API问题
                return None  # 不返回错误消息，避免被分类为工作流错误
            # 否则忽略API问题，继续分析其他错误
        
        # 分析失败原因
        if len(state.execution_history) == 0:
            # 没有执行任何工具
            if hasattr(state, 'format_error_count') and state.format_error_count > 0:
                return f"Tool call format errors detected ({state.format_error_count} times) - Model unable to use correct <tool_call>tool_name</tool_call> format"
            elif total_turns >= self.max_turns:
                return f"Max turns reached ({total_turns}) with no tool calls - Likely tool call format recognition issue"
            else:
                return f"No tool calls executed in {total_turns} turns - Model may not understand tool call format"
        
        elif len(state.execution_history) > 0:
            # 有执行但失败
            successful_tools = [r.tool_name for r in state.execution_history if r.success]
            failed_executions = [(r.tool_name, r.error) for r in state.execution_history if not r.success and r.error]
            
            # 优先返回具体的工具错误（保留原始错误信息）
            if failed_executions:
                # 首先检查是否是序列错误导致的失败
                if state.required_tools and len(state.execution_history) >= 1:
                    execution_order = [r.tool_name for r in state.execution_history]
                    
                    # 检查每个失败的工具是否因为顺序问题而失败
                    for failed_tool, error in failed_executions:
                        if failed_tool in state.required_tools and error:
                            error_lower = error.lower()
                            # 排除明确的依赖错误（DEPENDENCY_ERROR通常是系统依赖，不是工具顺序）
                            if 'dependency_error' in error_lower or 'dependency error' in error_lower:
                                continue  # 让后面的逻辑处理依赖错误
                            
                            # 如果错误暗示缺少输入（这通常是序列问题）
                            if 'no input' in error_lower or 'missing data' in error_lower or 'data not found' in error_lower:
                                # 检查这个工具是否在它的依赖之前执行了
                                tool_index = state.required_tools.index(failed_tool)
                                if tool_index > 0:
                                    # 这个工具有前置依赖
                                    required_before = state.required_tools[:tool_index]
                                    # 检查执行历史中这个工具之前是否执行了所有依赖
                                    exec_index = execution_order.index(failed_tool) if failed_tool in execution_order else -1
                                    if exec_index >= 0:
                                        executed_before = execution_order[:exec_index]
                                        missing_deps = [t for t in required_before if t not in executed_before]
                                        if missing_deps:
                                            return f"Sequence order error: {failed_tool} executed before {missing_deps[0]} - {error}"
                
                # 查找最重要的错误类型
                for tool_name, error in failed_executions:
                    if error:
                        error_lower = error.lower()
                        # 优先级1：超时错误
                        if 'timeout' in error_lower:
                            return f"{error} (tool: {tool_name})"
                        # 优先级2：依赖错误
                        elif 'dependency' in error_lower or 'depend' in error_lower:
                            return f"{error} (tool: {tool_name})"
                        # 优先级3：参数/输入错误
                        elif 'invalid' in error_lower or 'parameter' in error_lower or 'permission' in error_lower:
                            return f"{error} (tool: {tool_name})"
                
                # 如果没有匹配特定模式，返回第一个错误
                tool_name, error = failed_executions[0]
                return f"{error} (tool: {tool_name})"
            
            # 如果没有具体错误信息，使用概括性描述
            failed_tools = [r.tool_name for r in state.execution_history if not r.success]
            if not successful_tools and failed_tools:
                return f"All {len(failed_tools)} tool calls failed - Tool execution errors"
            elif state.required_tools:
                missing_tools = [t for t in state.required_tools if t not in successful_tools]
                if missing_tools:
                    # 检查是否是工具选择错误
                    if len(state.execution_history) > 0:
                        executed_tools = [r.tool_name for r in state.execution_history]
                        wrong_tools = [t for t in executed_tools if t not in state.required_tools]
                        if wrong_tools:
                            return f"Tool selection error: wrong tools used ({', '.join(wrong_tools)}) instead of required tools ({', '.join(state.required_tools)})"
                    
                    # 检查是否是序列顺序错误
                    if state.required_tools and len(successful_tools) > 0:
                        # 检查执行顺序
                        execution_order = [r.tool_name for r in state.execution_history if r.tool_name in state.required_tools]
                        if execution_order != state.required_tools[:len(execution_order)]:
                            return f"Sequence order error: tools executed in wrong order"
                    
                    return f"Required tools not completed: {', '.join(missing_tools)} - Task partially incomplete"
        
        # 默认错误消息
        return f"Task failed after {total_turns} turns - Unknown error"

    def _should_terminate(self, state: ExecutionState) -> bool:
        """检查是否应该终止执行"""
        # 检查是否所有必需工具都已尝试
        if state.required_tools:
            all_required_attempted = all(tool in state.executed_tools for tool in state.required_tools)
            if all_required_attempted:
                # 检查是否还有重试的机会
                successful_tools = {r.tool_name for r in state.execution_history if r.success}
                failed_required = [t for t in state.required_tools if t not in successful_tools]
                if failed_required:
                    print(f"  [CONTINUE] Required tools failed: {failed_required}, may retry")
                    # 不要立即终止，让系统有机会重试
                    return False
        
        # 检查是否有太多连续失败
        if len(state.execution_history) >= 5:
            recent_failures = sum(1 for r in state.execution_history[-5:] if not r.success)
            if recent_failures >= 5:
                print(f"  [TERMINATE] Too many consecutive failures: {recent_failures}")
                return True
        
        # 检查是否执行了太多工具
        if len(state.executed_tools) > 15:
            print(f"  [TERMINATE] Too many tools executed: {len(state.executed_tools)}")
            return True
        
        # 检查是否在循环（重复执行相同工具）
        if len(state.executed_tools) >= 5:
            recent_tools = state.executed_tools[-5:]
            if len(set(recent_tools)) == 1:
                print(f"  [TERMINATE] Stuck in loop: repeating {recent_tools[0]}")
                return True
        
        return False

    def _enhance_prompt_with_search_info(self, original_prompt: str, prompt_type: str) -> str:
        """增强prompt，添加工具搜索和详情查询信息"""
        if prompt_type == "baseline":
            # 对baseline prompt特别处理，移除原有的Available Tools部分
            # 并添加搜索说明
            lines = original_prompt.split('\n')
            enhanced_lines = []
            skip_tools = False
            
            for line in lines:
                if line.strip().startswith("Available Tools:"):
                    skip_tools = True
                    # 替换为搜索和详情查询说明
                    enhanced_lines.append("Tool Search Available:")
                    enhanced_lines.append("You have access to a comprehensive tool library.")
                    enhanced_lines.append("Search for tools using: <tool_search>query</tool_search>")
                    enhanced_lines.append("Get tool details using: <tool_info>tool_name</tool_info>")
                    enhanced_lines.append("")
                    enhanced_lines.append("Examples:")
                    enhanced_lines.append("- <tool_search>data validation parser</tool_search>")
                    enhanced_lines.append("- <tool_info>data_processing_validator</tool_info>")
                    enhanced_lines.append("")
                elif skip_tools and (line.strip() == "" or not line.startswith("-")):
                    skip_tools = False
                    enhanced_lines.append(line)
                elif not skip_tools:
                    enhanced_lines.append(line)
            
            return '\n'.join(enhanced_lines)
        else:
            # 对其他prompt类型，在合适位置添加搜索和详情查询说明
            search_info = """

    Note: You can search for tools using <tool_search>query</tool_search> and get tool details using <tool_info>tool_name</tool_info>."""
            return original_prompt + search_info

    def _extract_tool_searches(self, response: str) -> List[str]:
        """提取工具搜索查询"""
        pattern = r'<tool_search>(.*?)</tool_search>'
        matches = re.findall(pattern, response, re.DOTALL)
        queries = [match.strip() for match in matches]
        
        for query in queries:
            print(f"  [SEARCH] Query: {query}")
        
        return queries
    

    def _handle_tool_searches(self, queries: List[str], state: ExecutionState) -> List[Dict]:
        """处理工具搜索请求，返回完整的MCP协议信息"""
        all_results = []
        
        for query in queries:
            # 跟踪搜索历史
            self.search_history.append({
                'query': query,
                'turn': state.current_step,
                'timestamp': datetime.now().isoformat()
            })
            

            search_results = self.embedding_manager.search(
                query=query,
                k=5  # 返回前5个最相关的工具
            )
            
            # 格式化结果，包含完整的MCP协议信息
            formatted_results = []
            for result in search_results:
                # 确保工具在注册表中
                if result.tool_name in self.tool_registry:
                    # 获取完整的MCP协议
                    mcp_protocol = result.mcp_protocol  # <- 修改了这部分
                    
                    tool_info = {
                        'name': result.tool_name,
                        'description': mcp_protocol.get('description', ''),
                        'category': result.category,
                        'score': float(result.score),
                        # 添加完整的MCP协议信息  # <- 新增了这部分
                        'parameters': mcp_protocol.get('parameters', []),
                        'returns': mcp_protocol.get('returns', []),
                        'errors': mcp_protocol.get('errors', []),
                        'dependencies': mcp_protocol.get('dependencies', []),
                        'metadata': mcp_protocol.get('metadata', {})
                    }
                    formatted_results.append(tool_info)
            
            all_results.append({
                'query': query,
                'results': formatted_results
            })

        
        return all_results
    

    def _simple_tool_search(self, query: str) -> List[Dict]:
        """简单的关键词匹配工具搜索（降级方案），返回完整MCP信息"""
        print("啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊")
        query_words = query.lower().split()
        results = []
        
        # 优先从完整注册表获取信息  # <- 新增了这部分
        registry_to_use = self.full_tool_registry if hasattr(self, 'full_tool_registry') else self.tool_registry
        
        for tool_name, tool_spec in registry_to_use.items():
            # 计算匹配分数
            score = 0
            tool_lower = tool_name.lower()
            desc_lower = str(tool_spec.get('description', '')).lower()
            
            for word in query_words:
                if word in tool_lower:
                    score += 2
                if word in desc_lower:
                    score += 1
            
            if score > 0:
                results.append({
                    'name': tool_name,
                    'description': tool_spec.get('description', ''),
                    'category': tool_spec.get('metadata', {}).get('category', 'unknown'),
                    'score': score / len(query_words),
                    # 添加完整的MCP协议信息  # <- 新增了这部分
                    'parameters': tool_spec.get('parameters', []),
                    'returns': tool_spec.get('returns', []),
                    'errors': tool_spec.get('errors', []),
                    'dependencies': tool_spec.get('dependencies', []),
                    'metadata': tool_spec.get('metadata', {})
                })
        
        # 按分数排序并返回前5个
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:5]


    def _format_search_results(self, search_results: List[Dict]) -> str:
        """格式化搜索结果，包含完整的MCP协议信息"""
        feedback_parts = ["Tool Search Results:"]
        
        for search in search_results:
            feedback_parts.append(f"\nQuery: '{search['query']}'")
            
            if 'error' in search:
                feedback_parts.append(f"Error: {search['error']}")
                continue
            
            if search['results']:
                feedback_parts.append("Found tools:")
                for i, tool in enumerate(search['results'][:5], 1):
                    feedback_parts.append(f"\n{i}. {tool['name']}")
                    feedback_parts.append(f"   Category: {tool['category']}")
                    feedback_parts.append(f"   Description: {tool['description']}")
                    if 'score' in tool:
                        feedback_parts.append(f"   Relevance: {tool['score']:.2f}")
                    
                    # 添加参数信息  # <- 新增了这部分
                    if 'parameters' in tool and tool['parameters']:
                        feedback_parts.append("   Parameters:")
                        for param in tool['parameters']:
                            param_str = f"      - {param.get('name', 'unnamed')} ({param.get('type', 'any')})"
                            if param.get('description'):
                                param_str += f": {param['description']}"
                            if param.get('required', True):
                                param_str += " [REQUIRED]"
                            else:
                                param_str += " [OPTIONAL]"
                                if 'default' in param:
                                    param_str += f" default={param['default']}"
                            feedback_parts.append(param_str)
                    else:
                        feedback_parts.append("   Parameters: None required")
                    
                    # 添加返回值信息
                    if 'returns' in tool and tool['returns']:
                        feedback_parts.append("   Returns:")
                        for ret in tool['returns']:
                            ret_str = f"      - {ret.get('name', 'unnamed')} ({ret.get('type', 'any')})"
                            if ret.get('description'):
                                ret_str += f": {ret['description']}"
                            feedback_parts.append(ret_str)
                    
                    # 添加错误信息
                    if 'errors' in tool and tool['errors']:
                        feedback_parts.append("   Possible Errors:")
                        for err in tool['errors']:
                            err_str = f"      - {err.get('code', 'ERROR')}"
                            if err.get('description'):
                                err_str += f": {err['description']}"
                            feedback_parts.append(err_str)
                    
                    # 添加依赖信息
                    if 'dependencies' in tool and tool['dependencies']:
                        feedback_parts.append(f"   Dependencies: {', '.join(tool['dependencies'])}")
            else:
                feedback_parts.append("No matching tools found.")
        
        feedback_parts.append("\nYou can now use these tools with <tool_call>tool_name</tool_call>")
        
        return '\n'.join(feedback_parts)


    def _get_tool_details(self, tool_names: List[str], state: ExecutionState) -> str:
        """获取工具的详细MCP信息"""
        # 确保已加载完整的工具注册表
        if not hasattr(self, 'full_tool_registry'):
            self.full_tool_registry = self._load_full_tool_registry()
        
        feedback_parts = ["Tool Information:"]
        
        for tool_name in tool_names:
            # 跟踪信息请求历史
            self.search_history.append({
                'action': 'tool_info',
                'tool': tool_name,
                'turn': state.current_step,
                'timestamp': datetime.now().isoformat()
            })
            
            feedback_parts.append(f"\n=== {tool_name} ===")
            
            # 从完整注册表获取信息
            if tool_name in self.full_tool_registry:
                tool_spec = self.full_tool_registry[tool_name]
                
                # 基本信息
                feedback_parts.append(f"Description: {tool_spec.get('description', 'No description')}")
                feedback_parts.append(f"Category: {tool_spec.get('metadata', {}).get('category', 'general')}")
                
                # 参数详情
                parameters = tool_spec.get('parameters', [])
                if parameters:
                    feedback_parts.append("\nParameters:")
                    for param in parameters:
                        param_str = f"  - {param['name']} ({param['type']})"
                        if param.get('description'):
                            param_str += f": {param['description']}"
                        if param.get('required', True):
                            param_str += " [REQUIRED]"
                        else:
                            param_str += " [OPTIONAL]"
                            if 'default' in param:
                                param_str += f" default={param['default']}"
                        feedback_parts.append(param_str)
                else:
                    feedback_parts.append("Parameters: None required")
                
                # 返回值详情
                returns = tool_spec.get('returns', [])
                if returns:
                    feedback_parts.append("\nReturns:")
                    for ret in returns:
                        ret_str = f"  - {ret.get('name', 'unnamed')} ({ret.get('type', 'any')})"
                        if ret.get('description'):
                            ret_str += f": {ret['description']}"
                        feedback_parts.append(ret_str)
                
                # 错误详情
                errors = tool_spec.get('errors', [])
                if errors:
                    feedback_parts.append("\nPossible Errors:")
                    for err in errors:
                        err_str = f"  - {err.get('code', 'ERROR')}"
                        if err.get('description'):
                            err_str += f": {err['description']}"
                        feedback_parts.append(err_str)
                
                # 依赖关系
                dependencies = tool_spec.get('dependencies', [])
                if dependencies:
                    feedback_parts.append(f"\nDependencies: {', '.join(dependencies)}")
                    feedback_parts.append("  Note: These tools should be executed before this one")
                
                # 使用示例（如果适用）
                if tool_spec.get('metadata', {}).get('usage_hint'):
                    feedback_parts.append(f"\nUsage Hint: {tool_spec['metadata']['usage_hint']}")
                
            elif tool_name in self.tool_registry:
                # 降级：只有基本信息
                tool_info = self.tool_registry[tool_name]
                feedback_parts.append("Limited information available (full registry not loaded)")
                feedback_parts.append(f"Description: {self._get_tool_attribute(tool_info, 'description', 'No description')}")
                feedback_parts.append(f"Category: {self._get_tool_attribute(tool_info, 'category', 'general')}")
            else:
                feedback_parts.append(f"Tool '{tool_name}' not found in registry")
        
        feedback_parts.append("\nUse <tool_call>tool_name</tool_call> to execute a tool")
        
        return '\n'.join(feedback_parts)
    

    def _get_llm_response(self, conversation: List[Dict], state: ExecutionState) -> Optional[str]:
        """获取LLM的下一步响应"""
        # 调用LLM
        from api_client_manager import get_api_model_name
        import time
        import random
        
        # 获取正确的API模型名称
        api_model_name = get_api_model_name(self.model)
        print(f"[LLM_CALL] Using model: {self.model}, API name: {api_model_name}")
        
        # 添加重试逻辑处理API限流和400错误（不计入turn）
        max_retries = 5  # 增加重试次数
        response = None
        for attempt in range(max_retries):
            try:
                # 只传递必要参数，不设置max_tokens和temperature
                create_params = {
                    "model": api_model_name,
                    "messages": conversation
                }
                
                # 设置API调用超时时间为120秒
                response = self.llm_client.chat.completions.create(**create_params, timeout=120)
                break  # 成功则跳出循环
            except Exception as e:
                error_msg = str(e)
                print(f"[LLM_ERROR] Attempt {attempt + 1}/{max_retries}: {error_msg}")
                
                # 检查是否是超时错误（超时不重试，直接失败）
                is_timeout = "timeout" in error_msg.lower() or "timed out" in error_msg.lower()
                if is_timeout:
                    print(f"[TIMEOUT] API call timed out after 120 seconds, not retrying")
                    state.timeout_occurred = True  # 标记超时发生
                    return None  # 直接返回失败，不重试
                
                # 检查是否是可重试的错误（不包括超时）
                is_rate_limit = "限流" in error_msg or "rate limit" in error_msg.lower() or "PL-002" in error_msg
                is_400_error = "400" in error_msg or "Bad Request" in error_msg
                is_connection_error = ("Connection" in error_msg and "timeout" not in error_msg.lower())
                
                if is_rate_limit or is_400_error or is_connection_error:
                    if attempt < max_retries - 1:
                        # 减少重试间隔：0.5-1.5秒基础时间，指数退避更温和
                        base_wait = random.uniform(0.5, 1.5)
                        wait_time = base_wait * (1.5 ** attempt)  # 使用1.5而不是2作为指数基数
                        wait_time = min(wait_time, 10)  # 最大等待10秒
                        
                        if not self.silent:
                            if is_400_error:
                                print(f"[RETRY] 400 error detected, waiting {wait_time:.1f}s before retry (not counting as turn)...")
                            elif is_rate_limit:
                                print(f"[RETRY] Rate limited, waiting {wait_time:.1f}s before retry...")
                            else:
                                print(f"[RETRY] Connection issue, waiting {wait_time:.1f}s before retry...")
                        
                        time.sleep(wait_time)
                        continue
                    else:
                        if not self.silent:
                            print(f"[ERROR] Max retries reached after {max_retries} attempts")
                            # 返回None表示API失败，让主循环处理
                            print(f"[API_FAILURE] All retries exhausted")
                        return None  # 主循环会结束，但不会被统计为工作流错误
                else:
                    # 其他错误仍然抛出
                    raise
        
        if response is None:
            return None  # 返回None让调用者处理
        
        # 检查响应是否有效
        if not hasattr(response, 'choices') or not response.choices:
            print(f"[ERROR] Invalid response structure: no choices")
            return None
        
        if not hasattr(response.choices[0], 'message') or not response.choices[0].message:
            print(f"[ERROR] Invalid response: no message")
            return None
        
        message = response.choices[0].message.content
        
        # 某些模型(DeepSeek-R1, gpt-oss-120b等)使用reasoning_content字段
        if not message and hasattr(response.choices[0].message, 'reasoning_content'):
            reasoning = response.choices[0].message.reasoning_content
            if reasoning:
                print(f"[INFO] Model {api_model_name}: Using reasoning_content instead of content")
                message = reasoning
        
        if not message:
            # 打印更详细的调试信息
            print(f"[ERROR] Empty message content from API")
            print(f"[DEBUG] Response finish_reason: {response.choices[0].finish_reason}")
            if hasattr(response, 'usage'):
                print(f"[DEBUG] Token usage - prompt: {response.usage.prompt_tokens}, completion: {response.usage.completion_tokens}")
            print(f"[DEBUG] Model: {api_model_name}")
            # 检查是否有其他字段包含内容
            if hasattr(response.choices[0].message, '__dict__'):
                print(f"[DEBUG] Message fields: {response.choices[0].message.__dict__.keys()}")
            return None
        
        # 记录token使用
        if hasattr(response, 'usage'):
            state.total_tokens_used += response.usage.total_tokens
        
        return message
            
    


    def _execute_tools_with_feedback(self, tool_calls: List[str], state: ExecutionState) -> str:
        """执行工具并生成反馈消息"""
        feedback_parts = []
        
        for tool_name in tool_calls:
            print(f"  [EXECUTING] {tool_name}")
            
            # 执行工具
            result = self._execute_single_tool(tool_name, state)
            
            # 记录执行历史（包含成功和失败）
            state.execution_history.append(result)
            state.current_step += 1
            
            # 只有成功的工具才记录到 executed_tools
            if result.success:
                state.executed_tools.append(tool_name)
            
            # 生成反馈
            if result.success:
                feedback = f"✅ {tool_name} executed successfully.\nOutput: {json.dumps(result.output, indent=2)}"
                print(f"    Result: SUCCESS")
            else:
                feedback = f"❌ {tool_name} failed.\nError: {result.error}"
                print(f"    Result: FAILED - {result.error}")
            
            feedback_parts.append(feedback)
        
        # 组合所有反馈
        combined_feedback = "\n\n".join(feedback_parts)
        combined_feedback += f"\n\nCurrent progress: {len(state.executed_tools)} tools executed."
        
        # 移除required_tools提示，改为通用的进度信息  # <- 修改了这部分
        if hasattr(state, 'task_type'):  # <- 新增
            # 提供任务类型相关的通用提示  # <- 新增
            if state.task_type == 'simple_task':  # <- 新增
                combined_feedback += " Continue with your task processing."  # <- 新增
            elif state.task_type == 'data_pipeline':  # <- 新增
                combined_feedback += " Continue with the pipeline execution."  # <- 新增
            else:  # <- 新增
                combined_feedback += " Continue with the next step."  # <- 新增
        else:  # <- 新增
            combined_feedback += " What's your next action?"  # <- 保留原有的通用提示
        
        combined_feedback += "\n- If successful, execute the next tool in your workflow"
        combined_feedback += "\n- If failed, consider alternatives or error handling"
        combined_feedback += "\n- If task is complete, indicate completion"
        combined_feedback += "\n\nRemember: Execute only ONE tool per response."
    
        
        return combined_feedback
    
    def _execute_single_tool(self, tool_name: str, state: ExecutionState) -> ToolExecutionResult:
        """执行单个工具"""
        start_time = time.time()
        
        # 获取工具类别
        category = self._get_tool_category(tool_name)
        simulator = self.tool_simulators.get(category, self._simulate_generic)
        
        # 计算成功率
        success_rate = self._calculate_success_rate(tool_name, state)
        
        # 模拟执行
        success = random.random() < success_rate
        
        if success:
            output = simulator(tool_name, state)
            error = None
        else:
            output = None
            error = self._generate_error_message(tool_name)
        
        execution_time = time.time() - start_time
        
        return ToolExecutionResult(
            tool_name=tool_name,
            success=success,
            output=output,
            error=error,
            execution_time=execution_time,
            metadata={'category': category, 'attempt': state.current_step}
        )
    

    def _calculate_success_rate(self, tool_name: str, state: ExecutionState) -> float:
        """计算工具成功率（考虑依赖和状态）"""
        rate = self.success_rate
        
        # 检查依赖
        tool_info = self.tool_registry.get(tool_name, {})
        dependencies = self._get_tool_attribute(tool_info, 'dependencies', [])  # <- 修改：使用统一访问方法
        
        for dep in dependencies:
            if dep not in state.executed_tools:
                rate *= 0.5  # 依赖未满足，成功率降低
                print(f"    [DEPENDENCY] Missing: {dep}, success rate reduced")
            else:
                # 检查依赖是否成功
                dep_results = [r for r in state.execution_history if r.tool_name == dep]
                if dep_results and not dep_results[-1].success:
                    rate *= 0.7  # 依赖失败，成功率降低
                    print(f"    [DEPENDENCY] Failed: {dep}, success rate reduced")
        
        # 连续失败惩罚
        if len(state.execution_history) >= 3:
            recent_failures = sum(1 for r in state.execution_history[-3:] if not r.success)
            if recent_failures > 0:
                rate *= (0.9 ** recent_failures)
                print(f"    [PENALTY] Recent failures: {recent_failures}, success rate reduced")
        
        return max(0.1, min(0.95, rate))  # 保持在合理范围
    
    # === 工具模拟器 ===
    
    def _simulate_file_operation(self, tool_name: str, state: ExecutionState) -> Dict:
        """模拟文件操作"""
        operations = {
            'reader': {
                'content': f'File content with {random.randint(100, 1000)} lines',
                'size': random.randint(1024, 10240),
                'encoding': 'utf-8'
            },
            'writer': {
                'path': f'/output/result_{random.randint(1000, 9999)}.txt',
                'bytes_written': random.randint(1024, 5120),
                'status': 'success'
            },
            'scanner': {
                'files_found': random.randint(1, 20),
                'total_size': random.randint(10240, 102400),
                'file_types': ['txt', 'csv', 'json']
            },
            'compressor': {
                'original_size': random.randint(5000, 20000),
                'compressed_size': random.randint(1000, 5000),
                'compression_ratio': round(random.uniform(0.2, 0.7), 2)
            }
        }
        
        # 提取操作类型
        for op_type, result in operations.items():
            if op_type in tool_name.lower():
                return result
        
        return {'status': 'completed', 'operation': 'file_operation'}
    
    def _simulate_data_processing(self, tool_name: str, state: ExecutionState) -> Dict:
        """模拟数据处理"""
        base_records = random.randint(50, 200)
        
        operations = {
            'parser': {
                'records_parsed': base_records,
                'parse_errors': random.randint(0, 5),
                'format_detected': random.choice(['json', 'csv', 'xml']),
                'schema_valid': True
            },
            'transformer': {
                'records_input': base_records,
                'records_output': base_records,
                'transformations_applied': ['normalize', 'clean', 'format'],
                'duration_ms': random.randint(100, 1000)
            },
            'validator': {
                'records_checked': base_records,
                'valid_records': int(base_records * 0.95),
                'invalid_records': int(base_records * 0.05),
                'validation_rules': ['type_check', 'range_check', 'format_check']
            },
            'filter': {
                'records_input': base_records,
                'records_output': int(base_records * random.uniform(0.6, 0.9)),
                'filter_criteria': 'status=active AND score>0.5',
                'filters_applied': 2
            },
            'aggregator': {
                'records_processed': base_records,
                'groups_created': random.randint(5, 15),
                'aggregations': {
                    'sum': round(random.uniform(1000, 5000), 2),
                    'avg': round(random.uniform(10, 100), 2),
                    'count': base_records
                }
            }
        }
        
        # 提取操作类型
        for op_type, result in operations.items():
            if op_type in tool_name.lower():
                return result
        
        return {'records_processed': base_records}
    
    def _simulate_network_operation(self, tool_name: str, state: ExecutionState) -> Dict:
        """模拟网络操作"""
        operations = {
            'fetcher': {
                'status_code': 200,
                'data': {
                    'items': random.randint(10, 50),
                    'total': random.randint(100, 500),
                    'page': 1
                },
                'response_time_ms': random.randint(50, 500),
                'headers': {'content-type': 'application/json'}
            },
            'poster': {
                'status_code': 201,
                'created_id': f'resource_{random.randint(10000, 99999)}',
                'location': f'/api/resources/{random.randint(10000, 99999)}',
                'response_time_ms': random.randint(100, 1000)
            },
            'monitor': {
                'status': 'healthy',
                'latency_ms': random.randint(10, 100),
                'uptime_percent': round(random.uniform(99.0, 99.99), 2),
                'last_check': datetime.now().isoformat()
            },
            'router': {
                'route_selected': f'/api/v{random.randint(1, 3)}/endpoint',
                'backend_server': f'server-{random.randint(1, 5)}',
                'load_balanced': True
            },
            'validator': {
                'ssl_valid': True,
                'certificate_expiry_days': random.randint(30, 365),
                'response_valid': True,
                'schema_matches': True
            }
        }
        
        # 提取操作类型
        for op_type, result in operations.items():
            if op_type in tool_name.lower():
                return result
        
        return {'status': 'success', 'operation': 'network'}
    
    def _simulate_computation(self, tool_name: str, state: ExecutionState) -> Dict:
        """模拟计算操作"""
        operations = {
            'calculator': {
                'result': round(random.uniform(0, 1000), 4),
                'formula': 'sum(data) * factor',
                'computation_time_ms': random.randint(10, 100)
            },
            'analyzer': {
                'metrics': {
                    'mean': round(random.uniform(40, 60), 2),
                    'std_dev': round(random.uniform(5, 15), 2),
                    'min': round(random.uniform(0, 20), 2),
                    'max': round(random.uniform(80, 100), 2)
                },
                'patterns_found': random.randint(0, 5),
                'confidence': round(random.uniform(0.7, 0.99), 2)
            },
            'predictor': {
                'prediction': round(random.uniform(100, 500), 2),
                'confidence_interval': [
                    round(random.uniform(80, 100), 2),
                    round(random.uniform(500, 600), 2)
                ],
                'model_accuracy': round(random.uniform(0.8, 0.95), 2)
            },
            'simulator': {
                'iterations_run': random.randint(1000, 10000),
                'convergence_achieved': True,
                'final_state': {
                    'value': round(random.uniform(0, 1), 4),
                    'stable': True
                }
            },
            'optimizer': {
                'optimal_value': round(random.uniform(0, 100), 2),
                'parameters': {
                    'x': round(random.uniform(0, 10), 2),
                    'y': round(random.uniform(0, 10), 2)
                },
                'iterations': random.randint(10, 100),
                'converged': True
            }
        }
        
        # 提取操作类型
        for op_type, result in operations.items():
            if op_type in tool_name.lower():
                return result
        
        return {
            'result': round(random.uniform(0, 100), 2),
            'computation_time_ms': random.randint(10, 1000)
        }
    
    def _simulate_integration(self, tool_name: str, state: ExecutionState) -> Dict:
        """模拟集成操作"""
        operations = {
            'authenticator': {
                'auth_token': f'token_{random.randint(100000, 999999)}',
                'expires_in': 3600,
                'token_type': 'Bearer',
                'scopes': ['read', 'write']
            },
            'mapper': {
                'mappings_created': random.randint(10, 50),
                'fields_mapped': random.randint(20, 100),
                'mapping_conflicts': random.randint(0, 3),
                'auto_resolved': True
            },
            'connector': {
                'connection_id': f'conn_{random.randint(1000, 9999)}',
                'status': 'established',
                'protocol': random.choice(['HTTP', 'HTTPS', 'WebSocket']),
                'latency_ms': random.randint(10, 100)
            },
            'scheduler': {
                'job_id': f'job_{random.randint(10000, 99999)}',
                'scheduled_time': datetime.now().isoformat(),
                'frequency': random.choice(['hourly', 'daily', 'weekly']),
                'status': 'scheduled'
            },
            'queue': {
                'message_id': f'msg_{random.randint(100000, 999999)}',
                'queue_position': random.randint(1, 100),
                'estimated_processing_time': random.randint(1, 60),
                'priority': random.choice(['low', 'medium', 'high'])
            }
        }
        
        # 提取操作类型
        for op_type, result in operations.items():
            if op_type in tool_name.lower():
                return result
        
        return {
            'status': 'connected',
            'integration_point': 'api_v2'
        }
    
    def _simulate_utility(self, tool_name: str, state: ExecutionState) -> Dict:
        """模拟工具操作"""
        operations = {
            'cache': {
                'operation': random.choice(['get', 'set']),
                'cache_hit': random.choice([True, False]),
                'items_cached': random.randint(10, 100),
                'memory_usage_mb': round(random.uniform(10, 100), 2),
                'ttl_seconds': 3600
            },
            'logger': {
                'logs_written': random.randint(1, 20),
                'log_level': random.choice(['DEBUG', 'INFO', 'WARNING']),
                'log_file': f'/logs/app_{datetime.now().strftime("%Y%m%d")}.log',
                'size_kb': random.randint(10, 1000)
            },
            'tracker': {
                'events_tracked': random.randint(5, 50),
                'tracking_id': f'track_{random.randint(100000, 999999)}',
                'session_duration_seconds': random.randint(60, 3600),
                'user_actions': ['click', 'view', 'submit']
            },
            'notifier': {
                'notifications_sent': random.randint(1, 10),
                'channels': random.choice([['email'], ['email', 'sms'], ['push']]),
                'delivery_status': 'delivered',
                'read_receipts': random.randint(0, 5)
            },
            'helper': {
                'operations_completed': random.randint(1, 10),
                'helper_type': random.choice(['format', 'validate', 'convert']),
                'processing_time_ms': random.randint(10, 100)
            }
        }
        
        # 提取操作类型
        for op_type, result in operations.items():
            if op_type in tool_name.lower():
                return result
        
        return {'status': 'completed', 'utility_operation': 'generic'}
    
    def _simulate_generic(self, tool_name: str, state: ExecutionState) -> Dict:
        """通用工具模拟"""
        return {
            'status': 'completed',
            'tool': tool_name,
            'timestamp': datetime.now().isoformat(),
            'execution_context': {
                'step': state.current_step,
                'total_tools_executed': len(state.executed_tools)
            }
        }
    
    # === 辅助方法 ===

    def _get_tool_category(self, tool_name: str) -> str:
        """获取工具类别"""
        # 使用统一管理器  # <- 修改了这一行
        if tool_name in self.tool_registry:  # <- 修改了这一行
            capability = self.tool_registry.get(tool_name)  # <- 修改了这一行
            return self.tool_capability_manager.get_category(capability)  # <- 修改了这一行
        
        # Fallback: 从工具名推断
        categories = [
            'file_operations', 'data_processing', 'network',
            'computation', 'integration', 'utility'
        ]
        
        tool_lower = tool_name.lower()
        for category in categories:
            if category.replace('_', '') in tool_lower.replace('_', ''):
                return category
        
        return 'generic'
    

    def _generate_error_message(self, tool_name: str) -> str:
        """生成错误消息 - 优先使用工具特定的错误定义"""
        # 优先从完整注册表获取工具信息
        tool_info = self.full_tool_registry.get(tool_name, {})  # <- 修改：使用full_tool_registry
        
        # 如果完整注册表没有，降级到原始注册表
        if not tool_info:
            tool_info = self.tool_registry.get(tool_name, {})
        
        # 获取工具定义的错误列表
        tool_errors = self._get_tool_attribute(tool_info, 'errors', [])
        
        # 如果工具定义了错误，使用工具特定的错误
        if tool_errors and len(tool_errors) > 0:
            # 随机选择一个错误
            selected_error = random.choice(tool_errors)
            
            # 处理不同的错误格式
            if isinstance(selected_error, dict):
                error_code = selected_error.get('code', 'UNKNOWN_ERROR')
                error_desc = selected_error.get('description', 'An error occurred')
            elif hasattr(selected_error, 'code') and hasattr(selected_error, 'description'):
                # 如果是ToolError对象
                error_code = selected_error.code
                error_desc = selected_error.description
            else:
                # 默认格式
                error_code = 'UNKNOWN_ERROR'
                error_desc = str(selected_error)
            
            # 添加额外的上下文信息（可选）
            context_additions = {
                'TIMEOUT': f' (after {random.randint(10, 60)} seconds)',
                'NETWORK_ERROR': f' (connection to {random.choice(["server", "endpoint", "service"])} failed)',
                'FILE_NOT_FOUND': f' (path: /data/{tool_name}_{random.randint(100, 999)}.dat)',
                'PERMISSION_DENIED': f' (required permission: {random.choice(["read", "write", "execute"])})',
                'INVALID_INPUT': f' (expected: {random.choice(["JSON", "XML", "CSV"])} format)',
                'DEPENDENCY_ERROR': f' (missing: {random.choice(["data source", "configuration", "previous step"])})'
            }
            
            # 如果错误代码有对应的上下文，添加它
            context = context_additions.get(error_code, '')
            
            return f"{error_code}: {error_desc}{context}"
        
        # 如果工具没有定义错误，使用默认错误模板（向后兼容）
        else:
            print("fhaosfhasiofhaioshdcoicas ioadncobadsdcobausodcasincdoasicaisncda\n \n")
            default_error_templates = [
                ("OPERATION_FAILED", "Operation could not be completed"),
                ("INVALID_INPUT", "Input validation failed"),
                ("TIMEOUT", "Operation timed out"),
                ("DEPENDENCY_ERROR", "Required dependencies are not available"),
                ("RESOURCE_ERROR", "Resource temporarily unavailable")
            ]
            
            error_code, error_desc = random.choice(default_error_templates)
            return f"{error_code}: {error_desc} for tool '{tool_name}'"
        

    def _extract_tool_info_requests(self, response: str) -> List[str]:
        """提取工具详情查询请求"""
        pattern = r'<tool_info>(.*?)</tool_info>'
        matches = re.findall(pattern, response, re.DOTALL)
        tool_names = [match.strip() for match in matches]
        
        for tool_name in tool_names:
            print(f"  [INFO] Tool info request: {tool_name}")
        
        return tool_names

    def _check_completion_signal(self, response: str) -> bool:
        """检查是否有完成信号"""
        completion_signals = [
            "TASK_COMPLETED",
            "task completed",
            "task is complete",
            "finished executing",
            "all steps completed",
            "workflow complete",
            "done with the task",
            "successfully completed the task",
            "task has been completed"
        ]
        
        response_lower = response.lower()
        return any(signal.lower() in response_lower for signal in completion_signals)
    


    def _evaluate_success(self, state: ExecutionState) -> Tuple[SuccessLevel, Dict[str, Any]]:
        """评估任务成功级别 - 严格的分级判定"""
        success_level, _ = self._evaluate_success_detailed(state)
        return success_level in ("full_success", "partial_success")
    
    def _extract_final_outputs(self, state: ExecutionState) -> Dict[str, Any]:
        """提取最终输出"""
        outputs = {}
        
        # 收集所有成功工具的输出
        for result in state.execution_history:
            if result.success and result.output:
                outputs[result.tool_name] = result.output
        
        # 特别标记输出类工具的结果
        final_outputs = {}
        output_keywords = ['writer', 'export', 'save', 'post', 'publish', 'notifier', 'poster']
        
        for tool_name, output in outputs.items():
            if any(keyword in tool_name.lower() for keyword in output_keywords):
                final_outputs[tool_name] = output
        
        return {
            'all_outputs': outputs,
            'final_outputs': final_outputs,
            'summary': {
                'total_tools_executed': len(state.executed_tools),
                'unique_tools': len(set(state.executed_tools)),
                'successful_executions': sum(1 for r in state.execution_history if r.success),
                'failed_executions': sum(1 for r in state.execution_history if not r.success),
                'final_status': 'completed' if state.task_completed else 'incomplete',
                'required_tools_coverage': self._calculate_coverage(state)
            }
        }
    
    def _calculate_coverage(self, state: ExecutionState) -> Dict[str, Any]:
        """计算必需工具的覆盖率"""
        if not state.required_tools:
            return {'required_tools': 0, 'executed': 0, 'coverage': 1.0}
        
        executed_required = [t for t in state.required_tools if t in state.executed_tools]
        
        return {
            'required_tools': len(state.required_tools),
            'executed': len(executed_required),
            'coverage': len(executed_required) / len(state.required_tools),
            'missing': [t for t in state.required_tools if t not in state.executed_tools]
        }