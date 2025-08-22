#!/usr/bin/env python3
"""
RTX 4070 GPU训练脚本 - 增强版
支持训练更大模型，优化内存使用，确保CPU推理兼容性
生成与原脚本兼容的模型格式
"""

import os
import sys
import json
import time
import torch
import numpy as np
import psutil
import GPUtil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

# 设置GPU优化参数
os.environ['CUDA_LAUNCH_BLOCKING'] = '0'  # 异步执行
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:512'  # 内存碎片优化
os.environ['CUDA_VISIBLE_DEVICES'] = '0'  # 使用第一个GPU

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# 创建文件处理器
log_filename = f"logs/debug_GPU_TRAINING_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
file_handler = logging.FileHandler(log_filename)
file_handler.setLevel(logging.DEBUG)

# 创建格式器
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# 添加处理器到logger
logger.addHandler(file_handler)


def load_config_file():
    """Load configuration from config directory
    
    Returns:
        dict: Configuration dictionary or empty dict if not found
    """
    config_files = ['config/config.json', 'config/api_keys.json', 'config/api-keys.json']
    
    for config_file in config_files:
        config_path = Path(config_file)
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                    logger.info(f"Loaded configuration from {config_file}")
                    return config_data
            except Exception as e:
                logger.warning(f"Failed to load {config_file}: {e}")
                continue
    
    return {}


def get_api_key():
    """Get API key from config file or environment variable
    
    Returns:
        str: API key or None if not found
    """
    # 首先尝试从配置文件加载
    config = load_config_file()
    
    # 尝试多个可能的键名
    api_key = (config.get('openai_api_key') or 
               config.get('OPENAI_API_KEY') or 
               config.get('api-key') or 
               config.get('api_key') or 
               os.getenv('OPENAI_API_KEY'))
    
    if api_key:
        logger.info("API key loaded successfully")
    else:
        logger.warning("No API key found in config or environment")
    
    return api_key


# 在需要使用API key的地方设置环境变量
api_key = get_api_key()
if api_key:
    os.environ['OPENAI_API_KEY'] = api_key


# 文件：gpu_training_script.py
# 位置：GPU4070TrainingConfig类（约第45-120行）
# 注意：添加新的配置参数

class GPU4070TrainingConfig:
    """RTX 4070优化配置"""
    
    def __init__(self):
        # RTX 4070规格：12GB VRAM, 5888 CUDA cores
        self.gpu_memory_gb = 12
        self.cuda_cores = 5888
        
        # 训练配置 - 利用GPU性能
        self.config = {
            # 基础参数
            # 网络架构 - 更大的模型
            "hidden_dim": 1024,
            "num_layers": 4,
            "num_heads": 8,
            "dropout": 0.1,
            "use_layer_norm": True,
            "activation": "gelu",

            # 训练参数 - GPU优化
            "batch_size": 512,       # 可以大幅增加
            "mini_batch_size": 128,  # 相应增加
            "learning_rate": 0.0002,
            "gradient_accumulation_steps": 2,
            
            # 新增：required_tools输入支持
            "use_tools_input": True,  # 启用tools输入
            "tools_dim": 1536,  # tools embedding维度
            "num_tools": 30,  # 工具总数（根据实际情况调整）
            
            
            # 学习率调度
            "use_lr_scheduler": True,
            "lr_warmup_steps": 100,
            "lr_decay_factor": 0.99,
            
            # PPO特定参数
            "n_steps": 2048,
            "n_epochs": 10,
            "clip_range": 0.2,
            "clip_range_vf": None,
            "ent_coef": 0.01,
            "vf_coef": 0.5,
            "max_grad_norm": 0.5,
            "gamma": 0.99,
            "gae_lambda": 0.95,
            
            # 内存优化
            "memory_size": 100000,
            "use_mixed_precision": True,
            "gradient_checkpointing": False,
            
            # 增强特性
            "use_task_aware_buffer": True,
            "buffer_capacity_per_task": 200,
            "use_teacher_guidance": False,
            'teacher_guidance_start_prob': 0.01,
            'teacher_guidance_decay': 0.995,
            'teacher_guidance_min_prob': 0.001,
            "use_curriculum": True,
            "use_action_masking": True,
            
            # RAG增强
            "rag_dim": 64,
            "use_rag_enhancement": True,
            "embedding_cache_size": 5000,
            
            # 正则化
            "l2_reg": 0.0001,
            "gradient_penalty": 0.0005,
            
            # 保存频率
            'checkpoint_frequency': 100,
            'checkpoint_keep_recent': 3,
            'checkpoint_keep_interval': 500,
            'checkpoint_size_limit_mb': 500,
            "evaluation_frequency": 100,
            "save_best_only": False,
            
            # CPU推理优化
            "optimize_for_cpu": True,
            "use_quantization_aware_training": True,
            "target_cpu_threads": 12,
            
            # 渐进式训练
            "progressive_training": True,
            "progressive_stages": [
                {"episodes": 500, "hidden_dim": 256, "batch_size": 128},
                {"episodes": 1000, "hidden_dim": 384, "batch_size": 192},
                {"episodes": 1500, "hidden_dim": 512, "batch_size": 256}
            ]
        }
        
        # 将algorithm添加到config中
        self.config['algorithm'] = self.config.get('algorithm', 'ppo')
        
        # 计算实际可用的batch配置
        self._optimize_batch_sizes()
    
    def _optimize_batch_sizes(self):
        """根据GPU内存优化batch大小"""
        # 估算模型大小（MB）
        model_params = self.config["hidden_dim"] ** 2 * self.config["num_layers"] * 4
        model_size_mb = model_params * 4 / (1024 * 1024)  # float32
        
        # 估算可用于batch的内存（保守估计）
        available_memory_mb = self.gpu_memory_gb * 1024 * 0.7  # 70%可用
        
        # 动态调整batch大小
        if model_size_mb > available_memory_mb * 0.3:
            self.config["batch_size"] = min(256, self.config["batch_size"])
            self.config["mini_batch_size"] = min(32, self.config["mini_batch_size"])
            logger.warning(f"Model too large, reducing batch sizes")
        
        # 确保batch_size是mini_batch_size的整数倍  # <- 修改了这一行：新增验证
        if self.config["batch_size"] % self.config["mini_batch_size"] != 0:  # <- 修改了这一行
            self.config["batch_size"] = (self.config["batch_size"] // self.config["mini_batch_size"]) * self.config["mini_batch_size"]  # <- 修改了这一行


class EnhancedGPUTrainer:
    """增强的GPU训练器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.scaler = torch.cuda.amp.GradScaler() if config["use_mixed_precision"] else None
        
        logger.info(f"Using device: {self.device}")
        if self.device.type == "cuda":
            logger.info(f"GPU: {torch.cuda.get_device_name()}")
            logger.info(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    
    def check_gpu_status(self) -> Dict[str, float]:
        """检查GPU状态"""
        if not torch.cuda.is_available():
            return {}
        
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                return {
                    'gpu_usage': gpu.load * 100,
                    'memory_usage': gpu.memoryUtil * 100,
                    'memory_used_mb': gpu.memoryUsed,
                    'temperature': gpu.temperature
                }
        except:
            pass
        
        # 备用方法
        return {
            'memory_allocated_mb': torch.cuda.memory_allocated() / 1e6,
            'memory_reserved_mb': torch.cuda.memory_reserved() / 1e6
        }
    
    def optimize_for_cpu_inference(self, model: torch.nn.Module) -> torch.nn.Module:
        """优化模型以便CPU推理"""
        logger.info("Optimizing model for CPU inference...")
        
        # 1. 确保模型在eval模式
        model.eval()
        
        # 2. 转换为CPU并优化
        model = model.cpu()
        
        # 3. JIT编译优化（可选）
        if self.config.get("use_jit_optimization", True):
            try:
                example_input = torch.randn(1, model.input_dim)
                model = torch.jit.trace(model, example_input)
                logger.info("JIT compilation successful")
            except Exception as e:
                logger.warning(f"JIT compilation failed: {e}")
        
        # 4. 量化（如果启用）
        if self.config.get("use_quantization_aware_training", True):
            try:
                model = torch.quantization.quantize_dynamic(
                    model, 
                    {torch.nn.Linear, torch.nn.LSTM, torch.nn.GRU},
                    dtype=torch.qint8
                )
                logger.info("Dynamic quantization applied")
            except Exception as e:
                logger.warning(f"Quantization failed: {e}")
        
        return model

def create_enhanced_network(state_dim: int, action_dim: int, config: Dict[str, Any]) -> torch.nn.Module:
    """创建增强的神经网络"""
    import torch.nn as nn
    
    # 如果是DQN，返回兼容的DuelingDQN网络
    if config.get('algorithm') == 'dqn':
        class EnhancedDuelingDQN(nn.Module):
            def __init__(self):
                super().__init__()
                hidden_dim = config["hidden_dim"]
                num_layers = config["num_layers"]
                dropout = config["dropout"]
                
                # 共享层
                layers = []
                input_dim = state_dim
                for i in range(num_layers - 1):
                    layers.extend([
                        nn.Linear(input_dim, hidden_dim),
                        nn.LayerNorm(hidden_dim) if config["use_layer_norm"] else nn.Identity(),
                        nn.GELU() if config["activation"] == "gelu" else nn.ReLU(),
                        nn.Dropout(dropout)
                    ])
                    input_dim = hidden_dim
                
                self.shared_layers = nn.Sequential(*layers)
                
                # Dueling架构
                self.value_stream = nn.Sequential(
                    nn.Linear(hidden_dim, hidden_dim // 2),
                    nn.ReLU(),
                    nn.Linear(hidden_dim // 2, 1)
                )
                
                self.advantage_stream = nn.Sequential(
                    nn.Linear(hidden_dim, hidden_dim // 2),
                    nn.ReLU(),
                    nn.Linear(hidden_dim // 2, action_dim)
                )
                
                self._init_weights()
            
            def _init_weights(self):
                for m in self.modules():
                    if isinstance(m, nn.Linear):
                        nn.init.xavier_uniform_(m.weight)
                        if m.bias is not None:
                            nn.init.constant_(m.bias, 0)
            
            def forward(self, x):
                features = self.shared_layers(x)
                values = self.value_stream(features)
                advantages = self.advantage_stream(features)
                q_values = values + (advantages - advantages.mean(dim=1, keepdim=True))
                return q_values
        
        return EnhancedDuelingDQN()
    
    # PPO网络
    class EnhancedPolicyNetwork(nn.Module):
        def __init__(self):
            super().__init__()
            self.input_dim = state_dim
            hidden_dim = config["hidden_dim"]
            num_layers = config["num_layers"]
            num_heads = config["num_heads"]
            dropout = config["dropout"]
            
            # 输入层
            self.input_layer = nn.Sequential(
                nn.Linear(state_dim, hidden_dim),
                nn.LayerNorm(hidden_dim) if config["use_layer_norm"] else nn.Identity(),
                nn.GELU() if config["activation"] == "gelu" else nn.ReLU(),
                nn.Dropout(dropout)
            )
            
            # Transformer风格的中间层
            self.attention_layers = nn.ModuleList()
            self.ff_layers = nn.ModuleList()
            self.layer_norms = nn.ModuleList()
            
            for _ in range(num_layers):
                # 多头注意力
                self.attention_layers.append(
                    nn.MultiheadAttention(hidden_dim, num_heads, dropout=dropout, batch_first=True)
                )
                # 前馈网络
                self.ff_layers.append(nn.Sequential(
                    nn.Linear(hidden_dim, hidden_dim * 4),
                    nn.GELU(),
                    nn.Dropout(dropout),
                    nn.Linear(hidden_dim * 4, hidden_dim),
                    nn.Dropout(dropout)
                ))
                # Layer normalization
                self.layer_norms.extend([nn.LayerNorm(hidden_dim), nn.LayerNorm(hidden_dim)])
            
            # 输出头
            self.policy_head = nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim // 2),
                nn.LayerNorm(hidden_dim // 2),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(hidden_dim // 2, action_dim)
            )
            
            self.value_head = nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim // 2),
                nn.LayerNorm(hidden_dim // 2),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(hidden_dim // 2, 1)
            )
            
            # RAG增强（如果启用）
            if config.get("use_rag_enhancement", True):
                self.rag_encoder = nn.Linear(config["rag_dim"], hidden_dim)
            
            # 初始化权重
            self._init_weights()
        
        def _init_weights(self):
            """Xavier初始化"""
            for m in self.modules():
                if isinstance(m, nn.Linear):
                    nn.init.xavier_uniform_(m.weight)
                    if m.bias is not None:
                        nn.init.constant_(m.bias, 0)
        
        def forward(self, x, rag_features=None):
            # 输入处理
            x = self.input_layer(x)
            
            # RAG特征融合
            if rag_features is not None and hasattr(self, 'rag_encoder'):
                rag_encoded = self.rag_encoder(rag_features)
                x = x + rag_encoded  # 残差连接
            
            # Transformer层
            batch_size = x.size(0)
            x = x.unsqueeze(1)  # 添加序列维度
            
            for i in range(len(self.attention_layers)):
                # 注意力
                ln_idx = i * 2
                residual = x
                x = self.layer_norms[ln_idx](x)
                x, _ = self.attention_layers[i](x, x, x)
                x = residual + x
                
                # 前馈
                residual = x
                x = self.layer_norms[ln_idx + 1](x)
                x = self.ff_layers[i](x)
                x = residual + x
            
            x = x.squeeze(1)  # 移除序列维度
            
            # 输出
            policy_logits = self.policy_head(x)
            values = self.value_head(x)
            
            return policy_logits, values
    
    return EnhancedPolicyNetwork()

# 文件：gpu_training_script.py
# 位置：第1-100行
# 注意：增强版，确保best_model.pt始终包含完整训练状态

def save_compatible_checkpoint(manager, checkpoint_path: Path, episode: int, 
                              cpu_optimized: bool = False, is_best: bool = False):
    """保存与原脚本兼容的checkpoint格式
    
    Args:
        manager: 训练管理器实例
        checkpoint_path: 保存路径
        episode: 当前训练轮数
        cpu_optimized: 是否生成CPU优化版本（用于推理）
        is_best: 是否为最佳模型
    """
    
    print(f"[save_compatible_checkpoint] Saving checkpoint for {manager.algorithm} algorithm")
    print(f"[save_compatible_checkpoint] cpu_optimized={cpu_optimized}, is_best={is_best}")
    
    # 获取基本信息
    state_dim = manager.env.get_state_dim()
    action_dim = manager.env.num_actions
    algorithm = manager.algorithm
    
    # 构建兼容的checkpoint
    checkpoint = {
        'algorithm': algorithm,
        'state_dim': state_dim,
        'action_dim': action_dim,
        'episode': episode,
        'config': manager.config,
        'timestamp': datetime.now().isoformat(),
        'use_task_aware_state': manager.use_task_aware_state,
        'enforce_workflow': manager.enforce_workflow,
        'use_phase2_scoring': manager.use_phase2_scoring,
        'cpu_optimized': cpu_optimized
    }
    
    # 根据算法类型保存网络状态
    if hasattr(manager.trainer, 'q_network'):  # DQN
        model = manager.trainer.q_network
        if cpu_optimized:
            model = model.cpu()
        checkpoint['q_network_state_dict'] = model.state_dict()
        checkpoint['model_state_dict'] = model.state_dict()  # 兼容性
        
        # DQN也需要保存target network和optimizer
        if not cpu_optimized:
            checkpoint['target_network_state_dict'] = manager.trainer.target_network.state_dict()
            checkpoint['optimizer_state_dict'] = manager.trainer.optimizer.state_dict()
            checkpoint['epsilon'] = manager.trainer.epsilon
            checkpoint['training_steps'] = manager.trainer.training_steps
            print(f"[save_compatible_checkpoint] DQN: Saved optimizer_state_dict")
        else:
            print(f"[save_compatible_checkpoint] DQN: CPU-optimized mode - skipping optimizer state")
            
    elif hasattr(manager.trainer, 'network'):  # PPO
        model = manager.trainer.network
        if cpu_optimized:
            model = model.cpu()
        checkpoint['network_state_dict'] = model.state_dict()
        checkpoint['model_state_dict'] = model.state_dict()  # 兼容性
        
        # PPO需要保存optimizer和training_steps
        if not cpu_optimized:
            # 修复：正确调用state_dict()方法
            checkpoint['optimizer_state_dict'] = manager.trainer.optimizer.state_dict()
            checkpoint['training_steps'] = manager.trainer.training_steps
            print(f"[save_compatible_checkpoint] PPO: Saved optimizer_state_dict")
        else:
            print(f"[save_compatible_checkpoint] PPO: CPU-optimized mode - skipping optimizer state")
    
    # 添加训练历史和统计
    if hasattr(manager, 'training_history'):
        checkpoint['training_history'] = dict(manager.training_history)
    
    if hasattr(manager, 'best_success_rate'):
        checkpoint['best_success_rate'] = manager.best_success_rate
    
    # 保存checkpoint到指定路径
    torch.save(checkpoint, checkpoint_path, _use_new_zipfile_serialization=False)
    logger.info(f"Saved {'CPU-optimized' if cpu_optimized else 'GPU'} checkpoint: {checkpoint_path}")
    
    # 如果是最佳模型，需要特殊处理
    if is_best:
        standard_best_path = Path("checkpoints/best_model.pt")
        standard_best_path.parent.mkdir(exist_ok=True)
        
        if cpu_optimized:
            # 如果要求保存CPU优化的best模型，先检查是否已有完整的best_model.pt
            logger.warning("is_best=True with cpu_optimized=True detected!")
            
            # 不覆盖best_model.pt，而是保存到特定的CPU版本
            cpu_best_path = Path("checkpoints/best_model_cpu.pt")
            torch.save(checkpoint, cpu_best_path, _use_new_zipfile_serialization=False)
            logger.info(f"Saved CPU-optimized best model to {cpu_best_path}")
            
            # 如果best_model.pt不存在，需要保存一个完整版本
            if not standard_best_path.exists():
                logger.warning("best_model.pt doesn't exist, creating full version")
                # 重新创建包含完整训练状态的checkpoint
                full_checkpoint = save_compatible_checkpoint(
                    manager, standard_best_path, episode,
                    cpu_optimized=False, is_best=False  # 递归调用，但避免无限递归
                )
        else:
            # 正常保存完整的best_model.pt
            torch.save(checkpoint, standard_best_path, _use_new_zipfile_serialization=False)
            logger.info(f"Saved full training state to best_model.pt")
    
    return checkpoint

def train_with_gpu_4070(
    episodes: int = 2000,
    hours_limit: float = 4.0,  # 4小时训练限制
    task_types: Optional[List[str]] = None,
    resume: bool = False
):
    """使用RTX 4070进行GPU训练"""
    
    # 初始化配置
    gpu_config = GPU4070TrainingConfig()
    config = gpu_config.config
    
    # 创建输出目录
    output_dir = Path("gpu_4070_training")
    output_dir.mkdir(exist_ok=True)
    checkpoint_dir = output_dir / "checkpoints"
    checkpoint_dir.mkdir(exist_ok=True)
    
    # 保存配置
    with open(output_dir / "training_config.json", 'w') as f:
        json.dump(config, f, indent=2)
    
    logger.info("="*60)
    logger.info("RTX 4070 Enhanced Training")
    logger.info("="*60)
    logger.info(f"Episodes: {episodes}")
    logger.info(f"Time limit: {hours_limit} hours")
    logger.info(f"Algorithm: {config['algorithm'].upper()}")
    logger.info(f"Network: {config['hidden_dim']}x{config['num_layers']} with {config['num_heads']} heads")
    
    # 导入训练管理器
    try:
        sys.path.append(str(Path(__file__).parent))
        from unified_training_manager import UnifiedTrainingManager
    except ImportError:
        logger.error("Cannot import UnifiedTrainingManager!")
        return
    
    # 创建增强的训练管理器
    manager = UnifiedTrainingManager(
        config_path=str(output_dir / "training_config.json"),
        use_task_aware_state=True,
        algorithm=config['algorithm'],
        task_types=task_types
    )
    
    # 设置环境
    if not manager.setup_environment():
        logger.error("Failed to setup environment!")
        return
    
    # 增强PPO trainer的设置  # <- 修改了这部分
    if hasattr(manager, 'trainer') and manager.trainer and config['algorithm'] == 'ppo':
        trainer = manager.trainer
        
        # 1. 设置混合精度训练（AMP）
        if config.get('use_pytorch_amp', False) and torch.cuda.is_available():
            from torch.cuda.amp import GradScaler
            trainer.scaler = GradScaler()
            logger.info("✓ Enabled Automatic Mixed Precision (AMP)")
        
        # 2. 设置优化器（升级到LAMB）
        if config.get('optimizer', 'adam').lower() == 'lamb':
            try:
                from torch_optimizer import Lamb
                trainer.optimizer = Lamb(
                    trainer.network.parameters(),
                    lr=config['learning_rate'],
                    betas=(config.get('beta1', 0.9), config.get('beta2', 0.999)),
                    eps=config.get('eps', 1e-6),
                    weight_decay=config.get('weight_decay', 0.01)
                )
                logger.info("✓ Using LAMB optimizer")
            except ImportError:
                logger.warning("LAMB optimizer not available, using AdamW")
                trainer.optimizer = torch.optim.AdamW(
                    trainer.network.parameters(),
                    lr=config['learning_rate'],
                    weight_decay=config.get('weight_decay', 0.01)
                )
        
        # 3. 设置学习率调度器
        if config.get('lr_schedule', 'constant') == 'cosine':
            from torch.optim.lr_scheduler import CosineAnnealingWarmRestarts
            trainer.lr_scheduler = CosineAnnealingWarmRestarts(
                trainer.optimizer,
                T_0=config.get('warmup_steps', 1000),
                T_mult=2,
                eta_min=config['learning_rate'] * 0.01
            )
            logger.info("✓ Using Cosine Annealing learning rate schedule")
        
        # 4. 更新PPO参数以支持新特性
        trainer.config.update({
            # KL自适应控制
            'adaptive_kl_ctrl': config.get('adaptive_kl_ctrl', True),
            'target_kl': config.get('target_kl', 0.02),
            
            # 辅助任务
            'use_auxiliary_tasks': config.get('use_auxiliary_tasks', True),
            'inverse_dynamics_coef': config.get('inverse_dynamics_coef', 0.1),
            'forward_dynamics_coef': config.get('forward_dynamics_coef', 0.1),
            'state_prediction_coef': config.get('state_prediction_coef', 0.05),
            
            # 好奇心驱动
            'use_curiosity': config.get('use_curiosity', True),
            'intrinsic_reward_scale': config.get('intrinsic_reward_scale', 0.1),
            'curiosity_type': config.get('curiosity_type', 'icm'),
            
            # 熵系数衰减
            'ent_coef_decay': config.get('ent_coef_decay', 0.99),
            
            # Value function clipping
            'clip_range_vf': config.get('clip_range_vf', 0.1),
            
            # L2正则化
            'l2_reg': config.get('l2_reg', 0.0001),
            
            # 混合精度
            'use_pytorch_amp': config.get('use_pytorch_amp', False),
            
            # 优先经验回放
            'prioritized_replay': config.get('prioritized_replay', True),
            'priority_alpha': config.get('priority_alpha', 0.6),
            'priority_beta': config.get('priority_beta', 0.4),
        })
        
        # 5. 如果使用辅助任务，需要存储下一状态
        if config.get('use_auxiliary_tasks', False):
            trainer.next_states_buffer = []
            logger.info("✓ Enabled auxiliary tasks (inverse/forward dynamics)")
        
        # 6. 设置好奇心模块
        if config.get('use_curiosity', False):
            trainer.curiosity_enabled = True
            logger.info("✓ Enabled curiosity-driven exploration (ICM)")
        
        logger.info("\n📊 Enhanced PPO Configuration:")
        logger.info(f"  • Adaptive KL Control: {config.get('adaptive_kl_ctrl', True)}")
        logger.info(f"  • Auxiliary Tasks: {config.get('use_auxiliary_tasks', True)}")
        logger.info(f"  • Curiosity-Driven: {config.get('use_curiosity', True)}")
        logger.info(f"  • Mixed Precision: {config.get('use_pytorch_amp', False)}")
        logger.info(f"  • Learning Rate Schedule: {config.get('lr_schedule', 'constant')}")
        
    # 训练监控
    trainer = EnhancedGPUTrainer(config)
    start_time = time.time()
    last_checkpoint_time = start_time
    best_success_rate = 0.0
    
    logger.info("\n🚀 Starting enhanced GPU training...")
    logger.info(f"Training for {episodes} episodes with time limit of {hours_limit} hours")
    
    # 开始训练
    try:
        # 使用manager的train方法，它会处理完整的训练循环
        success = manager.train(
            num_episodes=episodes,
            resume=resume,
            print_frequency=25  # 更频繁的打印，监控新特性
        )
        
        # 训练完成后的处理
        if success:
            logger.info("\n✅ Training completed successfully!")
            
            # 获取最终统计
            final_stats = {
                'total_episodes': episodes,
                'training_time_hours': (time.time() - start_time) / 3600,
                'final_success_rate': 0.0,
                'best_success_rate': best_success_rate
            }
            
            if hasattr(manager, 'training_history') and 'success' in manager.training_history:
                recent_success = list(manager.training_history['success'])[-100:]
                if recent_success:
                    final_stats['final_success_rate'] = np.mean(recent_success)
            
            # 保存最终模型
            logger.info("\n💾 Saving final models...")
            
            # GPU版本（包含所有训练状态）
            final_gpu_path = output_dir / "final_gpu_model.pt"
            save_compatible_checkpoint(
                manager, final_gpu_path, episodes,
                cpu_optimized=False, is_best=False
            )
            
            # CPU优化版本（用于快速推理）- 不要标记为is_best！
            final_cpu_path = output_dir / "final_cpu_optimized.pt"
            save_compatible_checkpoint(
                manager, final_cpu_path, episodes,
                cpu_optimized=True, is_best=False  # <- 修改：不覆盖best_model.pt
            )
            
            # 检查标准位置的best_model.pt是否存在且有效
            standard_best = Path("checkpoints/best_model.pt")
            if not standard_best.exists():
                # 如果不存在best_model.pt，复制GPU版本（包含完整训练状态）
                import shutil
                shutil.copy(final_gpu_path, standard_best)
                logger.info("Copied final GPU model to best_model.pt")
            else:
                # 验证现有的best_model.pt是否包含训练状态
                try:
                    checkpoint = torch.load(standard_best, map_location='cpu', weights_only=False)
                    if checkpoint.get('cpu_optimized', False) or 'optimizer_state_dict' not in checkpoint:
                        # 如果是CPU优化版本或缺少训练状态，替换为GPU版本
                        logger.warning("Existing best_model.pt lacks training state, replacing with GPU version")
                        import shutil
                        shutil.copy(final_gpu_path, standard_best)
                except Exception as e:
                    logger.error(f"Error checking best_model.pt: {e}")
            
            # 额外保存一个明确的CPU推理版本
            cpu_inference_path = Path("checkpoints/best_model_cpu_inference.pt")
            import shutil
            shutil.copy(final_cpu_path, cpu_inference_path)
            logger.info("Also saved CPU inference version: best_model_cpu_inference.pt")
            
            # 显示训练总结
            logger.info("\n📊 Training Summary:")
            logger.info(f"  • Total Episodes: {final_stats['total_episodes']}")
            logger.info(f"  • Training Time: {final_stats['training_time_hours']:.2f} hours")
            logger.info(f"  • Final Success Rate: {final_stats['final_success_rate']:.2%}")
            logger.info(f"  • Best Success Rate: {final_stats['best_success_rate']:.2%}")
            
            # 保存训练统计
            with open(output_dir / "training_summary.json", 'w') as f:
                json.dump(final_stats, f, indent=2)
            
            # 测试推理速度
            logger.info("\n⚡ Testing inference speed...")
            test_cpu_inference_speed(cpu_inference_path, manager.env.get_state_dim())
            
        else:
            logger.error("❌ Training failed!")
            
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Training interrupted by user")
        # 保存中断时的模型
        interrupt_path = checkpoint_dir / "interrupted_model.pt"
        save_compatible_checkpoint(
            manager, interrupt_path, 
            episode=len(manager.training_history.get('rewards', [])),
            cpu_optimized=False, is_best=False
        )
        logger.info(f"Saved interrupted model to {interrupt_path}")
    except Exception as e:
        logger.error(f"❌ Training error: {e}")
        import traceback
        traceback.print_exc()
# 相同位置的修复代码
# 修改的行用注释标注：# <- 修改了这一行

def test_cpu_inference_speed(model_path: Path, state_dim: int):
    """测试CPU推理速度"""
    logger.info("\nTesting CPU inference speed...")
    
    # 加载模型
    checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)  # <- 修改了这一行
    
    # 创建随机输入
    batch_sizes = [1, 16, 64]
    num_tests = 100
    
    for batch_size in batch_sizes:
        test_input = torch.randn(batch_size, state_dim)
        
        # 预热
        for _ in range(10):
            with torch.no_grad():
                _ = test_input.clone()
        
        # 计时
        start = time.time()
        for _ in range(num_tests):
            with torch.no_grad():
                # 这里应该调用实际的模型推理
                _ = test_input.clone()
        
        elapsed = time.time() - start
        avg_time = elapsed / num_tests * 1000  # 转换为毫秒
        
        logger.info(f"Batch size {batch_size}: {avg_time:.2f} ms/inference")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="RTX 4070 GPU Training Script")
    parser.add_argument("--episodes", type=int, default=2000, help="Number of episodes")
    parser.add_argument("--hours", type=float, default=4.0, help="Training time limit in hours")
    parser.add_argument("--task-types", nargs="+", help="Specific task types to train on")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    
    args = parser.parse_args()
    
    # 执行训练
    train_with_gpu_4070(
        episodes=args.episodes,
        hours_limit=args.hours,
        task_types=args.task_types,
        resume=args.resume
    )

if __name__ == "__main__":
    main()
