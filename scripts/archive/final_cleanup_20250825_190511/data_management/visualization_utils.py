#!/usr/bin/env python3
"""
Visualization Utilities for Workflow Quality Testing
===================================================
This module contains all visualization functions for the workflow quality testing framework.
It provides comprehensive plotting capabilities for analyzing test results, performance metrics,
and quality assessments across different prompting strategies.
"""
import json
import logging
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime  # 添加缺失的datetime导入



# Configure matplotlib
matplotlib.use('Agg')

# Setup logging
logger = logging.getLogger(__name__)

# Import required data classes
from dataclasses import dataclass


class WorkflowVisualizationManager:
    """Manager class for all workflow quality visualization functions"""
    
    def __init__(self, output_dir: Path):
        """Initialize the visualization manager
        
        Args:
            output_dir: Directory to save visualization outputs
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Define consistent color schemes
        self.strategy_colors = {
            'baseline': '#ff7f0e',
            'optimal': '#2ca02c',
            'cot': '#1f77b4',
            'flawed_light': '#ffd700',
            'flawed_medium': '#ff8c00',
            'flawed_severe': '#dc143c'
        }
        
        # Set default plot style
        plt.style.use('seaborn-v0_8-darkgrid')
    
    def generate_all_visualizations(self, results: Dict[str, List[Any]]):
        """Generate all visualization plots
        
        Args:
            results: Dictionary mapping test keys to lists of ExecutionResult objects
        """
        logger.info("Generating visualization plots...")
        
        # 1. Success rate comparison
        self._plot_success_rates(results)
        
        # 2. Score distribution
        self._plot_score_distribution(results)
        
        # 3. Workflow adherence
        self._plot_workflow_adherence(results)
        
        # 4. Phase2 quality metrics comparison
        self._plot_phase2_metrics(results)
        
        # 5. Execution time analysis
        self._plot_execution_times(results)
        
        # 6. Severity impact analysis
        self._plot_severity_impact(results)
        
        # 7. Flaw type sensitivity
        self._plot_flaw_sensitivity(results)
        
        # 8. Detailed quality breakdown
        self._plot_quality_breakdown(results)
        
        # 9. Achievement vs Quality scatter plot
        self._plot_quality_vs_achievement(results)

        # 10. Comprehensive success rate comparison (新增)
        self._plot_comprehensive_success_comparison(results)
        
        logger.info(f"Visualizations saved to {self.output_dir}")

    def _plot_comprehensive_success_comparison(self, results: Dict[str, List['ExecutionResult']]):
        """Plot comprehensive success rate comparison across all strategies"""
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # 定义所有策略
        strategies = ['baseline', 'optimal', 'cot', 'flawed_light', 'flawed_medium', 'flawed_severe']
        strategy_labels = ['Baseline', 'Optimal', 'CoT', 'Flawed (Light)', 'Flawed (Medium)', 'Flawed (Severe)']
        strategy_colors = ['#ff7f0e', '#2ca02c', '#1f77b4', '#ffd700', '#ff8c00', '#dc143c']
        
        # 收集每种策略的数据
        strategy_data = {strategy: {'full_successes': 0, 'partial_successes': 0, 'total': 0} 
                        for strategy in strategies}
        
        # 遍历所有结果
        for key, task_results in results.items():
            for result in task_results:
                # 确定策略类型
                if result.prompt_type in ['baseline', 'optimal', 'cot']:
                    strategy = result.prompt_type
                elif result.prompt_type == 'flawed':
                    # 根据severity确定具体的flawed类型
                    severity = None
                    if hasattr(result, 'flaw_severity'):
                        severity = result.flaw_severity
                    elif hasattr(result, 'test_id'):
                        if '_light' in result.test_id:
                            severity = 'light'
                        elif '_medium' in result.test_id:
                            severity = 'medium'
                        elif '_severe' in result.test_id:
                            severity = 'severe'
                    
                    if severity:
                        strategy = f'flawed_{severity}'
                    else:
                        continue  # 跳过无法确定severity的flawed结果
                else:
                    continue  # 跳过未知类型
                
                # 统计成功级别
                if strategy in strategy_data:
                    strategy_data[strategy]['total'] += 1
                    if getattr(result, 'success_level', '') == 'full_success':
                        strategy_data[strategy]['full_successes'] += 1
                    elif getattr(result, 'success_level', '') == 'partial_success':
                        strategy_data[strategy]['partial_successes'] += 1
        
        # 计算成功率
        full_rates = []
        partial_rates = []
        total_counts = []
        
        for strategy in strategies:
            data = strategy_data[strategy]
            if data['total'] > 0:
                full_rate = data['full_successes'] / data['total']
                partial_rate = data['partial_successes'] / data['total']
            else:
                full_rate = 0
                partial_rate = 0
            
            full_rates.append(full_rate)
            partial_rates.append(partial_rate)
            total_counts.append(data['total'])
            
            # 打印调试信息
            logger.debug(f" {strategy}: full={data['full_successes']}, "
                  f"partial={data['partial_successes']}, total={data['total']}")
        
        # 绘制堆叠条形图
        x = np.arange(len(strategies))
        width = 0.6
        
        # 绘制full success部分
        bars_full = ax.bar(x, full_rates, width, label='Full Success', alpha=0.9)
        
        # 绘制partial success部分（堆叠在full之上）
        bars_partial = ax.bar(x, partial_rates, width, bottom=full_rates, 
                             label='Partial Success', alpha=0.6)
        
        # 为每个条形图设置颜色
        for i, (bar_full, bar_partial) in enumerate(zip(bars_full, bars_partial)):
            bar_full.set_color(strategy_colors[i])
            bar_partial.set_color(strategy_colors[i])
        
        # 添加总成功率标注
        for i in range(len(strategies)):
            total_rate = full_rates[i] + partial_rates[i]
            if total_rate > 0:
                # 在柱子顶部添加总成功率
                ax.text(i, total_rate + 0.02, f'{total_rate:.1%}', 
                       ha='center', va='bottom', fontsize=10, fontweight='bold')
                
                # 在柱子内部添加full和partial的百分比（如果空间足够）
                if full_rates[i] > 0.1:  # 只有当full部分足够大时才显示
                    ax.text(i, full_rates[i] / 2, f'{full_rates[i]:.1%}', 
                           ha='center', va='center', fontsize=9, color='white', fontweight='bold')
                
                if partial_rates[i] > 0.1:  # 只有当partial部分足够大时才显示
                    ax.text(i, full_rates[i] + partial_rates[i] / 2, f'{partial_rates[i]:.1%}', 
                           ha='center', va='center', fontsize=9, color='white', fontweight='bold')
            
            # 在x轴下方添加样本数
            ax.text(i, -0.05, f'n={total_counts[i]}', 
                   ha='center', va='top', fontsize=8, color='gray')
        
        # 设置图表属性
        ax.set_xlabel('Prompt Strategy', fontsize=14, fontweight='bold')
        ax.set_ylabel('Success Rate', fontsize=14, fontweight='bold')
        ax.set_title('Comprehensive Success Rate Comparison Across All Strategies\n'
                     'Full Success vs Partial Success Breakdown', 
                     fontsize=16, fontweight='bold', pad=20)
        
        # 设置x轴标签
        ax.set_xticks(x)
        ax.set_xticklabels(strategy_labels, rotation=15, ha='right')
        
        # 设置y轴范围和网格
        ax.set_ylim(0, 1.15)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: '{:.0%}'.format(y)))
        ax.grid(True, axis='y', alpha=0.3, linestyle='--')
        
        # 添加图例
        ax.legend(loc='upper right', fontsize=12, framealpha=0.9)
        
        # 添加分隔线来区分基本策略和flawed策略
        ax.axvline(x=2.5, color='black', linestyle='--', alpha=0.3, linewidth=1)
        ax.text(1, 1.08, 'Basic Strategies', ha='center', va='bottom', 
                fontsize=11, style='italic', transform=ax.get_xaxis_transform())
        ax.text(4, 1.08, 'Flawed Strategies', ha='center', va='bottom', 
                fontsize=11, style='italic', transform=ax.get_xaxis_transform())
        
        # 添加性能趋势箭头（如果有明显趋势）
        if len(strategies) >= 6:
            # 计算平均成功率
            basic_avg = np.mean([full_rates[i] + partial_rates[i] for i in range(3)])
            flawed_avg = np.mean([full_rates[i] + partial_rates[i] for i in range(3, 6)])
            
            # 在图表底部添加汇总信息
            summary_text = (f'Basic Strategies Avg: {basic_avg:.1%} | '
                          f'Flawed Strategies Avg: {flawed_avg:.1%} | '
                          f'Difference: {basic_avg - flawed_avg:+.1%}')
            ax.text(0.5, -0.15, summary_text, ha='center', va='top', 
                   transform=ax.transAxes, fontsize=10, 
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgray', alpha=0.5))
        
        plt.tight_layout()
        plt.savefig(self.output_dir / "comprehensive_success_comparison.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        # 生成补充的详细统计表
        print("\n=== Comprehensive Success Rate Statistics ===")
        print(f"{'Strategy':<20} {'Total':<8} {'Full':<12} {'Partial':<12} {'Total SR':<10}")
        print("-" * 62)
        for i, strategy in enumerate(strategies):
            data = strategy_data[strategy]
            total_sr = (data['full_successes'] + data['partial_successes']) / data['total'] if data['total'] > 0 else 0
            full_sr = data['full_successes'] / data['total'] if data['total'] > 0 else 0
            partial_sr = data['partial_successes'] / data['total'] if data['total'] > 0 else 0
            
            print(f"{strategy_labels[i]:<20} {data['total']:<8} "
                  f"{full_sr:<12.1%} {partial_sr:<12.1%} {total_sr:<10.1%}")
    
    def _plot_quality_vs_achievement(self, results: Dict[str, List['ExecutionResult']]):  # <- 修改了这一行：使用字符串形式的类型注解
        """Plot task achievement vs execution quality scatter plot"""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Collect data by prompt strategy
        strategy_data = defaultdict(lambda: {
            'task_achievement': [],
            'execution_quality': [],
            'final_scores': []
        })
        
        # 收集所有结果，包括flawed
        for key, task_results in results.items():
            for result in task_results:
                # Skip if no detailed metrics
                if not hasattr(result, 'adherence_scores') or not result.adherence_scores:
                    continue
                
                strategy = result.prompt_type
                if result.prompt_type == 'flawed' and hasattr(result, 'flaw_severity'):
                    strategy = f"flawed_{result.flaw_severity}"
                
                # Extract metrics
                adherence = result.adherence_scores
                if 'task_completion' in adherence and 'execution_success_rate' in adherence:
                    strategy_data[strategy]['task_achievement'].append(adherence['task_completion'])
                    strategy_data[strategy]['execution_quality'].append(adherence['execution_success_rate'])
                    strategy_data[strategy]['final_scores'].append(result.final_score)
        
        # Define strategies and colors
        strategies = ['baseline', 'optimal', 'cot', 'flawed_light', 'flawed_medium', 'flawed_severe']
        colors = ['#ff7f0e', '#2ca02c', '#1f77b4', '#ffd700', '#ff8c00', '#dc143c']
        markers = ['o', 's', '^', 'v', 'D', 'X']
        
        # 检查是否有数据
        has_data = False
        
        # Plot scatter for each strategy
        for i, strategy in enumerate(strategies):
            if strategy in strategy_data and strategy_data[strategy]['task_achievement']:
                has_data = True
                task_scores = strategy_data[strategy]['task_achievement']
                quality_scores = strategy_data[strategy]['execution_quality']
                final_scores = strategy_data[strategy]['final_scores']
                
                # Create scatter plot with size based on final score
                sizes = [max(20, s * 200) for s in final_scores]  # Ensure minimum size
                
                scatter = ax.scatter(
                    task_scores, 
                    quality_scores, 
                    c=colors[i], 
                    s=sizes, 
                    alpha=0.6, 
                    marker=markers[i],
                    edgecolors='black',
                    linewidth=0.5,
                    label=strategy.replace('_', ' ').title()
                )
        
        if not has_data:
            ax.text(0.5, 0.5, 'No achievement vs quality data available',
                    ha='center', va='center', transform=ax.transAxes,
                    fontsize=14, color='gray')
        else:
            # Add diagonal reference line
            ax.plot([0, 1], [0, 1], 'k--', alpha=0.3, label='Perfect Balance')
            
            # Add quadrant labels
            ax.text(0.75, 0.25, 'High Achievement\nLow Quality', 
                    ha='center', va='center', alpha=0.5, fontsize=10)
            ax.text(0.25, 0.75, 'Low Achievement\nHigh Quality', 
                    ha='center', va='center', alpha=0.5, fontsize=10)
            ax.text(0.75, 0.75, 'Optimal\nPerformance', 
                    ha='center', va='center', alpha=0.5, fontsize=10, weight='bold')
            ax.text(0.25, 0.25, 'Poor\nPerformance', 
                    ha='center', va='center', alpha=0.5, fontsize=10)
            
            # Legend
            ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1), borderaxespad=0)
            
            # Add note about size
            ax.text(0.02, 0.98, 'Note: Bubble size represents final score', 
                    transform=ax.transAxes, va='top', fontsize=9, alpha=0.7)
        
        # Styling
        ax.set_xlabel('Task Achievement Score', fontsize=12)
        ax.set_ylabel('Execution Quality Score', fontsize=12)
        ax.set_title('Task Achievement vs Execution Quality by Strategy', fontsize=14, weight='bold')
        ax.set_xlim(-0.05, 1.05)
        ax.set_ylim(-0.05, 1.05)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / "achievement_vs_quality.png", dpi=300, bbox_inches='tight')
        plt.close()


    def _plot_phase2_metrics(self, results: Dict[str, List['ExecutionResult']]):
        """Plot Phase2 scoring metrics comparison"""
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        
        # Collect metrics by prompt type
        metrics_by_type = defaultdict(lambda: {
            'phase2_scores': [],
            'quality_scores': [],
            'workflow_scores': []
        })
        
        # 调试计数器
        total_results = 0
        flawed_results = 0
        
        for key, task_results in results.items():
            logger.debug(f" Phase2 metrics - Processing key: {key}")
            for result in task_results:
                total_results += 1
                if hasattr(result, 'phase2_score') and result.phase2_score is not None:
                    prompt_key = result.prompt_type
                    if result.prompt_type == 'flawed':
                        flawed_results += 1
                        if hasattr(result, 'flaw_severity'):
                            prompt_key = f"flawed_{result.flaw_severity}"
                        else:
                            # 尝试从test_id提取severity
                            if hasattr(result, 'test_id'):
                                if '_light' in result.test_id:
                                    prompt_key = 'flawed_light'
                                elif '_medium' in result.test_id:
                                    prompt_key = 'flawed_medium'
                                elif '_severe' in result.test_id:
                                    prompt_key = 'flawed_severe'
                        logger.debug(f" Added flawed result with key: {prompt_key}")
                    
                    metrics_by_type[prompt_key]['phase2_scores'].append(result.phase2_score)
                    
                    if hasattr(result, 'quality_score'):
                        metrics_by_type[prompt_key]['quality_scores'].append(result.quality_score)
                    
                    if hasattr(result, 'workflow_score'):
                        metrics_by_type[prompt_key]['workflow_scores'].append(result.workflow_score)
        
        logger.debug(f" Total results: {total_results}, Flawed results: {flawed_results}")
        logger.debug(f" Metrics by type keys: {metrics_by_type.keys()}")
        
        # Sort prompt types for consistent ordering
        prompt_types = ['baseline', 'optimal', 'cot', 'flawed_light', 'flawed_medium', 'flawed_severe']
        prompt_types = [pt for pt in prompt_types if pt in metrics_by_type]
        
        logger.debug(f" Prompt types to plot: {prompt_types}")
        
        # Plot 1: Phase2 Score
        ax = axes[0]
        phase2_data = []
        labels = []
        for pt in prompt_types:
            if metrics_by_type[pt]['phase2_scores']:
                phase2_data.append(metrics_by_type[pt]['phase2_scores'])
                labels.append(pt.replace('_', ' ').title())
        
        if phase2_data:
            bp = ax.boxplot(phase2_data, labels=labels, patch_artist=True)
            colors = ['#ff7f0e', '#2ca02c', '#1f77b4', '#ffd700', '#ff8c00', '#dc143c']
            for patch, color in zip(bp['boxes'], colors[:len(bp['boxes'])]):
                patch.set_facecolor(color)
                patch.set_alpha(0.7)
        else:
            ax.text(0.5, 0.5, 'No Phase2 score data available',
                    ha='center', va='center', transform=ax.transAxes,
                    fontsize=14, color='gray')
        
        ax.set_ylabel('Phase2 Score')
        ax.set_title('Phase2 Score Distribution')
        if labels:
            ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.grid(True, axis='y', alpha=0.3)
        
        # Plot 2: Quality Score
        ax = axes[1]
        quality_data = []
        labels = []
        for pt in prompt_types:
            if metrics_by_type[pt]['quality_scores']:
                quality_data.append(metrics_by_type[pt]['quality_scores'])
                labels.append(pt.replace('_', ' ').title())
        
        if quality_data:
            bp = ax.boxplot(quality_data, labels=labels, patch_artist=True)
            colors = ['#ff7f0e', '#2ca02c', '#1f77b4', '#ffd700', '#ff8c00', '#dc143c']
            for patch, color in zip(bp['boxes'], colors[:len(bp['boxes'])]):
                patch.set_facecolor(color)
                patch.set_alpha(0.7)
        else:
            ax.text(0.5, 0.5, 'No Quality score data available',
                    ha='center', va='center', transform=ax.transAxes,
                    fontsize=14, color='gray')
        
        ax.set_ylabel('Quality Score')
        ax.set_title('Execution Quality Score Distribution')
        if labels:
            ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.grid(True, axis='y', alpha=0.3)
        
        # Plot 3: Workflow Score
        ax = axes[2]
        workflow_data = []
        labels = []
        for pt in prompt_types:
            if metrics_by_type[pt]['workflow_scores']:
                workflow_data.append(metrics_by_type[pt]['workflow_scores'])
                labels.append(pt.replace('_', ' ').title())
        
        if workflow_data:
            bp = ax.boxplot(workflow_data, labels=labels, patch_artist=True)
            colors = ['#ff7f0e', '#2ca02c', '#1f77b4', '#ffd700', '#ff8c00', '#dc143c']
            for patch, color in zip(bp['boxes'], colors[:len(bp['boxes'])]):
                patch.set_facecolor(color)
                patch.set_alpha(0.7)
        else:
            ax.text(0.5, 0.5, 'No Workflow score data available',
                    ha='center', va='center', transform=ax.transAxes,
                    fontsize=14, color='gray')
        
        ax.set_ylabel('Workflow Score')
        ax.set_title('Workflow Adherence Score Distribution')
        if labels:
            ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.grid(True, axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / "phase2_metrics.png", dpi=300)
        plt.close()


    def _plot_execution_times(self, results: Dict[str, List['ExecutionResult']]):
        """Plot execution time analysis"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Collect execution times by prompt type
        times_by_prompt = defaultdict(list)
        times_by_task = defaultdict(lambda: defaultdict(list))
        
        # 收集基础任务类型
        base_task_types = set()
        
        for key, task_results in results.items():
            # 确定基础任务类型
            if '_flawed' in key:
                parts = key.split('_flawed_')
                if parts:
                    base_task_type = parts[0]
                else:
                    logger.debug(f" Skipping malformed key: {key}")
                    continue
            else:
                base_task_type = key
            
            base_task_types.add(base_task_type)
            
            # 收集执行时间数据
            for result in task_results:
                prompt_key = result.prompt_type
                if result.prompt_type == 'flawed' and hasattr(result, 'flaw_severity'):
                    prompt_key = f"flawed_{result.flaw_severity}"
                
                times_by_prompt[prompt_key].append(result.execution_time)
                times_by_task[base_task_type][prompt_key].append(result.execution_time)
                logger.debug(f" Added execution time for {prompt_key} in {base_task_type}: {result.execution_time}")
        
        # Plot 1: Overall execution time by prompt type
        prompt_types = ['baseline', 'optimal', 'cot', 'flawed_light', 'flawed_medium', 'flawed_severe']
        prompt_types = [pt for pt in prompt_types if pt in times_by_prompt]
        
        time_data = []
        labels = []
        for pt in prompt_types:
            if times_by_prompt[pt]:
                time_data.append(times_by_prompt[pt])
                labels.append(pt.replace('_', ' ').title())
        
        if time_data:
            bp = ax1.boxplot(time_data, labels=labels, patch_artist=True)
            colors = ['#ff7f0e', '#2ca02c', '#1f77b4', '#ffd700', '#ff8c00', '#dc143c']
            for patch, color in zip(bp['boxes'], colors[:len(bp['boxes'])]):
                patch.set_facecolor(color)
                patch.set_alpha(0.7)
            
            ax1.set_ylabel('Execution Time (seconds)')
            ax1.set_title('Execution Time by Prompt Strategy')
            ax1.set_xticklabels(labels, rotation=45, ha='right')
            ax1.grid(True, axis='y', alpha=0.3)
        else:
            ax1.text(0.5, 0.5, 'No execution time data available',
                    ha='center', va='center', transform=ax1.transAxes,
                    fontsize=14, color='gray')
        
        # Plot 2: Execution time by task type
        task_types = sorted(base_task_types)
        
        if task_types and any(times_by_task[tt] for tt in task_types):
            x = np.arange(len(task_types))
            width = 0.12  # Reduced width to fit 6 bars
            
            # Include all prompt types with severity
            all_prompt_types = ['baseline', 'optimal', 'cot', 'flawed_light', 'flawed_medium', 'flawed_severe']
            bar_colors = ['#ff7f0e', '#2ca02c', '#1f77b4', '#ffd700', '#ff8c00', '#dc143c']
            
            for i, pt in enumerate(all_prompt_types):
                means = []
                stds = []
                for task_type in task_types:
                    times = times_by_task[task_type].get(pt, [])
                    means.append(np.mean(times) if times else 0)
                    stds.append(np.std(times) if times else 0)
                
                if any(means):  # Only plot if there's data
                    ax2.bar(x + (i - 2.5) * width, means, width, 
                            yerr=stds, capsize=3, 
                            label=pt.replace('_', ' ').title(), 
                            color=bar_colors[i],
                            alpha=0.8)
            
            ax2.set_xlabel('Task Type')
            ax2.set_ylabel('Execution Time (seconds)')
            ax2.set_title('Average Execution Time by Task Type and Strategy')
            ax2.set_xticks(x)
            ax2.set_xticklabels(task_types, rotation=45, ha='right')
            ax2.legend(loc='upper left', bbox_to_anchor=(1, 1))
            ax2.grid(True, axis='y', alpha=0.3)
        else:
            ax2.text(0.5, 0.5, 'No execution time data available',
                    ha='center', va='center', transform=ax2.transAxes,
                    fontsize=14, color='gray')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / "execution_times.png", dpi=300, bbox_inches='tight')
        plt.close()



    def _plot_success_rates(self, results: Dict[str, List['ExecutionResult']]):
        """Plot success rate comparison with full and partial success breakdown"""
        fig, ax = plt.subplots(figsize=(16, 10))
        
        # Group results by task type
        task_types = set()
        for key in results.keys():
            # Extract base task type (without prompt_type suffix)
            if '_flawed' in key:
                # Handle flawed keys differently
                task_type = key.split('_flawed')[0]
            else:
                task_type = key
            task_types.add(task_type)
        
        task_types = sorted(list(task_types))
        
        # Prepare data - 分别统计 full 和 partial success
        baseline_full_rates = []
        baseline_partial_rates = []
        optimal_full_rates = []
        optimal_partial_rates = []
        cot_full_rates = []
        cot_partial_rates = []
        flawed_light_full_rates = []
        flawed_light_partial_rates = []
        flawed_medium_full_rates = []
        flawed_medium_partial_rates = []
        flawed_severe_full_rates = []
        flawed_severe_partial_rates = []
        
        for task_type in task_types:
            # 收集该任务类型的所有结果
            task_results = []
            for key, results_list in results.items():
                if (key == task_type or 
                    (key.startswith(task_type + '_flawed') and not key.endswith(('_light', '_medium', '_severe')))):
                    task_results.extend(results_list)
            
            # 计算各策略的成功率
            baseline = [r for r in task_results if r.prompt_type == "baseline"]
            optimal = [r for r in task_results if r.prompt_type == "optimal"]
            cot = [r for r in task_results if r.prompt_type == "cot"]
            
            # 分别统计 full 和 partial success
            baseline_full = sum(1 for r in baseline if getattr(r, 'success_level', '') == "full_success")
            baseline_partial = sum(1 for r in baseline if getattr(r, 'success_level', '') == "partial_success")
            baseline_full_rates.append(baseline_full / len(baseline) if baseline else 0)
            baseline_partial_rates.append(baseline_partial / len(baseline) if baseline else 0)
            
            optimal_full = sum(1 for r in optimal if getattr(r, 'success_level', '') == "full_success")
            optimal_partial = sum(1 for r in optimal if getattr(r, 'success_level', '') == "partial_success")
            optimal_full_rates.append(optimal_full / len(optimal) if optimal else 0)
            optimal_partial_rates.append(optimal_partial / len(optimal) if optimal else 0)
            
            cot_full = sum(1 for r in cot if getattr(r, 'success_level', '') == "full_success")
            cot_partial = sum(1 for r in cot if getattr(r, 'success_level', '') == "partial_success")
            cot_full_rates.append(cot_full / len(cot) if cot else 0)
            cot_partial_rates.append(cot_partial / len(cot) if cot else 0)
            
            # 为flawed也计算分级成功率
            flawed = [r for r in task_results if r.prompt_type == "flawed"]
            
            flawed_light = []
            flawed_medium = []
            flawed_severe = []
            
            for r in flawed:
                result_severity = None
                if hasattr(r, 'flaw_severity'):
                    result_severity = r.flaw_severity
                elif hasattr(r, 'test_id') and '_light' in r.test_id:
                    result_severity = 'light'
                elif hasattr(r, 'test_id') and '_medium' in r.test_id:
                    result_severity = 'medium'
                elif hasattr(r, 'test_id') and '_severe' in r.test_id:
                    result_severity = 'severe'
                
                if result_severity == 'light':
                    flawed_light.append(r)
                elif result_severity == 'medium':
                    flawed_medium.append(r)
                elif result_severity == 'severe':
                    flawed_severe.append(r)
            
            # Flawed Light
            flawed_light_full = sum(1 for r in flawed_light if getattr(r, 'success_level', '') == 'full_success')
            flawed_light_partial = sum(1 for r in flawed_light if getattr(r, 'success_level', '') == 'partial_success')
            flawed_light_full_rates.append(flawed_light_full / len(flawed_light) if flawed_light else 0)
            flawed_light_partial_rates.append(flawed_light_partial / len(flawed_light) if flawed_light else 0)
            
            # Flawed Medium
            flawed_medium_full = sum(1 for r in flawed_medium if getattr(r, 'success_level', '') == 'full_success')
            flawed_medium_partial = sum(1 for r in flawed_medium if getattr(r, 'success_level', '') == 'partial_success')
            flawed_medium_full_rates.append(flawed_medium_full / len(flawed_medium) if flawed_medium else 0)
            flawed_medium_partial_rates.append(flawed_medium_partial / len(flawed_medium) if flawed_medium else 0)
            
            # Flawed Severe
            flawed_severe_full = sum(1 for r in flawed_severe if getattr(r, 'success_level', '') == 'full_success')
            flawed_severe_partial = sum(1 for r in flawed_severe if getattr(r, 'success_level', '') == 'partial_success')
            flawed_severe_full_rates.append(flawed_severe_full / len(flawed_severe) if flawed_severe else 0)
            flawed_severe_partial_rates.append(flawed_severe_partial / len(flawed_severe) if flawed_severe else 0)
        
        # 绘制堆叠条形图
        x = np.arange(len(task_types))
        width = 0.13  # 减小宽度以容纳6个柱状图
        
        # Baseline
        ax.bar(x - 2.5*width, baseline_full_rates, width, label='Baseline (Full)', 
            color='#ff7f0e', alpha=0.9)
        ax.bar(x - 2.5*width, baseline_partial_rates, width, bottom=baseline_full_rates,
            label='Baseline (Partial)', color='#ff7f0e', alpha=0.5)
        
        # Optimal
        ax.bar(x - 1.5*width, optimal_full_rates, width, label='Optimal (Full)', 
            color='#2ca02c', alpha=0.9)
        ax.bar(x - 1.5*width, optimal_partial_rates, width, bottom=optimal_full_rates,
            label='Optimal (Partial)', color='#2ca02c', alpha=0.5)
        
        # CoT
        ax.bar(x - 0.5*width, cot_full_rates, width, label='CoT (Full)', 
            color='#1f77b4', alpha=0.9)
        ax.bar(x - 0.5*width, cot_partial_rates, width, bottom=cot_full_rates,
            label='CoT (Partial)', color='#1f77b4', alpha=0.5)
        
        # Flawed Light
        ax.bar(x + 0.5*width, flawed_light_full_rates, width, label='Flawed Light (Full)', 
            color='#ffd700', alpha=0.9)
        ax.bar(x + 0.5*width, flawed_light_partial_rates, width, bottom=flawed_light_full_rates,
            label='Flawed Light (Partial)', color='#ffd700', alpha=0.5)
        
        # Flawed Medium
        ax.bar(x + 1.5*width, flawed_medium_full_rates, width, label='Flawed Medium (Full)', 
            color='#ff8c00', alpha=0.9)
        ax.bar(x + 1.5*width, flawed_medium_partial_rates, width, bottom=flawed_medium_full_rates,
            label='Flawed Medium (Partial)', color='#ff8c00', alpha=0.5)
        
        # Flawed Severe
        ax.bar(x + 2.5*width, flawed_severe_full_rates, width, label='Flawed Severe (Full)', 
            color='#dc143c', alpha=0.9)
        ax.bar(x + 2.5*width, flawed_severe_partial_rates, width, bottom=flawed_severe_full_rates,
            label='Flawed Severe (Partial)', color='#dc143c', alpha=0.5)
        
        ax.set_xlabel('Task Type', fontsize=12)
        ax.set_ylabel('Success Rate', fontsize=12)
        ax.set_title('Success Rates by Task Type and Prompt Strategy\n(Full Success + Partial Success)', fontsize=14)
        ax.set_xticks(x)
        ax.set_xticklabels(task_types, rotation=45, ha='right')
        ax.legend(loc='upper left', bbox_to_anchor=(1, 1), ncol=1)
        ax.grid(True, axis='y', alpha=0.3)
        ax.set_ylim(0, 1.1)  # 留出一些顶部空间
        
        # 添加总成功率的文字标注
        for i, task_type in enumerate(task_types):
            # 为每个条形图添加总成功率标注
            total_baseline = baseline_full_rates[i] + baseline_partial_rates[i]
            total_optimal = optimal_full_rates[i] + optimal_partial_rates[i]
            total_cot = cot_full_rates[i] + cot_partial_rates[i]
            total_flawed_light = flawed_light_full_rates[i] + flawed_light_partial_rates[i]
            total_flawed_medium = flawed_medium_full_rates[i] + flawed_medium_partial_rates[i]
            total_flawed_severe = flawed_severe_full_rates[i] + flawed_severe_partial_rates[i]
            
            # 只为有数据的条形图添加标注
            if total_baseline > 0:
                ax.text(i - 2.5*width, total_baseline + 0.01, f'{total_baseline:.0%}',
                        ha='center', va='bottom', fontsize=8)
            if total_optimal > 0:
                ax.text(i - 1.5*width, total_optimal + 0.01, f'{total_optimal:.0%}',
                        ha='center', va='bottom', fontsize=8)
            if total_cot > 0:
                ax.text(i - 0.5*width, total_cot + 0.01, f'{total_cot:.0%}',
                        ha='center', va='bottom', fontsize=8)
            if total_flawed_light > 0:
                ax.text(i + 0.5*width, total_flawed_light + 0.01, f'{total_flawed_light:.0%}',
                        ha='center', va='bottom', fontsize=8)
            if total_flawed_medium > 0:
                ax.text(i + 1.5*width, total_flawed_medium + 0.01, f'{total_flawed_medium:.0%}',
                        ha='center', va='bottom', fontsize=8)
            if total_flawed_severe > 0:
                ax.text(i + 2.5*width, total_flawed_severe + 0.01, f'{total_flawed_severe:.0%}',
                        ha='center', va='bottom', fontsize=8)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / "success_rates.png", dpi=300, bbox_inches='tight')
        plt.close()
    def _plot_severity_impact(self, results: Dict[str, List['ExecutionResult']]):
        """Plot severity impact analysis for flawed workflows"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        # Group by task type and severity
        task_severity_data = defaultdict(lambda: {
            'light': {'full_successes': 0, 'partial_successes': 0, 'total': 0, 'scores': []},
            'medium': {'full_successes': 0, 'partial_successes': 0, 'total': 0, 'scores': []},
            'severe': {'full_successes': 0, 'partial_successes': 0, 'total': 0, 'scores': []}
        })
        
        # 提取基础任务类型
        base_task_types = set()
        
        # 处理所有key，包括flawed的
        for key, task_results in results.items():
            # 确定基础任务类型
            if '_flawed' in key:
                # 从 "task_type_flawed_flaw_type_severity" 提取 task_type
                parts = key.split('_flawed_')
                if parts:
                    base_task_type = parts[0]
                else:
                    logger.debug(f" Skipping malformed key: {key}")
                    continue
            else:
                base_task_type = key
            
            base_task_types.add(base_task_type)
            
            # 收集flawed数据
            for result in task_results:
                if result.prompt_type == 'flawed' and hasattr(result, 'flaw_severity'):
                    severity = result.flaw_severity
                    if severity in ['light', 'medium', 'severe']:
                        task_severity_data[base_task_type][severity]['total'] += 1
                        # 使用success_level统计
                        if getattr(result, 'success_level', '') == 'full_success':
                            task_severity_data[base_task_type][severity]['full_successes'] += 1
                        elif getattr(result, 'success_level', '') == 'partial_success':
                            task_severity_data[base_task_type][severity]['partial_successes'] += 1
                        task_severity_data[base_task_type][severity]['scores'].append(result.final_score)
        
        # Plot 1: Success rate degradation by severity (堆叠条形图)
        task_types = sorted(base_task_types)
        severities = ['light', 'medium', 'severe']
        
        x = np.arange(len(task_types))
        width = 0.25
        
        for i, severity in enumerate(severities):
            full_rates = []
            partial_rates = []
            for task_type in task_types:
                data = task_severity_data[task_type][severity]
                full_rate = data['full_successes'] / data['total'] if data['total'] > 0 else 0
                partial_rate = data['partial_successes'] / data['total'] if data['total'] > 0 else 0
                full_rates.append(full_rate)
                partial_rates.append(partial_rate)
            
            color = {'light': '#ffd700', 'medium': '#ff8c00', 'severe': '#dc143c'}[severity]
            # 堆叠条形图
            ax1.bar(x + (i - 1) * width, full_rates, width, 
                    label=f'{severity.title()} (Full)', color=color, alpha=0.9)
            ax1.bar(x + (i - 1) * width, partial_rates, width, bottom=full_rates,
                    label=f'{severity.title()} (Partial)', color=color, alpha=0.5)
            
            # 添加总成功率标注
            for j, task_type in enumerate(task_types):
                total_rate = full_rates[j] + partial_rates[j]
                if total_rate > 0:
                    ax1.text(j + (i - 1) * width, total_rate + 0.01, f'{total_rate:.0%}',
                            ha='center', va='bottom', fontsize=8)
        
        ax1.set_xlabel('Task Type')
        ax1.set_ylabel('Success Rate')
        ax1.set_title('Success Rate by Task Type and Severity Level\n(Full + Partial Success)')
        ax1.set_xticks(x)
        ax1.set_xticklabels(task_types, rotation=45, ha='right')
        ax1.legend()
        ax1.grid(True, axis='y', alpha=0.3)
        ax1.set_ylim(0, 1.1)
        
        # Plot 2: Score distribution by severity (保持不变)
        severity_scores = {
            'light': [],
            'medium': [],
            'severe': []
        }
        
        for task_type_data in task_severity_data.values():
            for severity in severities:
                severity_scores[severity].extend(task_type_data[severity]['scores'])
        
        # Create box plot for scores
        score_data = []
        score_labels = []
        for severity in severities:
            if severity_scores[severity]:
                score_data.append(severity_scores[severity])
                score_labels.append(severity.title())
        
        if score_data:
            bp = ax2.boxplot(score_data, labels=score_labels, patch_artist=True)
            colors = ['#ffd700', '#ff8c00', '#dc143c']
            for patch, color in zip(bp['boxes'], colors[:len(bp['boxes'])]):
                patch.set_facecolor(color)
                patch.set_alpha(0.7)
            
            ax2.set_ylabel('Final Score')
            ax2.set_title('Score Distribution by Severity Level')
            ax2.grid(True, axis='y', alpha=0.3)
        else:
            ax2.text(0.5, 0.5, 'No severity score data available',
                    ha='center', va='center', transform=ax2.transAxes,
                    fontsize=14, color='gray')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / "severity_impact.png", dpi=300)
        plt.close()
        


    def _plot_flaw_sensitivity(self, results: Dict[str, List['ExecutionResult']]):
        """Plot flaw type sensitivity analysis"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        # Collect data by flaw type and severity
        flaw_data = defaultdict(lambda: {
            'light': {'full_success_rates': [], 'partial_success_rates': [], 'scores': []},
            'medium': {'full_success_rates': [], 'partial_success_rates': [], 'scores': []},
            'severe': {'full_success_rates': [], 'partial_success_rates': [], 'scores': []}
        })
        
        # 提取缺陷类型和严重程度数据
        for key, task_results in results.items():
            if '_flawed_' in key:
                # 解析key获取flaw type和severity
                parts = key.split('_flawed_')
                if len(parts) == 2:
                    flaw_parts = parts[1].split('_')
                    if len(flaw_parts) >= 2:
                        # 最后一个部分是severity，其余是flaw_type
                        severity = flaw_parts[-1]
                        flaw_type = '_'.join(flaw_parts[:-1])
                        
                        if severity in ['light', 'medium', 'severe']:
                            # 统计分级成功率
                            full_successes = sum(1 for r in task_results if getattr(r, 'success_level', '') == 'full_success')
                            partial_successes = sum(1 for r in task_results if getattr(r, 'success_level', '') == 'partial_success')
                            total = len(task_results)
                            scores = [r.final_score for r in task_results]
                            
                            if total > 0:
                                flaw_data[flaw_type][severity]['full_success_rates'].append(full_successes / total)
                                flaw_data[flaw_type][severity]['partial_success_rates'].append(partial_successes / total)
                                flaw_data[flaw_type][severity]['scores'].extend(scores)
                                logger.debug(f" Added flaw data: {flaw_type} - {severity}: full={full_successes}, partial={partial_successes}, total={total}")
        
        if not flaw_data:
            ax1.text(0.5, 0.5, 'No flaw sensitivity data available',
                    ha='center', va='center', transform=ax1.transAxes,
                    fontsize=14, color='gray')
            ax2.text(0.5, 0.5, 'No flaw sensitivity data available',
                    ha='center', va='center', transform=ax2.transAxes,
                    fontsize=14, color='gray')
            plt.tight_layout()
            plt.savefig(self.output_dir / "flaw_sensitivity.png", dpi=300)
            plt.close()
            return
        
        # Plot 1: Success rate by flaw type and severity (堆叠条形图)
        flaw_types = sorted(flaw_data.keys())
        severities = ['light', 'medium', 'severe']
        
        x = np.arange(len(flaw_types))
        width = 0.25
        
        for i, severity in enumerate(severities):
            full_rates = []
            partial_rates = []
            for flaw_type in flaw_types:
                full_list = flaw_data[flaw_type][severity]['full_success_rates']
                partial_list = flaw_data[flaw_type][severity]['partial_success_rates']
                full_rates.append(np.mean(full_list) if full_list else 0)
                partial_rates.append(np.mean(partial_list) if partial_list else 0)
            
            color = ['#ffd700', '#ff8c00', '#dc143c'][i]
            # 堆叠条形图
            ax1.bar(x + (i - 1) * width, full_rates, width,
                    label=f'{severity.capitalize()} (Full)', color=color, alpha=0.9)
            ax1.bar(x + (i - 1) * width, partial_rates, width, bottom=full_rates,
                    label=f'{severity.capitalize()} (Partial)', color=color, alpha=0.5)
            
            # 添加总成功率标注
            for j, flaw_type in enumerate(flaw_types):
                total_rate = full_rates[j] + partial_rates[j]
                if total_rate > 0:
                    ax1.text(j + (i - 1) * width, total_rate + 0.01, f'{total_rate:.0%}',
                            ha='center', va='bottom', fontsize=8)
        
        ax1.set_xlabel('Flaw Type')
        ax1.set_ylabel('Success Rate')
        ax1.set_title('Success Rate by Flaw Type and Severity\n(Full + Partial Success)')
        ax1.set_xticks(x)
        ax1.set_xticklabels([ft.replace('_', ' ').title() for ft in flaw_types], rotation=45, ha='right')
        ax1.legend()
        ax1.grid(True, axis='y', alpha=0.3)
        ax1.set_ylim(0, 1.1)
        
        # Plot 2: Score impact (保持不变)
        for i, severity in enumerate(severities):
            mean_scores = []
            std_scores = []
            for flaw_type in flaw_types:
                scores = flaw_data[flaw_type][severity]['scores']
                mean_scores.append(np.mean(scores) if scores else 0)
                std_scores.append(np.std(scores) if scores else 0)
            
            color = ['#ffd700', '#ff8c00', '#dc143c'][i]
            ax2.bar(x + (i - 1) * width, mean_scores, width,
                    yerr=std_scores, capsize=5,
                    label=severity.capitalize(), color=color, alpha=0.8)
        
        ax2.set_xlabel('Flaw Type')
        ax2.set_ylabel('Average Score')
        ax2.set_title('Score Impact by Flaw Type and Severity')
        ax2.set_xticks(x)
        ax2.set_xticklabels([ft.replace('_', ' ').title() for ft in flaw_types], rotation=45, ha='right')
        ax2.legend()
        ax2.grid(True, axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / "flaw_sensitivity.png", dpi=300)

        # Plot 3: Full vs Partial Success Breakdown (新增)
        fig3, ax3 = plt.subplots(figsize=(12, 8))
        
        x = np.arange(len(flaw_types))
        width = 0.2
        
        for i, severity in enumerate(severities):
            full_rates = []
            partial_rates = []
            for flaw_type in flaw_types:
                full_list = flaw_data[flaw_type][severity].get('full_success_rates', [])
                partial_list = flaw_data[flaw_type][severity].get('partial_success_rates', [])
                full_rates.append(np.mean(full_list) if full_list else 0)
                partial_rates.append(np.mean(partial_list) if partial_list else 0)
            
            color = ['#ffd700', '#ff8c00', '#dc143c'][i]
            # 堆叠条形图
            ax3.bar(x + (i - 1) * width, full_rates, width,
                    label=f'{severity.capitalize()} (Full)', color=color, alpha=0.9)
            ax3.bar(x + (i - 1) * width, partial_rates, width, bottom=full_rates,
                    label=f'{severity.capitalize()} (Partial)', color=color, alpha=0.5)
        
        ax3.set_xlabel('Flaw Type')
        ax3.set_ylabel('Success Rate')
        ax3.set_title('Full vs Partial Success Rate by Flaw Type and Severity')
        ax3.set_xticks(x)
        ax3.set_xticklabels([ft.replace('_', ' ').title() for ft in flaw_types], rotation=45, ha='right')
        ax3.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax3.grid(True, axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / "flaw_sensitivity_graded.png", dpi=300, bbox_inches='tight')
        plt.close()

    def _plot_quality_breakdown(self, results: Dict[str, List['ExecutionResult']]):
        """Plot detailed quality metrics breakdown"""
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        # Collect detailed metrics
        metrics_by_strategy = defaultdict(lambda: {
            'task_achievement': [],
            'execution_quality': [],
            'tool_coverage': [],
            'efficiency': []
        })
        
        # 调试计数器
        total_results = 0
        flawed_with_adherence = 0
        
        for key, task_results in results.items():
            logger.debug(f" Quality breakdown - Processing key: {key}")
            for result in task_results:
                total_results += 1
                # Skip if no detailed metrics
                if not hasattr(result, 'adherence_scores') or not result.adherence_scores:
                    continue
                
                strategy = result.prompt_type
                if result.prompt_type == 'flawed':
                    flawed_with_adherence += 1
                    if hasattr(result, 'flaw_severity'):
                        strategy = f"flawed_{result.flaw_severity}"
                    else:
                        # 尝试从test_id提取severity
                        if hasattr(result, 'test_id'):
                            if '_light' in result.test_id:
                                strategy = 'flawed_light'
                            elif '_medium' in result.test_id:
                                strategy = 'flawed_medium'
                            elif '_severe' in result.test_id:
                                strategy = 'flawed_severe'
                    logger.debug(f" Flawed strategy: {strategy}")
                
                # Extract metrics from adherence scores
                adherence = result.adherence_scores
                if 'task_completion' in adherence:
                    metrics_by_strategy[strategy]['task_achievement'].append(adherence['task_completion'])
                if 'execution_success_rate' in adherence:
                    metrics_by_strategy[strategy]['execution_quality'].append(adherence['execution_success_rate'])
                if 'tool_diversity' in adherence:
                    metrics_by_strategy[strategy]['tool_coverage'].append(adherence['tool_diversity'])
                if 'efficiency' in adherence:
                    metrics_by_strategy[strategy]['efficiency'].append(adherence['efficiency'])
        
        logger.debug(f" Total results: {total_results}, Flawed with adherence: {flawed_with_adherence}")
        logger.debug(f" Strategies found: {metrics_by_strategy.keys()}")
        
        # Define metric names and their subplot positions
        metrics_info = [
            ('task_achievement', 'Task Achievement Score', axes[0, 0]),
            ('execution_quality', 'Execution Quality Score', axes[0, 1]),
            ('tool_coverage', 'Tool Coverage/Diversity', axes[1, 0]),
            ('efficiency', 'Execution Efficiency', axes[1, 1])
        ]
        
        # Strategy order and colors
        strategies = ['baseline', 'optimal', 'cot', 'flawed_light', 'flawed_medium', 'flawed_severe']
        colors = ['#ff7f0e', '#2ca02c', '#1f77b4', '#ffd700', '#ff8c00', '#dc143c']
        
        for metric_key, title, ax in metrics_info:
            # Prepare data for plotting
            plot_data = []
            plot_labels = []
            plot_colors = []
            
            for i, strategy in enumerate(strategies):
                if strategy in metrics_by_strategy and metrics_by_strategy[strategy][metric_key]:
                    plot_data.append(metrics_by_strategy[strategy][metric_key])
                    plot_labels.append(strategy.replace('_', ' ').title())
                    plot_colors.append(colors[i])
                    logger.debug(f" {title} - Adding {strategy} with {len(metrics_by_strategy[strategy][metric_key])} data points")
            
            if plot_data:
                # Create violin plot
                parts = ax.violinplot(plot_data, showmeans=True, showmedians=True)
                
                # Color the violin plots
                for pc, color in zip(parts['bodies'], plot_colors):
                    pc.set_facecolor(color)
                    pc.set_alpha(0.7)
                
                # Style the plot
                ax.set_xticks(range(1, len(plot_labels) + 1))
                ax.set_xticklabels(plot_labels, rotation=45, ha='right')
                ax.set_ylabel('Score')
                ax.set_title(title)
                ax.grid(True, axis='y', alpha=0.3)
                ax.set_ylim(0, 1.1)
                
                # Add mean values as text
                for i, data in enumerate(plot_data):
                    mean_val = np.mean(data)
                    ax.text(i + 1, mean_val + 0.05, f'{mean_val:.2f}', 
                        ha='center', va='bottom', fontsize=9)
            else:
                ax.text(0.5, 0.5, 'No data available', 
                    ha='center', va='center', transform=ax.transAxes,
                    fontsize=14, color='gray')
                ax.set_title(title)
        
        plt.suptitle('Detailed Quality Metrics Breakdown', fontsize=16)
        plt.tight_layout()
        plt.savefig(self.output_dir / "quality_breakdown.png", dpi=300)
        plt.close()


    def _plot_score_distribution(self, results: Dict[str, List['ExecutionResult']]):
        """Plot score distribution"""
        fig, ax = plt.subplots(figsize=(12, 6))  # 增加宽度
        
        # Collect scores by prompt type (包括flawed按severity分开)
        baseline_scores = []
        optimal_scores = []
        cot_scores = []
        flawed_light_scores = []
        flawed_medium_scores = []
        flawed_severe_scores = []
        
        # 添加调试计数器
        flawed_count = 0
        
        for key, task_results in results.items():
            logger.debug(f" Processing key: {key} with {len(task_results)} results")
            for result in task_results:
                if result.prompt_type == "baseline":
                    baseline_scores.append(result.final_score)
                elif result.prompt_type == "optimal":
                    optimal_scores.append(result.final_score)
                elif result.prompt_type == "cot":
                    cot_scores.append(result.final_score)
                elif result.prompt_type == "flawed":
                    flawed_count += 1
                    # 提取severity信息
                    result_severity = None
                    if hasattr(result, 'flaw_severity'):
                        result_severity = result.flaw_severity
                    elif hasattr(result, 'test_id'):
                        if '_light' in result.test_id:
                            result_severity = 'light'
                        elif '_medium' in result.test_id:
                            result_severity = 'medium'
                        elif '_severe' in result.test_id:
                            result_severity = 'severe'
                    
                    logger.debug(f" Flawed result with severity: {result_severity}")
                    
                    if result_severity == 'light':
                        flawed_light_scores.append(result.final_score)
                    elif result_severity == 'medium':
                        flawed_medium_scores.append(result.final_score)
                    elif result_severity == 'severe':
                        flawed_severe_scores.append(result.final_score)
        
        logger.debug(f" Total flawed results found: {flawed_count}")
        logger.debug(f" Flawed light: {len(flawed_light_scores)}, medium: {len(flawed_medium_scores)}, severe: {len(flawed_severe_scores)}")
        
        # Filter out empty lists and prepare data
        data = []
        labels = []
        positions = []
        pos = 0
        
        if baseline_scores:
            data.append(baseline_scores)
            labels.append('Baseline')
            positions.append(pos)
            pos += 1
        
        if optimal_scores:
            data.append(optimal_scores)
            labels.append('Optimal')
            positions.append(pos)
            pos += 1
            
        if cot_scores:
            data.append(cot_scores)
            labels.append('CoT')
            positions.append(pos)
            pos += 1
        
        if flawed_light_scores:
            data.append(flawed_light_scores)
            labels.append('Flawed Light')
            positions.append(pos)
            pos += 1
        
        if flawed_medium_scores:
            data.append(flawed_medium_scores)
            labels.append('Flawed Medium')
            positions.append(pos)
            pos += 1
        
        if flawed_severe_scores:
            data.append(flawed_severe_scores)
            labels.append('Flawed Severe')
            positions.append(pos)
            pos += 1
        
        # Only plot if we have data
        if data:
            # Create violin plot
            parts = ax.violinplot(data, positions=positions, showmeans=True, showmedians=True)
            
            # 设置不同的颜色
            colors = ['#ff7f0e', '#2ca02c', '#1f77b4', '#ffd700', '#ff8c00', '#dc143c']
            for i, pc in enumerate(parts['bodies']):
                if i < len(colors):
                    pc.set_facecolor(colors[i])
                    pc.set_alpha(0.7)
            
            ax.set_xticks(positions)
            ax.set_xticklabels(labels, rotation=45, ha='right')
            ax.set_ylabel('Final Score')
            ax.set_title('Score Distribution by Prompt Strategy (Including Severity Levels)')
            ax.grid(True, axis='y', alpha=0.3)
        else:
            # No data to plot
            ax.text(0.5, 0.5, 'No data available for plotting', 
                    ha='center', va='center', transform=ax.transAxes,
                    fontsize=14, color='gray')
            ax.set_title('Score Distribution by Prompt Strategy (No Data)')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / "score_distribution.png", dpi=300)
        plt.close()


    def _plot_workflow_adherence(self, results: Dict[str, List['ExecutionResult']]):
        """Plot workflow adherence for ALL prompt strategies (not just optimal)"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        # Plot 1: Adherence by prompt type
        adherence_by_prompt = defaultdict(list)
        
        # 收集所有结果，包括flawed
        for key, task_results in results.items():
            for result in task_results:
                # 收集所有prompt types的adherence
                if result.adherence_scores and 'overall_adherence' in result.adherence_scores:
                    prompt_key = result.prompt_type
                    if result.prompt_type == 'flawed' and hasattr(result, 'flaw_severity'):
                        prompt_key = f"flawed_{result.flaw_severity}"
                    
                    adherence = result.adherence_scores.get('overall_adherence', 0)
                    adherence_by_prompt[prompt_key].append(adherence)
                    logger.debug(f" Added adherence for {prompt_key}: {adherence}")
        
        # 准备数据
        prompt_types = ['baseline', 'optimal', 'cot', 'flawed_light', 'flawed_medium', 'flawed_severe']
        adherence_data = []
        labels = []
        
        for pt in prompt_types:
            if pt in adherence_by_prompt and adherence_by_prompt[pt]:
                adherence_data.append(adherence_by_prompt[pt])
                labels.append(pt.replace('_', ' ').title())
        
        # 绘制箱线图
        if adherence_data:
            bp = ax1.boxplot(adherence_data, labels=labels, patch_artist=True)
            colors = ['#ff7f0e', '#2ca02c', '#1f77b4', '#ffd700', '#ff8c00', '#dc143c']
            for patch, color in zip(bp['boxes'], colors[:len(bp['boxes'])]):
                patch.set_facecolor(color)
                patch.set_alpha(0.7)
            
            ax1.set_xlabel('Prompt Strategy')
            ax1.set_ylabel('Workflow Adherence Score')
            ax1.set_title('Workflow Adherence Distribution by Strategy')
            ax1.set_xticklabels(labels, rotation=45, ha='right')
            ax1.grid(True, axis='y', alpha=0.3)
        else:
            ax1.text(0.5, 0.5, 'No adherence data available',
                    ha='center', va='center', transform=ax1.transAxes,
                    fontsize=14, color='gray')
        
        # Plot 2: Adherence components breakdown
        components_by_prompt = defaultdict(lambda: {
            'task_completion': [],
            'execution_success_rate': [],
            'efficiency': [],
            'tool_diversity': []
        })
        
        # 收集所有结果的组件数据
        for key, task_results in results.items():
            for result in task_results:
                if result.adherence_scores and len(result.adherence_scores) > 1:
                    prompt_key = result.prompt_type
                    if result.prompt_type == 'flawed' and hasattr(result, 'flaw_severity'):
                        prompt_key = f"flawed_{result.flaw_severity}"
                    
                    for component in ['task_completion', 'execution_success_rate', 'efficiency', 'tool_diversity']:
                        if component in result.adherence_scores:
                            components_by_prompt[prompt_key][component].append(
                                result.adherence_scores[component]
                            )
        
        # 绘制组件对比 - 扩展到包括所有策略
        if components_by_prompt:
            component_names = ['Task Completion', 'Success Rate', 'Efficiency', 'Tool Diversity']
            x = np.arange(len(component_names))
            width = 0.12  # 减小宽度以容纳6个策略
            
            strategies_to_plot = ['baseline', 'optimal', 'cot', 'flawed_light', 'flawed_medium', 'flawed_severe']
            bar_colors = ['#ff7f0e', '#2ca02c', '#1f77b4', '#ffd700', '#ff8c00', '#dc143c']
            
            for i, (prompt_type, color) in enumerate(zip(strategies_to_plot, bar_colors)):
                if prompt_type in components_by_prompt:
                    means = []
                    for comp in ['task_completion', 'execution_success_rate', 'efficiency', 'tool_diversity']:
                        values = components_by_prompt[prompt_type][comp]
                        means.append(np.mean(values) if values else 0)
                    
                    if any(means):  # 只有有数据时才绘制
                        ax2.bar(x + (i - 2.5) * width, means, width, 
                            label=prompt_type.replace('_', ' ').title(), 
                            color=color, alpha=0.8)
            
            ax2.set_xlabel('Adherence Components')
            ax2.set_ylabel('Average Score')
            ax2.set_title('Adherence Components by Strategy')
            ax2.set_xticks(x)
            ax2.set_xticklabels(component_names, rotation=45, ha='right')
            ax2.legend(loc='upper left', bbox_to_anchor=(1, 1))
            ax2.grid(True, axis='y', alpha=0.3)
        else:
            ax2.text(0.5, 0.5, 'No component data available',
                    ha='center', va='center', transform=ax2.transAxes,
                    fontsize=14, color='gray')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / "workflow_adherence.png", dpi=300, bbox_inches='tight')
        plt.close()


class ReportGenerator:
    """Unified report generator for various system components"""
    
    def __init__(self, output_dir: Union[str, Path] = "."):
        """Initialize report generator
        
        Args:
            output_dir: Directory to save reports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_tool_task_report(self, summary: Dict[str, Any], output_filename: str = "generation_report.txt") -> Path:
        """Generate human-readable report for tool and task generation
        
        Args:
            summary: Summary statistics from tool/task generation
            output_filename: Name of the output file
            
        Returns:
            Path to the generated report
        """
        report = [
            "MCP Tool and Task Generation Report",
            "=" * 40,
            f"Generated: {summary.get('generation_timestamp', datetime.now().isoformat())}",
            "",
            "Tool Statistics:",
            f"  Total tools: {summary['tool_statistics']['total_tools']}",
            "  By category:"
        ]
        
        for category, count in summary['tool_statistics']['tools_by_category'].items():
            report.append(f"    - {category}: {count}")
        
        report.extend([
            "",
            "Task Statistics:",
            f"  Total tasks: {summary['task_statistics']['total_tasks']}",
            "  By type:"
        ])
        
        for task_type, count in summary['task_statistics']['tasks_by_type'].items():
            report.append(f"    - {task_type}: {count}")
        
        report.extend([
            "  By complexity:",
            f"    - Easy: {summary['task_statistics']['tasks_by_complexity']['easy']}",
            f"    - Medium: {summary['task_statistics']['tasks_by_complexity']['medium']}",
            f"    - Hard: {summary['task_statistics']['tasks_by_complexity']['hard']}",
            "",
            "Top 10 Most Used Tools:"
        ])
        
        tool_usage = sorted(
            summary['task_statistics']['tool_usage'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        for tool, count in tool_usage:
            report.append(f"  - {tool}: {count} tasks")
        
        report_path = self.output_dir / output_filename
        with open(report_path, 'w') as f:
            f.write("\n".join(report))
        
        logger.info(f"Tool/task report generated: {report_path}")
        return report_path
    
    def generate_workflow_quality_report(self, results: Dict[str, Any], output_filename: str = "workflow_quality_report.md") -> Path:
        """Generate comprehensive workflow quality test report in Markdown format
        
        Args:
            results: Test results dictionary containing:
                - timestamp: When the test was run
                - summary: Overall summary statistics
                - test_results or all_results: Detailed results by task type
            output_filename: Name of the output file
            
        Returns:
            Path to the generated report
        """
        report_path = self.output_dir / output_filename
        
        with open(report_path, 'w') as f:
            f.write("# Workflow Quality Test Report\n\n")
            f.write(f"Generated: {results.get('timestamp', datetime.now().isoformat())}\n\n")
            
            # Executive Summary
            summary = results.get('summary', {})
            f.write("## Executive Summary\n\n")
            f.write(f"- Total tests: {summary.get('total_tests', 0)}\n")
            f.write(f"- Baseline success rate: {summary.get('baseline_success_rate', 0):.2%}\n")
            f.write(f"- Optimal success rate: {summary.get('optimal_success_rate', 0):.2%}\n")
            f.write(f"- CoT success rate: {summary.get('cot_success_rate', 0):.2%}\n")
            f.write(f"- Success rate improvement: {summary.get('success_rate_improvement', 0):+.2%}\n")
            f.write(f"- Score improvement: {summary.get('score_improvement', 0):+.3f}\n\n")
            
            # 1. Overall Performance Analysis
            f.write("## Overall Performance Analysis\n\n")
            
            # Collect all results for analysis
            all_results_flat = []
            all_results_dict = results.get('all_results', results.get('test_results', {}))
            
            for key, results_list in all_results_dict.items():
                if isinstance(results_list, list):
                    all_results_flat.extend(results_list)
            
            # Performance by Prompt Strategy table with graded success
            f.write("### Performance by Prompt Strategy\n\n")
            f.write("| Prompt Type | Total Tests | Total Success Rate | Full Success | Partial Success | Avg Score |\n")
            f.write("|-------------|-------------|--------------------|--------------|-----------------|------------|\n")
            
            # Calculate metrics by prompt type
            prompt_types = ['baseline', 'optimal', 'cot']
            
            for prompt_type in prompt_types:
                type_results = [r for r in all_results_flat if hasattr(r, 'prompt_type') and r.prompt_type == prompt_type]
                if type_results:
                    # 统计分级成功率
                    full_success = sum(1 for r in type_results if getattr(r, 'success_level', '') == 'full_success')
                    partial_success = sum(1 for r in type_results if getattr(r, 'success_level', '') == 'partial_success')
                    total_success = full_success + partial_success
                    
                    total_tests = len(type_results)
                    total_success_rate = total_success / total_tests if total_tests > 0 else 0
                    full_success_rate = full_success / total_tests if total_tests > 0 else 0
                    partial_success_rate = partial_success / total_tests if total_tests > 0 else 0
                    avg_score = np.mean([getattr(r, 'final_score', 0) for r in type_results])
                    
                    f.write(f"| {prompt_type.capitalize()} | {total_tests} | {total_success_rate:.2%} | "
                            f"{full_success_rate:.2%} | {partial_success_rate:.2%} | {avg_score:.3f} |\n")
            
            # Performance by Flawed Severity (if applicable)
            flawed_results = [r for r in all_results_flat if hasattr(r, 'prompt_type') and r.prompt_type == 'flawed']
            if flawed_results:
                f.write("\n### Performance by Flawed Severity\n\n")
                f.write("| Severity Level | Total Tests | Total Success Rate | Full Success | Partial Success | Avg Score |\n")
                f.write("|----------------|-------------|--------------------|--------------|-----------------|------------|\n")
                
                flawed_severities = ['light', 'medium', 'severe']
                for severity in flawed_severities:
                    severity_results = [r for r in flawed_results 
                                    if (hasattr(r, 'flaw_severity') and r.flaw_severity == severity) or
                                        (hasattr(r, 'test_id') and f'_{severity}' in r.test_id)]
                    if severity_results:
                        # 添加调试打印
                        logger.debug(f" Processing {severity} severity with {len(severity_results)} results")
                        
                        # 统计分级成功率
                        full_success = sum(1 for r in severity_results if getattr(r, 'success_level', '') == 'full_success')
                        partial_success = sum(1 for r in severity_results if getattr(r, 'success_level', '') == 'partial_success')
                        total_success = full_success + partial_success
                        
                        total_tests = len(severity_results)
                        total_success_rate = total_success / total_tests if total_tests > 0 else 0
                        full_success_rate = full_success / total_tests if total_tests > 0 else 0
                        partial_success_rate = partial_success / total_tests if total_tests > 0 else 0
                        avg_score = np.mean([getattr(r, 'final_score', 0) for r in severity_results])
                        
                        # 添加调试信息
                        logger.debug(f" {severity}: full={full_success}, partial={partial_success}, total={total_success}")
                        
                        f.write(f"| {severity.capitalize()} | {total_tests} | {total_success_rate:.2%} | "
                                f"{full_success_rate:.2%} | {partial_success_rate:.2%} | {avg_score:.3f} |\n")
                
                # 添加按缺陷类型的分级成功率统计
                f.write("\n### Performance by Flaw Type\n\n")
                f.write("| Flaw Type | Total Tests | Total Success Rate | Full Success | Partial Success | Avg Score |\n")
                f.write("|-----------|-------------|--------------------|--------------|-----------------|------------|\n")
                
                # 收集所有缺陷类型
                flaw_types = set()
                for r in flawed_results:
                    if hasattr(r, 'flaw_type') and r.flaw_type:
                        flaw_types.add(r.flaw_type)
                
                for flaw_type in sorted(flaw_types):
                    flaw_type_results = [r for r in flawed_results if getattr(r, 'flaw_type', '') == flaw_type]
                    if flaw_type_results:
                        # 统计分级成功率
                        full_success = sum(1 for r in flaw_type_results if getattr(r, 'success_level', '') == 'full_success')
                        partial_success = sum(1 for r in flaw_type_results if getattr(r, 'success_level', '') == 'partial_success')
                        total_success = full_success + partial_success
                        
                        total_tests = len(flaw_type_results)
                        total_success_rate = total_success / total_tests if total_tests > 0 else 0
                        full_success_rate = full_success / total_tests if total_tests > 0 else 0
                        partial_success_rate = partial_success / total_tests if total_tests > 0 else 0
                        avg_score = np.mean([getattr(r, 'final_score', 0) for r in flaw_type_results])
                        
                        f.write(f"| {flaw_type.replace('_', ' ').title()} | {total_tests} | {total_success_rate:.2%} | "
                                f"{full_success_rate:.2%} | {partial_success_rate:.2%} | {avg_score:.3f} |\n")
            
            # 2. Detailed Results by Task Type
            f.write("\n## Detailed Results by Task Type\n\n")
            
            # 重新组织数据按task_type分组
            task_type_results = {}
            for key, results_list in all_results_dict.items():
                if isinstance(results_list, list) and results_list:
                    # 从结果中提取task_type
                    task_type = results_list[0].task_type if hasattr(results_list[0], 'task_type') else 'unknown'
                    if task_type not in task_type_results:
                        task_type_results[task_type] = []
                    task_type_results[task_type].extend(results_list)
            
            for task_type, task_results in sorted(task_type_results.items()):
                f.write(f"### {task_type}\n\n")
                
                # Basic Performance table
                f.write("#### Basic Performance\n\n")
                f.write("| Metric | Baseline | Optimal | CoT |\n")
                f.write("|--------|----------|---------|-----|\n")
                
                # 计算各类结果
                baseline_results = [r for r in task_results if hasattr(r, 'prompt_type') and r.prompt_type == "baseline"]
                optimal_results = [r for r in task_results if hasattr(r, 'prompt_type') and r.prompt_type == "optimal"]
                cot_results = [r for r in task_results if hasattr(r, 'prompt_type') and r.prompt_type == "cot"]
                
                # Success Rate row - 添加分级统计
                baseline_full = sum(1 for r in baseline_results if getattr(r, 'success_level', '') == "full_success")
                baseline_partial = sum(1 for r in baseline_results if getattr(r, 'success_level', '') == "partial_success")
                baseline_total = baseline_full + baseline_partial
                baseline_sr = baseline_total / len(baseline_results) if baseline_results else 0
                
                optimal_full = sum(1 for r in optimal_results if getattr(r, 'success_level', '') == "full_success")
                optimal_partial = sum(1 for r in optimal_results if getattr(r, 'success_level', '') == "partial_success")
                optimal_total = optimal_full + optimal_partial
                optimal_sr = optimal_total / len(optimal_results) if optimal_results else 0
                
                cot_full = sum(1 for r in cot_results if getattr(r, 'success_level', '') == "full_success")
                cot_partial = sum(1 for r in cot_results if getattr(r, 'success_level', '') == "partial_success")
                cot_total = cot_full + cot_partial
                cot_sr = cot_total / len(cot_results) if cot_results else 0
                
                f.write(f"| Success Rate | {baseline_sr:.2%} | {optimal_sr:.2%} | {cot_sr:.2%} |\n")
                
                # Full Success row
                baseline_full_rate = baseline_full / len(baseline_results) if baseline_results else 0
                optimal_full_rate = optimal_full / len(optimal_results) if optimal_results else 0
                cot_full_rate = cot_full / len(cot_results) if cot_results else 0
                f.write(f"| Full Success | {baseline_full_rate:.2%} | {optimal_full_rate:.2%} | {cot_full_rate:.2%} |\n")
                
                # Partial Success row
                baseline_partial_rate = baseline_partial / len(baseline_results) if baseline_results else 0
                optimal_partial_rate = optimal_partial / len(optimal_results) if optimal_results else 0
                cot_partial_rate = cot_partial / len(cot_results) if cot_results else 0
                f.write(f"| Partial Success | {baseline_partial_rate:.2%} | {optimal_partial_rate:.2%} | {cot_partial_rate:.2%} |\n")
                
                # Avg Score row
                baseline_avg = np.mean([getattr(r, 'final_score', 0) for r in baseline_results]) if baseline_results else 0
                optimal_avg = np.mean([getattr(r, 'final_score', 0) for r in optimal_results]) if optimal_results else 0
                cot_avg = np.mean([getattr(r, 'final_score', 0) for r in cot_results]) if cot_results else 0
                f.write(f"| Avg Score | {baseline_avg:.3f} | {optimal_avg:.3f} | {cot_avg:.3f} |\n")
                
                # Test Count row
                f.write(f"| Test Count | {len(baseline_results)} | {len(optimal_results)} | {len(cot_results)} |\n")
                
                # Flawed Workflow Performance (if applicable)
                task_flawed = [r for r in task_results if hasattr(r, 'prompt_type') and r.prompt_type == 'flawed']
                if task_flawed:
                    f.write("\n#### Flawed Workflow Performance\n\n")
                    f.write("| Severity | Total Success Rate | Full Success | Partial Success | Avg Score | Count |\n")
                    f.write("|----------|-------------------|--------------|-----------------|-----------|-------|\n")
                    
                    flawed_severities = ['light', 'medium', 'severe']
                    for severity in flawed_severities:
                        severity_results = [r for r in task_flawed 
                                        if (hasattr(r, 'flaw_severity') and r.flaw_severity == severity) or
                                            (hasattr(r, 'test_id') and f'_{severity}' in getattr(r, 'test_id', ''))]
                        if severity_results:
                            # 统计分级成功率
                            full_success = sum(1 for r in severity_results if getattr(r, 'success_level', '') == 'full_success')
                            partial_success = sum(1 for r in severity_results if getattr(r, 'success_level', '') == 'partial_success')
                            total_success = full_success + partial_success
                            
                            total_tests = len(severity_results)
                            total_sr = total_success / total_tests if total_tests > 0 else 0
                            full_sr = full_success / total_tests if total_tests > 0 else 0
                            partial_sr = partial_success / total_tests if total_tests > 0 else 0
                            avg = np.mean([getattr(r, 'final_score', 0) for r in severity_results])
                            
                            logger.debug(f" Task {task_type} - {severity}: full={full_success}, partial={partial_success}, total={total_success}")
                            
                            f.write(f"| {severity.capitalize()} | {total_sr:.2%} | {full_sr:.2%} | {partial_sr:.2%} | {avg:.3f} | {total_tests} |\n")

                
                f.write("\n")
            
            # 3. Flawed Workflow Detailed Analysis (增强版)
            if any(hasattr(r, 'prompt_type') and r.prompt_type == 'flawed' for r in all_results_flat):
                f.write("## Flawed Workflow Detailed Analysis\n\n")
                
                # Performance by Flaw Type
                f.write("### Performance by Flaw Type\n\n")
                f.write("| Flaw Type | Total | Success Rate | Avg Score | Light SR | Medium SR | Severe SR |\n")
                f.write("|-----------|--------|--------------|-----------|----------|-----------|------------|\n")
                
                # 收集所有缺陷类型
                flaw_types = set()
                for key in all_results_dict.keys():
                    if '_flawed_' in key:
                        parts = key.split('_flawed_')
                        if len(parts) > 1:
                            flaw_parts = parts[1].split('_')
                            if len(flaw_parts) > 1:
                                flaw_type = '_'.join(flaw_parts[:-1])
                                flaw_types.add(flaw_type)
                
                for flaw_type in sorted(flaw_types):
                    flaw_results = []
                    severity_results = {'light': [], 'medium': [], 'severe': []}
                    
                    for key, results_list in all_results_dict.items():
                        if f'_flawed_{flaw_type}_' in key:
                            flaw_results.extend(results_list)
                            severity = key.split('_')[-1]
                            if severity in severity_results:
                                severity_results[severity].extend(results_list)
                    
                    if flaw_results:
                        total_tests = len(flaw_results)
                        success_rate = sum(1 for r in flaw_results if getattr(r, 'success', False)) / total_tests
                        avg_score = np.mean([getattr(r, 'final_score', 0) for r in flaw_results])
                        
                        # Calculate severity-specific success rates
                        light_sr = sum(1 for r in severity_results['light'] if getattr(r, 'success', False)) / len(severity_results['light']) * 100 if severity_results['light'] else 0
                        medium_sr = sum(1 for r in severity_results['medium'] if getattr(r, 'success', False)) / len(severity_results['medium']) * 100 if severity_results['medium'] else 0
                        severe_sr = sum(1 for r in severity_results['severe'] if getattr(r, 'success', False)) / len(severity_results['severe']) * 100 if severity_results['severe'] else 0
                        
                        flaw_type_display = flaw_type.replace('_', ' ').title()
                        f.write(f"| {flaw_type_display} | {total_tests} | {success_rate:.2%} | {avg_score:.3f} | "
                                f"{light_sr:.0f}% | {medium_sr:.0f}% | {severe_sr:.0f}% |\n")
                
                # Severity Impact Analysis
                f.write("\n### Severity Impact Analysis\n\n")
                f.write("#### Success Rate Trends by Severity\n\n")
                f.write("\n")
                
                # Recommendations
                f.write("#### Recommendations\n\n")
                
                # 分析哪些缺陷类型对严重程度最敏感
                sensitivity_scores = []
                for flaw_type in flaw_types:
                    severity_success_rates = []
                    for severity in ['light', 'medium', 'severe']:
                        key_pattern = f'_flawed_{flaw_type}_{severity}'
                        severity_flaw_results = []
                        for key, results_list in all_results_dict.items():
                            if key_pattern in key:
                                severity_flaw_results.extend(results_list)
                        
                        if severity_flaw_results:
                            sr = sum(1 for r in severity_flaw_results if getattr(r, 'success', False)) / len(severity_flaw_results)
                            severity_success_rates.append(sr)
                    
                    if len(severity_success_rates) >= 2:
                        sensitivity = max(severity_success_rates) - min(severity_success_rates)
                        sensitivity_scores.append((flaw_type, sensitivity))
                
                # 输出最敏感的缺陷类型
                sensitivity_scores.sort(key=lambda x: x[1], reverse=True)
                for flaw_type, sensitivity in sensitivity_scores[:4]:
                    if sensitivity > 0.1:
                        f.write(f"- {flaw_type.replace('_', ' ').title()} is highly sensitive to severity (impact: {sensitivity:.2f})\n")
            
            # 4. Phase 2 Scoring Details (if applicable)
            has_phase2 = [r for r in all_results_flat if hasattr(r, 'phase2_score')]
            if has_phase2:
                f.write("\n## Phase 2 Scoring Analysis\n\n")
                f.write("### Score Distribution\n\n")
                f.write("| Metric | Mean | Std Dev | Min | Max |\n")
                f.write("|--------|------|---------|-----|-----|\n")
                
                phase2_scores = [getattr(r, 'phase2_score', 0) for r in has_phase2]
                quality_scores = [getattr(r, 'quality_score', 0) for r in has_phase2 if hasattr(r, 'quality_score')]
                workflow_scores = [getattr(r, 'workflow_score', 0) for r in has_phase2 if hasattr(r, 'workflow_score')]
                
                if phase2_scores:
                    f.write(f"| Phase2 Score | {np.mean(phase2_scores):.3f} | "
                            f"{np.std(phase2_scores):.3f} | {min(phase2_scores):.3f} | {max(phase2_scores):.3f} |\n")
                
                if quality_scores:
                    f.write(f"| Quality Score | {np.mean(quality_scores):.3f} | "
                            f"{np.std(quality_scores):.3f} | {min(quality_scores):.3f} | {max(quality_scores):.3f} |\n")
                
                if workflow_scores:
                    f.write(f"| Workflow Score | {np.mean(workflow_scores):.3f} | "
                            f"{np.std(workflow_scores):.3f} | {min(workflow_scores):.3f} | {max(workflow_scores):.3f} |\n")
            
            # Footer
            f.write("\n---\n")
            f.write(f"*Report generated at {results.get('timestamp', datetime.now().isoformat())}*\n")
        
        logger.info(f"Workflow quality report generated: {report_path}")
        return report_path


    def generate_training_report(self, metrics: Dict[str, Any], output_filename: str = "training_report.md") -> Path:
        """Generate training progress report
        
        Args:
            metrics: Training metrics dictionary
            output_filename: Name of the output file
            
        Returns:
            Path to the generated report
        """
        report_path = self.output_dir / output_filename
        
        with open(report_path, 'w') as f:
            f.write("# Training Progress Report\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            
            # Training configuration
            if 'config' in metrics:
                f.write("## Training Configuration\n\n")
                for key, value in metrics['config'].items():
                    f.write(f"- **{key}**: {value}\n")
                f.write("\n")
            
            # Performance metrics
            if 'performance' in metrics:
                f.write("## Performance Metrics\n\n")
                perf = metrics['performance']
                f.write(f"- **Episodes Completed**: {perf.get('episodes', 0)}\n")
                f.write(f"- **Success Rate**: {perf.get('success_rate', 0):.2%}\n")
                f.write(f"- **Average Reward**: {perf.get('avg_reward', 0):.3f}\n")
                f.write(f"- **Best Reward**: {perf.get('best_reward', 0):.3f}\n")
                f.write("\n")
            
            # Task-specific performance
            if 'task_performance' in metrics:
                f.write("## Task-Specific Performance\n\n")
                f.write("| Task Type | Episodes | Success Rate | Avg Reward |\n")
                f.write("|-----------|----------|--------------|------------|\n")
                
                for task_type, task_metrics in metrics['task_performance'].items():
                    f.write(f"| {task_type} | {task_metrics.get('episodes', 0)} | "
                          f"{task_metrics.get('success_rate', 0):.2%} | "
                          f"{task_metrics.get('avg_reward', 0):.3f} |\n")
                f.write("\n")
            
            # Resource usage
            if 'resource_usage' in metrics:
                f.write("## Resource Usage\n\n")
                usage = metrics['resource_usage']
                f.write(f"- **Training Time**: {usage.get('time_hours', 0):.2f} hours\n")
                f.write(f"- **Peak Memory**: {usage.get('peak_memory_gb', 0):.2f} GB\n")
                f.write(f"- **GPU Utilization**: {usage.get('gpu_utilization', 0):.1%}\n")
                f.write("\n")
        
        logger.info(f"Training report generated: {report_path}")
        return report_path
    
    def generate_summary_json(self, data: Dict[str, Any], output_filename: str = "summary.json") -> Path:
        """Generate JSON summary of any data
        
        Args:
            data: Data to summarize
            output_filename: Name of the output file
            
        Returns:
            Path to the generated summary
        """
        summary_path = self.output_dir / output_filename
        
        # Add metadata
        data['_metadata'] = {
            'generated_at': datetime.now().isoformat(),
            'generator': 'MDPWorkflowSystem.ReportGenerator'
        }
        
        with open(summary_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"JSON summary generated: {summary_path}")
        return summary_path


# Additional utility functions
def calculate_statistics(values: List[float]) -> Dict[str, float]:
    """Calculate basic statistics for a list of values
    
    Args:
        values: List of numeric values
        
    Returns:
        Dictionary with mean, std, min, max, median
    """
    if not values:
        return {
            'mean': 0.0,
            'std': 0.0,
            'min': 0.0,
            'max': 0.0,
            'median': 0.0,
            'count': 0
        }
    
    return {
        'mean': float(np.mean(values)),
        'std': float(np.std(values)),
        'min': float(np.min(values)),
        'max': float(np.max(values)),
        'median': float(np.median(values)),
        'count': len(values)
    }


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string (e.g., "2h 15m 30s")
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    
    return " ".join(parts)


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers, returning default if denominator is zero
    
    Args:
        numerator: The numerator
        denominator: The denominator
        default: Default value if division by zero
        
    Returns:
        Result of division or default value
    """
    if denominator == 0:
        return default
    return numerator / denominator


# Export main classes and functions
__all__ = [
    'ReportGenerator',
    'calculate_statistics',
    'format_duration',
    'safe_divide'
]