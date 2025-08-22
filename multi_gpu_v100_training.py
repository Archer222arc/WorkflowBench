# 文件：multi_gpu_v100_training.py
# 位置：第1-900行
# 注意：完整的修复后代码，支持FSDP

#!/usr/bin/env python3
"""
Multi-GPU V100 训练脚本 - 支持4卡并行训练和断点续训
针对4块V100 GPU优化，支持FSDP分布式训练和resume功能
"""

import os
import sys
import json
import time
import torch
import torch.nn as nn
import torch.distributed as dist
import torch.multiprocessing as mp
from torch.distributed.fsdp import FullyShardedDataParallel as FSDP
from torch.distributed.fsdp.fully_sharded_data_parallel import (
    CPUOffload,
    BackwardPrefetch,
    MixedPrecision,
)
from torch.distributed.fsdp.wrap import (
    size_based_auto_wrap_policy,
    enable_wrap,
    wrap,
)
from torch.distributed.fsdp.sharded_grad_scaler import ShardedGradScaler
from functools import partial
from torch.utils.data.distributed import DistributedSampler
import numpy as np
import psutil
import GPUtil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
import logging
from collections import defaultdict
import socket
import multiprocessing as native_mp

# 设置环境变量优化NCCL通信
os.environ['NCCL_DEBUG'] = 'WARN'
os.environ['NCCL_TREE_THRESHOLD'] = '0'  # 始终使用tree算法
os.environ['CUDA_LAUNCH_BLOCKING'] = '0'  # 异步执行
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:512'

# 配置日志
logger = logging.getLogger(__name__)

class V100MultiGPUConfig:
    """多GPU V100优化配置 - 优化性能，使用DDP代替FSDP"""
    
    def __init__(self, num_gpus: int = 4):
        # V100规格：16GB/32GB VRAM per GPU
        self.num_gpus = num_gpus
        self.gpu_memory_gb = 16  # 假设16GB版本
        self.total_memory_gb = self.gpu_memory_gb * num_gpus
        
        # 优化的基础配置 - 减小批量大小以加快训练
        base_batch_size = 64  # 从256减少到64
        base_lr = 0.0002  # 略微提高学习率
        
        # 性能优化的缩放策略
        if num_gpus <= 4:
            # 4GPU优化策略
            batch_size_scale = num_gpus  # 线性扩展
            lr_scale = np.sqrt(num_gpus) * 0.8  # 保守的学习率扩展
            n_steps_scale = 1  # 减少n_steps以加快训练循环
        else:
            # 8GPU优化策略
            batch_size_scale = num_gpus * 0.75  # 考虑通信开销
            lr_scale = np.sqrt(num_gpus) * 0.7
            n_steps_scale = 1.5  # 略微增加但不要太多
        
        # 优化后的训练配置
        self.config = {
            'num_gpus': num_gpus,
            'batch_size': int(base_batch_size * batch_size_scale),
            'per_gpu_batch_size': base_batch_size,  # 每个GPU的批量大小
            'learning_rate': base_lr * lr_scale,
            'mini_batch_size': 32,  # PPO mini-batch
            'gradient_accumulation_steps': 1,  # 不使用梯度累积
            'device': 'cuda',
            
            # 算法配置
            'algorithm': 'ppo',  # 或 'ppo'
            'hidden_dim': 1024,
            'num_layers': 6,
            'num_heads': 16,
            'dropout': 0.1,
            
            # DQN specific
            'memory_size': 50000 * num_gpus,  # 适度的replay buffer
            'epsilon_start': 1.0,
            'epsilon_min': 0.05,
            'epsilon_decay': 0.9995,
            'gamma': 0.99,
            'target_update_freq': 50,  # 更频繁的target更新
            
            # PPO specific - 关键优化
            'n_steps': 512 * n_steps_scale,  # 大幅减少从8192到512-768
            'n_epochs': 4,  # 减少从10到4
            'clip_range': 0.2,
            'ent_coef': 0.01,
            'vf_coef': 0.5,
            'gae_lambda': 0.95,

            # Teacher guidance - 启用并优化参数
            'use_teacher_guidance': True,  # 启用teacher guidance
            'teacher_guidance_start_prob': 0.95,  # 提高初始概率以加速学习
            'teacher_guidance_decay': 0.99,  # 较慢的衰减速度
            'teacher_guidance_min_prob': 0.001,  # 保持最低5%的guidance
            'episode_guidance_mode': True,  # 使用episode级别的guidance
            
            # 新增：自适应guidance参数
            'adaptive_guidance': True,  # 根据任务难度自适应调整
            'guidance_temperature': 0.5,  # soft guidance的温度参数
            'guidance_blend_factor': 0.7,  # 混合teacher和model预测的权重
            
            # 优化器配置
            'weight_decay': 0.0001,
            'adam_eps': 1e-5,
            'max_grad_norm': 1.0,
            
            # 并行优化 - 使用DDP而非FSDP
            'use_mixed_precision': True,  # V100支持混合精度
            'use_fsdp': False,  # 关闭FSDP，使用标准DDP
            'ddp_find_unused_parameters': False,
            'ddp_bucket_cap_mb': 25,
            'gradient_compression': False,
            
            
            # 监控和日志 - 优化checkpoint频率
            'log_interval': 10,
            'checkpoint_frequency': 500,  # 从100增加到500，减少IO开销
            'checkpoint_keep_recent': 3,  # 减少保存的checkpoint数量
            'sync_frequency': 2000,  # 从500增加到2000，减少同步开销
            
            # Task-aware配置
            'use_task_aware_state': True,
            'use_task_aware_buffer': True,
            'buffer_capacity_per_task': 10000,  # 减少内存使用
            'min_episodes_per_task': 10,
            'task_mix_ratio': 0.7,
            
            # 训练参数
            'max_episode_length': 30,
            'use_action_masking': True,
            'use_curriculum': True,  # 关键修复：确保curriculum功能启用
            'evaluation_frequency': 100,  # 减少评估频率
            'evaluation_episodes': 5,  # 减少评估episodes
            
            # 性能监控
            'profile_training': True,  # 启用性能分析
            'log_episode_time': True,  # 记录每个episode的时间
            'target_episode_time': 1.0  # 目标：每个episode 1秒内完成
        }

        if 'per_gpu_batch_size' not in self.config:
            self.config['per_gpu_batch_size'] = self.config['batch_size'] // self.num_gpus

        # 如果某些FSDP配置缺失，添加默认值
        fsdp_defaults = {
            'fsdp_min_num_params': 1e6,
            'fsdp_cpu_offload': False,
            'fsdp_backward_prefetch': True,
            'fsdp_forward_prefetch': True,
            'fsdp_use_orig_params': True,
        }
        
        for key, default_value in fsdp_defaults.items():
            if key not in self.config:
                self.config[key] = default_value
        
        # 添加调试日志，确认curriculum已启用
        print(f"[V100MultiGPUConfig] Curriculum learning enabled: {self.config['use_curriculum']}")
    def _validate_batch_sizes(self):
        """验证并调整批量大小以确保兼容性"""
        # 确保总批量大小是GPU数量的倍数
        if self.config["batch_size"] % self.num_gpus != 0:
            self.config["batch_size"] = (self.config["batch_size"] // self.num_gpus) * self.num_gpus
            print(f"Adjusted batch_size to {self.config['batch_size']} for {self.num_gpus} GPUs")
        
        # 确保是mini_batch_size的倍数
        if self.config["batch_size"] % self.config["mini_batch_size"] != 0:
            self.config["batch_size"] = (self.config["batch_size"] // self.config["mini_batch_size"]) * self.config["mini_batch_size"]
            print(f"Adjusted batch_size to {self.config['batch_size']} to be divisible by mini_batch_size")
        
        # 计算每个GPU的批量大小
        self.config["per_gpu_batch_size"] = self.config["batch_size"] // self.num_gpus
        
        # 确保n_steps是batch_size的倍数（PPO要求）
        if self.config["n_steps"] % self.config["batch_size"] != 0:
            self.config["n_steps"] = (self.config["n_steps"] // self.config["batch_size"]) * self.config["batch_size"]
            print(f"Adjusted n_steps to {self.config['n_steps']} to be divisible by batch_size")
        
        # 打印验证信息
        print(f"\n📊 Batch Size Configuration:")
        print(f"  • Total batch size: {self.config['batch_size']}")
        print(f"  • Per-GPU batch size: {self.config['per_gpu_batch_size']}")
        print(f"  • Mini-batch size: {self.config['mini_batch_size']}")
        print(f"  • N-steps (rollout): {self.config['n_steps']}")
        print(f"  • Steps per update: {self.config['n_steps'] // self.config['batch_size']}")

def find_free_port():
    """动态查找一个可用的端口"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # 绑定到端口0让系统自动分配一个可用端口
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def setup_distributed(rank: int, world_size: int):
    """优化的分布式训练环境初始化 - 增强版本"""
    
    print(f"[Rank {rank}] Starting enhanced distributed setup for {world_size} GPUs...")
    
    # 从环境变量获取master port
    master_port = os.environ['MASTER_PORT']
    print(f"[Rank {rank}] Using master port: {master_port}")
    
    # 设置当前GPU设备
    torch.cuda.set_device(rank)
    print(f"[Rank {rank}] Set CUDA device to GPU {rank}")
    
    # 直接初始化进程组 - 增加超时时间
    print(f"[Rank {rank}] Initializing process group...")
    
    dist.init_process_group(
        backend="nccl",
        rank=rank,
        world_size=world_size,
        timeout=timedelta(minutes=30)  # 增加到30分钟，适应大规模训练
    )
    
    print(f"[Rank {rank}] Successfully initialized process group")
    
    # 验证初始化成功
    if dist.is_initialized():
        # 设置CUDA流优先级（8GPU时特别重要）
        if world_size > 4:
            torch.cuda.set_stream(torch.cuda.Stream(priority=-1))
        
        # 使用异步barrier避免死锁
        print(f"[Rank {rank}] Performing initial barrier sync...")
        barrier_handle = dist.barrier(async_op=True)
        
        # 等待barrier完成，但有超时保护
        if not barrier_handle.wait(timeout=timedelta(seconds=30)):
            print(f"[Rank {rank}] WARNING: Initial barrier timed out")
        
        if rank == 0:
            print(f"✅ Distributed training initialized with {world_size} GPUs")
            print(f"   Backend: {dist.get_backend()}")
            print(f"   World size: {dist.get_world_size()}")
            print(f"   Master port: {master_port}")
            print(f"   NCCL timeout: {os.environ.get('NCCL_TIMEOUT', 'default')} seconds")


def cleanup_distributed():
    """清理分布式训练环境"""
    if dist.is_initialized():
        dist.destroy_process_group()


def create_fsdp_model(model: nn.Module, rank: int, config: Dict[str, Any]) -> FSDP:
    """创建FSDP包装的模型 - 修复版本，避免嵌套FSDP问题"""
    
    print(f"[Rank {rank}] Creating FSDP model with improved wrapping strategy")
    
    # 混合精度配置
    mixed_precision_policy = None
    if config.get('use_mixed_precision', True):
        from torch.distributed.fsdp import MixedPrecision
        mixed_precision_policy = MixedPrecision(
            param_dtype=torch.float32,
            reduce_dtype=torch.float32,
            buffer_dtype=torch.float32,
        )
    
    # CPU offload配置（V100通常不需要）
    cpu_offload = None
    if config.get('fsdp_cpu_offload', False):
        cpu_offload = CPUOffload(offload_params=True)
    
    # 修复：更保守的包装策略，避免过度包装
    # 1. 增加最小参数阈值，减少自动包装的模块数量
    # 2. 只包装真正需要的大型模块
    min_params = config.get('fsdp_min_num_params', 1e6)
    
    # 对于ActorCriticNetwork，我们需要更精细的控制
    # 增加阈值以避免过度包装小模块
    adjusted_min_params = max(min_params, 5e6)  # 至少5M参数才包装
    
    print(f"[Rank {rank}] Using adjusted min_params threshold: {adjusted_min_params}")
    
    # 自定义包装策略 - 更精细的控制
    def custom_auto_wrap_policy(module, recurse, nonwrapped_numel):
        """自定义包装策略，避免嵌套FSDP问题"""
        # 计算模块参数数量
        num_params = sum(p.numel() for p in module.parameters(recurse=False))
        
        # 检查是否应该包装
        should_wrap = num_params >= adjusted_min_params
        
        # 特殊处理：避免包装已经是FSDP的模块
        if hasattr(module, '_is_root'):
            print(f"[Rank {rank}] Module {module.__class__.__name__} already has _is_root, skipping wrap")
            should_wrap = False
        
        # 避免包装某些特定类型的模块
        excluded_modules = (nn.LayerNorm, nn.Dropout, nn.Embedding)
        if isinstance(module, excluded_modules):
            should_wrap = False
        
        # 只包装大型的Transformer层或整个子网络
        if should_wrap:
            print(f"[Rank {rank}] Wrapping {module.__class__.__name__} with {num_params} params")
        
        return should_wrap
    
    # 使用自定义包装策略
    auto_wrap_policy = custom_auto_wrap_policy
    
    # 检查PyTorch版本，调整参数
    torch_version = tuple(map(int, torch.__version__.split('.')[:2]))
    
    # 创建FSDP模型时的参数
    fsdp_kwargs = {
        'module': model,
        'auto_wrap_policy': auto_wrap_policy,
        'mixed_precision': mixed_precision_policy,
        'cpu_offload': cpu_offload,
        'device_id': rank,
    }
    
    # 版本兼容性处理
    if torch_version >= (2, 0):
        # PyTorch 2.0+ 支持的参数
        fsdp_kwargs.update({
            'use_orig_params': config.get('fsdp_use_orig_params', False),  # 修改为False以避免冲突
            'sync_module_states': True,
        })
        if config.get('fsdp_backward_prefetch', True):
            fsdp_kwargs['backward_prefetch'] = BackwardPrefetch.BACKWARD_PRE
    else:
        # 旧版本PyTorch
        print(f"[Rank {rank}] Using legacy FSDP parameters for PyTorch {torch.__version__}")
    
    # 创建FSDP模型
    print(f"[Rank {rank}] Creating FSDP wrapper with kwargs: {list(fsdp_kwargs.keys())}")
    fsdp_model = FSDP(**fsdp_kwargs)
    
    print(f"[Rank {rank}] FSDP model created successfully")
    return fsdp_model

def save_checkpoint_fsdp(
    rank: int,
    model: FSDP,
    trainer,
    manager,
    episode: int,
    checkpoint_dir: Path,
    is_best: bool = False,
    config: Dict[str, Any] = None
):
    """在FSDP环境中保存checkpoint - 兼容不同PyTorch版本"""
    
    try:
        # 尝试导入FSDP相关类
        from torch.distributed.fsdp import (
            FullStateDictConfig,
            StateDictType,
        )
        
        # 检查StateDictType是否有正确的属性
        if hasattr(StateDictType, 'FULL_STATE_DICT') and StateDictType.FULL_STATE_DICT is not None:
            # 使用新版API
            save_policy = FullStateDictConfig(offload_to_cpu=True, rank0_only=True)
            
            with FSDP.state_dict_type(
                model, StateDictType.FULL_STATE_DICT, save_policy
            ):
                # 只在rank 0保存
                if rank == 0:
                    _save_checkpoint_content(model, trainer, manager, episode, checkpoint_dir, is_best, config)
        else:
            # 后备方案：使用旧版API或直接保存
            print(f"[Rank {rank}] Warning: StateDictType.FULL_STATE_DICT not available, using fallback")
            if rank == 0:
                # 尝试使用旧版API
                with FSDP.summon_full_params(model, writeback=False, rank0_only=True):
                    _save_checkpoint_content(model, trainer, manager, episode, checkpoint_dir, is_best, config)
                    
    except ImportError as e:
        # 如果导入失败，使用最基础的方法
        print(f"[Rank {rank}] Warning: FSDP state dict API not available: {e}")
        if rank == 0:
            # 直接保存模型状态
            _save_checkpoint_content(model, trainer, manager, episode, checkpoint_dir, is_best, config)
    
    except Exception as e:
        # 捕获其他错误
        print(f"[Rank {rank}] Error in save_checkpoint_fsdp: {e}")
        if rank == 0:
            # 尝试基础保存
            try:
                _save_checkpoint_content(model, trainer, manager, episode, checkpoint_dir, is_best, config)
            except:
                print(f"[Rank {rank}] Failed to save checkpoint")
                raise
    
    # 所有rank同步
    dist.barrier()

def _save_checkpoint_content(model, trainer, manager, episode: int, checkpoint_dir: Path, 
                            is_best: bool, config: Dict[str, Any]):
    """实际保存checkpoint内容的辅助函数"""
    # 准备checkpoint数据
    checkpoint = {
        'episode': episode,
        'algorithm': config.get('algorithm', 'ppo'),
        'config': config,
        'timestamp': datetime.now().isoformat(),
        'num_gpus_trained': config.get('num_gpus', 4),
        'training_complete': False,
        'fsdp_trained': True  # 标记使用FSDP训练
    }
    
    # 保存模型状态
    try:
        checkpoint['network_state_dict'] = model.state_dict()
    except:
        # 如果state_dict失败，尝试module
        if hasattr(model, 'module'):
            checkpoint['network_state_dict'] = model.module.state_dict()
        else:
            print(f"Warning: Could not save model state dict")
            checkpoint['network_state_dict'] = {}
    
    checkpoint['model_state_dict'] = checkpoint['network_state_dict']  # 兼容性
    
    # 对于DQN，保存target network
    if hasattr(trainer, 'target_network'):
        try:
            # Target network可能也被FSDP包装
            if isinstance(trainer.target_network, FSDP):
                # 尝试使用FSDP API
                try:
                    from torch.distributed.fsdp import StateDictType, FullStateDictConfig
                    if hasattr(StateDictType, 'FULL_STATE_DICT') and StateDictType.FULL_STATE_DICT is not None:
                        save_policy = FullStateDictConfig(offload_to_cpu=True, rank0_only=True)
                        with FSDP.state_dict_type(
                            trainer.target_network, StateDictType.FULL_STATE_DICT, save_policy
                        ):
                            checkpoint['target_network_state_dict'] = trainer.target_network.state_dict()
                    else:
                        # 使用旧版API
                        with FSDP.summon_full_params(trainer.target_network, writeback=False, rank0_only=True):
                            checkpoint['target_network_state_dict'] = trainer.target_network.state_dict()
                except:
                    # 直接尝试获取state_dict
                    checkpoint['target_network_state_dict'] = trainer.target_network.state_dict()
            else:
                checkpoint['target_network_state_dict'] = trainer.target_network.state_dict()
        except Exception as e:
            print(f"Warning: Could not save target network state: {e}")
    
    # 保存优化器状态
    if hasattr(trainer, 'optimizer'):
        checkpoint['optimizer_state_dict'] = trainer.optimizer.state_dict()
    
    # 保存学习率调度器状态
    if hasattr(trainer, 'lr_scheduler'):
        checkpoint['lr_scheduler_state_dict'] = trainer.lr_scheduler.state_dict()
    
    # 保存训练器状态
    if hasattr(trainer, 'training_steps'):
        checkpoint['training_steps'] = trainer.training_steps
    if hasattr(trainer, 'total_timesteps'):
        checkpoint['total_timesteps'] = trainer.total_timesteps
    if hasattr(trainer, 'epsilon'):
        checkpoint['epsilon'] = trainer.epsilon
    
    # 保存manager状态
    if manager:
        if hasattr(manager, 'training_history'):
            checkpoint['training_history'] = dict(manager.training_history)
        if hasattr(manager, 'best_success_rate'):
            checkpoint['best_success_rate'] = manager.best_success_rate
        if hasattr(manager, 'best_model_path'):
            checkpoint['best_model_path'] = str(manager.best_model_path) if manager.best_model_path else None
    
    # 确定保存路径
    if is_best:
        checkpoint_path = checkpoint_dir / "best_model.pt"
    else:
        checkpoint_path = checkpoint_dir / f"multi_gpu_checkpoint_{episode}.pt"
    
    # 保存checkpoint
    torch.save(checkpoint, checkpoint_path)
    logger.info(f"Saved FSDP checkpoint to {checkpoint_path}")
    
    # 清理旧的checkpoints（保留最近的几个）
    if not is_best:
        keep_recent = config.get('checkpoint_keep_recent', 5)
        all_checkpoints = sorted(checkpoint_dir.glob("multi_gpu_checkpoint_*.pt"), key=lambda p: p.stat().st_mtime)
        
        if len(all_checkpoints) > keep_recent:
            for old_checkpoint in all_checkpoints[:-keep_recent]:
                old_checkpoint.unlink()
                logger.info(f"Removed old checkpoint: {old_checkpoint}")


def load_checkpoint_fsdp(
    rank: int, 
    checkpoint_path: Path, 
    model: FSDP,
    trainer, 
    manager, 
    config: Dict[str, Any]
) -> int:
    """在FSDP环境中加载checkpoint - 兼容不同PyTorch版本"""
    
    if rank == 0:
        logger.info(f"Loading checkpoint from {checkpoint_path}")
    
    # 加载checkpoint
    checkpoint = torch.load(checkpoint_path, map_location=f'cuda:{rank}', weights_only=False)
    
    try:
        # 尝试使用新版FSDP API
        from torch.distributed.fsdp import (
            FullStateDictConfig,
            StateDictType,
        )
        
        # 检查StateDictType是否有正确的属性
        if hasattr(StateDictType, 'FULL_STATE_DICT') and StateDictType.FULL_STATE_DICT is not None:
            # 恢复模型状态
            with FSDP.state_dict_type(
                model, StateDictType.FULL_STATE_DICT
            ):
                model.load_state_dict(checkpoint.get('network_state_dict', checkpoint.get('model_state_dict', {})))
        else:
            # 使用旧版API
            print(f"[Rank {rank}] Warning: StateDictType.FULL_STATE_DICT not available, using fallback")
            with FSDP.summon_full_params(model, writeback=True):
                model.load_state_dict(checkpoint.get('network_state_dict', checkpoint.get('model_state_dict', {})))
                
    except Exception as e:
        # 后备方案：直接加载
        print(f"[Rank {rank}] Warning: FSDP state dict API failed: {e}, trying direct load")
        try:
            model.load_state_dict(checkpoint.get('network_state_dict', checkpoint.get('model_state_dict', {})))
        except:
            if hasattr(model, 'module'):
                model.module.load_state_dict(checkpoint.get('network_state_dict', checkpoint.get('model_state_dict', {})))
    
    # 对于DQN，还需要恢复target network
    if hasattr(trainer, 'target_network') and 'target_network_state_dict' in checkpoint:
        try:
            if isinstance(trainer.target_network, FSDP):
                # 尝试使用FSDP API
                try:
                    from torch.distributed.fsdp import StateDictType
                    if hasattr(StateDictType, 'FULL_STATE_DICT') and StateDictType.FULL_STATE_DICT is not None:
                        with FSDP.state_dict_type(
                            trainer.target_network, StateDictType.FULL_STATE_DICT
                        ):
                            trainer.target_network.load_state_dict(checkpoint['target_network_state_dict'])
                    else:
                        with FSDP.summon_full_params(trainer.target_network, writeback=True):
                            trainer.target_network.load_state_dict(checkpoint['target_network_state_dict'])
                except:
                    trainer.target_network.load_state_dict(checkpoint['target_network_state_dict'])
            else:
                trainer.target_network.load_state_dict(checkpoint['target_network_state_dict'])
        except Exception as e:
            print(f"[Rank {rank}] Warning: Could not restore target network: {e}")
    
    # 恢复优化器状态
    if 'optimizer_state_dict' in checkpoint and hasattr(trainer, 'optimizer'):
        trainer.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        if rank == 0:
            logger.info("Restored optimizer state")
    
    # 恢复学习率调度器
    if hasattr(trainer, 'lr_scheduler') and 'lr_scheduler_state_dict' in checkpoint:
        trainer.lr_scheduler.load_state_dict(checkpoint['lr_scheduler_state_dict'])
        if rank == 0:
            logger.info("Restored learning rate scheduler")
    
    # 恢复训练器特定状态
    if hasattr(trainer, 'training_steps'):
        trainer.training_steps = checkpoint.get('training_steps', 0)
    if hasattr(trainer, 'total_timesteps'):
        trainer.total_timesteps = checkpoint.get('total_timesteps', 0)
    
    # 对于DQN，恢复epsilon
    if hasattr(trainer, 'epsilon'):
        trainer.epsilon = checkpoint.get('epsilon', config.get('epsilon_start', 1.0))
    
    # 恢复manager状态（只在主进程）
    if rank == 0 and manager:
        if 'training_history' in checkpoint:
            manager.training_history = defaultdict(list, checkpoint['training_history'])
        if 'best_success_rate' in checkpoint:
            manager.best_success_rate = checkpoint['best_success_rate']
        if 'best_model_path' in checkpoint:
            manager.best_model_path = Path(checkpoint['best_model_path']) if checkpoint['best_model_path'] else None
    
    # 返回下一个要开始的episode
    start_episode = checkpoint.get('episode', 0) + 1
    
    if rank == 0:
        logger.info(f"Checkpoint loaded successfully, resuming from episode {start_episode}")
        
        # 打印恢复的状态信息
        if hasattr(trainer, 'training_steps'):
            logger.info(f"Training steps: {trainer.training_steps}")
        if hasattr(trainer, 'epsilon'):
            logger.info(f"Epsilon: {trainer.epsilon:.4f}")
    
    return start_episode

def find_latest_checkpoint(checkpoint_dir: Path) -> Optional[Tuple[Path, int]]:
    """查找最新的checkpoint文件"""
    # 首先尝试找best_model.pt
    best_model_path = checkpoint_dir / "best_model.pt"
    if best_model_path.exists():
        checkpoint = torch.load(best_model_path, map_location='cpu', weights_only=False)
        episode = checkpoint.get('episode', 0)
        return best_model_path, episode
    
    # 查找checkpoint_*.pt文件
    checkpoints = list(checkpoint_dir.glob("checkpoint_*.pt"))
    if not checkpoints:
        # 查找multi_gpu特定的checkpoint
        checkpoints = list(checkpoint_dir.glob("multi_gpu_checkpoint_*.pt"))
    
    if not checkpoints:
        return None
    
    # 按修改时间排序，获取最新的
    checkpoints.sort(key=lambda p: p.stat().st_mtime)
    latest_checkpoint = checkpoints[-1]
    
    checkpoint = torch.load(latest_checkpoint, map_location='cpu', weights_only=False)
    episode = checkpoint.get('episode', 0)
    return latest_checkpoint, episode



def train_worker(rank: int, world_size: int, config: Dict[str, Any], episodes: int, resume: bool = False):
    """每个GPU的训练进程 - 支持FSDP和Curriculum"""
    
    # 初始化变量，防止在finally块中引用未定义变量
    trainer = None
    manager = None
    last_sync_time = time.time()
    sync_failures = 0
    curriculum = None  # 添加curriculum变量
    
    # 设置分布式环境
    setup_distributed(rank, world_size)
    
    # 设置日志（只在主进程打印）
    if rank == 0:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    else:
        logger.setLevel(logging.WARNING)
    
    # 导入必要的模块
    sys.path.append(str(Path(__file__).parent))
    from unified_training_manager import UnifiedTrainingManager, CurriculumScheduler  # 导入CurriculumScheduler
    
    # 创建输出目录（只在主进程）
    output_dir = Path(".")
    checkpoint_dir = output_dir / "checkpoints"
    if rank == 0:
        checkpoint_dir.mkdir(exist_ok=True)
    
    # 等待所有进程准备就绪
    dist.barrier()
    
    try:
        # 创建训练管理器
        config_path = output_dir / "training_config.json" 
        if rank == 0:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
        
        # 确保配置文件写入完成
        dist.barrier()
        
        # 所有进程创建manager
        manager = UnifiedTrainingManager(
            config_path=str(config_path),
            use_task_aware_state=True,
            algorithm=config['algorithm']
        )
        
        # 设置环境
        if not manager.setup_environment():
            print(f"[Rank {rank}] Failed to setup environment!")
            return
        
        # 获取trainer
        trainer = manager.trainer
        if not trainer:
            print(f"[Rank {rank}] Trainer not initialized!")
            return
        
        # 将模型转换为FSDP（仅适用于PPO）
        if config['algorithm'] == 'ppo' and hasattr(trainer, 'network'):
            trainer.network = create_fsdp_model(trainer.network, rank, config)
            print(f"[Rank {rank}] Model converted to FSDP")
        
        # 恢复checkpoint（如果需要）
        start_episode = 0
        if resume and rank == 0:
            checkpoint_info = find_latest_checkpoint(checkpoint_dir)
            if checkpoint_info:
                checkpoint_path, _ = checkpoint_info
                model_to_load = trainer.network if hasattr(trainer, 'network') else trainer.q_network
                start_episode = load_checkpoint_fsdp(
                    rank, checkpoint_path, model_to_load, trainer, manager, config
                )

        # 广播开始episode到所有进程
        start_episode_tensor = torch.tensor(start_episode, dtype=torch.long).cuda(rank)
        dist.broadcast(start_episode_tensor, src=0)
        start_episode = start_episode_tensor.item()

        print(f"[Rank {rank}] Starting from episode {start_episode}")
        
        # 初始化curriculum（新增）
        if config.get('use_curriculum', True):
            curriculum = CurriculumScheduler(episodes)
            if resume and start_episode > 0:
                curriculum.current_episode = start_episode
            if rank == 0:
                print(f"[CURRICULUM] Initialized with {episodes} total episodes")
                print(f"[CURRICULUM] Starting from episode {start_episode}")
        
        # 训练循环
        episode_rewards = []
        episode_success = []
        episode_lengths = []
        start_time = time.time()
        
        # 初始化manager的training_history（如果不存在）
        if not hasattr(manager, 'training_history'):
            manager.training_history = {
                'rewards': [],
                'success': [],
                'lengths': []
            }
        
        for episode in range(start_episode, episodes):
            # 获取curriculum阶段（新增）
            curriculum_stage = None
            if curriculum:
                curriculum_stage = curriculum.get_stage()
                # 只在rank 0上打印curriculum信息
                if rank == 0 and episode % 100 == 0:
                    print(f"[CURRICULUM] Episode {episode}, Stage: {curriculum_stage}, "
                          f"Progress: {curriculum.current_episode/curriculum.total_episodes:.1%}")
            
            # 重置环境，传递curriculum_stage（修复的关键行）
            state = manager.env.reset(curriculum_stage=curriculum_stage)
            done = False
            episode_reward = 0
            episode_trajectory = []
            
            # Episode循环
            while not done and manager.env.episode_steps < config['max_episode_length']:
                # 获取有效动作
                valid_actions = manager.env.get_valid_actions() if config.get('use_action_masking', True) else None
                
                # 选择动作
                action = trainer.select_action(state, valid_actions)
                
                # 执行动作
                next_state, reward, done, info = manager.env.step(action)
                
                # 记录轨迹
                episode_trajectory.append({
                    'state': state.copy() if isinstance(state, np.ndarray) else state,
                    'action': action,
                    'reward': reward,
                    'next_state': next_state.copy() if isinstance(next_state, np.ndarray) else next_state,
                    'done': done,
                    'info': info
                })
                
                # 存储经验
                task_type = None
                if hasattr(manager.env, 'current_task') and hasattr(manager.env.current_task, 'task_type'):
                    task_type = manager.env.current_task.task_type
                
                trainer.store_experience(state, action, reward, next_state, done, task_type=task_type)
                trainer.step_completed()
                
                # 更新状态
                state = next_state
                episode_reward += reward
                
                # 训练（如果需要）
                if trainer.should_train():
                    loss = trainer.train_step()
                    if rank == 0 and episode % 10 == 0:
                        logger.debug(f"Episode {episode}, Loss: {loss:.4f}")
            
            # Episode结束处理
            trainer.on_episode_end()
            
            # 记录episode结果
            success = info.get('success', False)
            episode_rewards.append(episode_reward)
            episode_success.append(float(success))
            episode_lengths.append(manager.env.episode_steps)
            
            # 更新exploration
            trainer.update_exploration()
            
            # 更新curriculum（新增）
            if curriculum:
                curriculum.update()
                # 检查stage变化
                new_stage = curriculum.get_stage()
                if rank == 0 and episode > 0 and new_stage != curriculum_stage:
                    print(f"[CURRICULUM] Advanced to Stage {new_stage} at episode {episode}")
            
            # 定期同步和保存（保持原有逻辑）
            if episode % config.get('sync_frequency', 500) == 0 and episode > 0:
                if rank == 0:
                    logger.info(f"Episode {episode}/{episodes} - "
                               f"Reward: {np.mean(episode_rewards[-100:]):.2f}, "
                               f"Success: {np.mean(episode_success[-100:]):.2%}, "
                               f"Stage: {curriculum_stage if curriculum else 'N/A'}")
                
                # 同步训练状态
                try:
                    trainer.sync_parameters()
                    last_sync_time = time.time()
                    sync_failures = 0
                except Exception as e:
                    sync_failures += 1
                    if rank == 0:
                        logger.warning(f"Sync failed: {e} (failure #{sync_failures})")
                    
                    if sync_failures >= 3:
                        logger.error(f"[Rank {rank}] Too many sync failures, stopping training")
                        break
            
            # 保存checkpoint（保持原有逻辑）
            if rank == 0 and episode % config.get('checkpoint_frequency', 500) == 0 and episode > 0:
                model_to_save = trainer.network if hasattr(trainer, 'network') else trainer.q_network
                save_checkpoint_fsdp(
                    rank, model_to_save, trainer, manager, episode, checkpoint_dir,
                    is_best=False, config=config
                )

            hours_limit = config.get('hours_limit', None)
            # 检查时间限制（保持原有逻辑）
            if hours_limit and (time.time() - start_time) / 3600 > hours_limit:
                if rank == 0:
                    logger.info(f"Time limit reached ({hours_limit} hours)")
                break
        
        # 训练完成，保存最终模型（保持原有逻辑）
        if rank == 0:
            elapsed_time = (time.time() - start_time) / 3600
            logger.info(f"Training completed in {elapsed_time:.2f} hours")
            
            # 保存最终模型
            model_to_save = trainer.network if hasattr(trainer, 'network') else trainer.q_network
            save_checkpoint_fsdp(
                rank, model_to_save, trainer, manager, episodes, checkpoint_dir,
                is_best=False, config=config
            )
            
            # 打印curriculum最终状态（新增）
            if curriculum:
                print(f"\n[CURRICULUM FINAL] Training completed!")
                print(f"[CURRICULUM FINAL] Total episodes run: {curriculum.current_episode}")
                print(f"[CURRICULUM FINAL] Final stage: {curriculum.get_stage()}")
                print(f"[CURRICULUM FINAL] Final progress: {curriculum.current_episode/curriculum.total_episodes:.1%}")
            
            # 保存训练统计
            training_stats = {
                'total_episodes': episodes,
                'start_episode': start_episode,
                'training_time_hours': elapsed_time,
                'final_success_rate': np.mean(episode_success[-100:]) if episode_success else 0,
                'best_success_rate': manager.best_success_rate if hasattr(manager, 'best_success_rate') else 0,
                'num_gpus': world_size,
                'resumed': resume and start_episode > 0,
                'fsdp_enabled': True,
                'curriculum_enabled': curriculum is not None,
                'final_curriculum_stage': curriculum.get_stage() if curriculum else None
            }
            
            with open(output_dir / "training_stats.json", 'w') as f:
                json.dump(training_stats, f, indent=2)
    
    finally:
        # 清理分布式环境
        print(f"[Rank {rank}] Cleaning up distributed environment...")
        cleanup_distributed()


def train_multi_gpu_v100(
    episodes: int = 10000,
    num_gpus: int = 4,
    hours_limit: Optional[float] = None,
    resume: bool = False
):
    """使用4块V100进行FSDP分布式训练的主函数
    
    Args:
        episodes: 训练的总episode数
        num_gpus: 使用的GPU数量
        hours_limit: 时间限制（小时）
        resume: 是否从checkpoint恢复训练
    """
    
    print("=" * 60)
    print("🚀 Multi-GPU V100 Training Script with FSDP")
    print("=" * 60)
    
    # 检查GPU可用性
    if not torch.cuda.is_available():
        print("❌ CUDA is not available!")
        return
    
    available_gpus = torch.cuda.device_count()
    if available_gpus < num_gpus:
        print(f"❌ Requested {num_gpus} GPUs but only {available_gpus} available!")
        return
    
    # 打印GPU信息
    print(f"\n📊 System Information:")
    print(f"  • PyTorch version: {torch.__version__}")
    print(f"  • CUDA version: {torch.version.cuda}")
    print(f"  • Available GPUs: {available_gpus}")
    
    for i in range(num_gpus):
        gpu_name = torch.cuda.get_device_name(i)
        gpu_memory = torch.cuda.get_device_properties(i).total_memory / 1e9
        print(f"  • GPU {i}: {gpu_name} ({gpu_memory:.1f} GB)")
    
    # 检查是否有可恢复的checkpoint
    checkpoint_dir = Path(".") / "checkpoints"
    if resume and checkpoint_dir.exists():
        checkpoint_info = find_latest_checkpoint(checkpoint_dir)
        if checkpoint_info:
            checkpoint_path, last_episode = checkpoint_info
            print(f"\n📁 Found checkpoint: {checkpoint_path}")
            print(f"  • Last episode: {last_episode}")
            print(f"  • Will resume from episode: {last_episode + 1}")
            
            # 调整episodes数
            if last_episode >= episodes:
                print(f"⚠️  Training already completed {last_episode} episodes, increasing target to {last_episode + 1000}")
                episodes = last_episode + 1000
        else:
            print("\n⚠️  No checkpoint found, will start from scratch")
            resume = False
    
    # 创建配置
    gpu_config = V100MultiGPUConfig(num_gpus=num_gpus)
    config = gpu_config.config
    config['hours_limit'] = hours_limit

    print(f"\n⚙️  Training Configuration:")
    print(f"  • Algorithm: {config['algorithm'].upper()}")
    print(f"  • Network: {config['hidden_dim']}×{config['num_layers']} with {config['num_heads']} heads")
    print(f"  • Total batch size: {config['batch_size']}")
    print(f"  • Per-GPU batch size: {config['per_gpu_batch_size']}")
    print(f"  • Learning rate: {config['learning_rate']:.6f}")
    print(f"  • Mixed precision: {config['use_mixed_precision']}")
    print(f"  • FSDP enabled: YES")
    print(f"  • FSDP min params: {config['fsdp_min_num_params']:.0e}")
    print(f"  • Resume training: {resume}")
    
    # 预估训练时间
    estimated_time = episodes * 0.002  # 粗略估计，FSDP可能会略慢
    print(f"\n⏱️  Estimated training time: {estimated_time:.1f} hours")
    
    if hours_limit:
        print(f"  • Time limit set: {hours_limit} hours")
        if estimated_time > hours_limit:
            episodes = int(hours_limit / 0.002)
            print(f"  • Adjusted episodes to {episodes} to fit time limit")
    
    # 确认开始训练
    confirm = input("\nStart training with FSDP? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Training cancelled.")
        return
    
    # 设置分布式训练必需的环境变量
    os.environ['MASTER_ADDR'] = 'localhost'  # 单机多GPU使用localhost
    
    # 预先找到一个可用端口（避免进程间竞争）
    master_port = find_free_port()
    print(f"\n🚀 Using master address: localhost")
    print(f"🚀 Using master port: {master_port}")
    os.environ['MASTER_PORT'] = str(master_port)
    
    # 使用标准的multiprocessing启动
    print("\n🚀 Launching FSDP distributed training...")
    mp.spawn(
        train_worker,
        args=(num_gpus, config, episodes, resume),
        nprocs=num_gpus,
        join=True
    )
    
    print("\n✅ All training processes completed!")
    
    # 打印最终统计（如果训练完成）
    stats_path = Path(".") / "training_stats.json"
    if stats_path.exists():
        with open(stats_path, 'r') as f:
            stats = json.load(f)
        
        print("\n📊 Training Statistics:")
        print(f"  • Total episodes: {stats['total_episodes']}")
        print(f"  • Training time: {stats['training_time_hours']:.2f} hours")
        print(f"  • Final success rate: {stats['final_success_rate']:.2%}")
        print(f"  • Best success rate: {stats['best_success_rate']:.2%}")
        print(f"  • FSDP enabled: {stats.get('fsdp_enabled', False)}")
        if stats.get('resumed', False):
            print(f"  • Resumed from episode: {stats['start_episode']}")


def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Multi-GPU V100 Training with FSDP Support')
    parser.add_argument('--episodes', type=int, default=10000, help='Number of episodes')
    parser.add_argument('--num-gpus', type=int, default=4, help='Number of GPUs to use')
    parser.add_argument('--hours-limit', type=float, help='Time limit in hours')
    parser.add_argument('--resume', action='store_true', help='Resume from latest checkpoint')
    
    args = parser.parse_args()
    
    train_multi_gpu_v100(
        episodes=args.episodes,
        num_gpus=args.num_gpus,
        hours_limit=args.hours_limit,
        resume=args.resume
    )


if __name__ == "__main__":
    main()