#!/usr/bin/env python3
"""
Experiment Manager for PILOT-Bench
==================================
管理和执行综合实验评估计划中定义的各种实验
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from multi_model_batch_tester import BatchTestConfig, BatchTestRunner, ModelTestResult
from api_client_manager import SUPPORTED_MODELS

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 设置绘图风格
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")


@dataclass
class ExperimentConfig:
    """实验配置"""
    name: str
    description: str
    models: List[str]
    task_types: List[str]
    prompt_types: List[str]
    num_tests: int = 10
    focus: Optional[str] = None
    save_plots: bool = True


class ExperimentManager:
    """实验管理器"""
    
    def __init__(self, model_path: str, tools_path: str, output_base_dir: str = "experiment_results"):
        """初始化实验管理器"""
        self.model_path = model_path
        self.tools_path = tools_path
        self.output_base_dir = Path(output_base_dir)
        self.output_base_dir.mkdir(exist_ok=True)
        
        # 创建会话目录
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.output_base_dir / self.session_id
        self.session_dir.mkdir(exist_ok=True)
        
        # 实验配置
        self.experiments = self._load_experiment_configs()
        
        logger.info(f"ExperimentManager initialized. Session: {self.session_id}")
    
    def _load_experiment_configs(self) -> Dict[str, ExperimentConfig]:
        """加载预定义的实验配置"""
        configs = {
            # 4.1 整体性能评估实验
            "overall_performance": ExperimentConfig(
                name="整体性能评估",
                description="测试所有模型在各种任务类型上的整体性能",
                models=SUPPORTED_MODELS,  # 使用所有可用模型
                task_types=["basic_task", "simple_task", "data_pipeline", "api_integration", "multi_stage_pipeline"],
                prompt_types=["baseline", "cot", "optimal"],
                num_tests=10
            ),
            
            # 4.2 模型规模效应分析
            "qwen_scale_analysis": ExperimentConfig(
                name="Qwen系列规模效应分析",
                description="分析Qwen系列不同规模模型的性能差异",
                models=["qwen2.5-3b-instruct", "qwen2.5-7b-instruct", 
                       "qwen2.5-14b-instruct", "qwen2.5-32b-instruct", "qwen2.5-max"],
                task_types=["simple_task", "data_pipeline", "api_integration"],
                prompt_types=["baseline", "optimal"],
                num_tests=15,
                focus="scale_effects"
            ),
            
            # 4.3 Robustness评估
            "robustness_test": ExperimentConfig(
                name="缺陷工作流适应性测试",
                description="测试模型对缺陷工作流的适应能力",
                models=["gpt-41-0414-global", "o1-1217-global", "claude_opus4", 
                       "DeepSeek-V3-671B", "qwen2.5-72b-instruct"],
                task_types=["simple_task", "data_pipeline", "multi_stage_pipeline"],
                prompt_types=["optimal", "flawed"],
                num_tests=20,
                focus="robustness"
            ),
            
            # 4.4 提示类型敏感性
            "prompt_sensitivity": ExperimentConfig(
                name="提示类型敏感性分析",
                description="分析不同模型对各种提示类型的敏感性",
                models=SUPPORTED_MODELS[:10],  # 选择前10个模型
                task_types=["simple_task", "data_pipeline"],
                prompt_types=["baseline", "cot", "optimal", "flawed"],
                num_tests=10,
                focus="prompt_sensitivity"
            ),
            
            # 4.5 错误模式分析
            "error_analysis": ExperimentConfig(
                name="系统性错误分析",
                description="深入分析模型的错误模式",
                models=["gpt-41-0414-global", "claude_sonnet4", "gemini-2.5-pro-06-17",
                       "DeepSeek-R1-671B", "qwen2.5-32b-instruct"],
                task_types=["data_pipeline", "api_integration", "multi_stage_pipeline"],
                prompt_types=["baseline", "optimal"],
                num_tests=25,
                focus="error_patterns"
            )
        }
        
        return configs
    
    def run_experiment(self, experiment_name: str) -> Dict[str, Any]:
        """运行指定的实验"""
        if experiment_name not in self.experiments:
            raise ValueError(f"Unknown experiment: {experiment_name}")
        
        exp_config = self.experiments[experiment_name]
        logger.info(f"Running experiment: {exp_config.name}")
        
        # 创建实验目录
        exp_dir = self.session_dir / experiment_name
        exp_dir.mkdir(exist_ok=True)
        
        # 配置批量测试
        batch_config = BatchTestConfig(
            models=exp_config.models,
            task_types=exp_config.task_types,
            prompt_types=exp_config.prompt_types,
            num_tests_per_combination=exp_config.num_tests,
            max_parallel_models=3,
            save_individual_results=True,
            output_dir=str(exp_dir)
        )
        
        # 运行测试
        runner = BatchTestRunner(batch_config, self.model_path, self.tools_path)
        results = runner.run()
        
        # 分析结果
        analysis = self._analyze_results(results, exp_config)
        
        # 生成可视化
        if exp_config.save_plots:
            self._generate_visualizations(analysis, exp_config, exp_dir)
        
        # 保存实验报告
        self._save_experiment_report(exp_config, results, analysis, exp_dir)
        
        return analysis
    
    def _analyze_results(self, results: Dict[str, Any], config: ExperimentConfig) -> Dict[str, Any]:
        """分析实验结果"""
        analysis = {
            'experiment_name': config.name,
            'total_tests': results['total_tests'],
            'overall_success_rate': 0,
            'model_rankings': [],
            'task_difficulty': {},
            'prompt_effectiveness': {},
            'special_findings': {}
        }
        
        # 计算整体成功率
        detailed_results = results['detailed_results']
        if detailed_results:
            analysis['overall_success_rate'] = sum(1 for r in detailed_results if r['success']) / len(detailed_results)
        
        # 模型排名
        model_scores = []
        for model, stats in results['model_performance'].items():
            score = {
                'model': model,
                'success_rate': stats['success_rate'],
                'avg_execution_time': stats['avg_execution_time'],
                'avg_tool_count': stats['avg_tool_count'],
                'overall_score': stats['success_rate'] * 0.7 + (1 / (1 + stats['avg_execution_time'])) * 0.3
            }
            model_scores.append(score)
        
        analysis['model_rankings'] = sorted(model_scores, key=lambda x: x['overall_score'], reverse=True)
        
        # 任务难度分析
        for task, task_stats in results['task_performance'].items():
            analysis['task_difficulty'][task] = {
                'success_rate': task_stats['success_rate'],
                'difficulty_score': 1 - task_stats['success_rate']
            }
        
        # 提示有效性分析
        for prompt_type, prompt_stats in results['prompt_performance'].items():
            analysis['prompt_effectiveness'][prompt_type] = {
                'success_rate': prompt_stats['success_rate'],
                'avg_adherence': prompt_stats.get('avg_adherence_score', 0)
            }
        
        # 特殊发现（根据实验类型）
        if config.focus == "scale_effects":
            analysis['special_findings'] = self._analyze_scale_effects(detailed_results, config.models)
        elif config.focus == "robustness":
            analysis['special_findings'] = self._analyze_robustness(detailed_results)
        elif config.focus == "error_patterns":
            analysis['special_findings'] = self._analyze_error_patterns(detailed_results)
        
        return analysis
    
    def _analyze_scale_effects(self, results: List[Dict], models: List[str]) -> Dict[str, Any]:
        """分析规模效应"""
        # 提取Qwen模型的参数规模
        model_sizes = {
            "qwen2.5-3b-instruct": 3,
            "qwen2.5-7b-instruct": 7,
            "qwen2.5-14b-instruct": 14,
            "qwen2.5-32b-instruct": 32,
            "qwen2.5-max": 72,  # qwen2.5-72b
        }
        
        scale_analysis = {
            'performance_by_size': {},
            'efficiency_by_size': {},
            'optimal_size': None
        }
        
        for model in models:
            if model in model_sizes:
                model_results = [r for r in results if r['model_name'] == model]
                if model_results:
                    size = model_sizes[model]
                    success_rate = sum(1 for r in model_results if r['success']) / len(model_results)
                    avg_time = np.mean([r['execution_time'] for r in model_results])
                    
                    scale_analysis['performance_by_size'][size] = {
                        'success_rate': success_rate,
                        'avg_execution_time': avg_time,
                        'efficiency_score': success_rate / np.log(size)  # 效率评分
                    }
        
        # 找出最优规模
        if scale_analysis['performance_by_size']:
            optimal = max(scale_analysis['performance_by_size'].items(), 
                         key=lambda x: x[1]['efficiency_score'])
            scale_analysis['optimal_size'] = optimal[0]
        
        return scale_analysis
    
    def _analyze_robustness(self, results: List[Dict]) -> Dict[str, Any]:
        """分析鲁棒性"""
        robustness_analysis = {
            'flawed_vs_optimal': {},
            'recovery_ability': {}
        }
        
        # 比较flawed和optimal prompt的性能
        for model in set(r['model_name'] for r in results):
            model_optimal = [r for r in results if r['model_name'] == model and r['prompt_type'] == 'optimal']
            model_flawed = [r for r in results if r['model_name'] == model and r['prompt_type'] == 'flawed']
            
            if model_optimal and model_flawed:
                optimal_success = sum(1 for r in model_optimal if r['success']) / len(model_optimal)
                flawed_success = sum(1 for r in model_flawed if r['success']) / len(model_flawed)
                
                robustness_analysis['flawed_vs_optimal'][model] = {
                    'optimal_success_rate': optimal_success,
                    'flawed_success_rate': flawed_success,
                    'robustness_score': flawed_success / (optimal_success + 0.001)  # 避免除零
                }
        
        return robustness_analysis
    
    def _analyze_error_patterns(self, results: List[Dict]) -> Dict[str, Any]:
        """分析错误模式"""
        error_patterns = {
            'error_types': {},
            'error_by_task': {},
            'error_by_model': {}
        }
        
        failed_results = [r for r in results if not r['success']]
        
        # 统计错误类型
        for result in failed_results:
            error_msg = result.get('error_message', 'unknown_error')
            error_type = self._categorize_error(error_msg)
            
            if error_type not in error_patterns['error_types']:
                error_patterns['error_types'][error_type] = 0
            error_patterns['error_types'][error_type] += 1
            
            # 按任务统计
            task = result['task_type']
            if task not in error_patterns['error_by_task']:
                error_patterns['error_by_task'][task] = {}
            if error_type not in error_patterns['error_by_task'][task]:
                error_patterns['error_by_task'][task][error_type] = 0
            error_patterns['error_by_task'][task][error_type] += 1
            
            # 按模型统计
            model = result['model_name']
            if model not in error_patterns['error_by_model']:
                error_patterns['error_by_model'][model] = {}
            if error_type not in error_patterns['error_by_model'][model]:
                error_patterns['error_by_model'][model][error_type] = 0
            error_patterns['error_by_model'][model][error_type] += 1
        
        return error_patterns
    
    def _categorize_error(self, error_msg: str) -> str:
        """分类错误信息"""
        if not error_msg:
            return "no_error_message"
        
        error_lower = error_msg.lower()
        
        if "timeout" in error_lower:
            return "timeout"
        elif "rate" in error_lower or "限流" in error_lower:
            return "rate_limit"
        elif "tool" in error_lower and "not found" in error_lower:
            return "tool_not_found"
        elif "parameter" in error_lower or "argument" in error_lower:
            return "parameter_error"
        elif "connection" in error_lower or "network" in error_lower:
            return "network_error"
        else:
            return "other_error"
    
    def _generate_visualizations(self, analysis: Dict[str, Any], config: ExperimentConfig, output_dir: Path):
        """生成可视化图表"""
        # 1. 模型性能对比图
        if 'model_rankings' in analysis and analysis['model_rankings']:
            self._plot_model_performance(analysis['model_rankings'], output_dir)
        
        # 2. 任务难度热图
        if 'task_difficulty' in analysis:
            self._plot_task_difficulty(analysis['task_difficulty'], output_dir)
        
        # 3. 特殊可视化（根据实验类型）
        if config.focus == "scale_effects" and 'special_findings' in analysis:
            self._plot_scale_effects(analysis['special_findings'], output_dir)
        elif config.focus == "robustness" and 'special_findings' in analysis:
            self._plot_robustness(analysis['special_findings'], output_dir)
        elif config.focus == "error_patterns" and 'special_findings' in analysis:
            self._plot_error_patterns(analysis['special_findings'], output_dir)
    
    def _plot_model_performance(self, rankings: List[Dict], output_dir: Path):
        """绘制模型性能对比图"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # 成功率条形图
        models = [r['model'] for r in rankings[:10]]  # Top 10
        success_rates = [r['success_rate'] for r in rankings[:10]]
        
        ax1.barh(models, success_rates)
        ax1.set_xlabel('Success Rate')
        ax1.set_title('Model Success Rates (Top 10)')
        ax1.set_xlim(0, 1)
        
        # 综合得分散点图
        exec_times = [r['avg_execution_time'] for r in rankings[:10]]
        overall_scores = [r['overall_score'] for r in rankings[:10]]
        
        ax2.scatter(exec_times, success_rates, s=100)
        for i, model in enumerate(models):
            ax2.annotate(model.split('-')[0], (exec_times[i], success_rates[i]), fontsize=8)
        
        ax2.set_xlabel('Average Execution Time (s)')
        ax2.set_ylabel('Success Rate')
        ax2.set_title('Performance vs Efficiency')
        
        plt.tight_layout()
        plt.savefig(output_dir / 'model_performance.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_task_difficulty(self, task_difficulty: Dict[str, Dict], output_dir: Path):
        """绘制任务难度热图"""
        tasks = list(task_difficulty.keys())
        difficulties = [task_difficulty[t]['difficulty_score'] for t in tasks]
        
        plt.figure(figsize=(10, 6))
        plt.barh(tasks, difficulties, color=plt.cm.RdYlGn_r(difficulties))
        plt.xlabel('Difficulty Score (1 - Success Rate)')
        plt.title('Task Difficulty Analysis')
        plt.xlim(0, 1)
        
        plt.tight_layout()
        plt.savefig(output_dir / 'task_difficulty.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_scale_effects(self, scale_findings: Dict[str, Any], output_dir: Path):
        """绘制规模效应图"""
        if 'performance_by_size' not in scale_findings:
            return
        
        sizes = sorted(scale_findings['performance_by_size'].keys())
        success_rates = [scale_findings['performance_by_size'][s]['success_rate'] for s in sizes]
        efficiency_scores = [scale_findings['performance_by_size'][s]['efficiency_score'] for s in sizes]
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # 成功率 vs 模型规模
        ax1.plot(sizes, success_rates, 'o-', markersize=10)
        ax1.set_xlabel('Model Size (B parameters)')
        ax1.set_ylabel('Success Rate')
        ax1.set_title('Performance vs Model Scale')
        ax1.set_xscale('log')
        ax1.grid(True, alpha=0.3)
        
        # 效率评分 vs 模型规模
        ax2.plot(sizes, efficiency_scores, 's-', color='green', markersize=10)
        ax2.set_xlabel('Model Size (B parameters)')
        ax2.set_ylabel('Efficiency Score')
        ax2.set_title('Efficiency vs Model Scale')
        ax2.set_xscale('log')
        ax2.grid(True, alpha=0.3)
        
        # 标记最优规模
        if scale_findings.get('optimal_size'):
            opt_size = scale_findings['optimal_size']
            ax2.axvline(x=opt_size, color='red', linestyle='--', alpha=0.7)
            ax2.text(opt_size, max(efficiency_scores)*0.9, f'Optimal: {opt_size}B', 
                    ha='center', color='red')
        
        plt.tight_layout()
        plt.savefig(output_dir / 'scale_effects.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_robustness(self, robustness_findings: Dict[str, Any], output_dir: Path):
        """绘制鲁棒性分析图"""
        if 'flawed_vs_optimal' not in robustness_findings:
            return
        
        data = robustness_findings['flawed_vs_optimal']
        models = list(data.keys())
        optimal_rates = [data[m]['optimal_success_rate'] for m in models]
        flawed_rates = [data[m]['flawed_success_rate'] for m in models]
        robustness_scores = [data[m]['robustness_score'] for m in models]
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # 对比条形图
        x = np.arange(len(models))
        width = 0.35
        
        ax1.bar(x - width/2, optimal_rates, width, label='Optimal Workflow')
        ax1.bar(x + width/2, flawed_rates, width, label='Flawed Workflow')
        ax1.set_xlabel('Models')
        ax1.set_ylabel('Success Rate')
        ax1.set_title('Performance: Optimal vs Flawed Workflows')
        ax1.set_xticks(x)
        ax1.set_xticklabels([m.split('-')[0] for m in models], rotation=45)
        ax1.legend()
        
        # 鲁棒性得分
        ax2.bar(models, robustness_scores, color='orange')
        ax2.set_xlabel('Models')
        ax2.set_ylabel('Robustness Score')
        ax2.set_title('Model Robustness (Flawed/Optimal Ratio)')
        ax2.set_xticklabels([m.split('-')[0] for m in models], rotation=45)
        ax2.axhline(y=1.0, color='red', linestyle='--', alpha=0.5)
        
        plt.tight_layout()
        plt.savefig(output_dir / 'robustness_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_error_patterns(self, error_findings: Dict[str, Any], output_dir: Path):
        """绘制错误模式分析图"""
        if 'error_types' not in error_findings:
            return
        
        # 错误类型分布
        error_types = list(error_findings['error_types'].keys())
        error_counts = list(error_findings['error_types'].values())
        
        plt.figure(figsize=(10, 6))
        plt.pie(error_counts, labels=error_types, autopct='%1.1f%%', startangle=90)
        plt.title('Error Type Distribution')
        plt.axis('equal')
        
        plt.tight_layout()
        plt.savefig(output_dir / 'error_distribution.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # 错误热图（模型 x 错误类型）
        if 'error_by_model' in error_findings:
            models = list(error_findings['error_by_model'].keys())
            all_error_types = set()
            for errors in error_findings['error_by_model'].values():
                all_error_types.update(errors.keys())
            all_error_types = sorted(list(all_error_types))
            
            # 构建矩阵
            matrix = []
            for model in models:
                row = []
                for error_type in all_error_types:
                    count = error_findings['error_by_model'][model].get(error_type, 0)
                    row.append(count)
                matrix.append(row)
            
            plt.figure(figsize=(12, 8))
            sns.heatmap(matrix, xticklabels=all_error_types, yticklabels=models, 
                       annot=True, fmt='d', cmap='YlOrRd')
            plt.title('Error Patterns by Model')
            plt.xlabel('Error Type')
            plt.ylabel('Model')
            
            plt.tight_layout()
            plt.savefig(output_dir / 'error_heatmap.png', dpi=300, bbox_inches='tight')
            plt.close()
    
    def _save_experiment_report(self, config: ExperimentConfig, results: Dict[str, Any], 
                               analysis: Dict[str, Any], output_dir: Path):
        """保存实验报告"""
        report = {
            'experiment_config': asdict(config),
            'execution_summary': {
                'start_time': results['execution_time']['start'],
                'end_time': results['execution_time']['end'],
                'duration': results['execution_time']['duration_seconds'],
                'total_tests': results['total_tests']
            },
            'analysis': analysis,
            'raw_results': results
        }
        
        # 保存JSON报告
        report_path = output_dir / 'experiment_report.json'
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        # 生成Markdown报告
        self._generate_markdown_report(config, analysis, output_dir)
        
        logger.info(f"Experiment report saved to {output_dir}")
    
    def _generate_markdown_report(self, config: ExperimentConfig, analysis: Dict[str, Any], output_dir: Path):
        """生成Markdown格式的报告"""
        md_content = f"""# {config.name} - 实验报告

## 实验概述
- **描述**: {config.description}
- **测试模型数**: {len(config.models)}
- **任务类型**: {', '.join(config.task_types)}
- **提示类型**: {', '.join(config.prompt_types)}
- **每组合测试次数**: {config.num_tests}

## 主要发现

### 整体性能
- **总测试数**: {analysis['total_tests']}
- **整体成功率**: {analysis['overall_success_rate']:.2%}

### 模型排名 (Top 5)
| 排名 | 模型 | 成功率 | 平均执行时间 | 综合得分 |
|------|------|--------|--------------|----------|
"""
        
        for i, model in enumerate(analysis['model_rankings'][:5], 1):
            md_content += f"| {i} | {model['model']} | {model['success_rate']:.2%} | {model['avg_execution_time']:.2f}s | {model['overall_score']:.3f} |\n"
        
        # 添加特殊发现
        if analysis.get('special_findings'):
            md_content += "\n### 特殊发现\n"
            
            if config.focus == "scale_effects":
                findings = analysis['special_findings']
                if 'optimal_size' in findings:
                    md_content += f"- **最优模型规模**: {findings['optimal_size']}B\n"
            
            elif config.focus == "robustness":
                md_content += "- **鲁棒性分析**: 见robustness_analysis.png\n"
            
            elif config.focus == "error_patterns":
                md_content += "- **错误模式分析**: 见error_distribution.png和error_heatmap.png\n"
        
        md_content += "\n## 可视化结果\n"
        md_content += "- [模型性能对比](./model_performance.png)\n"
        md_content += "- [任务难度分析](./task_difficulty.png)\n"
        
        if config.focus == "scale_effects":
            md_content += "- [规模效应分析](./scale_effects.png)\n"
        elif config.focus == "robustness":
            md_content += "- [鲁棒性分析](./robustness_analysis.png)\n"
        elif config.focus == "error_patterns":
            md_content += "- [错误分布](./error_distribution.png)\n"
            md_content += "- [错误热图](./error_heatmap.png)\n"
        
        # 保存Markdown报告
        md_path = output_dir / 'experiment_report.md'
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
    
    def run_all_experiments(self) -> Dict[str, Any]:
        """运行所有预定义的实验"""
        all_results = {}
        
        for exp_name, exp_config in self.experiments.items():
            logger.info(f"\n{'='*60}")
            logger.info(f"Starting experiment: {exp_name}")
            logger.info(f"{'='*60}")
            
            try:
                results = self.run_experiment(exp_name)
                all_results[exp_name] = {
                    'status': 'completed',
                    'results': results
                }
            except Exception as e:
                logger.error(f"Experiment {exp_name} failed: {str(e)}")
                all_results[exp_name] = {
                    'status': 'failed',
                    'error': str(e)
                }
        
        # 生成综合报告
        self._generate_comprehensive_report(all_results)
        
        return all_results
    
    def _generate_comprehensive_report(self, all_results: Dict[str, Any]):
        """生成综合实验报告"""
        report_path = self.session_dir / 'comprehensive_report.md'
        
        content = f"""# PILOT-Bench 综合实验报告

**会话ID**: {self.session_id}
**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 实验概览

| 实验名称 | 状态 | 整体成功率 | 主要发现 |
|----------|------|-----------|----------|
"""
        
        for exp_name, result in all_results.items():
            status = result['status']
            if status == 'completed':
                success_rate = result['results'].get('overall_success_rate', 0)
                content += f"| {self.experiments[exp_name].name} | ✅ | {success_rate:.2%} | [查看详情](./{exp_name}/experiment_report.md) |\n"
            else:
                content += f"| {self.experiments[exp_name].name} | ❌ | - | {result.get('error', 'Unknown error')} |\n"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Comprehensive report saved to {report_path}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run PILOT-Bench experiments')
    parser.add_argument('--experiment', type=str, help='Specific experiment to run')
    parser.add_argument('--all', action='store_true', help='Run all experiments')
    parser.add_argument('--model-path', type=str, default='generalized_mdp_model_v5.pkl')
    parser.add_argument('--tools-path', type=str, default='mcp_tools')
    
    args = parser.parse_args()
    
    # 创建实验管理器
    manager = ExperimentManager(args.model_path, args.tools_path)
    
    if args.all:
        # 运行所有实验
        results = manager.run_all_experiments()
    elif args.experiment:
        # 运行特定实验
        results = manager.run_experiment(args.experiment)
    else:
        # 列出可用实验
        print("Available experiments:")
        for name, config in manager.experiments.items():
            print(f"  - {name}: {config.description}")
        print("\nUse --experiment <name> to run a specific experiment")
        print("Use --all to run all experiments")


if __name__ == "__main__":
    main()