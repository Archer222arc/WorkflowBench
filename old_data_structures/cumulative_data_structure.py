#!/usr/bin/env python3
"""
Comprehensive data structure for cumulative test statistics
Designed to capture all metrics required by the experiment plan (综合实验评估计划.md)
WITHOUT storing individual test instances
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime

@dataclass
class MetricStats:
    """Basic statistics for a metric"""
    count: int = 0
    sum: float = 0.0
    min: float = float('inf')
    max: float = float('-inf')
    
    @property
    def mean(self) -> float:
        return self.sum / self.count if self.count > 0 else 0.0
    
    def update(self, value: float):
        if value is None:
            return  # Skip None values
        self.count += 1
        self.sum += value
        self.min = min(self.min, value)
        self.max = max(self.max, value)

@dataclass
class SuccessMetrics:
    """Success metrics tracking with separate assisted attempts"""
    # 原有三元组统计（保持不变）
    total_tests: int = 0          # 基础测试数（不包含assisted）
    full_success: int = 0
    partial_success: int = 0
    failure: int = 0
    
    # 独立的assisted统计（不影响原有的success/failure统计）
    assisted_failure: int = 0     # 得到帮助但仍失败的测试数
    assisted_success: int = 0     # 得到帮助后成功的测试数
    total_assisted_turns: int = 0  # 所有测试中系统提供帮助的总轮数
    tests_with_assistance: int = 0  # 获得过帮助的测试总数
    
    @property
    def total_assisted_tests(self) -> int:
        """获得过帮助的测试总数"""
        return self.assisted_failure + self.assisted_success
    
    @property
    def total_success(self) -> int:
        """Total success = full + partial"""
        return self.full_success + self.partial_success
    
    @property
    def avg_assisted_turns(self) -> float:
        """平均每个测试获得帮助的轮数"""
        return self.total_assisted_turns / self.total_tests if self.total_tests > 0 else 0.0
    
    @property
    def assisted_success_rate(self) -> float:
        """获得帮助后的成功率"""
        total_assisted = self.total_assisted_tests
        return self.assisted_success / total_assisted if total_assisted > 0 else 0.0
    
    @property
    def assistance_rate(self) -> float:
        """获得帮助的测试占比"""
        return self.tests_with_assistance / self.total_tests if self.total_tests > 0 else 0.0
    
    @property
    def success_rate(self) -> float:
        """Overall success rate"""
        return self.total_success / self.total_tests if self.total_tests > 0 else 0.0
    
    @property
    def full_success_rate(self) -> float:
        return self.full_success / self.total_tests if self.total_tests > 0 else 0.0
    
    @property
    def partial_success_rate(self) -> float:
        return self.partial_success / self.total_tests if self.total_tests > 0 else 0.0
    
    @property
    def failure_rate(self) -> float:
        return self.failure / self.total_tests if self.total_tests > 0 else 0.0
    
    @property
    def weighted_success_score(self) -> float:
        """Weighted score: full=1.0, partial=0.5, failure=0.0 (不受assisted统计影响)"""
        if self.total_tests == 0:
            return 0.0
        return (self.full_success * 1.0 + self.partial_success * 0.5) / self.total_tests

@dataclass
class ScoreMetrics:
    """Score metrics tracking"""
    workflow_scores: MetricStats = field(default_factory=MetricStats)
    phase2_scores: MetricStats = field(default_factory=MetricStats)
    quality_scores: MetricStats = field(default_factory=MetricStats)
    final_scores: MetricStats = field(default_factory=MetricStats)

@dataclass
class ExecutionMetrics:
    """Execution performance metrics"""
    execution_times: MetricStats = field(default_factory=MetricStats)
    turns_used: MetricStats = field(default_factory=MetricStats)
    tool_calls: MetricStats = field(default_factory=MetricStats)
    
    # Tool usage tracking
    tools_used: Dict[str, int] = field(default_factory=dict)
    total_tool_invocations: int = 0
    unique_tools_count: int = 0
    
    # Tool coverage tracking (基于required_tools)
    tool_coverage_scores: MetricStats = field(default_factory=MetricStats)  # 每个测试的coverage分数
    
    @property
    def avg_execution_time(self) -> float:
        return self.execution_times.mean
    
    @property
    def avg_turns(self) -> float:
        return self.turns_used.mean
    
    @property
    def avg_tool_calls(self) -> float:
        return self.tool_calls.mean
    
    @property
    def tool_coverage_rate(self) -> float:
        """平均tool coverage rate：成功执行的required_tools占总的required_tools的比例"""
        return self.tool_coverage_scores.mean

@dataclass
class ErrorMetrics:
    """Error analysis metrics"""
    error_types: Dict[str, int] = field(default_factory=dict)
    total_errors: int = 0
    
    # Error categories for Table 4.5.1
    tool_selection_errors: int = 0
    parameter_config_errors: int = 0
    sequence_order_errors: int = 0
    dependency_errors: int = 0
    timeout_errors: int = 0
    max_turns_errors: int = 0
    tool_call_format_errors: int = 0  # 新增：工具调用格式错误
    other_errors: int = 0
    
    def categorize_error(self, error_msg: str):
        """Categorize error based on message content"""
        if not error_msg:
            return
        
        error_lower = error_msg.lower()
        self.total_errors += 1
        
        # Track specific error message
        self.error_types[error_msg] = self.error_types.get(error_msg, 0) + 1
        
        # Enhanced categorization with intelligent error detection
        if 'format errors detected' in error_lower or 'format recognition issue' in error_lower:
            # 明确的格式错误
            self.tool_call_format_errors += 1
        elif 'tool call format' in error_lower or 'understand tool call format' in error_lower:
            # 工具调用格式不理解
            self.tool_call_format_errors += 1
        elif ('no tool calls' in error_lower and 'turns' in error_lower) or ('max turns reached' in error_lower and 'no tool calls' in error_lower):
            # 没有工具调用或达到最大轮数且无工具调用 - 格式问题
            self.tool_call_format_errors += 1
        elif ('tool' in error_lower and ('select' in error_lower or 'choice' in error_lower)) or 'tool calls failed' in error_lower:
            # 工具选择错误或工具调用失败
            self.tool_selection_errors += 1
        elif ('parameter' in error_lower or 'argument' in error_lower or 'invalid_input' in error_lower or 
              'permission_denied' in error_lower or 'validation failed' in error_lower):
            # 参数配置错误（包括输入验证、权限等）
            self.parameter_config_errors += 1
        elif ('sequence' in error_lower or 'order' in error_lower or 'required tools not completed' in error_lower):
            # 序列顺序错误（包括必需工具未完成）
            self.sequence_order_errors += 1
        elif 'depend' in error_lower or 'dependency' in error_lower:
            # 依赖错误
            self.dependency_errors += 1
        elif 'timeout' in error_lower:
            # 超时错误
            self.timeout_errors += 1
        elif (('max turns' in error_lower or 'maximum turns' in error_lower or 'failed after' in error_lower) and 'no tool calls' not in error_lower):
            # 普通的最大轮数错误（有工具调用但未完成）
            self.max_turns_errors += 1
        else:
            self.other_errors += 1
    
    @property
    def tool_selection_error_rate(self) -> float:
        return self.tool_selection_errors / self.total_errors if self.total_errors > 0 else 0.0
    
    @property
    def parameter_error_rate(self) -> float:
        return self.parameter_config_errors / self.total_errors if self.total_errors > 0 else 0.0
    
    @property
    def sequence_error_rate(self) -> float:
        return self.sequence_order_errors / self.total_errors if self.total_errors > 0 else 0.0
    
    @property
    def dependency_error_rate(self) -> float:
        return self.dependency_errors / self.total_errors if self.total_errors > 0 else 0.0
    
    @property
    def timeout_error_rate(self) -> float:
        return self.timeout_errors / self.total_errors if self.total_errors > 0 else 0.0
    
    @property
    def format_error_rate(self) -> float:
        """Alias for tool_call_format_error_rate for consistency"""
        return self.tool_call_format_errors / self.total_errors if self.total_errors > 0 else 0.0
    
    @property
    def tool_call_format_error_rate(self) -> float:
        return self.tool_call_format_errors / self.total_errors if self.total_errors > 0 else 0.0
    
    @property
    def max_turns_error_rate(self) -> float:
        return self.max_turns_errors / self.total_errors if self.total_errors > 0 else 0.0

@dataclass
class PromptTypeStats:
    """Statistics for a specific prompt type"""
    prompt_type: str
    success_metrics: SuccessMetrics = field(default_factory=SuccessMetrics)
    score_metrics: ScoreMetrics = field(default_factory=ScoreMetrics)
    execution_metrics: ExecutionMetrics = field(default_factory=ExecutionMetrics)
    error_metrics: ErrorMetrics = field(default_factory=ErrorMetrics)

@dataclass
class TaskTypeStats:
    """Statistics for a specific task type"""
    task_type: str
    success_metrics: SuccessMetrics = field(default_factory=SuccessMetrics)
    score_metrics: ScoreMetrics = field(default_factory=ScoreMetrics)
    execution_metrics: ExecutionMetrics = field(default_factory=ExecutionMetrics)
    error_metrics: ErrorMetrics = field(default_factory=ErrorMetrics)
    
    # Task-specific prompt breakdowns
    prompt_breakdowns: Dict[str, SuccessMetrics] = field(default_factory=dict)

@dataclass
class FlawTypeStats:
    """Statistics for a specific flaw type"""
    flaw_type: str
    success_metrics: SuccessMetrics = field(default_factory=SuccessMetrics)
    score_metrics: ScoreMetrics = field(default_factory=ScoreMetrics)
    execution_metrics: ExecutionMetrics = field(default_factory=ExecutionMetrics)
    error_metrics: ErrorMetrics = field(default_factory=ErrorMetrics)
    
    @property
    def robustness_score(self) -> float:
        """Robustness score for this flaw type"""
        return self.success_metrics.weighted_success_score

@dataclass
class DifficultyStats:
    """Statistics for a specific difficulty level"""
    difficulty: str
    success_metrics: SuccessMetrics = field(default_factory=SuccessMetrics)
    score_metrics: ScoreMetrics = field(default_factory=ScoreMetrics)
    execution_metrics: ExecutionMetrics = field(default_factory=ExecutionMetrics)

# ============= V2 层次结构支持 =============
# 支持新的层次：model -> prompt_type -> tool_success_rate -> difficulty -> task_type

@dataclass
class TaskTypeStatsV2:
    """任务类型级别的统计（V2层次结构）"""
    task_type: str
    total_tests: int = 0
    full_success: int = 0
    partial_success: int = 0
    failure: int = 0
    
    # 执行指标
    avg_execution_time: float = 0.0
    avg_turns: float = 0.0
    avg_tool_calls: float = 0.0
    tool_coverage_rate: float = 0.0
    
    # 评分指标
    avg_workflow_score: float = 0.0
    avg_phase2_score: float = 0.0
    avg_quality_score: float = 0.0
    avg_final_score: float = 0.0
    
    # 错误统计
    total_errors: int = 0
    tool_call_format_errors: int = 0
    timeout_errors: int = 0
    dependency_errors: int = 0
    parameter_config_errors: int = 0
    tool_selection_errors: int = 0
    sequence_order_errors: int = 0
    max_turns_errors: int = 0
    
    # 辅助统计
    assisted_failure: int = 0
    assisted_success: int = 0
    total_assisted_turns: int = 0
    tests_with_assistance: int = 0
    
    @property
    def success_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return (self.full_success + self.partial_success) / self.total_tests
    
    @property
    def full_success_rate(self) -> float:
        return self.full_success / self.total_tests if self.total_tests > 0 else 0.0
    
    @property
    def partial_success_rate(self) -> float:
        return self.partial_success / self.total_tests if self.total_tests > 0 else 0.0
    
    @property
    def failure_rate(self) -> float:
        return self.failure / self.total_tests if self.total_tests > 0 else 0.0
    
    @property
    def avg_assisted_turns(self) -> float:
        return self.total_assisted_turns / self.tests_with_assistance if self.tests_with_assistance > 0 else 0.0
    
    @property
    def assisted_success_rate(self) -> float:
        total_assisted = self.assisted_success + self.assisted_failure
        return self.assisted_success / total_assisted if total_assisted > 0 else 0.0
    
    @property
    def assistance_rate(self) -> float:
        return self.tests_with_assistance / self.total_tests if self.total_tests > 0 else 0.0
    
    def update_from_test(self, test_record: Dict):
        """从测试记录更新统计"""
        self.total_tests += 1
        
        # 更新成功/失败统计
        success_level = test_record.get('success_level', 'failure')
        if success_level == 'full_success':
            self.full_success += 1
        elif success_level == 'partial_success':
            self.partial_success += 1
        else:
            self.failure += 1
            self.total_errors += 1
        
        # 更新执行指标（增量平均）
        n = self.total_tests
        self.avg_execution_time = ((n - 1) * self.avg_execution_time + test_record.get('execution_time', 0)) / n
        self.avg_turns = ((n - 1) * self.avg_turns + test_record.get('turns', 0)) / n
        self.avg_tool_calls = ((n - 1) * self.avg_tool_calls + len(test_record.get('tool_calls', []))) / n
        
        # 更新tool_coverage - 优先使用传入的值，否则计算
        if 'tool_coverage_rate' in test_record and test_record['tool_coverage_rate'] is not None:
            # 使用传入的值（增量平均）
            coverage = test_record['tool_coverage_rate']
            self.tool_coverage_rate = ((n - 1) * self.tool_coverage_rate + coverage) / n
        else:
            # 如果没有传入，则计算
            required_tools = test_record.get('required_tools', [])
            executed_tools = test_record.get('executed_tools', test_record.get('tool_calls', []))
            if required_tools:
                required_set = set(required_tools)
                executed_set = set(executed_tools)
                covered_tools = required_set.intersection(executed_set)
                coverage = len(covered_tools) / len(required_tools)
                # 增量平均
                self.tool_coverage_rate = ((n - 1) * self.tool_coverage_rate + coverage) / n
        
        # 更新评分指标（增量平均）
        if test_record.get('workflow_score') is not None:
            self.avg_workflow_score = ((n - 1) * self.avg_workflow_score + test_record['workflow_score']) / n
        if test_record.get('phase2_score') is not None:
            self.avg_phase2_score = ((n - 1) * self.avg_phase2_score + test_record['phase2_score']) / n
        if test_record.get('quality_score') is not None:
            self.avg_quality_score = ((n - 1) * self.avg_quality_score + test_record['quality_score']) / n
        if test_record.get('final_score') is not None:
            self.avg_final_score = ((n - 1) * self.avg_final_score + test_record['final_score']) / n
        
        # 更新辅助统计
        format_help_turns = test_record.get('format_error_count', 0)
        if format_help_turns > 0:
            self.tests_with_assistance += 1
            self.total_assisted_turns += format_help_turns
            if success_level in ['full_success', 'partial_success']:
                self.assisted_success += 1
            else:
                self.assisted_failure += 1
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'task_type': self.task_type,
            'total': self.total_tests,
            'success': self.full_success + self.partial_success,
            'full_success': self.full_success,
            'partial_success': self.partial_success,
            'failure': self.failure,
            'success_rate': self.success_rate,
            'full_success_rate': self.full_success_rate,
            'partial_success_rate': self.partial_success_rate,
            'failure_rate': self.failure_rate,
            'avg_execution_time': self.avg_execution_time,
            'avg_turns': self.avg_turns,
            'avg_tool_calls': self.avg_tool_calls,
            'tool_coverage_rate': self.tool_coverage_rate,
            'avg_workflow_score': self.avg_workflow_score,
            'avg_phase2_score': self.avg_phase2_score,
            'avg_quality_score': self.avg_quality_score,
            'avg_final_score': self.avg_final_score,
            'total_errors': self.total_errors,
            'tool_call_format_errors': self.tool_call_format_errors,
            'timeout_errors': self.timeout_errors,
            'dependency_errors': self.dependency_errors,
            'parameter_config_errors': self.parameter_config_errors,
            'tool_selection_errors': self.tool_selection_errors,
            'sequence_order_errors': self.sequence_order_errors,
            'max_turns_errors': self.max_turns_errors,
            'assisted_failure': self.assisted_failure,
            'assisted_success': self.assisted_success,
            'total_assisted_turns': self.total_assisted_turns,
            'tests_with_assistance': self.tests_with_assistance,
            'avg_assisted_turns': self.avg_assisted_turns,
            'assisted_success_rate': self.assisted_success_rate,
            'assistance_rate': self.assistance_rate
        }

@dataclass
class DifficultyStatsV2:
    """难度级别的统计（包含多个任务类型）"""
    difficulty: str
    by_task_type: Dict[str, TaskTypeStatsV2] = field(default_factory=dict)
    
    def get_or_create_task_type(self, task_type: str) -> TaskTypeStatsV2:
        if task_type not in self.by_task_type:
            self.by_task_type[task_type] = TaskTypeStatsV2(task_type=task_type)
        return self.by_task_type[task_type]
    
    def to_dict(self) -> Dict:
        return {
            'difficulty': self.difficulty,
            'by_task_type': {tt: stats.to_dict() for tt, stats in self.by_task_type.items()}
        }

@dataclass
class ToolSuccessRateStats:
    """工具成功率级别的统计（包含多个难度）"""
    tool_success_rate: float
    by_difficulty: Dict[str, DifficultyStatsV2] = field(default_factory=dict)
    
    def get_or_create_difficulty(self, difficulty: str) -> DifficultyStatsV2:
        if difficulty not in self.by_difficulty:
            self.by_difficulty[difficulty] = DifficultyStatsV2(difficulty=difficulty)
        return self.by_difficulty[difficulty]
    
    def to_dict(self) -> Dict:
        return {
            'tool_success_rate': self.tool_success_rate,
            'by_difficulty': {d: stats.to_dict() for d, stats in self.by_difficulty.items()}
        }

@dataclass
class PromptTypeStatsV2:
    """Prompt类型级别的统计（包含多个工具成功率）"""
    prompt_type: str
    by_tool_success_rate: Dict[float, ToolSuccessRateStats] = field(default_factory=dict)
    
    # 汇总统计
    total_tests: int = 0
    total_success: int = 0
    avg_success_rate: float = 0.0
    
    def get_or_create_tool_rate(self, rate: float) -> ToolSuccessRateStats:
        # 直接使用原始值（通常是0.6, 0.7, 0.8, 0.9）
        if rate not in self.by_tool_success_rate:
            self.by_tool_success_rate[rate] = ToolSuccessRateStats(tool_success_rate=rate)
        return self.by_tool_success_rate[rate]
    
    def update_summary(self):
        """更新汇总统计"""
        self.total_tests = 0
        self.total_success = 0
        
        for rate_stats in self.by_tool_success_rate.values():
            for diff_stats in rate_stats.by_difficulty.values():
                for task_stats in diff_stats.by_task_type.values():
                    self.total_tests += task_stats.total_tests
                    self.total_success += (task_stats.full_success + task_stats.partial_success)
        
        self.avg_success_rate = self.total_success / self.total_tests if self.total_tests > 0 else 0.0
    
    def to_dict(self) -> Dict:
        self.update_summary()
        return {
            'prompt_type': self.prompt_type,
            'total_tests': self.total_tests,
            'total_success': self.total_success,
            'avg_success_rate': self.avg_success_rate,
            'by_tool_success_rate': {rate: stats.to_dict() for rate, stats in self.by_tool_success_rate.items()}
        }

@dataclass
class ModelStatisticsV2:
    """模型级别的统计（新层次结构）"""
    model_name: str
    first_test_time: Optional[str] = None
    last_test_time: Optional[str] = None
    
    # 按prompt类型组织
    by_prompt_type: Dict[str, PromptTypeStatsV2] = field(default_factory=dict)
    
    # 总体统计
    total_tests: int = 0
    total_success: int = 0
    total_failure: int = 0
    overall_success_rate: float = 0.0
    avg_execution_time: float = 0.0
    tool_coverage_rate: float = 0.0  # 添加总体的tool_coverage_rate
    
    def get_or_create_prompt_type(self, prompt_type: str) -> PromptTypeStatsV2:
        if prompt_type not in self.by_prompt_type:
            self.by_prompt_type[prompt_type] = PromptTypeStatsV2(prompt_type=prompt_type)
        return self.by_prompt_type[prompt_type]
    
    def update_from_test(self, test_record: Dict):
        """从测试记录更新统计"""
        # 更新时间戳
        timestamp = test_record.get('timestamp', datetime.now().isoformat())
        if not self.first_test_time:
            self.first_test_time = timestamp
        self.last_test_time = timestamp
        
        # 提取关键信息
        prompt_type = test_record.get('prompt_type', 'baseline')
        tool_success_rate = test_record.get('tool_reliability', 0.8)  # 注意字段名
        difficulty = test_record.get('difficulty', 'easy')
        task_type = test_record.get('task_type', 'unknown')
        
        # 处理缺陷测试的prompt_type
        if test_record.get('is_flawed') and test_record.get('flaw_type'):
            prompt_type = f"flawed_{test_record['flaw_type']}"
        
        # 导航到正确的层次并更新
        prompt_stats = self.get_or_create_prompt_type(prompt_type)
        rate_stats = prompt_stats.get_or_create_tool_rate(tool_success_rate)
        diff_stats = rate_stats.get_or_create_difficulty(difficulty)
        task_stats = diff_stats.get_or_create_task_type(task_type)
        
        # 更新任务级别统计
        task_stats.update_from_test(test_record)
        
        # 更新总体统计
        self.total_tests += 1
        success_level = test_record.get('success_level', 'failure')
        if success_level in ['full_success', 'partial_success']:
            self.total_success += 1
        else:
            self.total_failure += 1
        
        self.overall_success_rate = self.total_success / self.total_tests if self.total_tests > 0 else 0.0
        
        # 更新平均执行时间
        n = self.total_tests
        exec_time = test_record.get('execution_time', 0)
        self.avg_execution_time = ((n - 1) * self.avg_execution_time + exec_time) / n
        
        # 更新总体的tool_coverage_rate（增量平均）
        if 'tool_coverage_rate' in test_record and test_record['tool_coverage_rate'] is not None:
            coverage = test_record['tool_coverage_rate']
            self.tool_coverage_rate = ((n - 1) * self.tool_coverage_rate + coverage) / n
    
    def to_dict(self) -> Dict:
        """转换为字典用于序列化"""
        return {
            'model_name': self.model_name,
            'first_test_time': self.first_test_time,
            'last_test_time': self.last_test_time,
            'total_tests': self.total_tests,
            'total_success': self.total_success,
            'total_failure': self.total_failure,
            'overall_success_rate': self.overall_success_rate,
            'avg_execution_time': self.avg_execution_time,
            'tool_coverage_rate': self.tool_coverage_rate,  # 添加tool_coverage_rate到序列化
            'by_prompt_type': {pt: stats.to_dict() for pt, stats in self.by_prompt_type.items()}
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ModelStatisticsV2':
        """从字典反序列化"""
        model = cls(
            model_name=data['model_name'],
            first_test_time=data.get('first_test_time'),
            last_test_time=data.get('last_test_time'),
            total_tests=data.get('total_tests', 0),
            total_success=data.get('total_success', 0),
            total_failure=data.get('total_failure', 0),
            overall_success_rate=data.get('overall_success_rate', 0.0),
            avg_execution_time=data.get('avg_execution_time', 0.0)
        )
        
        # 重建层次结构
        for pt_name, pt_data in data.get('by_prompt_type', {}).items():
            pt_stats = PromptTypeStatsV2(prompt_type=pt_name)
            
            for rate, rate_data in pt_data.get('by_tool_success_rate', {}).items():
                rate_float = float(rate) if isinstance(rate, str) else rate
                rate_stats = ToolSuccessRateStats(tool_success_rate=rate_float)
                
                for diff, diff_data in rate_data.get('by_difficulty', {}).items():
                    diff_stats = DifficultyStatsV2(difficulty=diff)
                    
                    for task, task_data in diff_data.get('by_task_type', {}).items():
                        task_stats = TaskTypeStatsV2(task_type=task)
                        # 恢复所有字段
                        for field, value in task_data.items():
                            if hasattr(task_stats, field) and field != 'task_type':
                                setattr(task_stats, field, value)
                        diff_stats.by_task_type[task] = task_stats
                    
                    rate_stats.by_difficulty[diff] = diff_stats
                
                pt_stats.by_tool_success_rate[rate_float] = rate_stats
            
            model.by_prompt_type[pt_name] = pt_stats
        
        return model

@dataclass
class ModelStatistics:
    """Complete statistics for a model - NO instance storage"""
    model_name: str
    first_test_time: Optional[str] = None
    last_test_time: Optional[str] = None
    
    # Overall metrics
    overall_success: SuccessMetrics = field(default_factory=SuccessMetrics)
    overall_scores: ScoreMetrics = field(default_factory=ScoreMetrics)
    overall_execution: ExecutionMetrics = field(default_factory=ExecutionMetrics)
    overall_errors: ErrorMetrics = field(default_factory=ErrorMetrics)
    
    # Breakdown by categories (for experiment tables)
    by_task_type: Dict[str, TaskTypeStats] = field(default_factory=dict)
    by_prompt_type: Dict[str, PromptTypeStats] = field(default_factory=dict)
    by_flaw_type: Dict[str, FlawTypeStats] = field(default_factory=dict)
    by_difficulty: Dict[str, DifficultyStats] = field(default_factory=dict)
    
    # Tool reliability sensitivity (Table 4.3.2)
    by_tool_reliability: Dict[float, SuccessMetrics] = field(default_factory=dict)
    
    # Prompt sensitivity metrics (Table 4.4.1)
    prompt_sensitivity_index: float = 0.0
    best_prompt_type: Optional[str] = None
    
    def update_from_test(self, test_record: Dict):
        """Update statistics from a test record WITHOUT storing the instance"""
        
        # Update timestamps
        timestamp = test_record.get('timestamp', datetime.now().isoformat())
        if not self.first_test_time:
            self.first_test_time = timestamp
        self.last_test_time = timestamp
        
        # Determine success level
        success = test_record.get('success', False)
        success_level = test_record.get('success_level', 'failure')
        
        # 获取assistance信息
        format_help_turns = test_record.get('format_error_count', 0)  # 系统提供帮助的轮数
        had_assistance = format_help_turns > 0
        
        # 原有三元组统计保持不变（不受assisted影响）
        self.overall_success.total_tests += 1
        if success_level == 'full_success':
            self.overall_success.full_success += 1
        elif success_level == 'partial_success':
            self.overall_success.partial_success += 1
        else:
            self.overall_success.failure += 1
        
        # 更新assisted统计（额外的统计，不影响原有逻辑）
        if had_assistance:
            self.overall_success.tests_with_assistance += 1
            self.overall_success.total_assisted_turns += format_help_turns
            
            # 根据最终结果分类
            if success_level in ['full_success', 'partial_success']:
                self.overall_success.assisted_success += 1
            else:
                self.overall_success.assisted_failure += 1
        
        # Update score metrics if available
        if 'workflow_score' in test_record and test_record['workflow_score'] is not None:
            self.overall_scores.workflow_scores.update(test_record['workflow_score'])
            # Debug output
            if test_record.get('model') == 'qwen2.5-3b-instruct':
                print(f"[DEBUG] Model stats updated - workflow_score: {test_record['workflow_score']:.3f}, count: {self.overall_scores.workflow_scores.count}, mean: {self.overall_scores.workflow_scores.mean:.3f}")
        if 'phase2_score' in test_record and test_record['phase2_score'] is not None:
            self.overall_scores.phase2_scores.update(test_record['phase2_score'])
        if 'quality_score' in test_record and test_record['quality_score'] is not None:
            self.overall_scores.quality_scores.update(test_record['quality_score'])
        if 'final_score' in test_record and test_record['final_score'] is not None:
            self.overall_scores.final_scores.update(test_record['final_score'])
        
        # Update execution metrics
        if 'execution_time' in test_record and test_record['execution_time'] is not None and test_record['execution_time'] > 0:
            self.overall_execution.execution_times.update(test_record['execution_time'])
        if 'turns' in test_record and test_record['turns'] is not None and test_record['turns'] > 0:
            self.overall_execution.turns_used.update(test_record['turns'])
        if 'tool_calls' in test_record and test_record['tool_calls'] is not None:
            num_calls = len(test_record['tool_calls']) if isinstance(test_record['tool_calls'], list) else test_record['tool_calls']
            self.overall_execution.tool_calls.update(num_calls)
            
            # Track tool usage - 优先使用executed_tools，回退到tool_calls
            tools_to_track = test_record.get('executed_tools', test_record.get('tool_calls', []))
            if isinstance(tools_to_track, list):
                for tool_call in tools_to_track:
                    tool_name = tool_call if isinstance(tool_call, str) else tool_call.get('tool', 'unknown')
                    self.overall_execution.tools_used[tool_name] = self.overall_execution.tools_used.get(tool_name, 0) + 1
                    self.overall_execution.total_tool_invocations += 1
                self.overall_execution.unique_tools_count = len(self.overall_execution.tools_used)
        
        # 计算tool coverage (基于required_tools) - 移到if外面
        required_tools = test_record.get('required_tools', [])
        executed_tools = test_record.get('executed_tools', [])
        if required_tools:
            # 计算成功执行的required_tools数量
            required_set = set(required_tools)
            executed_set = set(executed_tools) if executed_tools else set()
            covered_tools = required_set.intersection(executed_set)
            coverage_score = len(covered_tools) / len(required_tools)
            self.overall_execution.tool_coverage_scores.update(coverage_score)
        
        # Update error metrics with enhanced information
        if not success and 'error_message' in test_record:
            self.overall_errors.categorize_error(test_record['error_message'])
        
        # Track format error statistics
        if 'format_error_count' in test_record and test_record['format_error_count'] > 0:
            # 即使成功了，也要记录过程中的格式错误
            format_count = test_record['format_error_count']
            if not hasattr(self.overall_execution, 'format_error_attempts'):
                self.overall_execution.format_error_attempts = 0
            self.overall_execution.format_error_attempts += format_count
            
            print(f"[DEBUG] Model {test_record.get('model', 'unknown')} had {format_count} format errors during execution")
        
        # Update breakdown by task type
        task_type = test_record.get('task_type', 'unknown')
        if task_type not in self.by_task_type:
            self.by_task_type[task_type] = TaskTypeStats(task_type=task_type)
        
        task_stats = self.by_task_type[task_type]
        # 原有统计保持不变
        task_stats.success_metrics.total_tests += 1
        if success_level == 'full_success':
            task_stats.success_metrics.full_success += 1
        elif success_level == 'partial_success':
            task_stats.success_metrics.partial_success += 1
        else:
            task_stats.success_metrics.failure += 1
        
        # 更新assisted统计
        if had_assistance:
            task_stats.success_metrics.tests_with_assistance += 1
            task_stats.success_metrics.total_assisted_turns += format_help_turns
            if success_level in ['full_success', 'partial_success']:
                task_stats.success_metrics.assisted_success += 1
            else:
                task_stats.success_metrics.assisted_failure += 1
        
        # Update score metrics for task type
        if 'workflow_score' in test_record and test_record['workflow_score'] is not None:
            task_stats.score_metrics.workflow_scores.update(test_record['workflow_score'])
        if 'phase2_score' in test_record and test_record['phase2_score'] is not None:
            task_stats.score_metrics.phase2_scores.update(test_record['phase2_score'])
        if 'quality_score' in test_record and test_record['quality_score'] is not None:
            task_stats.score_metrics.quality_scores.update(test_record['quality_score'])
        if 'final_score' in test_record and test_record['final_score'] is not None:
            task_stats.score_metrics.final_scores.update(test_record['final_score'])
        
        # Update execution metrics for task type
        if 'execution_time' in test_record and test_record['execution_time'] is not None and test_record['execution_time'] > 0:
            task_stats.execution_metrics.execution_times.update(test_record['execution_time'])
        if 'turns' in test_record and test_record['turns'] is not None and test_record['turns'] > 0:
            task_stats.execution_metrics.turns_used.update(test_record['turns'])
        
        # Update tool usage tracking for task type
        tools_to_track = test_record.get('executed_tools', test_record.get('tool_calls', []))
        if tools_to_track:
            if isinstance(tools_to_track, list):
                task_stats.execution_metrics.tool_calls.update(len(tools_to_track))
                task_stats.execution_metrics.total_tool_invocations += len(tools_to_track)
                for tool in tools_to_track:
                    if tool:
                        task_stats.execution_metrics.tools_used[tool] = task_stats.execution_metrics.tools_used.get(tool, 0) + 1
                task_stats.execution_metrics.unique_tools_count = len(task_stats.execution_metrics.tools_used)
            else:
                task_stats.execution_metrics.tool_calls.update(tools_to_track)
        
        # Update error metrics for task type
        if 'error_message' in test_record and test_record['error_message']:
            task_stats.error_metrics.categorize_error(test_record['error_message'])
        
        # Update task's prompt breakdown
        prompt_type = test_record.get('prompt_type', 'unknown')
        # 使用effective_prompt_type来处理flawed类型
        effective_prompt_type = prompt_type
        if test_record.get('is_flawed', False) and test_record.get('flaw_type'):
            effective_prompt_type = f"flawed_{test_record['flaw_type']}"
        
        if effective_prompt_type not in task_stats.prompt_breakdowns:
            task_stats.prompt_breakdowns[effective_prompt_type] = SuccessMetrics()
        # 原有统计
        task_stats.prompt_breakdowns[effective_prompt_type].total_tests += 1
        if success_level == 'full_success':
            task_stats.prompt_breakdowns[effective_prompt_type].full_success += 1
        elif success_level == 'partial_success':
            task_stats.prompt_breakdowns[effective_prompt_type].partial_success += 1
        else:
            task_stats.prompt_breakdowns[effective_prompt_type].failure += 1
        # assisted统计
        if had_assistance:
            task_stats.prompt_breakdowns[effective_prompt_type].tests_with_assistance += 1
            task_stats.prompt_breakdowns[effective_prompt_type].total_assisted_turns += format_help_turns
            if success_level in ['full_success', 'partial_success']:
                task_stats.prompt_breakdowns[effective_prompt_type].assisted_success += 1
            else:
                task_stats.prompt_breakdowns[effective_prompt_type].assisted_failure += 1
        
        # Update breakdown by prompt type
        # 如果是flawed测试，将flaw_type合并到prompt_type中
        effective_prompt_type = prompt_type
        if test_record.get('is_flawed', False) and test_record.get('flaw_type'):
            # 将flawed_<type>作为独立的prompt_type
            effective_prompt_type = f"flawed_{test_record['flaw_type']}"
        
        if effective_prompt_type not in self.by_prompt_type:
            self.by_prompt_type[effective_prompt_type] = PromptTypeStats(prompt_type=effective_prompt_type)
        
        prompt_stats = self.by_prompt_type[effective_prompt_type]
        # 原有统计
        prompt_stats.success_metrics.total_tests += 1
        if success_level == 'full_success':
            prompt_stats.success_metrics.full_success += 1
        elif success_level == 'partial_success':
            prompt_stats.success_metrics.partial_success += 1
        else:
            prompt_stats.success_metrics.failure += 1
        # assisted统计
        if had_assistance:
            prompt_stats.success_metrics.tests_with_assistance += 1
            prompt_stats.success_metrics.total_assisted_turns += format_help_turns
            if success_level in ['full_success', 'partial_success']:
                prompt_stats.success_metrics.assisted_success += 1
            else:
                prompt_stats.success_metrics.assisted_failure += 1
        
        # Update score metrics for prompt type
        if 'workflow_score' in test_record and test_record['workflow_score'] is not None:
            prompt_stats.score_metrics.workflow_scores.update(test_record['workflow_score'])
        if 'phase2_score' in test_record and test_record['phase2_score'] is not None:
            prompt_stats.score_metrics.phase2_scores.update(test_record['phase2_score'])
        if 'quality_score' in test_record and test_record['quality_score'] is not None:
            prompt_stats.score_metrics.quality_scores.update(test_record['quality_score'])
        if 'final_score' in test_record and test_record['final_score'] is not None:
            prompt_stats.score_metrics.final_scores.update(test_record['final_score'])
        
        # Update execution metrics for prompt type
        if 'execution_time' in test_record and test_record['execution_time'] is not None and test_record['execution_time'] > 0:
            prompt_stats.execution_metrics.execution_times.update(test_record['execution_time'])
        if 'turns' in test_record and test_record['turns'] is not None and test_record['turns'] > 0:
            prompt_stats.execution_metrics.turns_used.update(test_record['turns'])
        
        # Update tool usage tracking for prompt type
        tools_to_track = test_record.get('executed_tools', test_record.get('tool_calls', []))
        if tools_to_track:
            if isinstance(tools_to_track, list):
                prompt_stats.execution_metrics.tool_calls.update(len(tools_to_track))
                prompt_stats.execution_metrics.total_tool_invocations += len(tools_to_track)
                for tool in tools_to_track:
                    if tool:
                        prompt_stats.execution_metrics.tools_used[tool] = prompt_stats.execution_metrics.tools_used.get(tool, 0) + 1
                prompt_stats.execution_metrics.unique_tools_count = len(prompt_stats.execution_metrics.tools_used)
            else:
                prompt_stats.execution_metrics.tool_calls.update(tools_to_track)
        
        # Update error metrics for prompt type - 无论成功与否都要分类错误
        if 'error_message' in test_record and test_record['error_message']:
            prompt_stats.error_metrics.categorize_error(test_record['error_message'])
        
        # NOTE: by_flaw_type统计已被合并到by_prompt_type中
        # 每个flawed_<type>现在都是一个独立的prompt_type
        # 保留这个代码以便向后兼容，但不再使用
        # if test_record.get('is_flawed', False) and test_record.get('flaw_type'):
        #     # 这部分代码已废弃，数据现在记录在by_prompt_type中
        
        # Update breakdown by difficulty
        difficulty = test_record.get('difficulty', 'unknown')
        if difficulty not in self.by_difficulty:
            self.by_difficulty[difficulty] = DifficultyStats(difficulty=difficulty)
        
        diff_stats = self.by_difficulty[difficulty]
        # 原有统计
        diff_stats.success_metrics.total_tests += 1
        if success_level == 'full_success':
            diff_stats.success_metrics.full_success += 1
        elif success_level == 'partial_success':
            diff_stats.success_metrics.partial_success += 1
        else:
            diff_stats.success_metrics.failure += 1
        # assisted统计
        if had_assistance:
            diff_stats.success_metrics.tests_with_assistance += 1
            diff_stats.success_metrics.total_assisted_turns += format_help_turns
            if success_level in ['full_success', 'partial_success']:
                diff_stats.success_metrics.assisted_success += 1
            else:
                diff_stats.success_metrics.assisted_failure += 1
        
        # Update tool reliability sensitivity if specified
        tool_reliability = test_record.get('tool_reliability', 0.8)
        # 直接使用原始值，不分桶（因为通常只测试0.6, 0.7, 0.8, 0.9）
        if tool_reliability not in self.by_tool_reliability:
            self.by_tool_reliability[tool_reliability] = SuccessMetrics()
        
        reliability_stats = self.by_tool_reliability[tool_reliability]
        # 原有统计
        reliability_stats.total_tests += 1
        if success_level == 'full_success':
            reliability_stats.full_success += 1
        elif success_level == 'partial_success':
            reliability_stats.partial_success += 1
        else:
            reliability_stats.failure += 1
        # assisted统计
        if had_assistance:
            reliability_stats.tests_with_assistance += 1
            reliability_stats.total_assisted_turns += format_help_turns
            if success_level in ['full_success', 'partial_success']:
                reliability_stats.assisted_success += 1
            else:
                reliability_stats.assisted_failure += 1
        
        # Calculate prompt sensitivity index
        self._update_prompt_sensitivity()
    
    def _update_prompt_sensitivity(self):
        """Calculate prompt sensitivity index and best prompt type"""
        if len(self.by_prompt_type) < 2:
            self.prompt_sensitivity_index = 0.0
            return
        
        success_rates = []
        best_rate = 0.0
        
        for prompt_type, stats in self.by_prompt_type.items():
            rate = stats.success_metrics.weighted_success_score
            success_rates.append(rate)
            if rate > best_rate:
                best_rate = rate
                self.best_prompt_type = prompt_type
        
        # Sensitivity index = std deviation of success rates
        if len(success_rates) > 1:
            mean_rate = sum(success_rates) / len(success_rates)
            variance = sum((r - mean_rate) ** 2 for r in success_rates) / len(success_rates)
            self.prompt_sensitivity_index = variance ** 0.5
    
    def get_experiment_metrics(self) -> Dict:
        """Get all metrics needed for experiment plan tables"""
        return {
            # Table 4.1.1 Main Performance Metrics
            "total_success_rate": self.overall_success.success_rate,
            "full_success_rate": self.overall_success.full_success_rate,
            "partial_success_rate": self.overall_success.partial_success_rate,
            "failure_rate": self.overall_success.failure_rate,
            "weighted_success_score": self.overall_success.weighted_success_score,
            
            # 新增：assisted统计（不影响原有成功率计算）
            "assisted_failure_count": self.overall_success.assisted_failure,
            "assisted_success_count": self.overall_success.assisted_success,
            "total_assisted_tests": self.overall_success.total_assisted_tests,
            "avg_assisted_turns": self.overall_success.avg_assisted_turns,
            "assisted_success_rate": self.overall_success.assisted_success_rate,
            "assistance_rate": self.overall_success.assistance_rate,
            "avg_execution_steps": self.overall_execution.avg_turns,
            "tool_coverage_rate": self.overall_execution.tool_coverage_rate,
            
            # Table 4.1.2 Task Type Performance
            "basic_task_success": self.by_task_type.get('basic_task', TaskTypeStats('basic_task')).success_metrics.success_rate,
            "simple_task_success": self.by_task_type.get('simple_task', TaskTypeStats('simple_task')).success_metrics.success_rate,
            "data_pipeline_success": self.by_task_type.get('data_pipeline', TaskTypeStats('data_pipeline')).success_metrics.success_rate,
            "api_integration_success": self.by_task_type.get('api_integration', TaskTypeStats('api_integration')).success_metrics.success_rate,
            "multi_stage_pipeline_success": self.by_task_type.get('multi_stage_pipeline', TaskTypeStats('multi_stage_pipeline')).success_metrics.success_rate,
            
            # Table 4.3.1 Robustness Metrics (Flaw Adaptation)
            "sequence_disorder_success": self.by_flaw_type.get('sequence_disorder', FlawTypeStats('sequence_disorder')).success_metrics.success_rate,
            "tool_misuse_success": self.by_flaw_type.get('tool_misuse', FlawTypeStats('tool_misuse')).success_metrics.success_rate,
            "parameter_error_success": self.by_flaw_type.get('parameter_error', FlawTypeStats('parameter_error')).success_metrics.success_rate,
            "missing_step_success": self.by_flaw_type.get('missing_step', FlawTypeStats('missing_step')).success_metrics.success_rate,
            "redundant_operations_success": self.by_flaw_type.get('redundant_operations', FlawTypeStats('redundant_operations')).success_metrics.success_rate,
            "logical_inconsistency_success": self.by_flaw_type.get('logical_inconsistency', FlawTypeStats('logical_inconsistency')).success_metrics.success_rate,
            "semantic_drift_success": self.by_flaw_type.get('semantic_drift', FlawTypeStats('semantic_drift')).success_metrics.success_rate,
            
            # Table 4.3.2 Tool Reliability Sensitivity
            "tool_reliability_90": self.by_tool_reliability.get(0.9, SuccessMetrics()).success_rate,
            "tool_reliability_80": self.by_tool_reliability.get(0.8, SuccessMetrics()).success_rate,
            "tool_reliability_70": self.by_tool_reliability.get(0.7, SuccessMetrics()).success_rate,
            "tool_reliability_60": self.by_tool_reliability.get(0.6, SuccessMetrics()).success_rate,
            
            # Table 4.4.1 Prompt Type Sensitivity
            "baseline_prompt_success": self.by_prompt_type.get('baseline', PromptTypeStats('baseline')).success_metrics.success_rate,
            "cot_prompt_success": self.by_prompt_type.get('cot', PromptTypeStats('cot')).success_metrics.success_rate,
            "optimal_prompt_success": self.by_prompt_type.get('optimal', PromptTypeStats('optimal')).success_metrics.success_rate,
            "flawed_prompt_success": self.by_prompt_type.get('flawed', PromptTypeStats('flawed')).success_metrics.success_rate,
            "prompt_sensitivity_index": self.prompt_sensitivity_index,
            "best_prompt_type": self.best_prompt_type,
            
            # Table 4.5.1 Error Pattern Analysis
            "tool_selection_error_rate": self.overall_errors.tool_selection_error_rate,
            "parameter_config_error_rate": self.overall_errors.parameter_error_rate,
            "sequence_order_error_rate": self.overall_errors.sequence_error_rate,
            "dependency_error_rate": self.overall_errors.dependency_error_rate,
            "tool_call_format_error_rate": self.overall_errors.tool_call_format_error_rate,  # 新增！
            "main_error_pattern": self._get_main_error_pattern(),
            
            # Additional metrics for scale analysis
            "avg_execution_time": self.overall_execution.avg_execution_time,
            "avg_tool_calls": self.overall_execution.avg_tool_calls,
            "total_tests": self.overall_success.total_tests,
        }
    
    def _get_main_error_pattern(self) -> str:
        """Identify the main error pattern"""
        if self.overall_errors.total_errors == 0:
            return "No errors"
        
        error_counts = {
            "Tool Selection": self.overall_errors.tool_selection_errors,
            "Parameter Config": self.overall_errors.parameter_config_errors,
            "Sequence Order": self.overall_errors.sequence_order_errors,
            "Dependencies": self.overall_errors.dependency_errors,
            "Timeout": self.overall_errors.timeout_errors,
            "Max Turns": self.overall_errors.max_turns_errors,
            "Tool Call Format": self.overall_errors.tool_call_format_errors,  # 新增
            "Other": self.overall_errors.other_errors,
        }
        
        return max(error_counts, key=error_counts.get)


@dataclass
class CumulativeDatabase:
    """The complete cumulative database structure"""
    version: str = "2.0"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Model statistics - the main data
    models: Dict[str, ModelStatistics] = field(default_factory=dict)
    
    # Global statistics
    total_tests_all_models: int = 0
    total_models_tested: int = 0
    
    def add_test_result(self, model_name: str, test_record: Dict):
        """Add a test result without storing the instance"""
        if model_name not in self.models:
            self.models[model_name] = ModelStatistics(model_name=model_name)
            self.total_models_tested = len(self.models)
        
        self.models[model_name].update_from_test(test_record)
        self.total_tests_all_models += 1
        self.last_updated = datetime.now().isoformat()
    
    def get_model_report(self, model_name: str) -> Optional[Dict]:
        """Get experiment metrics for a specific model"""
        if model_name not in self.models:
            return None
        return self.models[model_name].get_experiment_metrics()
    
    def get_all_models_summary(self) -> Dict:
        """Get summary of all models for experiment tables"""
        return {
            model_name: model_stats.get_experiment_metrics()
            for model_name, model_stats in self.models.items()
        }