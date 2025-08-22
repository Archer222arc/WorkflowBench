#!/usr/bin/env python3
"""
终极并行批测试脚本
==================
充分利用模型级别速率限制和多API Key实现最大并行
"""

import os
import sys
import json
import time
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from collections import defaultdict
from typing import List, Dict, Tuple

# 颜色输出
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'

def log_info(msg):
    print(f"{Colors.CYAN}[INFO]{Colors.NC} {msg}")

def log_success(msg):
    print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {msg}")

def log_warning(msg):
    print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {msg}")

def log_error(msg):
    print(f"{Colors.RED}[ERROR]{Colors.NC} {msg}")

class UltimateParallelTestRunner:
    """终极并行测试运行器"""
    
    def __init__(self, num_instances=20, difficulty='easy', task_types='all'):
        self.num_instances = num_instances
        self.difficulty = difficulty
        self.task_types = task_types
        
        # IdealLab API Keys
        self.idealab_keys = [
            "956c41bd0f31beaf68b871d4987af4bb",  # Key 0
            "3d906058842b6cf4cee8aaa019f7e77b",  # Key 1
            "88a9a9010f2864bfb53996279dc6c3b9"   # Key 2
        ]
        
        # 模型分组
        self.azure_models = ["gpt-4o-mini"]
        
        self.user_azure_models = [
            "gpt-5-nano",
            "DeepSeek-R1-0528", 
            "DeepSeek-V3-0324",
            "gpt-5-mini",
            "gpt-oss-120b",
            "grok-3",
            "Llama-3.3-70B-Instruct"
        ]
        
        self.idealab_models = [
            "qwen2.5-3b-instruct",
            "qwen2.5-7b-instruct",
            "qwen2.5-14b-instruct", 
            "qwen2.5-32b-instruct",
            "qwen2.5-72b-instruct",
            "qwen2.5-max",
            "DeepSeek-V3-671B",
            "DeepSeek-R1-671B",
            "claude37_sonnet",
            "claude_sonnet4",
            "claude_opus4",
            "gemini-2.5-pro-06-17",
            "gemini-2.5-flash-06-17",
            "gemini-1.5-pro",
            "gemini-2.0-flash",
            "kimi-k2",
            "o1-1217-global",
            "o3-0416-global",
            "o4-mini-0416-global",
            "gpt-41-0414-global"
        ]
        
        # Prompt类型
        self.prompt_types = ["baseline", "cot", "optimal"]
        self.flawed_types = [
            "sequence_disorder", "tool_misuse", "parameter_error",
            "missing_step", "redundant_operations",
            "logical_inconsistency", "semantic_drift"
        ]
        
        # 统计信息
        self.stats = defaultdict(lambda: defaultdict(int))
        self.start_time = None
        
    def run_single_test(self, model: str, prompt_type: str, 
                       tool_success_rate: float = 0.8,
                       api_key_override: str = None) -> bool:
        """运行单个测试"""
        
        # 构建命令
        cmd = [
            "python", "smart_batch_runner.py",
            "--model", model,
            "--prompt-types", prompt_type,
            "--difficulty", self.difficulty,
            "--task-types", self.task_types,
            "--num-instances", str(self.num_instances),
            "--tool-success-rate", str(tool_success_rate),
            "--adaptive",
            "--batch-commit",
            "--checkpoint-interval", "10",
            "--silent"
        ]
        
        # 设置环境变量（如果需要特定API Key）
        env = os.environ.copy()
        if api_key_override:
            env['IDEALAB_API_KEY_OVERRIDE'] = api_key_override
        
        # 运行命令
        try:
            log_info(f"开始: {model} | {prompt_type} | rate={tool_success_rate}")
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                env=env,
                timeout=600  # 10分钟超时
            )
            
            if result.returncode == 0:
                log_success(f"完成: {model} | {prompt_type}")
                self.stats[model][prompt_type] = 'success'
                return True
            else:
                log_error(f"失败: {model} | {prompt_type}")
                self.stats[model][prompt_type] = 'failed'
                return False
                
        except subprocess.TimeoutExpired:
            log_error(f"超时: {model} | {prompt_type}")
            self.stats[model][prompt_type] = 'timeout'
            return False
        except Exception as e:
            log_error(f"异常: {model} | {prompt_type} - {str(e)}")
            self.stats[model][prompt_type] = 'error'
            return False
    
    def run_azure_models_parallel(self):
        """运行Azure模型 - 所有prompt types并行"""
        log_info("="*60)
        log_info("Azure模型测试 (所有prompt types并行)")
        log_info("="*60)
        
        tasks = []
        for model in self.azure_models:
            # 常规prompt types
            for prompt_type in self.prompt_types:
                tasks.append((model, prompt_type, 0.8, None))
            
            # Flawed types
            for flaw_type in self.flawed_types:
                tasks.append((model, f"flawed_{flaw_type}", 0.8, None))
        
        log_info(f"Azure任务数: {len(tasks)}")
        
        # 使用线程池并行执行
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for model, prompt, rate, key in tasks:
                future = executor.submit(self.run_single_test, model, prompt, rate, key)
                futures.append(future)
            
            # 等待完成
            completed = 0
            for future in as_completed(futures):
                completed += 1
                log_info(f"Azure进度: {completed}/{len(tasks)}")
        
        log_success("Azure模型测试完成")
    
    def run_user_azure_models_parallel(self):
        """运行User Azure模型 (包括DeepSeek) - 并行"""
        log_info("="*60)
        log_info("User Azure模型测试 (包括DeepSeek)")
        log_info("="*60)
        
        tasks = []
        for model in self.user_azure_models:
            # 常规prompt types
            for prompt_type in self.prompt_types:
                tasks.append((model, prompt_type, 0.8, None))
            
            # Flawed types
            for flaw_type in self.flawed_types:
                tasks.append((model, f"flawed_{flaw_type}", 0.8, None))
        
        log_info(f"User Azure任务数: {len(tasks)}")
        
        # 使用线程池并行执行
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = []
            for model, prompt, rate, key in tasks:
                future = executor.submit(self.run_single_test, model, prompt, rate, key)
                futures.append(future)
            
            # 等待完成
            completed = 0
            for future in as_completed(futures):
                completed += 1
                log_info(f"User Azure进度: {completed}/{len(tasks)}")
        
        log_success("User Azure模型测试完成")
    
    def run_idealab_models_with_key_assignment(self):
        """运行IdealLab模型 - 智能分配API Keys"""
        log_info("="*60)
        log_info("IdealLab模型测试 (3个API Keys智能分配)")
        log_info("="*60)
        
        # 策略：每个prompt type使用不同的API Key
        prompt_key_mapping = {
            'baseline': self.idealab_keys[0],
            'cot': self.idealab_keys[1],
            'optimal': self.idealab_keys[2]
        }
        
        # Flawed types轮询使用3个keys
        tasks = []
        
        for model in self.idealab_models:
            # 常规prompt types - 每个使用指定的key
            for prompt_type in self.prompt_types:
                api_key = prompt_key_mapping[prompt_type]
                tasks.append((model, prompt_type, 0.8, api_key))
            
            # Flawed types - 轮询分配
            for i, flaw_type in enumerate(self.flawed_types):
                api_key = self.idealab_keys[i % 3]
                tasks.append((model, f"flawed_{flaw_type}", 0.8, api_key))
        
        log_info(f"IdealLab任务数: {len(tasks)}")
        
        # 按API Key分组显示
        key_tasks = defaultdict(list)
        for model, prompt, rate, key in tasks:
            key_idx = self.idealab_keys.index(key) if key else -1
            key_tasks[key_idx].append((model, prompt))
        
        for key_idx, task_list in key_tasks.items():
            if key_idx >= 0:
                log_info(f"  Key {key_idx}: {len(task_list)} 个任务")
        
        # 使用线程池并行执行
        with ThreadPoolExecutor(max_workers=24) as executor:  # 3 keys × 8 并发
            futures = []
            for model, prompt, rate, key in tasks:
                future = executor.submit(self.run_single_test, model, prompt, rate, key)
                futures.append(future)
            
            # 等待完成
            completed = 0
            for future in as_completed(futures):
                completed += 1
                if completed % 10 == 0:
                    log_info(f"IdealLab进度: {completed}/{len(tasks)}")
        
        log_success("IdealLab模型测试完成")
    
    def run_all_parallel(self):
        """并行运行所有测试组"""
        log_info("="*70)
        log_info("终极并行批测试")
        log_info(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log_info("="*70)
        
        log_info("测试配置:")
        log_info(f"  实例数: {self.num_instances}")
        log_info(f"  难度: {self.difficulty}")
        log_info(f"  任务类型: {self.task_types}")
        log_info(f"  模型总数: {len(self.azure_models + self.user_azure_models + self.idealab_models)}")
        
        # 询问确认
        response = input(f"{Colors.YELLOW}是否开始测试? (y/n): {Colors.NC}")
        if response.lower() != 'y':
            log_warning("测试取消")
            return
        
        self.start_time = time.time()
        
        # 使用进程池运行三大组
        with ProcessPoolExecutor(max_workers=3) as executor:
            futures = []
            
            # Azure组
            azure_future = executor.submit(self.run_azure_models_parallel)
            futures.append(('Azure', azure_future))
            
            # User Azure组
            user_azure_future = executor.submit(self.run_user_azure_models_parallel)
            futures.append(('User Azure', user_azure_future))
            
            # IdealLab组
            idealab_future = executor.submit(self.run_idealab_models_with_key_assignment)
            futures.append(('IdealLab', idealab_future))
            
            # 等待完成
            for name, future in futures:
                try:
                    future.result()
                    log_success(f"{name} 组完成")
                except Exception as e:
                    log_error(f"{name} 组失败: {e}")
        
        # 计算总耗时
        total_time = time.time() - self.start_time
        minutes = int(total_time // 60)
        seconds = int(total_time % 60)
        
        log_success("="*70)
        log_success("所有测试完成!")
        log_success(f"总耗时: {minutes}分{seconds}秒")
        log_success("="*70)
        
        # 生成报告
        self.generate_report()
    
    def generate_report(self):
        """生成测试报告"""
        log_info("生成测试报告...")
        
        # 统计结果
        total_tests = 0
        success_count = 0
        failed_count = 0
        
        for model, results in self.stats.items():
            for prompt, status in results.items():
                total_tests += 1
                if status == 'success':
                    success_count += 1
                else:
                    failed_count += 1
        
        # 显示统计
        print("\n" + "="*70)
        print("测试统计")
        print("="*70)
        print(f"总测试数: {total_tests}")
        print(f"成功: {success_count} ({success_count/max(1, total_tests)*100:.1f}%)")
        print(f"失败: {failed_count} ({failed_count/max(1, total_tests)*100:.1f}%)")
        
        # 按模型显示
        print("\n按模型统计:")
        for model in sorted(self.stats.keys()):
            model_success = sum(1 for s in self.stats[model].values() if s == 'success')
            model_total = len(self.stats[model])
            print(f"  {model}: {model_success}/{model_total}")
        
        # 保存到文件
        report_file = f"logs/parallel_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        Path("logs").mkdir(exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'config': {
                    'num_instances': self.num_instances,
                    'difficulty': self.difficulty,
                    'task_types': self.task_types
                },
                'summary': {
                    'total_tests': total_tests,
                    'success': success_count,
                    'failed': failed_count,
                    'duration_seconds': time.time() - self.start_time if self.start_time else 0
                },
                'details': dict(self.stats)
            }, f, indent=2)
        
        log_success(f"报告已保存: {report_file}")

def main():
    parser = argparse.ArgumentParser(description='终极并行批测试')
    parser.add_argument('--num-instances', type=int, default=20,
                       help='每个组合的测试实例数')
    parser.add_argument('--difficulty', default='easy',
                       choices=['easy', 'medium', 'hard'],
                       help='测试难度')
    parser.add_argument('--task-types', default='all',
                       help='任务类型')
    parser.add_argument('--test-group', 
                       choices=['azure', 'user-azure', 'idealab', 'all'],
                       default='all',
                       help='要测试的模型组')
    
    args = parser.parse_args()
    
    runner = UltimateParallelTestRunner(
        num_instances=args.num_instances,
        difficulty=args.difficulty,
        task_types=args.task_types
    )
    
    if args.test_group == 'all':
        runner.run_all_parallel()
    elif args.test_group == 'azure':
        runner.run_azure_models_parallel()
    elif args.test_group == 'user-azure':
        runner.run_user_azure_models_parallel()
    elif args.test_group == 'idealab':
        runner.run_idealab_models_with_key_assignment()

if __name__ == "__main__":
    main()