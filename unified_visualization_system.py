#!/usr/bin/env python3
"""
统一的Flawed Workflow测试结果可视化系统
=========================================
重新设计，确保数据展示的一致性和可理解性
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import logging
from typing import Dict, List, Any, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UnifiedFlawedVisualizer:
    """统一的可视化器 - 确保所有图表使用相同的数据处理逻辑"""
    
    def __init__(self, data_path: str = None):
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
        
        # 全局配置
        self.SCORE_WEIGHTS = {'success': 0.7, 'accuracy': 0.3}
        self.COLORS = {
            'baseline': '#FF6B6B',
            'optimal': '#4ECDC4', 
            'flawed': '#45B7D1',
            'light': '#FFE66D',
            'medium': '#FFA500',
            'severe': '#FF4444'
        }
        
        # 加载数据
        self.raw_data = self._load_all_data(data_path)
        self.processed_data = self._process_data()
        
    def _load_all_data(self, data_path: str = None) -> Dict:
        """加载所有测试数据"""
        if data_path and Path(data_path).exists():
            with open(data_path, 'r') as f:
                return json.load(f)
        
        # 否则尝试从多个来源加载
        all_data = {}
        patterns = [
            "output/flawed_test_*_*_*.json",
            "output/flawed_test_combined_results.json"
        ]
        
        for pattern in patterns:
            for file in Path(".").glob(pattern):
                try:
                    with open(file, 'r') as f:
                        data = json.load(f)
                        # 根据文件类型处理数据
                        if 'combined' in str(file):
                            all_data.update(self._parse_combined_data(data))
                        else:
                            all_data.update(self._parse_single_file(data))
                except Exception as e:
                    logger.warning(f"Failed to load {file}: {e}")
        
        return all_data
    
    def _parse_combined_data(self, data: Dict) -> Dict:
        """解析combined格式的数据"""
        result = {}
        for task_type, severity_data in data.items():
            for severity, test_data in severity_data.items():
                if 'flaw_test_results' in test_data:
                    for flaw_name, flaw_data in test_data['flaw_test_results'].items():
                        key = f"{task_type}_{severity}_{flaw_name}"
                        result[key] = flaw_data
        return result
    
    def _parse_single_file(self, data: Dict) -> Dict:
        """解析单个文件的数据"""
        result = {}
        task_type = data.get('task_type', 'unknown')
        severity = data.get('severity', 'unknown')
        
        if 'flaw_test_results' in data:
            for flaw_name, flaw_data in data['flaw_test_results'].items():
                key = f"{task_type}_{severity}_{flaw_name}"
                result[key] = flaw_data
        
        return result
    
    # 文件：unified_visualization_system.py
    # 位置：第90-150行
    # 函数：_process_data

    def _process_data(self) -> Dict:
        """处理原始数据 - 直接使用测试代码的输出，不重新计算"""
        processed = {
            'by_prompt': defaultdict(list),  # 按prompt类型分组
            'by_severity': defaultdict(lambda: defaultdict(list)),  # 按severity和prompt分组
            'by_flaw_type': defaultdict(lambda: defaultdict(list)),  # 按flaw类型和prompt分组
            'summary': {
                'total_tests': 0,
                'severities': set(),
                'flaw_types': set(),
                'task_types': set()
            }
        }
        
        for key, flaw_data in self.raw_data.items():
            # 提取元信息
            parts = key.split('_')
            task_type = parts[0] if len(parts) > 0 else 'unknown'
            severity = parts[1] if len(parts) > 1 else 'unknown'
            flaw_name = '_'.join(parts[2:]) if len(parts) > 2 else 'unknown'
            
            # 从flaw_info获取更准确的信息
            flaw_info = flaw_data.get('flaw_info', {})
            severity = flaw_info.get('severity', severity)
            flaw_type = flaw_info.get('type', flaw_name.split('_')[0] if flaw_name != 'unknown' else 'unknown')
            
            # 更新summary
            processed['summary']['severities'].add(severity)
            processed['summary']['flaw_types'].add(flaw_type)
            processed['summary']['task_types'].add(task_type)
            
            # === 修改开始：直接使用测试结果，不重新计算 ===
            perf = flaw_data.get('performance_comparison', {})
            
            for prompt_type in ['baseline_prompt', 'optimal_prompt', 'flawed_optimal_prompt']:
                if prompt_type in perf:
                    # 直接使用测试代码计算的所有指标
                    metrics = perf[prompt_type]
                    
                    data_point = {
                        # 使用原始数据，不重新计算
                        'success_rate': metrics.get('success_rate', 0),
                        'tool_accuracy': metrics.get('tool_accuracy', 0),
                        'avg_execution_time': metrics.get('avg_execution_time', 0),
                        'error_rate': metrics.get('error_rate', 0),
                        'total_tests': metrics.get('total_tests', 0),
                        # 元数据
                        'severity': severity,
                        'flaw_type': flaw_type,
                        'task_type': task_type,
                        'flaw_name': flaw_name,
                        'key': key,
                        # 如果测试代码提供了composite_score，使用它；否则不计算
                        'composite_score': metrics.get('composite_score', metrics.get('success_rate', 0))
                    }
                    
                    # 存储到不同的分组
                    processed['by_prompt'][prompt_type].append(data_point)
                    processed['by_severity'][severity][prompt_type].append(data_point)
                    processed['by_flaw_type'][flaw_type][prompt_type].append(data_point)
                    
                    processed['summary']['total_tests'] += data_point['total_tests']
            # === 修改结束 ===
        
        return processed
    
    # 文件：unified_visualization_system.py
    # 位置：在类中添加新方法，约第180行后

    def validate_data_consistency(self):
        """验证数据一致性，确保与测试代码输出匹配"""
        logger.info("Validating data consistency...")
        
        # 检查是否所有数据点都有必要的字段
        required_fields = ['success_rate', 'total_tests']
        missing_data = []
        
        for prompt_type, data_points in self.processed_data['by_prompt'].items():
            for dp in data_points:
                for field in required_fields:
                    if field not in dp or dp[field] is None:
                        missing_data.append({
                            'prompt_type': prompt_type,
                            'key': dp.get('key', 'unknown'),
                            'missing_field': field
                        })
        
        if missing_data:
            logger.warning(f"Found {len(missing_data)} data points with missing fields")
            for item in missing_data[:5]:  # 只显示前5个
                logger.warning(f"  {item}")
        
        # 检查数Value范围
        for prompt_type, data_points in self.processed_data['by_prompt'].items():
            for dp in data_points:
                sr = dp.get('success_rate', 0)
                if not 0 <= sr <= 1:
                    logger.warning(f"Invalid success_rate {sr} for {dp.get('key')}")
        
        return len(missing_data) == 0
    # 文件：unified_visualization_system.py
    # 位置：第160-180行
    # 函数：_calculate_stats

    def _calculate_stats(self, data_points: List[Dict], metric: str = 'success_rate') -> Dict:
        """计算统计信息 - 基于测试代码的原始数据"""
        if not data_points:
            return {
                'mean': 0, 
                'std': 0, 
                'count': 0, 
                'total_tests': 0,
                'raw_values': []  # 保存原始Value供调试
            }
        
        # === 修改开始：保留原始数据的精确性 ===
        values = [d[metric] for d in data_points]
        total_tests = sum(d.get('total_tests', 0) for d in data_points)
        
        return {
            'mean': np.mean(values) if values else 0,
            'std': np.std(values) if values else 0,
            'count': len(values),
            'total_tests': total_tests,
            'values': values,
            'raw_values': values,  # 保存原始Value
            'min': min(values) if values else 0,
            'max': max(values) if values else 0,
            'median': np.median(values) if values else 0
        }
        # === 修改结束 ===
    
    def visualize_unified_comparison(self):
        """创建统一的对比图 - 展示真实的数据分布"""
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        # 1. 整体性能对比（左上）
        ax1 = axes[0, 0]
        self._plot_overall_performance(ax1)
        
        # 2. 按Severity分组对比（右上）
        ax2 = axes[0, 1]
        self._plot_by_severity(ax2)
        
        # 3. 数据分布箱线图（左下）
        ax3 = axes[1, 0]
        self._plot_distribution_boxplot(ax3)
        
        # 4. 样本数量统计（右下）
        ax4 = axes[1, 1]
        self._plot_sample_counts(ax4)
        
        plt.suptitle('Unified Flawed Workflow Test Analysis', fontsize=16, y=0.98)
        plt.tight_layout()
        plt.savefig(self.output_dir / 'unified_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()
        logger.info("Generated: unified_analysis.png")
    
    def _plot_overall_performance(self, ax):
        """绘制整体性能对比"""
        # 计算每个prompt type的整体统计
        prompt_types = ['baseline_prompt', 'optimal_prompt', 'flawed_optimal_prompt']
        labels = ['Baseline\n(No MDP)', 'Optimal\n(With MDP)', 'Flawed\n(All Severities)']
        
        means = []
        stds = []
        counts = []
        
        for prompt_type in prompt_types:
            stats = self._calculate_stats(self.processed_data['by_prompt'][prompt_type])
            means.append(stats['mean'])
            stds.append(stats['std'])
            counts.append(stats['total_tests'])
        
        x = np.arange(len(labels))
        colors = [self.COLORS['baseline'], self.COLORS['optimal'], self.COLORS['flawed']]
        
        bars = ax.bar(x, means, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
        ax.errorbar(x, means, yerr=stds, fmt='none', color='black', capsize=5, linewidth=2)
        
        # 添加数Value标签
        for i, (bar, mean, count) in enumerate(zip(bars, means, counts)):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                   f'{mean:.1%}\n(n={count})', ha='center', va='bottom')
        
        ax.set_ylabel('Success Rate', fontsize=12)
        ax.set_title('Overall Performance Comparison\n(All Data Combined)', fontsize=14)
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.set_ylim(0, max(means) * 1.3 if means else 1.0)
        ax.grid(axis='y', alpha=0.3)
    
    # 相同位置的修复代码
    def _plot_by_severity(self, ax):
        """显示5个独立的策略：baseline, optimal, flawed(light/medium/severe)"""
        # 准备5个独立的条形数据
        strategies = []
        means = []
        stds = []
        counts = []
        colors = []
        
        # 1. Baseline (所有severity合并)
        baseline_stats = self._calculate_stats(self.processed_data['by_prompt']['baseline_prompt'])
        strategies.append('Baseline\n(No MDP)')
        means.append(baseline_stats['mean'])
        stds.append(baseline_stats['std'])
        counts.append(baseline_stats['total_tests'])
        colors.append(self.COLORS['baseline'])
        
        # 2. Optimal (所有severity合并)
        optimal_stats = self._calculate_stats(self.processed_data['by_prompt']['optimal_prompt'])
        strategies.append('Optimal\n(With MDP)')
        means.append(optimal_stats['mean'])
        stds.append(optimal_stats['std'])
        counts.append(optimal_stats['total_tests'])
        colors.append(self.COLORS['optimal'])
        
        # 3-5. Flawed按severity分开
        for severity in ['light', 'medium', 'severe']:
            flawed_stats = self._calculate_stats(
                self.processed_data['by_severity'][severity]['flawed_optimal_prompt'])
            strategies.append(f'Flawed\n{severity.capitalize()}')
            means.append(flawed_stats['mean'])
            stds.append(flawed_stats['std'])
            counts.append(flawed_stats['total_tests'])
            colors.append(self.COLORS[severity])
        
        # 绘制条形图
        x = np.arange(len(strategies))
        bars = ax.bar(x, means, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
        ax.errorbar(x, means, yerr=stds, fmt='none', color='black', capsize=5, linewidth=2)
        
        # 添加数Value标签
        for i, (bar, mean, count) in enumerate(zip(bars, means, counts)):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                f'{mean:.1%}\n(n={count})', ha='center', va='bottom', fontsize=9)
        
        ax.set_xlabel('Strategy', fontsize=12)
        ax.set_ylabel('Success Rate', fontsize=12)
        ax.set_title('Performance by Strategy\n(Unified View)', fontsize=14)
        ax.set_xticks(x)
        ax.set_xticklabels(strategies)
        ax.set_ylim(0, max(means) * 1.3 if means else 1.0)
        ax.grid(axis='y', alpha=0.3)
    
    def _plot_distribution_boxplot(self, ax):
        """绘制数据分布箱线图"""
        # 准备数据
        data_for_plot = []
        labels = []
        colors = []
        
        # Baseline和Optimal（所有severity合并）
        for prompt_type, label, color in [
            ('baseline_prompt', 'Baseline', self.COLORS['baseline']),
            ('optimal_prompt', 'Optimal', self.COLORS['optimal'])
        ]:
            values = [d['success_rate'] for d in self.processed_data['by_prompt'][prompt_type]]
            if values:
                data_for_plot.append(values)
                labels.append(label)
                colors.append(color)
        
        # Flawed按severity分组
        for severity in ['light', 'medium', 'severe']:
            values = [d['success_rate'] for d in 
                     self.processed_data['by_severity'][severity]['flawed_optimal_prompt']]
            if values:
                data_for_plot.append(values)
                labels.append(f'Flawed\n{severity.capitalize()}')
                colors.append(self.COLORS[severity])
        
        # 绘制箱线图
        bp = ax.boxplot(data_for_plot, labels=labels, patch_artist=True, notch=True)
        
        # 设置颜色
        for patch, color in zip(bp['boxes'], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        
        # 添加数据点数量
        for i, data in enumerate(data_for_plot):
            ax.text(i + 1, -0.08, f'n={len(data)}', ha='center', 
                   transform=ax.get_xaxis_transform(), fontsize=9)
        
        ax.set_ylabel('Success Rate Distribution', fontsize=12)
        ax.set_title('Success Rate Distribution\n(Showing Data Spread)', fontsize=14)
        ax.set_ylim(-0.1, 1.1)
        ax.grid(axis='y', alpha=0.3)
    
    def _plot_sample_counts(self, ax):
        """绘制样本数量统计"""
        # 创建表格数据
        severities = ['light', 'medium', 'severe']
        prompt_types = ['baseline_prompt', 'optimal_prompt', 'flawed_optimal_prompt']
        
        # 收集数据
        table_data = []
        for severity in severities:
            row = [severity.capitalize()]
            for prompt_type in prompt_types:
                stats = self._calculate_stats(
                    self.processed_data['by_severity'][severity][prompt_type])
                row.append(f"{stats['count']} flaws\n{stats['total_tests']} tests")
            table_data.append(row)
        
        # 添加总计行
        total_row = ['Total']
        for prompt_type in prompt_types:
            stats = self._calculate_stats(self.processed_data['by_prompt'][prompt_type])
            total_row.append(f"{stats['count']} flaws\n{stats['total_tests']} tests")
        table_data.append(total_row)
        
        # 创建表格
        col_labels = ['Severity', 'Baseline', 'Optimal', 'Flawed']
        
        # 隐藏坐标轴
        ax.axis('tight')
        ax.axis('off')
        
        # 创建表格
        table = ax.table(cellText=table_data, colLabels=col_labels,
                        cellLoc='center', loc='center',
                        colWidths=[0.2, 0.25, 0.25, 0.25])
        
        # 设置样式
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 2)
        
        # 设置标题
        ax.set_title('Sample Size Summary\n(Flaw Types and Test Counts)', 
                    fontsize=14, pad=20)
    
    def visualize_detailed_severity_analysis(self):
        """创建详细的severity分析图"""
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        
        severities = ['light', 'medium', 'severe']
        
        for i, severity in enumerate(severities):
            ax = axes[i]
            self._plot_severity_detail(ax, severity)
        
        plt.suptitle('Detailed Analysis by Severity Level', fontsize=16)
        plt.tight_layout()
        plt.savefig(self.output_dir / 'severity_detailed_analysis.png', 
                   dpi=300, bbox_inches='tight')
        plt.close()
        logger.info("Generated: severity_detailed_analysis.png")
    
    def _plot_severity_detail(self, ax, severity):
        """绘制单个severity的详细分析"""
        prompt_types = ['baseline_prompt', 'optimal_prompt', 'flawed_optimal_prompt']
        labels = ['Baseline', 'Optimal', 'Flawed']
        colors = [self.COLORS['baseline'], self.COLORS['optimal'], self.COLORS['flawed']]
        
        # 收集该severity下的所有数据
        data_by_prompt = []
        for prompt_type in prompt_types:
            values = [d['success_rate'] for d in 
                     self.processed_data['by_severity'][severity][prompt_type]]
            data_by_prompt.append(values)
        
        # 创建小提琴图
        positions = np.arange(len(prompt_types))
        
        # 绘制小提琴图
        parts = ax.violinplot(data_by_prompt, positions=positions, 
                             showmeans=True, showmedians=True)
        
        # 设置颜色
        for pc, color in zip(parts['bodies'], colors):
            pc.set_facecolor(color)
            pc.set_alpha(0.7)
        
        # 添加散点图显示实际数据点
        for i, (data, color) in enumerate(zip(data_by_prompt, colors)):
            if data:
                y = data
                x = np.random.normal(i, 0.04, size=len(y))
                ax.scatter(x, y, alpha=0.4, s=30, color=color)
        
        # 添加统计信息
        stats_text = []
        for i, (prompt_type, data) in enumerate(zip(prompt_types, data_by_prompt)):
            if data:
                mean = np.mean(data)
                std = np.std(data)
                stats_text.append(f"{labels[i]}: {mean:.1%}±{std:.1%} (n={len(data)})")
        
        ax.text(0.02, 0.98, '\n'.join(stats_text), 
               transform=ax.transAxes, va='top', fontsize=10,
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        ax.set_xticks(positions)
        ax.set_xticklabels(labels)
        ax.set_ylabel('Success Rate')
        ax.set_title(f'{severity.capitalize()} Severity', fontsize=14)
        ax.set_ylim(-0.05, 1.05)
        ax.grid(axis='y', alpha=0.3)
    
    # 文件：unified_visualization_system.py  
    # 位置：修改generate_comprehensive_report方法，约第400行

    def generate_comprehensive_report(self):
        """生成综合报告 - 包含数据来源信息"""
        report_path = self.output_dir / 'comprehensive_flawed_analysis_report.md'
        
        with open(report_path, 'w') as f:
            f.write("# Comprehensive Flawed Workflow Analysis Report\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # === 新增：数据来源说明 ===
            f.write("## Data Source\n\n")
            f.write("This report is based on the raw output from workflow_quality_test.py\n")
            f.write("All success rates and metrics are directly from the test execution results.\n\n")
            
            # 数据验证Status
            f.write("### Data Validation\n\n")
            if self.validate_data_consistency():
                f.write("✅ All data points have required fields\n\n")
            else:
                f.write("⚠️ Some data points have missing fields\n\n")
            
            # 数据概览
            f.write("## Dataset Overview\n\n")
            summary = self.processed_data['summary']
            f.write(f"- Total tests conducted: {summary['total_tests']}\n")
            f.write(f"- Severities tested: {', '.join(sorted(summary['severities']))}\n")
            f.write(f"- Flaw types: {len(summary['flaw_types'])}\n")
            f.write(f"- Task types: {', '.join(sorted(summary['task_types']))}\n\n")
            
            # === 新增：显示评分标准来源 ===
            f.write("## Scoring Standards\n\n")
            f.write("**Note**: All scores shown are from the test execution, not recalculated.\n")
            f.write("The test code uses the following evaluation:\n")
            f.write("- Task requirements from generated task instances\n")
            f.write("- Tool dependencies from tool_task_generator\n")
            f.write("- Objective scoring based on tool coverage and dependency satisfaction\n\n")
            
            # Key Finding（继续使用原有逻辑，但明确说明数据来源）
            # ... 其余代码保持不变
            
            # 评分标准
            f.write("## Scoring Standards\n\n")
            f.write(f"**Composite Score** = {self.SCORE_WEIGHTS['success']}×Success Rate + ")
            f.write(f"{self.SCORE_WEIGHTS['accuracy']}×Tool Accuracy\n\n")
            
            # Key Finding
            f.write("## Key Findings\n\n")
            
            # 整体性能
            f.write("### Overall Performance\n\n")
            f.write("| Prompt Type | Mean Success Rate | Std Dev | Total Tests |\n")
            f.write("|-------------|-------------------|---------|-------------|\n")
            
            for prompt_type, label in [
                ('baseline_prompt', 'Baseline (No MDP)'),
                ('optimal_prompt', 'Optimal (With MDP)'),
                ('flawed_optimal_prompt', 'Flawed (All)')
            ]:
                stats = self._calculate_stats(self.processed_data['by_prompt'][prompt_type])
                f.write(f"| {label} | {stats['mean']:.1%} | {stats['std']:.1%} | ")
                f.write(f"{stats['total_tests']} |\n")
            
            # 按Severity分析
            f.write("\n### Performance by Severity\n\n")
            
            for severity in ['light', 'medium', 'severe']:
                f.write(f"\n**{severity.capitalize()} Severity:**\n\n")
                f.write("| Prompt Type | Mean Success Rate | Sample Size |\n")
                f.write("|-------------|-------------------|-------------|\n")
                
                for prompt_type, label in [
                    ('baseline_prompt', 'Baseline'),
                    ('optimal_prompt', 'Optimal'),
                    ('flawed_optimal_prompt', 'Flawed')
                ]:
                    stats = self._calculate_stats(
                        self.processed_data['by_severity'][severity][prompt_type])
                    f.write(f"| {label} | {stats['mean']:.1%} | {stats['count']} |\n")
            
            # 数据质量检查
            f.write("\n## Data Quality Check\n\n")
            
            # 检查数据平衡性
            f.write("### Data Balance\n\n")
            severity_counts = defaultdict(int)
            for severity in ['light', 'medium', 'severe']:
                for prompt_type in ['baseline_prompt', 'optimal_prompt', 'flawed_optimal_prompt']:
                    count = len(self.processed_data['by_severity'][severity][prompt_type])
                    severity_counts[severity] += count
            
            imbalance_ratio = max(severity_counts.values()) / min(severity_counts.values()) \
                             if min(severity_counts.values()) > 0 else float('inf')
            
            if imbalance_ratio > 2:
                f.write("⚠️ **Warning**: Significant data imbalance detected between severities.\n")
                f.write(f"Imbalance ratio: {imbalance_ratio:.1f}\n\n")
            else:
                f.write("✅ Data is reasonably balanced across severities.\n\n")
            
            # 建议
            f.write("## Recommendations\n\n")
            
            # 基于数据的建议
            baseline_stats = self._calculate_stats(self.processed_data['by_prompt']['baseline_prompt'])
            optimal_stats = self._calculate_stats(self.processed_data['by_prompt']['optimal_prompt'])
            
            improvement = (optimal_stats['mean'] - baseline_stats['mean']) / baseline_stats['mean'] \
                         if baseline_stats['mean'] > 0 else float('inf')
            
            if improvement > 0:
                f.write(f"1. MDP guidance shows {improvement:.0%} improvement over baseline.\n")
            
            # 检查flawed性能
            for severity in ['light', 'medium', 'severe']:
                flawed_stats = self._calculate_stats(
                    self.processed_data['by_severity'][severity]['flawed_optimal_prompt'])
                if flawed_stats['mean'] > optimal_stats['mean']:
                    f.write(f"2. Flawed workflows with {severity} severity ")
                    f.write(f"outperform optimal ({flawed_stats['mean']:.1%} vs {optimal_stats['mean']:.1%}), ")
                    f.write("suggesting the model may be overfitting to specific patterns.\n")
                    break
        
        logger.info("Generated: comprehensive_flawed_analysis_report.md")
    # 文件：unified_visualization_system.py
    # 位置：添加新方法，用于调试数据流

    def trace_data_point(self, key: str):
        """跟踪特定数据点，用于调试"""
        logger.info(f"Tracing data point: {key}")
        
        # 在原始数据中查找
        if key in self.raw_data:
            raw = self.raw_data[key]
            logger.info("Raw data found:")
            logger.info(f"  Flaw info: {raw.get('flaw_info')}")
            perf = raw.get('performance_comparison', {})
            for prompt_type, metrics in perf.items():
                logger.info(f"  {prompt_type}:")
                logger.info(f"    - success_rate: {metrics.get('success_rate')}")
                logger.info(f"    - total_tests: {metrics.get('total_tests')}")
        
        # 在处理后的数据中查找
        for prompt_type, data_points in self.processed_data['by_prompt'].items():
            for dp in data_points:
                if dp.get('key') == key:
                    logger.info(f"Processed data in {prompt_type}:")
                    logger.info(f"  - success_rate: {dp.get('success_rate')}")
                    logger.info(f"  - Used in visualization: Yes")
                    break

    # 文件：workflow_quality_test_flawed.py
    # 位置：_calculate_flaw_performance方法，约第1400行

    def _calculate_flaw_performance(self, test_results: Dict[str, List]) -> Dict:
        """计算不同prompt在flawed workflow上的性能"""
        performance = {}
        
        for prompt_type, results in test_results.items():
            if results:
                success_count = sum(1 for r in results if r.success)
                total_count = len(results)
                avg_time = sum(r.execution_time for r in results) / total_count
                
                # 计算工具调用准确率
                correct_calls = 0
                total_calls = 0
                for r in results:
                    total_calls += len(r.tool_calls)
                    # 这里可以添加更复杂的正确性判断逻辑
                    if r.success and r.tool_calls:
                        correct_calls += len(r.tool_calls)
                
                performance[prompt_type] = {
                    'success_rate': success_count / total_count if total_count > 0 else 0,
                    'avg_execution_time': avg_time,
                    'tool_accuracy': correct_calls / total_calls if total_calls > 0 else 0,
                    'error_rate': 1 - (success_count / total_count) if total_count > 0 else 1,
                    'total_tests': total_count,
                    # === 新增：保存更多细节供可视化使用 ===
                    'success_count': success_count,
                    'total_calls': total_calls,
                    'correct_calls': correct_calls,
                    'test_ids': [r.test_id for r in results],  # 用于追踪
                    'individual_scores': [getattr(r, 'task_score', 0.0) for r in results]  # 如果有的话
                }
            else:
                performance[prompt_type] = {
                    'success_rate': 0,
                    'avg_execution_time': 0,
                    'tool_accuracy': 0,
                    'error_rate': 1,
                    'total_tests': 0,
                    'success_count': 0,
                    'total_calls': 0,
                    'correct_calls': 0,
                    'test_ids': [],
                    'individual_scores': []
                }
        
        return performance

    def run_all_visualizations(self):
        """运行所有可视化"""
        logger.info("Starting unified visualization generation...")
        
        # 设置统一样式
        plt.style.use('seaborn-v0_8-whitegrid')
        plt.rcParams['figure.facecolor'] = 'white'
        plt.rcParams['axes.facecolor'] = 'white'
        
        # 生成可视化
        self.visualize_unified_comparison()
        self.visualize_detailed_severity_analysis()
        self.generate_comprehensive_report()
        
        logger.info("All visualizations completed!")
        
        # 打印数据摘要
        print("\n📊 Data Summary:")
        print(f"Total test entries: {len(self.raw_data)}")
        print(f"Total tests conducted: {self.processed_data['summary']['total_tests']}")
        print(f"Severities: {', '.join(sorted(self.processed_data['summary']['severities']))}")
        print(f"Unique flaw types: {len(self.processed_data['summary']['flaw_types'])}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate unified flawed workflow visualizations')
    parser.add_argument('--data', type=str, help='Path to data file')
    parser.add_argument('--output-dir', type=str, default='output', help='Output directory')
    
    args = parser.parse_args()
    
    try:
        visualizer = UnifiedFlawedVisualizer(data_path=args.data)
        visualizer.run_all_visualizations()
        print("\n✅ All visualizations generated successfully!")
        print(f"📁 Check the '{visualizer.output_dir}' directory for results.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()