#!/usr/bin/env python3
"""
智能渐进式训练脚本 - 支持模型架构动态变化
通过知识蒸馏和权重迁移实现不同大小模型间的平滑过渡
"""

import os
import sys
import json
import time
import torch
import torch.nn as nn
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
import logging
import argparse
from collections import OrderedDict

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WeightTransferManager:
    """智能权重迁移管理器"""
    
    def __init__(self):
        self.transfer_stats = {
            'direct_copy': 0,
            'resized': 0,
            'partially_transferred': 0,
            'new_init': 0
        }
    
    def transfer_linear_weights(self, old_weight: torch.Tensor, new_weight: torch.Tensor) -> torch.Tensor:
        """迁移Linear层权重"""
        old_out, old_in = old_weight.shape
        new_out, new_in = new_weight.shape
        
        # 创建新权重张量
        transferred = new_weight.clone()
        
        # 如果新模型更大，先用Xavier初始化
        if new_out > old_out or new_in > old_in:
            nn.init.xavier_uniform_(transferred)
        
        # 复制重叠部分
        min_out = min(old_out, new_out)
        min_in = min(old_in, new_in)
        transferred[:min_out, :min_in] = old_weight[:min_out, :min_in]
        
        # 如果输入维度增加，对新增部分使用均值填充
        if new_in > old_in:
            # 使用已有权重的统计信息初始化新增部分
            mean_val = old_weight[:min_out, :].mean().item()
            std_val = old_weight[:min_out, :].std().item()
            transferred[:min_out, old_in:new_in] = torch.randn(min_out, new_in - old_in) * std_val + mean_val
        
        # 如果输出维度增加，使用类似的策略
        if new_out > old_out:
            for i in range(old_out, new_out):
                # 使用已有神经元的线性组合
                idx1, idx2 = np.random.choice(old_out, 2, replace=False)
                alpha = np.random.uniform(0.3, 0.7)
                transferred[i, :min_in] = alpha * old_weight[idx1, :min_in] + (1 - alpha) * old_weight[idx2, :min_in]
        
        return transferred
    
    def transfer_conv_weights(self, old_weight: torch.Tensor, new_weight: torch.Tensor) -> torch.Tensor:
        """迁移卷积层权重"""
        # 对于Transformer架构，通常不需要，但保留以备用
        return new_weight
    
    def transfer_norm_weights(self, old_weight: torch.Tensor, new_weight: torch.Tensor) -> torch.Tensor:
        """迁移归一化层权重"""
        old_size = old_weight.shape[0]
        new_size = new_weight.shape[0]
        
        transferred = new_weight.clone()
        min_size = min(old_size, new_size)
        
        # 直接复制重叠部分
        transferred[:min_size] = old_weight[:min_size]
        
        # 新增部分使用已有参数的均值
        if new_size > old_size:
            transferred[old_size:] = old_weight.mean()
        
        return transferred
    
    def intelligent_weight_transfer(self, old_state_dict: Dict[str, torch.Tensor], 
                                   new_model: nn.Module) -> Dict[str, torch.Tensor]:
        """执行智能权重迁移"""
        new_state_dict = new_model.state_dict()
        transferred_dict = OrderedDict()
        
        logger.info("\n" + "="*60)
        logger.info("🧠 Starting Intelligent Weight Transfer")
        logger.info("="*60)
        
        for key, new_param in new_state_dict.items():
            if key in old_state_dict:
                old_param = old_state_dict[key]
                
                # 完全匹配 - 直接复制
                if old_param.shape == new_param.shape:
                    transferred_dict[key] = old_param
                    self.transfer_stats['direct_copy'] += 1
                    logger.debug(f"✓ Direct copy: {key} {old_param.shape}")
                
                # 需要调整大小
                else:
                    logger.info(f"🔄 Resizing: {key} from {old_param.shape} to {new_param.shape}")
                    
                    # Linear层权重
                    if 'weight' in key and len(old_param.shape) == 2:
                        transferred_dict[key] = self.transfer_linear_weights(old_param, new_param)
                        self.transfer_stats['resized'] += 1
                    
                    # 偏置或归一化参数
                    elif len(old_param.shape) == 1:
                        transferred_dict[key] = self.transfer_norm_weights(old_param, new_param)
                        self.transfer_stats['resized'] += 1
                    
                    # 多头注意力的特殊处理
                    elif 'attention' in key and len(old_param.shape) > 2:
                        # 重塑并迁移
                        old_shape = old_param.shape
                        new_shape = new_param.shape
                        
                        if len(old_shape) == len(new_shape):
                            # 尝试逐维度迁移
                            transferred = new_param.clone()
                            for dim in range(len(old_shape)):
                                min_size = min(old_shape[dim], new_shape[dim])
                                slices = [slice(None)] * len(old_shape)
                                slices[dim] = slice(0, min_size)
                                transferred[tuple(slices)] = old_param[tuple(slices)]
                            transferred_dict[key] = transferred
                            self.transfer_stats['partially_transferred'] += 1
                        else:
                            transferred_dict[key] = new_param
                            self.transfer_stats['new_init'] += 1
                    
                    else:
                        # 无法智能迁移，使用新初始化
                        transferred_dict[key] = new_param
                        self.transfer_stats['new_init'] += 1
                        logger.warning(f"⚠️ Cannot transfer {key}, using new initialization")
            
            else:
                # 新参数
                transferred_dict[key] = new_param
                self.transfer_stats['new_init'] += 1
                logger.debug(f"✗ New parameter: {key}")
        
        # 打印迁移统计
        logger.info("\n📊 Transfer Statistics:")
        logger.info(f"  • Direct copies: {self.transfer_stats['direct_copy']}")
        logger.info(f"  • Resized: {self.transfer_stats['resized']}")
        logger.info(f"  • Partially transferred: {self.transfer_stats['partially_transferred']}")
        logger.info(f"  • New initializations: {self.transfer_stats['new_init']}")
        logger.info("="*60 + "\n")
        
        return transferred_dict


class ProgressiveStage:
    """训练阶段配置"""
    
    def __init__(self, name: str, difficulty: str, episodes: int, config: Dict[str, Any]):
        self.name = name
        self.difficulty = difficulty
        self.episodes = episodes
        self.config = config
        self.start_time = None
        self.end_time = None
        self.metrics = {}


class SmartProgressiveTrainer:
    """智能渐进式训练器"""
    
    def __init__(self, base_output_dir: str = "smart_progressive_training"):
        self.base_output_dir = Path(base_output_dir)
        self.base_output_dir.mkdir(exist_ok=True)
        
        # 权重迁移管理器
        self.weight_transfer_manager = WeightTransferManager()
        
        # 基础配置
        self.base_config = {
            "algorithm": "ppo",
            "device": "cuda",
            "use_mixed_precision": True,
            "use_task_aware_buffer": True,
            "use_curriculum": True,
            "use_lr_scheduler": True,
            "lr_schedule": "cosine",
            "use_auxiliary_tasks": True,
            "use_curiosity": True,
            "num_heads": 4,
            "dropout": 0.1,
            "activation": "gelu",
            "use_layer_norm": True,
            "n_epochs": 10,
            "gamma": 0.99,
            "gae_lambda": 0.95,
            "max_grad_norm": 0.5,
        }
        
        # 训练阶段定义
        self.stages = [
            ProgressiveStage(
                name="🌱 Foundation (Very Easy)",
                difficulty="very_easy",
                episodes=400,
                config={
                    "hidden_dim": 256,
                    "num_layers": 2,
                    "learning_rate": 0.0003,
                    "batch_size": 128,
                    "mini_batch_size": 32,
                    "ent_coef": 0.02,
                    "clip_range": 0.3,
                    "n_steps": 1024,
                    "intrinsic_reward_scale": 0.2,
                    "dropout": 0.15,
                }
            ),
            ProgressiveStage(
                name="🌿 Skill Building (Easy)",
                difficulty="easy",
                episodes=400,
                config={
                    "hidden_dim": 384,  # 架构增长！
                    "num_layers": 3,    # 层数增加！
                    "learning_rate": 0.0002,
                    "batch_size": 192,
                    "mini_batch_size": 48,
                    "ent_coef": 0.015,
                    "clip_range": 0.25,
                    "n_steps": 1536,
                    "intrinsic_reward_scale": 0.15,
                    "dropout": 0.12,
                }
            ),
            ProgressiveStage(
                name="🌳 Competence (Medium)",
                difficulty="medium",
                episodes=600,
                config={
                    "hidden_dim": 512,  # 继续增长！
                    "num_layers": 3,
                    "learning_rate": 0.00015,
                    "batch_size": 256,
                    "mini_batch_size": 64,
                    "ent_coef": 0.01,
                    "clip_range": 0.2,
                    "n_steps": 2048,
                    "intrinsic_reward_scale": 0.1,
                    "dropout": 0.1,
                    "l2_reg": 0.0001,
                }
            ),
            ProgressiveStage(
                name="💪 Mastery (Hard)",
                difficulty="hard",
                episodes=400,
                config={
                    "hidden_dim": 512,  # 保持稳定
                    "num_layers": 3,
                    "learning_rate": 0.0001,
                    "batch_size": 256,
                    "mini_batch_size": 64,
                    "ent_coef": 0.005,
                    "clip_range": 0.15,
                    "n_steps": 2048,
                    "intrinsic_reward_scale": 0.05,
                    "dropout": 0.08,
                    "l2_reg": 0.0002,
                    "gradient_penalty": 0.001,
                }
            ),
            ProgressiveStage(
                name="🏆 Expert (Mixed)",
                difficulty="all_difficulties",
                episodes=600,
                config={
                    "hidden_dim": 512,
                    "num_layers": 3,
                    "learning_rate": 0.00005,
                    "batch_size": 256,
                    "mini_batch_size": 64,
                    "ent_coef": 0.001,
                    "clip_range": 0.1,
                    "n_steps": 2048,
                    "intrinsic_reward_scale": 0.01,
                    "dropout": 0.05,
                    "l2_reg": 0.0003,
                    "gradient_penalty": 0.001,
                    "lr_warmup_steps": 50,
                }
            )
        ]
        
        # 训练历史
        self.training_history = []
        self.current_checkpoint = None
    
    def create_stage_config(self, stage: ProgressiveStage) -> Path:
        """创建阶段配置文件"""
        # 合并基础配置和阶段配置
        full_config = {**self.base_config, **stage.config}
        
        # 保存配置
        stage_dir = self.base_output_dir / f"stage_{len(self.training_history)+1}_{stage.difficulty}"
        stage_dir.mkdir(exist_ok=True)
        
        config_path = stage_dir / "config.json"
        with open(config_path, 'w') as f:
            json.dump(full_config, f, indent=2)
        
        return config_path, stage_dir
    
    def load_and_transfer_model(self, old_checkpoint_path: Path, new_config: Dict[str, Any]) -> Optional[Path]:
        """加载旧模型并迁移到新架构"""
        try:
            # 加载旧checkpoint
            old_checkpoint = torch.load(old_checkpoint_path, map_location='cpu')
            old_config = old_checkpoint.get('config', {})
            
            # 检查是否需要架构迁移
            architecture_changed = (
                old_config.get('hidden_dim') != new_config.get('hidden_dim') or
                old_config.get('num_layers') != new_config.get('num_layers') or
                old_config.get('num_heads') != new_config.get('num_heads')
            )
            
            if not architecture_changed:
                logger.info("✓ Architecture unchanged, direct resume possible")
                return old_checkpoint_path
            
            logger.info("\n🔄 Architecture changed, performing intelligent transfer...")
            logger.info(f"  Old: hidden_dim={old_config.get('hidden_dim')}, layers={old_config.get('num_layers')}")
            logger.info(f"  New: hidden_dim={new_config.get('hidden_dim')}, layers={new_config.get('num_layers')}")
            
            # 创建临时的训练管理器来构建新模型
            sys.path.append(str(Path(__file__).parent))
            from unified_training_manager import UnifiedTrainingManager
            
            # 创建临时配置文件
            temp_config_path = self.base_output_dir / "temp_config.json"
            with open(temp_config_path, 'w') as f:
                json.dump(new_config, f)
            
            # 创建新架构的管理器
            temp_manager = UnifiedTrainingManager(
                config_path=str(temp_config_path),
                algorithm=new_config.get('algorithm', 'ppo')
            )
            
            # 设置环境以获得正确的模型
            if not temp_manager.setup_environment():
                raise RuntimeError("Failed to setup environment for new model")
            
            # 获取旧的state_dict
            old_state_dict = None
            if 'network_state_dict' in old_checkpoint:
                old_state_dict = old_checkpoint['network_state_dict']
            elif 'model_state_dict' in old_checkpoint:
                old_state_dict = old_checkpoint['model_state_dict']
            elif 'q_network_state_dict' in old_checkpoint:
                old_state_dict = old_checkpoint['q_network_state_dict']
            
            if old_state_dict is None:
                logger.error("Could not find model state dict in checkpoint!")
                return None
            
            # 执行智能权重迁移
            new_model = temp_manager.trainer.network if hasattr(temp_manager.trainer, 'network') else temp_manager.trainer.q_network
            transferred_state_dict = self.weight_transfer_manager.intelligent_weight_transfer(
                old_state_dict,
                new_model
            )
            
            # 加载迁移后的权重
            new_model.load_state_dict(transferred_state_dict)
            
            # 创建新的checkpoint
            new_checkpoint = {
                'algorithm': new_config.get('algorithm', 'ppo'),
                'state_dim': temp_manager.env.get_state_dim(),
                'action_dim': temp_manager.env.num_actions,
                'config': new_config,
                'episode': old_checkpoint.get('episode', 0),
                'timestamp': datetime.now().isoformat(),
                'transferred_from': str(old_checkpoint_path),
                'architecture_migration': True
            }
            
            # 保存网络状态
            if hasattr(temp_manager.trainer, 'network'):
                new_checkpoint['network_state_dict'] = new_model.state_dict()
            else:
                new_checkpoint['q_network_state_dict'] = new_model.state_dict()
            
            # 保存训练历史（如果有）
            if 'training_history' in old_checkpoint:
                new_checkpoint['training_history'] = old_checkpoint['training_history']
            
            # 保存迁移后的checkpoint
            migrated_checkpoint_path = self.base_output_dir / f"migrated_checkpoint_stage_{len(self.training_history)+1}.pt"
            torch.save(new_checkpoint, migrated_checkpoint_path)
            
            logger.info(f"✅ Model successfully migrated and saved to {migrated_checkpoint_path}")
            
            # 清理临时文件
            temp_config_path.unlink()
            
            return migrated_checkpoint_path
            
        except Exception as e:
            logger.error(f"❌ Model migration failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def run_stage(self, stage: ProgressiveStage, resume_checkpoint: Optional[Path] = None) -> Tuple[bool, Optional[Path]]:
        """运行单个训练阶段"""
        stage.start_time = time.time()
        
        logger.info("\n" + "="*70)
        logger.info(f"🚀 Starting {stage.name}")
        logger.info(f"📊 Episodes: {stage.episodes}")
        logger.info(f"🧠 Architecture: hidden_dim={stage.config['hidden_dim']}, layers={stage.config['num_layers']}")
        logger.info("="*70 + "\n")
        
        # 创建阶段配置
        config_path, stage_dir = self.create_stage_config(stage)
        
        # 处理模型迁移（如果需要）
        actual_resume_checkpoint = None
        if resume_checkpoint:
            migrated_checkpoint = self.load_and_transfer_model(resume_checkpoint, {**self.base_config, **stage.config})
            if migrated_checkpoint:
                actual_resume_checkpoint = migrated_checkpoint
            else:
                logger.warning("⚠️ Model migration failed, starting fresh for this stage")
        
        # 准备训练命令
        cmd = [
            sys.executable,  # 使用当前Python解释器
            "gpu_training_script.py",
            "--episodes", str(stage.episodes),
            "--config", str(config_path),
        ]
        
        # 如果有可用的checkpoint，添加resume参数
        if actual_resume_checkpoint:
            cmd.extend(["--resume", "--checkpoint", str(actual_resume_checkpoint)])
        
        # 设置环境变量
        env = os.environ.copy()
        
        # 设置任务库路径
        if stage.difficulty == "all_difficulties":
            task_library = "mcp_generated_library/task_library_all_difficulties.json"
        else:
            task_library = f"mcp_generated_library/difficulty_versions/task_library_enhanced_v3_{stage.difficulty}.json"
        
        env['TASK_LIBRARY_PATH'] = task_library
        env['TRAINING_STAGE_DIR'] = str(stage_dir)
        
        # 运行训练
        logger.info(f"📍 Executing: {' '.join(cmd)}")
        logger.info(f"📚 Task library: {task_library}")
        
        try:
            import subprocess
            result = subprocess.run(cmd, env=env, check=True)
            
            # 查找生成的checkpoint
            checkpoint_pattern = stage_dir / "checkpoints" / "*.pt"
            checkpoints = list(Path(stage_dir).glob("checkpoints/*.pt"))
            
            if not checkpoints:
                # 尝试默认位置
                default_checkpoint = Path("gpu_4070_training/checkpoints/final_gpu_model.pt")
                if default_checkpoint.exists():
                    checkpoints = [default_checkpoint]
            
            if checkpoints:
                # 选择最新的checkpoint
                latest_checkpoint = max(checkpoints, key=lambda p: p.stat().st_mtime)
                stage.end_time = time.time()
                stage.metrics['duration'] = stage.end_time - stage.start_time
                stage.metrics['success'] = True
                
                logger.info(f"✅ Stage completed in {stage.metrics['duration']/60:.1f} minutes")
                return True, latest_checkpoint
            else:
                logger.error("❌ No checkpoint found after training!")
                return False, None
                
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Training failed with error code {e.returncode}")
            return False, None
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return False, None
    
    def run_progressive_training(self, start_stage: int = 0):
        """运行完整的渐进式训练"""
        logger.info("\n" + "🌟"*30)
        logger.info("🎯 SMART PROGRESSIVE TRAINING")
        logger.info("🧠 With Intelligent Weight Transfer")
        logger.info("🌟"*30 + "\n")
        
        total_start_time = time.time()
        current_checkpoint = self.current_checkpoint
        
        for i, stage in enumerate(self.stages[start_stage:], start=start_stage):
            success, checkpoint_path = self.run_stage(stage, current_checkpoint)
            
            if success:
                self.training_history.append({
                    'stage': i,
                    'name': stage.name,
                    'difficulty': stage.difficulty,
                    'episodes': stage.episodes,
                    'checkpoint': str(checkpoint_path),
                    'metrics': stage.metrics
                })
                current_checkpoint = checkpoint_path
                self.current_checkpoint = checkpoint_path
                
                # 保存训练历史
                self.save_training_history()
                
                # 阶段间休息
                if i < len(self.stages) - 1:
                    logger.info("\n⏸️  Resting before next stage (10 seconds)...")
                    time.sleep(10)
            else:
                logger.error(f"❌ Stage {stage.name} failed! Stopping training.")
                break
        
        # 训练总结
        total_time = time.time() - total_start_time
        total_episodes = sum(s.episodes for s in self.stages[:len(self.training_history)])
        
        logger.info("\n" + "="*70)
        logger.info("📊 TRAINING SUMMARY")
        logger.info("="*70)
        logger.info(f"✅ Completed stages: {len(self.training_history)}/{len(self.stages)}")
        logger.info(f"⏱️  Total time: {total_time/3600:.2f} hours")
        logger.info(f"🎮 Total episodes: {total_episodes}")
        
        if self.current_checkpoint:
            logger.info(f"💾 Final model: {self.current_checkpoint}")
        
        # 分析架构变化的影响
        self.analyze_architecture_progression()
    
    def save_training_history(self):
        """保存训练历史"""
        history_path = self.base_output_dir / "training_history.json"
        with open(history_path, 'w') as f:
            json.dump(self.training_history, f, indent=2)
    
    def analyze_architecture_progression(self):
        """分析架构变化对性能的影响"""
        logger.info("\n📈 Architecture Progression Analysis:")
        
        for i, record in enumerate(self.training_history):
            stage_config = self.stages[i].config
            logger.info(f"\nStage {i+1}: {record['name']}")
            logger.info(f"  • Hidden dim: {stage_config.get('hidden_dim')}")
            logger.info(f"  • Layers: {stage_config.get('num_layers')}")
            logger.info(f"  • Duration: {record['metrics'].get('duration', 0)/60:.1f} min")
    
    def create_final_ensemble(self):
        """创建最终的集成模型（可选）"""
        logger.info("\n🎭 Creating ensemble from all stages...")
        # 这里可以实现模型集成逻辑
        pass


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Smart Progressive Training with Architecture Evolution"
    )
    parser.add_argument(
        "--start-stage", 
        type=int, 
        default=0, 
        help="Start from specific stage (0-indexed)"
    )
    parser.add_argument(
        "--output-dir", 
        type=str, 
        default="smart_progressive_training",
        help="Output directory for all stages"
    )
    parser.add_argument(
        "--resume", 
        type=str, 
        help="Resume from specific checkpoint path"
    )
    parser.add_argument(
        "--test-transfer", 
        action="store_true",
        help="Test weight transfer without training"
    )
    
    args = parser.parse_args()
    
    # 创建训练器
    trainer = SmartProgressiveTrainer(base_output_dir=args.output_dir)
    
    # 如果指定了恢复checkpoint
    if args.resume:
        trainer.current_checkpoint = Path(args.resume)
        logger.info(f"📂 Resuming from checkpoint: {args.resume}")
    
    # 测试模式
    if args.test_transfer:
        logger.info("🧪 Running in test mode - weight transfer only")
        # 这里可以添加测试权重迁移的代码
        return
    
    # 运行渐进式训练
    trainer.run_progressive_training(start_stage=args.start_stage)


if __name__ == "__main__":
    main()