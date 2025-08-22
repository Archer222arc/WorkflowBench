#!/usr/bin/env python3
"""详细分析特定的异常情况"""

import json
from pathlib import Path
from collections import defaultdict

def analyze_zero_success_models():
    """详细分析成功率为0的模型"""
    
    db_path = Path('pilot_bench_cumulative_results/master_database.json')
    with open(db_path, 'r') as f:
        db = json.load(f)
    
    print("="*70)
    print("成功率为0的测试详细分析")
    print("="*70)
    
    # 特别关注的模型
    zero_success_models = ['qwen2.5-72b-instruct', 'llama-4-scout-17b']
    
    for model_name in zero_success_models:
        if model_name not in db.get('models', {}):
            continue
            
        print(f"\n### {model_name}")
        model_data = db['models'][model_name]
        
        # 统计错误类型
        error_stats = defaultdict(int)
        total_tests = 0
        total_errors = 0
        
        if 'by_prompt_type' in model_data:
            for prompt_type, prompt_data in model_data['by_prompt_type'].items():
                print(f"\n  Prompt Type: {prompt_type}")
                
                if 'by_tool_success_rate' in prompt_data:
                    for rate_key, rate_data in prompt_data['by_tool_success_rate'].items():
                        if 'by_difficulty' in rate_data:
                            for difficulty, diff_data in rate_data['by_difficulty'].items():
                                if 'by_task_type' in diff_data:
                                    for task_type, task_data in diff_data['by_task_type'].items():
                                        total = task_data.get('total', 0)
                                        success_rate = task_data.get('success_rate', 0)
                                        
                                        if total > 0:
                                            total_tests += total
                                            
                                            # 收集错误信息
                                            errors = task_data.get('total_errors', 0)
                                            total_errors += errors
                                            
                                            if success_rate == 0:
                                                print(f"    - {difficulty}/{task_type}: "
                                                      f"{total} tests, ALL FAILED")
                                                
                                                # 分析错误类型
                                                for error_field in ['tool_call_format_errors', 
                                                                  'timeout_errors',
                                                                  'dependency_errors',
                                                                  'parameter_config_errors',
                                                                  'tool_selection_errors',
                                                                  'sequence_order_errors',
                                                                  'max_turns_errors',
                                                                  'other_errors']:
                                                    error_count = task_data.get(error_field, 0)
                                                    if error_count > 0:
                                                        error_stats[error_field] += error_count
                                                        print(f"        {error_field}: {error_count}")
        
        # 总结
        if total_tests > 0:
            print(f"\n  总计: {total_tests} 个测试, {total_errors} 个错误")
            print(f"  错误分布:")
            for error_type, count in sorted(error_stats.items(), key=lambda x: x[1], reverse=True):
                print(f"    - {error_type}: {count} ({count/total_errors*100:.1f}%)")

def analyze_partial_success_models():
    """分析部分成功的模型，找出规律"""
    
    db_path = Path('pilot_bench_cumulative_results/master_database.json')
    with open(db_path, 'r') as f:
        db = json.load(f)
    
    print("\n" + "="*70)
    print("部分成功模型的规律分析")
    print("="*70)
    
    # 分析表现中等的模型
    medium_models = ['qwen2.5-14b-instruct', 'qwen2.5-7b-instruct', 'qwen2.5-3b-instruct']
    
    for model_name in medium_models:
        if model_name not in db.get('models', {}):
            continue
            
        print(f"\n### {model_name}")
        model_data = db['models'][model_name]
        
        # 按任务类型统计成功率
        task_type_stats = defaultdict(lambda: {'total': 0, 'success': 0})
        
        if 'by_prompt_type' in model_data:
            for prompt_data in model_data['by_prompt_type'].values():
                if 'by_tool_success_rate' in prompt_data:
                    for rate_data in prompt_data['by_tool_success_rate'].values():
                        if 'by_difficulty' in rate_data:
                            for diff_data in rate_data['by_difficulty'].values():
                                if 'by_task_type' in diff_data:
                                    for task_type, task_data in diff_data['by_task_type'].items():
                                        total = task_data.get('total', 0)
                                        success = task_data.get('success', 0)
                                        
                                        task_type_stats[task_type]['total'] += total
                                        task_type_stats[task_type]['success'] += success
        
        # 显示按任务类型的成功率
        print(f"  按任务类型的成功率:")
        for task_type, stats in sorted(task_type_stats.items()):
            if stats['total'] > 0:
                success_rate = stats['success'] / stats['total']
                print(f"    - {task_type:<25}: {success_rate:6.2%} "
                      f"({stats['success']}/{stats['total']})")

def check_flawed_tests():
    """专门检查flawed测试的情况"""
    
    db_path = Path('pilot_bench_cumulative_results/master_database.json')
    with open(db_path, 'r') as f:
        db = json.load(f)
    
    print("\n" + "="*70)
    print("Flawed测试专项分析")
    print("="*70)
    
    flawed_stats = defaultdict(lambda: {'models': [], 'total_tests': 0, 'total_success': 0})
    
    for model_name, model_data in db.get('models', {}).items():
        if 'by_prompt_type' in model_data:
            for prompt_type, prompt_data in model_data['by_prompt_type'].items():
                if prompt_type.startswith('flawed'):
                    # 提取缺陷类型
                    if prompt_type == 'flawed':
                        flaw_type = 'generic'
                    else:
                        flaw_type = prompt_type.replace('flawed_', '')
                    
                    # 统计该缺陷类型的测试
                    if 'summary' in prompt_data:
                        total = prompt_data['summary'].get('total', 0)
                        success = prompt_data['summary'].get('success', 0)
                        
                        if total > 0:
                            flawed_stats[flaw_type]['models'].append(model_name)
                            flawed_stats[flaw_type]['total_tests'] += total
                            flawed_stats[flaw_type]['total_success'] += success
    
    # 显示结果
    print("\n  缺陷类型测试覆盖:")
    for flaw_type, stats in sorted(flawed_stats.items()):
        if stats['total_tests'] > 0:
            success_rate = stats['total_success'] / stats['total_tests']
            print(f"\n  {flaw_type}:")
            print(f"    - 测试模型数: {len(stats['models'])}")
            print(f"    - 总测试数: {stats['total_tests']}")
            print(f"    - 成功率: {success_rate:.2%}")
            print(f"    - 测试的模型: {', '.join(stats['models'][:3])}...")

def analyze_deepseek_models():
    """专门分析DeepSeek模型的表现"""
    
    db_path = Path('pilot_bench_cumulative_results/master_database.json')
    with open(db_path, 'r') as f:
        db = json.load(f)
    
    print("\n" + "="*70)
    print("DeepSeek模型专项分析")
    print("="*70)
    
    deepseek_models = ['DeepSeek-V3-0324', 'DeepSeek-R1-0528']
    
    for model_name in deepseek_models:
        if model_name not in db.get('models', {}):
            continue
            
        print(f"\n### {model_name}")
        model_data = db['models'][model_name]
        
        # 获取整体统计
        overall_stats = model_data.get('overall_stats', {})
        print(f"  总体成功率: {overall_stats.get('success_rate', 0):.2%}")
        print(f"  总测试数: {overall_stats.get('total', 0)}")
        
        # 分析不同prompt类型的表现
        print(f"\n  按Prompt类型分析:")
        if 'by_prompt_type' in model_data:
            for prompt_type in sorted(model_data['by_prompt_type'].keys()):
                prompt_data = model_data['by_prompt_type'][prompt_type]
                if 'summary' in prompt_data:
                    summary = prompt_data['summary']
                    total = summary.get('total', 0)
                    success_rate = summary.get('success_rate', 0)
                    
                    if total > 0:
                        print(f"    - {prompt_type:<30}: {success_rate:6.2%} ({total} tests)")

def main():
    """运行所有分析"""
    
    # 1. 分析成功率为0的模型
    analyze_zero_success_models()
    
    # 2. 分析部分成功的模型
    analyze_partial_success_models()
    
    # 3. 检查flawed测试
    check_flawed_tests()
    
    # 4. 分析DeepSeek模型
    analyze_deepseek_models()
    
    print("\n" + "="*70)
    print("分析完成")
    print("="*70)

if __name__ == "__main__":
    main()