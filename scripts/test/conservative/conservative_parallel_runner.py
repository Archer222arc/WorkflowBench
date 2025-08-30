#!/usr/bin/env python3
"""
Conservative Parallel Runner - 保守并发执行器
设计目标：
1. 有效利用多个API keys，但避免系统过载
2. 每个key独立运行，避免并发冲突
3. 动态调整并发数，防止内存溢出
4. 完整的错误恢复和进度保存
"""

import os
import sys
import json
import time
import subprocess
import argparse
import psutil
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConservativeParallelRunner:
    """保守并发执行器 - 稳定优先，性能其次"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.checkpoints_dir = self.base_dir / "checkpoints"
        self.checkpoints_dir.mkdir(exist_ok=True)
        
        # 保守的默认配置
        self.default_config = {
            'qwen_models': {
                'max_workers_per_key': 1,  # qwen每个key的max_workers就是1（限流要求）
                'num_keys': 3,  # 使用3个keys (key0, key1, key2)
                'delay_between_keys': 5,  # keys之间启动延迟(秒)
                'qps_limit': 10.0,  # QPS限制为10
            },
            'azure_models': {
                'max_workers': 50,  # Azure模型保持原有并发数
                'delay_between_shards': 3,  # 分片之间启动延迟
            },
            'ideallab_closed': {
                'max_workers': 1,  # IdealLab闭源模型也是1个worker（限流要求）
                'qps_limit': 10.0,  # QPS限制为10
            },
            'system': {
                'memory_threshold': 70,  # 内存使用率阈值(%)
                'cpu_threshold': 80,  # CPU使用率阈值(%)
                'check_interval': 10,  # 系统检查间隔(秒)
                'max_total_processes': 10,  # 最大总进程数
            }
        }
        
        self.active_processes = []
        self.completed_shards = set()
        
    def check_system_resources(self) -> Tuple[float, float]:
        """检查系统资源使用情况"""
        memory_percent = psutil.virtual_memory().percent
        cpu_percent = psutil.cpu_percent(interval=1)
        return memory_percent, cpu_percent
    
    def should_wait_for_resources(self) -> bool:
        """判断是否需要等待系统资源释放"""
        memory_percent, cpu_percent = self.check_system_resources()
        
        if memory_percent > self.default_config['system']['memory_threshold']:
            logger.warning(f"⚠️ 内存使用率过高: {memory_percent:.1f}%")
            return True
            
        if cpu_percent > self.default_config['system']['cpu_threshold']:
            logger.warning(f"⚠️ CPU使用率过高: {cpu_percent:.1f}%")
            return True
            
        active_count = len([p for p in self.active_processes if p.poll() is None])
        if active_count >= self.default_config['system']['max_total_processes']:
            logger.warning(f"⚠️ 活跃进程数过多: {active_count}")
            return True
            
        return False
    
    def wait_for_resources(self):
        """等待系统资源释放"""
        logger.info("⏳ 等待系统资源释放...")
        while self.should_wait_for_resources():
            time.sleep(self.default_config['system']['check_interval'])
            self.cleanup_finished_processes()
    
    def cleanup_finished_processes(self):
        """清理已完成的进程"""
        self.active_processes = [p for p in self.active_processes if p.poll() is None]
    
    def create_qwen_shards(self, model: str, prompt_types: str, difficulty: str,
                          task_types: str, num_instances: int, tool_success_rate: float) -> List[Dict]:
        """为qwen模型创建保守的分片策略"""
        shards = []
        
        # 检查是否是5.3的多prompt_types情况
        if "," in prompt_types and "flawed" in prompt_types:
            # 5.3场景：多个flawed类型
            prompt_list = prompt_types.split(",")
            
            # 将所有prompt分成3组，分配给3个keys
            group_size = len(prompt_list) // 3
            remainder = len(prompt_list) % 3
            
            groups = []
            start = 0
            for i in range(3):
                size = group_size + (1 if i < remainder else 0)
                if size > 0:
                    groups.append(",".join(prompt_list[start:start+size]))
                    start += size
            
            # 分配给3个keys
            for key_idx, group in enumerate(groups):
                if group:
                    shards.append({
                        'model': model,
                        'prompt_types': group,
                        'difficulty': difficulty,
                        'task_types': task_types,
                        'num_instances': num_instances,
                        'tool_success_rate': tool_success_rate,
                        'key_index': key_idx,  # 0, 1, 2
                        'max_workers': self.default_config['qwen_models']['max_workers_per_key']
                    })
        else:
            # 5.1/5.2/5.4/5.5场景：单个prompt_type
            # 平均分配到3个keys
            instances_per_key = num_instances // 3
            remainder = num_instances % 3
            
            for key_idx in range(3):  # 使用key0, key1, key2
                shard_instances = instances_per_key + (1 if key_idx < remainder else 0)
                
                if shard_instances > 0:
                    shards.append({
                        'model': model,
                        'prompt_types': prompt_types,
                        'difficulty': difficulty,
                        'task_types': task_types,
                        'num_instances': shard_instances,
                        'tool_success_rate': tool_success_rate,
                        'key_index': key_idx,
                        'max_workers': self.default_config['qwen_models']['max_workers_per_key']
                    })
        
        logger.info(f"📦 Qwen保守分片: {len(shards)}个分片，每个使用独立的API key")
        return shards
    
    def create_azure_shards(self, model: str, prompt_types: str, difficulty: str,
                           task_types: str, num_instances: int, tool_success_rate: float) -> List[Dict]:
        """为Azure模型创建保守的分片策略"""
        # Azure模型使用单分片，但降低并发数
        return [{
            'model': model,
            'prompt_types': prompt_types,
            'difficulty': difficulty,
            'task_types': task_types,
            'num_instances': num_instances,
            'tool_success_rate': tool_success_rate,
            'max_workers': self.default_config['azure_models']['max_workers']
        }]
    
    def execute_shard(self, shard: Dict, phase: str) -> subprocess.Popen:
        """执行单个分片"""
        cmd = [
            "python3", "smart_batch_runner.py",
            "--model", shard['model'],
            "--prompt-types", shard['prompt_types'],
            "--difficulty", shard['difficulty'],
            "--task-types", shard['task_types'],
            "--num-instances", str(shard['num_instances']),
            "--tool-success-rate", str(shard['tool_success_rate']),
            "--phase", phase,
            "--workers", str(shard['max_workers']),
            "--batch-commit",
            "--enable-checkpoints"
        ]
        
        # 添加qwen特定参数
        if 'key_index' in shard:
            cmd.extend(["--idealab-key-index", str(shard['key_index'])])
            cmd.extend(["--qps", str(self.default_config['qwen_models']['qps_limit'])])
        
        # 设置环境变量
        env = os.environ.copy()
        env['USE_RESULT_COLLECTOR'] = 'true'
        env['STORAGE_FORMAT'] = 'json'
        
        # 创建日志文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.base_dir / "logs" / f"conservative_{shard['model']}_{timestamp}.log"
        
        logger.info(f"🚀 启动分片: {shard['model']} (workers={shard['max_workers']})")
        
        with open(log_file, 'w') as f:
            process = subprocess.Popen(
                cmd,
                stdout=f,
                stderr=subprocess.STDOUT,
                env=env,
                cwd=str(self.base_dir)
            )
        
        return process
    
    def run_phase(self, phase: str, model: str, prompt_types: str, difficulty: str,
                  task_types: str, num_instances: int, tool_success_rate: float = 0.8):
        """运行单个测试阶段"""
        logger.info(f"\n{'='*60}")
        logger.info(f"🎯 执行阶段 {phase}: {model}")
        logger.info(f"   Prompt: {prompt_types}")
        logger.info(f"   难度: {difficulty}, 任务类型: {task_types}")
        logger.info(f"   实例数: {num_instances}")
        logger.info(f"{'='*60}\n")
        
        # 创建分片
        if "qwen" in model.lower():
            shards = self.create_qwen_shards(model, prompt_types, difficulty,
                                            task_types, num_instances, tool_success_rate)
        elif any(x in model.lower() for x in ['deepseek', 'llama', 'gpt', 'gemini', 'kimi', 'o3']):
            shards = self.create_azure_shards(model, prompt_types, difficulty,
                                             task_types, num_instances, tool_success_rate)
        else:
            logger.error(f"❌ 未知模型类型: {model}")
            return
        
        # 执行分片
        for i, shard in enumerate(shards):
            # 等待系统资源
            self.wait_for_resources()
            
            # 启动分片
            process = self.execute_shard(shard, phase)
            self.active_processes.append(process)
            
            # 分片之间的延迟
            if i < len(shards) - 1:
                if "qwen" in model.lower():
                    delay = self.default_config['qwen_models']['delay_between_keys']
                else:
                    delay = self.default_config['azure_models']['delay_between_shards']
                
                logger.info(f"⏰ 等待{delay}秒后启动下一个分片...")
                time.sleep(delay)
        
        # 等待所有进程完成
        logger.info(f"\n⏳ 等待所有分片完成...")
        while any(p.poll() is None for p in self.active_processes):
            time.sleep(10)
            self.cleanup_finished_processes()
            
            # 显示进度
            active = len([p for p in self.active_processes if p.poll() is None])
            if active > 0:
                logger.info(f"   仍有{active}个分片在运行...")
        
        logger.info(f"✅ 阶段{phase}完成！")
    
    def run_5_3_test(self, models: List[str]):
        """运行5.3测试（缺陷工作流）"""
        # 5.3的7种缺陷类型
        defect_groups = [
            "flawed_sequence_disorder,flawed_partial_execution",  # 组1
            "flawed_missing_step,flawed_redundant_step",  # 组2
            "flawed_logical_inconsistency,flawed_parameter_mismatch,flawed_ambiguous_instruction"  # 组3
        ]
        
        for model in models:
            for defects in defect_groups:
                self.run_phase(
                    phase="5.3",
                    model=model,
                    prompt_types=defects,
                    difficulty="easy",
                    task_types="all",
                    num_instances=30,  # 保守的实例数
                    tool_success_rate=0.8
                )
                
                # 组之间的延迟
                logger.info("⏰ 等待30秒后处理下一组缺陷...")
                time.sleep(30)

def main():
    parser = argparse.ArgumentParser(description='Conservative Parallel Runner')
    parser.add_argument('--phase', type=str, help='Test phase (5.1-5.5)')
    parser.add_argument('--models', type=str, help='Comma-separated model list')
    parser.add_argument('--test', action='store_true', help='Run test mode')
    
    args = parser.parse_args()
    
    runner = ConservativeParallelRunner()
    
    if args.test:
        # 测试模式：运行小规模测试
        logger.info("🧪 测试模式：运行小规模测试")
        runner.run_phase(
            phase="5.1",
            model="qwen2.5-7b-instruct",
            prompt_types="optimal",
            difficulty="easy",
            task_types="simple_task",
            num_instances=4,
            tool_success_rate=0.8
        )
    elif args.phase == "5.3":
        # 5.3特殊处理
        models = args.models.split(",") if args.models else ["qwen2.5-7b-instruct"]
        runner.run_5_3_test(models)
    else:
        logger.info("请指定 --phase 和 --models 参数")

if __name__ == "__main__":
    main()