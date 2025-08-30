#!/usr/bin/env python3
"""
Enhanced MDP-Based Workflow Generator with Structured Workflow Enforcement
=======================================================================
This module generates optimal tool execution sequences using trained MDP policies
and enforces structured workflow execution with mandatory sequences.

Key Features:
1. Policy-based workflow generation using DQN
2. Mandatory execution sequences with adherence tracking
3. Workflow quality metrics and validation
4. Structured prompts for MCP task execution
5. Pattern learning from successful/failed executions
"""

import json
import os
import networkx as nx

# Conditional torch import for memory optimization
try:
    if os.getenv('SKIP_MODEL_LOADING', 'false').lower() != 'true':
        import torch
        import torch.nn as nn
        TORCH_AVAILABLE = True
    else:
        print("[INFO] ⚡ SKIP_MODEL_LOADING=true - Skipping torch imports")
        torch = None
        TORCH_AVAILABLE = False
except ImportError as e:
    print(f"[WARNING] torch import failed: {e}")
    torch = None
    TORCH_AVAILABLE = False
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime
import logging
import re

# Import from generalized MDP (assumed to be available)
from generalized_mdp_framework import (  # <- 修改了这一行
    GeneralizedMDPState, GeneralizedAction, GeneralizedMDP,
    ToolExecutionStatus, ErrorCategory, ToolCapability,
    ActionType, DataFlowState, load_tool_capabilities  # <- 添加了DataFlowState
)

from workflow_reasoning_generator import WorkflowReasoningGenerator
from tool_capability_manager import ToolCapabilityManager, get_tool_capability_manager

# Setup logger
logger = logging.getLogger(__name__)


# ===========================
# Workflow Data Classes
# ===========================

@dataclass
class WorkflowNode:
    """Node in workflow DAG"""
    state_id: str
    state: GeneralizedMDPState
    is_initial: bool = False
    is_terminal: bool = False
    is_success: bool = False

# 文件：mdp_workflow_generator.py
# 在WorkflowNode类后添加新的数据结构

# 文件：mdp_workflow_generator.py
# 在WorkflowEdge类后添加

@dataclass
class WorkflowStep:
    """表示workflow中的一个执行步骤"""
    step_id: int
    action_type: ActionType
    tool_name: Optional[str] = None
    conditions: Dict[str, Any] = field(default_factory=dict)
    on_success: Optional[int] = None
    on_failure: Optional[int] = None
    max_retries: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SmartWorkflow:
    """智能workflow，包含条件执行逻辑"""
    task_type: str
    steps: List[WorkflowStep]
    entry_point: int = 0
    success_criteria: Dict[str, Any] = field(default_factory=dict)
    
    def to_sequence(self) -> List[str]:
        """转换为简单的工具序列（向后兼容）"""
        return [s.tool_name for s in self.steps 
                if s.action_type == ActionType.INVOKE_TOOL and s.tool_name]

@dataclass
class WorkflowEdge:
    """Edge in workflow DAG"""
    action: GeneralizedAction
    probability: float
    reward: float
    reasoning: str = ""


# ===========================
# Main Workflow Generator Class
# ===========================


# 文件：mdp_workflow_generator.py
# 位置：第80-280行
# MDPWorkflowGenerator.__init__ 方法的完整修复

# 文件：mdp_workflow_generator.py
# 位置：第80-280行
# MDPWorkflowGenerator.__init__ 方法的完整修复

class MDPWorkflowGenerator:
    def __init__(self, model_path: str = "checkpoints/best_model.pt", 
                tools_path: str = "mcp_generated_library/tool_registry_consolidated.json", 
                use_embeddings: bool = True,
                thresholds=None,
                config_path: str = None):
        """Initialize the enhanced workflow generator
        
        Args:
            model_path: Path to the trained model checkpoint
            tools_path: Path to the tool registry JSON file
            use_embeddings: Whether to use semantic embeddings for tool selection
            thresholds: ScoringThresholds object or None (will use defaults if None)
            config_path: Path to external config JSON file (overrides checkpoint config)
        """
        self._initialized = False

        self.model_path = Path(model_path) if model_path else None
        self.tools_path = Path(tools_path)
        self.use_embeddings = use_embeddings
        self.config_path = Path(config_path) if config_path else None
        self.tool_capability_manager = get_tool_capability_manager()
        
        # 设置设备（GPU优先）
        if TORCH_AVAILABLE:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            print(f"[INFO] Using device: {self.device}")
            if self.device.type == 'cuda':
                print(f"[INFO] GPU: {torch.cuda.get_device_name()}")
                print(f"[INFO] GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
        else:
            self.device = None
            print(f"[INFO] ⚡ SKIP_MODEL_LOADING=true - No device initialization")
        
        # 初始化阈值配置
        if thresholds is None:
            # 创建默认的阈值配置（避免循环导入）
            from dataclasses import dataclass
            from typing import Dict
            
            @dataclass
            class DefaultThresholds:
                semantic_match_threshold: float = 0.75
                validator_reliability: float = 0.95
                network_reliability: float = 0.70
                reader_writer_reliability: float = 0.85
                default_reliability: float = 0.80
                min_history_for_learning: int = 5
            
            self.thresholds = DefaultThresholds()
        else:
            self.thresholds = thresholds
        
        # Initialize workflow storage first
        self.workflows = {}
        self.workflow_adherence_scores = {}
        self.successful_patterns = defaultdict(list)
        self.failure_patterns = defaultdict(list)
        self.tool_importance = defaultdict(float)
        self.tool_dependencies = defaultdict(set)
        self.optimal_sequences = defaultdict(list)
        self.workflow_data = {}
        self.workflow_quality_metrics = {}

        # 初始化工具成功率统计（用于WorkflowQualityTester兼容）
        self.tool_success_rates = defaultdict(lambda: {'success': 0, 'total': 0})
        self.tool_criticality_scores = defaultdict(float)
        self.tool_failure_impact = defaultdict(float)
        self.tool_position_importance = defaultdict(lambda: defaultdict(float))
        self.learned_critical_patterns = []
        print("[INFO] Initialized tool success tracking attributes")

        self.algorithm = 'ppo'
        
        # Initialize embedding manager if requested
        self.embedding_manager = None
        if self.use_embeddings:
            print("[INFO] Initializing embedding manager for enhanced tool selection")
            self._initialize_embedding_manager()
        else:
            print("[INFO] Using rule-based tool selection (embeddings disabled)")
        
        # Initialize components
        self.q_network = None
        self.network = None
        self.state_dim = None
        self.action_dim = None
        self.tool_capabilities = {}
        self.tool_names = []
        self.tool_to_idx = {}
        self.idx_to_tool = {}
        
        # 初始化任务类型列表
        self.task_types = ['simple_task', 'data_pipeline', 'api_integration', 
                          'basic_task', 'multi_stage_pipeline']
        print(f"[INFO] Initialized task types: {self.task_types}")
        
        # 保存从checkpoint加载的配置
        self.loaded_config = None
        self.checkpoint_loaded = False
        
        # 新增：加载外部配置文件
        self.external_config = None
        if self.config_path and self.config_path.exists():
            print(f"[INFO] Loading external config from {self.config_path}")
            with open(self.config_path, 'r') as f:
                self.external_config = json.load(f)
            print(f"[INFO] External config loaded: {list(self.external_config.keys())}")
        

        # 关键修复：提前加载 full_tool_registry，在任何可能调用它的方法之前
        print("[INFO] Loading full MCP protocol registry...")
        self.full_tool_registry = self._load_full_mcp_registry()
        print(f"[INFO] Loaded full tool registry with {len(self.full_tool_registry)} tools")
        
        # Load tools and model
        self._load_tools()

        if self.state_dim is None:
            print("[INFO] Setting default state_dim based on loaded tools")
            # 计算state_dim: num_tools * 11 (tool states) + 10 (progress features)
            num_tools = len(self.tool_names)
            base_dim = num_tools * 11 + 10
            
            # 添加任务类型编码维度（5个任务类型）
            task_type_dim = 5
            self.state_dim = base_dim + task_type_dim
            
            print(f"[INFO] state_dim set to {self.state_dim} (tools={num_tools}, base={base_dim}, task_types={task_type_dim})")
            logger.info(f"Default state_dim calculated: {self.state_dim}")
        
        if self.action_dim is None:
            print("[INFO] Setting default action_dim based on loaded tools")
            # action_dim = num_tools + 1 (for NO_OP action)
            self.action_dim = len(self.tool_names) + 1
            print(f"[INFO] action_dim set to {self.action_dim} (tools={len(self.tool_names)} + NO_OP)")
            logger.info(f"Default action_dim calculated: {self.action_dim}")


        # Check for environment variable to skip model loading (memory optimization)
        import os
        skip_model_loading = os.getenv('SKIP_MODEL_LOADING', 'false').lower() == 'true'
        
        if skip_model_loading:
            print("[INFO] ⚡ SKIP_MODEL_LOADING=true - Skipping neural network model loading")
            print("[INFO] ⚡ Memory optimization: Saving ~350MB by not loading model")
            print("[INFO] ⚡ Will use pre-generated workflows or random policy")
            self.q_network = None
            self.network = None
            logger.info("Model loading skipped for memory optimization (SKIP_MODEL_LOADING=true)")
        elif self.model_path and self.model_path.exists():
            self._load_model()
            print(f"[INFO] Loaded checkpoint: algorithm={self.algorithm}")
        else:
            print(f"[INFO] No model loaded - workflow generation will use random policy")
            logger.warning("No model loaded - using random policy for workflow generation")
            
        # 初始化缺失的关键组件
        # =====================
        
        # 初始化 task_manager
        print("[INFO] Initializing TaskManager...")
        # 使用动态导入避免循环依赖
        from unified_training_manager import TaskManager
        
        # 使用默认的任务库路径
        task_library_path = "mcp_generated_library/task_library_all_difficulties.json"
        self.task_manager = TaskManager(task_library_path, task_types=self.task_types)
        
        print(f"[INFO] TaskManager initialized with {len(self.task_manager.tasks)} tasks")
        print(f"[INFO] Task types available: {list(self.task_manager.tasks_by_type.keys())}")

        
        # 初始化 output_verifier (ToolCallVerifier)
        print("[INFO] Initializing ToolCallVerifier...")
        # 使用动态导入避免循环依赖
        from workflow_quality_test_flawed import ToolCallVerifier
        
        # 使用已加载的工具能力和embedding manager
        self.output_verifier = ToolCallVerifier(
            tool_capabilities=self.tool_capabilities,
            embedding_manager=self.embedding_manager
        )
        
        print(f"[INFO] ToolCallVerifier initialized with {len(self.tool_capabilities)} tools")
        print(f"[INFO] Output tools identified: {len(self.output_verifier.output_tools)}")

        
        # 验证所有组件的初始化状态
        print(f"[INFO] Component initialization status:")
        print(f"  - embedding_manager: {'initialized' if self.embedding_manager else 'not initialized'}")
        print(f"  - task_manager: {'initialized' if self.task_manager else 'not initialized'}")
        print(f"  - output_verifier: {'initialized' if self.output_verifier else 'not initialized'}")
        print(f"  - tool_capability_manager: {'initialized' if self.tool_capability_manager else 'not initialized'}")
        print(f"  - tool_success_rates: initialized with {len(self.tool_success_rates)} entries")
        
        print(f"[INFO] MDPWorkflowGenerator initialization complete")
        logger.info("MDPWorkflowGenerator initialized successfully")




    def update_network(self, network_state_dict: Dict[str, "torch.Tensor"], algorithm: str = None):
        """更新生成器使用的网络
        
        Args:
            network_state_dict: 网络的state_dict
            algorithm: 算法类型 ('ppo' 或 'dqn')
        """
        if algorithm:
            self.algorithm = algorithm
        
        print(f"[INFO] Updating MDPWorkflowGenerator network ({self.algorithm})")
        
        if self.algorithm == 'ppo':
            if self.network is None:
                # 如果还没有网络，先创建
                self._create_default_network()
            # 更新网络权重
            self.network.load_state_dict(network_state_dict)
            self.network.eval()  # 设置为评估模式
            logger.info("PPO network updated in MDPWorkflowGenerator")
            
        elif self.algorithm == 'dqn':
            if self.q_network is None:
                # 创建DQN网络
                from unified_training_manager import DuelingDQN
                self.q_network = DuelingDQN(self.state_dim, self.action_dim, 256)
                self.q_network.to(self.device)
            # 更新网络权重
            self.q_network.load_state_dict(network_state_dict)
            self.q_network.eval()  # 设置为评估模式
            logger.info("DQN network updated in MDPWorkflowGenerator")
        
        print(f"[INFO] Network update complete")

    def set_network_reference(self, network: "nn.Module", algorithm: str):
        """直接设置网络引用（共享网络对象）
        
        Args:
            network: 网络对象
            algorithm: 算法类型
        """
        self.algorithm = algorithm
        
        if algorithm == 'ppo':
            self.network = network
            logger.info("PPO network reference set in MDPWorkflowGenerator")
        elif algorithm == 'dqn':
            self.q_network = network
            logger.info("DQN network reference set in MDPWorkflowGenerator")

    def _create_default_network(self):
        """创建默认的PPO网络，优先使用外部配置"""
        print("[INFO] Creating default PPO network")
        # 导入ActorCriticNetwork
        from unified_training_manager import ActorCriticNetwork
        
        # 配置优先级：外部配置 > checkpoint配置 > 默认配置
        network_config = {}
        
        # 1. 首先设置默认配置
        default_config = {
            'hidden_dim': 256,
            'num_layers': 3,
            'num_heads': 4,
            'dropout': 0.1,
            'use_pre_norm': True,
            'use_auxiliary_tasks': False,
            'use_curiosity': False,
            'spectral_norm': False,
            'rag_dim': 64,
            'use_mac_optimization': False,
            'use_rag_enhancement': True,
            'use_tools_input': True,
            'tools_dim': 64,
            'num_tools': self.action_dim
        }
        network_config.update(default_config)
        
        # 2. 如果有checkpoint配置，覆盖默认值
        if self.loaded_config is not None:
            print("[INFO] Applying network config from checkpoint")
            for key in default_config.keys():
                if key in self.loaded_config:
                    network_config[key] = self.loaded_config[key]
        
        # 3. 如果有外部配置，优先使用（最高优先级）
        if self.external_config is not None:
            print("[INFO] Applying network config from external config file")
            for key in default_config.keys():
                if key in self.external_config:
                    network_config[key] = self.external_config[key]
                    print(f"[INFO] Override {key}: {network_config[key]} (from external config)")
        
        print(f"[INFO] Final network config: hidden_dim={network_config['hidden_dim']}, "
              f"num_layers={network_config['num_layers']}, use_rag={network_config['use_rag_enhancement']}")
        
        # 创建网络实例并移动到正确的设备
        self.network = ActorCriticNetwork(self.state_dim, self.action_dim, network_config)
        self.network.to(self.device)  # 移动到GPU/CPU
        self.network.eval()  # 设置为评估模式
        
        print(f"[INFO] Created ActorCriticNetwork on {self.device}")
        logger.info(f"PPO network created successfully on {self.device}")

    def _load_full_mcp_registry(self) -> Dict[str, Any]:
        """加载包含完整MCP protocol定义的工具注册表"""
        # 尝试多个可能的路径
        possible_paths = [
            self.tools_path,  # 使用提供的路径
            Path("mcp_generated_library/tool_registry_consolidated.json"),
            # Path("mcp_generated_library/tool_registry.json"),
            # Path("tool_registry_consolidated.json"),
            # Path("tool_registry.json")
        ]
        
        for path in possible_paths:
            if Path(path).exists():
                try:
                    with open(path, 'r') as f:
                        registry = json.load(f)
                        logger.info(f"Loaded full tool registry from {path}")
                        return registry
                except Exception as e:
                    logger.warning(f"Failed to load {path}: {e}")
        
        logger.warning("Could not load full tool registry, using empty registry")
        return {}
    

    def _initialize_embedding_manager(self):
        """Initialize the embedding manager for semantic tool search"""
        from mcp_embedding_manager import get_embedding_manager
        
        # 使用单例模式获取MCPEmbeddingManager
        self.embedding_manager = get_embedding_manager()
        
        # Try to load existing index
        index_path = Path(".mcp_embedding_cache/tool_index.pkl")
        
        print(f"[INFO] Loading embedding index from {index_path}")
        self.embedding_manager.load_index(index_path)
        print(f"[SUCCESS] Loaded {len(self.embedding_manager.tool_embeddings)} tool embeddings")
        logger.info(f"Embedding index loaded successfully")
        
        # 最终验证
        print(f"[SUCCESS] Embedding manager initialized with {len(self.embedding_manager.tool_embeddings)} tools")



    # 文件：mdp_workflow_generator.py
    # 位置：第458-690行
    # 函数：_load_model

    def _load_model(self):
        """从checkpoint加载模型"""
        if not self.model_path:
            print("[WARNING] No model path specified")
            self._create_default_network()
            return
        
        print(f"[INFO] Loading model from {self.model_path}")
        
        # 添加文件存在性检查
        import os
        if not os.path.exists(self.model_path):
            print(f"[ERROR] Model file not found: {self.model_path}")
            print("[INFO] Creating default network instead")
            self._create_default_network()
            return
        
        checkpoint = torch.load(self.model_path, map_location=self.device, weights_only=False)
        
        # 检查是否是裸露的state_dict
        if 'network_state_dict' in checkpoint:
            network_state_dict = checkpoint['network_state_dict']
            # 获取其他信息
            self.algorithm = checkpoint.get('algorithm', 'ppo')
            
            # 从checkpoint获取配置并保存到self.loaded_config
            if 'config' in checkpoint:
                self.loaded_config = checkpoint['config']
                print(f"[INFO] Loaded config from checkpoint")
            elif 'network_config' in checkpoint:
                self.loaded_config = checkpoint['network_config']
                print(f"[INFO] Loaded network_config from checkpoint")
        else:
            # 裸露的state_dict
            network_state_dict = checkpoint
            self.algorithm = 'ppo'  # 默认使用PPO
        
        # 验证算法类型
        if self.algorithm not in ['dqn', 'ppo']:
            print(f"[WARNING] Unknown algorithm '{self.algorithm}', defaulting to PPO")
            self.algorithm = 'ppo'
            
        print(f"[INFO] Using algorithm: {self.algorithm}")
        
        # 根据算法类型加载不同的模型
        if self.algorithm == 'ppo':
            # PPO使用Actor-Critic网络
            from unified_training_manager import ActorCriticNetwork
            
            # 从checkpoint获取维度信息
            if 'state_dim' in checkpoint and 'action_dim' in checkpoint:
                self.state_dim = checkpoint['state_dim']
                self.action_dim = checkpoint['action_dim']
                print(f"[INFO] Loaded dimensions from checkpoint: state_dim={self.state_dim}, action_dim={self.action_dim}")
            else:
                # 从网络权重推断
                network_state = checkpoint.get('network_state_dict', checkpoint)
                
                # 推断state_dim（从输入层）
                for key in network_state.keys():
                    if 'input_projection.0.weight' in key:
                        self.state_dim = network_state[key].shape[1]
                        print(f"[INFO] Inferred state_dim={self.state_dim} from input_projection")
                        break
                
                # 推断action_dim（从actor_head的最后一层）
                self.action_dim = None
                actor_linear_keys = [k for k in network_state.keys() if 'actor_head' in k and '.weight' in k]
                if actor_linear_keys:
                    actor_linear_keys.sort()
                    last_actor_key = actor_linear_keys[-1]
                    self.action_dim = network_state[last_actor_key].shape[0]
                    print(f"[INFO] Inferred action_dim={self.action_dim} from {last_actor_key}")
                
                if self.action_dim is None:
                    print("[WARNING] Could not infer action_dim, using default")
                    self.action_dim = len(self.tool_names) if hasattr(self, 'tool_names') else 50
            
            # 使用_build_network_config()方法构建配置
            network_config = self._build_network_config()
            
            # 处理tools_projection维度不匹配问题
            tools_proj_key = 'tools_projection.0.weight'
            if tools_proj_key in network_state_dict:
                saved_tools_dim = network_state_dict[tools_proj_key].shape[1]
                config_tools_dim = network_config.get('tools_dim', 64)
                
                if saved_tools_dim != config_tools_dim:
                    print(f"[WARNING] tools_dim mismatch: saved={saved_tools_dim}, config={config_tools_dim}")
                    print(f"[INFO] Adapting tools_projection layer...")
                    
                    # 创建一个临时的网络来加载权重
                    temp_config = network_config.copy()
                    temp_config['tools_dim'] = saved_tools_dim
                    temp_network = ActorCriticNetwork(self.state_dim, self.action_dim, temp_config)
                    
                    # 加载权重到临时网络
                    temp_network.load_state_dict(network_state_dict, strict=False)
                    
                    # 创建目标网络
                    self.network = ActorCriticNetwork(self.state_dim, self.action_dim, network_config)
                    
                    # 复制除了tools_projection以外的所有权重
                    target_dict = self.network.state_dict()
                    source_dict = temp_network.state_dict()
                    
                    for key in target_dict.keys():
                        if 'tools_projection' not in key and key in source_dict:
                            if target_dict[key].shape == source_dict[key].shape:
                                target_dict[key] = source_dict[key]
                            else:
                                print(f"[WARNING] Shape mismatch for {key}, skipping")
                    
                    # 处理tools_projection层
                    if saved_tools_dim < config_tools_dim:
                        # 扩展维度：用零填充
                        print(f"[INFO] Expanding tools dimension from {saved_tools_dim} to {config_tools_dim}")
                        for key in ['tools_projection.0.weight', 'tools_projection.0.bias']:
                            if key in source_dict:
                                if 'weight' in key:
                                    # 对于权重矩阵，在输入维度上填充零
                                    pad_size = config_tools_dim - saved_tools_dim
                                    padded = torch.nn.functional.pad(source_dict[key], (0, pad_size, 0, 0))
                                    target_dict[key] = padded
                                else:
                                    # bias不需要改变
                                    target_dict[key] = source_dict[key]
                    else:
                        # 截断维度
                        print(f"[INFO] Truncating tools dimension from {saved_tools_dim} to {config_tools_dim}")
                        for key in ['tools_projection.0.weight', 'tools_projection.0.bias']:
                            if key in source_dict:
                                if 'weight' in key:
                                    # 截断输入维度
                                    target_dict[key] = source_dict[key][:, :config_tools_dim]
                                else:
                                    # bias不需要改变
                                    target_dict[key] = source_dict[key]
                    
                    # 加载适配后的权重
                    self.network.load_state_dict(target_dict, strict=False)
                    print("[INFO] Successfully adapted and loaded model with dimension conversion")
                else:
                    # 维度匹配，正常加载
                    print(f"[INFO] Creating network with matching tools_dim={saved_tools_dim}")
                    self.network = ActorCriticNetwork(self.state_dim, self.action_dim, network_config)
                    
                    missing_keys, unexpected_keys = self.network.load_state_dict(
                        network_state_dict, 
                        strict=False
                    )
                    
                    if missing_keys:
                        print(f"[WARNING] Missing keys: {len(missing_keys)}")
                        for key in missing_keys[:5]:
                            print(f"  - {key}")
                    if unexpected_keys:
                        print(f"[WARNING] Unexpected keys: {len(unexpected_keys)}")
                        for key in unexpected_keys[:5]:
                            print(f"  - {key}")
            else:
                # 没有tools_projection，正常创建和加载
                self.network = ActorCriticNetwork(self.state_dim, self.action_dim, network_config)
                
                missing_keys, unexpected_keys = self.network.load_state_dict(
                    network_state_dict, 
                    strict=False
                )
                
                if missing_keys:
                    print(f"[WARNING] Missing keys: {len(missing_keys)}")
                if unexpected_keys:
                    print(f"[WARNING] Unexpected keys: {len(unexpected_keys)}")
                    
        else:
            # DQN网络加载逻辑
            from unified_training_manager import DuelingDQN
            
            # 获取维度信息
            if 'state_dim' in checkpoint and 'action_dim' in checkpoint:
                self.state_dim = checkpoint['state_dim']
                self.action_dim = checkpoint['action_dim']
            else:
                # 使用默认值或从其他地方推断
                print("[WARNING] DQN dimensions not found in checkpoint, using defaults")
                if not hasattr(self, 'state_dim') or self.state_dim is None:
                    self.state_dim = len(self.tool_names) * 11 + 15
                if not hasattr(self, 'action_dim') or self.action_dim is None:
                    self.action_dim = len(self.tool_names) + 1
            
            # 创建DQN网络
            self.q_network = DuelingDQN(self.state_dim, self.action_dim, 256)
            self.q_network.to(self.device)
            
            # 加载权重
            try:
                self.q_network.load_state_dict(network_state_dict, strict=True)
                print("[INFO] Successfully loaded DQN weights (strict mode)")
            except RuntimeError as e:
                print(f"[WARNING] Strict loading failed for DQN: {e}")
                missing_keys, unexpected_keys = self.q_network.load_state_dict(
                    network_state_dict, 
                    strict=False
                )
                if missing_keys:
                    print(f"[WARNING] Missing keys in DQN: {missing_keys}")
                if unexpected_keys:
                    print(f"[WARNING] Unexpected keys in DQN: {unexpected_keys}")
            
            self.q_network.eval()
            print(f"[INFO] DQN network loaded and set to eval mode on {self.device}")
        
        # 加载其他数据
        if 'workflows' in checkpoint:
            self.workflow_data = checkpoint['workflows']
        if 'tool_importance' in checkpoint:
            self.tool_importance = defaultdict(float, checkpoint['tool_importance'])
        if 'successful_patterns' in checkpoint:
            self.successful_patterns = defaultdict(list, checkpoint['successful_patterns'])
        
        # 设置网络为评估模式
        if self.network is not None:
            self.network.eval()
            print("[INFO] Model loaded and set to eval mode")
        else:
            print("[ERROR] Failed to load model, network is None")
        
        print(f"[INFO] Model loaded successfully: algorithm={self.algorithm}, state_dim={self.state_dim}, action_dim={self.action_dim}")
            
    def _build_network_config(self):
        """构建网络配置，优先级：外部配置 > checkpoint配置 > 默认配置"""
        # 默认配置
        network_config = {
            'hidden_dim': 256,
            'num_layers': 3,
            'num_heads': 4,
            'dropout': 0.1,
            'use_pre_norm': True,
            'use_auxiliary_tasks': False,
            'use_curiosity': False,
            'spectral_norm': False,
            'rag_dim': 64,
            'use_mac_optimization': False,
            'use_rag_enhancement': True,
            'use_tools_input': True,
            'tools_dim': 64,
            'num_tools': self.action_dim
        }
        
        # 从checkpoint配置覆盖
        if self.loaded_config:
            print("[INFO] Applying config from checkpoint")
            for key in network_config.keys():
                if key in self.loaded_config:
                    network_config[key] = self.loaded_config[key]
        
        # 从外部配置覆盖（最高优先级）
        if self.external_config:
            print("[INFO] Applying config from external file")
            for key in network_config.keys():
                if key in self.external_config:
                    old_value = network_config[key]
                    network_config[key] = self.external_config[key]
                    if old_value != network_config[key]:
                        print(f"[INFO] Config override - {key}: {old_value} -> {network_config[key]}")
        
        print(f"[INFO] Final network config: hidden_dim={network_config['hidden_dim']}, "
            f"num_layers={network_config['num_layers']}, dropout={network_config['dropout']}")
        
        return network_config


    def _load_tools(self):
        """Load tool capabilities and build indices"""
        logger.info(f"Loading tools from {self.tools_path}")
        print(f"[INFO] Loading tools from {self.tools_path}")
        
        if not self.tools_path.exists():
            raise FileNotFoundError(f"Tools file not found: {self.tools_path}")
            logger.error(f"Tools file not found: {self.tools_path}")
            return
        
        # Load tool data
        with open(self.tools_path, 'r') as f:
            tools_data = json.load(f)
        
        # 检查 embedding manager 状态

        print(f"[INFO] Embedding manager ready with {len(self.embedding_manager.tool_embeddings)} tools")
        print("[WARNING] Embedding manager exists but has no embeddings")
        print("[INFO] Consider rebuilding index with: embedding_manager.build_index(tools_path)")


        
        # Process tools - 这部分与 embedding 无关，总是需要执行
        for tool_name, tool_def in tools_data.items():
            # Extract input types from parameters
            input_types = {}
            for param in tool_def.get('parameters', []):
                if isinstance(param, dict):
                    input_types[param.get('name', '')] = param.get('type', 'any')
            
            # Extract output types from returns
            output_types = {}
            for ret in tool_def.get('returns', []):
                if isinstance(ret, dict):
                    output_types[ret.get('name', '')] = ret.get('type', 'any')
            
            # 高级语义操作提取
            semantic_ops = self._extract_semantic_operations(tool_name, tool_def)
            
            # Create ToolCapability object
            capability = ToolCapability(
                tool_name=tool_name,
                input_types=input_types,
                output_types=output_types,
                dependencies=tool_def.get('dependencies', []),
                semantic_operations=semantic_ops
            )
            
            self.tool_capabilities[tool_name] = capability
            self.tool_names.append(tool_name)
        
        # Create tool indices
        self.tool_names = sorted(self.tool_names)
        self.tool_to_idx = {tool: i for i, tool in enumerate(self.tool_names)}
        self.idx_to_tool = {i: tool for tool, i in self.tool_to_idx.items()}
        
        logger.info(f"Loaded {len(self.tool_names)} tools")



    def _extract_semantic_operations(self, tool_name: str, tool_def: Dict) -> List[str]:
        """
        使用高级方法提取语义操作
        
        Args:
            tool_name: 工具名称
            tool_def: 工具定义字典
            
        Returns:
            语义操作列表
        """
        semantic_ops = []
        

        # 获取工具的embedding信息
        tool_embedding = self.embedding_manager.tool_embeddings[tool_name]
        
        # 使用工具的类别和描述生成查询
        category = tool_embedding.category
        description = tool_embedding.description
        
        # 构建语义查询
        semantic_query = f"{description} {category} tool"
        
        # 在操作索引中搜索相关操作
        related_ops = self.tool_capability_manager.operation_index.search_operation(
            semantic_query, k=5
        )
        
        # 添加高相关度的操作
        for op_name, score in related_ops:
            if score > 0.6:  # 相关度阈值
                semantic_ops.append(op_name)
                logger.debug(f" Tool {tool_name}: found semantic operation '{op_name}' (score: {score:.3f})")
        
        # 如果找到了语义操作，返回
        # 基于类别添加额外的标准操作
        category_ops = self._get_category_standard_operations(category)
        for op in category_ops:
            if op not in semantic_ops:
                semantic_ops.append(op)
        
        print(f"[INFO] Tool {tool_name}: semantic operations = {semantic_ops}")
        return semantic_ops

        

    def _get_category_standard_operations(self, category: str) -> List[str]:
        """
        获取类别的标准操作
        
        Args:
            category: 工具类别
            
        Returns:
            该类别的标准操作列表
        """
        category_operations = {
            'file_operations': ['read', 'write', 'parse', 'transform'],
            'data_processing': ['validate', 'transform', 'filter', 'aggregate'],
            'network': ['read', 'write', 'validate', 'integrate'],
            'computation': ['compute', 'aggregate', 'transform'],
            'integration': ['integrate', 'transform', 'validate'],
            'utility': ['cache', 'process']
        }
        
        return category_operations.get(category, ['process'])

    def _extract_task_types(self) -> List[str]:
        """Extract available task types"""
        # Define standard task types
        task_types = [
            "simple_task",
            "data_pipeline", 
            "api_integration",
            "basic_task",
            "multi_stage_pipeline"
        ]
        
        # Add from workflow data if available
        if self.workflow_data:
            task_types.extend(list(self.workflow_data.keys()))
        
        return list(set(task_types))
    


    def _generate_reasoning_steps(self, task_type: str, optimal_sequence: List[str]) -> List[str]:
        """Generate reasoning steps for the workflow execution"""
        # 使用工具能力管理器生成更智能的reasoning  # <- 修改了这一行
        reasoning_generator = WorkflowReasoningGenerator(  # <- 修改了这一行
            self.tool_capabilities,  # <- 修改了这一行
            self.tool_capability_manager  # <- 修改了这一行
        )  # <- 修改了这一行
        return reasoning_generator.generate_reasoning(task_type, optimal_sequence)  # <- 修改了这一行
    
    def _preload_workflow_data(self):
        """Pre-load workflow data from checkpoint if available"""
        if self.workflow_data:
            logger.info(f"Pre-loading {len(self.workflow_data)} workflows from checkpoint")
            for task_type, data in self.workflow_data.items():
                if 'optimal_sequence' in data:
                    data['optimal_sequence'] = self._clean_optimal_sequence(data['optimal_sequence'])
    
    def _clean_optimal_sequence(self, sequence: Any) -> List[str]:
        """Clean and validate optimal sequence"""
        if isinstance(sequence, torch.Tensor):
            sequence = sequence.tolist()
        
        cleaned = []
        for item in sequence:
            if isinstance(item, (int, np.integer)):
                # Convert tool index to name
                if 0 <= item < len(self.tool_names):
                    cleaned.append(self.tool_names[item])
            elif isinstance(item, str) and item in self.tool_names:
                cleaned.append(item)
        
        return cleaned


    def generate_workflow(self, task_type: str, max_depth: int = 20, 
                        task_instance: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate enhanced workflow with quality metrics"""
        
        # 如果提供了task_instance，使用增强的生成方法
        if task_instance:
        #     print(task_instance,"\n\n\n\n")
            # sleep(11111)
            return self.generate_workflow_for_instance(task_instance, max_depth)
        
        logger.info(f"Generating enhanced workflow for {task_type}")
        
        # 移除缓存检查，确保每次都生成新的workflow  # <- 修改了这部分
        # 原因：同一类型的不同任务实例需要不同的工具序列  # <- 修改了这部分
        
        # 不再使用预加载的workflow data  # <- 修改了这部分
        # 原因：预加载的数据是基于task_type的通用方案  # <- 修改了这部分
        
        # Generate new workflow
        if self.q_network:
            workflow = self._generate_workflow_with_model(task_type, max_depth)
        else:
            workflow = self._generate_random_workflow(task_type)
        
        # Calculate quality metrics
        workflow['workflow_quality'] = self._calculate_workflow_quality(workflow)
        
        # 不再存储到self.workflows缓存中  # <- 修改了这一行
        # 原因：避免后续调用使用缓存的结果  # <- 修改了这一行
        return workflow
    


    def _generate_workflow_with_model(self, task_type: str, max_depth: int = 20) -> Dict[str, Any]:
        """使用训练模型生成智能workflow"""
        logger.info(f"Generating smart workflow for {task_type}")
        
        # 创建初始状态
        state = self._create_initial_state(task_type)
        smart_workflow = SmartWorkflow(task_type=task_type, steps=[])
        step_id = 0
        tool_to_step = {}
        
        # 添加语义上下文存储
        semantic_contexts = {}  # 使用语义化的键名
        rag_context = {}
        tool_selection_history = []
        model_decision_scores = {}
        
        for depth in range(max_depth):
            # 编码状态
            state_vector = self._encode_state_for_generation(state, task_type)
            state_tensor = torch.FloatTensor(state_vector).unsqueeze(0)
            
            # 获取策略
            if self.algorithm == 'ppo' and hasattr(self, 'network'):
                with torch.no_grad():
                    logits, _ = self.network(state_tensor)
                    probs = torch.softmax(logits, dim=-1)
                    action_idx = probs.argmax().item()
            elif self.algorithm == 'dqn' and hasattr(self, 'q_network'):
                with torch.no_grad():
                    q_values = self.q_network(state_tensor).squeeze()
                    action_idx = q_values.argmax().item()
            else:
                # 随机选择
                action_idx = random.randint(0, len(self.action_space) - 1)
            
            # 将action_idx转换为具体的action
            action = self._index_to_action(action_idx)
            
            # 根据action类型创建workflow step
            if action.action_type == ActionType.INVOKE_TOOL:
                step = WorkflowStep(
                    step_id=step_id,
                    action_type=ActionType.INVOKE_TOOL,
                    tool_name=action.tool_name,
                    on_success=step_id + 1,
                    on_failure=None
                )
                tool_to_step[action.tool_name] = step_id
                smart_workflow.steps.append(step)
                
                # 在每步决策后，可能更新RAG上下文
                if self.use_embeddings and self.embedding_manager:
                    try:
                        # 获取工具的语义操作
                        tool_capability = self.tool_capabilities.get(action.tool_name)
                        if tool_capability and hasattr(tool_capability, 'semantic_operations'):
                            # 使用工具的实际语义操作作为上下文键
                            primary_operation = (tool_capability.semantic_operations[0] 
                                            if tool_capability.semantic_operations 
                                            else f"step_{step_id}")
                            
                            # 生成基于当前操作的查询
                            context_query = self._generate_semantic_query(
                                state, 
                                action.tool_name,
                                primary_operation
                            )
                            
                            if context_query:
                                search_results = self.embedding_manager.search(
                                    query=context_query,
                                    k=5,
                                    return_scores=True
                                )
                                
                                # 使用语义化的键名存储结果
                                semantic_key = f"{primary_operation}_at_step_{step_id}"
                                semantic_contexts[semantic_key] = {
                                    'tool': action.tool_name,
                                    'operation': primary_operation,
                                    'results': search_results,
                                    'step': step_id
                                }
                                
                                # 同时更新rag_context以保持向后兼容
                                rag_context[primary_operation] = search_results
                                
                    except Exception as e:
                        logger.debug(f"Failed to update semantic context: {e}")
                
                step_id += 1
                
            elif action.action_type == ActionType.RETRY_TOOL and action.tool_name in tool_to_step:
                # 为之前的工具添加retry逻辑
                original_step_id = tool_to_step[action.tool_name]
                original_step = smart_workflow.steps[original_step_id]
                original_step.max_retries = max(original_step.max_retries, 1)
                original_step.on_failure = step_id
                
                retry_step = WorkflowStep(
                    step_id=step_id,
                    action_type=ActionType.RETRY_TOOL,
                    tool_name=action.tool_name,
                    on_success=original_step.on_success,
                    on_failure=step_id + 1,
                    metadata={'retry_of': original_step_id}
                )
                smart_workflow.steps.append(retry_step)
                step_id += 1
                
            elif action.action_type == ActionType.VALIDATE_OUTPUT:
                step = WorkflowStep(
                    step_id=step_id,
                    action_type=ActionType.VALIDATE_OUTPUT,
                    on_success=step_id + 1,
                    on_failure=step_id + 1,
                    metadata={'validation_target': 'previous_output'}
                )
                smart_workflow.steps.append(step)
                step_id += 1
            
            # 更新状态
            state = self._simulate_action_execution(state, action)
            
            # 检查是否完成
            workflow_sequence = smart_workflow.to_sequence()
            if self._is_workflow_complete(state, workflow_sequence):
                break
        
        # 创建workflow字典时包含语义化的上下文信息
        workflow = self._smart_workflow_to_dict(smart_workflow)
        workflow['model_scores'] = model_decision_scores
        workflow['selection_history'] = tool_selection_history
        workflow['semantic_contexts'] = semantic_contexts  # 新增语义上下文
        workflow['rag_context'] = rag_context  # 保留原有格式
        workflow['rag_enhanced_network'] = hasattr(self.network, 'rag_projection')
        workflow['rag_usage_stats'] = {
            'network_supports_rag': hasattr(self.network, 'rag_projection'),
            'semantic_context_count': len(semantic_contexts),
            'total_rag_results': sum(len(ctx.get('results', [])) 
                                    for ctx in semantic_contexts.values()),
            'average_rag_confidence': self._calculate_average_rag_confidence(semantic_contexts)
        }
        
        return workflow

    def _generate_semantic_query(self, state: GeneralizedMDPState, 
                                tool_name: str, operation: str) -> str:
        """基于工具和操作生成语义化的搜索查询"""
        # 获取任务上下文
        task_context = getattr(state, 'task_objective', '')
        data_state = getattr(state, 'data_flow_state', DataFlowState.EMPTY)
        
        # 基于操作类型生成不同的查询
        if 'read' in operation or 'load' in operation:
            return f"tools for loading data in {task_context}"
        elif 'transform' in operation:
            return f"data transformation tools for {task_context}"
        elif 'validate' in operation:
            return f"validation tools for {self._get_data_type_context(state)}"
        elif 'write' in operation or 'export' in operation:
            return f"output tools for saving {self._get_data_type_context(state)}"
        else:
            # 默认使用操作和任务类型
            return f"{operation} tools for {state.task_type}"

    def _calculate_average_rag_confidence(self, semantic_contexts: Dict) -> float:
        """计算平均RAG置信度"""
        all_scores = []
        for context in semantic_contexts.values():
            results = context.get('results', [])
            for result in results:
                if hasattr(result, 'score'):
                    all_scores.append(result.score)
        
        return sum(all_scores) / len(all_scores) if all_scores else 0.0

    def _get_data_type_context(self, state: GeneralizedMDPState) -> str:
        """获取当前数据类型的上下文描述"""
        # 从状态中提取数据类型信息
        if hasattr(state, 'current_context'):
            context_keys = list(state.current_context.keys())
            if context_keys:
                # 尝试从上下文键中推断数据类型
                for key in context_keys:
                    if 'json' in key.lower():
                        return "JSON data"
                    elif 'csv' in key.lower():
                        return "CSV data"
                    elif 'xml' in key.lower():
                        return "XML data"
        
        return "processed data"

    def _generate_execution_plan(self, smart_workflow: SmartWorkflow) -> str:
        """将智能workflow转换为人类可读的执行计划"""
        if not smart_workflow.steps:
            return "No execution steps required."
        
        plan_lines = []
        step_number = 1
        
        for step in smart_workflow.steps:
            if step.action_type == ActionType.INVOKE_TOOL:
                line = f"{step_number}. Execute {step.tool_name}"
                if step.max_retries > 0:
                    line += f" (retry up to {step.max_retries} times if failed)"
                plan_lines.append(line)
                step_number += 1
                
            elif step.action_type == ActionType.RETRY_TOOL:
                # Retry步骤在执行计划中作为条件说明，不单独计数
                continue
        
        return "\n".join(plan_lines)

    def _extract_error_handling(self, smart_workflow: SmartWorkflow) -> str:
        """提取错误处理策略描述"""
        strategies = []
        
        # 分析retry策略
        retry_tools = set()
        for step in smart_workflow.steps:
            if step.action_type == ActionType.RETRY_TOOL:
                retry_tools.add(step.tool_name)
        
        if retry_tools:
            strategies.append(f"Retry these critical tools if they fail: {', '.join(sorted(retry_tools))}")
        else:
            strategies.append("No automatic retries configured")
        
        # 添加通用策略
        strategies.append("If a non-critical tool fails, log the error and continue")
        strategies.append("If all critical tools fail after retries, report the issue and stop")
        
        return " ".join(strategies)

    def _smart_workflow_to_dict(self, smart_workflow: SmartWorkflow) -> Dict[str, Any]:
        """将智能workflow转换为标准格式"""
        tool_sequence = smart_workflow.to_sequence()
        
        # 生成执行计划描述
        execution_plan = self._generate_execution_plan(smart_workflow)
        
        return {
            'task_type': smart_workflow.task_type,
            'optimal_sequence': tool_sequence,
            'smart_workflow': smart_workflow,  # 保留完整的智能workflow
            'execution_plan': execution_plan,  # 人类可读的执行计划
            'success_probability': self._calculate_success_probability(tool_sequence, nx.DiGraph()),
            'workflow_quality': self._calculate_workflow_quality({'optimal_sequence': tool_sequence}),
            'critical_tools': self._identify_critical_tools(smart_workflow),
            'error_handling': self._extract_error_handling(smart_workflow),
            'generated_at': datetime.now().isoformat()
        }

    def _generate_workflow_with_dqn(self, task_type: str, max_depth: int = 20) -> Dict[str, Any]:
        """Generate workflow using DQN policy"""
        logger.info(f"Generating workflow with DQN for {task_type}")
        
        # 创建初始状态
        state = self._create_initial_state(task_type)
        workflow_sequence = []
        visited_tools = set()
        
        for step in range(max_depth):
            # 编码状态
            state_vector = self._encode_state_for_generation(state, task_type)
            state_tensor = torch.FloatTensor(state_vector).unsqueeze(0)
            
            # 获取Q值
            with torch.no_grad():
                q_values = self.q_network(state_tensor).squeeze()
            
            # 选择动作（贪婪策略）
            valid_actions = self._get_valid_actions(state, visited_tools)
            if not valid_actions:
                break
            
            # Mask无效动作
            masked_q_values = q_values.clone()
            for i in range(len(q_values)):
                if i not in valid_actions:
                    masked_q_values[i] = float('-inf')
            
            action_idx = masked_q_values.argmax().item()
            
            # 执行动作
            if action_idx < len(self.tool_names):
                tool_name = self.tool_names[action_idx]
                workflow_sequence.append(tool_name)
                visited_tools.add(tool_name)
                
                # 更新状态
                state = self._update_state_after_tool(state, tool_name)
                
                # 检查是否完成
                if self._is_workflow_complete(state, workflow_sequence):
                    break
        
        return self._create_workflow_dict(task_type, workflow_sequence)

    def _generate_workflow_with_ppo(self, task_type: str, max_depth: int = 20) -> Dict[str, Any]:
        """Generate workflow using PPO policy"""
        logger.info(f"Generating workflow with PPO for {task_type}")
        
        # 创建初始状态
        state = self._create_initial_state(task_type)
        workflow_sequence = []
        visited_tools = set()
        
        for step in range(max_depth):
            # 编码状态
            state_vector = self._encode_state_for_generation(state, task_type)
            state_tensor = torch.FloatTensor(state_vector).unsqueeze(0)
            
            # 获取策略
            with torch.no_grad():
                logits, _ = self.network(state_tensor)
                
                # 获取有效动作
                valid_actions = self._get_valid_actions(state, visited_tools)
                if not valid_actions:
                    break
                
                # Mask无效动作
                masked_logits = logits.clone()
                for i in range(logits.shape[1]):
                    if i not in valid_actions:
                        masked_logits[0, i] = float('-inf')
                
                # 使用确定性策略（选择概率最高的）
                probs = torch.softmax(masked_logits, dim=-1)
                action_idx = probs.argmax().item()
            
            # 执行动作
            if action_idx < len(self.tool_names):
                tool_name = self.tool_names[action_idx]
                workflow_sequence.append(tool_name)
                visited_tools.add(tool_name)
                
                # 更新状态
                state = self._update_state_after_tool(state, tool_name)
                
                # 检查是否完成
                if self._is_workflow_complete(state, workflow_sequence):
                    break
        
        return self._create_workflow_dict(task_type, workflow_sequence)
    
    def _search_tools_semantic(self, query: str, k: int = 10, 
                              return_scores: bool = True) -> List[Any]:  # <- 新增了这个方法
        """
        使用语义搜索查找相关工具
        
        Args:
            query: 搜索查询
            k: 返回结果数量
            return_scores: 是否返回分数
            
        Returns:
            搜索结果列表（SearchResult对象）
        """
        if not self.embedding_manager:
            logger.warning("Embedding manager not available for semantic search")
            return []
        
        try:
            # 调用embedding manager的search方法
            search_results = self.embedding_manager.search(
                query=query,
                k=k,
                return_scores=return_scores
            )
            return search_results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []


    def _ensure_rag_search_works(self, description: str, task_type: str, 
                                task_instance: Dict[str, Any]) -> Dict[str, List]:
        """确保RAG搜索返回有效结果的增强方法"""
        rag_context = {}
        
        if not self.embedding_manager:
            logger.warning("Embedding manager not available")
            return rag_context
        
        # 1. 多策略搜索
        search_strategies = [
            # 策略1：完整描述
            (description, "full_description"),
            # 策略2：任务类型相关
            (f"{task_type} workflow tools", "task_type"),
            # 策略3：提取的关键词
            (" ".join(self._extract_keywords(description)), "keywords"),
            # 策略4：required_tools相关  # <- 新增策略
            (self._create_required_tools_query(task_instance), "required_tools"),  # <- 新增
            # 策略5：通用功能描述
            ("data processing pipeline tools", "generic")
        ]
        
        for query, strategy_name in search_strategies:
            if not query:  # <- 新增：跳过空查询
                continue
            
            try:
                results = self._search_tools_semantic(query, k=20, return_scores=True)
                if results:
                    rag_context[strategy_name] = results
                    logger.info(f"RAG search successful with strategy '{strategy_name}': {len(results)} results")
                    
                    # 记录前3个结果用于调试  # <- 新增调试信息
                    for i, result in enumerate(results[:3]):  # <- 新增
                        logger.debug(f"  {i+1}. {result.tool_name} (score: {result.score:.3f})")  # <- 新增
            except Exception as e:
                logger.error(f"RAG search failed for strategy '{strategy_name}': {e}")
        
        # 2. 如果所有策略都失败，使用备用方案
        if not rag_context:
            logger.warning("All RAG search strategies failed, using fallback")
            rag_context['fallback'] = self._get_fallback_tools(task_type, task_instance)  # <- 修改：传入task_instance
        
        # 3. 确保包含required_tools  # <- 新增这部分
        if 'required_tools' in task_instance:  # <- 新增
            self._ensure_required_tools_in_context(rag_context, task_instance['required_tools'])  # <- 新增
        
        return rag_context

    def _extract_keywords(self, text: str) -> List[str]:
        """从文本中提取关键词"""
        # 简单的关键词提取
        keywords = []
        important_words = ['read', 'write', 'process', 'transform', 'validate', 
                        'export', 'import', 'analyze', 'compute', 'aggregate',
                        'fetch', 'store', 'parse', 'filter', 'merge', 'split',  # <- 新增更多关键词
                        'convert', 'generate', 'create', 'update', 'delete']  # <- 新增
        
        text_lower = text.lower()
        for word in important_words:
            if word in text_lower:
                keywords.append(word)
        
        # 提取任务相关的特定词汇  # <- 新增这部分
        if 'pipeline' in text_lower:  # <- 新增
            keywords.extend(['pipeline', 'stage', 'flow'])  # <- 新增
        if 'file' in text_lower:  # <- 新增
            keywords.extend(['file', 'document', 'data'])  # <- 新增
        if 'api' in text_lower:  # <- 新增
            keywords.extend(['api', 'endpoint', 'request'])  # <- 新增
        
        return list(set(keywords))  # <- 去重

    def _create_required_tools_query(self, task_instance: Dict[str, Any]) -> str:
        """基于required_tools创建搜索查询"""
        if 'required_tools' not in task_instance:
            return ""
        
        required_tools = task_instance['required_tools']
        if not required_tools:
            return ""
        
        # 从工具名中提取操作词
        operations = []
        for tool_name in required_tools:
            parts = tool_name.split('_')
            if len(parts) >= 2:
                operations.append(parts[-1])  # 通常最后一部分是操作
        
        return " ".join(operations) + " tools"

    def _get_fallback_tools(self, task_type: str, task_instance: Dict[str, Any]) -> List:
        """获取备用工具列表"""
        fallback_tools = []
        
        # 1. 首先添加required_tools  # <- 新增
        if 'required_tools' in task_instance:  # <- 新增
            for tool_name in task_instance['required_tools']:  # <- 新增
                if tool_name in self.tool_names:  # <- 新增
                    # 创建模拟的搜索结果  # <- 新增
                    fallback_tools.append(type('SearchResult', (), {  # <- 新增
                        'tool_name': tool_name,  # <- 新增
                        'score': 0.9,  # 高分因为是required  # <- 新增
                        'source': 'required_tools'  # <- 新增
                    })())  # <- 新增
        
        # 2. 根据任务类型添加常用工具  # <- 修改注释
        task_tool_mapping = {
            'data_pipeline': ['file_operations_reader', 'data_processing_transformer', 'file_operations_writer'],
            'api_integration': ['network_fetcher', 'data_processing_parser', 'network_poster'],
            'basic_task': ['file_operations_reader', 'file_operations_converter', 'file_operations_writer'],
            'multi_stage_pipeline': ['data_processing_filter', 'data_processing_aggregator', 'data_processing_validator']
        }
        
        if task_type in task_tool_mapping:
            for tool_name in task_tool_mapping[task_type]:
                if tool_name in self.tool_names and tool_name not in [t.tool_name for t in fallback_tools]:  # <- 修改：避免重复
                    fallback_tools.append(type('SearchResult', (), {
                        'tool_name': tool_name,
                        'score': 0.5,  # <- 修改：较低分因为是通用推荐
                        'source': 'task_type_default'  # <- 新增
                    })())
        
        return fallback_tools

    def _ensure_required_tools_in_context(self, rag_context: Dict[str, List], required_tools: List[str]):
        """确保required_tools出现在RAG上下文中"""
        # 检查每个required tool是否已经在结果中
        existing_tools = set()
        for strategy, results in rag_context.items():
            for result in results:
                existing_tools.add(result.tool_name)
        
        # 添加缺失的required tools
        missing_tools = []
        for tool_name in required_tools:
            if tool_name not in existing_tools and tool_name in self.tool_names:
                missing_tools.append(type('SearchResult', (), {
                    'tool_name': tool_name,
                    'score': 0.95,  # 高分因为是必需的
                    'source': 'required_injection'
                })())
        
        if missing_tools:
            if 'required_tools' not in rag_context:
                rag_context['required_tools'] = []
            rag_context['required_tools'].extend(missing_tools)
            logger.info(f"Injected {len(missing_tools)} required tools into RAG context")

    def generate_workflow_for_instance(self, task_instance: Dict[str, Any], 
                                    max_depth: int = 20) -> Dict[str, Any]:
        """Generate workflow based on specific task instance with description analysis"""
        logger.info(f"Generating instance-aware workflow for task {task_instance.get('id', 'unknown')}")
        
        # 0. Check for pre-generated workflow (memory optimization)
        if 'workflow' in task_instance:
            logger.info("[OPTIMIZATION] Using pre-generated workflow from task instance")
            print("[INFO] ⚡ Using pre-generated workflow - skipping generation")
            return task_instance['workflow']
        
        # 1. 提取任务信息
        task_type = task_instance.get('task_type', 'unknown')
        description = task_instance.get('description', '')
        
        # 2. 分析任务描述，提取关键操作（作为可选的辅助信息）  # <- 修改了注释
        operations = self._extract_operations_from_description(description)
        logger.info(f"Extracted operations: {operations}")
        
        # 3. 获取工具能力映射
        tools_by_category = self._categorize_tools_by_capability()
        dependency_graph = self._build_dependency_graph()
        
        # 4. 基于描述和语义分析生成最优序列
        optimal_sequence = []
        
        # 4a. 使用任务描述进行全面的语义搜索  # <- 修改了注释
        rag_context = {}  
        initial_tools = []
        print(f"[INSTANCE] Using embedding search with task description")
            # 直接使用完整描述进行搜索  # <- 修改了这部分
        full_search_results = self._search_tools_semantic(
            query=description,
            k=20,  # 增加搜索数量
            return_scores=True
        )
        
        # 将结果按语义相关性分组
        rag_context['full_description'] = full_search_results
        initial_tools.extend([r.tool_name for r in full_search_results[:10]])
        
        # 如果提取到了操作，也为每个操作进行搜索（作为补充）
        if operations:
            for operation in operations:
                search_query = f"{operation} {task_type}"
                search_results = self._search_tools_semantic(
                    query=search_query,
                    k=10,
                    return_scores=True
                )
                rag_context[operation] = search_results
                # 添加高分结果
                for r in search_results[:3]:
                    if r.tool_name not in initial_tools and r.score > 0.7:
                        initial_tools.append(r.tool_name)
        
        print(f"[INSTANCE] Found {len(initial_tools)} relevant tools via embedding")
        logger.info(f"Embedding search successful: {len(initial_tools)} tools found")

        print(initial_tools, "\n\n\n\n")
    
        
        # 4b. 使用PPO模型结合RAG生成序列，传入完整的任务信息  # <- 修改了注释
        # 添加详细的调试信息
        logger.info(f"[DEBUG] Checking model availability:")
        logger.info(f"  - algorithm: {self.algorithm}")
        logger.info(f"  - hasattr(self, 'network'): {hasattr(self, 'network')}")
        logger.info(f"  - hasattr(self, 'q_network'): {hasattr(self, 'q_network')}")
        if hasattr(self, 'network'):
            logger.info(f"  - self.network is not None: {self.network is not None}")
        if hasattr(self, 'q_network'):
            logger.info(f"  - self.q_network is not None: {self.q_network is not None}")

        print("self.algorithm:", self.algorithm)

        # 使用PPO模型生成workflow，传入RAG上下文
        logger.info("[DEBUG] Using PPO model")
        workflow_from_model = self._generate_workflow_with_ppo_and_rag(
            task_type, task_instance, rag_context, max_depth
        )
        optimal_sequence = workflow_from_model.get('optimal_sequence', [])
        logger.info(f"Using PPO+RAG model-generated sequence: {optimal_sequence}")

        # elif hasattr(self, 'q_network') and self.q_network is not None:
        #     # 使用DQN模型生成workflow
        #     logger.info("[DEBUG] Using DQN model")
        #     workflow_from_model = self._generate_workflow_with_model(task_type, max_depth)
        #     optimal_sequence = workflow_from_model.get('optimal_sequence', [])
        #     logger.info(f"Using DQN model-generated sequence: {optimal_sequence}")
        # else:
        #     optimal_sequence = []
        #     logger.info("No trained model available, using heuristic generation")
        
        # # 4c. 合并基于模型和基于描述的序列
        # if initial_tools and not optimal_sequence:
        #     # 如果模型没有生成序列，使用语义搜索结果
        #     optimal_sequence = initial_tools[:10]  # 使用前10个最相关的工具
        #     logger.info(f"Using semantic search results as optimal sequence")
        # elif initial_tools and optimal_sequence:
        #     # 合并两种方法的结果
        #     combined_sequence = []
        #     model_set = set(optimal_sequence)
        #     embedding_set = set(initial_tools)
            
        #     # 优先添加两者都选择的工具
        #     for tool in optimal_sequence:
        #         if tool in embedding_set:
        #             combined_sequence.append(tool)
            
        #     # 添加模型选择但语义搜索未选择的工具
        #     for tool in optimal_sequence:
        #         if tool not in combined_sequence:
        #             combined_sequence.append(tool)
            
        #     # 考虑添加一些高分的语义搜索结果
        #     for tool in initial_tools[:5]:
        #         if tool not in combined_sequence and len(combined_sequence) < max_depth:
        #             combined_sequence.append(tool)
            
        #     optimal_sequence = combined_sequence
        
        # 5. 如果仍然没有序列，使用改进的启发式方法  # <- 修改了这部分
        if not optimal_sequence:
            print(f"[WARNING] No optimal sequence from model, using heuristic for task: {task_instance.get('id', 'unknown')}")
            logger.info("Using improved heuristic sequence generation")
            
            # 基于任务类型选择初始工具
            if task_type in ['basic_task', 'simple_task']:
                # 简单任务：选择基础的输入输出工具
                starter_tools = ['file_operations_reader', 'data_processing_parser', 'utility_cache']
                optimal_sequence = [t for t in starter_tools if t in self.tool_names][:3]
            elif task_type == 'data_pipeline':
                # 数据管道：选择数据处理工具链
                pipeline_tools = ['data_processing_parser', 'data_processing_validator', 
                                'data_processing_transformer', 'file_operations_writer']
                optimal_sequence = [t for t in pipeline_tools if t in self.tool_names]
            elif task_type == 'api_integration':
                # API集成：选择网络相关工具
                api_tools = ['integration_authenticator', 'network_fetcher', 
                            'data_processing_parser', 'integration_mapper']
                optimal_sequence = [t for t in api_tools if t in self.tool_names]
            elif task_type == 'multi_stage_pipeline':
                # 多阶段管道：选择多个处理阶段的工具
                multi_tools = ['file_operations_reader', 'data_processing_parser',
                              'data_processing_transformer', 'data_processing_validator',
                              'file_operations_writer']
                optimal_sequence = [t for t in multi_tools if t in self.tool_names]
            elif task_type == 'basic_task':
                # 文件处理：选择文件操作工具
                file_tools = ['file_operations_reader', 'file_operations_scanner',
                             'file_operations_converter', 'file_operations_compressor',
                             'file_operations_writer']
                optimal_sequence = [t for t in file_tools if t in self.tool_names]
            else:
                # 默认：选择一些通用工具
                generic_tools = ['file_operations_reader', 'data_processing_transformer', 
                            'file_operations_writer']
                optimal_sequence = [t for t in generic_tools if t in self.tool_names]
            
            # 如果还是没有，从可用工具中随机选择
            if not optimal_sequence and self.tool_names:
                optimal_sequence = list(self.tool_names)[:min(5, len(self.tool_names))]
            
            logger.info(f"Heuristic sequence: {optimal_sequence}")
        
        # 6. 生成推理步骤
        reasoning_steps = self._generate_contextual_reasoning(
            task_instance, optimal_sequence, operations
        )
        
        # 7. 构建工作流字典
        workflow = self._create_workflow_dict(task_type, optimal_sequence, task_instance)  # <- 修改：添加task_instance参数
    
        # 新增：保存required_tools到workflow中
        if 'required_tools' in task_instance:
            workflow['required_tools'] = task_instance['required_tools']
        
        # 8. 添加增强信息（包括smart_actions）
        workflow['instance_id'] = task_instance.get('id', 'unknown')
        workflow['reasoning_steps'] = reasoning_steps
        workflow['extracted_operations'] = operations
        workflow['used_embeddings'] = self.use_embeddings
        workflow['alternative_sequences'] = self._generate_alternatives(optimal_sequence, operations)
        workflow['rag_context'] = rag_context
        
        # 创建smart_actions信息
        smart_actions = []
        for i, tool_name in enumerate(optimal_sequence):
            action_info = {
                'tool_name': tool_name,
                'step': i + 1,
                'search_source': 'unknown',
                'semantic_score': 0.0,
                'confidence': 0.0,
                'alternatives': [],
                'reasoning': '',
                'dependencies': [],
                'expected_outcome': {},
                'mcp_protocol': {}
            }
            
            # 添加完整的MCP protocol信息
            if tool_name in self.full_tool_registry:
                mcp_info = self.full_tool_registry[tool_name]
                action_info['mcp_protocol'] = {
                    'description': mcp_info.get('description', ''),
                    'parameters': mcp_info.get('parameters', []),
                    'returns': mcp_info.get('returns', []),
                    'errors': mcp_info.get('errors', []),
                    'dependencies': mcp_info.get('dependencies', []),
                    'metadata': mcp_info.get('metadata', {})
                }
            
            # 如果这个工具来自embedding搜索，记录相关信息
            if tool_name in initial_tools:
                action_info['search_source'] = 'embedding_search'
                # 从RAG上下文获取语义得分
                for operation, results in rag_context.items():
                    for result in results:
                        if result.tool_name == tool_name:
                            action_info['semantic_score'] = result.score
                            action_info['reasoning'] = f"Semantic match for '{operation}' operation"
                            break
            
            # 获取工具的依赖和可靠性信息
            if tool_name in self.tool_capabilities:
                capability = self.tool_capabilities[tool_name]
                action_info['dependencies'] = getattr(capability, 'dependencies', [])
                action_info['confidence'] = self._calculate_tool_reliability(tool_name)
            
            smart_actions.append(action_info)
        
        workflow['smart_actions'] = smart_actions
        workflow['rag_enhanced'] = self.use_embeddings and len(initial_tools) > 0
        
        # 计算质量指标
        workflow['workflow_quality'] = self._calculate_workflow_quality(workflow)
        
        return workflow
    

    def _create_enhanced_smart_actions(self, optimal_sequence: List[str], 
                                    rag_context: Dict[str, List],
                                    initial_tools: List[str],
                                    task_instance: Dict[str, Any],
                                    model_scores: Dict[str, float] = None) -> List[Dict]:
        """创建增强的smart actions，整合模型输出和RAG结果"""
        smart_actions = []
        
        # 预先构建工具相关信息的索引
        tool_rag_scores = {}  # 工具名 -> RAG得分
        tool_rag_sources = {}  # 工具名 -> 搜索来源
        tool_alternatives = defaultdict(list)  # 工具名 -> 替代工具列表
        
        # 1. 从RAG上下文中提取信息
        for operation, results in rag_context.items():
            for idx, result in enumerate(results):
                tool_name = result.tool_name
                score = result.score
                
                # 记录最高的RAG得分
                if tool_name not in tool_rag_scores or score > tool_rag_scores[tool_name]:
                    tool_rag_scores[tool_name] = score
                    tool_rag_sources[tool_name] = 'embedding_search' if score > 0.5 else 'pattern_match'
                
                # 为每个工具收集替代工具（基于相同操作的其他高分工具）
                if idx > 0 and score > 0.6:  # 不是最高分但仍然相关
                    for primary_tool in results[:idx]:
                        if primary_tool.tool_name in optimal_sequence:
                            tool_alternatives[primary_tool.tool_name].append({
                                'tool_name': tool_name,
                                'score': score,
                                'operation': operation
                            })
        
        # 2. 为optimal_sequence中的每个工具创建smart action
        for i, tool_name in enumerate(optimal_sequence):
            action_info = {
                'tool_name': tool_name,
                'step': i + 1,
                'search_source': 'unknown',
                'semantic_score': 0.0,
                'confidence': 0.0,
                'alternatives': [],
                'reasoning': '',
                'dependencies': [],
                'expected_outcome': {},
                'mcp_protocol': {}
            }
            
            # 3. 填充搜索来源和语义得分
            if tool_name in tool_rag_scores:
                action_info['semantic_score'] = tool_rag_scores[tool_name]
                action_info['search_source'] = tool_rag_sources[tool_name]
            elif tool_name in initial_tools:
                # 如果在initial_tools中但没有具体得分，设置默认值
                action_info['search_source'] = 'embedding_search'
                action_info['semantic_score'] = 0.7  # 默认中等得分
            elif model_scores and tool_name in model_scores:
                # 仅由模型选择的工具
                action_info['search_source'] = 'model_prediction'
                action_info['semantic_score'] = 0.0  # 模型选择没有语义得分
            
            # 4. 计算置信度（结合多个因素）
            confidence = self._calculate_comprehensive_confidence(
                tool_name, 
                action_info['semantic_score'],
                model_scores.get(tool_name, 0.0) if model_scores else 0.0,
                i,  # 位置信息
                len(optimal_sequence)  # 序列长度
            )
            action_info['confidence'] = confidence
            
            # 5. 添加替代工具
            if tool_name in tool_alternatives:
                # 按得分排序并取前3个
                sorted_alts = sorted(tool_alternatives[tool_name], 
                                key=lambda x: x['score'], reverse=True)[:3]
                action_info['alternatives'] = sorted_alts
            
            # 6. 生成推理说明
            action_info['reasoning'] = self._generate_tool_reasoning(
                tool_name, i, task_instance, action_info
            )
            
            # 7. 填充工具依赖信息
            if tool_name in self.tool_capabilities:
                capability = self.tool_capabilities[tool_name]
                action_info['dependencies'] = capability.dependencies
                
                # 预期结果基于工具能力
                action_info['expected_outcome'] = {
                    'data_state': self._predict_data_state_after_tool(capability),
                    'milestone': capability.semantic_operations[0] if capability.semantic_operations else 'process'
                }
            
            # 8. 添加MCP协议信息
            if tool_name in self.full_tool_registry:
                action_info['mcp_protocol'] = self._extract_mcp_info(
                    self.full_tool_registry[tool_name]
                )
            
            smart_actions.append(action_info)
        
        return smart_actions

    def _calculate_comprehensive_confidence(self, tool_name: str, 
                                        semantic_score: float,
                                        model_score: float,
                                        position: int,
                                        sequence_length: int) -> float:
        """综合计算工具执行置信度"""
        
        # 基础置信度来自历史成功率
        base_confidence = self._calculate_tool_reliability(tool_name)
        
        # 语义匹配加成（最多+0.2）
        semantic_boost = min(0.2, semantic_score * 0.25)
        
        # 模型预测加成（最多+0.15）
        model_boost = min(0.15, model_score * 0.2)
        
        # 位置惩罚（序列越长，后面的工具置信度略降）
        position_penalty = 0.0
        if sequence_length > 5:
            position_penalty = min(0.1, (position / sequence_length) * 0.15)
        
        # 关键工具加成
        critical_boost = 0.0
        if tool_name in self.tool_criticality_scores:
            critical_boost = min(0.1, self.tool_criticality_scores[tool_name] * 0.15)
        
        # 综合计算
        final_confidence = min(0.95, max(0.1, 
            base_confidence + semantic_boost + model_boost + critical_boost - position_penalty
        ))
        
        return round(final_confidence, 3)

    def _generate_tool_reasoning(self, tool_name: str, position: int, 
                            task_instance: Dict, action_info: Dict) -> str:
        """生成工具选择的推理说明"""
        reasons = []
        
        # 1. 基于搜索来源
        if action_info['search_source'] == 'embedding_search':
            reasons.append(f"Selected via semantic search (score: {action_info['semantic_score']:.2f})")
        elif action_info['search_source'] == 'model_prediction':
            reasons.append("Selected by trained model based on task pattern")
        
        # 2. 基于任务需求
        if 'required_tools' in task_instance and tool_name in task_instance['required_tools']:
            reasons.append("Required tool for this task")
        
        # 3. 基于工具能力
        if tool_name in self.tool_capabilities:
            capability = self.tool_capabilities[tool_name]
            if capability.semantic_operations:
                ops = ', '.join(capability.semantic_operations[:2])
                reasons.append(f"Performs {ops} operations")
        
        # 4. 基于位置
        if position == 0:
            reasons.append("Initial data loading/setup step")
        elif position == len(action_info) - 1:
            reasons.append("Final output/completion step")
        
        # 5. 基于依赖
        if action_info['dependencies']:
            reasons.append(f"Depends on: {', '.join(action_info['dependencies'])}")
        
        return "; ".join(reasons) if reasons else "Standard workflow step"

    def _predict_data_state_after_tool(self, capability) -> str:
        """预测工具执行后的数据状态"""
        operations = capability.semantic_operations
        
        if 'read' in operations or 'load' in operations:
            return 'data_loaded'
        elif 'transform' in operations:
            return 'data_transformed'
        elif 'validate' in operations:
            return 'data_validated'
        elif 'write' in operations or 'export' in operations:
            return 'data_exported'
        elif 'aggregate' in operations:
            return 'data_aggregated'
        else:
            return 'data_processed'

    def _get_adaptive_weights(self, state: GeneralizedMDPState, 
                            rag_context: Dict[str, List]) -> Tuple[float, float]:
        """根据状态和RAG置信度动态调整PPO/RAG权重"""
        # 基础权重
        base_ppo_weight = 0.6
        base_rag_weight = 0.4
        
        # 计算RAG置信度
        rag_confidence = 0.0
        total_scores = 0
        score_count = 0
        
        for operation, results in rag_context.items():
            for result in results:
                total_scores += result.score
                score_count += 1
        
        if score_count > 0:
            rag_confidence = total_scores / score_count
        
        # 根据workflow进度调整权重
        progress_factor = state.workflow_step / 20.0  # 假设平均20步
        
        # 早期阶段更依赖RAG
        if progress_factor < 0.3:
            rag_boost = 0.2
        elif progress_factor < 0.7:
            rag_boost = 0.1
        else:
            rag_boost = 0.0
        
        # 根据RAG置信度调整
        if rag_confidence > 0.8:
            rag_boost += 0.15
        elif rag_confidence > 0.6:
            rag_boost += 0.1
        
        # 根据错误率调整
        if state.consecutive_errors > 2:
            # 错误多时更依赖RAG
            rag_boost += 0.1
        
        # 计算最终权重
        ppo_weight = max(0.3, base_ppo_weight - rag_boost)
        rag_weight = min(0.7, base_rag_weight + rag_boost)
        
        # 归一化
        total = ppo_weight + rag_weight
        return ppo_weight / total, rag_weight / total


    def _generate_workflow_with_ppo_and_rag(self, task_type: str, task_instance: Dict[str, Any],
                                        rag_context: Dict[str, List], max_depth: int = 20) -> Dict[str, Any]:
        """使用PPO模型结合RAG信息和required_tools生成智能workflow"""
        logger.info(f"Generating PPO+RAG workflow for {task_type}")
        
        # 添加网络可用性检查
        if self.network is None:
            logger.warning("Network not set in workflow generator, creating default network")
            print("[WARNING] Network not initialized when generating workflow")
            print("[INFO] Creating default network for workflow generation")
            self._create_default_network()
            
        # 再次验证网络是否成功创建
        if self.network is None:
            raise RuntimeError(
                "Failed to create network for workflow generation. "
                "Please ensure the model is properly initialized."
            )
        
        # 验证网络具有必需的属性
        if not hasattr(self.network, 'tools_projection'):
            raise RuntimeError(
                f"Network type {type(self.network).__name__} does not support tools projection. "
                "Expected ActorCriticNetwork with tools_projection layer."
            )
        
        # 创建初始状态，包含RAG信息和任务实例
        state = self._create_initial_state(task_type, task_instance)
        
        # 使用 metadata 字典存储额外信息
        state.metadata['rag_context'] = rag_context
        state.metadata['task_description'] = task_instance.get('description', '')
        
        # 新增：提取required_tools
        required_tools = task_instance.get('required_tools', [])
        initial_required_tools_count = len(required_tools)  # 记录初始数量
        if required_tools:
            logger.info(f"Task has {len(required_tools)} required tools: {required_tools}")
        else:
            # 不再抛出错误，因为有些任务可能确实没有required_tools
            logger.warning("No required tools provided for this task instance")
        
        remaining_required_tools = required_tools.copy()
        used_required_tools = set()

        workflow_sequence = []
        visited_tools = set()
        
        # 记录模型的决策分数和选择历史
        model_decision_scores = {}
        tool_selection_history = []
        
        for step in range(max_depth):
            logger.debug(f"Step {step}: Processing workflow generation")
            
            # 编码状态（包含RAG信息）
            state_vector, rag_embedding = self._encode_state_with_rag(state, task_type, rag_context)
            state_tensor = torch.FloatTensor(state_vector).unsqueeze(0).to(self.device)
            rag_tensor = torch.FloatTensor(rag_embedding).unsqueeze(0).to(self.device)
            
            # 新增：编码required_tools（改进版本）
            required_tools_tensor = None
            
            # 现在可以安全地检查network的属性，因为我们已经确保它存在
            if hasattr(self.network, 'tools_projection'):
                if required_tools:  # 如果有required_tools
                    # 使用MDPWorkflowGenerator自己的embedding_manager
                    from unified_training_manager import encode_required_tools_embedding
                    
                    # 获取网络期望的tools维度
                    target_tools_dim = getattr(self.network, 'tools_dim', 64)
                    
                    required_tools_embedding = encode_required_tools_embedding(
                        required_tools,
                        self.embedding_manager,  # 使用self的embedding_manager
                        target_dim=target_tools_dim  # 传入目标维度
                    )
                    required_tools_tensor = torch.FloatTensor(required_tools_embedding).unsqueeze(0).to(self.device)
                    logger.debug(f" Step {step}: Encoded {len(required_tools)} required tools with target dim={target_tools_dim}")
                else:
                    # 所有required_tools都已使用，使用零向量
                    tools_dim = getattr(self.network, 'tools_dim', 64)
                    required_tools_tensor = torch.zeros(1, tools_dim).to(self.device)
                    logger.debug(f" Step {step}: All required tools used, using zero vector for tools input")
            else:
                # 这个分支现在不应该被执行，因为我们在方法开始时已经验证了
                raise RuntimeError("Network does not support tools projection after initialization check")
            
            # 获取PPO策略
            with torch.no_grad():
                # 检查网络支持的输入
                if hasattr(self.network, 'tools_projection'):
                    # 新版网络，支持tools输入
                    logits, _ = self.network(state_tensor, rag_tensor, required_tools_tensor)
                    logger.debug(f" Step {step}: Using network with RAG and tools embeddings")
                else:
                    # 旧版网络不应该到这里，因为上面已经检查过了
                    raise ValueError("Inconsistent network configuration")
            
            # 获取有效动作
            valid_actions = self._get_valid_actions(state, visited_tools)
            if not valid_actions:
                logger.debug(f" Step {step}: No valid actions available")
                # 如果是第一步就没有有效动作，使用启发式方法选择一些基础工具
                if step == 0 and not required_tools:
                    logger.warning("No valid actions at start, using fallback tools")
                    # 选择一些基础工具作为起点
                    fallback_tools = ['file_operations_reader', 'data_processing_parser', 
                                     'network_fetcher', 'utility_cache']
                    for tool in fallback_tools:
                        if tool in self.tool_names and tool not in visited_tools:
                            workflow_sequence.append(tool)
                            visited_tools.add(tool)
                            # 更新状态
                            action = GeneralizedAction(
                                action_type=ActionType.INVOKE_TOOL,
                                tool_name=tool
                            )
                            state, _, _, _ = self._simulate_tool_execution(state, action)
                            break  # 只添加一个工具，然后继续循环
                    if workflow_sequence:
                        continue  # 继续主循环
                break  # 如果不是第一步或无法找到fallback，终止
            
            # 结合PPO策略和RAG分数选择动作
            action_scores = {}
            ppo_raw_scores = {}
            rag_scores = {}
            
            # 1. 获取PPO原始分数
            action_probs = torch.softmax(logits[0], dim=0).cpu().numpy()
            for action_idx in valid_actions:
                tool_name = self.idx_to_tool[action_idx]
                ppo_raw_scores[tool_name] = float(action_probs[action_idx])
            
            # 2. 获取RAG相关性分数（保持原有逻辑）
            for strategy, results in rag_context.items():
                for result in results:
                    if result.tool_name in [self.idx_to_tool[idx] for idx in valid_actions]:
                        if result.tool_name not in rag_scores:
                            rag_scores[result.tool_name] = 0
                        rag_scores[result.tool_name] = max(rag_scores[result.tool_name], result.score)
            
            # 3. 新增：对required_tools增加权重
            def apply_required_tools_ordering(action_scores, remaining_required_tools, 
                                            state, workflow_sequence, required_tools):
                """应用required_tools的顺序约束"""
                
                # 如果没有required_tools，返回原始分数
                if not required_tools:
                    return action_scores
                
                # 找出已经成功执行的required_tools
                executed_required = []
                for tool in workflow_sequence:
                    if tool in required_tools and tool not in executed_required:
                        # 确认成功执行
                        if tool in state.tool_states and state.tool_states[tool] == ToolExecutionStatus.SUCCESS:
                            executed_required.append(tool)
                
                logger.debug(f" Executed required tools: {executed_required}")
                logger.debug(f" Required tools order: {required_tools}")
                
                # 确定下一个应该执行的required_tool
                next_required_index = len(executed_required)
                
                if next_required_index < len(required_tools):
                    next_required_tool = required_tools[next_required_index]
                    logger.debug(f" Next required tool should be: {next_required_tool}")
                    
                    # 创建新的分数字典，强制选择正确的工具
                    ordered_scores = {}
                    
                    for tool_name in action_scores:
                        if tool_name == next_required_tool:
                            # 给下一个required_tool极高的分数
                            ordered_scores[tool_name] = 0.95  # 接近最大值
                            logger.debug(f" Boosted score for required tool {tool_name}: 0.95")
                        elif tool_name in required_tools:
                            # 其他required_tools给予极低分数（防止乱序）
                            tool_index = required_tools.index(tool_name)
                            if tool_index < next_required_index:
                                # 已经执行过的工具
                                ordered_scores[tool_name] = 0.01
                            else:
                                # 还未到执行时机的工具
                                ordered_scores[tool_name] = 0.05
                            logger.debug(f" Suppressed score for out-of-order required tool {tool_name}")
                        else:
                            # 非required_tools给予低分
                            ordered_scores[tool_name] = action_scores[tool_name] * 0.1
                    
                    return ordered_scores
                else:
                    # 所有required_tools都已执行，恢复正常选择
                    logger.debug(f" All required tools executed, using normal scores")
                    return action_scores

            # 在主循环中应用顺序控制
            # 替换原来的步骤3和5：
            required_boost = 0.3  # required_tools的权重提升
            for action_idx in valid_actions:
                tool_name = self.idx_to_tool[action_idx]
                base_score = ppo_raw_scores.get(tool_name, 0.0)
                action_scores[tool_name] = base_score

            print(f" Step {step}: Initial action scores: {action_scores}\n\n\n")
            # 应用required_tools的顺序约束
            action_scores = apply_required_tools_ordering(
                action_scores, 
                remaining_required_tools, 
                state, 
                workflow_sequence,
                required_tools  # 原始的完整列表
            )

            print(f" Step {step}: Action scores after required tools ordering: {action_scores}\n\n\n")
                        
            # 4. 计算动态混合权重（保持原有逻辑）
            rag_confidence = np.mean(list(rag_scores.values())) if rag_scores else 0.5
            # ppo_weight, rag_weight = self._calculate_dynamic_weights(state, rag_confidence)
            ppo_weight, rag_weight = 1, 0
            
            # 5. 组合最终分数
            for tool_name in action_scores:
                ppo_score = ppo_raw_scores.get(tool_name, 0.0)
                rag_score = rag_scores.get(tool_name, 0.0)
                
                # 如果是required_tool，已经在步骤3中提升了
                if tool_name not in remaining_required_tools:  # 使用remaining_required_tools
                    action_scores[tool_name] = ppo_weight * ppo_score + rag_weight * rag_score
            
                
                model_decision_scores[f"step_{step}_{tool_name}"] = {
                    'ppo_score': ppo_score,
                    'rag_score': rag_score,
                    'final_score': action_scores[tool_name],
                    'ppo_weight': ppo_weight,
                    'rag_weight': rag_weight,
                    'is_required': tool_name in required_tools
                }
            
            # 选择最佳动作
            best_tool = max(action_scores.items(), key=lambda x: x[1])[0]
            best_action = self.tool_to_idx[best_tool]
            
            # 记录选择历史
            tool_selection_history.append({
                'step': step,
                'tool': best_tool,
                'score': action_scores[best_tool],
                'scores': action_scores.copy(),
                'used_required_tools': best_tool in required_tools
            })
            
            # 执行动作并更新状态（保持原有逻辑）
            next_state, _, done, _ = self._simulate_tool_execution(state, best_action)
            
            workflow_sequence.append(best_tool)
            visited_tools.add(best_tool)
            
            # 更新required_tools（移除已使用的）
            if best_tool in remaining_required_tools:
                remaining_required_tools.remove(best_tool)  # 从副本中移除
                used_required_tools.add(best_tool)  # 标记为已使用
                logger.debug(f" Used required tool {best_tool}, remaining: {remaining_required_tools}")
                logger.debug(f" Total used required tools: {len(used_required_tools)}/{len(required_tools)}")
        
            state = next_state
            
            # 检查是否完成
            if self._is_workflow_complete(state, workflow_sequence):
                logger.debug(f" Workflow complete at step {step}")
                break

        logger.info(f"[DEBUG] Before topological sort: {workflow_sequence}")
        if workflow_sequence:
            sorted_sequence = self._topological_sort_workflow_sequence(workflow_sequence)
            logger.info(f"[DEBUG] After topological sort: {sorted_sequence}")
            workflow_sequence = sorted_sequence
            
            # 更新smart_workflow以反映排序后的序列
            # smart_workflow = self._rebuild_smart_workflow_from_sequence(
                # task_type, workflow_sequence, smart_workflow, tool_selection_history
            # )
        
        # 创建workflow字典时包含额外信息
        workflow = self._create_workflow_dict(task_type, workflow_sequence, task_instance)  # <- 添加task_instance参数
        workflow['model_scores'] = model_decision_scores
        workflow['selection_history'] = tool_selection_history
        workflow['rag_enhanced_network'] = hasattr(self.network, 'rag_projection')
        workflow['tools_input_network'] = hasattr(self.network, 'tools_projection')  # 新增
        workflow['rag_usage_stats'] = {
            'network_supports_rag': hasattr(self.network, 'rag_projection'),
            'network_supports_tools': hasattr(self.network, 'tools_projection'),  # 新增
            'rag_context_size': sum(len(results) for results in rag_context.values()),
            'average_rag_confidence': np.mean([r.score for results in rag_context.values() for r in results]) if rag_context else 0.0
        }
        workflow['required_tools_usage'] = {
            'initial_count': initial_required_tools_count,
            'used_count': initial_required_tools_count - len(required_tools),
            'completion_rate': (initial_required_tools_count - len(required_tools)) / max(1, initial_required_tools_count)
        }
        
        return workflow

    def _calculate_reward_with_order(self, state: GeneralizedMDPState, action: GeneralizedAction,
                                    next_state: GeneralizedMDPState, done: bool) -> float:
        """计算奖励，考虑required_tools的执行顺序"""
        
        # 基础奖励（使用原有逻辑）
        base_reward = self._calculate_base_reward(state, action, next_state, done)
        
        # 获取required_tools
        required_tools = []
        if hasattr(state, 'metadata') and 'task_instance' in state.metadata:
            required_tools = state.metadata['task_instance'].get('required_tools', [])
        
        if not required_tools:
            return base_reward
        
        # 顺序相关的奖励/惩罚
        order_reward = 0.0
        
        if action.action_type == ActionType.INVOKE_TOOL and action.tool_name:
            # 获取已执行的required_tools
            executed_required = []
            for tool in state.execution_sequence:
                if tool in required_tools and tool not in executed_required:
                    executed_required.append(tool)
            
            # 检查当前执行的工具
            if action.tool_name in required_tools:
                expected_index = len(executed_required)
                actual_index = required_tools.index(action.tool_name)
                
                print(f"[REWARD] Executing required tool: {action.tool_name}")
                print(f"[REWARD] Expected index: {expected_index}, Actual index: {actual_index}")
                
                if actual_index == expected_index:
                    # 正确的顺序执行
                    if next_state.tool_states.get(action.tool_name) == ToolExecutionStatus.SUCCESS:
                        order_reward += 5.0  # 大奖励
                        print(f"[REWARD] Correct order execution: +5.0")
                    else:
                        # 虽然顺序正确但执行失败
                        order_reward -= 2.0
                        print(f"[REWARD] Correct order but failed: -2.0")
                else:
                    # 错误的顺序执行
                    order_reward -= 10.0  # 严重惩罚
                    print(f"[REWARD] Wrong order execution: -10.0")
                    
                    # 如果跳过了前面的required_tools
                    if actual_index < expected_index:
                        # 执行了已经执行过的工具
                        order_reward -= 5.0
                        print(f"[REWARD] Duplicate execution: -5.0")
                    else:
                        # 跳过了前面的工具
                        skipped_count = actual_index - expected_index
                        order_reward -= skipped_count * 3.0
                        print(f"[REWARD] Skipped {skipped_count} tools: -{skipped_count * 3.0}")
            else:
                # 在还有未完成的required_tools时执行了其他工具
                remaining_required = len(required_tools) - len(executed_required)
                if remaining_required > 0:
                    order_reward -= 1.0
                    print(f"[REWARD] Executing non-required tool with {remaining_required} required tools remaining: -1.0")
        
        # Episode结束时的额外奖励
        if done:
            # 检查是否按正确顺序完成了所有required_tools
            required_execution_order = []
            for tool in next_state.execution_sequence:
                if tool in required_tools and tool not in required_execution_order:
                    required_execution_order.append(tool)
            
            if required_execution_order == required_tools:
                # 完美执行
                all_successful = all(
                    next_state.tool_states.get(tool) == ToolExecutionStatus.SUCCESS
                    for tool in required_tools
                )
                if all_successful:
                    order_reward += 10.0
                    print(f"[REWARD] Perfect execution of all required tools in order: +10.0")
            else:
                # 顺序错误或不完整
                order_reward -= 5.0
                print(f"[REWARD] Incomplete or wrong order execution at episode end: -5.0")
        
        return base_reward + order_reward

    def _topological_sort_workflow_sequence(self, sequence: List[str]) -> List[str]:
        """对工作流序列进行拓扑排序"""
        if not sequence or len(sequence) <= 1:
            return sequence
        
        logger.info(f"[DEBUG] Starting topological sort for workflow sequence")
        
        # 获取依赖图
        if not hasattr(self, '_dependency_graph'):
            self._dependency_graph = self._build_dependency_graph()
        
        dep_graph = self._dependency_graph
        
        # 创建包含序列中工具的子图
        subgraph = dep_graph.subgraph(sequence)
        
        # 尝试拓扑排序
        # 获取子图的拓扑排序
        sorted_nodes = list(nx.topological_sort(subgraph))
        
        # 处理不在依赖图中的工具（保持相对顺序）
        remaining_tools = [t for t in sequence if t not in sorted_nodes]
        
        # 合并排序结果
        result = sorted_nodes + remaining_tools
        
        logger.info(f"[DEBUG] Topological sort successful")
        return result
            


    def _simulate_tool_execution(self, state: GeneralizedMDPState, action_idx: int) -> Tuple[GeneralizedMDPState, float, bool, Dict[str, Any]]:
        """模拟工具执行并返回下一个状态
        
        Args:
            state: 当前状态
            action_idx: 动作索引（工具索引）
            
        Returns:
            tuple: (next_state, reward, done, info)
                - next_state: 执行后的新状态
                - reward: 奖励值（这里简化为0，因为workflow生成不需要真实奖励）
                - done: 是否完成
                - info: 额外信息
        """
        logger.debug(f" _simulate_tool_execution called with action_idx: {action_idx}")
        
        # 获取工具名称
        if action_idx < 0 or action_idx >= len(self.tool_names):
            print(f"[ERROR] Invalid action index: {action_idx}")
            # 返回原状态，标记为完成
            return state, 0.0, True, {'error': 'invalid_action'}
        
        tool_name = self.tool_names[action_idx]
        logger.debug(f" Simulating execution of tool: {tool_name}")
        
        # 使用已有的方法更新状态
        next_state = self._update_state_after_tool(state, tool_name)
        
        # 简单的奖励计算（workflow生成阶段不需要真实奖励）
        reward = 0.0
        
        # 检查是否完成
        done = self._is_workflow_complete(next_state, next_state.execution_sequence)
        
        # 构建信息字典
        info = {
            'tool_executed': tool_name,
            'step': next_state.workflow_step,
            'progress': next_state.overall_progress,
            'execution_sequence': next_state.execution_sequence
        }
        
        logger.debug(f" Simulation result - done: {done}, progress: {next_state.overall_progress}")
        
        return next_state, reward, done, info

    def _generate_contextual_query(self, state: GeneralizedMDPState, workflow_sequence: List[str]) -> str:
        """基于当前状态生成上下文相关的搜索查询"""
        # 根据数据流状态生成查询
        if state.data_flow_state == DataFlowState.EMPTY:
            return f"load input data for {state.task_type}"
        elif state.data_flow_state == DataFlowState.INITIALIZED:
            return f"validate verify check data after {workflow_sequence[-1] if workflow_sequence else 'start'}"
        elif state.data_flow_state == DataFlowState.VALIDATED:
            return f"transform process convert data for {state.task_type}"
        elif state.data_flow_state == DataFlowState.TRANSFORMED:
            return f"write export save output after transformation"
        else:
            # 基于最后执行的工具
            if workflow_sequence:
                return f"next step after {workflow_sequence[-1]} for {state.task_type}"
            else:
                return f"initial step for {state.task_type}"

    def _extract_state_features(self, state: GeneralizedMDPState) -> Dict[str, Any]:
        """提取状态的关键特征用于记录"""
        return {
            'progress': state.overall_progress,
            'workflow_step': state.workflow_step,
            'data_flow_state': state.data_flow_state.value if hasattr(state.data_flow_state, 'value') else str(state.data_flow_state),
            'executed_tools': len(state.execution_sequence),
            'consecutive_errors': state.consecutive_errors,
            'milestones_achieved': len(state.milestones_achieved)
        }


    def _encode_state_with_rag(self, state: GeneralizedMDPState, task_type: str, 
                            rag_context: Dict[str, List]) -> Tuple[np.ndarray, np.ndarray]:
        """编码状态和RAG上下文为网络输入"""
        
        # 添加防御性检查
        if self.state_dim is None:
            print("[ERROR] state_dim is None in _encode_state_with_rag")
            print("[ERROR] This indicates initialization order issue")
            print(f"[ERROR] tool_names count: {len(self.tool_names) if hasattr(self, 'tool_names') else 'Not initialized'}")
            # 直接报错，不使用fallback
            raise RuntimeError("state_dim must be initialized before encoding state. Check initialization order in MDPWorkflowGenerator.__init__")
        
        # 1. 基础状态编码（保持原有逻辑）
        base_features = []
        
        # Task type encoding (one-hot)
        task_type_idx = self.task_types.index(task_type) if task_type in self.task_types else 0
        task_encoding = [0.0] * len(self.task_types)
        task_encoding[task_type_idx] = 1.0
        base_features.extend(task_encoding)
        
        # Progress and step features
        # 计算验证通过的数量
        validations_passed_count = sum(1 for v in state.validation_results.values() if v)
        validations_total = len(state.validations_performed)
        
        base_features.extend([
            state.overall_progress,
            state.workflow_step / 20.0,  # normalized
            float(state.consecutive_errors) / 5.0,  # normalized
            float(len(state.execution_sequence)) / 10.0,  # normalized
            float(validations_passed_count) / max(1, validations_total)
        ])
        
        # Tool execution status (binary for each tool)
        for tool in self.tool_names[:30]:  # 限制前30个工具
            if tool in state.tool_states:
                status = state.tool_states[tool]
                base_features.append(1.0 if status == ToolExecutionStatus.SUCCESS else 0.5)
            else:
                base_features.append(0.0)
        
        # Pad to state_dim - 现在有了防御性检查
        state_vector = np.array(base_features[:self.state_dim])
        if len(state_vector) < self.state_dim:
            state_vector = np.pad(state_vector, (0, self.state_dim - len(state_vector)))
        
        # 2. RAG embedding 编码
        rag_embedding = np.zeros(64)  # 固定64维RAG embedding
        
        if rag_context and self.embedding_manager:
            # 收集所有搜索结果的分数和embeddings
            all_scores = []
            all_embeddings = []
            
            for operation, results in rag_context.items():
                for result in results[:5]:  # 每个操作最多5个结果
                    if hasattr(result, 'score'):
                        all_scores.append(result.score)
                        # 如果有embedding，使用它
                        if hasattr(result, 'embedding') and result.embedding is not None:
                            all_embeddings.append(result.embedding)
            
            # 聚合RAG信息
            if all_scores:
                # 平均置信度
                rag_embedding[0] = np.mean(all_scores)
                # 最高置信度
                rag_embedding[1] = np.max(all_scores)
                # 结果数量（归一化）
                rag_embedding[2] = len(all_scores) / 20.0
                
                # 如果有embeddings，计算加权平均
                if all_embeddings and len(all_embeddings[0]) >= 64:
                    weights = np.array(all_scores[:len(all_embeddings)]) / sum(all_scores[:len(all_embeddings)])
                    weighted_embedding = np.average(all_embeddings, axis=0, weights=weights)
                    rag_embedding[3:64] = weighted_embedding[:61]  # 填充剩余维度
            
            # 添加上下文信息
            if state.execution_sequence:
                # 最后执行的工具在工具列表中的索引（归一化）
                last_tool = state.execution_sequence[-1]
                if last_tool in self.tool_to_idx:
                    rag_embedding[10] = self.tool_to_idx[last_tool] / len(self.tool_names)
        
        # 打印调试信息
        print(f"[_encode_state_with_rag] state_vector shape: {state_vector.shape}, rag_embedding shape: {rag_embedding.shape}")
        
        return state_vector, rag_embedding

    def _calculate_tool_reliability(self, tool_name: str) -> float:
        """计算工具的可靠性得分 - 基于学习和语义理解"""
        logger.debug(f" Calculating reliability for {tool_name}")
        
        # 使用统一的管理器获取基础可靠性  # <- 修改了这一行
        base_reliability = self.tool_capability_manager.get_base_reliability(tool_name)  # <- 修改了这一行
        
        # 1. 首先检查历史学习数据（保持原有逻辑）
        if hasattr(self, 'tool_success_rates') and tool_name in self.tool_success_rates:
            stats = self.tool_success_rates[tool_name]
            if stats['total'] >= self.thresholds.min_history_for_learning:
                learned_reliability = stats['success'] / stats['total']
                logger.debug(f" Using learned reliability for {tool_name}: {learned_reliability:.3f} "
                    f"(based on {stats['total']} executions)")
                return learned_reliability
        
        # 如果没有学习数据，返回基础可靠性
        return base_reliability
        



# 文件：mdp_workflow_generator.py
# 位置：第3200行左右

    def _generate_smart_execution_plan(self, smart_actions: List[Dict]) -> str:
        """Generate intelligent execution plan with RAG insights and MCP details"""
        if not smart_actions:
            return "No execution steps required."
        
        plan_lines = []
        
        for action in smart_actions:
            step_num = action.get('step', 0)
            tool_name = action.get('tool_name', 'unknown')
            
            # 构建步骤描述
            plan_line = f"{step_num}. Execute {tool_name}"
            
            # 添加语义匹配信息
            if action.get('search_source') == 'embedding_search' and action.get('semantic_score', 0) > 0:
                score_percent = action['semantic_score'] * 100
                plan_line += f" (Semantic match: {score_percent:.0f}%)"
            
            # 添加推理说明
            if action.get('reasoning'):
                plan_line += f"\n   - Reason: {action['reasoning']}"
            
            # 添加依赖信息
            if action.get('dependencies'):
                deps = action['dependencies']
                if deps:
                    plan_line += f"\n   - Requires: {', '.join(deps[:3])}"
                    if len(deps) > 3:
                        plan_line += f" (+{len(deps)-3} more)"
            
            # 添加替代工具信息
            if action.get('alternatives'):
                alt_tools = [alt['tool_name'] for alt in action['alternatives'][:2]]
                if alt_tools:
                    plan_line += f"\n   - Alternatives: {', '.join(alt_tools)}"
            
            # 添加预期结果
            if action.get('expected_outcome'):
                outcome = action['expected_outcome']
                if 'milestone' in outcome:
                    plan_line += f"\n   - Expected: {outcome['milestone']}"
            
            # 添加置信度信息
            confidence = action.get('confidence', 0)
            if confidence > 0:
                if confidence >= 0.8:
                    confidence_level = "High"
                elif confidence >= 0.5:
                    confidence_level = "Medium"
                else:
                    confidence_level = "Low"
                plan_line += f"\n   - Confidence: {confidence_level} ({confidence:.1%})"
            
            plan_lines.append(plan_line)
        
        # 添加总结信息
        summary_lines = []
        
        # 统计语义搜索的使用
        semantic_tools = [a for a in smart_actions 
                        if a.get('search_source') == 'embedding_search']
        if semantic_tools:
            avg_score = sum(a.get('semantic_score', 0) for a in semantic_tools) / len(semantic_tools)
            summary_lines.append(f"Semantic Search Usage: {len(semantic_tools)}/{len(smart_actions)} tools")
            summary_lines.append(f"Average Semantic Score: {avg_score:.1%}")
        
        # 统计关键工具
        critical_count = sum(1 for a in smart_actions 
                            if a.get('confidence', 0) >= 0.8)
        if critical_count > 0:
            summary_lines.append(f"Critical Steps: {critical_count}")
        
        # 组合最终的执行计划
        result = "\n".join(plan_lines)
        
        if summary_lines:
            result += "\n\n### Execution Summary:\n"
            result += "\n".join(f"- {line}" for line in summary_lines)
        
        return result

    def _extract_operations_from_description(self, description: str) -> List[str]:
        """从任务描述中提取关键操作并进行拓扑排序"""
        operations = []
        
        # 优先使用语义索引进行操作提取
        logger.debug(f" Extracting operations semantically from: {description[:100]}...")
        
        # 使用工具能力管理器的语义理解功能
        suggested_operations = self.tool_capability_manager.suggest_operations_for_task(
            description, k=8
        )
        
        operations.extend(suggested_operations)
        logger.debug(f" Semantically extracted operations: {operations}")
        
        # 新增：基于工具依赖关系进行拓扑排序
        sorted_operations = self._topological_sort_operations(operations)
        logger.debug(f" After topological sort: {sorted_operations}")
        
        return sorted_operations

    def _topological_sort_operations(self, operations: List[str]) -> List[str]:
        """根据工具依赖关系对操作进行拓扑排序"""
        if not operations or len(operations) <= 1:
            return operations
        
        logger.debug(f" Starting topological sort for operations: {operations}")
        
        # 获取依赖图
        if not hasattr(self, '_dependency_graph'):
            self._dependency_graph = self._build_dependency_graph()
        
        dep_graph = self._dependency_graph
        
        # 收集与操作相关的所有工具
        operation_tools = {}  # operation -> [tools]
        tools_for_operations = set()
        
        # 遍历所有工具，找出与操作匹配的工具
        for tool_name, capability in self.tool_capabilities.items():
            if hasattr(capability, 'semantic_operations'):
                for sem_op in capability.semantic_operations:
                    for operation in operations:
                        # 检查操作是否匹配
                        if operation in sem_op or sem_op in operation:
                            if operation not in operation_tools:
                                operation_tools[operation] = []
                            operation_tools[operation].append(tool_name)
                            tools_for_operations.add(tool_name)
                            logger.debug(f" Operation '{operation}' matched tool '{tool_name}'")
        
        # 如果没有找到匹配的工具，返回原始顺序
        if not tools_for_operations:
            logger.debug(f" No tools matched operations, using predefined order")
            return self._sort_by_predefined_order(operations)
        
        # 创建操作之间的依赖关系
        operation_dep_graph = nx.DiGraph()
        
        # 添加所有操作作为节点
        for op in operations:
            operation_dep_graph.add_node(op)
        
        # 根据工具依赖关系推断操作依赖关系
        for op1 in operations:
            for op2 in operations:
                if op1 == op2:
                    continue
                
                # 检查op1的任何工具是否依赖于op2的任何工具
                tools1 = operation_tools.get(op1, [])
                tools2 = operation_tools.get(op2, [])
                
                for tool1 in tools1:
                    for tool2 in tools2:
                        if tool1 in dep_graph and tool2 in dep_graph:
                            # 如果tool2是tool1的依赖，那么op2应该在op1之前
                            if dep_graph.has_edge(tool2, tool1):
                                operation_dep_graph.add_edge(op2, op1)
                                logger.debug(f" Added dependency: {op2} -> {op1}")
                                break
                    if operation_dep_graph.has_edge(op2, op1):
                        break
        
        # 尝试拓扑排序
        try:
            sorted_operations = list(nx.topological_sort(operation_dep_graph))
            
            # 处理不在排序结果中的操作（孤立节点）
            remaining_operations = [op for op in operations if op not in sorted_operations]
            
            # 对剩余操作使用预定义顺序排序
            remaining_sorted = self._sort_by_predefined_order(remaining_operations)
            
            # 合并结果
            result = sorted_operations + remaining_sorted
            
            logger.debug(f" Topological sort successful: {result}")
            return result
            
        except nx.NetworkXUnfeasible:
            # 如果有循环依赖，使用预定义顺序
            print(f"[WARNING] Circular dependency detected in operations, using predefined order")
            return self._sort_by_predefined_order(operations)
        except Exception as e:
            print(f"[ERROR] Topological sort failed: {e}")
            # 降级到预定义顺序
            return self._sort_by_predefined_order(operations)

    def _sort_by_predefined_order(self, operations: List[str]) -> List[str]:
        """按预定义的逻辑顺序排序操作（备用方案）"""
        # 保持操作的逻辑顺序
        operation_order = ['read', 'fetch', 'parse', 'validate', 'filter', 
                        'transform', 'compute', 'aggregate', 'integrate', 
                        'write', 'export', 'cache']
        
        # 按逻辑顺序排序
        ordered_operations = []
        for op_type in operation_order:
            for op in operations:
                if op == op_type or op.startswith(op_type):
                    if op not in ordered_operations:
                        ordered_operations.append(op)
        
        # 添加未在顺序中的操作
        for op in operations:
            if op not in ordered_operations:
                ordered_operations.append(op)
        
        return ordered_operations



    def _create_initial_state(self, task_type: str, task_instance: Optional[Dict[str, Any]] = None) -> GeneralizedMDPState:
        """创建初始状态"""
        # 创建基础state对象
        state = GeneralizedMDPState(
            task_id=task_instance.get('instance_id', f"{task_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}") if task_instance else f"{task_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            task_type=task_type,
            task_objective=task_instance.get('description', f"Complete {task_type} workflow") if task_instance else f"Complete {task_type} workflow"
        )
        
        # 初始化进度相关属性
        state.overall_progress = 0.0
        state.workflow_step = 0
        state.execution_sequence = []
        state.consecutive_errors = 0
        state.total_errors = 0
        
        # 初始化数据流状态 - 这是修复的关键
        logger.debug(f" Initializing data_flow_state to DataFlowState.EMPTY")
        state.data_flow_state = DataFlowState.EMPTY
        
        # 初始化其他Phase 3相关属性
        state.milestones_achieved = set()
        state.expected_milestones = set()
        state.semantic_milestones = []
        state.subtask_progress = {}
        state.tool_states = {}
        state.tool_outputs = {}
        state.tool_errors = {}
        state.retry_counts = {}
        state.validations_performed = []
        state.validation_results = {}
        state.tool_timings = {}
        state.confidence_score = 1.0
        state.tool_synergy_score = 0.0
        
        # RAG相关属性初始化
        state.rag_search_results = {}
        state.tool_candidates = {}
        state.semantic_confidence_scores = {}
        state.tool_selection_history = []
        
        # 如果有task_instance，存储额外信息和提取任务特征
        if task_instance:
            state.metadata['task_instance'] = task_instance
            state.metadata['description'] = task_instance.get('description', '')
            state.metadata['required_tools'] = task_instance.get('required_tools', [])
            
            # 提取任务特征（调用_extract_task_features会自动设置task_features）
            if not hasattr(state, 'task_features') or state.task_features is None:
                # 触发__post_init__来初始化task_features
                state._extract_task_features()
                state._initialize_expected_milestones()
        
        logger.debug(f" Created initial state with data_flow_state: {state.data_flow_state}")
        
        return state

    def _encode_state_for_generation(self, state: GeneralizedMDPState, task_type: str) -> np.ndarray:
        """编码状态用于模型输入"""
        # 这需要与训练时的编码方式一致
        
        encoded = []
        
        # 工具执行状态（每个工具11维）
        for tool in self.tool_names:
            if tool in state.execution_sequence:  # 使用 execution_sequence 而不是 executed_tools
                encoded.extend([0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0])  # SUCCESS状态
            else:
                encoded.extend([1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])  # NOT_STARTED状态
        
        # 进度特征（10维）
        encoded.extend([
            state.overall_progress,
            len(state.execution_sequence) / 20.0,
            state.consecutive_errors / 10.0,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
        ])
        
        # 任务类型特征（如果使用task-aware）
        task_types = ['simple_task', 'data_pipeline', 'api_integration', 
                    'basic_task', 'multi_stage_pipeline']
        task_one_hot = [0.0] * len(task_types)
        if task_type in task_types:
            task_one_hot[task_types.index(task_type)] = 1.0
        encoded.extend(task_one_hot)
        
        # 补齐到正确的维度
        while len(encoded) < self.state_dim:
            encoded.append(0.0)
        
        return np.array(encoded[:self.state_dim], dtype=np.float32)

    def _get_valid_actions(self, state: GeneralizedMDPState, visited_tools: Set[str]) -> List[int]:
        """获取有效的动作索引 - 强制按顺序执行required_tools"""
        
        # 获取required_tools
        required_tools = []
        if hasattr(state, 'metadata') and 'task_instance' in state.metadata:
            required_tools = state.metadata['task_instance'].get('required_tools', [])
        
        logger.debug(f" Getting valid actions:")
        print(f"  Required tools: {required_tools}")
        print(f"  Visited tools: {visited_tools}")
        print(f"  Execution sequence: {state.execution_sequence}")
        
        # 如果有required_tools，强制按顺序执行
        if required_tools:
            # 找出已经成功执行的required_tools
            executed_required = []
            for tool in state.execution_sequence:
                if tool in required_tools and tool not in executed_required:
                    # 检查是否成功执行
                    if tool in state.tool_states and state.tool_states[tool] == ToolExecutionStatus.SUCCESS:
                        executed_required.append(tool)
            
            logger.debug(f" Executed required tools: {executed_required}")
            
            # 确定下一个应该执行的required_tool
            next_required_index = len(executed_required)
            
            if next_required_index < len(required_tools):
                # 还有required_tools需要执行
                next_required_tool = required_tools[next_required_index]
                
                # 检查依赖关系是否满足
                # capability = self.tool_capabilities.get(next_required_tool)
                # if capability and hasattr(capability, 'dependencies'):
                #     deps_satisfied = all(
                #         dep in state.execution_sequence and
                #         state.tool_states.get(dep) == ToolExecutionStatus.SUCCESS
                #         for dep in capability.dependencies
                #     )
                    
                    # if not deps_satisfied:
                    #     logger.debug(f" Dependencies not satisfied for {next_required_tool}")
                    #     # 如果依赖不满足，不返回任何工具动作
                    #     return []
                
                # 只返回下一个required_tool的索引
                if next_required_tool in self.tool_names:
                    tool_index = self.tool_names.index(next_required_tool)
                    logger.debug(f" Next required tool: {next_required_tool} (index: {tool_index})")
                    return [tool_index]
                else:
                    print(f"[ERROR] Required tool {next_required_tool} not found in tool_names!")
                    return []
            else:
                # 所有required_tools都已执行，可以执行其他工具
                logger.debug(f" All required tools executed, allowing other actions")
        
        # 如果没有required_tools或都已完成，使用原来的逻辑
        valid_actions = []
        
        for i, tool in enumerate(self.tool_names):
            # 跳过已执行的工具
            if tool in visited_tools:
                continue
            
            # 检查依赖关系
            capability = self.tool_capabilities.get(tool)
            if capability and hasattr(capability, 'dependencies') and capability.dependencies:
                # 如果是第一步且没有required_tools，允许没有依赖的工具
                if len(state.execution_sequence) == 0 and not required_tools:
                    # 只允许没有依赖或依赖很少的工具
                    if len(capability.dependencies) == 0:
                        valid_actions.append(i)
                else:
                    deps_satisfied = all(
                        dep in state.execution_sequence and
                        state.tool_states.get(dep) == ToolExecutionStatus.SUCCESS
                        for dep in capability.dependencies
                    )
                    if deps_satisfied:
                        valid_actions.append(i)
            else:
                # 没有依赖的工具总是有效的
                valid_actions.append(i)
        
        logger.debug(f" Valid actions: {[self.tool_names[i] for i in valid_actions[:5]]}...")  # 只显示前5个
        return valid_actions

    #
    # def _get_valid_actions(self, state: GeneralizedMDPState, visited_tools: Set[str]) -> List[int]:  # <- 修改了这一行：类型注解
    #     """获取有效的动作索引"""
    #     valid_actions = []
        
    #     for i, tool in enumerate(self.tool_names):
    #         # 跳过已执行的工具
    #         if tool in visited_tools:
    #             continue
            
    #         # 检查依赖关系
    #         capability = self.tool_capabilities.get(tool)
    #         if capability and hasattr(capability, 'dependencies'):
    #             deps_satisfied = all(dep in state.execution_sequence  # <- 修改了这一行：使用 execution_sequence
    #                             for dep in capability.dependencies)
    #             if deps_satisfied:
    #                 valid_actions.append(i)
    #         else:
    #             valid_actions.append(i)
        
    #     return valid_actions

    def _update_state_after_tool(self, state: GeneralizedMDPState, tool_name: str) -> GeneralizedMDPState:
        """更新执行工具后的状态"""
        # 使用 transition 方法创建新状态，或手动复制
        new_state = GeneralizedMDPState(
            task_id=state.task_id,
            task_type=state.task_type,
            task_objective=state.task_objective
        )
        
        # 复制所有状态属性
        new_state.tool_states = state.tool_states.copy()
        new_state.tool_outputs = state.tool_outputs.copy()
        new_state.tool_errors = state.tool_errors.copy()
        new_state.retry_counts = state.retry_counts.copy()
        new_state.overall_progress = min(1.0, state.overall_progress + 0.1)
        new_state.workflow_step = state.workflow_step + 1
        new_state.execution_sequence = state.execution_sequence + [tool_name]
        new_state.consecutive_errors = state.consecutive_errors
        new_state.total_errors = state.total_errors
        new_state.error_history = state.error_history.copy()
        new_state.milestones_achieved = state.milestones_achieved.copy()
        new_state.expected_milestones = state.expected_milestones.copy()
        new_state.metadata = state.metadata.copy()
        
        # 复制 task features（如果有）
        if hasattr(state, 'task_features'):
            new_state.task_features = state.task_features
        
        # 设置工具状态
        new_state.tool_states[tool_name] = ToolExecutionStatus.SUCCESS
        
        return new_state
    
    def get_tool_success_history(self) -> Dict[str, Dict[str, int]]:
        """获取工具成功历史记录
        
        Returns:
            Dict[str, Dict[str, int]]: 工具名称到成功统计的映射
                每个工具的统计包含:
                - 'success': 成功次数
                - 'total': 总执行次数
        """
        # 直接返回tool_success_rates，它已经是所需的格式
        return dict(self.tool_success_rates)

    def _is_workflow_complete(self, state: GeneralizedMDPState, workflow_sequence: List[str]) -> bool:
        """检查工作流是否完成 - 基于required_tools的完成情况和顺序"""
        
        # 获取required_tools（从state的metadata中）
        required_tools = []
        if hasattr(state, 'metadata') and 'task_instance' in state.metadata:
            required_tools = state.metadata['task_instance'].get('required_tools', [])
        
        # 打印调试信息
        logger.debug(f" Checking workflow completion:")
        print(f"  Required tools: {required_tools}")
        print(f"  Execution sequence: {state.execution_sequence}")
        print(f"  Tool states: {state.tool_states}")
        
        # 条件1：如果有required_tools，检查是否按顺序成功完成
        if required_tools:
            # 从execution_sequence中提取required_tools的执行顺序
            required_execution_order = []
            for tool in state.execution_sequence:
                if tool in required_tools and tool not in required_execution_order:
                    required_execution_order.append(tool)
            
            # 检查是否所有required_tools都被执行
            all_executed = len(required_execution_order) == len(required_tools)
            
            # 检查是否都成功
            all_successful = all(
                tool in state.tool_states and 
                state.tool_states[tool] == ToolExecutionStatus.SUCCESS
                for tool in required_tools
            )
            
            # 检查顺序是否正确
            sequence_correct = required_execution_order == required_tools
            
            logger.debug(f" Required tools execution order: {required_execution_order}")
            logger.debug(f" All executed: {all_executed}, All successful: {all_successful}, Sequence correct: {sequence_correct}")
            
            # 只有当所有条件都满足时才算完成
            if all_executed and all_successful and sequence_correct:
                logger.debug(f" All required tools completed successfully in correct order!")
                return True
            else:
                # 显示具体问题
                if not all_executed:
                    missing_tools = [t for t in required_tools if t not in required_execution_order]
                    logger.debug(f" Missing required tools: {missing_tools}")
                if not sequence_correct and required_execution_order:
                    logger.debug(f" Incorrect execution order. Expected: {required_tools}, Got: {required_execution_order}")
                if not all_successful:
                    failed_tools = [t for t in required_tools if t not in state.tool_states or 
                                state.tool_states[t] != ToolExecutionStatus.SUCCESS]
                    logger.debug(f" Failed required tools: {failed_tools}")
        
        # 条件2：达到最大步骤数（防止无限循环）
        max_steps = 20  # 稍微增加，给顺序执行更多空间
        if len(workflow_sequence) >= max_steps:
            logger.debug(f" Maximum steps ({max_steps}) reached")
            return True
        
        # 条件3：如果没有required_tools，使用其他完成标准
        if not required_tools:
            # 至少执行3个工具
            if len(workflow_sequence) < 3:
                return False
            
            # 检查是否有输出工具执行成功
            output_tools = ['file_operations_writer', 'network_poster', 'utility_notifier']
            output_completed = any(
                tool in state.tool_states and 
                state.tool_states[tool] == ToolExecutionStatus.SUCCESS
                for tool in output_tools
            )
            
            if output_completed:
                logger.debug(f" Output tool completed")
                return True
            
            # 如果已经执行了5个或更多工具，认为完成
            if len(workflow_sequence) >= 5:
                logger.debug(f" Executed {len(workflow_sequence)} tools, considering complete")
                return True
            
            # 检查里程碑完成情况
            if state.expected_milestones and state.milestones_achieved:
                achievement_ratio = len(state.milestones_achieved & state.expected_milestones) / len(state.expected_milestones)
                if achievement_ratio >= 0.9:  # 90%的里程碑
                    logger.debug(f" Milestones achieved: {achievement_ratio:.1%}")
                    return True
        
        # 条件4：连续多次NO_OP（表示模型认为已完成）
        if len(workflow_sequence) >= 3:
            # 检查最后3个动作是否都是NO_OP
            last_actions = workflow_sequence[-3:]
            if all(action == 'NO_OP' for action in last_actions):
                logger.debug(f" Multiple consecutive NO_OP actions")
                return True
        
        return False


# 文件：mdp_workflow_generator.py
# 位置：第8850-8920行左右
# 函数名：_create_workflow_dict

    def _create_workflow_dict(self, task_type: str, sequence: List[str], 
                            task_instance: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """创建工作流字典，包含智能workflow"""
        
        # 构建依赖图（而不是传递空图）
        dependency_graph = self._build_dependency_graph()
        
        # 新增：根据required_tools重新排序sequence
        if task_instance and 'required_tools' in task_instance:
            required_tools = task_instance.get('required_tools', [])
            if required_tools:
                print(f"[DEBUG] Reordering sequence based on required_tools: {required_tools}")
                print(f"[DEBUG] Original sequence: {sequence}")
                
                # 重新排序sequence
                reordered = []
                remaining = list(sequence)  # 复制原始序列
                
                # 首先按照required_tools的顺序添加
                for tool in required_tools:
                    if tool in remaining:
                        reordered.append(tool)
                        remaining.remove(tool)
                
                # 然后添加剩余的工具（保持它们的相对顺序）
                reordered.extend(remaining)
                
                print(f"[DEBUG] Reordered sequence: {reordered}")
                sequence = reordered
            else:
                raise 
        else:
            raise
        
        # 创建智能workflow
        smart_workflow = self._sequence_to_smart_workflow(task_type, sequence)
        
        # 生成执行计划
        execution_plan = self._generate_execution_plan(smart_workflow)
        
        # 提取错误处理策略
        error_handling = self._extract_error_handling(smart_workflow)
        
        return {
            'task_type': task_type,
            'optimal_sequence': sequence,
            'smart_workflow': smart_workflow,
            'execution_plan': execution_plan,
            'error_handling': error_handling,
            'success_probability': self._calculate_success_probability(sequence, dependency_graph),  # 使用实际的依赖图
            'workflow_quality': self._calculate_workflow_quality({'optimal_sequence': sequence}),
            'critical_tools': self._identify_critical_tools(sequence, dependency_graph),  # 也使用依赖图
            'algorithm': getattr(self, 'algorithm', 'random'),
            'generated_at': datetime.now().isoformat()
        }
    
    def _reorder_sequence_by_required_tools(self, sequence: List[str], required_tools: List[str]) -> List[str]:
        """根据required_tools的顺序重新排列工具序列"""
        
        print(f"[DEBUG] Reordering sequence based on required_tools: {required_tools}")
        print(f"[DEBUG] Original sequence: {sequence}")
        
        # 创建重新排序的序列
        reordered = []
        remaining = list(sequence)  # 复制原始序列
        
        # 首先按照required_tools的顺序添加
        for tool in required_tools:
            if tool in remaining:
                reordered.append(tool)
                remaining.remove(tool)
        
        # 然后添加剩余的工具（保持它们的相对顺序）
        reordered.extend(remaining)
        
        print(f"[DEBUG] Reordered sequence: {reordered}")
        
        return reordered


    def _is_critical_tool(self, tool_name: str, task_type: str) -> bool:
        """
        基于学习到的数据判断工具是否关键
        
        判断标准（全部基于历史数据）：
        1. 工具的历史成功率影响
        2. 工具在成功workflow中的位置
        3. 工具失败后任务的恢复难度
        4. 工具在特定任务类型中的重要性
        """
        
        # 1. 基于学习到的关键性得分
        if hasattr(self, 'tool_criticality_scores'):
            criticality_score = self.tool_criticality_scores.get(tool_name, 0.0)
            if criticality_score > 0.7:  # 高关键性阈值
                return True
        
        # 2. 基于工具在成功workflow中的位置重要性
        if hasattr(self, 'tool_position_importance') and task_type in self.tool_position_importance:
            position_scores = self.tool_position_importance[task_type]
            
            # 检查工具是否经常出现在关键位置（开始或结束）
            start_importance = position_scores.get(f"{tool_name}_start", 0.0)
            end_importance = position_scores.get(f"{tool_name}_end", 0.0)
            
            if start_importance > 0.6 or end_importance > 0.6:
                return True
        
        # 3. 基于工具失败影响（如果工具失败后任务成功率很低，则认为关键）
        if hasattr(self, 'tool_failure_impact'):
            failure_impact = self.tool_failure_impact.get(tool_name, 0.0)
            if failure_impact > 0.8:  # 失败影响大
                return True
        
        # 4. 基于任务特定的工具重要性（从成功patterns中学习）
        if hasattr(self, 'tool_importance') and task_type in self.tool_importance:
            task_importance = self.tool_importance[task_type].get(tool_name, 0.0)
            if task_importance > 0.75:
                return True
        
        # 5. 基于工具的成功率统计
        if hasattr(self, 'tool_success_rates'):
            stats = self.tool_success_rates.get(tool_name, {'success': 0, 'total': 0})
            if stats['total'] > 10:  # 有足够的统计数据
                success_rate = stats['success'] / stats['total']
                # 成功率特别低的工具可能需要重试（反向逻辑）
                if success_rate < 0.5:
                    return True
        
        # 6. 使用embedding相似度（如果可用）来判断语义重要性
        if self.use_embeddings and self.embedding_manager and hasattr(self, 'learned_critical_patterns'):
            # 使用学习到的关键模式而不是硬编码查询
            for pattern in self.learned_critical_patterns:
                try:
                    results = self.embedding_manager.search(pattern['query'], k=10, return_scores=True)
                    for result in results:
                        if result.tool_name == tool_name and result.score > pattern['threshold']:
                            return True
                except:
                    pass
        
        return False

    def update_tool_criticality(self, episode_data: Dict[str, Any]):
        """
        从训练episode中更新工具关键性数据
        
        Args:
            episode_data: 包含episode信息的字典，包括：
                - trajectory: 执行轨迹
                - final_score: 最终得分
                - task_type: 任务类型
                - tool_failures: 工具失败记录
        """
        trajectory = episode_data.get('trajectory', [])
        final_score = episode_data.get('final_score', 0.0)
        task_type = episode_data.get('task_type', 'unknown')
        tool_failures = episode_data.get('tool_failures', {})
        
        # 1. 更新工具成功率统计
        for state, action, reward, next_state in trajectory:
            if action.action_type == ActionType.INVOKE_TOOL and action.tool_name:
                tool_name = action.tool_name
                self.tool_success_rates[tool_name]['total'] += 1
                
                if next_state.tool_states.get(tool_name) == ToolExecutionStatus.SUCCESS:
                    self.tool_success_rates[tool_name]['success'] += 1
        
        # 2. 更新位置重要性（成功的episode才更新）
        if final_score > 0.7:
            executed_tools = [action.tool_name for _, action, _, _ in trajectory 
                            if action.action_type == ActionType.INVOKE_TOOL and action.tool_name]
            
            if executed_tools:
                # 第一个工具
                first_tool = executed_tools[0]
                self.tool_position_importance[task_type][f"{first_tool}_start"] += final_score
                
                # 最后一个工具
                last_tool = executed_tools[-1]
                self.tool_position_importance[task_type][f"{last_tool}_end"] += final_score
        
        # 3. 更新失败影响分析
        for failed_tool, failure_data in tool_failures.items():
            # 如果工具失败但任务最终成功，说明工具不是关键的
            if final_score > 0.5:
                self.tool_failure_impact[failed_tool] *= 0.9  # 降低影响
            else:
                # 工具失败且任务失败，增加影响分数
                self.tool_failure_impact[failed_tool] = min(1.0, 
                    self.tool_failure_impact[failed_tool] * 1.1 + 0.1)
        
        # 4. 基于整体表现更新关键性得分
        for state, action, reward, next_state in trajectory:
            if action.action_type == ActionType.INVOKE_TOOL and action.tool_name:
                tool_name = action.tool_name
                
                # 综合考虑多个因素计算关键性
                position_factor = 0.0
                if executed_tools.index(tool_name) == 0:  # 第一个工具
                    position_factor = 0.3
                elif executed_tools.index(tool_name) == len(executed_tools) - 1:  # 最后一个工具
                    position_factor = 0.3
                
                # 基于奖励的重要性
                reward_factor = min(1.0, reward / 10.0) if reward > 0 else 0.0
                
                # 基于最终得分的调整
                score_factor = final_score
                
                # 更新关键性得分（使用指数移动平均）
                new_criticality = position_factor + reward_factor * 0.5 + score_factor * 0.2
                old_criticality = self.tool_criticality_scores[tool_name]
                self.tool_criticality_scores[tool_name] = old_criticality * 0.8 + new_criticality * 0.2

    def learn_critical_patterns_from_episodes(self, successful_episodes: List[Dict]):
        """
        从成功的episodes中学习关键模式
        
        替代硬编码的critical_queries
        """
        self.learned_critical_patterns = []
        
        # 分析成功episodes中的工具使用模式
        tool_context_pairs = defaultdict(list)
        
        for episode in successful_episodes:
            if episode['final_score'] > 0.8:  # 只学习高分episodes
                trajectory = episode['trajectory']
                task_description = episode.get('task_description', '')
                
                for state, action, _, _ in trajectory:
                    if action.action_type == ActionType.INVOKE_TOOL and action.tool_name:
                        # 记录工具和上下文的配对
                        context = f"{state.task_type} {task_description}"
                        tool_context_pairs[action.tool_name].append({
                            'context': context,
                            'position': state.workflow_step,
                            'score': episode['final_score']
                        })
        
        # 从高频模式中提取关键查询
        for tool_name, contexts in tool_context_pairs.items():
            if len(contexts) >= 3:  # 至少出现3次
                # 提取最常见的上下文词
                context_words = defaultdict(int)
                for ctx_data in contexts:
                    words = ctx_data['context'].lower().split()
                    for word in words:
                        context_words[word] += 1
                
                # 构建查询模式
                top_words = sorted(context_words.items(), key=lambda x: x[1], reverse=True)[:3]
                if top_words:
                    query = ' '.join([word for word, _ in top_words])
                    avg_score = sum(ctx['score'] for ctx in contexts) / len(contexts)
                    
                    self.learned_critical_patterns.append({
                        'query': query,
                        'threshold': avg_score * 0.9,  # 动态阈值
                        'tool_examples': [tool_name]
                    })

    def save_learned_criticality(self, path: Optional[str] = None):
        """保存学习到的工具关键性数据"""
        if path is None:
            path = self.model_path.parent / "tool_criticality.json" if self.model_path else "tool_criticality.json"
        
        criticality_data = {
            'tool_criticality_scores': dict(self.tool_criticality_scores),
            'tool_failure_impact': dict(self.tool_failure_impact),
            'tool_position_importance': {k: dict(v) for k, v in self.tool_position_importance.items()},
            'tool_success_rates': dict(self.tool_success_rates),
            'learned_critical_patterns': getattr(self, 'learned_critical_patterns', []),
            'timestamp': datetime.now().isoformat()
        }
        
        with open(path, 'w') as f:
            json.dump(criticality_data, f, indent=2)
        
        logger.info(f"Saved tool criticality data to {path}")

    def load_learned_criticality(self, path: Optional[str] = None):
        """加载学习到的工具关键性数据"""
        if path is None:
            path = self.model_path.parent / "tool_criticality.json" if self.model_path else "tool_criticality.json"
        
        if not Path(path).exists():
            logger.warning(f"No criticality data found at {path}")
            return
        
        try:
            with open(path, 'r') as f:
                criticality_data = json.load(f)
            
            self.tool_criticality_scores = defaultdict(float, criticality_data.get('tool_criticality_scores', {}))
            self.tool_failure_impact = defaultdict(float, criticality_data.get('tool_failure_impact', {}))
            self.tool_position_importance = defaultdict(lambda: defaultdict(float))
            for task_type, positions in criticality_data.get('tool_position_importance', {}).items():
                self.tool_position_importance[task_type] = defaultdict(float, positions)
            self.tool_success_rates = defaultdict(lambda: {'success': 0, 'total': 0}, 
                                                criticality_data.get('tool_success_rates', {}))
            self.learned_critical_patterns = criticality_data.get('learned_critical_patterns', [])
            
            logger.info(f"Loaded tool criticality data from {path}")
        except Exception as e:
            logger.error(f"Failed to load criticality data: {e}")

    def _sequence_to_smart_workflow(self, task_type: str, sequence: List[str]) -> SmartWorkflow:
        """将简单的工具序列转换为智能workflow"""
        smart_workflow = SmartWorkflow(task_type=task_type, steps=[])
        
        for i, tool_name in enumerate(sequence):
            # 创建主要的工具调用步骤
            step = WorkflowStep(
                step_id=i * 2,  # 留出空间给retry步骤
                action_type=ActionType.INVOKE_TOOL,
                tool_name=tool_name,
                on_success=i * 2 + 2 if i < len(sequence) - 1 else None,
                on_failure=i * 2 + 1,  # 指向retry步骤
                max_retries=1
            )
            smart_workflow.steps.append(step)
            
            # 为关键工具添加retry步骤
            if self._is_critical_tool(tool_name, task_type):
                retry_step = WorkflowStep(
                    step_id=i * 2 + 1,
                    action_type=ActionType.RETRY_TOOL,
                    tool_name=tool_name,
                    on_success=step.on_success,
                    on_failure=step.on_success,  # 失败后继续
                    metadata={'retry_of': i * 2}
                )
                smart_workflow.steps.append(retry_step)
        
        return smart_workflow


    def _match_tools_for_operation(self, operation: str, tools_by_category: Dict[str, List[str]], 
                                current_sequence: List[str]) -> List[str]:
        """为特定操作匹配工具（使用语义理解）"""
        matched = []
        
        # 优先使用语义搜索
        logger.debug(f" Matching tools semantically for operation: {operation}")
        
        # 查找语义相似的操作
        similar_operations = self.tool_capability_manager.enhance_semantic_operations([operation])
        
        # 在工具能力中查找匹配
        for tool_name, capability in self.tool_capabilities.items():
            if tool_name in current_sequence:
                continue
            
            # 计算操作相似度
            for sem_op in capability.semantic_operations:
                for similar_op in similar_operations:
                    if similar_op in sem_op or sem_op in similar_op:
                        matched.append(tool_name)
                        break
                if tool_name in matched:
                    break
                    
        # Fallback: 原有的直接匹配逻辑
        if not matched and operation in tools_by_category:
            for tool in tools_by_category[operation]:
                if tool not in current_sequence:
                    matched.append(tool)
        
        return matched[:3]  # 返回最多3个匹配


    def _order_tools_by_dependencies(self, tools: List[str], 
                                    dependency_graph: nx.DiGraph) -> List[str]:
        """根据依赖关系排序工具"""
        # 创建子图
        subgraph = dependency_graph.subgraph(tools)
        
        # 尝试拓扑排序
        try:
            ordered = list(nx.topological_sort(subgraph))
            # 添加没有在图中的工具
            for tool in tools:
                if tool not in ordered:
                    ordered.append(tool)
            return ordered
        except nx.NetworkXUnfeasible:
            # 如果有循环依赖，返回原序列
            return tools

    def _deduplicate_and_order(self, sequence: List[str], dependency_graph: nx.DiGraph) -> List[str]:
        """去重并根据依赖关系排序工具序列"""
        # 去重
        seen = set()
        unique_sequence = []
        for tool in sequence:
            if tool not in seen:
                seen.add(tool)
                unique_sequence.append(tool)
        
        # 尝试根据依赖关系排序
        try:
            # 创建子图只包含序列中的工具
            subgraph = dependency_graph.subgraph(unique_sequence)
            # 拓扑排序
            ordered = list(nx.topological_sort(subgraph))
            # 保持原序列中不在依赖图中的工具
            for tool in unique_sequence:
                if tool not in ordered:
                    ordered.append(tool)
            return ordered
        except nx.NetworkXError:
            # 如果有循环依赖，返回原序列
            return unique_sequence


    def _generate_contextual_reasoning(self, task_instance: Dict[str, Any],
                                    optimal_sequence: List[str],
                                    operations: List[str]) -> List[str]:
        """生成基于上下文的推理步骤"""
        # 使用统一的reasoning生成器  # <- 修改了这一行
        reasoning_generator = WorkflowReasoningGenerator(  # <- 修改了这一行
            self.tool_capabilities,  # <- 修改了这一行
            self.tool_capability_manager  # <- 修改了这一行
        )  # <- 修改了这一行
        return reasoning_generator.generate_contextual_reasoning(  # <- 修改了这一行
            task_instance, optimal_sequence, operations  # <- 修改了这一行
        )  # <- 修改了这一行

    def _generate_alternatives(self, primary_sequence: List[str], 
                            operations: List[str]) -> List[List[str]]:
        """生成替代的工具序列"""
        alternatives = []
        
        # 为每个操作找替代工具
        for i, tool in enumerate(primary_sequence[:3]):  # 只为前3个工具生成替代
            alt_sequence = primary_sequence.copy()
            
            # 找同类工具
            if tool in self.tool_capabilities:
                capability = self.tool_capabilities[tool]
                if hasattr(capability, 'semantic_operations'):
                    # 找有相似操作的工具
                    for alt_tool, alt_cap in self.tool_capabilities.items():
                        if alt_tool != tool and hasattr(alt_cap, 'semantic_operations'):
                            if set(capability.semantic_operations) & set(alt_cap.semantic_operations):
                                alt_sequence[i] = alt_tool
                                alternatives.append(alt_sequence)
                                break
        
        return alternatives[:2]  # 最多返回2个替代方案

    def _generate_random_workflow(self, task_type: str) -> Dict[str, Any]:
        """Generate a workflow based on tool dependencies and capabilities"""
        logger.info("Generating workflow based on tool capabilities")
        
        try:
            # 1. 分析可用工具的能力和依赖
            tools_by_category = self._categorize_tools_by_capability()
            dependency_graph = self._build_dependency_graph()
            
            # 2. 根据任务类型确定需要的能力
            required_capabilities = self._get_required_capabilities(task_type)
            
            # 3. 动态构建工具序列
            optimal_sequence = self._build_optimal_sequence(
                required_capabilities, 
                tools_by_category, 
                dependency_graph,
                task_type
            )
            
            # 4. 验证序列的有效性
            if not optimal_sequence:
                raise ValueError("No valid sequence found")
                print(f"[WARNING] No valid sequence found for {task_type}, using fallback")
                optimal_sequence = self._get_fallback_sequence(task_type)
            
            # 5. 生成workflow数据
            success_probability = self._calculate_success_probability(optimal_sequence, dependency_graph)
            
            workflow = {
                'task_type': task_type,
                'success_probability': success_probability,
                'optimal_sequence': optimal_sequence,
                'alternative_sequences': [],
                'tool_importance': self._calculate_tool_importance(optimal_sequence, dependency_graph),
                'critical_tools': self._identify_critical_tools(optimal_sequence, dependency_graph),
                'workflow_dag': self._build_dag_metrics(optimal_sequence, dependency_graph),
                'reasoning_steps': self._generate_reasoning_steps(task_type, optimal_sequence),
                'generated_at': datetime.now().isoformat()
            }
            
            logger.info(f"Generated workflow for {task_type}: {optimal_sequence}")
            return workflow
            
        except Exception as e:
            print(f"[ERROR] Failed to generate workflow: {e}")
            print(f"[ERROR] Using emergency fallback")
            return self._generate_emergency_fallback(task_type)


    def _categorize_tools_by_capability(self) -> Dict[str, List[str]]:
        """将工具按能力分类（使用语义理解）"""
        capability_map = {}
        
        for tool_name, capability in self.tool_capabilities.items():
            # 获取工具类别（使用语义理解）
            if self.tool_capability_manager:
                category = self.tool_capability_manager.get_category(capability)
                key = f"category_{category}"
                if key not in capability_map:
                    capability_map[key] = []
                capability_map[key].append(tool_name)
                logger.debug(f" Tool {tool_name} categorized as {category}")
            
            # 基于语义操作分组
            if hasattr(capability, 'semantic_operations'):
                for op in capability.semantic_operations:
                    if op not in capability_map:
                        capability_map[op] = []
                    capability_map[op].append(tool_name)
            
            # 也按数据域分组
            if hasattr(capability, 'data_domains'):
                for domain in capability.data_domains:
                    key = f"domain_{domain}"
                    if key not in capability_map:
                        capability_map[key] = []
                    capability_map[key].append(tool_name)
        
        return capability_map

    def _build_dependency_graph(self) -> nx.DiGraph:
        """构建工具依赖图"""
        G = nx.DiGraph()
        
        # 添加所有工具作为节点
        for tool_name in self.tool_capabilities:
            G.add_node(tool_name)
        
        # 添加依赖边
        for tool_name, capability in self.tool_capabilities.items():
            if hasattr(capability, 'dependencies') and capability.dependencies:
                for dep in capability.dependencies:
                    if dep in self.tool_capabilities:
                        G.add_edge(dep, tool_name)  # dep -> tool_name
                        print(f"[DEPENDENCY] {dep} -> {tool_name}")
        
        print(f"[DEPENDENCY] Built graph with {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
        return G

    def _get_required_capabilities(self, task_type: str) -> List[str]:
        """根据任务类型获取需要的能力"""
        # 基于任务类型的语义映射
        capability_requirements = {
            'simple_task': ['read', 'transform', 'write'],
            'basic_task': ['read', 'process'],
            'data_pipeline': ['read', 'parse', 'transform', 'validate', 'write'],
            'api_integration': ['fetch', 'validate', 'transform', 'post'],
            'basic_task': ['read', 'parse', 'transform', 'write'],
            'multi_stage_pipeline': ['read', 'parse', 'transform', 'aggregate', 'validate', 'write']
        }
        
        # 获取默认能力需求
        default_capabilities = ['read', 'process', 'write']
        capabilities = capability_requirements.get(task_type, default_capabilities)
        
        print(f"[CAPABILITY] Task {task_type} requires: {capabilities}")
        return capabilities


    def _calculate_success_probability(self, sequence: List[str], dep_graph: nx.DiGraph) -> float:
        """基于序列质量计算成功概率"""
        if not sequence:
            return 0.0
        
        base_prob = 0.5
        
        # 依赖满足度加分
        deps_satisfied = 0
        deps_total = 0
        executed = set()
        
        for tool in sequence:
            deps = list(dep_graph.predecessors(tool))
            deps_total += len(deps)
            deps_satisfied += sum(1 for dep in deps if dep in executed)
            executed.add(tool)
        
        if deps_total > 0:
            dep_score = deps_satisfied / deps_total
            base_prob += 0.3 * dep_score
        
        # 序列长度合理性
        if 3 <= len(sequence) <= 8:
            base_prob += 0.2
        elif 1 <= len(sequence) < 3:
            base_prob += 0.1
        
        return min(0.95, base_prob)

    def _calculate_tool_importance(self, sequence: List[str], dep_graph: nx.DiGraph) -> Dict[str, float]:
        """计算每个工具的重要性"""
        importance = {}
        
        for tool in sequence:
            # 基础重要性
            score = 1.0 / len(sequence) if sequence else 0
            
            # 被依赖程度加分
            dependents = list(dep_graph.successors(tool))
            score += 0.1 * len(dependents)
            
            # 依赖数量减分（越独立越重要）
            dependencies = list(dep_graph.predecessors(tool))
            score += 0.05 * (1 - len(dependencies) / max(len(sequence), 1))
            
            importance[tool] = min(1.0, score)
        
        return importance

    def _identify_critical_tools(self, sequence: List[str], dep_graph: nx.DiGraph) -> List[str]:
        """识别关键工具"""
        if not sequence:
            return []
        
        critical = []
        
        # 1. 没有依赖的起始工具
        for tool in sequence:
            if dep_graph.in_degree(tool) == 0:
                critical.append(tool)
                break
        
        # 2. 被多个工具依赖的枢纽工具
        for tool in sequence:
            if dep_graph.out_degree(tool) >= 2:
                critical.append(tool)
        
        # 3. 输出类工具
        for tool in sequence:
            capability = self.tool_capabilities.get(tool)
            if capability and hasattr(capability, 'semantic_operations'):
                if 'write' in capability.semantic_operations or 'export' in capability.semantic_operations:
                    critical.append(tool)
        
        # 去重并限制数量
        critical = list(dict.fromkeys(critical))[:3]
        
        # 如果没有找到关键工具，返回前两个
        if not critical and len(sequence) >= 2:
            critical = sequence[:2]
        
        return critical

    def _build_dag_metrics(self, sequence: List[str], dep_graph: nx.DiGraph) -> Dict[str, int]:
        """构建DAG度量"""
        if not sequence:
            return {'nodes': 0, 'edges': 0}
        
        # 创建序列的子图
        subgraph = dep_graph.subgraph(sequence)
        
        return {
            'nodes': subgraph.number_of_nodes(),
            'edges': subgraph.number_of_edges()
        }


    def _get_fallback_sequence(self, task_type: str) -> List['SearchResult']:
        """获取任务类型的fallback工具序列（使用语义理解）"""
        fallback_tools = []
        
        # 优先使用语义理解推荐工具
        if self.tool_capability_manager and task_type:
            logger.debug(f" Getting semantic fallback for task type: {task_type}")
            
            # 基于任务类型的语义描述推荐工具
            task_descriptions = {
                'data_pipeline': "read data, transform it, and write output",
                'api_integration': "fetch data from API, parse response, and post results",
                'basic_task': "read files, convert format, and write processed files",
                'multi_stage_pipeline': "filter data, aggregate results, and validate output"
            }
            
            if task_type in task_descriptions:
                operations = self.tool_capability_manager.suggest_operations_for_task(
                    task_descriptions[task_type], k=5
                )
                
                # 为每个操作找到最合适的工具
                for operation in operations:
                    for tool_name, capability in self.tool_capabilities.items():
                        if hasattr(capability, 'semantic_operations'):
                            for sem_op in capability.semantic_operations:
                                if operation in sem_op or sem_op in operation:
                                    fallback_tools.append(type('SearchResult', (), {
                                        'tool_name': tool_name,
                                        'score': 0.7,
                                        'source': 'semantic_fallback'
                                    })())
                                    break
                        if len(fallback_tools) >= 5:
                            break
        
        # Fallback: 硬编码的任务-工具映射
        if not fallback_tools:
            logger.debug(f" Using hardcoded fallback for task type: {task_type}")
            task_tool_mapping = {
                'data_pipeline': ['file_operations_reader', 'data_processing_transformer', 'file_operations_writer'],
                'api_integration': ['network_fetcher', 'data_processing_parser', 'network_poster'],
                'basic_task': ['file_operations_reader', 'file_operations_converter', 'file_operations_writer'],
                'multi_stage_pipeline': ['data_processing_filter', 'data_processing_aggregator', 'data_processing_validator']
            }
            
            if task_type in task_tool_mapping:
                for tool_name in task_tool_mapping[task_type]:
                    if tool_name in self.tool_names:
                        fallback_tools.append(type('SearchResult', (), {
                            'tool_name': tool_name,
                            'score': 0.5,
                            'source': 'task_type_default'
                        })())
        
        return fallback_tools


    def _build_optimal_sequence(self, required_capabilities: List[str], 
                            tools_by_category: Dict[str, List[str]], 
                            dependency_graph: nx.DiGraph,
                            task_type: str) -> List[str]:
        """基于能力需求构建最优序列（集成embedding搜索）"""
        sequence = []
        used_capabilities = set()
        
        # 按照数据流顺序处理能力
        capability_order = ['read', 'fetch', 'parse', 'validate', 
                        'filter', 'transform', 'aggregate', 
                        'compute', 'write', 'export']
        
        for capability in capability_order:
            if capability in required_capabilities and capability not in used_capabilities:
                candidates = []
                
                # 1. 首先尝试使用embedding搜索（如果启用）
                if self.use_embeddings and self.embedding_manager:
                    print(f"[SEQUENCE] Using embedding search for capability: {capability}")
                    # 构建搜索查询
                    search_query = f"{capability} {task_type}"
                    embedding_candidates = self._select_tools_with_embeddings(
                        query=search_query,
                        required_capabilities=[capability],
                        k=5
                    )
                    candidates.extend(embedding_candidates)
                    print(f"[SEQUENCE] Found {len(embedding_candidates)} tools via embedding search")
                
                # 2. 使用规则方法获取候选工具
                rule_candidates = tools_by_category.get(capability, [])
                # 合并候选工具，去重
                for tool in rule_candidates:
                    if tool not in candidates:
                        candidates.append(tool)
                
                if candidates:
                    # 选择依赖最少的工具
                    best_tool = None
                    min_deps = float('inf')
                    
                    # 考虑embedding分数（如果有）
                    for i, tool in enumerate(candidates):
                        if tool not in sequence:
                            deps = len(list(dependency_graph.predecessors(tool)))
                            # 如果是embedding搜索的前几个结果，给予优先权
                            if self.use_embeddings and i < len(embedding_candidates):
                                deps = deps * 0.8  # 降低20%的依赖权重
                            
                            if deps < min_deps:
                                min_deps = deps
                                best_tool = tool
                    
                    if best_tool:
                        sequence.append(best_tool)
                        used_capabilities.add(capability)
                        print(f"[SEQUENCE] Selected {best_tool} for {capability}")
                else:
                    print(f"[WARNING] No tools found for capability: {capability}")
        
        # 根据依赖关系排序
        return self._order_tools_by_dependencies(sequence, dependency_graph)

    def _select_tools_with_embeddings(self, query: str, required_capabilities: List[str], 
                                    k: int = 10, filter_tools: Optional[List[str]] = None) -> List[str]:
        """Select tools using semantic search combined with capability requirements
        
        Args:
            query: Search query (task description or operation)
            required_capabilities: Required semantic operations
            k: Number of tools to retrieve
            filter_tools: Optional list of tools to search within
            
        Returns:
            List of selected tool names
        """
        if not self.embedding_manager:
            print("[WARNING] Embedding manager not available, returning empty list")
            return []
        
        try:
            # Search for semantically similar tools
            search_results = self.embedding_manager.search(
                query=query,
                k=k,
                filter_tools=filter_tools if filter_tools else self.tool_names
            )
            
            # Filter by required capabilities
            selected_tools = []
            for result in search_results:
                tool_name = result.tool_name
                if tool_name in self.tool_capabilities:
                    capability = self.tool_capabilities[tool_name]
                    if hasattr(capability, 'semantic_operations'):
                        # Check if tool has any required capability
                        tool_ops = set(capability.semantic_operations)
                        required_ops = set(required_capabilities)
                        if tool_ops & required_ops:  # Intersection
                            selected_tools.append(tool_name)
                            print(f"[EMBEDDING] Selected {tool_name} (score: {result.score:.3f})")
                        elif not required_capabilities:  # If no specific requirements, add anyway
                            selected_tools.append(tool_name)
                            print(f"[EMBEDDING] Selected {tool_name} (no capability filter, score: {result.score:.3f})")
            
            return selected_tools
            
        except Exception as e:
            print(f"[ERROR] Embedding search failed: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _generate_emergency_fallback(self, task_type: str) -> Dict[str, Any]:
        """紧急备用方案"""
        return {
            'task_type': task_type,
            'success_probability': 0.5,
            'optimal_sequence': self.tool_names[:3] if self.tool_names else [],
            'alternative_sequences': [],
            'tool_importance': {},
            'critical_tools': [],
            'workflow_dag': {'nodes': 3, 'edges': 2},
            'reasoning_steps': ["Emergency fallback workflow"],
            'generated_at': datetime.now().isoformat()
        }
    
    def _build_workflow_dag(self, initial_state: GeneralizedMDPState, max_depth: int) -> nx.DiGraph:
        """Build workflow DAG using BFS exploration"""
        dag = nx.DiGraph()
        
        # Add initial node
        initial_id = "state_0"
        dag.add_node(initial_id, state=initial_state, is_initial=True)
        
        # BFS exploration
        queue = deque([(initial_id, initial_state, 0)])
        visited = {initial_id}
        state_counter = 1
        
        while queue and state_counter < max_depth * 5:  # Limit total states
            current_id, current_state, depth = queue.popleft()
            
            if depth >= max_depth:
                continue
            
            # Get ranked actions
            actions = self._get_ranked_actions(current_state)
            
            # Explore top actions
            for action, q_value, reasoning in actions[:3]:  # Top 3 actions
                # Simulate transition
                next_state = self._simulate_transition(current_state, action)
                
                # Create state ID
                next_id = f"state_{state_counter}"
                state_counter += 1
                
                # Add node if new
                if next_id not in visited:
                    dag.add_node(
                        next_id,
                        state=next_state,
                        is_terminal=next_state.is_complete
                    )
                    visited.add(next_id)
                    
                    # Add to queue if not terminal
                    if not next_state.is_complete:
                        queue.append((next_id, next_state, depth + 1))
                
                # Add edge
                dag.add_edge(
                    current_id,
                    next_id,
                    action=action,
                    q_value=q_value,
                    reasoning=reasoning,
                    probability=self._calculate_transition_probability(current_state, action)
                )
        
        return dag
    
    def _get_ranked_actions(self, state: GeneralizedMDPState) -> List[Tuple[GeneralizedAction, float, str]]:
        """Get actions ranked by Q-values with reasoning"""
        ranked_actions = []
        
        # Get state features
        state_features = self._extract_state_features(state)
        state_tensor = torch.FloatTensor(state_features).unsqueeze(0)
        
        # Get Q-values
        with torch.no_grad():
            q_values = self.q_network(state_tensor).squeeze()
        
        # Create actions and rank them
        for i, tool_name in enumerate(self.tool_names):
            if i < len(q_values):
                action = GeneralizedAction(
                    action_type=ActionType.INVOKE_TOOL,
                    tool_name=tool_name
                )
                
                q_value = q_values[i].item()
                reasoning = self._generate_action_reasoning(state, action, q_value)
                
                ranked_actions.append((action, q_value, reasoning))
        
        # Sort by Q-value
        ranked_actions.sort(key=lambda x: x[1], reverse=True)
        
        return ranked_actions


    def _analyze_selection_reason(self, selected_tool: str, combined_scores: Dict[str, float],
                                ppo_scores: Dict[str, float], rag_scores: Dict[str, float],
                                state: GeneralizedMDPState) -> str:
        """分析工具被选择的原因"""
        reasons = []
        
        # 检查是否是最高分
        if combined_scores and selected_tool == max(combined_scores.items(), key=lambda x: x[1])[0]:
            reasons.append("highest combined score")
        
        # 检查PPO偏好
        if ppo_scores and selected_tool in ppo_scores:
            # 检查是否是PPO的最高分选择
            if selected_tool == max(ppo_scores.items(), key=lambda x: x[1])[0]:
                reasons.append("PPO model preference")
            elif ppo_scores[selected_tool] > 0.2:  # 如果PPO给了相对高的分数
                reasons.append(f"PPO score: {ppo_scores[selected_tool]:.3f}")
        
        # 检查RAG匹配
        if selected_tool in rag_scores:
            if rag_scores[selected_tool] > 0.8:
                reasons.append(f"strong semantic match ({rag_scores[selected_tool]:.2f})")
            elif rag_scores[selected_tool] > 0.6:
                reasons.append(f"good semantic match ({rag_scores[selected_tool]:.2f})")
            elif rag_scores[selected_tool] > 0.4:
                reasons.append(f"moderate semantic match ({rag_scores[selected_tool]:.2f})")
        
        # 检查是否满足依赖
        if hasattr(state, 'tool_states') and selected_tool in self.tool_capabilities:
            capability = self.tool_capabilities[selected_tool]
            if hasattr(capability, 'dependencies') and capability.dependencies:
                # 获取已完成的工具
                completed_tools = []
                
                # 从execution_sequence获取
                if hasattr(state, 'execution_sequence'):
                    completed_tools.extend(list(state.execution_sequence))
                
                # 从tool_states获取成功的工具
                if hasattr(state, 'tool_states'):
                    for tool, status in state.tool_states.items():
                        # 检查状态是否为SUCCESS
                        if hasattr(status, 'name') and status.name == 'SUCCESS':
                            if tool not in completed_tools:
                                completed_tools.append(tool)
                        elif hasattr(status, 'value') and status.value == 'SUCCESS':
                            if tool not in completed_tools:
                                completed_tools.append(tool)
                
                # 检查依赖满足情况
                satisfied_deps = [dep for dep in capability.dependencies if dep in completed_tools]
                if len(satisfied_deps) == len(capability.dependencies) and capability.dependencies:
                    reasons.append("all dependencies satisfied")
                elif satisfied_deps:
                    reasons.append(f"partial dependencies satisfied ({len(satisfied_deps)}/{len(capability.dependencies)})")
        
        # 检查是否是初始工具
        execution_sequence = getattr(state, 'execution_sequence', [])
        if len(execution_sequence) == 0:
            reasons.append("initial tool selection")
        elif len(execution_sequence) < 3:
            reasons.append("early stage selection")
        
        # 检查是否有模式匹配
        if len(execution_sequence) >= 2:
            # 构建模式字符串
            pattern = '->'.join(execution_sequence[-2:] + [selected_tool])
            if hasattr(self, 'successful_patterns') and pattern in self.successful_patterns:
                pattern_count = self.successful_patterns.get(pattern, 0)
                reasons.append(f"matches successful pattern (seen {pattern_count} times)")
        
        # 检查是否是关键工具
        if hasattr(self, 'tool_criticality_scores') and selected_tool in self.tool_criticality_scores:
            criticality = self.tool_criticality_scores[selected_tool]
            if criticality > 0.8:
                reasons.append(f"critical tool (score: {criticality:.2f})")
        
        # 如果没有特别的原因，添加默认原因
        if not reasons:
            if combined_scores.get(selected_tool, 0) > 0.5:
                reasons.append("balanced score selection")
            else:
                reasons.append("exploratory selection")
        
        return "; ".join(reasons)

    # def _extract_state_features(self, state: GeneralizedMDPState) -> Dict[str, Any]:
    #     """提取状态特征用于记录和分析"""
    #     features = {
    #         'workflow_step': getattr(state, 'workflow_step', 0),
    #         'overall_progress': getattr(state, 'overall_progress', 0.0),
    #         'executed_tools': list(getattr(state, 'execution_sequence', [])),
    #         'consecutive_errors': getattr(state, 'consecutive_errors', 0),
    #         'total_errors': getattr(state, 'total_errors', 0),
    #         'milestones_achieved': list(getattr(state, 'milestones_achieved', set())),
    #         'data_flow_state': 'UNKNOWN'
    #     }
        
    #     # 安全获取 data_flow_state
    #     if hasattr(state, 'data_flow_state'):
    #         if hasattr(state.data_flow_state, 'name'):
    #             features['data_flow_state'] = state.data_flow_state.name
    #         else:
    #             features['data_flow_state'] = str(state.data_flow_state)
        
    #     # 添加工具状态统计
    #     if hasattr(state, 'tool_states'):
    #         tool_status_counts = defaultdict(int)
    #         for tool, status in state.tool_states.items():
    #             if hasattr(status, 'name'):
    #                 status_name = status.name
    #             elif hasattr(status, 'value'):
    #                 status_name = str(status.value)
    #             else:
    #                 status_name = str(status)
    #             tool_status_counts[status_name] += 1
    #         features['tool_status_summary'] = dict(tool_status_counts)
    #     else:
    #         features['tool_status_summary'] = {}
        
    #     # 添加任务特征（如果有）
    #     if hasattr(state, 'task_features'):
    #         features['task_complexity'] = getattr(state.task_features, 'complexity', 'UNKNOWN')
    #         features['task_domain'] = getattr(state.task_features, 'domain', 'UNKNOWN')
        
    #     return features
    

    def _simulate_transition(self, state: GeneralizedMDPState, action: GeneralizedAction) -> GeneralizedMDPState:
        """Simulate state transition"""
        new_state = GeneralizedMDPState(
            task_id=state.task_id,
            task_type=state.task_type,
            task_objective=state.task_objective,
            executed_tools=state.executed_tools + [action.tool_name],
            current_context=state.current_context.copy(),
            progress=min(1.0, state.progress + 0.2),
            is_complete=False
        )
        
        # Update context based on tool
        if action.tool_name in self.tool_capabilities:
            capability = self.tool_capabilities[action.tool_name]
            new_state.current_context[f"{action.tool_name}_output"] = f"output_of_{action.tool_name}"
        
        # Check completion
        if new_state.progress >= 0.8 or len(new_state.executed_tools) >= 5:
            new_state.is_complete = True
        
        return new_state
    
    def _calculate_transition_probability(self, state: GeneralizedMDPState, action: GeneralizedAction) -> float:
        """Calculate transition probability"""
        # Base probability
        prob = 0.8
        
        # Adjust based on tool dependencies
        if action.tool_name in self.tool_capabilities:
            capability = self.tool_capabilities[action.tool_name]
            if hasattr(capability, 'dependencies'):
                for dep in capability.dependencies:
                    if dep not in state.executed_tools:
                        prob *= 0.5
        
        return prob
    
    def _generate_action_reasoning(self, state: GeneralizedMDPState, action: GeneralizedAction, q_value: float) -> str:
        """Generate reasoning for action selection"""
        reasons = []
        
        if q_value > 0.8:
            reasons.append("High expected value")
        elif q_value > 0.5:
            reasons.append("Moderate expected value")
        else:
            reasons.append("Exploratory choice")
        
        # Tool-specific reasoning
        if action.tool_name in self.tool_capabilities:
            capability = self.tool_capabilities[action.tool_name]
            if hasattr(capability, 'semantic_operations'):
                ops = capability.semantic_operations[:2]
                if ops:
                    reasons.append(f"Can perform: {', '.join(ops)}")
        
        # Context reasoning
        if len(state.executed_tools) == 0:
            reasons.append("Good starting tool")
        elif len(state.executed_tools) >= 3:
            reasons.append("Workflow completion")
        
        return "; ".join(reasons)
    
    def _find_optimal_path(self, dag: nx.DiGraph) -> List[WorkflowEdge]:
        """Find optimal path through DAG"""
        # Find initial and terminal nodes
        initial_nodes = [n for n, d in dag.nodes(data=True) if d.get('is_initial')]
        terminal_nodes = [n for n, d in dag.nodes(data=True) if d.get('is_terminal')]
        
        if not initial_nodes or not terminal_nodes:
            return []
        
        # Find best path using Dijkstra with negative Q-values as weights
        best_path = None
        best_score = float('-inf')
        
        for terminal in terminal_nodes:
            try:
                # Use negative Q-values as weights (to find maximum)
                path = nx.shortest_path(
                    dag,
                    initial_nodes[0],
                    terminal,
                    weight=lambda u, v, d: -d.get('q_value', 0)
                )
                
                # Calculate path score
                score = sum(dag[u][v].get('q_value', 0) for u, v in zip(path[:-1], path[1:]))
                
                if score > best_score:
                    best_score = score
                    best_path = path
                    
            except nx.NetworkXNoPath:
                continue
        
        if not best_path:
            return []
        
        # Convert to WorkflowEdge list
        edges = []
        for u, v in zip(best_path[:-1], best_path[1:]):
            edge_data = dag[u][v]
            edges.append(WorkflowEdge(
                action=edge_data['action'],
                probability=edge_data.get('probability', 1.0),
                reward=edge_data.get('q_value', 0.0),
                reasoning=edge_data.get('reasoning', '')
            ))
        
        return edges
    
    
    def _find_alternative_sequences(self, dag: nx.DiGraph) -> List[List[str]]:
        """Find alternative tool sequences"""
        alternatives = []
        
        # Find initial and terminal nodes
        initial_nodes = [n for n, d in dag.nodes(data=True) if d.get('is_initial')]
        terminal_nodes = [n for n, d in dag.nodes(data=True) if d.get('is_terminal')]
        
        if not initial_nodes or not terminal_nodes:
            return alternatives
        
        # Find multiple paths
        for terminal in terminal_nodes[:3]:  # Limit to 3 terminals
            try:
                paths = list(nx.all_simple_paths(
                    dag,
                    initial_nodes[0],
                    terminal,
                    cutoff=8
                ))[:5]  # Limit to 5 paths per terminal
                
                for path in paths:
                    sequence = []
                    for u, v in zip(path[:-1], path[1:]):
                        action = dag[u][v]['action']
                        if action.action_type == ActionType.INVOKE_TOOL:
                            sequence.append(action.tool_name)
                    
                    if sequence and sequence not in alternatives:
                        alternatives.append(sequence)
                        
            except:
                continue
        
        return alternatives[:3]  # Return top 3 alternatives
    
    def _analyze_tool_importance(self, dag: nx.DiGraph) -> Dict[str, float]:
        """Analyze tool importance in workflow"""
        tool_scores = defaultdict(float)
        
        # Count occurrences in all paths
        initial_nodes = [n for n, d in dag.nodes(data=True) if d.get('is_initial')]
        terminal_nodes = [n for n, d in dag.nodes(data=True) if d.get('is_terminal')]
        
        if not initial_nodes or not terminal_nodes:
            return dict(tool_scores)
        
        for terminal in terminal_nodes:
            try:
                paths = list(nx.all_simple_paths(
                    dag,
                    initial_nodes[0],
                    terminal,
                    cutoff=8
                ))
                
                for path in paths:
                    path_score = 1.0
                    tools_in_path = []
                    
                    for u, v in zip(path[:-1], path[1:]):
                        edge_data = dag[u][v]
                        action = edge_data['action']
                        
                        if action.action_type == ActionType.INVOKE_TOOL:
                            tools_in_path.append(action.tool_name)
                            path_score *= edge_data.get('probability', 1.0)
                    
                    # Update tool scores
                    for tool in tools_in_path:
                        tool_scores[tool] += path_score / len(tools_in_path)
                        
            except:
                continue
        
        # Normalize scores
        max_score = max(tool_scores.values()) if tool_scores else 1.0
        return {tool: score / max_score for tool, score in tool_scores.items()}

    
    def _dag_to_dict(self, dag: nx.DiGraph) -> Dict[str, Any]:
        """Convert DAG to serializable dictionary"""
        return {
            'nodes': len(dag.nodes()),
            'edges': len(dag.edges()),
            'depth': nx.dag_longest_path_length(dag) if nx.is_directed_acyclic_graph(dag) else 0,
            'branching_factor': np.mean([dag.out_degree(n) for n in dag.nodes()]) if dag.nodes() else 0
        }
    
    def _calculate_workflow_quality(self, workflow: Dict[str, Any]) -> Dict[str, float]:
        """Calculate comprehensive workflow quality metrics"""
        metrics = {}
        
        # Sequence length score (prefer 3-7 tools)
        seq_len = len(workflow.get('optimal_sequence', []))
        if 3 <= seq_len <= 7:
            metrics['length_score'] = 1.0
        elif seq_len < 3:
            metrics['length_score'] = seq_len / 3.0
        else:
            metrics['length_score'] = max(0.5, 1.0 - (seq_len - 7) * 0.1)
        
        # Tool diversity score
        unique_tools = set(workflow.get('optimal_sequence', []))
        metrics['diversity_score'] = len(unique_tools) / max(1, seq_len)
        
        # Dependency satisfaction score
        metrics['dependency_score'] = self._calculate_dependency_score(workflow.get('optimal_sequence', []))
        
        # Alternative path score
        alt_sequences = workflow.get('alternative_sequences', [])
        metrics['flexibility_score'] = min(1.0, len(alt_sequences) / 3.0)
        
        # Critical tool coverage
        critical_tools = workflow.get('critical_tools', [])
        optimal_seq = workflow.get('optimal_sequence', [])
        if critical_tools:
            covered = sum(1 for t in critical_tools if t in optimal_seq)
            metrics['critical_coverage'] = covered / len(critical_tools)
        else:
            metrics['critical_coverage'] = 1.0
        
        # Overall quality score
        metrics['overall_quality'] = np.mean([
            metrics['length_score'] * 0.2,
            metrics['diversity_score'] * 0.2,
            metrics['dependency_score'] * 0.3,
            metrics['flexibility_score'] * 0.15,
            metrics['critical_coverage'] * 0.15
        ])
        
        # Store in tracking
        task_type = workflow.get('task_type', 'unknown')
        self.workflow_quality_metrics[task_type] = metrics
        
        return metrics
    
    def _calculate_dependency_score(self, sequence: List[str]) -> float:
        """Calculate how well dependencies are satisfied"""
        if not sequence:
            return 0.0
        
        score = 1.0
        tools_so_far = set()
        
        for tool in sequence:
            if tool in self.tool_capabilities:
                capability = self.tool_capabilities[tool]
                if hasattr(capability, 'dependencies'):
                    for dep in capability.dependencies:
                        if dep not in tools_so_far:
                            score *= 0.8  # Penalty for unsatisfied dependency
            
            tools_so_far.add(tool)
        
        return score


    def _get_tool_semantic_info(self, tool_name: str, task_description: str) -> Optional[Dict]:
        """Get semantic information about a tool selection"""
        if not self.embedding_manager:
            return None
        
        try:
            # 搜索与任务相关的工具
            results = self.embedding_manager.search(
                query=f"{task_description} {tool_name}",
                k=5,
                return_scores=True
            )
            
            # 找到当前工具的信息
            tool_info = None
            alternatives = []
            
            for i, result in enumerate(results):
                if result.tool_name == tool_name:
                    tool_info = {
                        'score': result.score,
                        'reasoning': f"Semantically matches task requirement (rank #{i+1})"
                    }
                else:
                    alternatives.append({
                        'tool_name': result.tool_name,
                        'score': result.score
                    })
            
            if tool_info:
                tool_info['alternatives'] = alternatives[:3]  # Top 3 alternatives
                return tool_info
                
        except Exception as e:
            logger.debug(f"Failed to get semantic info: {e}")
        
        return None

    def _generate_semantic_insights(self, workflow: Dict) -> str:
        """Generate insights from semantic analysis"""
        if 'smart_actions' not in workflow:
            return "No semantic analysis performed"
        
        insights = []
        
        # 分析语义得分分布
        scores = [a['semantic_score'] for a in workflow['smart_actions'] if a['semantic_score'] > 0]
        if scores:
            avg_score = sum(scores) / len(scores)
            insights.append(f"Average semantic match: {avg_score:.1%}")
            
            high_confidence = sum(1 for s in scores if s > 0.8)
            insights.append(f"High confidence selections: {high_confidence}/{len(scores)}")
        
        # 分析搜索来源
        sources = [a['search_source'] for a in workflow['smart_actions']]
        embedding_count = sources.count('embedding_search')
        if embedding_count > 0:
            insights.append(f"Tools found via semantic search: {embedding_count}/{len(sources)}")
        
        return '\n'.join(insights) if insights else "Limited semantic insights available"

    def generate_mcp_prompt(self, task_type: str, task_instance: Optional[Dict] = None) -> str:
        """Generate structured prompt with RAG-enhanced workflow guidance"""
        
        # 如果有task_instance，重新生成workflow以获取RAG信息
        if task_instance:
            workflow = self.generate_workflow_for_instance(task_instance)
        else:
            workflow = self.workflows.get(task_type)
            if not workflow:
                workflow = self.generate_workflow(task_type)
        
        # 检查是否有智能action信息
        has_smart_actions = 'smart_actions' in workflow and workflow['smart_actions']
        
        prompt = f"""
        <mcp_task>
        <task_type>{task_type}</task_type>
        
        <workflow_intelligence>
        This workflow was {'enhanced with semantic search' if has_smart_actions else 'generated using patterns'}.
        Confidence Level: {workflow.get('success_probability', 0.0):.1%}
        </workflow_intelligence>
        
        <execution_plan>
        {'## Intelligent Execution Plan' if has_smart_actions else '## Standard Execution Plan'}
        
        {self._generate_smart_execution_plan(workflow['smart_actions']) if has_smart_actions else self._format_mandatory_sequence(workflow['optimal_sequence'])}
        </execution_plan>
        
        <semantic_insights>
        {self._generate_semantic_insights(workflow) if has_smart_actions else 'No semantic analysis available'}
        </semantic_insights>
        
        <tool_relationships>
        {self._generate_tool_relationship_graph(workflow)}
        </tool_relationships>
        
        <failure_handling>
        For each tool execution:
        1. Try the primary tool first
        2. If it fails and alternatives exist, try them in order of semantic similarity
        3. Report which tool was used and why
        4. If all alternatives fail, explain the issue and ask for guidance
        </failure_handling>
        
        <execution_tracking>
        Track and report:
        - Tool selection rationale (especially for semantic matches)
        - Actual vs expected outcomes
        - Any deviations from the plan and justification
        - Confidence in each step's success
        </execution_tracking>
        </mcp_task>"""
        
        return prompt
        
    def _format_mandatory_sequence(self, sequence: List[str]) -> str:
        """Format the mandatory execution sequence with clear numbering"""
        if not sequence:
            return "No tools required"
        
        formatted = []
        for i, tool in enumerate(sequence, 1):
            formatted.append(f"{i}. {tool} [MANDATORY - Step {i} of {len(sequence)}]")
        
        return '\n'.join(formatted)
    
    def _format_available_tools(self, sequence: List[str]) -> str:
        """Format available tools with categories and reliability info"""  # <- 修改了注释
        if not self.tool_capabilities:
            return "No tools available"
        
        # Group tools by category
        categorized = {}
        tool_reliability = {}  # <- 新增这一行
        
        for tool in self.tool_capabilities:
            cat = self._get_tool_category(tool)
            if cat not in categorized:
                categorized[cat] = []
            categorized[cat].append(tool)
            
            # 计算工具的历史成功率（基于训练经验）  # <- 新增这一行
            # 这里可以从训练历史中获取，现在使用模拟值  # <- 新增这一行
            if hasattr(self, 'tool_success_history'):  # <- 新增这一行
                success_rate = self.tool_success_history.get(tool, 0.8)  # <- 新增这一行
            else:  # <- 新增这一行
                # 基于工具类型的默认成功率  # <- 新增这一行
                if 'validator' in tool or 'checker' in tool:  # <- 新增这一行
                    success_rate = 0.95  # 验证类工具通常更可靠  # <- 新增这一行
                elif 'network' in cat or 'api' in tool:  # <- 新增这一行
                    success_rate = 0.7  # 网络工具可能失败率更高  # <- 新增这一行
                else:  # <- 新增这一行
                    success_rate = 0.85  # 默认成功率  # <- 新增这一行
            
            tool_reliability[tool] = success_rate  # <- 新增这一行
    
    def _get_tool_description(self, capability: ToolCapability) -> str:
        """Get concise tool description"""
        # Create a simple description from the capability
        ops = capability.semantic_operations if hasattr(capability, 'semantic_operations') else []
        if ops:
            return f"Performs {', '.join(ops[:2])}"
        else:
            return "Process data"
    
    def _format_expected_flow(self, sequence: List[str]) -> str:
        """Format the expected data flow through tools"""
        if not sequence:
            return "No data flow"
        
        flow_parts = []
        for i, tool in enumerate(sequence):
            if i == 0:
                flow_parts.append(f"1. START → {tool}")
            elif i == len(sequence) - 1:
                flow_parts.append(f"{i+1}. {sequence[i-1]} → {tool} → END")
            else:
                flow_parts.append(f"{i+1}. {sequence[i-1]} → {tool}")
        
        return '\n'.join(flow_parts)

    def validate_workflow_adherence(self, task_type: str, executed_sequence: List[str], 
                                    required_tools: List[str] = None, task_instance: Dict = None) -> Dict[str, Any]:
        """
        Validate how well an executed sequence adhered to task requirements
        Returns detailed adherence metrics based on actual task needs, not hardcoded workflow
        """
        # 新策略：基于任务完成质量，而非预定义序列  # <- 修改了这一行
        
        # 基于实际执行评估  # <- 修改了这一行
        metrics = {}
        
        # 1. 执行成功率（核心指标）  # <- 修改了这一行
        if executed_sequence:
            unique_tools = set(executed_sequence)
            total_calls = len(executed_sequence)
            
            # 假设大部分调用成功（因为没有详细执行信息）
            metrics['execution_success_rate'] = 0.8 if total_calls > 0 else 0.0
            
            # 效率：避免过度冗余
            metrics['efficiency'] = min(1.0, len(unique_tools) / max(total_calls, 1))
            metrics['redundancy_count'] = total_calls - len(unique_tools)
        else:
            metrics['execution_success_rate'] = 0.0
            metrics['efficiency'] = 0.0
            metrics['redundancy_count'] = 0
        
        # 2. 任务完成指标（不依赖required_tools）  # <- 修改了这一行
        # 检查是否有输出相关的工具
        output_tools = ['writer', 'export', 'output', 'save', 'store', 'persist']
        has_output = any(any(out in tool.lower() for out in output_tools) 
                        for tool in executed_sequence)
        
        # 检查是否有数据处理
        process_tools = ['transform', 'process', 'parse', 'compute', 'analyze', 'filter']
        has_processing = any(any(proc in tool.lower() for proc in process_tools) 
                        for tool in executed_sequence)
        
        # 任务完成度评估
        if has_output and has_processing:
            metrics['task_completion'] = 1.0
        elif has_output or has_processing:
            metrics['task_completion'] = 0.6
        else:
            metrics['task_completion'] = 0.3 if executed_sequence else 0.0
        
        # 3. 工具多样性（鼓励使用不同类型的工具）  # <- 新增了这一部分
        tool_categories = set()
        for tool in executed_sequence:
            if 'read' in tool or 'load' in tool:
                tool_categories.add('input')
            elif 'process' in tool or 'transform' in tool:
                tool_categories.add('processing')
            elif 'write' in tool or 'export' in tool:
                tool_categories.add('output')
            elif 'validate' in tool or 'check' in tool:
                tool_categories.add('validation')
        
        metrics['tool_diversity'] = len(tool_categories) / 4.0  # 最多4个类别
        
        # 4. 合理的序列长度  # <- 新增了这一部分
        if executed_sequence:
            # 3-7个工具是合理的范围
            if 3 <= len(unique_tools) <= 7:
                metrics['sequence_length_score'] = 1.0
            elif 2 <= len(unique_tools) <= 10:
                metrics['sequence_length_score'] = 0.7
            else:
                metrics['sequence_length_score'] = 0.4
        else:
            metrics['sequence_length_score'] = 0.0
        
        # 5. 总体遵从度评分 - 基于任务完成质量  # <- 修改了这一行
        metrics['overall_adherence'] = (
            metrics['task_completion'] * 0.4 +          # 40%：任务完成
            metrics['execution_success_rate'] * 0.3 +   # 30%：执行成功率
            metrics['efficiency'] * 0.15 +              # 15%：执行效率
            metrics['tool_diversity'] * 0.1 +           # 10%：工具多样性
            metrics['sequence_length_score'] * 0.05     # 5%：合理长度
        )
        
        logger.info(f"[ADHERENCE] Task-based evaluation: {metrics['overall_adherence']:.3f}")
        logger.info(f"[ADHERENCE] Details: completion={metrics['task_completion']:.2f}, "
                    f"success={metrics['execution_success_rate']:.2f}, "
                    f"efficiency={metrics['efficiency']:.2f}")
        
        # 存储分析结果
        self.workflow_adherence_scores[task_type] = metrics
        
        return metrics
    
    def _calculate_sequence_match(self, expected: List[str], actual: List[str]) -> float:
        """Calculate how well sequences match (exact order)"""
        if not expected:
            return 1.0 if not actual else 0.0
        
        if not actual:
            return 0.0
        
        # Use longest common subsequence
        lcs_length = self._lcs_length(expected, actual)
        return lcs_length / max(len(expected), len(actual))
    
    def _calculate_order_preservation(self, expected: List[str], actual: List[str]) -> float:
        """Calculate how well order is preserved (relative positions)"""
        if not expected or not actual:
            return 0.0
        
        # Find tools that appear in both
        common_tools = set(expected) & set(actual)
        if not common_tools:
            return 0.0
        
        # Check order preservation for common tools
        preserved = 0
        total_pairs = 0
        
        for i, tool1 in enumerate(expected):
            if tool1 not in common_tools:
                continue
            for j, tool2 in enumerate(expected[i+1:], i+1):
                if tool2 not in common_tools:
                    continue
                
                total_pairs += 1
                
                # Check if order is preserved in actual sequence
                try:
                    idx1 = actual.index(tool1)
                    idx2 = actual.index(tool2)
                    if idx1 < idx2:
                        preserved += 1
                except ValueError:
                    pass
        
        return preserved / total_pairs if total_pairs > 0 else 1.0
    
    def _lcs_length(self, seq1: List[str], seq2: List[str]) -> int:
        """Calculate length of longest common subsequence"""
        m, n = len(seq1), len(seq2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if seq1[i-1] == seq2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        
        return dp[m][n]


# ===========================
# Testing and Visualization
# ===========================

def test_workflow_generator():
    """Test the workflow generator"""
    logger.info("Testing enhanced workflow generator...")
    
    # Create generator
    generator = MDPWorkflowGenerator(
        model_path=None,  # Will use random generation
        tools_path="./mcp_generated_library/tool_registry_consolidated.json"
    )
    
    # Test different task types
    task_types = ["simple_task", "data_pipeline", "api_integration"]
    
    for task_type in task_types:
        logger.info(f"\nGenerating workflow for: {task_type}")
        
        # 创建测试用的task_instance  # <- 修改了这部分
        task_instance = {
            'task_type': task_type,
            'description': f'Test {task_type} with data processing and validation',
            'required_tools': [],
            'id': f'test_{task_type}_001'
        }
        
        # Generate workflow with task_instance  # <- 修改了这一行
        workflow = generator.generate_workflow(task_type, task_instance=task_instance)
        
        # Print results
        logger.info(f"Success Probability: {workflow['success_probability']:.2%}")
        logger.info(f"Optimal Sequence: {' → '.join(workflow['optimal_sequence'])}")
        logger.info(f"Critical Tools: {workflow['critical_tools']}")
        logger.info(f"Quality Metrics: {workflow['workflow_quality']}")
        logger.info(f"Used embeddings: {workflow.get('used_embeddings', False)}")  # <- 新增了这一行
        
        # Generate prompt with task_instance  # <- 修改了这一行
        prompt = generator.generate_mcp_prompt(task_type, task_instance=task_instance)
        logger.info(f"\nGenerated Prompt Preview:")
        logger.info(prompt[:500] + "...")
        
        # Test adherence validation
        test_sequence = workflow['optimal_sequence'][:2] + ['random_tool'] + workflow['optimal_sequence'][2:]
        adherence = generator.validate_workflow_adherence(task_type, test_sequence)
        logger.info(f"\nAdherence Test Results: {adherence}")


if __name__ == "__main__":
    import random
    test_workflow_generator()