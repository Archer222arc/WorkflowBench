#!/usr/bin/env python3
"""
合并数据库中同一模型的不同实例
例如：DeepSeek-V3-0324, deepseek-v3-0324-2, deepseek-v3-0324-3 应该合并为一个
"""

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def get_main_model_name(model_name):
    """获取主模型名称"""
    # 定义模型映射规则
    model_name_lower = model_name.lower()
    
    # DeepSeek V3
    if 'deepseek-v3' in model_name_lower or 'deepseek_v3' in model_name_lower:
        return 'DeepSeek-V3-0324'
    
    # DeepSeek R1
    if 'deepseek-r1' in model_name_lower or 'deepseek_r1' in model_name_lower:
        return 'DeepSeek-R1-0528'
    
    # Llama 3.3
    if 'llama-3.3' in model_name_lower or 'llama_3.3' in model_name_lower:
        return 'Llama-3.3-70B-Instruct'
    
    # Qwen系列保持原样
    if 'qwen' in model_name_lower:
        # 提取版本号
        if '72b' in model_name_lower:
            return 'qwen2.5-72b-instruct'
        elif '32b' in model_name_lower:
            return 'qwen2.5-32b-instruct'
        elif '14b' in model_name_lower:
            return 'qwen2.5-14b-instruct'
        elif '7b' in model_name_lower:
            return 'qwen2.5-7b-instruct'
        elif '3b' in model_name_lower:
            return 'qwen2.5-3b-instruct'
    
    # 其他模型保持原样
    return model_name

def merge_model_data(data1, data2):
    """合并两个模型的数据"""
    merged = data1.copy() if data1 else {}
    
    if not data2:
        return merged
    
    # 合并 overall_stats
    if 'overall_stats' in data2:
        if 'overall_stats' not in merged:
            merged['overall_stats'] = {}
        
        for key, value in data2['overall_stats'].items():
            if key in merged['overall_stats']:
                if isinstance(value, (int, float)):
                    # 对于数值，累加
                    if key.endswith('_rate') or key == 'success_rate':
                        # 对于率值，需要重新计算
                        continue
                    else:
                        merged['overall_stats'][key] = merged['overall_stats'].get(key, 0) + value
            else:
                merged['overall_stats'][key] = value
    
    # 合并 by_prompt_type
    if 'by_prompt_type' in data2:
        if 'by_prompt_type' not in merged:
            merged['by_prompt_type'] = {}
        
        for prompt_type, prompt_data in data2['by_prompt_type'].items():
            if prompt_type not in merged['by_prompt_type']:
                merged['by_prompt_type'][prompt_type] = prompt_data
            else:
                # 递归合并
                merged['by_prompt_type'][prompt_type] = merge_prompt_data(
                    merged['by_prompt_type'][prompt_type], 
                    prompt_data
                )
    
    return merged

def merge_prompt_data(data1, data2):
    """合并prompt数据"""
    merged = data1.copy() if data1 else {}
    
    if not data2:
        return merged
    
    # 合并 by_tool_success_rate
    if 'by_tool_success_rate' in data2:
        if 'by_tool_success_rate' not in merged:
            merged['by_tool_success_rate'] = {}
        
        for rate, rate_data in data2['by_tool_success_rate'].items():
            if rate not in merged['by_tool_success_rate']:
                merged['by_tool_success_rate'][rate] = rate_data
            else:
                merged['by_tool_success_rate'][rate] = merge_rate_data(
                    merged['by_tool_success_rate'][rate],
                    rate_data
                )
    
    return merged

def merge_rate_data(data1, data2):
    """合并rate数据"""
    merged = data1.copy() if data1 else {}
    
    if not data2:
        return merged
    
    # 合并 by_difficulty
    if 'by_difficulty' in data2:
        if 'by_difficulty' not in merged:
            merged['by_difficulty'] = {}
        
        for diff, diff_data in data2['by_difficulty'].items():
            if diff not in merged['by_difficulty']:
                merged['by_difficulty'][diff] = diff_data
            else:
                merged['by_difficulty'][diff] = merge_difficulty_data(
                    merged['by_difficulty'][diff],
                    diff_data
                )
    
    return merged

def merge_difficulty_data(data1, data2):
    """合并difficulty数据"""
    merged = data1.copy() if data1 else {}
    
    if not data2:
        return merged
    
    # 合并 by_task_type
    if 'by_task_type' in data2:
        if 'by_task_type' not in merged:
            merged['by_task_type'] = {}
        
        for task, task_data in data2['by_task_type'].items():
            if task not in merged['by_task_type']:
                merged['by_task_type'][task] = task_data
            else:
                # 合并任务数据
                merged['by_task_type'][task] = merge_task_data(
                    merged['by_task_type'][task],
                    task_data
                )
    
    return merged

def merge_task_data(data1, data2):
    """合并任务数据"""
    merged = {}
    
    # 累加计数
    merged['total'] = data1.get('total', 0) + data2.get('total', 0)
    merged['success'] = data1.get('success', 0) + data2.get('success', 0)
    merged['partial'] = data1.get('partial', 0) + data2.get('partial', 0)
    merged['failure'] = data1.get('failure', 0) + data2.get('failure', 0)
    
    # 重新计算率值
    if merged['total'] > 0:
        merged['success_rate'] = merged['success'] / merged['total']
        
        # 加权平均其他指标
        w1 = data1.get('total', 0) / merged['total']
        w2 = data2.get('total', 0) / merged['total']
        
        if 'tool_coverage_rate' in data1 or 'tool_coverage_rate' in data2:
            merged['tool_coverage_rate'] = (
                w1 * data1.get('tool_coverage_rate', 0) + 
                w2 * data2.get('tool_coverage_rate', 0)
            )
        
        if 'avg_turns' in data1 or 'avg_turns' in data2:
            merged['avg_turns'] = (
                w1 * data1.get('avg_turns', 0) + 
                w2 * data2.get('avg_turns', 0)
            )
        
        if 'avg_execution_time' in data1 or 'avg_execution_time' in data2:
            merged['avg_execution_time'] = (
                w1 * data1.get('avg_execution_time', 0) + 
                w2 * data2.get('avg_execution_time', 0)
            )
    
    return merged

def merge_database():
    """合并数据库中的模型实例"""
    db_path = Path('pilot_bench_cumulative_results/master_database.json')
    
    # 读取当前数据库
    with open(db_path, 'r') as f:
        db = json.load(f)
    
    # 备份
    backup_path = db_path.parent / f"master_database_before_merge_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(backup_path, 'w') as f:
        json.dump(db, f, indent=2)
    print(f"已备份到: {backup_path}")
    
    # 分组模型
    model_groups = defaultdict(list)
    for model_name in db['models'].keys():
        main_name = get_main_model_name(model_name)
        model_groups[main_name].append(model_name)
    
    # 合并同组模型
    new_models = {}
    merge_log = []
    
    for main_name, instances in model_groups.items():
        if len(instances) == 1 and instances[0] == main_name:
            # 不需要合并
            new_models[main_name] = db['models'][instances[0]]
        else:
            # 需要合并
            print(f"\n合并 {main_name}:")
            print(f"  实例: {instances}")
            
            merged_data = {}
            for instance in instances:
                if instance in db['models']:
                    merged_data = merge_model_data(merged_data, db['models'][instance])
                    merge_log.append(f"  + {instance}")
            
            new_models[main_name] = merged_data
            
            # 统计合并后的测试数
            total_tests = 0
            if 'by_prompt_type' in merged_data:
                for prompt_data in merged_data['by_prompt_type'].values():
                    if 'by_tool_success_rate' in prompt_data:
                        for rate_data in prompt_data['by_tool_success_rate'].values():
                            if 'by_difficulty' in rate_data:
                                for diff_data in rate_data['by_difficulty'].values():
                                    if 'by_task_type' in diff_data:
                                        for task_data in diff_data['by_task_type'].values():
                                            total_tests += task_data.get('total', 0)
            
            print(f"  合并后测试数: {total_tests}")
    
    # 更新数据库
    db['models'] = new_models
    db['last_updated'] = datetime.now().isoformat()
    
    # 保存
    with open(db_path, 'w') as f:
        json.dump(db, f, indent=2)
    
    print(f"\n合并完成!")
    print(f"原模型数: {len(model_groups)}")
    print(f"合并后模型数: {len(new_models)}")
    
    # 验证
    print("\n=== 合并后的模型列表 ===")
    for model_name in sorted(new_models.keys()):
        test_count = 0
        if 'by_prompt_type' in new_models[model_name]:
            for prompt_data in new_models[model_name]['by_prompt_type'].values():
                if 'by_tool_success_rate' in prompt_data:
                    for rate_data in prompt_data['by_tool_success_rate'].values():
                        if 'by_difficulty' in rate_data:
                            for diff_data in rate_data['by_difficulty'].values():
                                if 'by_task_type' in diff_data:
                                    for task_data in diff_data['by_task_type'].values():
                                        test_count += task_data.get('total', 0)
        
        print(f"  {model_name}: {test_count} 个测试")

if __name__ == "__main__":
    print("合并数据库中同一模型的不同实例...")
    response = input("是否继续? (y/n): ")
    if response.lower() == 'y':
        merge_database()
    else:
        print("已取消")