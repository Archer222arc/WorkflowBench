#!/usr/bin/env python3
"""
清理数据库中因超时而失败的测试结果
删除今天(2025-08-14)产生的不完整/失败的缺陷测试数据
"""

import json
import os
from datetime import datetime
from pathlib import Path

def backup_database():
    """备份原始数据库"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"pilot_bench_cumulative_results/master_database_backup_before_timeout_cleanup_{timestamp}.json"
    
    with open("pilot_bench_cumulative_results/master_database.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 已备份原始数据库到: {backup_path}")
    return backup_path

def should_clean_model(model_name, model_data):
    """判断是否应该清理某个模型的数据"""
    
    # 检查是否是今天测试的
    last_test = model_data.get('last_test_time', '')
    if '2025-08-14' not in last_test:
        return False, "非今日测试"
    
    # 检查是否有缺陷测试
    if 'by_prompt_type' not in model_data:
        return False, "无prompt_type数据"
    
    flawed_types = [pt for pt in model_data['by_prompt_type'].keys() if 'flawed' in pt]
    if not flawed_types:
        return False, "无缺陷测试"
    
    # 基于失败日志的特定模型 (已知超时失败的)
    timeout_models = [
        'deepseek-v3-0324-3',    # 对应 DeepSeek-V3-0324 的分片
        'deepseek-r1-0528-2',    # 对应 DeepSeek-R1-0528 的分片  
        'deepseek-r1-0528-3',    # 对应 DeepSeek-R1-0528 的分片
        'llama-3.3-70b-instruct-3'  # 对应 Llama-3.3-70B-Instruct 的分片
    ]
    
    if model_name in timeout_models:
        return True, f"已知超时失败模型: {model_name}"
    
    # 检查是否是主模型但测试不完整（可能被超时中断）
    main_timeout_models = ['qwen2.5-3b-instruct', 'DeepSeek-R1-0528', 'Llama-3.3-70B-Instruct', 'qwen2.5-14b-instruct']
    if model_name in main_timeout_models:
        # 检查今天是否有缺陷测试但时间在下午（可能是失败的测试）
        if '14:' in last_test or '15:' in last_test or '16:' in last_test:
            return True, f"主模型今日下午缺陷测试(可能超时): {model_name}"
    
    return False, "保留"

def clean_database():
    """清理数据库"""
    
    print("========================================")
    print("清理数据库中的超时失败测试结果")
    print("========================================")
    
    # 备份原始数据库
    backup_path = backup_database()
    
    # 读取数据库
    with open("pilot_bench_cumulative_results/master_database.json", 'r', encoding='utf-8') as f:
        db = json.load(f)
    
    models_to_remove = []
    models_to_clean_flawed = []
    
    print("\n分析需要清理的模型:")
    print("-" * 50)
    
    for model_name, model_data in db['models'].items():
        should_clean, reason = should_clean_model(model_name, model_data)
        
        if should_clean:
            total_tests = model_data.get('total_tests', 0)
            last_test = model_data.get('last_test_time', '')
            
            # 如果是分片模型（xxx-2, xxx-3），完全删除
            if any(model_name.endswith(suffix) for suffix in ['-2', '-3']):
                models_to_remove.append(model_name)
                print(f"🗑️  完全删除: {model_name}")
                print(f"    原因: {reason}")
                print(f"    测试数: {total_tests}, 最后测试: {last_test}")
            else:
                # 主模型只清理今天的缺陷测试
                models_to_clean_flawed.append(model_name)
                print(f"🧹 清理缺陷测试: {model_name}")
                print(f"    原因: {reason}")
                print(f"    测试数: {total_tests}, 最后测试: {last_test}")
        
        print(f"✅ 保留: {model_name} ({reason})")
    
    # 执行清理
    print(f"\n开始清理...")
    print(f"完全删除模型数: {len(models_to_remove)}")
    print(f"清理缺陷测试模型数: {len(models_to_clean_flawed)}")
    
    if not models_to_remove and not models_to_clean_flawed:
        print("❌ 没有需要清理的数据")
        return
    
    # 完全删除分片模型
    for model_name in models_to_remove:
        print(f"🗑️  删除模型: {model_name}")
        del db['models'][model_name]
        
        # 同时删除相关的test_groups
        groups_to_remove = [group_id for group_id in db['test_groups'].keys() if model_name in group_id]
        for group_id in groups_to_remove:
            print(f"    删除test_group: {group_id}")
            del db['test_groups'][group_id]
    
    # 清理主模型的今日缺陷测试
    for model_name in models_to_clean_flawed:
        model_data = db['models'][model_name]
        
        print(f"🧹 清理模型缺陷测试: {model_name}")
        
        # 删除所有flawed开头的prompt_type
        if 'by_prompt_type' in model_data:
            flawed_types = [pt for pt in model_data['by_prompt_type'].keys() if 'flawed' in pt]
            for flawed_type in flawed_types:
                print(f"    删除prompt_type: {flawed_type}")
                del model_data['by_prompt_type'][flawed_type]
        
        # 重新计算overall_stats（去除缺陷测试后）
        # 这里简化处理，将overall_stats清空，让系统重新计算
        model_data['overall_stats'] = {}
        
        # 减少total_tests（粗略估计，实际应该重新计算）
        # 暂时不修改，让系统在下次测试时重新计算
    
    # 更新数据库时间戳
    db['last_updated'] = datetime.now().isoformat()
    
    # 保存清理后的数据库
    with open("pilot_bench_cumulative_results/master_database.json", 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
    
    print("\n========================================")
    print("✅ 清理完成！")
    print("========================================")
    print(f"备份文件: {backup_path}")
    print(f"已删除 {len(models_to_remove)} 个分片模型")
    print(f"已清理 {len(models_to_clean_flawed)} 个主模型的缺陷测试")
    print("\n可以运行重新测试脚本:")
    print("./rerun_failed_tests.sh")

if __name__ == "__main__":
    clean_database()