#!/usr/bin/env python3
"""
5.1基准测试数据清理脚本
清理所有模型的 optimal prompt + easy难度 + 0.8工具成功率 的测试数据
"""

import json
import sys
from pathlib import Path

def cleanup_5_1_data():
    """清理5.1基准测试数据"""
    db_path = Path("pilot_bench_cumulative_results/master_database.json")
    
    if not db_path.exists():
        print("❌ 数据库文件不存在")
        return False
    
    print("🔄 加载数据库...")
    with open(db_path, 'r', encoding='utf-8') as f:
        db = json.load(f)
    
    models = db.get('models', {})
    cleaned_count = 0
    cleaned_models = []
    
    print("\n📊 开始清理5.1数据 (optimal + easy + 0.8)...")
    print("=" * 60)
    
    for model_name in list(models.keys()):
        model_data = models[model_name]
        
        # 检查是否存在optimal prompt类型
        by_prompt = model_data.get('by_prompt_type', {})
        if 'optimal' not in by_prompt:
            continue
            
        optimal_data = by_prompt['optimal']
        by_rate = optimal_data.get('by_tool_success_rate', {})
        
        # 检查是否存在0.8工具成功率
        if '0.8' not in by_rate:
            continue
            
        rate_08_data = by_rate['0.8']
        by_difficulty = rate_08_data.get('by_difficulty', {})
        
        # 检查是否存在easy难度
        if 'easy' not in by_difficulty:
            continue
            
        easy_data = by_difficulty['easy']
        by_task_type = easy_data.get('by_task_type', {})
        
        if by_task_type:
            # 计算要清理的数据数量
            total_tests = sum(task_data.get('total', 0) for task_data in by_task_type.values())
            if total_tests > 0:
                print(f"🗑️  {model_name}: 清理 {total_tests} 个测试记录")
                cleaned_count += total_tests
                cleaned_models.append(model_name)
                
                # 清理easy难度下的所有任务类型数据
                by_difficulty['easy'] = {'by_task_type': {}}
                
                # 如果easy是唯一的难度，清理整个0.8层级
                if list(by_difficulty.keys()) == ['easy']:
                    by_rate['0.8'] = {'by_difficulty': {}}
                    
                    # 如果0.8是唯一的工具成功率，清理整个optimal层级
                    if list(by_rate.keys()) == ['0.8']:
                        by_prompt['optimal'] = {'by_tool_success_rate': {}}
                        
                        # 如果optimal是唯一的prompt类型，清理整个模型数据
                        if list(by_prompt.keys()) == ['optimal']:
                            models[model_name] = {'by_prompt_type': {}}
    
    print(f"\n📈 清理统计:")
    print(f"  清理模型数: {len(cleaned_models)}")
    print(f"  清理测试数: {cleaned_count}")
    print(f"  涉及模型: {', '.join(cleaned_models[:3])}{'...' if len(cleaned_models) > 3 else ''}")
    
    if cleaned_count == 0:
        print("⚠️  没有找到5.1数据可清理")
        return True
    
    # 重新计算summary统计
    print("\n🔄 重新计算summary统计...")
    total_tests = 0
    total_success = 0
    total_partial = 0
    total_failure = 0
    
    for model_name, model_data in models.items():
        by_prompt = model_data.get('by_prompt_type', {})
        for prompt_type, prompt_data in by_prompt.items():
            by_rate = prompt_data.get('by_tool_success_rate', {})
            for rate, rate_data in by_rate.items():
                by_difficulty = rate_data.get('by_difficulty', {})
                for difficulty, diff_data in by_difficulty.items():
                    by_task_type = diff_data.get('by_task_type', {})
                    for task_type, task_data in by_task_type.items():
                        total_tests += task_data.get('total', 0)
                        total_success += task_data.get('successful', 0)
                        total_partial += task_data.get('partial', 0)
                        total_failure += task_data.get('failed', 0)
    
    db['summary'] = {
        'total_tests': total_tests,
        'total_success': total_success,
        'total_partial': total_partial, 
        'total_failure': total_failure,
        'models_tested': list(models.keys()),
        'last_test_time': db.get('summary', {}).get('last_test_time', '')
    }
    
    # 保存清理后的数据库
    print("\n💾 保存清理后的数据库...")
    with open(db_path, 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 5.1数据清理完成！清理了 {cleaned_count} 个测试记录")
    return True

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--confirm':
        cleanup_5_1_data()
    else:
        print("🚨 这将清理所有5.1基准测试数据 (optimal + easy + 0.8)")
        print("📋 涉及的配置:")
        print("   - Prompt类型: optimal")
        print("   - 难度: easy")  
        print("   - 工具成功率: 0.8")
        print("\n⚠️  请确认要继续清理，使用: python cleanup_5_1_data.py --confirm")