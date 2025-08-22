#!/usr/bin/env python3
"""
PPO训练实时监控脚本
显示训练进度、性能指标和资源使用情况
"""

import json
import time
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from datetime import datetime
import torch

class TrainingMonitor:
    def __init__(self, checkpoint_dir="checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.history_file = self.checkpoint_dir / "training_history.json"
        
        # 设置matplotlib
        plt.ion()  # 交互模式
        self.fig, self.axes = plt.subplots(2, 2, figsize=(12, 8))
        self.fig.suptitle('PPO Training Monitor', fontsize=16)
        
    def load_latest_checkpoint(self):
        """加载最新的checkpoint信息"""
        checkpoints = list(self.checkpoint_dir.glob("checkpoint_episode_*.pt"))
        if not checkpoints:
            return None
            
        latest = max(checkpoints, key=lambda p: p.stat().st_mtime)
        
        try:
            checkpoint = torch.load(latest, map_location='cpu')
            return {
                'episode': checkpoint.get('episode', 0),
                'success_rate': checkpoint.get('best_success_rate', 0),
                'checkpoint_file': latest.name
            }
        except:
            return None
    
    def load_training_history(self):
        """加载训练历史"""
        if self.history_file.exists():
            with open(self.history_file, 'r') as f:
                return json.load(f)
        return None
    
    def plot_metrics(self, history):
        """绘制训练指标"""
        # 清空图表
        for ax in self.axes.flat:
            ax.clear()
        
        episodes = range(len(history['rewards']))
        
        # 1. 奖励曲线
        ax = self.axes[0, 0]
        rewards = history['rewards']
        ax.plot(episodes, rewards, 'b-', alpha=0.6)
        
        # 计算移动平均
        window = min(100, len(rewards) // 10)
        if len(rewards) > window:
            moving_avg = np.convolve(rewards, np.ones(window)/window, mode='valid')
            ax.plot(range(window-1, len(rewards)), moving_avg, 'r-', linewidth=2, label=f'MA({window})')
        
        ax.set_title('Episode Rewards')
        ax.set_xlabel('Episode')
        ax.set_ylabel('Reward')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # 2. 成功率
        ax = self.axes[0, 1]
        success_rate = history['success']
        ax.plot(episodes, success_rate, 'g-', alpha=0.6)
        
        # 移动平均
        if len(success_rate) > window:
            success_avg = np.convolve(success_rate, np.ones(window)/window, mode='valid')
            ax.plot(range(window-1, len(success_rate)), success_avg, 'darkgreen', linewidth=2, label=f'MA({window})')
        
        ax.set_title('Success Rate')
        ax.set_xlabel('Episode')
        ax.set_ylabel('Success Rate')
        ax.set_ylim(-0.05, 1.05)
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # 3. Episode长度
        ax = self.axes[1, 0]
        lengths = history['lengths']
        ax.plot(episodes, lengths, 'purple', alpha=0.6)
        ax.set_title('Episode Length')
        ax.set_xlabel('Episode')
        ax.set_ylabel('Steps')
        ax.grid(True, alpha=0.3)
        
        # 4. 任务分布（如果有）
        ax = self.axes[1, 1]
        if 'task_distribution' in history:
            task_dist = history['task_distribution']
            tasks = list(task_dist.keys())
            counts = list(task_dist.values())
            
            ax.bar(tasks, counts)
            ax.set_title('Task Distribution')
            ax.set_xlabel('Task Type')
            ax.set_ylabel('Count')
            ax.tick_params(axis='x', rotation=45)
        else:
            # 显示最近的性能统计
            recent_rewards = rewards[-100:] if len(rewards) > 100 else rewards
            recent_success = success_rate[-100:] if len(success_rate) > 100 else success_rate
            
            stats_text = f"Recent Performance (last {len(recent_rewards)} episodes):\n\n"
            stats_text += f"Avg Reward: {np.mean(recent_rewards):.2f} ± {np.std(recent_rewards):.2f}\n"
            stats_text += f"Avg Success: {np.mean(recent_success):.2%}\n"
            stats_text += f"Max Reward: {np.max(recent_rewards):.2f}\n"
            stats_text += f"Min Reward: {np.min(recent_rewards):.2f}"
            
            ax.text(0.5, 0.5, stats_text, transform=ax.transAxes,
                   fontsize=12, verticalalignment='center',
                   horizontalalignment='center',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
            ax.set_title('Recent Statistics')
            ax.axis('off')
        
        plt.tight_layout()
        plt.draw()
        plt.pause(0.01)
    
    def monitor(self, refresh_interval=5):
        """持续监控训练进度"""
        print("🔍 PPO训练监控器启动")
        print("按 Ctrl+C 退出\n")
        
        last_episode = 0
        
        try:
            while True:
                # 加载最新checkpoint
                checkpoint_info = self.load_latest_checkpoint()
                if checkpoint_info:
                    current_episode = checkpoint_info['episode']
                    
                    # 显示进度
                    print(f"\r📊 Episode: {current_episode} | "
                          f"Success Rate: {checkpoint_info['success_rate']:.2%} | "
                          f"Episodes/min: {(current_episode - last_episode) / refresh_interval * 60:.1f}", 
                          end='', flush=True)
                    
                    last_episode = current_episode
                
                # 加载并绘制历史
                history = self.load_training_history()
                if history:
                    self.plot_metrics(history)
                
                time.sleep(refresh_interval)
                
        except KeyboardInterrupt:
            print("\n\n监控器已停止")
            plt.close()

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='PPO训练监控器')
    parser.add_argument('--checkpoint-dir', default='checkpoints', 
                       help='Checkpoint目录路径')
    parser.add_argument('--refresh', type=int, default=5,
                       help='刷新间隔（秒）')
    
    args = parser.parse_args()
    
    monitor = TrainingMonitor(args.checkpoint_dir)
    monitor.monitor(args.refresh)

if __name__ == "__main__":
    main()
