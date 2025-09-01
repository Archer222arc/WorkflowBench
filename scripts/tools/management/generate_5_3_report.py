#!/usr/bin/env python3
"""
生成5.3缺陷工作流适应性测试报告
"""
import json
from pathlib import Path
from typing import Dict, List, Tuple

def get_flawed_stats(model_data: Dict, flaw_type: str) -> Tuple[float, int]:
    """获取特定缺陷类型的统计数据"""
    if 'by_prompt_type' not in model_data or flaw_type not in model_data['by_prompt_type']:
        return 0.0, 0
    
    flaw_data = model_data['by_prompt_type'][flaw_type]
    
    # 获取默认配置数据 (tool_success_rate=0.8, difficulty=easy)
    if 'by_tool_success_rate' not in flaw_data or '0.8' not in flaw_data['by_tool_success_rate']:
        return 0.0, 0
    
    rate_data = flaw_data['by_tool_success_rate']['0.8']
    
    if 'by_difficulty' not in rate_data or 'easy' not in rate_data['by_difficulty']:
        return 0.0, 0
    
    diff_data = rate_data['by_difficulty']['easy']
    
    # 汇总所有task_type的数据
    total_tests = 0
    total_success = 0
    
    if 'by_task_type' in diff_data:
        for task_data in diff_data['by_task_type'].values():
            total_tests += task_data.get('total', 0)
            # 注意：字段名是'success'而不是'successful'
            total_success += task_data.get('success', 0)
    
    # 计算成功率
    success_rate = (total_success / total_tests * 100) if total_tests > 0 else 0.0
    
    return success_rate, total_tests

def main():
    # 读取数据库
    db_path = Path('pilot_bench_cumulative_results/master_database.json')
    with open(db_path, 'r') as f:
        db = json.load(f)
    
    # 模型列表
    models = [
        'DeepSeek-V3-0324',
        'DeepSeek-R1-0528', 
        'qwen2.5-72b-instruct',
        'qwen2.5-32b-instruct',
        'qwen2.5-14b-instruct',
        'qwen2.5-7b-instruct',
        'qwen2.5-3b-instruct',
        'Llama-3.3-70B-Instruct'
    ]
    
    # 缺陷类型
    flaw_types = [
        ('flawed_sequence_disorder', '顺序错误'),
        ('flawed_tool_misuse', '工具误用'),
        ('flawed_parameter_error', '参数错误'),
        ('flawed_missing_step', '缺失步骤'),
        ('flawed_redundant_operations', '冗余操作'),
        ('flawed_logical_inconsistency', '逻辑不连续'),
        ('flawed_semantic_drift', '语义漂移')
    ]
    
    print("=" * 80)
    print("5.3 缺陷工作流适应性测试表 - 开源模型")
    print("=" * 80)
    print()
    
    # 打印表头
    print("| 模型名称 | 顺序错误 | 工具误用 | 参数错误 | 缺失步骤 | 冗余操作 | 逻辑不连续 | 语义漂移 | 平均 |")
    print("|----------|----------|----------|----------|----------|----------|-----------|----------|------|")
    
    # 统计每个模型
    for model in models:
        if model not in db['models']:
            print(f"| {model[:20]:20} | - | - | - | - | - | - | - | - |")
            continue
        
        model_data = db['models'][model]
        row = [f"{model[:20]:20}"]
        
        rates = []
        total_tests = 0
        
        for flaw_type, _ in flaw_types:
            rate, tests = get_flawed_stats(model_data, flaw_type)
            total_tests += tests
            
            if tests > 0:
                row.append(f"{rate:5.1f}%")
                rates.append(rate)
            else:
                row.append("   -  ")
        
        # 计算平均值
        if rates:
            avg_rate = sum(rates) / len(rates)
            row.append(f"{avg_rate:5.1f}%")
        else:
            row.append("   -  ")
        
        print("| " + " | ".join(row) + " |")
    
    print()
    
    # 详细统计
    print("\n详细测试统计：")
    print("-" * 40)
    
    total_all = 0
    for model in models:
        if model not in db['models']:
            continue
        
        model_data = db['models'][model]
        model_total = 0
        flaw_count = 0
        
        for flaw_type, flaw_name in flaw_types:
            rate, tests = get_flawed_stats(model_data, flaw_type)
            if tests > 0:
                model_total += tests
                flaw_count += 1
        
        if model_total > 0:
            print(f"{model}: {model_total}个测试, {flaw_count}种缺陷类型")
            total_all += model_total
    
    print(f"\n总计: {total_all}个测试")
    expected = len(models) * 7 * 100  # 8个模型 × 7种缺陷 × 100个测试
    completion = (total_all / expected * 100) if expected > 0 else 0
    print(f"期望: {expected}个测试")
    print(f"完成率: {completion:.1f}%")

if __name__ == "__main__":
    main()