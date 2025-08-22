#!/usr/bin/env python3
"""
训练曲线可视化脚本
==================
从checkpoint加载训练历史并画出三个关键曲线：
1. Success Rate（成功率）
2. Reward（奖励）
3. Episode Length（episode长度）

注意：如果使用PyTorch 2.6+，脚本会自动处理weights_only加载问题
"""

import torch
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import argparse
import json
from typing import List, Dict, Any, Optional

# 设置matplotlib风格
try:
    plt.style.use('seaborn-v0_8-darkgrid')
except:
    try:
        plt.style.use('seaborn-darkgrid')
    except:
        plt.style.use('default')
        print("⚠️  Using default matplotlib style")

try:
    sns.set_palette("husl")
except:
    pass

def calculate_moving_average(data: List[float], window_size: int) -> List[float]:
    """计算移动平均"""
    moving_avg = []
    for i in range(len(data)):
        start = max(0, i - window_size + 1)
        window = data[start:i+1]
        moving_avg.append(np.mean(window))
    return moving_avg

def plot_success_rate(success_history: List[float], output_dir: Path, window_size: int = 50):
    """画成功率曲线"""
    plt.figure(figsize=(12, 6))
    
    # 原始数据（透明度较低）
    episodes = list(range(1, len(success_history) + 1))
    plt.plot(episodes, success_history, alpha=0.3, label='Episode Success', color='blue')
    
    # 移动平均（主曲线）
    moving_avg = calculate_moving_average(success_history, window_size)
    plt.plot(episodes, moving_avg, label=f'Moving Average ({window_size} episodes)', 
             color='darkblue', linewidth=2)
    
    # 添加整体趋势线
    if len(episodes) > 10:
        z = np.polyfit(episodes, success_history, 1)
        p = np.poly1d(z)
        plt.plot(episodes, p(episodes), "--", alpha=0.8, 
                label=f'Trend (slope={z[0]:.4f})', color='red')
    
    plt.xlabel('Episode')
    plt.ylabel('Success Rate')
    plt.title('Training Progress: Success Rate')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 添加统计信息
    final_success = np.mean(success_history[-100:]) if len(success_history) >= 100 else np.mean(success_history)
    plt.text(0.02, 0.98, f'Final Success Rate: {final_success:.2%}', 
             transform=plt.gca().transAxes, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig(output_dir / 'success_rate_curve.png', dpi=300)
    plt.close()
    print(f"✓ Success rate curve saved to {output_dir / 'success_rate_curve.png'}")

def plot_reward_curve(reward_history: List[float], output_dir: Path, window_size: int = 50):
    """画奖励曲线"""
    plt.figure(figsize=(12, 6))
    
    episodes = list(range(1, len(reward_history) + 1))
    
    # 原始奖励（散点图）
    plt.scatter(episodes, reward_history, alpha=0.3, s=10, label='Episode Reward', color='green')
    
    # 移动平均
    moving_avg = calculate_moving_average(reward_history, window_size)
    plt.plot(episodes, moving_avg, label=f'Moving Average ({window_size} episodes)', 
             color='darkgreen', linewidth=2)
    
    # 添加四分位数范围
    if len(reward_history) >= window_size:
        lower_quartile = []
        upper_quartile = []
        for i in range(len(reward_history)):
            start = max(0, i - window_size + 1)
            window = reward_history[start:i+1]
            lower_quartile.append(np.percentile(window, 25))
            upper_quartile.append(np.percentile(window, 75))
        
        plt.fill_between(episodes, lower_quartile, upper_quartile, 
                        alpha=0.2, color='green', label='25-75 percentile range')
    
    plt.xlabel('Episode')
    plt.ylabel('Total Reward')
    plt.title('Training Progress: Episode Rewards')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 添加统计信息
    avg_reward = np.mean(reward_history)
    final_avg_reward = np.mean(reward_history[-100:]) if len(reward_history) >= 100 else avg_reward
    improvement = ((final_avg_reward - np.mean(reward_history[:100])) / 
                  abs(np.mean(reward_history[:100])) * 100) if len(reward_history) >= 200 else 0
    
    stats_text = f'Average Reward: {avg_reward:.2f}\n'
    stats_text += f'Final Average: {final_avg_reward:.2f}\n'
    if improvement != 0:
        stats_text += f'Improvement: {improvement:+.1f}%'
    
    plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes, 
             verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig(output_dir / 'reward_curve.png', dpi=300)
    plt.close()
    print(f"✓ Reward curve saved to {output_dir / 'reward_curve.png'}")

def plot_episode_length(length_history: List[int], output_dir: Path, 
                       max_episode_length: int = 30, window_size: int = 50):
    """画episode长度曲线"""
    plt.figure(figsize=(12, 6))
    
    episodes = list(range(1, len(length_history) + 1))
    
    # 原始长度（条形图，稀疏显示）
    sparse_episodes = episodes[::max(1, len(episodes)//100)]  # 最多显示100个条
    sparse_lengths = length_history[::max(1, len(episodes)//100)]
    plt.bar(sparse_episodes, sparse_lengths, alpha=0.3, 
            width=max(1, len(episodes)/100), label='Episode Length', color='orange')
    
    # 移动平均
    moving_avg = calculate_moving_average(length_history, window_size)
    plt.plot(episodes, moving_avg, label=f'Moving Average ({window_size} episodes)', 
             color='darkorange', linewidth=2)
    
    # 添加最大长度参考线
    plt.axhline(y=max_episode_length, color='red', linestyle='--', 
                alpha=0.5, label=f'Max Length ({max_episode_length})')
    
    plt.xlabel('Episode')
    plt.ylabel('Episode Length (steps)')
    plt.title('Training Progress: Episode Efficiency')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.ylim(0, max_episode_length * 1.1)
    
    # 添加效率统计
    avg_length = np.mean(length_history)
    final_avg_length = np.mean(length_history[-100:]) if len(length_history) >= 100 else avg_length
    efficiency_gain = ((avg_length - final_avg_length) / avg_length * 100) if avg_length > 0 else 0
    
    stats_text = f'Average Length: {avg_length:.1f} steps\n'
    stats_text += f'Final Average: {final_avg_length:.1f} steps\n'
    if efficiency_gain > 0:
        stats_text += f'Efficiency Gain: {efficiency_gain:.1f}%'
    
    plt.text(0.98, 0.98, stats_text, transform=plt.gca().transAxes, 
             verticalalignment='top', horizontalalignment='right',
             bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig(output_dir / 'episode_length_curve.png', dpi=300)
    plt.close()
    print(f"✓ Episode length curve saved to {output_dir / 'episode_length_curve.png'}")

def plot_combined_overview(training_history: Dict[str, List], output_dir: Path):
    """创建一个综合的训练概览图"""
    fig, axes = plt.subplots(3, 1, figsize=(14, 12))
    
    # 准备数据
    success_history = training_history.get('success', [])
    reward_history = training_history.get('rewards', [])
    length_history = training_history.get('lengths', [])
    
    if not all([success_history, reward_history, length_history]):
        print("⚠️  Missing required data for combined plot")
        return
    
    episodes = list(range(1, len(success_history) + 1))
    window_size = min(50, max(10, len(episodes) // 20))
    
    # 1. Success Rate
    ax1 = axes[0]
    ax1.plot(episodes, success_history, alpha=0.2, color='blue')
    moving_avg_success = calculate_moving_average(success_history, window_size)
    ax1.plot(episodes, moving_avg_success, color='darkblue', linewidth=2)
    ax1.set_ylabel('Success Rate')
    ax1.set_title('Training Overview: Performance Metrics')
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(-0.05, 1.05)
    
    # 2. Reward
    ax2 = axes[1]
    ax2.scatter(episodes, reward_history, alpha=0.3, s=5, color='green')
    moving_avg_reward = calculate_moving_average(reward_history, window_size)
    ax2.plot(episodes, moving_avg_reward, color='darkgreen', linewidth=2)
    ax2.set_ylabel('Total Reward')
    ax2.grid(True, alpha=0.3)
    
    # 3. Episode Length
    ax3 = axes[2]
    ax3.scatter(episodes, length_history, alpha=0.3, s=5, color='orange')
    moving_avg_length = calculate_moving_average(length_history, window_size)
    ax3.plot(episodes, moving_avg_length, color='darkorange', linewidth=2)
    ax3.set_xlabel('Episode')
    ax3.set_ylabel('Episode Length')
    ax3.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'training_overview.png', dpi=300)
    plt.close()
    print(f"✓ Combined overview saved to {output_dir / 'training_overview.png'}")

def generate_training_report(checkpoint: Dict[str, Any], output_dir: Path):
    """生成训练报告"""
    report_path = output_dir / 'training_report.txt'
    
    with open(report_path, 'w') as f:
        f.write("Training Report\n")
        f.write("=" * 50 + "\n\n")
        
        # 基本信息
        f.write("## Basic Information\n")
        f.write(f"Algorithm: {checkpoint.get('algorithm', 'Unknown')}\n")
        f.write(f"Episode: {checkpoint.get('episode', 'Unknown')}\n")
        f.write(f"Timestamp: {checkpoint.get('timestamp', 'Unknown')}\n")
        f.write(f"Best Success Rate: {checkpoint.get('best_success_rate', 0):.2%}\n\n")
        
        # 训练历史统计
        if 'training_history' in checkpoint:
            history = checkpoint['training_history']
            
            f.write("## Training Statistics\n")
            
            if 'success' in history:
                success = history['success']
                f.write(f"Total Episodes: {len(success)}\n")
                f.write(f"Overall Success Rate: {np.mean(success):.2%}\n")
                f.write(f"Final 100 Success Rate: {np.mean(success[-100:]):.2%}\n")
            
            if 'rewards' in history:
                rewards = history['rewards']
                f.write(f"Average Reward: {np.mean(rewards):.2f}\n")
                f.write(f"Max Reward: {np.max(rewards):.2f}\n")
                f.write(f"Final 100 Avg Reward: {np.mean(rewards[-100:]):.2f}\n")
            
            if 'lengths' in history:
                lengths = history['lengths']
                f.write(f"Average Episode Length: {np.mean(lengths):.1f}\n")
                f.write(f"Min Episode Length: {np.min(lengths)}\n")
                f.write(f"Final 100 Avg Length: {np.mean(lengths[-100:]):.1f}\n")
        
        # 配置信息
        if 'config' in checkpoint:
            f.write("\n## Training Configuration\n")
            config = checkpoint['config']
            f.write(f"Learning Rate: {config.get('learning_rate', 'N/A')}\n")
            f.write(f"Batch Size: {config.get('batch_size', 'N/A')}\n")
            f.write(f"Gamma: {config.get('gamma', 'N/A')}\n")
            f.write(f"Hidden Dim: {config.get('hidden_dim', 'N/A')}\n")
    
    print(f"✓ Training report saved to {report_path}")

def main():
    parser = argparse.ArgumentParser(description='Visualize training curves from checkpoint')
    parser.add_argument('checkpoint_path', type=str, help='Path to checkpoint file')
    parser.add_argument('--output-dir', type=str, default='training_curves', 
                       help='Directory to save plots (default: training_curves)')
    parser.add_argument('--window-size', type=int, default=50,
                       help='Window size for moving average (default: 50)')
    parser.add_argument('--no-combined', action='store_true',
                       help='Skip combined overview plot')
    
    args = parser.parse_args()
    
    # 检查PyTorch版本
    torch_version = torch.__version__
    print(f"📦 Using PyTorch version: {torch_version}")
    if torch_version.startswith('2.6'):
        print("ℹ️  PyTorch 2.6+ detected, using weights_only=False for compatibility")
    
    # 检查checkpoint文件
    checkpoint_path = Path(args.checkpoint_path)
    if not checkpoint_path.exists():
        print(f"❌ Checkpoint file not found: {checkpoint_path}")
        return
    
    # 创建输出目录
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    print(f"📊 Loading checkpoint from {checkpoint_path}")
    
    # 加载checkpoint
    try:
        # PyTorch 2.6+ 需要设置 weights_only=False 来加载包含numpy对象的checkpoint
        checkpoint = torch.load(checkpoint_path, map_location='cpu', weights_only=False)
        print("✓ Checkpoint loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load checkpoint: {e}")
        # 尝试旧版本PyTorch的加载方式
        try:
            checkpoint = torch.load(checkpoint_path, map_location='cpu')
            print("✓ Checkpoint loaded successfully (legacy mode)")
        except Exception as e2:
            print(f"❌ Failed to load checkpoint in legacy mode: {e2}")
            return
    
    # 检查是否有训练历史
    if 'training_history' not in checkpoint:
        print("❌ No training history found in checkpoint")
        return
    
    training_history = checkpoint['training_history']
    
    # 检查必要的数据
    required_keys = ['success', 'rewards', 'lengths']
    available_keys = [k for k in required_keys if k in training_history and training_history[k]]
    
    if not available_keys:
        print("❌ No training data available in checkpoint")
        return
    
    print(f"✓ Found training data: {', '.join(available_keys)}")
    print(f"📈 Generating plots...")
    
    # 画各个曲线
    if 'success' in training_history and training_history['success']:
        plot_success_rate(training_history['success'], output_dir, args.window_size)
    
    if 'rewards' in training_history and training_history['rewards']:
        plot_reward_curve(training_history['rewards'], output_dir, args.window_size)
    
    if 'lengths' in training_history and training_history['lengths']:
        max_length = checkpoint.get('config', {}).get('max_episode_length', 30)
        plot_episode_length(training_history['lengths'], output_dir, max_length, args.window_size)
    
    # 画综合图
    if not args.no_combined and len(available_keys) == 3:
        plot_combined_overview(training_history, output_dir)
    
    # 生成报告
    generate_training_report(checkpoint, output_dir)
    
    print(f"\n✅ All plots saved to {output_dir}/")
    print("📊 Available plots:")
    for plot_file in output_dir.glob("*.png"):
        print(f"   - {plot_file.name}")

if __name__ == "__main__":
    main()