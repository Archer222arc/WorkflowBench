#!/usr/bin/env python3
"""
清理Llama-3.3-70B-Instruct的flawed测试结果（0%成功率的无效数据）
"""
import json
from pathlib import Path
from datetime import datetime

def main():
    # 备份原始文件
    db_path = Path('pilot_bench_cumulative_results/master_database.json')
    backup_path = db_path.parent / f"master_database_backup_before_llama_cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    # 读取数据库
    with open(db_path, 'r') as f:
        db = json.load(f)
    
    # 备份
    with open(backup_path, 'w') as f:
        json.dump(db, f, indent=2)
    print(f"✅ 已备份到: {backup_path}")
    
    # 检查Llama-3.3-70B-Instruct的数据
    model = 'Llama-3.3-70B-Instruct'
    if model not in db['models']:
        print(f"❌ 未找到{model}的数据")
        return
    
    model_data = db['models'][model]
    
    # 要删除的flawed类型
    flawed_types = [
        'flawed_sequence_disorder',
        'flawed_tool_misuse',
        'flawed_parameter_error',
        'flawed_missing_step',
        'flawed_redundant_operations',
        'flawed_logical_inconsistency',
        'flawed_semantic_drift'
    ]
    
    print(f"\n清理前 {model} 的数据:")
    deleted_count = 0
    
    if 'by_prompt_type' in model_data:
        for flaw_type in flawed_types:
            if flaw_type in model_data['by_prompt_type']:
                # 获取该缺陷类型的数据
                flaw_data = model_data['by_prompt_type'][flaw_type]
                
                # 检查是否都是0%成功率
                total_tests = 0
                total_success = 0
                
                if 'by_tool_success_rate' in flaw_data and '0.8' in flaw_data['by_tool_success_rate']:
                    rate_data = flaw_data['by_tool_success_rate']['0.8']
                    if 'by_difficulty' in rate_data and 'easy' in rate_data['by_difficulty']:
                        diff_data = rate_data['by_difficulty']['easy']
                        if 'by_task_type' in diff_data:
                            for task_data in diff_data['by_task_type'].values():
                                total_tests += task_data.get('total', 0)
                                total_success += task_data.get('success', 0)
                
                success_rate = (total_success / total_tests * 100) if total_tests > 0 else 0
                
                print(f"  {flaw_type}: {total_tests}个测试, 成功率={success_rate:.1f}%")
                
                # 如果成功率是0%，删除这个缺陷类型
                if success_rate == 0 and total_tests > 0:
                    del model_data['by_prompt_type'][flaw_type]
                    deleted_count += 1
                    print(f"    ❌ 已删除 (0%成功率)")
    
    # 更新总体统计
    if deleted_count > 0:
        # 重新计算总体统计
        total_tests = 0
        total_success = 0
        
        if 'by_prompt_type' in model_data:
            for prompt_type in model_data['by_prompt_type'].values():
                if 'by_tool_success_rate' in prompt_type:
                    for rate_data in prompt_type['by_tool_success_rate'].values():
                        if 'by_difficulty' in rate_data:
                            for diff_data in rate_data['by_difficulty'].values():
                                if 'by_task_type' in diff_data:
                                    for task_data in diff_data['by_task_type'].values():
                                        total_tests += task_data.get('total', 0)
                                        total_success += task_data.get('success', 0)
        
        # 更新overall_stats
        if 'overall_stats' in model_data:
            model_data['overall_stats']['total_tests'] = total_tests
            model_data['overall_stats']['success_rate'] = (total_success / total_tests) if total_tests > 0 else 0
        
        print(f"\n✅ 已删除 {deleted_count} 个无效的缺陷测试类型")
        print(f"剩余测试数: {total_tests}")
        
        # 保存更新后的数据库
        with open(db_path, 'w') as f:
            json.dump(db, f, indent=2)
        print(f"✅ 已更新数据库: {db_path}")
    else:
        print("\n没有需要删除的数据")

if __name__ == "__main__":
    main()