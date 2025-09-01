#!/usr/bin/env python3
"""
WorkflowBench实验结果数据提取脚本 - 重要核心脚本

功能: 从master_database.json提取并计算5.1/5.2/5.3实验表格数据
特点: 自动排除timeout失败，确保数据准确性
用途: 生成标准化的实验结果表格用于论文和报告

作者: Claude Assistant (WorkflowBench项目)
创建时间: 2025-08-30
最后更新: 2025-08-30
版本: 1.0.0

重要性级别: ★★★★★ (核心数据处理脚本)
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class WorkflowBenchDataExtractor:
    """WorkflowBench测试数据提取器"""
    
    def __init__(self, db_path: str = "pilot_bench_cumulative_results/master_database.json"):
        """初始化数据提取器"""
        self.db_path = Path(db_path)
        self.db = self._load_database()
        
        # 模型分组
        self.baseline_models = [
            'DeepSeek-V3-0324',
            'Llama-3.3-70B-Instruct', 
            'DeepSeek-R1-0528',
            'qwen2.5-3b-instruct',
            'qwen2.5-14b-instruct',
            'qwen2.5-7b-instruct',
            'qwen2.5-32b-instruct',
            'qwen2.5-72b-instruct'
        ]
        
        self.qwen_models = [
            'qwen2.5-3b-instruct',
            'qwen2.5-7b-instruct', 
            'qwen2.5-14b-instruct',
            'qwen2.5-32b-instruct',
            'qwen2.5-72b-instruct'
        ]
        
        # 缺陷类型
        self.flawed_types = [
            'flawed_sequence_disorder',
            'flawed_tool_misuse', 
            'flawed_parameter_error',
            'flawed_missing_step',
            'flawed_redundant_operations',
            'flawed_logical_inconsistency',
            'flawed_semantic_drift'
        ]

    def _load_database(self) -> dict:
        """加载数据库"""
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        
        with open(self.db_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _calculate_timeout_excluded_stats(self, model: str, prompt_type: str = 'optimal', 
                                        difficulty: str = 'easy', tool_rate: str = '0.8') -> Optional[Dict]:
        """计算排除timeout后的模型统计数据
        
        关键逻辑:
        1. timeout_failures = min(timeout_errors, failed) - 确保不超过实际失败数
        2. effective_total = original_total - timeout_failures - 从总数中排除timeout失败
        3. success_rate = success / effective_total - 基于有效总数计算
        """
        if model not in self.db['models']:
            return None
        
        model_data = self.db['models'][model]
        
        try:
            prompt_data = model_data['by_prompt_type'][prompt_type]
            rate_data = prompt_data['by_tool_success_rate'][tool_rate]
            diff_data = rate_data['by_difficulty'][difficulty]
            
            # 聚合所有任务类型的数据
            total_tests = 0
            total_success = 0
            total_partial = 0
            total_failed = 0
            total_timeout_errors = 0
            
            task_breakdown = {}
            
            for task_type, task_data in diff_data['by_task_type'].items():
                task_total = task_data.get('total', 0)
                task_success = task_data.get('success', 0)
                task_partial = task_data.get('partial', 0)
                task_failed = task_data.get('failed', 0)
                task_timeout = task_data.get('timeout_errors', 0)
                
                # 计算该任务的timeout失败数
                task_timeout_failures = min(task_timeout, task_failed)
                task_effective_total = task_total - task_timeout_failures
                
                task_success_rate = task_success / task_effective_total * 100 if task_effective_total > 0 else 0.0
                
                task_breakdown[task_type] = {
                    'original_total': task_total,
                    'effective_total': task_effective_total,
                    'success': task_success,
                    'success_rate': task_success_rate,
                    'timeout_failures': task_timeout_failures
                }
                
                total_tests += task_total
                total_success += task_success
                total_partial += task_partial
                total_failed += task_failed
                total_timeout_errors += task_timeout
            
            # 计算模型级别的统计
            total_timeout_failures = min(total_timeout_errors, total_failed)
            effective_total = total_tests - total_timeout_failures
            non_timeout_failed = total_failed - total_timeout_failures
            
            if effective_total > 0:
                full_success = total_success - total_partial
                
                total_success_rate = total_success / effective_total * 100
                full_success_rate = full_success / effective_total * 100
                partial_success_rate = total_partial / effective_total * 100
                failure_rate = non_timeout_failed / effective_total * 100
                
                return {
                    'original_total': total_tests,
                    'effective_total': effective_total,
                    'total_success': total_success,
                    'partial_success': total_partial,
                    'full_success': full_success,
                    'non_timeout_failed': non_timeout_failed,
                    'timeout_failures': total_timeout_failures,
                    'total_success_rate': total_success_rate,
                    'full_success_rate': full_success_rate,
                    'partial_success_rate': partial_success_rate,
                    'failure_rate': failure_rate,
                    'task_breakdown': task_breakdown
                }
            
        except KeyError as e:
            print(f"Data not found for {model} - {prompt_type} - {difficulty}: {e}")
            return None

    def extract_5_1_baseline_results(self) -> Dict:
        """提取5.1基准测试结果 (optimal, easy, 0.8)"""
        print("📊 提取5.1基准测试结果 (排除timeout失败)")
        print("=" * 60)
        
        results = []
        total_stats = {
            'original_total': 0,
            'effective_total': 0,
            'total_success': 0,
            'total_partial': 0,
            'total_failed': 0,
            'timeout_failures': 0
        }
        
        for model in self.baseline_models:
            stats = self._calculate_timeout_excluded_stats(model)
            if stats:
                print(f"✅ {model}: {stats['total_success_rate']:.1f}% 成功率 "
                      f"({stats['effective_total']} 有效测试, 排除 {stats['timeout_failures']} timeout)")
                
                results.append({
                    'model': model,
                    'total_success_rate': stats['total_success_rate'],
                    'full_success_rate': stats['full_success_rate'],
                    'partial_success_rate': stats['partial_success_rate'],
                    'failure_rate': stats['failure_rate'],
                    'effective_total': stats['effective_total'],
                    'timeout_failures': stats['timeout_failures']
                })
                
                # 累计统计
                total_stats['original_total'] += stats['original_total']
                total_stats['effective_total'] += stats['effective_total']
                total_stats['total_success'] += stats['total_success']
                total_stats['total_partial'] += stats['partial_success']
                total_stats['total_failed'] += stats['non_timeout_failed']
                total_stats['timeout_failures'] += stats['timeout_failures']
            else:
                print(f"❌ {model}: 数据未找到")
        
        # 计算总体统计
        if total_stats['effective_total'] > 0:
            total_stats['overall_success_rate'] = total_stats['total_success'] / total_stats['effective_total'] * 100
            total_stats['overall_full_success_rate'] = (total_stats['total_success'] - total_stats['total_partial']) / total_stats['effective_total'] * 100
            total_stats['overall_failure_rate'] = total_stats['total_failed'] / total_stats['effective_total'] * 100
        
        return {
            'results': results,
            'summary': total_stats
        }

    def extract_5_2_qwen_scale_results(self) -> Dict:
        """提取5.2 Qwen规模效应结果 (optimal, very_easy/medium, 0.8)"""
        print("\n📊 提取5.2 Qwen规模效应结果 (排除timeout失败)")
        print("=" * 60)
        
        param_counts = {
            'qwen2.5-3b-instruct': 3,
            'qwen2.5-7b-instruct': 7,
            'qwen2.5-14b-instruct': 14,
            'qwen2.5-32b-instruct': 32,
            'qwen2.5-72b-instruct': 72
        }
        
        task_types = ['simple_task', 'basic_task', 'data_pipeline', 'api_integration', 'multi_stage_pipeline']
        
        results = {}
        
        for difficulty in ['very_easy', 'medium']:
            print(f"\n### {difficulty.upper()} 难度:")
            difficulty_results = []
            
            for model in self.qwen_models:
                stats = self._calculate_timeout_excluded_stats(model, difficulty=difficulty)
                if stats:
                    param_count = param_counts[model]
                    overall_rate = stats['total_success_rate']
                    efficiency_score = overall_rate / (param_count ** 0.5) if param_count > 0 else 0
                    
                    # 提取任务特定成功率
                    task_rates = []
                    for task_type in task_types:
                        if task_type in stats['task_breakdown']:
                            rate = stats['task_breakdown'][task_type]['success_rate']
                        else:
                            rate = 0.0
                        task_rates.append(rate)
                    
                    difficulty_results.append({
                        'model': model,
                        'param_count': param_count,
                        'task_rates': task_rates,
                        'overall_rate': overall_rate,
                        'efficiency_score': efficiency_score,
                        'timeout_failures': stats['timeout_failures']
                    })
                    
                    print(f"✅ {model}: {overall_rate:.1f}% 整体成功率 "
                          f"(排除 {stats['timeout_failures']} timeout)")
                else:
                    print(f"❌ {model}: 数据未找到")
            
            results[difficulty] = difficulty_results
        
        return results

    def extract_5_3_flawed_workflow_results(self) -> Dict:
        """提取5.3缺陷工作流适应性结果"""
        print("\n📊 提取5.3缺陷工作流适应性结果 (排除timeout失败)")
        print("=" * 60)
        
        results = {}
        
        for model in self.baseline_models:
            print(f"\n### {model}:")
            model_results = {}
            model_total_tests = 0
            model_total_corrections = 0
            model_total_timeout_failures = 0
            
            for flawed_type in self.flawed_types:
                stats = self._calculate_timeout_excluded_stats(model, prompt_type=flawed_type)
                if stats:
                    correction_rate = stats['total_success_rate']
                    timeout_failures = stats['timeout_failures']
                    
                    if timeout_failures > 0:
                        print(f"  {flawed_type}: {correction_rate:.1f}% "
                              f"({stats['total_success']}/{stats['effective_total']}) "
                              f"[排除{timeout_failures}个timeout]")
                    else:
                        print(f"  {flawed_type}: {correction_rate:.1f}% "
                              f"({stats['total_success']}/{stats['original_total']})")
                    
                    model_results[flawed_type] = correction_rate
                    model_total_tests += stats['effective_total']
                    model_total_corrections += stats['total_success']
                    model_total_timeout_failures += timeout_failures
                else:
                    model_results[flawed_type] = 0.0
                    print(f"  {flawed_type}: ❌ 数据未找到")
            
            # 计算平均适应性得分
            if model_total_tests > 0:
                avg_score = model_total_corrections / model_total_tests * 100
                model_results['average'] = avg_score
                
                if model_total_timeout_failures > 0:
                    print(f"  🔴 排除timeout失败: {model_total_timeout_failures}个")
                    print(f"  平均适应性得分: {avg_score:.1f}% "
                          f"({model_total_corrections}/{model_total_tests}) [排除timeout后]")
                else:
                    print(f"  ✅ 无timeout需排除")
                    print(f"  平均适应性得分: {avg_score:.1f}% "
                          f"({model_total_corrections}/{model_total_tests})")
            else:
                model_results['average'] = 0.0
                print(f"  平均适应性得分: 0.0%")
            
            results[model] = model_results
        
        return results

    def generate_markdown_tables(self, output_dir: str = "docs/analysis/generated/"):
        """生成markdown格式的表格文件"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 生成5.1表格
        baseline_results = self.extract_5_1_baseline_results()
        self._write_5_1_table(baseline_results, output_path / "5.1_baseline_results_auto.md")
        
        # 生成5.2表格
        qwen_results = self.extract_5_2_qwen_scale_results()
        self._write_5_2_table(qwen_results, output_path / "5.2_qwen_scale_results_auto.md")
        
        # 生成5.3表格
        flawed_results = self.extract_5_3_flawed_workflow_results()
        self._write_5_3_table(flawed_results, output_path / "5.3_flawed_workflow_results_auto.md")
        
        print(f"\n✅ 所有表格已生成到: {output_path}")

    def _write_5_1_table(self, data: Dict, output_file: Path):
        """写入5.1基准测试表格"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# 5.1 基准测试结果表 (自动生成 - 排除timeout失败)\n\n")
            f.write("| 模型名称 | 总体成功率 | 完全成功率 | 部分成功率 | 失败率 | 有效测试数 | 排除timeout数 |\n")
            f.write("|---------|-----------|-----------|-----------|-------|-----------|-------------|\n")
            
            for result in data['results']:
                f.write(f"| **{result['model']}** | "
                       f"{result['total_success_rate']:.1f}% | "
                       f"{result['full_success_rate']:.1f}% | "
                       f"{result['partial_success_rate']:.1f}% | "
                       f"{result['failure_rate']:.1f}% | "
                       f"{result['effective_total']} | "
                       f"{result['timeout_failures']} |\n")
            
            summary = data['summary']
            avg_total = len(data['results'])
            f.write(f"| **平均值** | "
                   f"{summary['overall_success_rate']:.1f}% | "
                   f"{summary['overall_full_success_rate']:.1f}% | "
                   f"{(summary['total_partial'] / summary['effective_total'] * 100):.1f}% | "
                   f"{summary['overall_failure_rate']:.1f}% | "
                   f"{summary['effective_total'] // avg_total} | "
                   f"{summary['timeout_failures'] // avg_total} |\n")

    def _write_5_2_table(self, data: Dict, output_file: Path):
        """写入5.2 Qwen规模效应表格"""
        task_names = ['简单任务成功率', '基础任务成功率', '数据管道成功率', 'API集成成功率', '多阶段管道成功率']
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# 5.2 Qwen规模效应测试表 (自动生成 - 排除timeout失败)\n\n")
            
            for difficulty, results in data.items():
                f.write(f"## {difficulty.title()}难度性能\n\n")
                f.write("| 模型规模 | 参数量 | " + " | ".join(task_names) + " | 整体成功率 | 每参数效率得分 | 排除timeout数 |\n")
                f.write("|---------|-------|" + "---|" * len(task_names) + "-----------|--------------|-------------|\n")
                
                for result in results:
                    param = result['param_count']
                    rates = [f"{rate:.1f}%" for rate in result['task_rates']]
                    f.write(f"| **Qwen2.5-{param}B-Instruct** | {param}B | " + 
                           " | ".join(rates) + f" | {result['overall_rate']:.1f}% | " +
                           f"{result['efficiency_score']:.4f} | {result['timeout_failures']} |\n")
                f.write("\n")

    def _write_5_3_table(self, data: Dict, output_file: Path):
        """写入5.3缺陷工作流适应性表格"""
        flawed_names = ['顺序错误纠正率', '工具误用纠正率', '参数错误纠正率', '缺失步骤补全率', 
                       '冗余操作识别率', '逻辑不连续修复率', '语义漂移纠正率']
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# 5.3 缺陷工作流适应性测试表 (自动生成 - 排除timeout失败)\n\n")
            f.write("| 模型名称 | " + " | ".join(flawed_names) + " | 平均适应性得分 |\n")
            f.write("|---------|" + "-------------|" * len(flawed_names) + "-------------|\n")
            
            for model, results in data.items():
                rates = []
                for flawed_type in self.flawed_types:
                    rate = results.get(flawed_type, 0.0)
                    rates.append(f"{rate:.1f}%")
                
                avg_rate = results.get('average', 0.0)
                f.write(f"| **{model}** | " + " | ".join(rates) + f" | {avg_rate:.1f}% |\n")


def main():
    """主函数"""
    print("🚀 WorkflowBench实验结果数据提取工具")
    print("=" * 60)
    
    # 检查数据库文件
    db_path = "pilot_bench_cumulative_results/master_database.json"
    if not Path(db_path).exists():
        print(f"❌ 数据库文件未找到: {db_path}")
        sys.exit(1)
    
    # 创建提取器
    extractor = WorkflowBenchDataExtractor(db_path)
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "5.1":
            results = extractor.extract_5_1_baseline_results()
            print("\n📋 5.1基准测试表格数据:")
            for result in results['results']:
                print(f"| **{result['model']}** | {result['total_success_rate']:.1f}% | "
                      f"{result['full_success_rate']:.1f}% | {result['partial_success_rate']:.1f}% | "
                      f"{result['failure_rate']:.1f}% | {result['effective_total']} | {result['timeout_failures']} |")
                      
        elif command == "5.2":
            results = extractor.extract_5_2_qwen_scale_results()
            print("\n📋 5.2 Qwen规模效应表格数据已提取")
            
        elif command == "5.3":
            results = extractor.extract_5_3_flawed_workflow_results()
            print("\n📋 5.3缺陷工作流适应性表格数据已提取")
            
        elif command == "generate":
            extractor.generate_markdown_tables()
            
        else:
            print(f"❌ 未知命令: {command}")
            print("可用命令: 5.1, 5.2, 5.3, generate")
    else:
        # 默认提取所有数据
        print("📊 提取所有实验结果...")
        extractor.extract_5_1_baseline_results()
        extractor.extract_5_2_qwen_scale_results()
        extractor.extract_5_3_flawed_workflow_results()
        
        print("\n🎯 如需生成markdown表格，使用: python extract_experiment_results.py generate")


if __name__ == "__main__":
    main()