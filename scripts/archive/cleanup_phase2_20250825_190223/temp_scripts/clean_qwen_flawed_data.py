#!/usr/bin/env python3
"""
清理qwen模型5.3-5.5测试的错误数据

背景：
- 5.1和5.2使用直接调用，数据应该是准确的
- 5.3-5.5使用ultra_parallel_runner，存在映射错误
- qwen2.5-7b和3b的5.3-5.5数据实际是72b的结果

清理策略：
1. 保留5.1和5.2的数据（optimal, baseline, cot等基础prompt类型）
2. 清理5.3-5.5的数据（flawed_*类型的prompt）
3. 可选：将错误数据移动到72b的统计中
"""

import json
import os
from datetime import datetime
from pathlib import Path
import shutil

def analyze_qwen_data():
    """分析qwen模型的数据分布"""
    
    db_path = Path("pilot_bench_cumulative_results/master_database.json")
    if not db_path.exists():
        print("❌ 数据库文件不存在")
        return None
    
    with open(db_path, 'r', encoding='utf-8') as f:
        db = json.load(f)
    
    print("=" * 60)
    print("qwen模型数据分析")
    print("=" * 60)
    
    qwen_models = [
        "qwen2.5-72b-instruct",
        "qwen2.5-32b-instruct", 
        "qwen2.5-14b-instruct",
        "qwen2.5-7b-instruct",
        "qwen2.5-3b-instruct"
    ]
    
    for model in qwen_models:
        if model in db.get('models', {}):
            model_data = db['models'][model]
            print(f"\n📊 {model}:")
            print(f"  总测试数: {model_data.get('overall_stats', {}).get('total_tests', 0)}")
            
            # 分析prompt类型分布
            if 'by_prompt_type' in model_data:
                print("  按prompt类型:")
                for prompt_type in model_data['by_prompt_type']:
                    prompt_data = model_data['by_prompt_type'][prompt_type]
                    total = prompt_data.get('total_tests', 0)
                    if total > 0:
                        print(f"    - {prompt_type}: {total} 个测试")
                        
                        # 对于flawed类型，这可能是错误数据
                        if prompt_type.startswith('flawed_'):
                            print(f"      ⚠️ 可能是错误数据（5.3-5.5测试）")
    
    return db

def clean_flawed_data(backup=True, move_to_72b=False):
    """清理qwen 7b和3b的flawed数据
    
    Args:
        backup: 是否备份原数据
        move_to_72b: 是否将数据移动到72b统计中（因为实际是72b的结果）
    """
    
    db_path = Path("pilot_bench_cumulative_results/master_database.json")
    
    # 备份
    if backup:
        backup_path = db_path.parent / f"master_database_backup_qwen_cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        shutil.copy2(db_path, backup_path)
        print(f"✅ 已备份到: {backup_path}")
    
    # 读取数据
    with open(db_path, 'r', encoding='utf-8') as f:
        db = json.load(f)
    
    # 需要清理的模型
    models_to_clean = ["qwen2.5-7b-instruct", "qwen2.5-3b-instruct"]
    
    # 记录清理的数据
    cleaned_data = {}
    
    for model in models_to_clean:
        if model not in db.get('models', {}):
            continue
            
        model_data = db['models'][model]
        cleaned_data[model] = {}
        
        print(f"\n🧹 清理 {model} 的flawed数据...")
        
        # 清理by_prompt_type中的flawed_*
        if 'by_prompt_type' in model_data:
            flawed_types = [pt for pt in model_data['by_prompt_type'] if pt.startswith('flawed_')]
            
            for flawed_type in flawed_types:
                # 保存要清理的数据
                cleaned_data[model][flawed_type] = model_data['by_prompt_type'][flawed_type]
                
                # 获取测试数量
                total_tests = model_data['by_prompt_type'][flawed_type].get('total_tests', 0)
                print(f"  - 删除 {flawed_type}: {total_tests} 个测试")
                
                # 如果需要，移动到72b
                if move_to_72b and total_tests > 0:
                    if 'qwen2.5-72b-instruct' in db['models']:
                        # TODO: 合并数据到72b（需要更复杂的逻辑）
                        print(f"    → 移动到72b统计中")
                
                # 删除flawed数据
                del model_data['by_prompt_type'][flawed_type]
        
        # 重新计算overall_stats
        recalculate_overall_stats(model_data)
        
    # 清理test_groups中相关的条目
    if 'test_groups' in db:
        groups_to_remove = []
        for group_id, group_data in db['test_groups'].items():
            # 检查是否是7b或3b的flawed测试
            if (group_data.get('model') in models_to_clean and 
                group_data.get('prompt_type', '').startswith('flawed_')):
                groups_to_remove.append(group_id)
        
        for group_id in groups_to_remove:
            print(f"  - 删除test_group: {group_id}")
            del db['test_groups'][group_id]
    
    # 更新summary
    update_summary(db)
    
    # 保存清理后的数据
    with open(db_path, 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
    
    print("\n✅ 清理完成！")
    
    # 保存清理的数据记录
    if cleaned_data:
        cleaned_file = Path(f"cleaned_qwen_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(cleaned_file, 'w', encoding='utf-8') as f:
            json.dump(cleaned_data, f, indent=2, ensure_ascii=False)
        print(f"📄 清理的数据已保存到: {cleaned_file}")
    
    return cleaned_data

def recalculate_overall_stats(model_data):
    """重新计算模型的overall_stats"""
    
    total_tests = 0
    total_success = 0
    total_partial = 0
    total_failed = 0
    
    # 遍历所有prompt_type
    if 'by_prompt_type' in model_data:
        for prompt_data in model_data['by_prompt_type'].values():
            total_tests += prompt_data.get('total_tests', 0)
            
            # 如果有更详细的统计
            if 'by_tool_success_rate' in prompt_data:
                for rate_data in prompt_data['by_tool_success_rate'].values():
                    if 'by_difficulty' in rate_data:
                        for diff_data in rate_data['by_difficulty'].values():
                            if 'by_task_type' in diff_data:
                                for task_data in diff_data['by_task_type'].values():
                                    total_success += task_data.get('successful', 0)
                                    total_partial += task_data.get('partial', 0)
                                    total_failed += task_data.get('failed', 0)
    
    # 更新overall_stats
    if 'overall_stats' not in model_data:
        model_data['overall_stats'] = {}
    
    model_data['overall_stats']['total_tests'] = total_tests
    model_data['overall_stats']['success_count'] = total_success
    model_data['overall_stats']['partial_count'] = total_partial
    model_data['overall_stats']['failure_count'] = total_failed
    
    if total_tests > 0:
        model_data['overall_stats']['success_rate'] = total_success / total_tests
        model_data['overall_stats']['partial_rate'] = total_partial / total_tests
        model_data['overall_stats']['failure_rate'] = total_failed / total_tests

def update_summary(db):
    """更新数据库的summary"""
    
    total_tests = 0
    total_success = 0
    total_partial = 0
    total_failure = 0
    models_tested = []
    
    for model_name, model_data in db.get('models', {}).items():
        if model_data.get('overall_stats', {}).get('total_tests', 0) > 0:
            models_tested.append(model_name)
            total_tests += model_data['overall_stats'].get('total_tests', 0)
            total_success += model_data['overall_stats'].get('success_count', 0)
            total_partial += model_data['overall_stats'].get('partial_count', 0)
            total_failure += model_data['overall_stats'].get('failure_count', 0)
    
    db['summary'] = {
        'total_tests': total_tests,
        'total_success': total_success,
        'total_partial': total_partial,
        'total_failure': total_failure,
        'models_tested': sorted(models_tested),
        'last_test_time': datetime.now().isoformat()
    }

def main():
    """主函数"""
    
    print("=" * 60)
    print("qwen模型5.3-5.5错误数据清理工具")
    print("=" * 60)
    
    # 先分析数据
    db = analyze_qwen_data()
    
    if not db:
        return
    
    print("\n" + "=" * 60)
    print("清理选项:")
    print("1. 只分析，不清理")
    print("2. 清理7b和3b的flawed数据（推荐）")
    print("3. 清理并尝试移动到72b统计")
    print("0. 退出")
    
    choice = input("\n请选择 (0-3): ").strip()
    
    if choice == '2':
        print("\n开始清理...")
        clean_flawed_data(backup=True, move_to_72b=False)
    elif choice == '3':
        print("\n开始清理并移动...")
        clean_flawed_data(backup=True, move_to_72b=True)
    elif choice == '1':
        print("\n仅分析，不进行清理")
    else:
        print("\n退出")

if __name__ == "__main__":
    main()