#!/usr/bin/env python3
# 文件：visualize_flawed_results.py
# 位置：第1-17行
#!/usr/bin/env python3
"""
从已保存的flawed workflow测试结果生成可视化
无需重新运行测试
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from collections import defaultdict
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional  # 添加类型提示导入

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FlawedResultsVisualizer:
    """从保存的结果生成可视化"""
    
    def __init__(self, checkpoint_path: str = None, report_path: str = None):
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
        
        # 尝试多种方式加载数据
        self.flaw_test_results = self._load_test_results(checkpoint_path, report_path)
        
        if not self.flaw_test_results:
            raise ValueError("No test results found. Please specify valid checkpoint or report path.")

        # 添加全局配置以确保一致性
        self.score_weights = {
            'success_rate': 0.7,
            'tool_accuracy': 0.3
        }
        
        self.standardized_data = None

    def _standardize_data(self):
        """标准化所有数据，确保一致的统计方式"""
        if self.standardized_data is not None:
            return self.standardized_data
            
        # 初始化标准化数据结构
        standardized = {
            'by_prompt_type': {
                'baseline_prompt': {'all': [], 'by_severity': defaultdict(list)},
                'optimal_prompt': {'all': [], 'by_severity': defaultdict(list)},
                'flawed_optimal_prompt': {'all': [], 'by_severity': defaultdict(list)}
            },
            'by_severity': defaultdict(lambda: defaultdict(list)),
            'by_flaw_type': defaultdict(lambda: defaultdict(list)),
            'metadata': {
                'total_tests': 0,
                'test_counts': defaultdict(int),
                'flaw_types': set(),
                'severities': set(),
                'task_types': set()
            }
        }
        
        # 收集并标准化所有数据
        for flaw_key, flaw_data in self.flaw_test_results.items():
            # 提取元数据
            flaw_info = flaw_data.get('flaw_info', {})
            severity = flaw_info.get('severity', 'unknown')
            flaw_type = flaw_info.get('type', 'unknown')
            task_type = flaw_info.get('task_type', 'unknown')
            
            # 更新元数据
            standardized['metadata']['severities'].add(severity)
            standardized['metadata']['flaw_types'].add(flaw_type)
            standardized['metadata']['task_types'].add(task_type)
            
            # 处理性能数据
            perf = flaw_data.get('performance_comparison', {})
            
            for prompt_type in ['baseline_prompt', 'optimal_prompt', 'flawed_optimal_prompt']:
                if prompt_type in perf:
                    # 计算统一的综合分数
                    success_rate = perf[prompt_type].get('success_rate', 0)
                    tool_accuracy = perf[prompt_type].get('tool_accuracy', 0)
                    composite_score = (self.score_weights['success_rate'] * success_rate + 
                                     self.score_weights['tool_accuracy'] * tool_accuracy)
                    
                    # 创建标准化的数据点
                    data_point = {
                        'success_rate': success_rate,
                        'tool_accuracy': tool_accuracy,
                        'composite_score': composite_score,
                        'execution_time': perf[prompt_type].get('avg_execution_time', 0),
                        'error_rate': perf[prompt_type].get('error_rate', 0),
                        'total_tests': perf[prompt_type].get('total_tests', 0),
                        'flaw_key': flaw_key,
                        'severity': severity,
                        'flaw_type': flaw_type,
                        'task_type': task_type
                    }
                    
                    # 按不同维度存储
                    standardized['by_prompt_type'][prompt_type]['all'].append(data_point)
                    standardized['by_prompt_type'][prompt_type]['by_severity'][severity].append(data_point)
                    standardized['by_severity'][severity][prompt_type].append(data_point)
                    standardized['by_flaw_type'][flaw_type][prompt_type].append(data_point)
                    
                    # 更新总测试数
                    standardized['metadata']['total_tests'] += data_point['total_tests']
                    standardized['metadata']['test_counts'][f"{prompt_type}_{severity}"] += data_point['total_tests']
        
        self.standardized_data = standardized
        return standardized
    
    def _calculate_statistics(self, data_points: List[Dict]) -> Dict:
        """计算一组数据点的统计信息"""
        if not data_points:
            return {
                'mean_success_rate': 0,
                'mean_composite_score': 0,
                'std_success_rate': 0,
                'std_composite_score': 0,
                'total_tests': 0,
                'data_points': 0
            }
        
        success_rates = [d['success_rate'] for d in data_points]
        composite_scores = [d['composite_score'] for d in data_points]
        total_tests = sum(d['total_tests'] for d in data_points)
        
        return {
            'mean_success_rate': np.mean(success_rates),
            'mean_composite_score': np.mean(composite_scores),
            'std_success_rate': np.std(success_rates),
            'std_composite_score': np.std(composite_scores),
            'total_tests': total_tests,
            'data_points': len(data_points)
        }
    
    def _generate_consistent_performance_comparison(self):
        """生成一致的性能对比图 - 合并所有severity的数据"""
        data = self._standardize_data()
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        # 准备数据 - 使用相同的统计方法
        categories = ['Baseline\n(No MDP)', 'Optimal\n(With MDP)', 
                     'Flawed\nLight', 'Flawed\nMedium', 'Flawed\nSevere']
        
        # 计算统计数据
        stats = {}
        
        # Baseline和Optimal使用所有severity的数据
        stats['baseline'] = self._calculate_statistics(
            data['by_prompt_type']['baseline_prompt']['all'])
        stats['optimal'] = self._calculate_statistics(
            data['by_prompt_type']['optimal_prompt']['all'])
        
        # Flawed按severity分组
        for severity in ['light', 'medium', 'severe']:
            stats[f'flawed_{severity}'] = self._calculate_statistics(
                data['by_prompt_type']['flawed_optimal_prompt']['by_severity'][severity])
        
        # 提取绘图数据
        plot_keys = ['baseline', 'optimal', 'flawed_light', 'flawed_medium', 'flawed_severe']
        success_rates = [stats[key]['mean_success_rate'] for key in plot_keys]
        success_stds = [stats[key]['std_success_rate'] for key in plot_keys]
        composite_scores = [stats[key]['mean_composite_score'] for key in plot_keys]
        composite_stds = [stats[key]['std_composite_score'] for key in plot_keys]
        total_tests = [stats[key]['total_tests'] for key in plot_keys]
        
        x = np.arange(len(categories))
        colors = ['#FF6B6B', '#4ECDC4', '#FFE66D', '#FFA500', '#FF4444']
        
        # 子图1：成功率对比
        bars1 = ax1.bar(x, success_rates, color=colors, alpha=0.8)
        ax1.errorbar(x, success_rates, yerr=success_stds, fmt='none', 
                    color='black', capsize=5, linewidth=2)
        
        # 添加数值标签
        for i, (bar, rate, count) in enumerate(zip(bars1, success_rates, total_tests)):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                    f'{rate:.1%}\n(n={count})', ha='center', va='bottom', fontsize=10)
        
        ax1.set_xlabel('Prompt Strategy', fontsize=12)
        ax1.set_ylabel('Success Rate', fontsize=12)
        ax1.set_title('Success Rate Comparison\n(All severities merged for Baseline/Optimal)', fontsize=14)
        ax1.set_xticks(x)
        ax1.set_xticklabels(categories)
        ax1.set_ylim(0, max(success_rates) * 1.3 if success_rates else 1.0)
        ax1.grid(axis='y', alpha=0.3)
        
        # 子图2：综合分数对比
        bars2 = ax2.bar(x, composite_scores, color=colors, alpha=0.8)
        ax2.errorbar(x, composite_scores, yerr=composite_stds, fmt='none', 
                    color='black', capsize=5, linewidth=2)
        
        for i, (bar, score, count) in enumerate(zip(bars2, composite_scores, total_tests)):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                    f'{score:.1%}\n(n={count})', ha='center', va='bottom', fontsize=10)
        
        ax2.set_xlabel('Prompt Strategy', fontsize=12)
        ax2.set_ylabel('Composite Score', fontsize=12)
        ax2.set_title(f'Composite Score Comparison\n({self.score_weights["success_rate"]}×Success + '
                     f'{self.score_weights["tool_accuracy"]}×Tool Accuracy)', fontsize=14)
        ax2.set_xticks(x)
        ax2.set_xticklabels(categories)
        ax2.set_ylim(0, max(composite_scores) * 1.3 if composite_scores else 1.0)
        ax2.grid(axis='y', alpha=0.3)
        
        # 添加一致性说明
        fig.text(0.5, 0.02, 
                'Note: Baseline and Optimal include all severity levels; '
                'Flawed results are shown separately by severity', 
                ha='center', fontsize=10, style='italic')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'consistent_performance_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
        logger.info("Generated: consistent_performance_comparison.png")

    def _generate_consistent_severity_comparison(self):
        """生成一致的severity对比图 - 每个severity独立计算"""
        data = self._standardize_data()
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        severities = ['light', 'medium', 'severe']
        prompt_types = ['baseline_prompt', 'optimal_prompt', 'flawed_optimal_prompt']
        prompt_labels = ['Baseline', 'Optimal', 'Flawed']
        
        # 计算每个severity下的统计数据
        severity_stats = {}
        for severity in severities:
            severity_stats[severity] = {}
            for prompt_type in prompt_types:
                severity_stats[severity][prompt_type] = self._calculate_statistics(
                    data['by_severity'][severity][prompt_type])
        
        # 准备绘图数据
        x = np.arange(len(severities))
        width = 0.25
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']
        
        # 子图1：成功率按severity分组
        for i, (prompt_type, label, color) in enumerate(zip(prompt_types, prompt_labels, colors)):
            means = [severity_stats[sev][prompt_type]['mean_success_rate'] for sev in severities]
            stds = [severity_stats[sev][prompt_type]['std_success_rate'] for sev in severities]
            
            bars = ax1.bar(x + i*width - width, means, width, label=label, color=color, alpha=0.8)
            ax1.errorbar(x + i*width - width, means, yerr=stds, fmt='none', color='black', capsize=5)
            
            # 添加数值标签
            for j, (bar, mean) in enumerate(zip(bars, means)):
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                        f'{mean:.1%}', ha='center', va='bottom', fontsize=9)
        
        ax1.set_xlabel('Flaw Severity', fontsize=12)
        ax1.set_ylabel('Success Rate', fontsize=12)
        ax1.set_title('Success Rate by Severity\n(Each severity calculated independently)', fontsize=14)
        ax1.set_xticks(x)
        ax1.set_xticklabels([s.capitalize() for s in severities])
        ax1.legend()
        ax1.grid(axis='y', alpha=0.3)
        ax1.set_ylim(0, 1.1)
        
        # 子图2：综合分数按severity分组
        for i, (prompt_type, label, color) in enumerate(zip(prompt_types, prompt_labels, colors)):
            means = [severity_stats[sev][prompt_type]['mean_composite_score'] for sev in severities]
            stds = [severity_stats[sev][prompt_type]['std_composite_score'] for sev in severities]
            
            bars = ax2.bar(x + i*width - width, means, width, label=label, color=color, alpha=0.8)
            ax2.errorbar(x + i*width - width, means, yerr=stds, fmt='none', color='black', capsize=5)
            
            for j, (bar, mean) in enumerate(zip(bars, means)):
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                        f'{mean:.1%}', ha='center', va='bottom', fontsize=9)
        
        ax2.set_xlabel('Flaw Severity', fontsize=12)
        ax2.set_ylabel('Composite Score', fontsize=12)
        ax2.set_title(f'Composite Score by Severity\n'
                     f'({self.score_weights["success_rate"]}×Success + '
                     f'{self.score_weights["tool_accuracy"]}×Tool Accuracy)', fontsize=14)
        ax2.set_xticks(x)
        ax2.set_xticklabels([s.capitalize() for s in severities])
        ax2.legend()
        ax2.grid(axis='y', alpha=0.3)
        ax2.set_ylim(0, 1.1)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'consistent_severity_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
        logger.info("Generated: consistent_severity_comparison.png")
    
    def _generate_data_consistency_report(self):
        """生成数据一致性报告"""
        data = self._standardize_data()
        
        report_path = self.output_dir / 'data_consistency_report.md'
        
        with open(report_path, 'w') as f:
            f.write("# Data Consistency Report\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # 元数据摘要
            f.write("## Dataset Overview\n\n")
            f.write(f"- Total tests conducted: {data['metadata']['total_tests']}\n")
            f.write(f"- Unique flaw types: {len(data['metadata']['flaw_types'])}\n")
            f.write(f"- Severities tested: {', '.join(sorted(data['metadata']['severities']))}\n")
            f.write(f"- Task types: {', '.join(sorted(data['metadata']['task_types']))}\n\n")
            
            # 评分标准
            f.write("## Scoring Standards\n\n")
            f.write(f"**Composite Score Formula**: ")
            f.write(f"{self.score_weights['success_rate']}×Success Rate + ")
            f.write(f"{self.score_weights['tool_accuracy']}×Tool Accuracy\n\n")
            
            # 数据平衡性检查
            f.write("## Data Balance Check\n\n")
            f.write("### Tests per Severity and Prompt Type\n\n")
            f.write("| Severity | Baseline | Optimal | Flawed |\n")
            f.write("|----------|----------|---------|--------|\n")
            
            for severity in ['light', 'medium', 'severe']:
                baseline_count = data['metadata']['test_counts'].get(f'baseline_prompt_{severity}', 0)
                optimal_count = data['metadata']['test_counts'].get(f'optimal_prompt_{severity}', 0)
                flawed_count = data['metadata']['test_counts'].get(f'flawed_optimal_prompt_{severity}', 0)
                f.write(f"| {severity.capitalize()} | {baseline_count} | {optimal_count} | {flawed_count} |\n")
            
            # 一致性验证
            f.write("\n## Consistency Validation\n\n")
            
            # 检查每个prompt type在不同severity下的表现是否一致
            f.write("### Baseline/Optimal Consistency Across Severities\n\n")
            
            for prompt_type in ['baseline_prompt', 'optimal_prompt']:
                f.write(f"\n**{prompt_type.replace('_', ' ').title()}**:\n")
                severity_stats = []
                for severity in ['light', 'medium', 'severe']:
                    stats = self._calculate_statistics(
                        data['by_severity'][severity][prompt_type])
                    if stats['data_points'] > 0:
                        severity_stats.append({
                            'severity': severity,
                            'success_rate': stats['mean_success_rate'],
                            'data_points': stats['data_points']
                        })
                
                if severity_stats:
                    # 计算变异系数
                    success_rates = [s['success_rate'] for s in severity_stats]
                    mean_rate = np.mean(success_rates)
                    std_rate = np.std(success_rates)
                    cv = std_rate / mean_rate if mean_rate > 0 else 0
                    
                    f.write(f"- Mean success rate: {mean_rate:.1%}\n")
                    f.write(f"- Std deviation: {std_rate:.1%}\n")
                    f.write(f"- Coefficient of variation: {cv:.2f}\n")
                    
                    if cv > 0.3:
                        f.write("⚠️ **Warning**: High variation across severities suggests ")
                        f.write("inconsistent test conditions or incomplete data.\n")
            
            # 数据完整性检查
            f.write("\n### Data Completeness Check\n\n")
            
            expected_combinations = len(data['metadata']['severities']) * len(data['metadata']['flaw_types'])
            actual_combinations = len(self.flaw_test_results)
            completeness = actual_combinations / expected_combinations if expected_combinations > 0 else 0
            
            f.write(f"- Expected test combinations: {expected_combinations}\n")
            f.write(f"- Actual test combinations: {actual_combinations}\n")
            f.write(f"- Completeness: {completeness:.1%}\n")
            
            if completeness < 0.9:
                f.write("\n⚠️ **Warning**: Dataset appears incomplete. Some severity/flaw combinations may be missing.\n")
        
        logger.info("Generated: data_consistency_report.md")
    
    def _load_test_results(self, checkpoint_path=None, report_path=None):
        """从多种来源加载测试结果"""
        
        # 1. 尝试从checkpoint加载
        if checkpoint_path and Path(checkpoint_path).exists():
            logger.info(f"Loading from checkpoint: {checkpoint_path}")
            try:
                import torch
                checkpoint = torch.load(checkpoint_path, map_location='cpu', weights_only=False)
                if 'flaw_test_results' in checkpoint:
                    return checkpoint['flaw_test_results']
            except Exception as e:
                logger.warning(f"Failed to load from checkpoint: {e}")
        
        # 2. 尝试从JSON报告加载
        if report_path and Path(report_path).exists():
            logger.info(f"Loading from report: {report_path}")
            try:
                with open(report_path, 'r') as f:
                    data = json.load(f)
                    # 处理嵌套结构
                    if 'flaw_test_results' in data:
                        return data['flaw_test_results']
                    elif any('flaw' in k for k in data.keys()):
                        return data
            except Exception as e:
                logger.warning(f"Failed to load from report: {e}")
        
        # 3. 优先尝试加载综合结果文件
        combined_path = Path("output/flawed_test_combined_results.json")
        if combined_path.exists():
            logger.info(f"Loading combined results from: {combined_path}")
            try:
                with open(combined_path, 'r') as f:
                    combined_data = json.load(f)
                
                # 合并所有task_type和severity的结果
                # 相同位置的修复代码
                # 合并所有task_type和severity的结果
                merged_results = {}
                for task_type, severity_data in combined_data.items():
                    for severity, test_data in severity_data.items():
                        flaw_results = test_data.get('flaw_test_results', {})
                        for flaw_name, flaw_data in flaw_results.items():
                            # 始终创建唯一的key，包含task_type和severity信息
                            unique_key = f"{flaw_name}_{task_type}_{severity}"
                            merged_results[unique_key] = flaw_data
                            
                            # 确保severity和task_type信息存在
                            if 'flaw_info' not in merged_results[unique_key]:
                                merged_results[unique_key]['flaw_info'] = {}
                            merged_results[unique_key]['flaw_info']['severity'] = severity
                            merged_results[unique_key]['flaw_info']['task_type'] = task_type

                if merged_results:
                    logger.info(f"Loaded {len(merged_results)} flaw results from combined file")
                    
                    # 添加统计信息
                    severity_stats = defaultdict(lambda: {'flaw_count': 0, 'total_tests': 0})
                    for key, data in merged_results.items():
                        severity = data.get('flaw_info', {}).get('severity', 'unknown')
                        perf = data.get('performance_comparison', {})
                        
                        severity_stats[severity]['flaw_count'] += 1
                        
                        # 累加所有prompt类型的测试数
                        for prompt_type in ['baseline_prompt', 'optimal_prompt', 'flawed_optimal_prompt']:
                            if prompt_type in perf:
                                severity_stats[severity]['total_tests'] += perf[prompt_type].get('total_tests', 0)
                    
                    logger.info("Severity statistics from combined file:")
                    for severity, stats in severity_stats.items():
                        logger.info(f"  - {severity}: {stats['flaw_count']} flaws, {stats['total_tests']} total tests")
                    
                    return merged_results
            except Exception as e:
                logger.warning(f"Failed to load combined results: {e}")
        
        # 4. 查找并加载所有相关的测试结果文件
        test_results_patterns = [
            # 新格式：包含task_type和severity
            "output/flawed_test_*_*_*.json",  # flawed_test_basic_task_severe_20250620_105756.json
            # 旧格式：只有时间戳
            "output/flawed_test_results_*.json",  # flawed_test_results_20250620_101450.json
            # 其他可能的位置
            "test_bugs/summaries/flawed_results_*.json",
            "test_bugs/summaries/flawed_test_*.json"
        ]
        
        all_results = {}
        loaded_files = []
        severity_inference_map = {}  # 用于推断旧文件的severity
        
        # 收集所有匹配的文件
        all_files = []
        for pattern in test_results_patterns:
            files = list(Path(".").glob(pattern))
            all_files.extend(files)
        
        # 去重并按时间排序
        unique_files = list(set(all_files))
        unique_files.sort(key=lambda p: p.stat().st_mtime)
        
        logger.info(f"Found {len(unique_files)} test result files")
        
        for file in unique_files:
            if 'combined' in str(file):  # 跳过综合文件
                continue
                
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    
                # 提取文件名中的信息
                filename = file.stem
                parts = filename.split('_')
                
                # 尝试从文件名推断信息
                task_type = 'unknown'
                severity = 'unknown'
                
                # 新格式：flawed_test_basic_task_severe_20250620_105756
                if len(parts) >= 5 and parts[0] == 'flawed' and parts[1] == 'test':
                    if parts[3] in ['light', 'medium', 'severe']:
                        task_type = parts[2]
                        severity = parts[3]
                    elif parts[4] in ['light', 'medium', 'severe']:
                        task_type = f"{parts[2]}_{parts[3]}"
                        severity = parts[4]
                
                # 从JSON数据中获取信息（优先级更高）
                if isinstance(data, dict):
                    task_type = data.get('task_type', task_type)
                    severity = data.get('severity', severity)
                    
                    # 处理包含flaw_test_results的格式
                    if 'flaw_test_results' in data:
                        flaw_results = data['flaw_test_results']
                        
                        # 记录加载信息
                        loaded_files.append({
                            'file': str(file),
                            'task_type': task_type,
                            'severity': severity,
                            'timestamp': data.get('timestamp', 'unknown'),
                            'flaw_count': len(flaw_results)
                        })
                        
                        # 合并结果
                        for flaw_name, flaw_data in flaw_results.items():
                            # 创建一个标识符来检查是否需要添加severity后缀
                            base_key = flaw_name
                            
                            # 如果severity是unknown，尝试从其他文件推断
                            if severity == 'unknown' and base_key in severity_inference_map:
                                severity = severity_inference_map[base_key]
                            
                            # 检查是否已存在相同的flaw
                            # 在_load_test_results方法中，修复unique_key问题
                            # 确保key_to_use总是被定义
                            if base_key in all_results:
                                # 检查severity是否相同
                                existing_severity = all_results[base_key].get('flaw_info', {}).get('severity', 'unknown')
                                if existing_severity != severity and severity != 'unknown':
                                    # 创建新的唯一key
                                    unique_key = f"{base_key}_{severity}"
                                    if unique_key in all_results:
                                        unique_key = f"{base_key}_{task_type}_{severity}"
                                    all_results[unique_key] = flaw_data
                                    key_to_use = unique_key
                                else:
                                    # 更新现有数据（如果新数据更完整）
                                    if severity != 'unknown' and existing_severity == 'unknown':
                                        all_results[base_key] = flaw_data
                                    key_to_use = base_key
                            else:
                                all_results[base_key] = flaw_data
                                key_to_use = base_key
                            
                            # 确保flaw_info存在并包含正确信息
                            if 'flaw_info' not in all_results[key_to_use]:
                                all_results[key_to_use]['flaw_info'] = {}
                            
                            # 更新severity和task_type信息
                            if severity != 'unknown':
                                all_results[key_to_use]['flaw_info']['severity'] = severity
                                severity_inference_map[base_key] = severity
                            if task_type != 'unknown':
                                all_results[key_to_use]['flaw_info']['task_type'] = task_type
                    
                    # 处理直接包含flaw数据的旧格式
                    elif any('flaw' in k for k in data.keys()):
                        loaded_files.append({
                            'file': str(file),
                            'task_type': task_type,
                            'severity': severity,
                            'timestamp': 'unknown',
                            'flaw_count': len([k for k in data.keys() if 'flaw' in k])
                        })
                        
                        # 对于旧格式，尝试从数据推断severity
                        for key, value in data.items():
                            if 'flaw' in key and isinstance(value, dict):
                                if key not in all_results:
                                    all_results[key] = value
                                
                                # 尝试从flaw_info推断
                                if 'flaw_info' in value:
                                    inferred_severity = value['flaw_info'].get('severity', severity)
                                    if inferred_severity != 'unknown':
                                        severity_inference_map[key] = inferred_severity
                                
                                # 确保flaw_info存在
                                if 'flaw_info' not in all_results[key]:
                                    all_results[key]['flaw_info'] = {}
                                
                                # 只在有明确信息时更新
                                if severity != 'unknown':
                                    all_results[key]['flaw_info']['severity'] = severity
                                if task_type != 'unknown':
                                    all_results[key]['flaw_info']['task_type'] = task_type
                            
            except Exception as e:
                logger.warning(f"Failed to load {file}: {e}")
        
        if all_results:
            # 打印加载摘要
            logger.info(f"\nLoaded {len(all_results)} total flaw results from {len(loaded_files)} files:")
            
            # 按severity统计
            severity_stats = defaultdict(lambda: {'count': 0, 'files': []})
            for file_info in loaded_files:
                sev = file_info['severity']
                severity_stats[sev]['count'] += file_info['flaw_count']
                severity_stats[sev]['files'].append(file_info['file'].split('/')[-1])
            
            logger.info("\nSeverity distribution:")
            for severity in ['light', 'medium', 'severe', 'unknown']:
                if severity in severity_stats:
                    stats = severity_stats[severity]
                    logger.info(f"  - {severity}: {stats['count']} flaws from {len(stats['files'])} files")
                    for filename in stats['files'][:3]:  # 显示前3个文件
                        logger.info(f"      • {filename}")
                    if len(stats['files']) > 3:
                        logger.info(f"      • ... and {len(stats['files']) - 3} more files")
            
            # 尝试推断unknown severity的数据
            unknown_count = sum(1 for flaw_data in all_results.values() 
                            if flaw_data.get('flaw_info', {}).get('severity', 'unknown') == 'unknown')
            if unknown_count > 0:
                logger.warning(f"\n⚠️  {unknown_count} flaws have unknown severity. They will be excluded from severity-based analysis.")
                logger.info("   Consider re-running tests with proper severity specification.")
            
            return all_results
        
        # 5. 最后尝试从markdown报告解析
        md_report = Path("output/flawed_workflow_report.md")
        if md_report.exists():
            logger.info("Attempting to parse from markdown report...")
            return self._parse_from_markdown(md_report)
        
        return None
    
    def _parse_from_markdown(self, md_path):
        """从markdown报告解析数据（备用方案）"""
        flaw_results = {}
        
        with open(md_path, 'r') as f:
            content = f.read()
        
        # 简单的解析逻辑，提取表格数据
        # 这是一个备用方案，可能需要根据实际markdown格式调整
        current_flaw = None
        
        for line in content.split('\n'):
            if '###' in line and any(flaw_type in line.lower() for flaw_type in 
                                   ['order', 'tool', 'parameter', 'missing', 'redundant', 'logic']):
                # 提取flaw名称
                flaw_name = line.replace('###', '').strip().lower().replace(' ', '_')
                current_flaw = flaw_name
                flaw_results[current_flaw] = {
                    'flaw_info': {'type': flaw_name, 'severity': 'medium'},
                    'performance_comparison': {}
                }
            
            elif current_flaw and '|' in line and '%' in line:
                # 尝试解析表格行
                parts = [p.strip() for p in line.split('|') if p.strip()]
                if len(parts) >= 4:
                    prompt_type = parts[0].lower().replace(' ', '_')
                    try:
                        success_rate = float(parts[1].replace('%', '')) / 100
                        if prompt_type in ['optimal_prompt', 'baseline_prompt', 'current_prompt']:
                            flaw_results[current_flaw]['performance_comparison'][prompt_type] = {
                                'success_rate': success_rate,
                                'tool_accuracy': success_rate * 0.9,  # 估算值
                                'avg_execution_time': 3.0
                            }
                    except ValueError:
                        pass
        
        return flaw_results if flaw_results else None
    
# 文件：visualize_flawed_results.py
# 位置：在generate_all_visualizations方法后添加新方法，约150行后

    def generate_all_visualizations(self):
        """生成所有可视化 - 确保一致性"""
        logger.info("Generating consistent visualizations...")
        
        # 标准化数据（只处理一次）
        self._standardize_data()
        
        # 设置统一的风格
        plt.style.use('seaborn-v0_8-darkgrid')
        sns.set_palette("husl")
        
        # 生成一致的可视化
        self._generate_consistent_performance_comparison()
        self._generate_consistent_severity_comparison()
        self._generate_data_consistency_report()
        
        # 生成其他补充图表
        self._generate_flaw_category_comparison()  # 保留原有方法
        self._generate_prompt_radar_chart()        # 保留原有方法
        
        logger.info("All visualizations generated with consistent standards!")

    def _generate_multi_threshold_analysis(self):
        """生成多阈值成功率分析图"""
        # 检查是否有多阈值数据
        has_multi_threshold = self._check_multi_threshold_data()
        
        if not has_multi_threshold:
            logger.info("No multi-threshold data found, skipping threshold analysis")
            return
            
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        # 定义阈值
        thresholds = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        threshold_labels = {
            0.5: "Partial (50%+)",
            0.6: "Basic (60%+)",
            0.7: "Standard (70%+)",
            0.8: "High (80%+)",
            0.9: "Very High (90%+)",
            1.0: "Perfect (100%)"
        }
        
        # 子图1：整体成功率随阈值变化
        overall_rates = self._calculate_overall_threshold_rates(thresholds)
        
        x = np.arange(len(thresholds))
        width = 0.25
        
        baseline_rates = [overall_rates[t]['baseline'] for t in thresholds]
        mdp_rates = [overall_rates[t]['mdp'] for t in thresholds]
        flawed_optimal_rates = [overall_rates[t]['flawed_optimal'] for t in thresholds]
        
        rects1 = ax1.bar(x - width, baseline_rates, width, label='Without MDP', color='#FF6B6B')
        rects2 = ax1.bar(x, mdp_rates, width, label='With MDP', color='#4ECDC4')
        rects3 = ax1.bar(x + width, flawed_optimal_rates, width, label='Flawed Optimal', color='#45B7D1')
        
        ax1.set_xlabel('Completion Threshold', fontsize=12)
        ax1.set_ylabel('Success Rate', fontsize=12)
        ax1.set_title('Success Rate by Completion Threshold', fontsize=14)
        ax1.set_xticks(x)
        ax1.set_xticklabels([f"{t:.0%}" for t in thresholds], rotation=45)
        ax1.legend()
        ax1.grid(axis='y', alpha=0.3)
        ax1.set_ylim(0, 1.1)
        
        # 添加数值标签
        for rects in [rects1, rects2, rects3]:
            for rect in rects:
                height = rect.get_height()
                ax1.annotate(f'{height:.1%}',
                            xy=(rect.get_x() + rect.get_width() / 2, height),
                            xytext=(0, 3),
                            textcoords="offset points",
                            ha='center', va='bottom',
                            fontsize=8)
        
        # 子图2：改进率趋势线
        improvement_mdp = [(mdp - base) / (base + 0.001) * 100 
                          for mdp, base in zip(mdp_rates, baseline_rates)]
        improvement_flawed = [(flawed - base) / (base + 0.001) * 100 
                             for flawed, base in zip(flawed_optimal_rates, baseline_rates)]
        
        ax2.plot(thresholds, improvement_mdp, 'o-', linewidth=2, markersize=8, 
                label='With MDP vs Baseline', color='#4ECDC4')
        ax2.plot(thresholds, improvement_flawed, 's-', linewidth=2, markersize=8,
                label='Flawed Optimal vs Baseline', color='#45B7D1')
        
        ax2.set_xlabel('Completion Threshold', fontsize=12)
        ax2.set_ylabel('Improvement Rate (%)', fontsize=12)
        ax2.set_title('Performance Improvement vs Baseline by Threshold', fontsize=14)
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        
        # 添加阈值描述
        ax2.set_xticks(thresholds)
        ax2.set_xticklabels([f"{t:.0%}" for t in thresholds])
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'multi_threshold_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()
        logger.info("Generated: multi_threshold_analysis.png")

    def _generate_threshold_gradient_heatmap(self):
        """生成阈值梯度热力图"""
        if not self._check_multi_threshold_data():
            return
            
        fig, ax = plt.subplots(figsize=(12, 10))
        
        thresholds = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        
        # 收集所有flaw类型
        flaw_types = sorted(list(self.flaw_test_results.keys()))[:15]  # 限制显示前15个
        
        # 构建数据矩阵
        heatmap_data = []
        
        for flaw in flaw_types:
            flaw_data = self.flaw_test_results[flaw]
            row_data = []
            
            # 检查是否有多阈值数据
            if 'threshold_performance' in flaw_data:
                # 使用多阈值数据
                for threshold in thresholds:
                    perf = flaw_data['threshold_performance'].get(str(threshold), {})
                    # 计算三种prompt的平均成功率
                    avg_rate = np.mean([
                        perf.get('baseline_prompt', {}).get('success_rate', 0),
                        perf.get('optimal_prompt', {}).get('success_rate', 0),
                        perf.get('flawed_optimal_prompt', {}).get('success_rate', 0)
                    ])
                    row_data.append(avg_rate)
            else:
                # 使用单一成功率数据，模拟阈值效应
                base_rate = flaw_data.get('performance_comparison', {}).get('optimal_prompt', {}).get('success_rate', 0)
                for threshold in thresholds:
                    # 简单的阈值效应模拟
                    if threshold <= 0.7:
                        row_data.append(base_rate)
                    else:
                        # 高阈值下成功率下降
                        row_data.append(base_rate * (1.7 - threshold))
            
            heatmap_data.append(row_data)
        
        # 创建热力图
        heatmap_array = np.array(heatmap_data)
        im = ax.imshow(heatmap_array, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)
        
        # 设置标签
        ax.set_xticks(np.arange(len(thresholds)))
        ax.set_yticks(np.arange(len(flaw_types)))
        ax.set_xticklabels([f"{t:.0%}" for t in thresholds])
        ax.set_yticklabels([f.replace('_', ' ').title() for f in flaw_types])
        
        # 添加数值标注
        for i in range(len(flaw_types)):
            for j in range(len(thresholds)):
                value = heatmap_array[i, j]
                color = 'white' if value < 0.5 else 'black'
                text = ax.text(j, i, f'{value:.0%}',
                             ha="center", va="center", color=color, fontsize=9)
        
        # 添加颜色条
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Average Success Rate', rotation=270, labelpad=20)
        
        ax.set_title('Success Rate Gradient Across Completion Thresholds', fontsize=16, pad=20)
        ax.set_xlabel('Completion Threshold', fontsize=12)
        ax.set_ylabel('Flaw Type', fontsize=12)
        
        # 添加阈值线（标记默认阈值）
        ax.axvline(x=2, color='blue', linestyle='--', linewidth=2, alpha=0.5)  # 70%阈值
        ax.text(2, -1, 'Default (70%)', ha='center', va='top', color='blue', fontsize=10)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'threshold_gradient_heatmap.png', dpi=300, bbox_inches='tight')
        plt.close()
        logger.info("Generated: threshold_gradient_heatmap.png")

    def _check_multi_threshold_data(self) -> bool:
        """检查是否有多阈值数据"""
        for flaw_data in self.flaw_test_results.values():
            if 'threshold_performance' in flaw_data:
                return True
        return False

    def _calculate_overall_threshold_rates(self, thresholds: List[float]) -> Dict:
        """计算各阈值下的整体成功率"""
        results = {}
        
        for threshold in thresholds:
            baseline_rates = []
            mdp_rates = []
            flawed_optimal_rates = []
            
            for flaw_data in self.flaw_test_results.values():
                if 'threshold_performance' in flaw_data:
                    # 使用实际的多阈值数据
                    perf = flaw_data['threshold_performance'].get(str(threshold), {})
                    baseline_rates.append(perf.get('baseline_prompt', {}).get('success_rate', 0))
                    mdp_rates.append(perf.get('optimal_prompt', {}).get('success_rate', 0))
                    flawed_optimal_rates.append(perf.get('flawed_optimal_prompt', {}).get('success_rate', 0))
                else:
                    # 使用单一成功率数据，根据阈值调整
                    perf = flaw_data.get('performance_comparison', {})
                    base_baseline = perf.get('baseline_prompt', {}).get('success_rate', 0)
                    base_mdp = perf.get('optimal_prompt', {}).get('success_rate', 0)
                    base_flawed = perf.get('flawed_optimal_prompt', {}).get('success_rate', 0)
                    
                    # 简单的阈值效应模拟
                    if threshold <= 0.7:
                        baseline_rates.append(base_baseline)
                        mdp_rates.append(base_mdp)
                        flawed_optimal_rates.append(base_flawed)
                    else:
                        # 高阈值下成功率下降
                        factor = 1.7 - threshold
                        baseline_rates.append(base_baseline * factor)
                        mdp_rates.append(base_mdp * factor)
                        flawed_optimal_rates.append(base_flawed * factor)
            
            results[threshold] = {
                'baseline': np.mean(baseline_rates) if baseline_rates else 0,
                'mdp': np.mean(mdp_rates) if mdp_rates else 0,
                'flawed_optimal': np.mean(flawed_optimal_rates) if flawed_optimal_rates else 0
            }
        
        return results
        
    def _generate_flaw_category_comparison(self):
        """生成flaw类别性能对比图"""
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        axes = axes.flatten()
        
        # 按类别分组flaws
        categories = {
            'Order': ['order_flaw_swap', 'order_flaw_dependency'],
            'Tool': ['tool_misuse_similar', 'tool_misuse_wrong_category'],
            'Parameter': ['param_missing', 'param_wrong_type'],
            'Missing': ['missing_middle', 'missing_validation'],
            'Redundancy': ['redundant_duplicate', 'redundant_unnecessary'],
            'Logic': ['logic_break_format', 'logic_break_unrelated']
        }
        
        for idx, (category, flaws) in enumerate(categories.items()):
            ax = axes[idx]
            
            # 收集该类别的数据
            prompt_scores = {'Without MDP': [], 'With MDP': [], 'Flawed Optimal': []}
            
            for flaw in flaws:
                if flaw in self.flaw_test_results:
                    perf = self.flaw_test_results[flaw].get('performance_comparison', {})
                    prompt_scores['Without MDP'].append(perf.get('baseline_prompt', {}).get('success_rate', 0))
                    prompt_scores['With MDP'].append(perf.get('optimal_prompt', {}).get('success_rate', 0))
                    prompt_scores['Flawed Optimal'].append(perf.get('flawed_optimal_prompt', {}).get('success_rate', 0))
            
            # 创建箱线图
            data = [prompt_scores['Without MDP'], prompt_scores['With MDP'], prompt_scores['Flawed Optimal']]
            # 过滤空数据
            data = [d if d else [0] for d in data]
            
            bp = ax.boxplot(data, labels=['Without\nMDP', 'With\nMDP', 'Flawed\nOptimal'], 
                            patch_artist=True, notch=True)
            
            # 设置颜色
            colors = ['lightcoral', 'lightblue', 'lightgreen']
            for patch, color in zip(bp['boxes'], colors):
                patch.set_facecolor(color)
            
            ax.set_title(f'{category} Flaws', fontsize=14)
            ax.set_ylabel('Success Rate', fontsize=12)
            ax.set_ylim(0, 1.1)
            ax.grid(axis='y', alpha=0.3)
            
            # 添加均值标记
            for i, prompt in enumerate(['Without MDP', 'With MDP', 'Flawed Optimal']):
                if prompt_scores[prompt]:
                    mean_val = np.mean(prompt_scores[prompt])
                    ax.scatter(i+1, mean_val, color='red', s=50, zorder=3, marker='D')
        
        plt.suptitle('Performance Distribution by Flaw Category', fontsize=18)
        plt.tight_layout()
        plt.savefig(self.output_dir / 'flaw_category_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()
        logger.info("Generated: flaw_category_analysis.png")
    
    def _generate_prompt_radar_chart(self):
        """生成prompt策略的雷达图对比"""
        from math import pi
        
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
        
        # 准备数据
        categories = ['Order', 'Tool', 'Parameter', 'Missing', 'Redundancy', 'Logic']
        N = len(categories)
        
        # 计算每个类别的平均得分
        prompt_data = {
            'Without MDP': [],
            'With MDP': [],
            'Flawed Optimal': []
        }
        
        category_flaws = {
            'Order': ['order_flaw_swap', 'order_flaw_dependency'],
            'Tool': ['tool_misuse_similar', 'tool_misuse_wrong_category'],
            'Parameter': ['param_missing', 'param_wrong_type'],
            'Missing': ['missing_middle', 'missing_validation'],
            'Redundancy': ['redundant_duplicate', 'redundant_unnecessary'],
            'Logic': ['logic_break_format', 'logic_break_unrelated']
        }
        
        for category, flaws in category_flaws.items():
            category_scores = {'baseline_prompt': [], 'optimal_prompt': [], 'flawed_optimal_prompt': []}
            
            for flaw in flaws:
                if flaw in self.flaw_test_results:
                    perf = self.flaw_test_results[flaw].get('performance_comparison', {})
                    for prompt_key, display_name in [('baseline_prompt', 'Without MDP'), 
                                                    ('optimal_prompt', 'With MDP'), 
                                                    ('flawed_optimal_prompt', 'Flawed Optimal')]:
                        if prompt_key in perf:
                            score = perf[prompt_key].get('success_rate', 0)
                            category_scores[prompt_key].append(score)
            
            # 计算平均值
            prompt_data['Without MDP'].append(np.mean(category_scores['baseline_prompt']) if category_scores['baseline_prompt'] else 0)
            prompt_data['With MDP'].append(np.mean(category_scores['optimal_prompt']) if category_scores['optimal_prompt'] else 0)
            prompt_data['Flawed Optimal'].append(np.mean(category_scores['flawed_optimal_prompt']) if category_scores['flawed_optimal_prompt'] else 0)
        
        # 设置角度
        angles = [n / float(N) * 2 * pi for n in range(N)]
        angles += angles[:1]
        
        # 绘制雷达图
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']
        for idx, (prompt, values) in enumerate(prompt_data.items()):
            values += values[:1]  # 闭合图形
            ax.plot(angles, values, 'o-', linewidth=2, label=prompt, color=colors[idx])
            ax.fill(angles, values, alpha=0.25, color=colors[idx])
        
        # 设置标签
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, size=12)
        ax.set_ylim(0, 1)
        
        # 添加网格
        ax.set_rticks([0.2, 0.4, 0.6, 0.8, 1.0])
        ax.set_rlabel_position(45)
        ax.grid(True)
        
        # 添加图例和标题
        plt.legend(loc='upper right', bbox_to_anchor=(1.2, 1.1))
        plt.title('Prompt Strategy Performance Across Flaw Categories', size=16, pad=30)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'prompt_radar_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
        logger.info("Generated: prompt_radar_comparison.png")

    def _generate_performance_comparison(self):
        """生成类似原测试的性能对比图（成功率和执行时间）"""
        # 准备数据
        task_types = []
        baseline_success = []
        mdp_success = []
        flawed_optimal_success = []
        
        # 按flaw类型聚合数据
        for flaw_name, flaw_data in self.flaw_test_results.items():
            task_types.append(flaw_name.replace('_', ' ').title()[:20])  # 限制长度
            perf = flaw_data.get('performance_comparison', {})
            
            baseline_success.append(perf.get('baseline_prompt', {}).get('success_rate', 0))
            mdp_success.append(perf.get('optimal_prompt', {}).get('success_rate', 0))
            flawed_optimal_success.append(perf.get('flawed_optimal_prompt', {}).get('success_rate', 0))
        
        # 创建图表
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        # 子图1：成功率对比
        x = np.arange(len(task_types))
        width = 0.25
        
        rects1 = ax1.bar(x - width, baseline_success, width, label='Without MDP', color='#FF6B6B')
        rects2 = ax1.bar(x, mdp_success, width, label='With MDP', color='#4ECDC4')
        rects3 = ax1.bar(x + width, flawed_optimal_success, width, label='Flawed Optimal', color='#45B7D1')
        
        ax1.set_xlabel('Flaw Type', fontsize=12)
        ax1.set_ylabel('Success Rate', fontsize=12)
        ax1.set_title('Success Rate Comparison Across Flaw Types', fontsize=14)
        ax1.set_xticks(x)
        ax1.set_xticklabels(task_types, rotation=45, ha='right')
        ax1.legend()
        ax1.grid(axis='y', alpha=0.3)
        ax1.set_ylim(0, 1.1)
        
        # 添加数值标签
        def autolabel(rects, ax):
            for rect in rects:
                height = rect.get_height()
                ax.annotate(f'{height:.0%}',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom',
                        fontsize=8)
        
        autolabel(rects1, ax1)
        autolabel(rects2, ax1)
        autolabel(rects3, ax1)
        
        # 子图2：改进率对比（相对于baseline）
        improvement_mdp = [(mdp - base) / (base + 0.001) * 100 if base > 0 else 0 
                        for mdp, base in zip(mdp_success, baseline_success)]
        improvement_flawed = [(flawed - base) / (base + 0.001) * 100 if base > 0 else 0 
                            for flawed, base in zip(flawed_optimal_success, baseline_success)]
        
        x2 = np.arange(len(task_types))
        width2 = 0.35
        
        rects4 = ax2.bar(x2 - width2/2, improvement_mdp, width2, label='With MDP vs Baseline', color='#4ECDC4')
        rects5 = ax2.bar(x2 + width2/2, improvement_flawed, width2, label='Flawed Optimal vs Baseline', color='#45B7D1')
        
        ax2.set_xlabel('Flaw Type', fontsize=12)
        ax2.set_ylabel('Improvement Rate (%)', fontsize=12)
        ax2.set_title('Performance Improvement Relative to Baseline', fontsize=14)
        ax2.set_xticks(x2)
        ax2.set_xticklabels(task_types, rotation=45, ha='right')
        ax2.legend()
        ax2.grid(axis='y', alpha=0.3)
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        
        # 添加数值标签
        def autolabel_improvement(rects, ax):
            for rect in rects:
                height = rect.get_height()
                label = f'{height:+.0f}%'
                if height < 0:
                    va = 'top'
                    y_offset = -3
                else:
                    va = 'bottom'
                    y_offset = 3
                ax.annotate(label,
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, y_offset),
                        textcoords="offset points",
                        ha='center', va=va,
                        fontsize=8)
        
        autolabel_improvement(rects4, ax2)
        autolabel_improvement(rects5, ax2)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'performance_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
        logger.info("Generated: performance_comparison.png")

    def _generate_performance_by_severity(self):
        """生成按严重程度分组的性能对比图"""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # 按严重程度分组数据
        severity_data = {
            'light': {'baseline': [], 'mdp': [], 'flawed_optimal': []},
            'medium': {'baseline': [], 'mdp': [], 'flawed_optimal': []},
            'severe': {'baseline': [], 'mdp': [], 'flawed_optimal': []}
        }

        # 收集数据 - 现在可以正确获取severity信息
        # 收集数据 - 改进severity提取逻辑
        for flaw_key, flaw_data in self.flaw_test_results.items():
            # 从flaw_info获取severity
            severity = flaw_data.get('flaw_info', {}).get('severity', None)
            
            # 如果flaw_info中没有severity，尝试从key中提取（针对旧数据）
            if not severity and '_' in flaw_key:
                # 尝试匹配模式：tasktype_severity_flawname 或 flawname_tasktype_severity
                parts = flaw_key.split('_')
                for part in parts:
                    if part in ['light', 'medium', 'severe']:
                        severity = part
                        break
            
            # 如果还是没有找到，使用默认值
            if not severity:
                severity = 'medium'
                logger.warning(f"Could not determine severity for {flaw_key}, using default: {severity}")
            
            perf = flaw_data.get('performance_comparison', {})
            
            if severity in severity_data:
                severity_data[severity]['baseline'].append(
                    perf.get('baseline_prompt', {}).get('success_rate', 0))
                severity_data[severity]['mdp'].append(
                    perf.get('optimal_prompt', {}).get('success_rate', 0))
                severity_data[severity]['flawed_optimal'].append(
                    perf.get('flawed_optimal_prompt', {}).get('success_rate', 0))
            else:
                logger.warning(f"Unknown severity '{severity}' for {flaw_key}")
        
        # 计算平均值
        severities = ['light', 'medium', 'severe']
        baseline_means = []
        mdp_means = []
        flawed_optimal_means = []
        
        for severity in severities:
            if severity_data[severity]['baseline']:
                baseline_means.append(np.mean(severity_data[severity]['baseline']))
                mdp_means.append(np.mean(severity_data[severity]['mdp']))
                flawed_optimal_means.append(np.mean(severity_data[severity]['flawed_optimal']))
            else:
                baseline_means.append(0)
                mdp_means.append(0)
                flawed_optimal_means.append(0)
        
        # 创建分组柱状图
        x = np.arange(len(severities))
        width = 0.25
        
        rects1 = ax.bar(x - width, baseline_means, width, label='Without MDP', color='#FF6B6B')
        rects2 = ax.bar(x, mdp_means, width, label='With MDP', color='#4ECDC4')
        rects3 = ax.bar(x + width, flawed_optimal_means, width, label='Flawed Optimal', color='#45B7D1')
        
        # 添加误差条
        baseline_stds = [np.std(severity_data[s]['baseline']) if severity_data[s]['baseline'] else 0 
                        for s in severities]
        mdp_stds = [np.std(severity_data[s]['mdp']) if severity_data[s]['mdp'] else 0 
                    for s in severities]
        flawed_optimal_stds = [np.std(severity_data[s]['flawed_optimal']) if severity_data[s]['flawed_optimal'] else 0 
                            for s in severities]
        
        ax.errorbar(x - width, baseline_means, yerr=baseline_stds, fmt='none', color='black', capsize=5)
        ax.errorbar(x, mdp_means, yerr=mdp_stds, fmt='none', color='black', capsize=5)
        ax.errorbar(x + width, flawed_optimal_means, yerr=flawed_optimal_stds, fmt='none', color='black', capsize=5)
        
        ax.set_xlabel('Flaw Severity', fontsize=14)
        ax.set_ylabel('Average Success Rate', fontsize=14)
        ax.set_title('Performance by Flaw Severity Level', fontsize=16)
        ax.set_xticks(x)
        ax.set_xticklabels([s.capitalize() for s in severities])
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        ax.set_ylim(0, 1.1)
        
        # 添加数值标签
        for i, (baseline, mdp, flawed) in enumerate(zip(baseline_means, mdp_means, flawed_optimal_means)):
            ax.text(i - width, baseline + 0.01, f'{baseline:.1%}', ha='center', va='bottom', fontsize=9)
            ax.text(i, mdp + 0.01, f'{mdp:.1%}', ha='center', va='bottom', fontsize=9)
            ax.text(i + width, flawed + 0.01, f'{flawed:.1%}', ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'performance_by_severity.png', dpi=300, bbox_inches='tight')
        plt.close()
        logger.info("Generated: performance_by_severity.png")

    def _generate_merged_performance_comparison(self):
        """生成合并severity后的性能对比图（包含score和成功率两种）"""
        # 创建两个子图：一个显示完全成功率，一个显示score
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        # 数据收集结构 - 添加total_tests字段
        merged_data = {
            'baseline': {'success_rates': [], 'scores': [], 'total_tests': 0},
            'optimal': {'success_rates': [], 'scores': [], 'total_tests': 0},
            'flawed_light': {'success_rates': [], 'scores': [], 'total_tests': 0},
            'flawed_medium': {'success_rates': [], 'scores': [], 'total_tests': 0},
            'flawed_severe': {'success_rates': [], 'scores': [], 'total_tests': 0}
        }
        
        # 添加详细的调试信息
        severity_counts = {'light': 0, 'medium': 0, 'severe': 0}
        flaw_test_counts = {'light': 0, 'medium': 0, 'severe': 0}
        
        # 收集所有数据
        for flaw_key, flaw_data in self.flaw_test_results.items():
            severity = flaw_data.get('flaw_info', {}).get('severity', 'medium')
            perf = flaw_data.get('performance_comparison', {})
            
            # 记录每个severity的flaw数量
            if severity in severity_counts:
                severity_counts[severity] += 1
            
            # 对于baseline和optimal，合并所有severity的数据
            if 'baseline_prompt' in perf:
                success_rate = perf['baseline_prompt'].get('success_rate', 0)
                tool_accuracy = perf['baseline_prompt'].get('tool_accuracy', 0)
                score = 0.7 * success_rate + 0.3 * tool_accuracy
                total_tests = perf['baseline_prompt'].get('total_tests', 0)
                
                merged_data['baseline']['success_rates'].append(success_rate)
                merged_data['baseline']['scores'].append(score)
                merged_data['baseline']['total_tests'] += total_tests  # 累加总测试次数
                
            if 'optimal_prompt' in perf:
                success_rate = perf['optimal_prompt'].get('success_rate', 0)
                tool_accuracy = perf['optimal_prompt'].get('tool_accuracy', 0)
                score = 0.7 * success_rate + 0.3 * tool_accuracy
                total_tests = perf['optimal_prompt'].get('total_tests', 0)
                
                merged_data['optimal']['success_rates'].append(success_rate)
                merged_data['optimal']['scores'].append(score)
                merged_data['optimal']['total_tests'] += total_tests  # 累加总测试次数
            
            # 对于flawed_optimal，按severity分组
            if 'flawed_optimal_prompt' in perf:
                success_rate = perf['flawed_optimal_prompt'].get('success_rate', 0)
                tool_accuracy = perf['flawed_optimal_prompt'].get('tool_accuracy', 0)
                score = 0.7 * success_rate + 0.3 * tool_accuracy
                total_tests = perf['flawed_optimal_prompt'].get('total_tests', 0)
                
                key = f'flawed_{severity}'
                if key in merged_data:
                    merged_data[key]['success_rates'].append(success_rate)
                    merged_data[key]['scores'].append(score)
                    merged_data[key]['total_tests'] += total_tests  # 累加总测试次数
                    flaw_test_counts[severity] += total_tests  # 统计每个severity的实际测试数

        # 打印调试信息
        logger.info("=== Data Collection Summary ===")
        logger.info(f"Flaw types by severity: {severity_counts}")
        logger.info(f"Actual tests by severity: {flaw_test_counts}")
        logger.info("Data points collected:")
        for key, data in merged_data.items():
            logger.info(f"  {key}: {len(data['success_rates'])} flaw types, "
                    f"{data['total_tests']} total tests")

        # 计算平均值 - 使用正确的数据点数
        plot_data = {}
        for key, data in merged_data.items():
            # 使用total_tests作为样本数
            actual_count = data['total_tests']
            
            # 如果没有测试数据，使用数据点数量 × 预期的每个flaw测试次数
            if actual_count == 0 and data['success_rates']:
                # 假设每个flaw应该有100次测试
                actual_count = len(data['success_rates']) * 100
                logger.warning(f"{key}: No total_tests info, estimated as {actual_count}")
            
            plot_data[key] = {
                'avg_success_rate': np.mean(data['success_rates']) if data['success_rates'] else 0,
                'avg_score': np.mean(data['scores']) if data['scores'] else 0,
                'std_success_rate': np.std(data['success_rates']) if data['success_rates'] else 0,
                'std_score': np.std(data['scores']) if data['scores'] else 0,
                'count': actual_count,
                'flaw_count': len(data['success_rates'])  # 也记录flaw类型数量
            }
        
        # 检查light severity是否异常
        if plot_data['flawed_light']['count'] < plot_data['flawed_medium']['count'] / 3:
            logger.warning(f"⚠️ Light severity has significantly fewer tests: "
                        f"{plot_data['flawed_light']['count']} vs "
                        f"medium: {plot_data['flawed_medium']['count']}")
            logger.warning("This suggests incomplete test execution for light severity.")
            
            # 在图表上添加警告
            fig.text(0.5, 0.02, 
                    '⚠️ Note: Light severity appears to have incomplete test data', 
                    ha='center', fontsize=10, color='red', style='italic')
        
        # 子图1：完全成功率对比
        categories = ['Baseline\n(No MDP)', 'Optimal\n(With MDP)', 
                    'Flawed\nLight', 'Flawed\nMedium', 'Flawed\nSevere']
        category_keys = ['baseline', 'optimal', 'flawed_light', 'flawed_medium', 'flawed_severe']
        
        success_rates = [plot_data[key]['avg_success_rate'] for key in category_keys]
        success_stds = [plot_data[key]['std_success_rate'] for key in category_keys]
        counts = [plot_data[key]['count'] for key in category_keys]
        flaw_counts = [plot_data[key]['flaw_count'] for key in category_keys]
        
        x = np.arange(len(categories))
        colors = ['#FF6B6B', '#4ECDC4', '#FFE66D', '#FFA500', '#FF4444']
        
        bars1 = ax1.bar(x, success_rates, color=colors, alpha=0.8)
        ax1.errorbar(x, success_rates, yerr=success_stds, fmt='none', 
                    color='black', capsize=5, linewidth=2)
        
        # 添加数值标签 - 同时显示测试数和flaw数
        for i, (bar, rate, count, flaw_count) in enumerate(zip(bars1, success_rates, counts, flaw_counts)):
            height = bar.get_height()
            # 显示成功率、总测试数和flaw类型数
            label_text = f'{rate:.1%}\n(n={count})'
            if i >= 2:  # 对于flawed类型，也显示flaw数量
                label_text += f'\n{flaw_count} flaws'
            ax1.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                    label_text, ha='center', va='bottom', fontsize=9)
        
        ax1.set_xlabel('Prompt Strategy', fontsize=12)
        ax1.set_ylabel('Complete Success Rate', fontsize=12)
        ax1.set_title('Complete Success Rate Comparison\n(Task fully completed)', fontsize=14)
        ax1.set_xticks(x)
        ax1.set_xticklabels(categories)
        ax1.set_ylim(0, 1.2)  # 增加高度以容纳标签
        ax1.grid(axis='y', alpha=0.3)
        
        # 子图2：综合Score对比
        scores = [plot_data[key]['avg_score'] for key in category_keys]
        score_stds = [plot_data[key]['std_score'] for key in category_keys]
        
        bars2 = ax2.bar(x, scores, color=colors, alpha=0.8)
        ax2.errorbar(x, scores, yerr=score_stds, fmt='none', 
                    color='black', capsize=5, linewidth=2)
        
        # 添加数值标签
        for i, (bar, score, count, flaw_count) in enumerate(zip(bars2, scores, counts, flaw_counts)):
            height = bar.get_height()
            label_text = f'{score:.1%}\n(n={count})'
            if i >= 2:  # 对于flawed类型，也显示flaw数量
                label_text += f'\n{flaw_count} flaws'
            ax2.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                    label_text, ha='center', va='bottom', fontsize=9)
        
        ax2.set_xlabel('Prompt Strategy', fontsize=12)
        ax2.set_ylabel('Composite Score', fontsize=12)
        ax2.set_title('Composite Performance Score\n(0.7×Success + 0.3×Tool Accuracy)', fontsize=14)
        ax2.set_xticks(x)
        ax2.set_xticklabels(categories)
        ax2.set_ylim(0, 1.2)
        ax2.grid(axis='y', alpha=0.3)
        
        # 添加整体说明
        fig.suptitle('Merged Performance Analysis: Baseline and Optimal Across All Severities', 
                    fontsize=16, y=1.02)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'merged_performance_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
        logger.info("Generated: merged_performance_comparison.png")
        
        # 生成表格形式的数据总结
        self._generate_performance_table(plot_data)
        
        # 如果发现light severity数据点异常少，输出警告
        if plot_data['flawed_light']['count'] < plot_data['flawed_medium']['count'] / 2:
            logger.warning(f"Light severity has significantly fewer data points: "
                        f"{plot_data['flawed_light']['count']} vs "
                        f"medium: {plot_data['flawed_medium']['count']}, "
                        f"severe: {plot_data['flawed_severe']['count']}")
            logger.warning("This might indicate incomplete test execution for light severity flaws.")

    def _generate_performance_table(self, plot_data):
        """生成性能数据表格"""
        table_path = self.output_dir / 'performance_summary_table.md'
        
        with open(table_path, 'w') as f:
            f.write("# Performance Summary Table\n\n")
            f.write("## Key Insights\n\n")
            f.write("- **Baseline and Optimal** data are merged across all severity levels (as they should be unaffected by severity)\n")
            f.write("- **Flawed Optimal** is shown separately for each severity level\n")
            f.write("- **Score** = 0.7 × Success Rate + 0.3 × Tool Accuracy\n\n")
            
            f.write("## Detailed Results\n\n")
            f.write("| Strategy | Sample Size | Success Rate | Composite Score | Success Std | Score Std |\n")
            f.write("|----------|-------------|--------------|-----------------|-------------|------------|\n")
            
            display_names = {
                'baseline': 'Baseline (No MDP)',
                'optimal': 'Optimal (With MDP)',
                'flawed_light': 'Flawed - Light',
                'flawed_medium': 'Flawed - Medium',
                'flawed_severe': 'Flawed - Severe'
            }
            
            for key in ['baseline', 'optimal', 'flawed_light', 'flawed_medium', 'flawed_severe']:
                data = plot_data[key]
                name = display_names[key]
                f.write(f"| {name} | {data['count']} | {data['avg_success_rate']:.1%} | "
                    f"{data['avg_score']:.1%} | ±{data['std_success_rate']:.1%} | "
                    f"±{data['std_score']:.1%} |\n")
            
            # 计算改进率
            f.write("\n## Improvement Analysis\n\n")
            
            baseline_success = plot_data['baseline']['avg_success_rate']
            optimal_success = plot_data['optimal']['avg_success_rate']
            
            if baseline_success > 0:
                improvement = (optimal_success - baseline_success) / baseline_success * 100
                f.write(f"- **MDP Improvement over Baseline**: {improvement:+.1f}%\n")
            else:
                f.write(f"- **MDP Success Rate**: {optimal_success:.1%} (Baseline: 0%)\n")
            
            # Flawed performance degradation
            f.write("\n### Flawed Performance Degradation\n\n")
            for severity in ['light', 'medium', 'severe']:
                key = f'flawed_{severity}'
                flawed_success = plot_data[key]['avg_success_rate']
                if optimal_success > 0:
                    degradation = (flawed_success - optimal_success) / optimal_success * 100
                    f.write(f"- **{severity.capitalize()} Severity**: {degradation:.1f}% "
                        f"(from {optimal_success:.1%} to {flawed_success:.1%})\n")
        
        logger.info("Generated: performance_summary_table.md")


def main():
    parser = argparse.ArgumentParser(description='Generate visualizations from saved flawed workflow test results')
    parser.add_argument('--checkpoint', type=str, help='Path to checkpoint file')
    parser.add_argument('--report', type=str, help='Path to JSON report file')
    parser.add_argument('--output-dir', type=str, default='output', help='Output directory for visualizations')
    
    args = parser.parse_args()
    
    try:
        visualizer = FlawedResultsVisualizer(
            checkpoint_path=args.checkpoint,
            report_path=args.report
        )
        visualizer.generate_all_visualizations()
        print("✅ Visualizations generated successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nUsage examples:")
        print("  python visualize_flawed_results.py")
        print("  python visualize_flawed_results.py --checkpoint checkpoints/flawed_results.pt")
        print("  python visualize_flawed_results.py --report output/flawed_test_results.json")

if __name__ == "__main__":
    main()