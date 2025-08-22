#!/usr/bin/env python3
"""分析测试数据库中的异常情况"""

import json
from pathlib import Path
from typing import Dict, List, Tuple
import statistics

def load_database():
    """加载数据库"""
    db_path = Path('pilot_bench_cumulative_results/master_database.json')
    with open(db_path, 'r') as f:
        return json.load(f)

def analyze_success_rates(db: Dict) -> List[Dict]:
    """分析成功率异常的测试"""
    anomalies = []
    
    if 'models' not in db:
        return anomalies
    
    for model_name, model_data in db['models'].items():
        if 'by_prompt_type' not in model_data:
            continue
            
        for prompt_type, prompt_data in model_data['by_prompt_type'].items():
            if 'by_tool_success_rate' not in prompt_data:
                continue
                
            for rate_key, rate_data in prompt_data['by_tool_success_rate'].items():
                if 'by_difficulty' not in rate_data:
                    continue
                    
                for difficulty, diff_data in rate_data['by_difficulty'].items():
                    if 'by_task_type' not in diff_data:
                        continue
                        
                    for task_type, task_data in diff_data['by_task_type'].items():
                        # 检查异常情况
                        total = task_data.get('total', 0)
                        success_rate = task_data.get('success_rate', 0)
                        avg_execution_time = task_data.get('avg_execution_time', 0)
                        avg_turns = task_data.get('avg_turns', 0)
                        
                        # 异常条件
                        if total > 0:
                            # 1. 成功率为0（完全失败）
                            if success_rate == 0:
                                anomalies.append({
                                    'type': 'zero_success_rate',
                                    'model': model_name,
                                    'prompt_type': prompt_type,
                                    'tool_success_rate': rate_key,
                                    'difficulty': difficulty,
                                    'task_type': task_type,
                                    'total_tests': total,
                                    'success_rate': success_rate,
                                    'avg_execution_time': avg_execution_time
                                })
                            
                            # 2. 执行时间异常（可能是超时）
                            if avg_execution_time >= 180:  # 180秒是超时值
                                anomalies.append({
                                    'type': 'timeout',
                                    'model': model_name,
                                    'prompt_type': prompt_type,
                                    'tool_success_rate': rate_key,
                                    'difficulty': difficulty,
                                    'task_type': task_type,
                                    'total_tests': total,
                                    'avg_execution_time': avg_execution_time
                                })
                            
                            # 3. 平均轮数为0（可能没有执行）
                            if avg_turns == 0 and success_rate > 0:
                                anomalies.append({
                                    'type': 'zero_turns',
                                    'model': model_name,
                                    'prompt_type': prompt_type,
                                    'tool_success_rate': rate_key,
                                    'difficulty': difficulty,
                                    'task_type': task_type,
                                    'total_tests': total,
                                    'avg_turns': avg_turns
                                })
                            
                            # 4. 异常高的错误率
                            for error_type in ['tool_selection_error_rate', 'sequence_error_rate', 
                                             'dependency_error_rate', 'timeout_error_rate']:
                                error_rate = task_data.get(error_type, 0)
                                if error_rate > 0.8:  # 80%以上的错误率
                                    anomalies.append({
                                        'type': f'high_{error_type}',
                                        'model': model_name,
                                        'prompt_type': prompt_type,
                                        'tool_success_rate': rate_key,
                                        'difficulty': difficulty,
                                        'task_type': task_type,
                                        'error_type': error_type,
                                        'error_rate': error_rate
                                    })
    
    return anomalies

def analyze_model_performance(db: Dict) -> Dict:
    """分析每个模型的整体表现"""
    model_stats = {}
    
    if 'models' not in db:
        return model_stats
    
    for model_name, model_data in db['models'].items():
        stats = {
            'total_tests': 0,
            'total_success': 0,
            'prompt_types': set(),
            'difficulties': set(),
            'task_types': set(),
            'avg_execution_times': [],
            'success_rates': []
        }
        
        if 'by_prompt_type' in model_data:
            for prompt_type, prompt_data in model_data['by_prompt_type'].items():
                stats['prompt_types'].add(prompt_type)
                
                if 'by_tool_success_rate' in prompt_data:
                    for rate_data in prompt_data['by_tool_success_rate'].values():
                        if 'by_difficulty' in rate_data:
                            for difficulty, diff_data in rate_data['by_difficulty'].items():
                                stats['difficulties'].add(difficulty)
                                
                                if 'by_task_type' in diff_data:
                                    for task_type, task_data in diff_data['by_task_type'].items():
                                        stats['task_types'].add(task_type)
                                        
                                        total = task_data.get('total', 0)
                                        success = task_data.get('success', 0)
                                        success_rate = task_data.get('success_rate', 0)
                                        avg_time = task_data.get('avg_execution_time', 0)
                                        
                                        stats['total_tests'] += total
                                        stats['total_success'] += success
                                        
                                        if total > 0:
                                            stats['success_rates'].append(success_rate)
                                            stats['avg_execution_times'].append(avg_time)
        
        # 计算统计信息
        if stats['total_tests'] > 0:
            stats['overall_success_rate'] = stats['total_success'] / stats['total_tests']
        else:
            stats['overall_success_rate'] = 0
        
        if stats['avg_execution_times']:
            stats['mean_execution_time'] = statistics.mean(stats['avg_execution_times'])
            stats['median_execution_time'] = statistics.median(stats['avg_execution_times'])
            stats['max_execution_time'] = max(stats['avg_execution_times'])
            stats['min_execution_time'] = min(stats['avg_execution_times'])
        
        # 转换集合为列表以便JSON序列化
        stats['prompt_types'] = list(stats['prompt_types'])
        stats['difficulties'] = list(stats['difficulties'])
        stats['task_types'] = list(stats['task_types'])
        
        model_stats[model_name] = stats
    
    return model_stats

def find_incomplete_tests(db: Dict) -> List[Dict]:
    """找出可能未完成的测试配置"""
    incomplete = []
    
    # 定义预期的配置
    expected_prompt_types = ['baseline', 'flawed', 'optimal', 'cot']
    expected_difficulties = ['easy', 'medium', 'hard']
    expected_task_types = ['simple_task', 'basic_task', 'multi_stage_pipeline', 
                          'data_pipeline', 'api_integration']
    
    if 'models' not in db:
        return incomplete
    
    for model_name, model_data in db['models'].items():
        if 'by_prompt_type' not in model_data:
            continue
        
        # 检查是否有预期的prompt_type
        actual_prompt_types = set(model_data['by_prompt_type'].keys())
        
        # 收集所有的difficulty和task_type
        actual_difficulties = set()
        actual_task_types = set()
        
        for prompt_data in model_data['by_prompt_type'].values():
            if 'by_tool_success_rate' in prompt_data:
                for rate_data in prompt_data['by_tool_success_rate'].values():
                    if 'by_difficulty' in rate_data:
                        actual_difficulties.update(rate_data['by_difficulty'].keys())
                        
                        for diff_data in rate_data['by_difficulty'].values():
                            if 'by_task_type' in diff_data:
                                actual_task_types.update(diff_data['by_task_type'].keys())
        
        # 找出缺失的配置
        missing_prompt_types = [pt for pt in expected_prompt_types 
                               if pt not in actual_prompt_types and 
                               not pt.startswith('flawed_')]
        
        if missing_prompt_types or len(actual_difficulties) < 2 or len(actual_task_types) < 3:
            incomplete.append({
                'model': model_name,
                'actual_prompt_types': list(actual_prompt_types),
                'missing_prompt_types': missing_prompt_types,
                'actual_difficulties': list(actual_difficulties),
                'actual_task_types': list(actual_task_types),
                'coverage': {
                    'prompt_types': len(actual_prompt_types),
                    'difficulties': len(actual_difficulties),
                    'task_types': len(actual_task_types)
                }
            })
    
    return incomplete

def main():
    """主分析函数"""
    print("="*70)
    print("测试数据库异常分析")
    print("="*70)
    
    # 加载数据库
    db = load_database()
    
    # 1. 分析异常
    print("\n1. 检查异常情况...")
    anomalies = analyze_success_rates(db)
    
    if anomalies:
        print(f"   发现 {len(anomalies)} 个异常")
        
        # 按类型分组
        anomaly_types = {}
        for anomaly in anomalies:
            atype = anomaly['type']
            if atype not in anomaly_types:
                anomaly_types[atype] = []
            anomaly_types[atype].append(anomaly)
        
        print("\n   异常类型分布:")
        for atype, items in anomaly_types.items():
            print(f"   - {atype}: {len(items)} 个")
        
        # 显示详细信息
        if 'zero_success_rate' in anomaly_types:
            print("\n   ⚠️ 完全失败的测试（成功率=0）:")
            for item in anomaly_types['zero_success_rate'][:5]:  # 只显示前5个
                print(f"      {item['model']} / {item['prompt_type']} / {item['task_type']} "
                      f"({item['total_tests']} tests)")
        
        if 'timeout' in anomaly_types:
            print("\n   ⚠️ 超时的测试（执行时间>=180s）:")
            for item in anomaly_types['timeout'][:5]:
                print(f"      {item['model']} / {item['prompt_type']} / {item['task_type']} "
                      f"(avg: {item['avg_execution_time']:.1f}s)")
    else:
        print("   ✅ 没有发现明显异常")
    
    # 2. 分析模型性能
    print("\n2. 模型性能分析...")
    model_stats = analyze_model_performance(db)
    
    if model_stats:
        print(f"   共分析 {len(model_stats)} 个模型")
        
        # 按成功率排序
        sorted_models = sorted(model_stats.items(), 
                             key=lambda x: x[1]['overall_success_rate'], 
                             reverse=True)
        
        print("\n   模型排名（按成功率）:")
        for i, (model_name, stats) in enumerate(sorted_models[:10], 1):
            success_rate = stats['overall_success_rate']
            total_tests = stats['total_tests']
            avg_time = stats.get('mean_execution_time', 0)
            
            print(f"   {i:2}. {model_name:<30} "
                  f"成功率: {success_rate:6.2%} "
                  f"测试数: {total_tests:4} "
                  f"平均时间: {avg_time:6.2f}s")
        
        # 找出表现最差的模型
        if sorted_models:
            worst_models = [m for m, s in sorted_models if s['overall_success_rate'] < 0.3]
            if worst_models:
                print(f"\n   ⚠️ 表现较差的模型（成功率<30%）: {', '.join(worst_models[:5])}")
    
    # 3. 检查测试完整性
    print("\n3. 测试覆盖度分析...")
    incomplete = find_incomplete_tests(db)
    
    if incomplete:
        print(f"   发现 {len(incomplete)} 个模型的测试可能不完整")
        
        for item in incomplete[:5]:
            print(f"\n   {item['model']}:")
            print(f"      Prompt types: {item['coverage']['prompt_types']} 种")
            print(f"      Difficulties: {item['coverage']['difficulties']} 种")
            print(f"      Task types: {item['coverage']['task_types']} 种")
            
            if item['missing_prompt_types']:
                print(f"      缺失的prompt: {', '.join(item['missing_prompt_types'])}")
    else:
        print("   ✅ 所有模型的测试覆盖度正常")
    
    # 4. 统计摘要
    print("\n4. 数据库统计摘要:")
    total_models = len(db.get('models', {}))
    total_tests = sum(model_stats.get(m, {}).get('total_tests', 0) 
                     for m in model_stats)
    
    print(f"   - 总模型数: {total_models}")
    print(f"   - 总测试数: {total_tests}")
    
    if db.get('summary'):
        summary = db['summary']
        print(f"   - 总成功数: {summary.get('total_success', 0)}")
        print(f"   - 总失败数: {summary.get('total_failure', 0)}")
        print(f"   - 最后更新: {db.get('last_updated', 'Unknown')}")
    
    # 保存详细报告
    report = {
        'anomalies': anomalies,
        'model_stats': model_stats,
        'incomplete_tests': incomplete,
        'summary': {
            'total_anomalies': len(anomalies),
            'total_models': total_models,
            'total_tests': total_tests
        }
    }
    
    report_file = Path('test_anomaly_report.json')
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n详细报告已保存到: {report_file}")
    
    # 最终建议
    print("\n" + "="*70)
    print("建议:")
    
    if anomalies:
        if 'zero_success_rate' in anomaly_types:
            print("1. 重新运行成功率为0的测试，可能是配置问题")
        if 'timeout' in anomaly_types:
            print("2. 检查超时的测试，可能需要增加超时时间或优化代码")
        if any('high_' in a for a in anomaly_types):
            print("3. 分析高错误率的测试，了解失败原因")
    
    if incomplete:
        print("4. 补充缺失的测试配置，确保完整的测试覆盖")
    
    if not anomalies and not incomplete:
        print("✅ 数据库状态良好，没有明显问题！")
    
    print("="*70)

if __name__ == "__main__":
    main()