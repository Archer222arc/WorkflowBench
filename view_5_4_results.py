#!/usr/bin/env python3
"""
查看5.4工具可靠性敏感性测试结果
从数据库提取并分析不同tool_success_rate下的表现
"""

import json
from pathlib import Path
from typing import Dict, List
import numpy as np

def load_database() -> Dict:
    """加载数据库"""
    db_path = Path("pilot_bench_cumulative_results/master_database.json")
    if not db_path.exists():
        print(f"❌ 数据库不存在: {db_path}")
        return {}
    
    with open(db_path, 'r') as f:
        return json.load(f)

def extract_5_4_data(db: Dict) -> Dict:
    """提取5.4测试数据"""
    results = {}
    
    # 要分析的模型
    models = [
        "qwen2.5-72b-instruct",
        "qwen2.5-32b-instruct", 
        "qwen2.5-14b-instruct",
        "qwen2.5-7b-instruct",
        "qwen2.5-3b-instruct",
        "DeepSeek-V3-0324",
        "DeepSeek-R1-0528",
        "Llama-3.3-70B-Instruct"
    ]
    
    # 工具成功率配置
    tool_rates = ["0.9", "0.8", "0.7", "0.6"]
    
    for model in models:
        if model not in db.get('models', {}):
            continue
            
        model_data = db['models'][model]
        results[model] = {}
        
        # 查找optimal prompt下的数据
        if 'by_prompt_type' in model_data and 'optimal' in model_data['by_prompt_type']:
            optimal_data = model_data['by_prompt_type']['optimal']
            
            if 'by_tool_success_rate' in optimal_data:
                for rate in tool_rates:
                    if rate in optimal_data['by_tool_success_rate']:
                        rate_data = optimal_data['by_tool_success_rate'][rate]
                        
                        # 查找easy难度下的数据
                        if 'by_difficulty' in rate_data and 'easy' in rate_data['by_difficulty']:
                            easy_data = rate_data['by_difficulty']['easy']
                            
                            # 汇总所有任务类型
                            total_tests = 0
                            successful = 0
                            task_results = {}
                            
                            if 'by_task_type' in easy_data:
                                for task_type, task_data in easy_data['by_task_type'].items():
                                    total = task_data.get('total', 0)
                                    success = task_data.get('successful', 0)
                                    
                                    if total > 0:
                                        total_tests += total
                                        successful += success
                                        task_results[task_type] = {
                                            'total': total,
                                            'successful': success,
                                            'rate': success / total if total > 0 else 0
                                        }
                            
                            if total_tests > 0:
                                results[model][float(rate)] = {
                                    'total': total_tests,
                                    'successful': successful,
                                    'success_rate': successful / total_tests,
                                    'tasks': task_results
                                }
    
    return results

def calculate_sensitivity(performance_dict: Dict[float, Dict]) -> Dict:
    """计算敏感性指标"""
    rates = sorted([r for r in performance_dict.keys() if performance_dict[r]['total'] > 0])
    
    if len(rates) < 2:
        return {
            'sensitivity': None,
            'robustness': None,
            'degradation': None
        }
    
    performances = [performance_dict[r]['success_rate'] for r in rates]
    
    # 计算敏感性系数（标准差/平均值）
    if np.mean(performances) > 0:
        sensitivity = np.std(performances) / np.mean(performances)
    else:
        sensitivity = None
    
    # 计算鲁棒性得分
    if sensitivity is not None:
        robustness = np.mean(performances) * 0.6 + (1 - min(sensitivity, 1)) * 0.4
    else:
        robustness = None
    
    # 计算退化率
    degradation = {}
    for i in range(len(rates) - 1):
        key = f"{rates[i]:.0%}→{rates[i+1]:.0%}"
        if performances[i] > 0:
            degradation[key] = (performances[i] - performances[i+1]) / performances[i]
        else:
            degradation[key] = None
    
    return {
        'sensitivity': sensitivity,
        'robustness': robustness,
        'degradation': degradation,
        'mean_performance': np.mean(performances)
    }

def print_results_table(results: Dict):
    """打印结果表格"""
    
    print("\n" + "=" * 100)
    print("5.4 工具可靠性敏感性测试结果")
    print("=" * 100)
    
    # 主表格
    print("\n📊 性能汇总表")
    print("-" * 100)
    print(f"{'模型名称':<30} {'90%':>10} {'80%':>10} {'70%':>10} {'60%':>10} {'敏感系数':>10} {'鲁棒性':>10}")
    print("-" * 100)
    
    for model, data in results.items():
        row = [model[:28]]
        
        for rate in [0.9, 0.8, 0.7, 0.6]:
            if rate in data and data[rate]['total'] > 0:
                row.append(f"{data[rate]['success_rate']:.1%}")
            else:
                row.append("-")
        
        # 计算敏感性指标
        metrics = calculate_sensitivity(data)
        
        if metrics['sensitivity'] is not None:
            row.append(f"{metrics['sensitivity']:.3f}")
        else:
            row.append("-")
            
        if metrics['robustness'] is not None:
            row.append(f"{metrics['robustness']:.1%}")
        else:
            row.append("-")
        
        print(f"{row[0]:<30} {row[1]:>10} {row[2]:>10} {row[3]:>10} {row[4]:>10} {row[5]:>10} {row[6]:>10}")
    
    print("-" * 100)
    
    # 详细任务分解（每个工具成功率）
    for rate in [0.9, 0.8, 0.7, 0.6]:
        has_data = any(rate in data and data[rate]['total'] > 0 for data in results.values())
        
        if has_data:
            print(f"\n📋 工具成功率 {rate:.0%} 详细分解")
            print("-" * 100)
            print(f"{'模型名称':<30} {'简单任务':>12} {'基础任务':>12} {'数据管道':>12} {'API集成':>12} {'多阶段':>12}")
            print("-" * 100)
            
            for model, data in results.items():
                if rate in data and data[rate]['total'] > 0:
                    row = [model[:28]]
                    
                    task_mapping = {
                        'simple_task': '简单任务',
                        'basic_task': '基础任务',
                        'data_pipeline': '数据管道',
                        'api_integration': 'API集成',
                        'multi_stage_pipeline': '多阶段'
                    }
                    
                    for task_key in ['simple_task', 'basic_task', 'data_pipeline', 
                                    'api_integration', 'multi_stage_pipeline']:
                        if task_key in data[rate]['tasks']:
                            task_data = data[rate]['tasks'][task_key]
                            rate_str = f"{task_data['rate']:.1%}"
                            count_str = f"({task_data['successful']}/{task_data['total']})"
                            row.append(rate_str)
                        else:
                            row.append("-")
                    
                    print(f"{row[0]:<30} {row[1]:>12} {row[2]:>12} {row[3]:>12} {row[4]:>12} {row[5]:>12}")
            
            print("-" * 100)
    
    # 性能退化分析
    print("\n📉 性能退化分析")
    print("-" * 100)
    print(f"{'模型名称':<30} {'90%→80%':>15} {'80%→70%':>15} {'70%→60%':>15} {'稳定性评级':>15}")
    print("-" * 100)
    
    for model, data in results.items():
        metrics = calculate_sensitivity(data)
        row = [model[:28]]
        
        if metrics['degradation']:
            for key in ['90%→80%', '80%→70%', '70%→60%']:
                if key in metrics['degradation'] and metrics['degradation'][key] is not None:
                    deg = metrics['degradation'][key]
                    row.append(f"{deg:.1%}")
                else:
                    row.append("-")
            
            # 评级
            avg_deg = [d for d in metrics['degradation'].values() if d is not None]
            if avg_deg:
                avg = np.mean(avg_deg)
                if avg < 0.1:
                    rating = "A级"
                elif avg < 0.2:
                    rating = "B级"
                elif avg < 0.3:
                    rating = "C级"
                else:
                    rating = "D级"
            else:
                rating = "-"
            row.append(rating)
        else:
            row.extend(["-", "-", "-", "-"])
        
        print(f"{row[0]:<30} {row[1]:>15} {row[2]:>15} {row[3]:>15} {row[4]:>15}")
    
    print("-" * 100)

def print_summary_stats(results: Dict):
    """打印汇总统计"""
    print("\n📊 统计汇总")
    print("-" * 50)
    
    # 统计数据完整性
    total_models = len(results)
    models_with_data = {}
    
    for rate in [0.9, 0.8, 0.7, 0.6]:
        count = sum(1 for data in results.values() if rate in data and data[rate]['total'] > 0)
        models_with_data[rate] = count
    
    print(f"总模型数: {total_models}")
    for rate, count in models_with_data.items():
        print(f"  {rate:.0%}工具成功率: {count}个模型有数据")
    
    # 找出最鲁棒的模型
    best_robustness = None
    best_model = None
    
    for model, data in results.items():
        metrics = calculate_sensitivity(data)
        if metrics['robustness'] is not None:
            if best_robustness is None or metrics['robustness'] > best_robustness:
                best_robustness = metrics['robustness']
                best_model = model
    
    if best_model:
        print(f"\n🏆 最鲁棒模型: {best_model}")
        print(f"   鲁棒性得分: {best_robustness:.1%}")
    
    # 找出最敏感的模型
    most_sensitive = None
    sensitive_model = None
    
    for model, data in results.items():
        metrics = calculate_sensitivity(data)
        if metrics['sensitivity'] is not None:
            if most_sensitive is None or metrics['sensitivity'] > most_sensitive:
                most_sensitive = metrics['sensitivity']
                sensitive_model = model
    
    if sensitive_model:
        print(f"\n⚠️ 最敏感模型: {sensitive_model}")
        print(f"   敏感系数: {most_sensitive:.3f}")

def main():
    """主函数"""
    print("加载数据库...")
    db = load_database()
    
    if not db:
        return
    
    print("提取5.4测试数据...")
    results = extract_5_4_data(db)
    
    if not results:
        print("❌ 未找到5.4测试数据")
        return
    
    # 打印结果
    print_results_table(results)
    print_summary_stats(results)
    
    print("\n" + "=" * 100)
    print("提示：")
    print("- 敏感系数 < 0.2: 低敏感性（稳定）")
    print("- 敏感系数 0.2-0.4: 中等敏感性")
    print("- 敏感系数 > 0.4: 高敏感性（易受影响）")
    print("- 鲁棒性得分综合考虑性能和稳定性")
    print("=" * 100)

if __name__ == "__main__":
    main()