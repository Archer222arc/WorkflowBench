#!/usr/bin/env python3
"""
Generalized MDP Framework for Tool Selection with Phase 2/3 Fixes
Enhanced with:
- TaskFeatures normalization
- Action selection fallback mechanism
- Improved error handling
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Set, Union
from enum import Enum
import json
import uuid
from datetime import datetime
import logging
import numpy as np
from collections import defaultdict
from pathlib import Path




# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ===========================
# Enums and Constants
# ===========================

class ActionType(Enum):
    """Types of actions available in the MDP"""
    INVOKE_TOOL = "invoke_tool"
    VALIDATE_OUTPUT = "validate_output"
    RETRY_TOOL = "retry_tool"
    RECOVER_ERROR = "recover_error"
    CHECK_DEPENDENCIES = "check_dependencies"
    CREATE_CHECKPOINT = "create_checkpoint"
    RESTORE_CHECKPOINT = "restore_checkpoint"
    NO_OP = "no_op"
    PARALLEL_EXECUTE = "parallel_execute"
    CONDITIONAL_BRANCH = "conditional_branch"


class ToolExecutionStatus(Enum):
    """Status of tool execution"""
    NOT_ATTEMPTED = "not_attempted"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    DEPENDENCY_FAILED = "dependency_failed"
    VALIDATION_FAILED = "validation_failed"
    RECOVERED = "recovered"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class ErrorCategory(Enum):
    """Categories of errors that can occur"""
    NONE = "none"
    TOOL_NOT_FOUND = "tool_not_found"
    INVALID_INPUT = "invalid_input"
    EXECUTION_ERROR = "execution_error"
    TIMEOUT_ERROR = "timeout_error"
    DEPENDENCY_ERROR = "dependency_error"
    VALIDATION_ERROR = "validation_error"
    RESOURCE_ERROR = "resource_error"
    PERMISSION_ERROR = "permission_error"
    NETWORK_ERROR = "network_error"
    UNKNOWN_ERROR = "unknown_error"


class TaskDomain(Enum):
    """High-level task domains for Phase 3"""
    GENERAL = "general"
    DATA_PROCESSING = "data_processing"
    API_INTEGRATION = "api_integration"
    FILE_OPERATIONS = "file_operations"
    VALIDATION = "validation"
    TRANSFORMATION = "transformation"
    AGGREGATION = "aggregation"


class TaskComplexity(Enum):
    """Task complexity levels for Phase 3"""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


class DataFlowState(Enum):
    """Data flow states for Phase 3"""
    EMPTY = "empty"
    INITIALIZED = "initialized"
    PARTIAL = "partial"
    TRANSFORMED = "transformed"
    VALIDATED = "validated"
    CORRUPTED = "corrupted"


# ===========================
# Utility Functions
# ===========================

def safe_getattr(obj: Any, attr_path: str, default: Any = None) -> Any:
    """
    Safely get nested attributes with fallback.
    Supports paths like 'attr.sub_attr.value'
    """
    try:
        attrs = attr_path.split('.')
        value = obj
        
        for attr in attrs:
            if hasattr(value, attr):
                value = getattr(value, attr)
            elif isinstance(value, dict) and attr in value:
                value = value[attr]
            else:
                return default
        
        return value
    except Exception:
        return default


def normalize_enum_value(value: Union[str, Enum], enum_class: type) -> Enum:
    """
    Normalize string or enum value to enum instance.
    """
    if isinstance(value, enum_class):
        return value
    
    if isinstance(value, str):
        # Try exact match first
        for enum_member in enum_class:
            if enum_member.value == value:
                return enum_member
        
        # Try case-insensitive match
        value_lower = value.lower()
        for enum_member in enum_class:
            if enum_member.value.lower() == value_lower:
                return enum_member
        
        # Try name match
        try:
            return enum_class[value.upper()]
        except KeyError:
            pass
    
    # Return default (first enum value)
    return list(enum_class)[0]


# ===========================
# Data Classes
# ===========================

@dataclass
class ToolCapability:
    """Represents the capabilities and requirements of a tool"""
    tool_name: str
    input_types: Dict[str, str]
    output_types: Dict[str, str]
    error_types: List[ErrorCategory] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    parallel_safe: bool = True
    idempotent: bool = True
    expected_duration: float = 1.0
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    semantic_operations: List[str] = field(default_factory=list)
    data_domains: List[str] = field(default_factory=list)


@dataclass
class TaskFeatures:
    """Semantic task features for enhanced state representation (Phase 3) - WITH NORMALIZATION FIX"""
    # Basic characteristics
    has_input_requirement: bool = False
    has_output_requirement: bool = False
    requires_validation: bool = False
    requires_transformation: bool = False
    requires_aggregation: bool = False
    requires_filtering: bool = False
    
    # Data characteristics
    data_volume: str = "small"  # small, medium, large
    data_variety: int = 1  # number of different data types
    quality_requirements: str = "standard"  # low, standard, high
    
    # Task metadata
    domain: TaskDomain = TaskDomain.GENERAL
    complexity: TaskComplexity = TaskComplexity.MODERATE
    estimated_steps: int = 3
    parallel_potential: float = 0.0  # 0-1 score
    error_sensitivity: float = 0.5  # 0-1 score
    
    def to_vector(self) -> np.ndarray:
        """Convert features to normalized numerical vector"""
        # Binary features (6)
        binary_features = [
            float(self.has_input_requirement),
            float(self.has_output_requirement),
            float(self.requires_validation),
            float(self.requires_transformation),
            float(self.requires_aggregation),
            float(self.requires_filtering)
        ]
        
        # Categorical features encoded
        volume_encoding = {"small": 0.0, "medium": 0.5, "large": 1.0}
        quality_encoding = {"low": 0.0, "standard": 0.5, "high": 1.0}
        
        # Domain encoding (one-hot, 7 dimensions)
        domain_vector = [0.0] * len(TaskDomain)
        domain_idx = list(TaskDomain).index(self.domain)
        domain_vector[domain_idx] = 1.0
        
        # Complexity encoding (ordinal)
        complexity_map = {
            TaskComplexity.SIMPLE: 0.0,
            TaskComplexity.MODERATE: 0.33,
            TaskComplexity.COMPLEX: 0.67,
            TaskComplexity.VERY_COMPLEX: 1.0
        }
        
        # Combine all features
        vector = (
            binary_features +  # 6
            [volume_encoding.get(self.data_volume, 0.5)] +  # 1
            [self.data_variety / 10.0] +  # 1, normalized
            [quality_encoding.get(self.quality_requirements, 0.5)] +  # 1
            domain_vector +  # 7
            [complexity_map.get(self.complexity, 0.5)] +  # 1
            [self.estimated_steps / 20.0] +  # 1, normalized
            [self.parallel_potential] +  # 1
            [self.error_sensitivity]  # 1
        )
        
        vector = np.array(vector, dtype=np.float32)  # Total: 20 dimensions
        
        # NORMALIZATION FIX: Normalize the vector to have zero mean and unit variance
        # This prevents training instability
        if vector.std() > 0:
            vector = (vector - vector.mean()) / (vector.std() + 1e-8)
        
        return vector


@dataclass
class GeneralizedMDPState:
    """Enhanced MDP state with task-aware features (Phase 3)"""
    # Task identification
    task_id: str
    task_type: str
    task_objective: str
    
    # Tool execution state
    tool_states: Dict[str, ToolExecutionStatus] = field(default_factory=dict)
    tool_outputs: Dict[str, Any] = field(default_factory=dict)
    tool_errors: Dict[str, ErrorCategory] = field(default_factory=dict)
    retry_counts: Dict[str, int] = field(default_factory=dict)
    
    # Progress tracking - MODIFIED FOR BETTER GRANULARITY
    overall_progress: float = 0.0
    workflow_step: int = 0
    execution_sequence: List[str] = field(default_factory=list)
    subtask_progress: Dict[str, float] = field(default_factory=dict)
    
    # Milestone tracking - NEW FOR BETTER PROGRESS
    milestones_achieved: Set[str] = field(default_factory=set)
    expected_milestones: Set[str] = field(default_factory=set)
    
    # Error handling
    consecutive_errors: int = 0
    total_errors: int = 0
    error_history: List[Tuple[str, ErrorCategory]] = field(default_factory=list)
    
    # Validation and stages
    validations_performed: List[str] = field(default_factory=list)
    validation_results: Dict[str, bool] = field(default_factory=dict)
    current_stage: int = 0
    stage_progress: Dict[int, float] = field(default_factory=dict)
    
    # Completion state - MODIFIED THRESHOLDS
    is_completed: bool = False
    is_successful: bool = False
    partial_success: bool = False
    recovery_count: int = 0
    
    # Time tracking
    start_time: datetime = field(default_factory=datetime.now)
    elapsed_time: float = 0.0
    tool_timings: Dict[str, float] = field(default_factory=dict)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidence_score: float = 1.0
    
    # Phase 3 additions
    task_features: Optional['TaskFeatures'] = None
    semantic_milestones: List[str] = field(default_factory=list)
    data_flow_state: DataFlowState = DataFlowState.EMPTY
    tool_synergy_score: float = 0.0
    
    # RAG and semantic search additions  # <- 新增注释
    rag_search_results: Dict[str, List[Tuple[str, float]]] = field(default_factory=dict)  # <- 新增这一行
    tool_candidates: Dict[str, List[str]] = field(default_factory=dict)  # <- 新增这一行
    semantic_confidence_scores: Dict[str, float] = field(default_factory=dict)  # <- 新增这一行
    tool_selection_history: List[Dict[str, Any]] = field(default_factory=list)  # <- 新增这一行

    # 新增：嵌入搜索缓存
    embedding_search_cache: Dict[str, float] = field(default_factory=dict)  # <- 新增这一行
    
    def __post_init__(self):
        """Initialize task features if not provided"""
        if self.task_features is None:
            self.task_features = self._extract_task_features()
        
        # Initialize expected milestones based on task
        if not self.expected_milestones:
            self._initialize_expected_milestones()
    
    def _extract_task_features(self) -> TaskFeatures:
        """Extract semantic features from task objective"""
        objective_lower = self.task_objective.lower()
        
        features = TaskFeatures()
        
        # Analyze task objective for requirements
        features.has_input_requirement = any(
            keyword in objective_lower 
            for keyword in ['read', 'load', 'import', 'fetch', 'get']
        )
        features.has_output_requirement = any(
            keyword in objective_lower 
            for keyword in ['write', 'save', 'export', 'store', 'output']
        )
        features.requires_validation = any(
            keyword in objective_lower 
            for keyword in ['validat', 'verify', 'check', 'ensure', 'confirm']
        )
        features.requires_transformation = any(
            keyword in objective_lower 
            for keyword in ['transform', 'convert', 'process', 'modify', 'change']
        )
        features.requires_aggregation = any(
            keyword in objective_lower 
            for keyword in ['aggregat', 'combin', 'merg', 'join', 'sum', 'collect']
        )
        features.requires_filtering = any(
            keyword in objective_lower 
            for keyword in ['filter', 'select', 'extract', 'find', 'search']
        )
        
        # Estimate complexity based on requirements
        requirement_count = sum([
            features.has_input_requirement,
            features.has_output_requirement,
            features.requires_validation,
            features.requires_transformation,
            features.requires_aggregation,
            features.requires_filtering
        ])
        
        if requirement_count <= 2:
            features.complexity = TaskComplexity.SIMPLE
            features.estimated_steps = 3
        elif requirement_count <= 3:
            features.complexity = TaskComplexity.MODERATE
            features.estimated_steps = 5
        elif requirement_count <= 4:
            features.complexity = TaskComplexity.COMPLEX
            features.estimated_steps = 8
        else:
            features.complexity = TaskComplexity.VERY_COMPLEX
            features.estimated_steps = 12
        
        # Determine domain
        if any(kw in objective_lower for kw in ['api', 'endpoint', 'request']):
            features.domain = TaskDomain.API_INTEGRATION
        elif any(kw in objective_lower for kw in ['file', 'csv', 'json', 'xml']):
            features.domain = TaskDomain.FILE_OPERATIONS
        elif features.requires_validation:
            features.domain = TaskDomain.VALIDATION
        elif features.requires_transformation:
            features.domain = TaskDomain.TRANSFORMATION
        elif features.requires_aggregation:
            features.domain = TaskDomain.AGGREGATION
        else:
            features.domain = TaskDomain.DATA_PROCESSING
        
        return features
    
    def _initialize_expected_milestones(self):
        """Initialize expected milestones based on task features"""
        if self.task_features.has_input_requirement:
            self.expected_milestones.add("data_loaded")
        if self.task_features.requires_validation:
            self.expected_milestones.add("data_validated")
        if self.task_features.requires_transformation:
            self.expected_milestones.add("data_transformed")
        if self.task_features.requires_aggregation:
            self.expected_milestones.add("data_aggregated")
        if self.task_features.requires_filtering:
            self.expected_milestones.add("data_filtered")
        if self.task_features.has_output_requirement:
            self.expected_milestones.add("data_exported")
    
    def _calculate_data_coherence(self) -> float:
        """Calculate data flow coherence score"""
        if self.data_flow_state == DataFlowState.EMPTY:
            return 0.0
        elif self.data_flow_state == DataFlowState.CORRUPTED:
            return -0.5
        elif self.data_flow_state == DataFlowState.PARTIAL:
            return 0.3
        elif self.data_flow_state == DataFlowState.INITIALIZED:
            return 0.5
        elif self.data_flow_state == DataFlowState.TRANSFORMED:
            return 0.7
        elif self.data_flow_state == DataFlowState.VALIDATED:
            return 1.0
        return 0.0
    
    def get_completed_tools(self) -> List[str]:
        """Get list of successfully completed tools"""
        return [tool for tool, status in self.tool_states.items() 
                if status == ToolExecutionStatus.SUCCESS]
    
    def get_failed_tools(self) -> List[str]:
        """Get list of failed tools"""
        return [tool for tool, status in self.tool_states.items() 
                if status == ToolExecutionStatus.FAILED]
    
    def create_checkpoint(self) -> Dict[str, Any]:
        """Create a checkpoint of current state"""
        return {
            'checkpoint_id': str(uuid.uuid4()),
            'timestamp': datetime.now().isoformat(),
            'state': self.to_dict()
        }
    
    def restore_from_checkpoint(self, checkpoint: Dict[str, Any]):
        """Restore state from checkpoint"""
        if 'state' in checkpoint:
            state_data = checkpoint['state']
            # Restore relevant fields
            self.tool_states = {k: ToolExecutionStatus(v) for k, v in state_data.get('tool_states', {}).items()}
            self.overall_progress = state_data.get('overall_progress', 0.0)
            self.workflow_step = state_data.get('workflow_step', 0)
            self.milestones_achieved = set(state_data.get('milestones_achieved', []))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary"""
        base_dict = {
            'task_id': self.task_id,
            'task_type': self.task_type,
            'task_objective': self.task_objective,
            'tool_states': {k: v.value for k, v in self.tool_states.items()},
            'overall_progress': self.overall_progress,
            'workflow_step': self.workflow_step,
            'consecutive_errors': self.consecutive_errors,
            'is_completed': self.is_completed,
            'is_successful': self.is_successful,
            'milestones_achieved': list(self.milestones_achieved),
            'expected_milestones': list(self.expected_milestones)
        }
        
        # Add task features
        if self.task_features:
            base_dict['task_features'] = {
                'has_input_requirement': self.task_features.has_input_requirement,
                'has_output_requirement': self.task_features.has_output_requirement,
                'requires_validation': self.task_features.requires_validation,
                'requires_transformation': self.task_features.requires_transformation,
                'requires_aggregation': self.task_features.requires_aggregation,
                'requires_filtering': self.task_features.requires_filtering,
                'data_volume': self.task_features.data_volume,
                'data_variety': self.task_features.data_variety,
                'quality_requirements': self.task_features.quality_requirements,
                'domain': self.task_features.domain.value,
                'complexity': self.task_features.complexity.value,
                'estimated_steps': self.task_features.estimated_steps,
                'parallel_potential': self.task_features.parallel_potential,
                'error_sensitivity': self.task_features.error_sensitivity
            }
        base_dict['data_flow_state'] = self.data_flow_state.value if isinstance(self.data_flow_state, Enum) else self.data_flow_state
        base_dict['semantic_milestones'] = self.semantic_milestones
        
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GeneralizedMDPState':
        """Create state from dictionary with task features"""
        # Create base state
        state = cls(
            task_id=data.get('task_id', 'unknown'),
            task_type=data.get('task_type', 'unknown'),
            task_objective=data.get('task_objective', 'Complete task')
        )
        
        # Restore task features
        if 'task_features' in data:
            tf_data = data['task_features']
            state.task_features = TaskFeatures(
                has_input_requirement=tf_data.get('has_input_requirement', False),
                has_output_requirement=tf_data.get('has_output_requirement', False),
                requires_validation=tf_data.get('requires_validation', False),
                requires_transformation=tf_data.get('requires_transformation', False),
                requires_aggregation=tf_data.get('requires_aggregation', False),
                requires_filtering=tf_data.get('requires_filtering', False),
                data_volume=tf_data.get('data_volume', 'small'),
                data_variety=tf_data.get('data_variety', 1),
                quality_requirements=tf_data.get('quality_requirements', 'standard'),
                domain=normalize_enum_value(tf_data.get('domain', 'general'), TaskDomain),
                complexity=normalize_enum_value(tf_data.get('complexity', 'moderate'), TaskComplexity),
                estimated_steps=tf_data.get('estimated_steps', 3),
                parallel_potential=tf_data.get('parallel_potential', 0.0),
                error_sensitivity=tf_data.get('error_sensitivity', 0.5)
            )
        
        # Restore simple fields
        state.overall_progress = float(data.get('overall_progress', 0.0))
        state.workflow_step = int(data.get('workflow_step', 0))
        state.consecutive_errors = int(data.get('consecutive_errors', 0))
        state.is_completed = bool(data.get('is_completed', False))
        state.is_successful = bool(data.get('is_successful', False))
        
        # Restore milestones
        state.milestones_achieved = set(data.get('milestones_achieved', []))
        state.expected_milestones = set(data.get('expected_milestones', []))
        
        # Restore tool states
        tool_states = data.get('tool_states', {})
        for tool, status in tool_states.items():
            state.tool_states[tool] = ToolExecutionStatus(status)
        
        # Restore data flow state
        dfs_value = data.get('data_flow_state', 'empty')
        state.data_flow_state = normalize_enum_value(dfs_value, DataFlowState)
        
        state.semantic_milestones = data.get('semantic_milestones', [])
        
        return state
    
    def should_recover(self) -> bool:
        """Determine if recovery is needed"""
        return (self.consecutive_errors >= 3 or 
                any(err == ErrorCategory.EXECUTION_ERROR for _, err in self.error_history[-3:]))


# Phase 3: Task-aware state subclass
class TaskAwareMDPState(GeneralizedMDPState):
    """Extended state with Phase 3 task-aware features"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Additional task-aware attributes initialized in parent __post_init__



@dataclass
class GeneralizedAction:
    """Action representation with Phase 3 improvements"""
    action_type: ActionType
    tool_name: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    expected_outcome: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    
    # RAG-enhanced action attributes  # <- 新增注释
    semantic_score: float = 0.0  # <- 新增这一行
    search_source: str = "rule_based"  # <- 新增这一行 (rule_based, embedding_search, hybrid)
    alternative_tools: List[str] = field(default_factory=list)  # <- 新增这一行
    
    def __hash__(self):
        """Make action hashable for use in sets/dicts"""
        return hash((self.action_type, self.tool_name))
    
    def __eq__(self, other):
        """Equality comparison"""
        if not isinstance(other, GeneralizedAction):
            return False
        return (self.action_type == other.action_type and 
                self.tool_name == other.tool_name)
    
    def __str__(self):
        """String representation"""
        if self.tool_name:
            return f"{self.action_type.value}({self.tool_name})"
        return self.action_type.value


# ===========================
# Enhanced MDP Logic
# ===========================
# 文件：generalized_mdp_framework.py  
# 位置：第650-680行左右
# 完整的修复后的__init__方法相关部分

class GeneralizedMDP:
    """Enhanced MDP for tool selection with improved completion criteria and fallback mechanism"""
    
    def __init__(self, tool_capabilities: Dict[str, ToolCapability], 
                reward_config: Optional[Dict[str, float]] = None,
                completion_thresholds: Optional[Dict[str, float]] = None,
                use_embeddings: bool = True):
        self.tool_capabilities = tool_capabilities
        self.use_embeddings = use_embeddings

        # 初始化工具能力管理器
        from tool_capability_manager import ToolCapabilityManager
        self.tool_capability_manager = ToolCapabilityManager()
        print(f"[GeneralizedMDP] Initialized tool_capability_manager")
        
        # 修改奖励配置 - 激活RAG奖励组件
        self.reward_config = reward_config or {
            'success_reward': 10.0,
            'failure_penalty': 0.0,
            'progress_reward': 2.0,
            'efficiency_bonus': 3.0,
            'redundancy_penalty': 0.0,
            'error_recovery_bonus': 5.0,
            'validation_success_bonus': 2.0,
            'checkpoint_bonus': 0.0,
            'milestone_bonus': 0.0,
            # RAG增强奖励 - 激活并调整权重
            'semantic_alignment_bonus': 1.5,
            'data_flow_coherence_bonus': 1.0,
            'rag_guidance_bonus': 2.0,
            'pattern_completion_bonus': 1.5,
            'milestone_achievement_bonus': 0.0,
            'tool_synergy_bonus': 0.0
        }
        
        # 动态完成阈值 - 根据课程阶段调整
        self.base_completion_thresholds = completion_thresholds or {  # 修复：改为base_completion_thresholds
            'minimum_progress': 0.7,
            'maximum_steps': 50,
            'maximum_errors': 10,
            'minimum_milestones': 0.6,
            'validation_required': True
        }
        
        # 根据课程阶段调整阈值
        self.completion_thresholds = self._adjust_thresholds_for_curriculum()  # 现在可以正常工作
        
        # Build tool dependency graph
        self._build_dependency_graph()
        self._build_semantic_groupings()
        self.successful_patterns = defaultdict(float)
        self.task_tool_preferences = defaultdict(lambda: defaultdict(float))
        self.pattern_occurrence_count = defaultdict(int)
        self.episode_history = []
        
        # 工具成功率统计
        self.tool_success_rates = defaultdict(lambda: {'success': 0, 'total': 0})
        self.tool_criticality_scores = defaultdict(float)
        self.tool_failure_impact = defaultdict(float)
        self.tool_position_importance = defaultdict(lambda: defaultdict(float))
        self.learned_critical_patterns = []
        
        # Initialize embedding manager if requested
        self.embedding_manager = None
        if self.use_embeddings:
            self._initialize_embedding_manager()

# 文件：generalized_mdp_framework.py
# 位置：第690-730行左右  
# 完整的_adjust_thresholds_for_curriculum方法

    def _adjust_thresholds_for_curriculum(self) -> Dict[str, Any]:
        """根据课程阶段调整完成阈值"""
        # 默认课程阶段为0，如果没有设置
        if not hasattr(self, 'curriculum_stage'):
            self.curriculum_stage = 0
            
        print(f"[CURRICULUM] Adjusting thresholds for stage {self.curriculum_stage}")
        
        # 创建阈值副本
        thresholds = self.base_completion_thresholds.copy()  # 修复：使用base_completion_thresholds
        
        if self.curriculum_stage == 0:  # Very Easy 阶段：极度宽松
            thresholds['minimum_progress'] = 0.1      # 极低进度要求
            thresholds['maximum_steps'] = 150        # 给予充足步数
            thresholds['maximum_errors'] = 50        # 容忍大量错误
            thresholds['minimum_milestones'] = 0.0   # 不要求里程碑
            thresholds['validation_required'] = False # 不要求验证
            thresholds['minimum_tools'] = 1          # 至少执行1个工具
            thresholds['required_tools_coverage'] = 0.2  # 20%的required_tools即可
            print(f"[CURRICULUM] Stage 0 (Very Easy): Minimal requirements")
            
        elif self.curriculum_stage == 1:  # Easy 阶段：较宽松
            thresholds['minimum_progress'] = 0.3
            thresholds['maximum_steps'] = 100
            thresholds['maximum_errors'] = 30
            thresholds['minimum_milestones'] = 0.2
            thresholds['validation_required'] = False
            thresholds['minimum_tools'] = 2
            thresholds['required_tools_coverage'] = 0.4  # 40%的required_tools
            print(f"[CURRICULUM] Stage 1 (Easy): Basic requirements")
            
        elif self.curriculum_stage == 2:  # Medium 阶段：适度要求
            thresholds['minimum_progress'] = 0.5
            thresholds['maximum_steps'] = 75
            thresholds['maximum_errors'] = 20
            thresholds['minimum_milestones'] = 0.4
            thresholds['validation_required'] = True
            thresholds['minimum_tools'] = 3
            thresholds['required_tools_coverage'] = 0.7  # 70%的required_tools
            print(f"[CURRICULUM] Stage 2 (Medium): Moderate requirements")
            
        elif self.curriculum_stage == 3:  # Hard 阶段：接近标准
            thresholds['minimum_progress'] = 0.7
            thresholds['maximum_steps'] = 60
            thresholds['maximum_errors'] = 15
            thresholds['minimum_milestones'] = 0.6
            thresholds['validation_required'] = True
            thresholds['minimum_tools'] = 4
            thresholds['required_tools_coverage'] = 0.9  # 90%的required_tools
            print(f"[CURRICULUM] Stage 3 (Hard): Near-standard requirements")
            
        else:  # curriculum_stage >= 4：完全标准（Phase 2要求）
            thresholds['required_tools_coverage'] = 1.0  # 100%的required_tools
            thresholds['minimum_tools'] = None  # 使用任务定义的要求
            print(f"[CURRICULUM] Stage 4+ (All): Full Phase 2 requirements")
        
        print(f"[CURRICULUM] Stage {self.curriculum_stage} thresholds: "
            f"progress={thresholds['minimum_progress']}, "
            f"errors={thresholds['maximum_errors']}, "
            f"req_coverage={thresholds.get('required_tools_coverage', 1.0)}")
        
        return thresholds
    
    def set_curriculum_stage(self, stage: int):
        """更新课程阶段并调整阈值"""
        self.curriculum_stage = stage
        self.completion_thresholds = self._adjust_thresholds_for_curriculum()
        print(f"[CURRICULUM] Updated to stage {stage}")

    def _initialize_embedding_manager(self):
        """Initialize the embedding manager for semantic tool search"""
        from mcp_embedding_manager import MCPEmbeddingManager
        
        self.embedding_manager = MCPEmbeddingManager()
        
        # Try to load existing index
        index_path = Path(".mcp_embedding_cache/tool_index.pkl")
        
        # 检查文件是否存在
        print(f"[INFO] Found embedding index at {index_path}")
        # 尝试加载索引
        self.embedding_manager.load_index(index_path)
        print(f"[SUCCESS] Loaded embedding index with {len(self.embedding_manager.tool_embeddings)} tools")
        logger.info(f"Embedding index loaded successfully")
        
        # 验证加载的数据
        if not self.embedding_manager.tool_embeddings:
            print("[WARNING] Loaded index is empty, will try to rebuild")
            raise ValueError("Empty tool embeddings after loading")



            

    
    def _determine_tool_category(self, capability: ToolCapability) -> str:
        """Determine tool category from semantic operations"""
        for operation in capability.semantic_operations:
            if 'read' in operation or 'load' in operation:
                return 'input'
            elif 'validat' in operation:
                return 'validation'
            elif 'transform' in operation or 'convert' in operation:
                return 'transformation'
            elif 'aggregat' in operation or 'combin' in operation:
                return 'aggregation'
            elif 'write' in operation or 'export' in operation:
                return 'output'
        return 'general'
    
    def _build_dependency_graph(self):
        """Build dependency relationships between tools"""
        self.dependency_graph = {}
        for tool_name, capability in self.tool_capabilities.items():
            self.dependency_graph[tool_name] = capability.dependencies
    
    def _build_semantic_groupings(self):
        """Build semantic groupings for Phase 3"""
        self.semantic_groups = {
            'input': [],
            'validation': [],
            'transformation': [],
            'aggregation': [],
            'output': []
        }
        
        for tool_name, capability in self.tool_capabilities.items():
            for operation in capability.semantic_operations:
                if 'read' in operation or 'load' in operation:
                    self.semantic_groups['input'].append(tool_name)
                elif 'validat' in operation:
                    self.semantic_groups['validation'].append(tool_name)
                elif 'transform' in operation or 'convert' in operation:
                    self.semantic_groups['transformation'].append(tool_name)
                elif 'aggregat' in operation or 'combin' in operation:
                    self.semantic_groups['aggregation'].append(tool_name)
                elif 'write' in operation or 'export' in operation:
                    self.semantic_groups['output'].append(tool_name)



    def _calculate_semantic_confidence(self, state: GeneralizedMDPState, 
                                    tool_name: str, capability: ToolCapability) -> float:
        """Calculate semantic confidence for tool selection with pattern learning and embeddings"""
        base_confidence = 0.5
        
        # 1. Embedding-based semantic similarity with CACHING
        if self.embedding_manager and hasattr(state, 'task_objective'):
            # Check if we already have cached embedding search results
            if not hasattr(state, 'embedding_search_cache'):
                # This should not happen if _initialize_embedding_cache was called
                print(f"[WARNING] No embedding cache found, performing search...")
                try:
                    search_query = f"{state.task_objective} {state.task_type}"
                    search_results = self.embedding_manager.search(
                        query=search_query,
                        k=30,
                        return_scores=True
                    )
                    
                    # Build cache
                    state.embedding_search_cache = {}
                    for result in search_results:
                        state.embedding_search_cache[result.tool_name] = result.score
                    
                    state.rag_search_results = {}
                    
                except Exception as e:
                    logger.debug(f"Embedding search failed: {e}, falling back to rule-based")
                    state.embedding_search_cache = {}
            
            # Use cached results - O(1) lookup instead of search
            if hasattr(state, 'embedding_search_cache') and tool_name in state.embedding_search_cache:
                embedding_confidence = state.embedding_search_cache[tool_name]
                base_confidence = base_confidence * 0.4 + embedding_confidence * 0.6
                
                # Store results by semantic operation (using cached score)
                if not hasattr(state, 'rag_search_results'):
                    state.rag_search_results = {}
                
                for operation in capability.semantic_operations:
                    if operation not in state.rag_search_results:
                        state.rag_search_results[operation] = []
                    state.rag_search_results[operation].append((tool_name, embedding_confidence))
        
        # 2. Task feature alignment (original logic)
        if hasattr(state, 'task_features') and state.task_features:
            task_features = state.task_features
            for operation in capability.semantic_operations:
                if task_features.has_input_requirement and ('read' in operation or 'load' in operation):
                    base_confidence += 0.1
                elif task_features.has_output_requirement and ('write' in operation or 'export' in operation):
                    base_confidence += 0.1
                elif task_features.requires_validation and 'validat' in operation:
                    base_confidence += 0.1
                elif task_features.requires_transformation and 'transform' in operation:
                    base_confidence += 0.1
                elif task_features.requires_aggregation and 'aggregat' in operation:
                    base_confidence += 0.1
        
        # 3. Pattern-based confidence boost (original logic)
        if len(state.execution_sequence) >= 2:
            # Check if this forms a known successful pattern
            recent_pattern = '->'.join(state.execution_sequence[-2:] + [tool_name])
            if recent_pattern in self.successful_patterns:
                pattern_confidence = self.successful_patterns[recent_pattern]
                base_confidence = max(base_confidence, pattern_confidence * 0.8)
        
        # 4. Task-specific tool preference (original logic)
        if hasattr(state, 'task_type') and state.task_type in self.task_tool_preferences:
            task_prefs = self.task_tool_preferences[state.task_type]
            if tool_name in task_prefs:
                preference_score = task_prefs[tool_name]
                base_confidence += preference_score * 0.2
        
        # 5. Dependency satisfaction boost (original logic)
        if capability.dependencies:
            all_deps_met = all(
                state.tool_states.get(dep) == ToolExecutionStatus.SUCCESS 
                for dep in capability.dependencies
            )
            if all_deps_met:
                base_confidence += 0.15
        
        # 6. Progress-based adjustment (original logic)
        if state.overall_progress < 0.3:  # Early stage
            # Prefer input/initialization tools
            if any('read' in op or 'load' in op for op in capability.semantic_operations):
                base_confidence += 0.1
        elif state.overall_progress > 0.7:  # Late stage
            # Prefer output/finalization tools
            if any('write' in op or 'export' in op for op in capability.semantic_operations):
                base_confidence += 0.1
        
        # 7. Penalty for failed attempts (original logic)
        if tool_name in state.retry_counts:
            retry_penalty = 0.1 * state.retry_counts[tool_name]
            base_confidence -= retry_penalty
        
        return min(1.0, max(0.1, base_confidence))

    def _initialize_embedding_cache(self, state: GeneralizedMDPState):
        """Pre-compute all embedding scores at the beginning of episode"""
        if not self.embedding_manager or not hasattr(state, 'task_objective'):
            return
        
        print(f"[INFO] Pre-computing embedding scores for all tools...")
        import time
        start_time = time.time()
        
        # Single search to get all relevant tools
        search_query = f"{state.task_objective} {state.task_type}"
        search_results = self.embedding_manager.search(
            query=search_query,
            k=len(self.tool_capabilities),  # Get scores for all tools
            return_scores=True
        )
        
        # Build cache
        state.embedding_search_cache = {}
        for result in search_results:
            state.embedding_search_cache[result.tool_name] = result.score
        
        # Initialize rag_search_results
        state.rag_search_results = {}
        
        elapsed = time.time() - start_time
        print(f"[INFO] Embedding cache initialized in {elapsed:.2f}s for {len(state.embedding_search_cache)} tools")



    def search_tools_by_semantic(self, query: str, k: int = 5, 
                               filter_available: bool = True,
                               state: Optional[GeneralizedMDPState] = None) -> List[Tuple[str, float]]:
        """
        Search for tools using semantic similarity
        
        Args:
            query: Search query describing the desired functionality
            k: Number of results to return
            filter_available: If True, only return tools that can be executed
            state: Current MDP state for filtering
            
        Returns:
            List of (tool_name, score) tuples
        """
        if not self.embedding_manager:
            logger.warning("Embedding manager not available, returning empty results")
            return []
        
        try:
            # Search for semantically similar tools
            search_results = self.embedding_manager.search(
                query=query,
                k=k * 2 if filter_available else k,  # Get more results if filtering
                return_scores=True
            )
            
            # Convert to tuples and filter if needed
            results = []
            for result in search_results:
                tool_name = result.tool_name
                
                # Filter based on availability if requested
                if filter_available and state:
                    # Skip if already executed successfully
                    if state.tool_states.get(tool_name) == ToolExecutionStatus.SUCCESS:
                        continue
                    
                    # Skip if dependencies not met
                    capability = self.tool_capabilities.get(tool_name)
                    if capability and capability.dependencies:
                        deps_met = all(
                            state.tool_states.get(dep) == ToolExecutionStatus.SUCCESS
                            for dep in capability.dependencies
                        )
                        if not deps_met:
                            continue
                
                results.append((tool_name, result.score))
                
                if len(results) >= k:
                    break
            
            return results
            
        except Exception as e:
            logger.error(f"Semantic tool search failed: {e}")
            return []

    def evaluate_rag_action(self, state: GeneralizedMDPState, tool_name: str, 
                          capability: ToolCapability, action: GeneralizedAction) -> Dict[str, Any]:
        """Comprehensive evaluation of RAG-enhanced action"""
        evaluation = {
            'tool_name': tool_name,
            'scores': {},
            'factors': {},
            'recommendation': None
        }
        
        # 1. Rule-based semantic confidence
        rule_confidence = self._calculate_semantic_confidence(state, tool_name, capability)
        evaluation['scores']['rule_based'] = rule_confidence
        
        # 2. RAG search score (if available)
        rag_score = getattr(action, 'semantic_score', 0.0)
        evaluation['scores']['rag_search'] = rag_score
        
        # 3. Historical pattern score
        pattern_score = 0.0
        if len(state.execution_sequence) >= 2:
            recent_pattern = '->'.join(state.execution_sequence[-2:] + [tool_name])
            if recent_pattern in self.successful_patterns:
                pattern_score = self.successful_patterns[recent_pattern]
        evaluation['scores']['pattern'] = pattern_score
        
        # 4. Task preference score
        task_preference = 0.0
        if hasattr(state, 'task_type') and state.task_type in self.task_tool_preferences:
            task_prefs = self.task_tool_preferences[state.task_type]
            task_preference = task_prefs.get(tool_name, 0.0)
        evaluation['scores']['task_preference'] = task_preference
        
        # 5. Data flow coherence
        coherence_score = 0.0
        if hasattr(state, 'data_flow_state'):
            # Check if tool operations align with current data flow state
            for operation in capability.semantic_operations:
                if state.data_flow_state == DataFlowState.EMPTY and ('read' in operation or 'load' in operation):
                    coherence_score = 0.9
                elif state.data_flow_state == DataFlowState.INITIALIZED and 'validat' in operation:
                    coherence_score = 0.8
                elif state.data_flow_state == DataFlowState.VALIDATED and 'transform' in operation:
                    coherence_score = 0.8
                elif state.data_flow_state == DataFlowState.TRANSFORMED and ('write' in operation or 'export' in operation):
                    coherence_score = 0.9
        evaluation['scores']['data_flow_coherence'] = coherence_score
        
        # 6. Alternative tools assessment
        alternatives = getattr(action, 'alternative_tools', [])
        if alternatives:
            alt_scores = {}
            for alt_tool in alternatives[:3]:  # Check top 3 alternatives
                if alt_tool in self.tool_capabilities:
                    alt_capability = self.tool_capabilities[alt_tool]
                    alt_confidence = self._calculate_semantic_confidence(state, alt_tool, alt_capability)
                    alt_scores[alt_tool] = alt_confidence
            evaluation['factors']['alternatives'] = alt_scores
        
        # 7. Risk assessment
        risk_factors = []
        if state.consecutive_errors > 2:
            risk_factors.append("high_error_rate")
        if state.workflow_step > 30:
            risk_factors.append("excessive_steps")
        if tool_name in state.retry_counts and state.retry_counts[tool_name] > 1:
            risk_factors.append("previous_failures")
        evaluation['factors']['risks'] = risk_factors
        
        # 8. Composite score and recommendation
        composite_weights = {
            'rule_based': 0.25,
            'rag_search': 0.20,
            'pattern': 0.20,
            'task_preference': 0.15,
            'data_flow_coherence': 0.20
        }
        
        composite_score = sum(
            evaluation['scores'][key] * weight 
            for key, weight in composite_weights.items()
        )
        evaluation['composite_score'] = composite_score
        
        # Recommendation
        if composite_score > 0.7:
            evaluation['recommendation'] = 'highly_recommended'
        elif composite_score > 0.5:
            evaluation['recommendation'] = 'recommended'
        elif composite_score > 0.3:
            evaluation['recommendation'] = 'acceptable'
        else:
            evaluation['recommendation'] = 'not_recommended'
        
        return evaluation
    

    def update_successful_patterns(self, completed_episodes: List[Dict[str, Any]]):
        """Learn from completed episodes to update pattern preferences"""
        # Reset counts for fresh learning
        pattern_counts = defaultdict(int)
        pattern_scores = defaultdict(float)
        task_tool_counts = defaultdict(lambda: defaultdict(int))
        task_tool_scores = defaultdict(lambda: defaultdict(float))
        
        for episode in completed_episodes:
            state = episode['final_state']
            score = episode['score']  # Assumes score from evaluation (0-1)
            
            # Only learn from reasonably successful episodes
            if score < 0.5:
                continue
            
            # Extract execution sequence
            if hasattr(state, 'execution_sequence'):
                sequence = state.execution_sequence
            else:
                # Fallback to tool_states
                sequence = [tool for tool, status in state.tool_states.items() 
                          if status == ToolExecutionStatus.SUCCESS]
            
            # Learn sequential patterns (2-3 tool sequences)
            for pattern_len in [2, 3]:
                for i in range(len(sequence) - pattern_len + 1):
                    pattern = '->'.join(sequence[i:i + pattern_len])
                    pattern_counts[pattern] += 1
                    pattern_scores[pattern] += score
            
            # Learn task-tool associations
            if hasattr(state, 'task_type'):
                task_type = state.task_type
                for tool in sequence:
                    task_tool_counts[task_type][tool] += 1
                    task_tool_scores[task_type][tool] += score
        
        # Update successful patterns with normalized scores
        self.successful_patterns.clear()
        for pattern, count in pattern_counts.items():
            if count >= 2:  # Require at least 2 occurrences
                avg_score = pattern_scores[pattern] / count
                self.successful_patterns[pattern] = avg_score
                self.pattern_occurrence_count[pattern] = count
        
        # Update task-tool preferences
        self.task_tool_preferences.clear()
        for task_type, tool_counts in task_tool_counts.items():
            total_count = sum(tool_counts.values())
            if total_count > 0:
                for tool, count in tool_counts.items():
                    if count >= 2:  # Require at least 2 occurrences
                        avg_score = task_tool_scores[task_type][tool] / count
                        # Combine frequency and score
                        preference = (count / total_count) * 0.4 + avg_score * 0.6
                        self.task_tool_preferences[task_type][tool] = preference
        
        # Store episodes for future reference
        self.episode_history.extend(completed_episodes[-100:])  # Keep last 100 episodes
        if len(self.episode_history) > 100:
            self.episode_history = self.episode_history[-100:]
        
        # Log learning results
        logger.info(f"Updated patterns: {len(self.successful_patterns)} patterns learned")
        logger.info(f"Task preferences: {len(self.task_tool_preferences)} task types")

# 文件：generalized_mdp_framework.py
# 在update_successful_patterns方法后添加

    def calculate_episode_adjustment(self, trajectory: List[Tuple[GeneralizedMDPState, GeneralizedAction, float, GeneralizedMDPState]], 
                                   final_score: float) -> List[float]:
        """Calculate adjusted rewards for entire episode based on final score"""
        adjusted_rewards = []
        
        # Score-based multiplier
        if final_score >= 0.9:
            multiplier = 1.5  # Excellent performance
        elif final_score >= 0.7:
            multiplier = 1.2  # Good performance
        elif final_score >= 0.5:
            multiplier = 1.0  # Acceptable performance
        else:
            multiplier = 0.7  # Poor performance
        
        # Process each transition
        for i, (state, action, reward, next_state) in enumerate(trajectory):
            adjusted_reward = reward * multiplier
            
            # Additional adjustments for tool selection actions
            if action.action_type == ActionType.INVOKE_TOOL and action.tool_name:
                # Position-based bonus (early correct choices are more valuable)
                position_factor = 1.0 - (i / len(trajectory)) * 0.3
                
                # RAG-based selection bonus
                if hasattr(action, 'search_source') and action.search_source == "embedding_search":
                    if final_score > 0.7:  # Only reward if it led to success
                        adjusted_reward += 1.0 * position_factor
                
                # Pattern completion bonus
                if i >= 2 and hasattr(state, 'execution_sequence'):
                    recent_pattern = '->'.join(state.execution_sequence[-3:])
                    if recent_pattern in self.successful_patterns:
                        pattern_score = self.successful_patterns[recent_pattern]
                        if pattern_score > 0.7 and final_score > 0.7:
                            adjusted_reward += 0.5 * pattern_score
            
            adjusted_rewards.append(adjusted_reward)
        
        return adjusted_rewards

    def get_available_actions(self, state: GeneralizedMDPState) -> List[GeneralizedAction]:
        """Get available actions with Phase 3 semantic filtering and FALLBACK MECHANISM"""
        actions = []
        
        # Always allow NO_OP
        actions.append(GeneralizedAction(ActionType.NO_OP, confidence=0.1))
        
        # Check if we should create a checkpoint
        if state.workflow_step > 0 and state.workflow_step % 5 == 0:
            actions.append(GeneralizedAction(ActionType.CREATE_CHECKPOINT, confidence=0.5))
        
        # Recovery actions if needed
        if state.should_recover():
            actions.append(GeneralizedAction(ActionType.RECOVER_ERROR, confidence=0.8))
            if state.metadata.get('checkpoints'):
                actions.append(GeneralizedAction(ActionType.RESTORE_CHECKPOINT, confidence=0.7))
        
        # Tool invocation actions
        for tool_name, capability in self.tool_capabilities.items():
            if state.tool_states.get(tool_name) == ToolExecutionStatus.SUCCESS:
                continue
            
            if state.tool_states.get(tool_name) == ToolExecutionStatus.FAILED:
                if state.retry_counts.get(tool_name, 0) < 3:
                    actions.append(GeneralizedAction(
                        ActionType.RETRY_TOOL,
                        tool_name=tool_name,
                        confidence=0.4
                    ))
                continue
            
            # Check dependencies
            dependencies_met = all(
                state.tool_states.get(dep, ToolExecutionStatus.NOT_ATTEMPTED) == ToolExecutionStatus.SUCCESS
                for dep in capability.dependencies
            )
            
            if not dependencies_met:
                continue
            
            # Phase 3: Semantic filtering
            confidence = self._calculate_semantic_confidence(state, tool_name, capability)
            
            # Enhanced: Check RAG search results  # <- 新增注释
            semantic_score = 0.0  # <- 新增这一行
            search_source = "rule_based"  # <- 新增这一行
            
            # Check if we have RAG search results for current semantic operation  # <- 新增这部分
            if hasattr(state, 'rag_search_results'):  # <- 新增
                for operation in capability.semantic_operations:  # <- 新增
                    if operation in state.rag_search_results:  # <- 新增
                        # Find if this tool is in search results  # <- 新增
                        for result_tool, score in state.rag_search_results[operation]:  # <- 新增
                            if result_tool == tool_name:  # <- 新增
                                semantic_score = max(semantic_score, score)  # <- 新增
                                search_source = "embedding_search"  # <- 新增
                                confidence = confidence * 0.7 + score * 0.3  # <- 新增：混合置信度
            
            # Pattern-based confidence adjustment  # <- 新增这部分
            if len(state.execution_sequence) >= 2:  # <- 新增
                potential_pattern = '->'.join(state.execution_sequence[-2:] + [tool_name])  # <- 新增
                if potential_pattern in self.successful_patterns:  # <- 新增
                    pattern_boost = self.successful_patterns[potential_pattern] * 0.3  # <- 新增
                    confidence = min(1.0, confidence + pattern_boost)  # <- 新增
                    search_source = "hybrid" if search_source == "embedding_search" else "pattern_based"  # <- 新增
            
            if confidence > 0.2:  # Lowered threshold for fallback
                action = GeneralizedAction(  # <- 修改：创建action变量
                    ActionType.INVOKE_TOOL,
                    tool_name=tool_name,
                    confidence=confidence,
                    semantic_score=semantic_score,  # <- 新增
                    search_source=search_source  # <- 新增
                )
                actions.append(action)  # <- 修改：使用action变量
        
        # Validation action
        if any(status == ToolExecutionStatus.SUCCESS for status in state.tool_states.values()):
            actions.append(GeneralizedAction(ActionType.VALIDATE_OUTPUT, confidence=0.6))
        
        # FALLBACK MECHANISM: If no tool actions available (except NO_OP), add some candidates
        tool_actions = [a for a in actions if a.action_type == ActionType.INVOKE_TOOL]
        if not tool_actions and state.workflow_step < 10:  # Early in workflow
            # Enhanced: Try to get candidates from state's tool_candidates  # <- 新增注释
            if hasattr(state, 'tool_candidates') and state.tool_candidates:  # <- 新增这部分
                for capability_type, candidate_tools in state.tool_candidates.items():  # <- 新增
                    for tool_name in candidate_tools[:2]:  # <- 新增：取前2个候选
                        if (tool_name in self.tool_capabilities and  # <- 新增
                            state.tool_states.get(tool_name) != ToolExecutionStatus.SUCCESS):  # <- 新增
                            actions.append(GeneralizedAction(  # <- 新增
                                ActionType.INVOKE_TOOL,  # <- 新增
                                tool_name=tool_name,  # <- 新增
                                confidence=0.35,  # <- 新增
                                search_source="rag_fallback"  # <- 新增
                            ))  # <- 新增
            
            # Original fallback: Add tools with no dependencies  # <- 修改了注释
            for tool_name, capability in self.tool_capabilities.items():
                if (not capability.dependencies and 
                    state.tool_states.get(tool_name) != ToolExecutionStatus.SUCCESS):
                    actions.append(GeneralizedAction(
                        ActionType.INVOKE_TOOL,
                        tool_name=tool_name,
                        confidence=0.3
                    ))
        
        return actions
    
    def _get_semantic_actions(self, state: GeneralizedMDPState) -> List[GeneralizedAction]:
        """Get semantically appropriate actions based on task state"""
        actions = []
        features = state.task_features
        
        # Determine what type of action is needed based on subtask progress
        if features.has_input_requirement and 'data_loaded' not in state.milestones_achieved:
            # Need input tools
            for tool in self.semantic_groups.get('input', []):
                if tool not in state.tool_states:
                    actions.append(GeneralizedAction(
                        ActionType.INVOKE_TOOL,
                        tool_name=tool,
                        confidence=0.9
                    ))
        
        elif features.requires_validation and 'data_validated' not in state.milestones_achieved:
            # Need validation tools
            for tool in self.semantic_groups.get('validation', []):
                if tool not in state.tool_states:
                    actions.append(GeneralizedAction(
                        ActionType.INVOKE_TOOL,
                        tool_name=tool,
                        confidence=0.8
                    ))
        
        elif features.requires_transformation and 'data_transformed' not in state.milestones_achieved:
            # Need transformation tools
            for tool in self.semantic_groups.get('transformation', []):
                if tool not in state.tool_states:
                    actions.append(GeneralizedAction(
                        ActionType.INVOKE_TOOL,
                        tool_name=tool,
                        confidence=0.85
                    ))
        
        return actions
    
    def _calculate_action_confidence(self, state: GeneralizedMDPState, tool_name: str) -> float:
        """Calculate confidence score for an action based on semantic alignment"""
        base_confidence = 0.5
        
        # Check semantic alignment
        if hasattr(state, 'task_features'):
            capability = self.tool_capabilities[tool_name]
            
            # Boost confidence for semantically aligned tools
            for operation in capability.semantic_operations:
                if state.task_features.requires_validation and 'validat' in operation:
                    base_confidence += 0.2
                elif state.task_features.requires_transformation and 'transform' in operation:
                    base_confidence += 0.2
                elif state.task_features.requires_aggregation and 'aggregat' in operation:
                    base_confidence += 0.2
        
        # Penalty for retrying failed tools
        if tool_name in state.tool_states and state.tool_states[tool_name] == ToolExecutionStatus.FAILED:
            base_confidence *= 0.5
        
        return min(1.0, max(0.1, base_confidence))
    
    def _can_invoke_tool(self, state: GeneralizedMDPState, tool_name: str, 
                        capability: ToolCapability) -> bool:
        """Check if a tool can be invoked given current state"""
        # Tool already succeeded
        if state.tool_states.get(tool_name) == ToolExecutionStatus.SUCCESS:
            return False
        
        # Check retry limit
        if state.retry_counts.get(tool_name, 0) >= 3:
            return False
        
        # Check dependencies
        for dep in capability.dependencies:
            if state.tool_states.get(dep) != ToolExecutionStatus.SUCCESS:
                return False
        
        # Check if parallel execution is safe
        running_tools = [t for t, s in state.tool_states.items() 
                        if s == ToolExecutionStatus.RUNNING]
        if running_tools and not capability.parallel_safe:
            return False
        
        return True
    
    def transition(self, state: GeneralizedMDPState, action: GeneralizedAction) -> GeneralizedMDPState:
        """Execute state transition"""
        # Deep copy current state
        next_state = GeneralizedMDPState(
            task_id=state.task_id,
            task_type=state.task_type,
            task_objective=state.task_objective
        )
        
        # Copy all state attributes
        next_state.tool_states = state.tool_states.copy()
        next_state.tool_outputs = state.tool_outputs.copy()
        next_state.tool_errors = state.tool_errors.copy()
        next_state.retry_counts = state.retry_counts.copy()
        next_state.overall_progress = state.overall_progress
        next_state.workflow_step = state.workflow_step + 1
        next_state.execution_sequence = state.execution_sequence.copy()
        next_state.consecutive_errors = state.consecutive_errors
        next_state.total_errors = state.total_errors
        next_state.error_history = state.error_history.copy()
        next_state.milestones_achieved = state.milestones_achieved.copy()
        next_state.expected_milestones = state.expected_milestones.copy()
        next_state.metadata = state.metadata.copy()
        
        # Phase 3: Copy task-aware attributes
        if hasattr(state, 'task_features'):
            next_state.task_features = state.task_features
            next_state.semantic_milestones = state.semantic_milestones.copy()
            next_state.data_flow_state = state.data_flow_state
            next_state.subtask_progress = state.subtask_progress.copy()
        
        # Execute action
        if action.action_type == ActionType.INVOKE_TOOL:
            self._execute_tool(next_state, action.tool_name)
        elif action.action_type == ActionType.VALIDATE_OUTPUT:
            self._validate_outputs(next_state)
        elif action.action_type == ActionType.RETRY_TOOL:
            self._retry_tool(next_state, action.tool_name)
        elif action.action_type == ActionType.RECOVER_ERROR:
            self._recover_from_error(next_state)
        elif action.action_type == ActionType.CREATE_CHECKPOINT:
            self._create_checkpoint(next_state)
        elif action.action_type == ActionType.RESTORE_CHECKPOINT:
            self._restore_checkpoint(next_state)
        elif action.action_type == ActionType.NO_OP:
            pass  # No operation
        
        # Update progress
        self._update_progress(next_state)
        
        # Check completion
        self._check_completion(next_state)
        
        return next_state
    
    def _execute_tool(self, state: GeneralizedMDPState, tool_name: str):
        """Simulate tool execution with enhanced reliability model"""
        if tool_name not in self.tool_capabilities:
            state.tool_states[tool_name] = ToolExecutionStatus.FAILED
            state.tool_errors[tool_name] = ErrorCategory.TOOL_NOT_FOUND
            state.consecutive_errors += 1
            return
        
        capability = self.tool_capabilities[tool_name]
        state.execution_sequence.append(tool_name)
        
        # 提高基础成功率，特别是在训练初期
        if hasattr(state, 'metadata') and state.metadata:
            current_success_rate = state.metadata.get('current_success_rate', 0.0)
            
            # 动态调整基础成功率
            if current_success_rate < 0.1:
                # 训练初期：非常高的成功率
                base_reliability = 0.95
            elif current_success_rate < 0.3:
                # 中期：较高成功率
                base_reliability = 0.9
            else:
                # 后期：正常成功率
                base_reliability = 0.85
        else:
            base_reliability = 0.9  # 默认较高成功率
        
        # 依赖性调整（减轻惩罚）
        dependency_factor = 1.0
        for dep in capability.dependencies:
            if state.tool_states.get(dep) != ToolExecutionStatus.SUCCESS:
                dependency_factor *= 0.8  # 从0.5增加到0.8
        
        # 重试调整（减轻惩罚）
        retry_factor = 0.95 ** state.retry_counts.get(tool_name, 0)  # 从0.9增加到0.95
        
        # 语义对齐调整
        semantic_factor = 1.0
        if hasattr(state, 'task_features') and state.task_features:
            # 检查工具是否与任务需求匹配
            for operation in capability.semantic_operations:
                if 'validat' in operation and getattr(state.task_features, 'requires_validation', False):
                    semantic_factor *= 1.2
                elif 'transform' in operation and getattr(state.task_features, 'requires_transformation', False):
                    semantic_factor *= 1.2
                elif 'read' in operation or 'load' in operation:
                    semantic_factor *= 1.1  # 读取操作通常更可靠
        
        # Required tools有更高成功率
        if hasattr(state, 'metadata') and 'required_tools' in state.metadata:
            if tool_name in state.metadata['required_tools']:
                semantic_factor *= 1.3  # required tools更容易成功
        
        reliability = base_reliability * dependency_factor * retry_factor * semantic_factor
        reliability = min(0.99, reliability)  # 上限99%
        
        success = np.random.random() < reliability
        
        if success:
            state.tool_states[tool_name] = ToolExecutionStatus.SUCCESS
            state.consecutive_errors = 0
            
            # 更新数据流状态（如果适用）
            if hasattr(state, 'data_flow_state'):
                self._update_data_flow_state(state, tool_name, capability)
            
            # 检查里程碑成就
            self._check_milestones(state, tool_name, capability)
            
            print(f"[EXECUTE] Tool {tool_name} SUCCESS (reliability: {reliability:.2%})")
        else:
            state.tool_states[tool_name] = ToolExecutionStatus.FAILED
            state.consecutive_errors += 1
            state.total_errors += 1
            
            # 简化错误类型（减少复杂性）
            if dependency_factor < 1.0:
                error_type = ErrorCategory.DEPENDENCY_ERROR
            else:
                error_type = ErrorCategory.EXECUTION_ERROR
            
            state.tool_errors[tool_name] = error_type
            state.error_history.append((tool_name, error_type))
            
            print(f"[EXECUTE] Tool {tool_name} FAILED (reliability: {reliability:.2%})")
        
        # 更新重试计数
        state.retry_counts[tool_name] = state.retry_counts.get(tool_name, 0) + 1


    def _update_data_flow_state(self, state: GeneralizedMDPState, tool_name: str, 
                               capability: ToolCapability):
        """Update data flow state based on tool execution"""
        if not hasattr(state, 'data_flow_state'):
            return
        
        # Update based on semantic operations
        for operation in capability.semantic_operations:
            if 'read' in operation or 'load' in operation:
                state.data_flow_state = DataFlowState.INITIALIZED
                state.subtask_progress['input_acquired'] = 1.0
            elif 'validat' in operation:
                if state.data_flow_state != DataFlowState.CORRUPTED:
                    state.data_flow_state = DataFlowState.VALIDATED
                state.subtask_progress['validated'] = 1.0
            elif 'transform' in operation:
                state.data_flow_state = DataFlowState.TRANSFORMED
                state.subtask_progress['transformed'] = 1.0
            elif 'write' in operation or 'export' in operation:
                state.subtask_progress['output_generated'] = 1.0
    
    def _check_milestones(self, state: GeneralizedMDPState, tool_name: str, 
                         capability: ToolCapability):
        """Check and update milestone achievements"""
        # Semantic milestones
        for operation in capability.semantic_operations:
            if 'read' in operation and 'data_loaded' not in state.milestones_achieved:
                state.milestones_achieved.add('data_loaded')
                state.semantic_milestones.append(f"Data loaded by {tool_name}")
            elif 'validat' in operation and 'data_validated' not in state.milestones_achieved:
                state.milestones_achieved.add('data_validated')
                state.semantic_milestones.append(f"Data validated by {tool_name}")
            elif 'transform' in operation and 'data_transformed' not in state.milestones_achieved:
                state.milestones_achieved.add('data_transformed')
                state.semantic_milestones.append(f"Data transformed by {tool_name}")
            elif 'write' in operation and 'data_exported' not in state.milestones_achieved:
                state.milestones_achieved.add('data_exported')
                state.semantic_milestones.append(f"Data exported by {tool_name}")
    

    def _update_progress(self, state: GeneralizedMDPState):
        """Update overall progress - 基于任务类型和完成情况灵活计算"""
        
        # 获取required_tools
        required_tools = []
        if hasattr(state, 'metadata') and 'required_tools' in state.metadata:
            required_tools = state.metadata['required_tools']
        
        # 1. 如果有required_tools，基于其完成情况计算进度
        if required_tools:
            completed_required = sum(1 for tool in required_tools 
                                if state.tool_states.get(tool) == ToolExecutionStatus.SUCCESS)
            required_progress = completed_required / len(required_tools)
            
            # 执行顺序奖励（如果按顺序执行）
            sequence_bonus = 0.0
            if completed_required > 0:
                executed_in_order = True
                for i, tool in enumerate(required_tools[:completed_required]):
                    if tool not in state.execution_sequence:
                        executed_in_order = False
                        break
                    # 检查是否按顺序执行
                    tool_position = state.execution_sequence.index(tool)
                    if i > 0:
                        prev_tool = required_tools[i-1]
                        if prev_tool in state.execution_sequence:
                            prev_position = state.execution_sequence.index(prev_tool)
                            if tool_position < prev_position:
                                executed_in_order = False
                                break
                
                if executed_in_order:
                    sequence_bonus = 0.1  # 10%的顺序奖励
            
            # 基础进度 = required tools完成度 + 顺序奖励
            base_progress = min(1.0, required_progress + sequence_bonus)
        
        else:
            # 2. 没有required_tools时，基于里程碑和执行步数
            milestone_progress = 0.0
            
            # 关键里程碑的权重
            milestone_weights = {
                'data_loaded': 0.2,
                'data_validated': 0.2,
                'data_transformed': 0.3,
                'data_exported': 0.3,
                'first_tool_success': 0.1,
                'multiple_tools_success': 0.2
            }
            
            # 计算里程碑进度
            for milestone, weight in milestone_weights.items():
                if milestone in state.milestones_achieved:
                    milestone_progress += weight
            
            # 执行步数进度（防止无限循环）
            step_progress = min(1.0, state.workflow_step / 20.0)  # 假设20步内应该完成
            
            # 成功执行的工具数量
            successful_tools = sum(1 for status in state.tool_states.values() 
                                if status == ToolExecutionStatus.SUCCESS)
            tool_progress = min(1.0, successful_tools / 5.0)  # 假设5个工具是合理的
            
            # 综合计算进度
            base_progress = 0.3 * milestone_progress + 0.4 * tool_progress + 0.3 * step_progress
        
        # 3. 错误惩罚（轻微）
        error_penalty = 0.0
        if state.total_errors > 0:
            error_penalty = min(0.2, state.total_errors * 0.02)  # 每个错误减少2%，最多20%
        
        # 4. 最终进度计算
        final_progress = max(0.0, min(1.0, base_progress - error_penalty))
        
        # 5. 进度只能增加（避免倒退）
        if final_progress > state.overall_progress:
            old_progress = state.overall_progress
            state.overall_progress = final_progress
            print(f"[PROGRESS] Updated: {old_progress:.1%} -> {final_progress:.1%}")
            
            # 记录进度增量
            if hasattr(state, 'metadata'):
                state.metadata['last_progress_delta'] = final_progress - old_progress
        
        # 6. 检查是否应该标记为完成
        if state.overall_progress >= 0.95 and not state.is_completed:
            print(f"[PROGRESS] Progress reached 95%, checking completion criteria")
            # 这会触发_check_completion在下一步检查
            
    def _check_completion(self, state: GeneralizedMDPState):
        """Check if task is completed - adaptive to task type"""
        
        # 1. 检查是否已经设置了完成标志
        if state.is_completed:
            return
        
        # 2. 基于进度的完成检查
        if state.overall_progress >= 1.0:
            print(f"[CHECK_COMPLETION] Progress 100% - marking as completed")
            state.is_completed = True
            state.is_successful = True
            return
        
        # 3. 基于required tools的完成检查
        if hasattr(state, 'metadata') and 'required_tools' in state.metadata:
            required_tools = state.metadata['required_tools']
            if required_tools:
                # 检查所有required tools是否成功执行
                executed_required = [t for t in required_tools 
                                if state.tool_states.get(t) == ToolExecutionStatus.SUCCESS]
                
                if len(executed_required) == len(required_tools):
                    print(f"[CHECK_COMPLETION] All required tools executed successfully")
                    state.is_completed = True
                    state.is_successful = True
                    return
                
                # 部分完成但步数过多
                if state.workflow_step > len(required_tools) * 3:
                    completion_ratio = len(executed_required) / len(required_tools)
                    if completion_ratio >= 0.5:
                        print(f"[CHECK_COMPLETION] Partial completion ({completion_ratio:.1%}) after many steps")
                        state.is_completed = True
                        state.is_successful = False
                        return
        
        # 4. 基于里程碑的完成检查（仅对有dataflow的任务）
        if hasattr(state, 'data_flow_state') and hasattr(state, 'task_features'):
            # 只有当任务明确需要数据流时才检查dataflow里程碑
            if (getattr(state.task_features, 'has_input_requirement', False) or 
                getattr(state.task_features, 'has_output_requirement', False)):
                
                key_milestones = {'data_loaded', 'data_validated', 'data_transformed', 'data_exported'}
                achieved_key_milestones = state.milestones_achieved & key_milestones
                
                # 灵活的完成条件
                has_input = any(m in achieved_key_milestones for m in ['data_loaded', 'data_validated'])
                has_output = 'data_exported' in achieved_key_milestones
                has_transform = 'data_transformed' in achieved_key_milestones
                
                # 满足基本输入输出即可
                if (has_input and has_output) or (has_input and has_transform):
                    print(f"[CHECK_COMPLETION] Data flow milestones achieved")
                    state.is_completed = True
                    state.is_successful = True
                    return
        
        # 5. 基于执行步数的完成检查
        max_steps = self.completion_thresholds.get('maximum_steps', 50)
        if state.workflow_step >= max_steps:
            print(f"[CHECK_COMPLETION] Maximum steps reached ({max_steps})")
            state.is_completed = True
            # 根据进度判断成功与否
            state.is_successful = state.overall_progress >= 0.5
            return
        
        # 6. 死锁检查
        available_actions = self.get_available_actions(state)
        if len(available_actions) <= 1:  # 只有NO_OP或结束动作
            print(f"[CHECK_COMPLETION] Deadlock detected - no valid actions")
            state.is_completed = True
            state.is_successful = state.overall_progress >= 0.3  # 更宽松的成功标准
            return
        
        # 7. 连续错误检查（更宽松）
        if state.consecutive_errors >= 10:  # 从5增加到10
            print(f"[CHECK_COMPLETION] Too many consecutive errors ({state.consecutive_errors})")
            state.is_completed = True
            state.is_successful = False
            return
        
        # 继续执行
        print(f"[CHECK_COMPLETION] Continue - no completion criteria met")

    def get_reward(self, state: GeneralizedMDPState, action: GeneralizedAction, 
                next_state: GeneralizedMDPState) -> float:
        """Calculate reward for state transition with two-phase training strategy
        
        Two-phase training approach:
        1. Coverage Phase (success_rate < threshold):
        - Focus on learning to use ALL required tools
        - Ignore execution order
        - High rewards for tool coverage
        
        2. Sequence Phase (success_rate >= threshold):
        - Enforce correct execution order
        - Reward proper sequencing
        - Penalize out-of-order execution
        """
        reward = 0.0
        
        # 获取当前训练成功率和阈值配置
        current_success_rate = 0.0
        success_rate_threshold = 0.3  # 默认阈值30%
        
        if hasattr(state, 'metadata') and state.metadata is not None:
            current_success_rate = state.metadata.get('current_success_rate', 0.0)
            success_rate_threshold = state.metadata.get('success_rate_threshold', 0.3)
            mode = "coverage" if current_success_rate < success_rate_threshold else "sequence"
            print(f"[REWARD] Training mode: {mode} (success_rate={current_success_rate:.2%}, threshold={success_rate_threshold:.2%})")
        else:
            print(f"[REWARD] No success rate info in metadata, using defaults")
        
        # 0. 立即奖励：任何非NO_OP动作都给予小奖励（鼓励探索）
        if action.action_type != ActionType.NO_OP:
            exploration_reward = 1.0  # 基础探索奖励
            reward += exploration_reward
            print(f"[REWARD] Action taken (not NO_OP): +{exploration_reward}")
        
        # 1. 进度奖励（大幅增强）
        progress_delta = next_state.overall_progress - state.overall_progress
        if progress_delta > 0:
            # 超高进度奖励
            base_progress_reward = progress_delta * 100  # 从30增加到100
            reward += base_progress_reward
            
            # 早期进度巨额奖励
            if state.workflow_step < 10:
                early_bonus = progress_delta * 50  # 从15增加到50
                reward += early_bonus
                print(f"[REWARD] Early progress bonus: +{early_bonus:.2f}")
            
            print(f"[REWARD] Progress reward: +{base_progress_reward:.2f} (delta: {progress_delta:.2%})")
        
        # 1.5 步数奖励：每走一步都有小奖励（避免停滞）
        if state.workflow_step < 30:  # 前30步
            step_reward = 0.5
            reward += step_reward
            print(f"[REWARD] Step bonus: +{step_reward}")
        
        # 2. 工具执行奖励（增强正向激励）
        if action.action_type == ActionType.INVOKE_TOOL and action.tool_name:
            tool_name = action.tool_name
            
            # 成功执行工具
            if next_state.tool_states.get(tool_name) == ToolExecutionStatus.SUCCESS:
                # 增强基础执行奖励
                reward += 8  # 从5增加到8
                
                # 首次成功执行奖励
                if tool_name not in state.execution_sequence:
                    first_exec_reward = 10  # 从5增加到10
                    reward += first_exec_reward
                    print(f"[REWARD] First successful execution of {tool_name}: +{8 + first_exec_reward}")
                
        # 2. 工具执行奖励（大幅增强即时反馈）
        if action.action_type == ActionType.INVOKE_TOOL and action.tool_name:
            tool_name = action.tool_name
            
            # 2.1 尝试执行工具就给奖励（鼓励尝试）
            attempt_reward = 3
            reward += attempt_reward
            print(f"[REWARD] Tool execution attempt ({tool_name}): +{attempt_reward}")
            
            # 2.2 首次尝试某个工具的额外奖励
            if tool_name not in state.tool_states:
                first_attempt_bonus = 5
                reward += first_attempt_bonus
                print(f"[REWARD] First attempt at tool {tool_name}: +{first_attempt_bonus}")
            
            # 2.3 成功执行工具
            if next_state.tool_states.get(tool_name) == ToolExecutionStatus.SUCCESS:
                # 巨额成功奖励
                success_reward = 20  # 从8增加到20
                reward += success_reward
                
                # 首次成功执行奖励
                if tool_name not in state.execution_sequence:
                    first_exec_reward = 30  # 从10增加到30
                    reward += first_exec_reward
                    print(f"[REWARD] First successful execution of {tool_name}: +{success_reward + first_exec_reward}")
                
                # Required tools超级奖励
                if hasattr(state, 'metadata') and 'required_tools' in state.metadata:
                    required_tools = state.metadata['required_tools']
                    if tool_name in required_tools:
                        # 基于成功率的不同奖励策略
                        if current_success_rate < success_rate_threshold:
                            # 覆盖率模式：巨额奖励
                            coverage_reward = 50  # 从20增加到50
                            reward += coverage_reward
                            print(f"[REWARD] Required tool executed (coverage mode): +{coverage_reward}")
                            
                            # 检查覆盖进度
                            executed_required = [t for t in required_tools if t in state.execution_sequence or 
                                            (t == tool_name)]
                            coverage_ratio = len(executed_required) / len(required_tools)
                            
                            # 每增加一个required tool的覆盖都给奖励
                            incremental_coverage_reward = 20 * coverage_ratio
                            reward += incremental_coverage_reward
                            print(f"[REWARD] Coverage progress ({coverage_ratio:.1%}): +{incremental_coverage_reward:.1f}")
                            
                            if coverage_ratio == 1.0:
                                # 完全覆盖巨奖
                                full_coverage_bonus = 100  # 从30增加到100
                                reward += full_coverage_bonus
                                print(f"[REWARD] Full required tools coverage achieved: +{full_coverage_bonus}")
                        
                        else:
                            # 顺序模式的奖励（保持原样）
                            base_reward = 10
                            reward += base_reward
                            print(f"[REWARD] Required tool executed (sequence mode): +{base_reward}")
                            
                            # 检查执行顺序
                            executed_required = [t for t in state.execution_sequence if t in required_tools]
                            expected_index = len(executed_required)
                            actual_index = required_tools.index(tool_name)
                            
                            if actual_index == expected_index:
                                sequence_reward = 15
                                reward += sequence_reward
                                print(f"[REWARD] Perfect sequence order: +{sequence_reward}")
                            elif abs(actual_index - expected_index) == 1:
                                near_reward = 5
                                reward += near_reward
                                print(f"[REWARD] Near correct order: +{near_reward}")
                            else:
                                sequence_penalty = -5 * abs(actual_index - expected_index)
                                reward += sequence_penalty
                                print(f"[REWARD] Wrong sequence order: {sequence_penalty}")
                    
                    else:
                        # 非required tool但成功执行也给奖励
                        if current_success_rate < success_rate_threshold:
                            exploration_reward = 5
                            reward += exploration_reward
                            print(f"[REWARD] Non-required tool success (exploration): +{exploration_reward}")
            
            # 工具执行失败（大幅减轻惩罚）
            elif next_state.tool_states.get(tool_name) in [ToolExecutionStatus.FAILED, ToolExecutionStatus.TIMEOUT]:
                failure_penalty = -1  # 从-3减少到-1（几乎不惩罚）
                reward += failure_penalty
                print(f"[REWARD] Tool execution failed: {failure_penalty} (minimal penalty)")
            
            # 重复执行惩罚（基于模式调整）
            if tool_name in state.execution_sequence:
                count = state.execution_sequence.count(tool_name)
                if count >= 2:
                    if current_success_rate < success_rate_threshold:
                        # 覆盖率模式：对重复执行更宽容
                        if tool_name in state.metadata.get('required_tools', []):
                            # required tool重复执行轻微惩罚
                            repeat_penalty = -1 * (count - 1)
                        else:
                            # 非required tool重复执行中等惩罚
                            repeat_penalty = -2 * (count - 1)
                    else:
                        # 顺序模式：正常惩罚
                        repeat_penalty = -5 * (count - 1)
                    
                    reward += repeat_penalty
                    print(f"[REWARD] Repeated execution penalty (count={count}): {repeat_penalty}")
        
        # 3. 错误惩罚（仅在高成功率时启用）
        if current_success_rate >= 0.1:  # 只有成功率超过10%才开始惩罚错误
            error_increase = next_state.total_errors - state.total_errors
            if error_increase > 0:
                error_penalty = error_increase * 2  # 从5减少到2
                reward -= error_penalty
                print(f"[REWARD] Error penalty: -{error_penalty}")
        
        # 4. 连续错误惩罚（极度宽松）
        if next_state.consecutive_errors > 5:  # 从2增加到5
            # 只有连续错误超过5次才惩罚
            if current_success_rate < 0.2:
                consec_penalty = 1 * (next_state.consecutive_errors - 5)
            else:
                consec_penalty = 2 * (next_state.consecutive_errors - 5)
            reward -= consec_penalty
            print(f"[REWARD] Consecutive errors penalty: -{consec_penalty}")
        
        # 5. 里程碑奖励（大幅增强）
        new_milestones = len(next_state.milestones_achieved) - len(state.milestones_achieved)
        if new_milestones > 0:
            milestone_reward = new_milestones * 40  # 从20增加到40
            reward += milestone_reward
            print(f"[REWARD] Milestone achieved: +{milestone_reward}")
            
            # 特殊里程碑额外奖励
            for milestone in next_state.milestones_achieved - state.milestones_achieved:
                if 'data_loaded' in milestone:
                    reward += 20
                    print(f"[REWARD] Data loaded milestone: +20")
                elif 'data_validated' in milestone:
                    reward += 20
                    print(f"[REWARD] Data validated milestone: +20")
                elif 'data_transformed' in milestone:
                    reward += 20
                    print(f"[REWARD] Data transformed milestone: +20")
                elif 'data_exported' in milestone:
                    reward += 30
                    print(f"[REWARD] Data exported milestone: +30")
        
        # 6. 语义奖励（保持不变）
        if hasattr(action, 'semantic_score') and action.semantic_score > 0:
            semantic_reward = action.semantic_score * 5.0
            if action.semantic_score > 0.8:
                semantic_reward += 2.0
            reward += semantic_reward
            print(f"[REWARD] Semantic relevance: +{semantic_reward:.1f}")
        
        # 7. 数据流连贯性奖励（增强）
        if hasattr(state, 'data_flow_state') and hasattr(next_state, 'data_flow_state'):
            if self._is_data_flow_progression(state.data_flow_state, next_state.data_flow_state):
                flow_reward = 8  # 从5增加到8
                reward += flow_reward
                print(f"[REWARD] Data flow progression: +{flow_reward}")
        
        # 8. 时间奖励（反转：鼓励持续探索）
        if not next_state.is_completed and state.workflow_step < 30:
            # 前30步给予时间奖励而非惩罚
            time_bonus = 0.2
            reward += time_bonus
        
        # 9. 任务完成奖励（基于模式的不同策略）
        if next_state.is_completed:
            if next_state.is_successful:
                # 基础成功奖励
                if current_success_rate < success_rate_threshold:
                    # 覆盖率模式：重点奖励完成任务
                    base_success = 150
                    
                    # 检查required tools覆盖率
                    if hasattr(state, 'metadata') and 'required_tools' in state.metadata:
                        required_tools = state.metadata['required_tools']
                        executed_required = [t for t in required_tools if t in next_state.execution_sequence]
                        coverage_ratio = len(executed_required) / len(required_tools) if required_tools else 1.0
                        
                        if coverage_ratio == 1.0:
                            # 完美覆盖额外奖励
                            coverage_bonus = 50
                            reward += coverage_bonus
                            print(f"[REWARD] Perfect required tools coverage at completion: +{coverage_bonus}")
                        else:
                            # 部分覆盖惩罚
                            coverage_penalty = -30 * (1 - coverage_ratio)
                            reward += coverage_penalty
                            print(f"[REWARD] Incomplete coverage ({coverage_ratio:.1%}): {coverage_penalty:.1f}")
                else:
                    # 顺序模式：标准奖励
                    base_success = 100
                    
                    # 检查顺序正确性
                    if hasattr(state, 'metadata') and 'required_tools' in state.metadata:
                        required_tools = state.metadata['required_tools']
                        executed_sequence = [t for t in next_state.execution_sequence if t in required_tools]
                        
                        if executed_sequence == required_tools:
                            # 完美顺序执行
                            sequence_bonus = 50
                            reward += sequence_bonus
                            print(f"[REWARD] Perfect sequence execution: +{sequence_bonus}")
                
                reward += base_success
                print(f"[REWARD] Task success (mode: {'coverage' if current_success_rate < success_rate_threshold else 'sequence'}): +{base_success}")
                
                # 效率奖励（两种模式都适用）
                if state.workflow_step < 20:
                    efficiency_bonus = 30 * (20 - state.workflow_step) / 20
                    reward += efficiency_bonus
                    print(f"[REWARD] Efficiency bonus: +{efficiency_bonus:.1f}")
                
                # 零错误奖励
                if next_state.total_errors == 0:
                    perfect_bonus = 30
                    reward += perfect_bonus
                    print(f"[REWARD] Perfect execution (no errors): +{perfect_bonus}")
            else:
                # 失败惩罚（大幅减轻）
                base_failure = -20  # 从-50减少到-20
                
                # 根据进度给予部分奖励
                if next_state.overall_progress > 0.3:
                    partial_credit = next_state.overall_progress * 50
                    reward += partial_credit
                    print(f"[REWARD] Partial progress credit: +{partial_credit:.1f}")
                
                reward += base_failure
                print(f"[REWARD] Task failed: {base_failure}")
        
        # 10. 无操作惩罚（加重）
        if action.action_type == ActionType.NO_OP:
            # 严重惩罚NO_OP，强制智能体行动
            noop_penalty = -5  # 从-1增加到-5
            reward += noop_penalty
            print(f"[REWARD] No-op penalty: {noop_penalty}")
            
            # 连续NO_OP额外惩罚
            if hasattr(state, 'metadata') and state.metadata.get('last_action') == 'NO_OP':
                consecutive_noop_penalty = -10
                reward += consecutive_noop_penalty
                print(f"[REWARD] Consecutive NO_OP penalty: {consecutive_noop_penalty}")
        
        # 11. 恢复奖励（增强）
        if action.action_type == ActionType.RECOVER_ERROR and next_state.consecutive_errors == 0:
            recovery_reward = 8  # 从5增加到8
            reward += recovery_reward
            print(f"[REWARD] Successful recovery: +{recovery_reward}")
        
        # 12. 检查点奖励（优化）
        if action.action_type == ActionType.CREATE_CHECKPOINT:
            if state.consecutive_errors > 0:
                checkpoint_reward = 3  # 从2增加到3
                reward += checkpoint_reward
            else:
                checkpoint_penalty = -0.5  # 从-1减少到-0.5
                reward += checkpoint_penalty
        
        # 13. 奖励裁剪（扩大范围以适应激进奖励）
        reward = np.clip(reward, -50, 500)  # 从300增加到500
        
        # 最小保底奖励：确保大多数动作都有正奖励
        if action.action_type != ActionType.NO_OP and reward < 1:
            reward = 1  # 保底奖励
            print(f"[REWARD] Minimum reward applied: 1")
        
        # 打印模式总结
        if state.workflow_step == 0:  # 首步时打印策略说明
            if current_success_rate < success_rate_threshold:
                print(f"[REWARD] Coverage Mode Active - Learn to use all required tools first")
                print(f"[REWARD] Bonus: Any action +1, Tool attempt +3, First attempt +5, Success +20-50")
            else:
                print(f"[REWARD] Sequence Mode Active - Now optimizing execution order")
        
        print(f"[REWARD] Total reward: {reward:.2f}")
        
        return reward

    def _is_data_flow_progression(self, current: DataFlowState, next: DataFlowState) -> bool:
        """判断数据流是否正向进展"""
        progression_map = {
            DataFlowState.EMPTY: [DataFlowState.INITIALIZED],
            DataFlowState.INITIALIZED: [DataFlowState.VALIDATED, DataFlowState.PARTIAL],
            DataFlowState.PARTIAL: [DataFlowState.TRANSFORMED, DataFlowState.VALIDATED],
            DataFlowState.VALIDATED: [DataFlowState.TRANSFORMED],
            DataFlowState.TRANSFORMED: [],  # 终态
        }
        
        return next in progression_map.get(current, [])
    
    # 新增辅助方法
    def _calculate_data_flow_coherence(self, state: GeneralizedMDPState, 
                                    capability: ToolCapability) -> float:
        """计算数据流一致性得分"""
        coherence = 0.0
        
        if not hasattr(state, 'data_flow_state'):
            return coherence
            
        for operation in capability.semantic_operations:
            if state.data_flow_state == DataFlowState.EMPTY and ('read' in operation or 'load' in operation):
                coherence = 0.9
            elif state.data_flow_state == DataFlowState.INITIALIZED and 'validat' in operation:
                coherence = 0.8
            elif state.data_flow_state == DataFlowState.VALIDATED and 'transform' in operation:
                coherence = 0.8
            elif state.data_flow_state == DataFlowState.TRANSFORMED and ('write' in operation or 'export' in operation):
                coherence = 0.9
                
        return coherence
    
    def _calculate_semantic_alignment(self, task_features: TaskFeatures, 
                                    capability: ToolCapability) -> float:
        """Calculate semantic alignment between task and tool"""
        alignment = 0.0
        
        # Check operation alignment
        for operation in capability.semantic_operations:
            if task_features.requires_validation and 'validat' in operation:
                alignment += 0.3
            elif task_features.requires_transformation and 'transform' in operation:
                alignment += 0.3
            elif task_features.requires_aggregation and 'aggregat' in operation:
                alignment += 0.3
            elif task_features.has_input_requirement and ('read' in operation or 'load' in operation):
                alignment += 0.2
            elif task_features.has_output_requirement and ('write' in operation or 'export' in operation):
                alignment += 0.2
        
        return min(1.0, alignment)
    
    def _validate_outputs(self, state: GeneralizedMDPState):
        """Validate outputs of completed tools"""
        # Simulate validation
        validation_success = np.random.random() < 0.9
        
        if validation_success:
            state.validations_performed.append(f"step_{state.workflow_step}")
            state.validation_results[f"step_{state.workflow_step}"] = True
        else:
            state.consecutive_errors += 1
    
    def _retry_tool(self, state: GeneralizedMDPState, tool_name: str):
        """Retry a failed tool"""
        if tool_name in state.tool_states:
            # Reset tool state for retry
            state.tool_states[tool_name] = ToolExecutionStatus.QUEUED
            # Execute tool again
            self._execute_tool(state, tool_name)
    
    def _recover_from_error(self, state: GeneralizedMDPState):
        """Attempt to recover from errors"""
        # Simple recovery: reset consecutive errors and mark recovery
        state.consecutive_errors = 0
        state.recovery_count += 1
        state.metadata['last_recovery'] = state.workflow_step
    
    def _create_checkpoint(self, state: GeneralizedMDPState):
        """Create a checkpoint"""
        checkpoint = state.create_checkpoint()
        if 'checkpoints' not in state.metadata:
            state.metadata['checkpoints'] = []
        state.metadata['checkpoints'].append(checkpoint)
    
    def _restore_checkpoint(self, state: GeneralizedMDPState):
        """Restore from last checkpoint"""
        if 'checkpoints' in state.metadata and state.metadata['checkpoints']:
            last_checkpoint = state.metadata['checkpoints'][-1]
            state.restore_from_checkpoint(last_checkpoint)


    def step(self, state: GeneralizedMDPState, action: GeneralizedAction) -> Tuple[GeneralizedMDPState, float, bool]:
        """
        Execute a step in the MDP, combining transition and reward calculation.
        
        This method provides a unified interface that matches the expected signature
        in MDPEnvironment, wrapping the existing transition and get_reward methods.
        
        Args:
            state: Current MDP state
            action: Action to execute
            
        Returns:
            tuple: (next_state, reward, done)
                - next_state: The resulting state after executing the action
                - reward: The immediate reward for this transition
                - done: Whether the episode has terminated
        """
        # 打印调试信息，帮助追踪执行流程
        # print(f"[GeneralizedMDP.step] Action: {action}")
        # print(f"[GeneralizedMDP.step] Action type: {action.action_type}")
        # print(f"[GeneralizedMDP.step] Tool name: {action.tool_name}")
        # print(f"[GeneralizedMDP.step] Current state progress: {state.overall_progress:.2%}")
        # print(f"[GeneralizedMDP.step] Current workflow step: {state.workflow_step}")
        
        # 使用现有的 transition 方法执行状态转换
        next_state = self.transition(state, action)
        
        # 打印转换后的状态信息
        # print(f"[GeneralizedMDP.step] Next state progress: {next_state.overall_progress:.2%}")
        # print(f"[GeneralizedMDP.step] Next workflow step: {next_state.workflow_step}")
        # print(f"[GeneralizedMDP.step] Completed: {next_state.is_completed}, Successful: {next_state.is_successful}")
        
        # 使用现有的 get_reward 方法计算奖励
        reward = self.get_reward(state, action, next_state)
        
        # 打印奖励信息
        # print(f"[GeneralizedMDP.step] Reward: {reward:.2f}")
        
        # 使用现有的 is_terminal 方法检查是否结束
        done = next_state.is_completed
        
        # 打印终止状态
        # print(f"[GeneralizedMDP.step] Done: {done}")
        
        # 额外的调试信息：如果有工具执行，打印工具状态
        if action.action_type == ActionType.INVOKE_TOOL and action.tool_name:
            tool_status = next_state.tool_states.get(action.tool_name, "NOT_EXECUTED")
            # print(f"[GeneralizedMDP.step] Tool '{action.tool_name}' status: {tool_status}")
            
            # # 打印工具执行序列
            # print(f"[GeneralizedMDP.step] Execution sequence: {next_state.execution_sequence}")
        
        # 如果出现错误，打印错误信息
        # if next_state.consecutive_errors > 0:
        #     print(f"[GeneralizedMDP.step] Consecutive errors: {next_state.consecutive_errors}")
        #     print(f"[GeneralizedMDP.step] Total errors: {next_state.total_errors}")
        #     if action.tool_name and action.tool_name in next_state.tool_errors:
        #         print(f"[GeneralizedMDP.step] Error type: {next_state.tool_errors[action.tool_name]}")
        
        # 打印里程碑信息
        if hasattr(next_state, 'milestones_achieved') and next_state.milestones_achieved:
            print(f"[GeneralizedMDP.step] Milestones achieved: {next_state.milestones_achieved}")
        
        return next_state, reward, done
# ===========================
# Helper Functions
# ===========================

# 相同位置的修复代码
# 修改的行用注释标注：# <- 修改了这一行

def load_tool_capabilities(registry_path: './mcp_generated_library/tool_registry_consolidated.json') -> Dict[str, ToolCapability]:
    """Load tool capabilities from registry file"""
    with open(registry_path, 'r') as f:
        data = json.load(f)
    
    # Handle different data formats
    if isinstance(data, dict) and 'tools' in data:
        tools_list = data['tools']
    elif isinstance(data, dict) and not any(isinstance(v, dict) for v in data.values()):  # <- 修改了这一行
        # If it's a dict but values aren't dicts, it might be in a different format
        tools_list = data  # <- 修改了这一行
    elif isinstance(data, dict):  # <- 修改了这一行
        # If it's a dict of dicts (tool_name -> tool_data), convert to list  # <- 修改了这一行
        tools_list = []  # <- 修改了这一行
        for tool_name, tool_data in data.items():  # <- 修改了这一行
            if isinstance(tool_data, dict):  # <- 修改了这一行
                tool_data['name'] = tool_name  # Ensure name is set  # <- 修改了这一行
                tools_list.append(tool_data)  # <- 修改了这一行
    else:
        tools_list = data
    
    capabilities = {}
    for tool_data in tools_list:
        if isinstance(tool_data, dict):
            tool_name = tool_data.get('name', tool_data.get('tool_name', 'unknown'))
            
            # Extract semantic operations from description or operations field

            semantic_ops = tool_data.get('semantic_operations', [])

            # 增强的语义操作提取逻辑
            if not semantic_ops:
                logger.debug(f" Extracting semantic operations for tool: {tool_name}")
                
                # 合并多个信息源进行提取
                text_sources = []
                
                # 1. 工具名称
                if tool_name:
                    text_sources.append(tool_name.lower())
                
                # 2. 描述
                if 'description' in tool_data:
                    text_sources.append(tool_data['description'].lower())
                
                # 3. 参数信息（如果有的话）
                if 'parameters' in tool_data:
                    for param in tool_data['parameters']:
                        if isinstance(param, dict) and 'name' in param:
                            text_sources.append(param['name'].lower())
                
                # 4. 返回值信息
                if 'returns' in tool_data:
                    for ret in tool_data['returns']:
                        if isinstance(ret, dict) and 'name' in ret:
                            text_sources.append(ret['name'].lower())
                
                # 合并所有文本源
                combined_text = ' '.join(text_sources)
                logger.debug(f" Combined text for extraction: {combined_text[:100]}...")
                
                # 扩展的操作关键词映射
                operation_patterns = {
                    'read': ['read', 'load', 'fetch', 'get', 'retrieve', 'access', 'scan', 'import', 'input', 'source'],
                    'write': ['write', 'save', 'export', 'output', 'store', 'persist', 'put', 'post', 'send', 'publish'],
                    'validate': ['validat', 'verify', 'check', 'ensure', 'confirm', 'test', 'assert', 'audit'],
                    'transform': ['transform', 'convert', 'process', 'modify', 'change', 'format', 'parse', 'decode'],
                    'filter': ['filter', 'select', 'extract', 'remove', 'criteria', 'match', 'search', 'find'],
                    'aggregate': ['aggregat', 'combine', 'merge', 'join', 'consolidate', 'sum', 'group', 'collect'],
                    'compute': ['compute', 'calculate', 'analyze', 'process', 'simulate', 'predict', 'estimate'],
                    'monitor': ['monitor', 'track', 'watch', 'observe', 'detect', 'measure', 'gauge'],
                    'cache': ['cache', 'buffer', 'temporary', 'store', 'memoize', 'retain'],
                    'integrate': ['integrat', 'connect', 'link', 'coordinate', 'synchronize', 'map', 'bridge'],
                    'authenticate': ['auth', 'login', 'credential', 'token', 'security', 'permission'],
                    'compress': ['compress', 'zip', 'pack', 'reduce', 'compact'],
                    'network': ['network', 'http', 'api', 'request', 'response', 'web', 'url'],
                    'queue': ['queue', 'schedule', 'batch', 'async', 'background', 'delay'],
                    'log': ['log', 'record', 'trace', 'debug', 'audit', 'history'],
                    'notify': ['notify', 'alert', 'message', 'inform', 'signal', 'broadcast']
                }
                
                # 从文本中提取操作
                extracted_count = 0
                for operation, keywords in operation_patterns.items():
                    for keyword in keywords:
                        if keyword in combined_text:
                            if operation not in semantic_ops:
                                semantic_ops.append(operation)
                                extracted_count += 1
                                logger.debug(f" Extracted operation '{operation}' from keyword '{keyword}'")
                            break  # 找到一个匹配就够了
                
                # 如果还是没有提取到任何操作，基于工具名称进行智能推断
                if not semantic_ops and tool_name:
                    logger.debug(f" No operations extracted, inferring from tool name: {tool_name}")
                    
                    # 基于工具名称的模式推断
                    name_lower = tool_name.lower()
                    
                    # 常见的工具名称模式
                    if 'reader' in name_lower or 'scanner' in name_lower or 'fetcher' in name_lower:
                        semantic_ops.append('read')
                    elif 'writer' in name_lower or 'exporter' in name_lower or 'poster' in name_lower:
                        semantic_ops.append('write')
                    elif 'validator' in name_lower or 'checker' in name_lower:
                        semantic_ops.append('validate')
                    elif 'transformer' in name_lower or 'converter' in name_lower or 'parser' in name_lower:
                        semantic_ops.append('transform')
                    elif 'filter' in name_lower:
                        semantic_ops.append('filter')
                    elif 'aggregator' in name_lower or 'combiner' in name_lower:
                        semantic_ops.append('aggregate')
                    elif 'calculator' in name_lower or 'analyzer' in name_lower or 'simulator' in name_lower:
                        semantic_ops.append('compute')
                    elif 'monitor' in name_lower or 'tracker' in name_lower:
                        semantic_ops.append('monitor')
                    elif 'cache' in name_lower:
                        semantic_ops.append('cache')
                    elif 'authenticator' in name_lower:
                        semantic_ops.append('authenticate')
                    elif 'compressor' in name_lower:
                        semantic_ops.append('compress')
                    elif 'network' in name_lower or 'http' in name_lower:
                        semantic_ops.append('network')
                    elif 'queue' in name_lower or 'scheduler' in name_lower:
                        semantic_ops.append('queue')
                    elif 'logger' in name_lower:
                        semantic_ops.append('log')
                    elif 'notifier' in name_lower:
                        semantic_ops.append('notify')
                    else:
                        # 最后的备用方案：基于工具名称的前缀/后缀推断
                        if name_lower.startswith(('data_', 'file_')):
                            semantic_ops.append('transform')  # 数据/文件操作通常涉及转换
                        elif name_lower.startswith('network_'):
                            semantic_ops.append('network')
                        elif name_lower.startswith('utility_'):
                            semantic_ops.append('cache')  # 工具类通常涉及缓存/辅助功能
                        elif name_lower.startswith('integration_'):
                            semantic_ops.append('integrate')
                        elif name_lower.startswith('computation_'):
                            semantic_ops.append('compute')
                        else:
                            # 实在没办法，给一个默认的通用操作
                            semantic_ops.append('transform')
                    
                    if semantic_ops:
                        logger.debug(f" Inferred operations from tool name: {semantic_ops}")
                
                logger.debug(f" Final semantic_ops for {tool_name}: {semantic_ops}")

            # 确保至少有一个操作（避免空列表）
            if not semantic_ops:
                print(f"[WARNING] No semantic operations found for {tool_name}, using default 'transform'")
                semantic_ops = ['transform']  # 默认操作
            
            capability = ToolCapability(
                tool_name=tool_name,
                input_types=tool_data.get('input_types', tool_data.get('inputs', {})),
                output_types=tool_data.get('output_types', tool_data.get('outputs', {})),
                error_types=[ErrorCategory.EXECUTION_ERROR],
                dependencies=tool_data.get('dependencies', []),
                parallel_safe=tool_data.get('parallel_safe', True),
                idempotent=tool_data.get('idempotent', True),
                semantic_operations=semantic_ops,
                data_domains=tool_data.get('data_domains', [])
            )
            capabilities[tool_name] = capability
    
    return capabilities


# ===========================
# Main Execution
# ===========================

if __name__ == "__main__":
    # Example usage with Phase 3 features
    logger.info("Generalized MDP Framework - Phase 3 Demo")
    
    # Create example tools
    example_tools = {
        'data_reader': ToolCapability(
            tool_name='data_reader',
            input_types={'source': 'string'},
            output_types={'data': 'string'},
            dependencies=[],
            semantic_operations=['read'],
            data_domains=['file_operations']
        ),
        'data_validator': ToolCapability(
            tool_name='data_validator',
            input_types={'data': 'string'},
            output_types={'valid': 'bool', 'errors': 'list'},
            dependencies=['data_reader'],
            semantic_operations=['validate']
        ),
        'data_transformer': ToolCapability(
            tool_name='data_transformer',
            input_types={'data': 'string'},
            output_types={'transformed_data': 'string'},
            dependencies=['data_validator'],
            semantic_operations=['transform']
        ),
        'data_exporter': ToolCapability(
            tool_name='data_exporter',
            input_types={'data': 'string'},
            output_types={'success': 'bool'},
            dependencies=['data_transformer'],
            semantic_operations=['write'],
            data_domains=['file_operations']
        )
    }
    
    # Create MDP
    mdp = GeneralizedMDP(example_tools)
    
    # Create initial state with task-aware features
    state = TaskAwareMDPState(
        task_id='example_task_001',
        task_type='data_pipeline',
        task_objective='Read data from source, validate it, transform it, and export the results'
    )
    
    print(f"Task: {state.task_objective}")
    print(f"Task Features:")
    print(f"  Domain: {state.task_features.domain.value}")
    print(f"  Complexity: {state.task_features.complexity.value}")
    print(f"  Estimated steps: {state.task_features.estimated_steps}")
    print(f"  Expected milestones: {state.expected_milestones}")
    print()
    
    # Simulate workflow
    for step in range(10):
        print(f"Step {step + 1}:")
        
        # Get available actions
        actions = mdp.get_available_actions(state)
        sorted_actions = sorted(actions, key=lambda a: a.confidence, reverse=True)
        
        print(f"  Available actions: {len(actions)}")
        for action in sorted_actions[:3]:
            print(f"    - {action} (confidence: {action.confidence:.2f})")
        
        if actions:
            # Select action with highest confidence
            action = sorted_actions[0]
            print(f"  Selected: {action}")
            
            # Execute action
            next_state = mdp.transition(state, action)
            reward = mdp.get_reward(state, action, next_state)
            
            print(f"  Result:")
            print(f"    Progress: {state.overall_progress:.1%} → {next_state.overall_progress:.1%}")
            print(f"    Milestones: {len(state.milestones_achieved)} → {len(next_state.milestones_achieved)}")
            print(f"    Reward: {reward:.2f}")
            
            # Show new milestones
            new_milestones = next_state.milestones_achieved - state.milestones_achieved
            if new_milestones:
                print(f"    New milestones: {new_milestones}")
            
            # Update state
            state = next_state
            
            if state.is_completed:
                print(f"\n✅ Task completed!")
                print(f"   Success: {state.is_successful}")
                print(f"   Total steps: {state.workflow_step}")
                print(f"   Final progress: {state.overall_progress:.1%}")
                print(f"   Milestones achieved: {len(state.milestones_achieved)}/{len(state.expected_milestones)}")
                break
        
        print()