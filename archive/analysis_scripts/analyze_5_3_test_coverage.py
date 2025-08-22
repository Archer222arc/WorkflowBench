#!/usr/bin/env python3
"""
分析5.3缺陷测试的覆盖情况
"""

import json
from pathlib import Path
from collections import defaultdict

def analyze_test_coverage():
    db_path = Path('pilot_bench_cumulative_results/master_database.json')
    
    with open(db_path, 'r') as f:
        db = json.load(f)
    
    print(f"数据库最后更新: {db.get('last_updated', '未知')}\n")
    
    # 定义模型映射
    model_mapping = {
        'DeepSeek-V3-0324': 'DeepSeek-V3-0324',
        'deepseek-v3-0324-2': 'DeepSeek-V3-0324',
        'deepseek-v3-0324-3': 'DeepSeek-V3-0324',
        'DeepSeek-R1-0528': 'DeepSeek-R1-0528',
        'deepseek-r1-0528-2': 'DeepSeek-R1-0528',
        'deepseek-r1-0528-3': 'DeepSeek-R1-0528',
        'Llama-3.3-70B-Instruct': 'Llama-3.3-70B-Instruct',
        'llama-3.3-70b-instruct-2': 'Llama-3.3-70B-Instruct',
        'llama-3.3-70b-instruct-3': 'Llama-3.3-70B-Instruct',
    }
    
    expected_models = [
        'DeepSeek-V3-0324', 'DeepSeek-R1-0528',
        'qwen2.5-72b-instruct', 'qwen2.5-32b-instruct', 'qwen2.5-14b-instruct',
        'qwen2.5-7b-instruct', 'qwen2.5-3b-instruct',
        'Llama-3.3-70B-Instruct'
    ]
    
    flaw_types = [
        'flawed_sequence_disorder',
        'flawed_tool_misuse', 
        'flawed_parameter_error',
        'flawed_missing_step',
        'flawed_redundant_operations',
        'flawed_logical_inconsistency',
        'flawed_semantic_drift'
    ]
    
    print("=== 5.3 缺陷测试覆盖分析 ===\n")
    print("预期: 8个模型 × 7种缺陷 × 20个实例 = 1,120个测试\n")
    
    # 合并统计
    merged_coverage = defaultdict(lambda: defaultdict(int))
    
    # 先统计原始数据
    print("原始实例数据:")
    for model_name, model_data in db['models'].items():
        if 'by_prompt_type' not in model_data:
            continue
        
        test_count = 0
        flaw_count = 0
        for flaw in flaw_types:
            if flaw in model_data['by_prompt_type']:
                flaw_count += 1
                # 计算测试数
                flaw_data = model_data['by_prompt_type'][flaw]
                if 'by_tool_success_rate' in flaw_data and '0.8' in flaw_data['by_tool_success_rate']:
                    rate_data = flaw_data['by_tool_success_rate']['0.8']
                    if 'by_difficulty' in rate_data and 'easy' in rate_data['by_difficulty']:
                        diff_data = rate_data['by_difficulty']['easy']
                        if 'by_task_type' in diff_data:
                            for task_data in diff_data['by_task_type'].values():
                                test_count += task_data.get('total', 0)
        
        if test_count > 0:
            print(f"  {model_name}: {flaw_count}/7 缺陷, {test_count} 测试")
            
            # 合并到主模型
            main_model = model_mapping.get(model_name, model_name)
            for flaw in flaw_types:
                if flaw in model_data['by_prompt_type']:
                    merged_coverage[main_model][flaw] = 1
    
    print("\n合并后的模型覆盖:")
    total_tests = 0
    missing_configs = []
    
    for model in expected_models:
        if model in merged_coverage:
            covered = len(merged_coverage[model])
            print(f"  ✅ {model}: {covered}/7 缺陷类型")
            
            # 列出缺失的缺陷类型
            missing = []
            for flaw in flaw_types:
                if flaw not in merged_coverage[model]:
                    missing.append(flaw.replace('flawed_', ''))
                    missing_configs.append(f"{model}:{flaw}")
            
            if missing:
                print(f"     缺失: {', '.join(missing)}")
        else:
            print(f"  ❌ {model}: 0/7 缺陷类型 (完全缺失)")
            for flaw in flaw_types:
                missing_configs.append(f"{model}:{flaw}")
    
    print(f"\n缺失的测试配置数: {len(missing_configs)}")
    print(f"缺失的测试数: {len(missing_configs) * 20} (每个配置20个实例)")
    
    # 诊断并发写入问题
    print("\n=== 并发写入问题诊断 ===")
    print("可能的原因:")
    print("1. 多个分片同时完成并写入数据库")
    print("2. 后写入的覆盖了先写入的数据")
    print("3. 特别是Qwen系列使用了相同的实例池")
    
    print("\n建议解决方案:")
    print("1. 实现文件锁机制防止并发写入")
    print("2. 使用原子写入操作")
    print("3. 或者让每个分片写入独立文件，最后合并")

if __name__ == "__main__":
    analyze_test_coverage()