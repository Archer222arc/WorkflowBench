#!/usr/bin/env python3
"""
Mac M1 PPO整晚训练脚本
针对Apple Silicon优化，包含内存管理和性能监控
"""

import os
import sys
import json
import time
import psutil
import torch
import subprocess
from datetime import datetime
from pathlib import Path

# Mac M1优化设置
os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'  # 启用MPS回退
os.environ['MKL_NUM_THREADS'] = '1'  # 减少线程竞争
os.environ['OMP_NUM_THREADS'] = '1'

def check_system():
    """检查系统状态"""
    print("🖥️  系统检查...")
    print(f"  • Python版本: {sys.version.split()[0]}")
    print(f"  • PyTorch版本: {torch.__version__}")
    print(f"  • MPS可用: {torch.backends.mps.is_available()}")
    print(f"  • CPU核心数: {psutil.cpu_count()}")
    print(f"  • 总内存: {psutil.virtual_memory().total / (1024**3):.1f} GB")
    print(f"  • 可用内存: {psutil.virtual_memory().available / (1024**3):.1f} GB")

def monitor_resources():
    """监控资源使用"""
    memory = psutil.virtual_memory()
    cpu_percent = psutil.cpu_percent(interval=1)
    
    # 获取GPU使用情况（Mac M1）
    try:
        result = subprocess.run(['powermetrics', '-i', '1000', '-n', '1', '--samplers', 'gpu_power'], 
                              capture_output=True, text=True, check=True)
        gpu_info = "GPU活跃"
    except:
        gpu_info = "GPU监控不可用"
    
    return {
        'memory_percent': memory.percent,
        'memory_gb': memory.used / (1024**3),
        'cpu_percent': cpu_percent,
        'gpu_info': gpu_info
    }

def create_enhanced_config():
    """创建增强的配置"""
    base_config = {
        "learning_rate": 0.0001,
        "batch_size": 128,  # Mac M1友好的批量大小
        "memory_size": 100000,
        "gamma": 0.99,
        "hidden_dim": 512,  # 增强的网络容量
        
        # PPO参数
        "n_steps": 2048,
        "n_epochs": 10,
        "clip_range": 0.2,
        "ent_coef": 0.01,
        "vf_coef": 0.5,
        "gae_lambda": 0.95,
        "max_grad_norm": 0.5,
        
        # Teacher guidance
        "use_teacher_guidance": True,
        "teacher_guidance_start_prob": 0.1,
        "teacher_guidance_decay": 0.995,
        "teacher_guidance_min_prob": 0.05,
        "episode_guidance_mode": True,
        
        # Task-aware buffer
        "use_task_aware_buffer": True,
        "buffer_capacity_per_task": 200,
        "min_episodes_per_task": 20,
        "prioritize_medium_reward": True,
        "task_mix_ratio": 0.7,
        
        # 训练设置
        "use_curriculum": True,
        "use_action_masking": True,
        "checkpoint_frequency": 100,
        "evaluation_frequency": 100,
        "evaluation_episodes": 20,
        "max_episode_length": 30,
        
        # 网络增强参数
        "num_heads": 4,
        "num_layers": 3,
        "dropout": 0.1,
        "rag_dim": 64,
        "use_mac_optimization": True
    }
    
    # 保存配置
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)
    config_path = config_dir / "ppo_m1_overnight_config.json"
    
    with open(config_path, 'w') as f:
        json.dump(base_config, f, indent=2)
    
    return config_path

def run_training(episodes=5000, task_types=None, resume=False):
    """运行训练"""
    config_path = create_enhanced_config()
    
    # 构建命令
    cmd = [
        sys.executable, "main.py", "train",
        "--algorithm", "ppo",
        "--episodes", str(episodes),
        "--use-task-aware"
    ]
    
    if resume:
        cmd.append("--resume")
    
    if task_types:
        cmd.extend(["--task-types"] + task_types)
    
    print(f"\n🚀 开始训练...")
    print(f"命令: {' '.join(cmd)}")
    
    # 运行训练
    start_time = time.time()
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                             universal_newlines=True, bufsize=1)
    
    # 实时输出和监控
    try:
        for line in process.stdout:
            print(line, end='')
            
            # 每隔一段时间显示资源使用
            if "Episode" in line and "00]" in line:  # 每100个episode
                resources = monitor_resources()
                print(f"\n📊 资源使用: 内存 {resources['memory_gb']:.1f}GB ({resources['memory_percent']:.1f}%), "
                      f"CPU {resources['cpu_percent']:.1f}%, {resources['gpu_info']}")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  训练被用户中断")
        process.terminate()
        return
    
    process.wait()
    elapsed_time = (time.time() - start_time) / 3600
    print(f"\n✅ 训练完成! 总用时: {elapsed_time:.2f} 小时")

def main():
    """主函数"""
    print("=" * 60)
    print("🌙 Mac M1 PPO整晚训练脚本")
    print("=" * 60)
    
    # 系统检查
    check_system()
    
    # 询问训练选项
    print("\n📋 训练选项:")
    print("1. 训练所有任务类型 (推荐)")
    print("2. 训练特定任务类型")
    print("3. 从checkpoint恢复训练")
    
    choice = input("\n选择 (1-3): ").strip()
    
    episodes = 5000  # 整晚训练的默认episodes数
    task_types = None
    resume = False
    
    if choice == "2":
        print("\n可用的任务类型:")
        print("- basic_task")
        print("- simple_task") 
        print("- data_pipeline")
        print("- api_integration")
        print("- multi_stage_pipeline")
        
        types_input = input("\n输入任务类型（空格分隔）: ").strip()
        task_types = types_input.split() if types_input else None
    
    elif choice == "3":
        resume = True
        
    # 询问训练轮数
    episodes_input = input(f"\n训练轮数 (默认 {episodes}): ").strip()
    if episodes_input.isdigit():
        episodes = int(episodes_input)
    
    # 开始训练
    print(f"\n⏰ 预计训练时间: {episodes * 0.005:.1f} - {episodes * 0.01:.1f} 小时")
    confirm = input("开始训练? (y/n): ").strip().lower()
    
    if confirm == 'y':
        # 设置Mac省电模式（防止睡眠）
        print("\n💡 提示: 请确保Mac设置为'防止睡眠'模式")
        print("   系统偏好设置 > 节能 > 防止电脑自动睡眠")
        input("按Enter继续...")
        
        run_training(episodes, task_types, resume)
    else:
        print("训练已取消")

if __name__ == "__main__":
    main()
