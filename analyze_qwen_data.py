#!/usr/bin/env python3
"""
分析qwen模型数据，识别需要清理的部分
"""

import json
from pathlib import Path
from collections import defaultdict

def analyze_qwen_data():
    """深入分析qwen模型的数据"""
    
    # 检查JSON数据库
    json_db_path = Path("pilot_bench_cumulative_results/master_database.json")
    if json_db_path.exists():
        print("=" * 60)
        print("JSON数据库分析")
        print("=" * 60)
        with open(json_db_path, 'r', encoding='utf-8') as f:
            json_db = json.load(f)
        analyze_database(json_db, "JSON")
    else:
        print("❌ JSON数据库不存在")
    
    # 检查Parquet数据
    parquet_path = Path("pilot_bench_parquet_data/test_results.parquet")
    if parquet_path.exists():
        print("\n" + "=" * 60)
        print("Parquet数据分析")
        print("=" * 60)
        try:
            import pandas as pd
            df = pd.read_parquet(parquet_path)
            
            # 筛选qwen模型
            qwen_models = ["qwen2.5-72b-instruct", "qwen2.5-32b-instruct", 
                          "qwen2.5-14b-instruct", "qwen2.5-7b-instruct", 
                          "qwen2.5-3b-instruct"]
            
            for model in qwen_models:
                model_df = df[df['model'] == model] if 'model' in df.columns else pd.DataFrame()
                if not model_df.empty:
                    print(f"\n📊 {model}:")
                    print(f"  总记录数: {len(model_df)}")
                    
                    if 'prompt_type' in model_df.columns:
                        prompt_counts = model_df['prompt_type'].value_counts()
                        print("  按prompt类型:")
                        for prompt_type, count in prompt_counts.items():
                            indicator = "⚠️" if prompt_type.startswith('flawed_') else "✅"
                            print(f"    {indicator} {prompt_type}: {count}")
        except ImportError:
            print("  ⚠️ pandas未安装，无法分析Parquet数据")
        except Exception as e:
            print(f"  ❌ 分析Parquet失败: {e}")

def analyze_database(db, db_type=""):
    """分析数据库中的qwen数据"""
    
    qwen_models = [
        "qwen2.5-72b-instruct",
        "qwen2.5-32b-instruct", 
        "qwen2.5-14b-instruct",
        "qwen2.5-7b-instruct",
        "qwen2.5-3b-instruct"
    ]
    
    # 统计汇总
    summary = {
        'total_by_model': {},
        'flawed_by_model': {},
        'normal_by_model': {}
    }
    
    for model in qwen_models:
        if model not in db.get('models', {}):
            print(f"\n📊 {model}: 无数据")
            continue
            
        model_data = db['models'][model]
        total_tests = 0
        flawed_tests = 0
        normal_tests = 0
        
        print(f"\n📊 {model}:")
        
        # 分析prompt类型分布
        if 'by_prompt_type' in model_data:
            print("  按prompt类型:")
            for prompt_type in sorted(model_data['by_prompt_type'].keys()):
                prompt_data = model_data['by_prompt_type'][prompt_type]
                
                # 计算该prompt类型的测试总数
                prompt_total = 0
                if 'total_tests' in prompt_data:
                    prompt_total = prompt_data['total_tests']
                elif 'by_tool_success_rate' in prompt_data:
                    # 遍历所有层级计算
                    for rate_data in prompt_data['by_tool_success_rate'].values():
                        if 'by_difficulty' in rate_data:
                            for diff_data in rate_data['by_difficulty'].values():
                                if 'by_task_type' in diff_data:
                                    for task_data in diff_data['by_task_type'].values():
                                        prompt_total += task_data.get('total', 0)
                
                if prompt_total > 0:
                    total_tests += prompt_total
                    
                    if prompt_type.startswith('flawed_'):
                        flawed_tests += prompt_total
                        indicator = "⚠️ [5.3-5.5]"
                    else:
                        normal_tests += prompt_total
                        indicator = "✅ [5.1-5.2]"
                    
                    print(f"    {indicator} {prompt_type}: {prompt_total} 个测试")
        
        # 汇总
        summary['total_by_model'][model] = total_tests
        summary['flawed_by_model'][model] = flawed_tests
        summary['normal_by_model'][model] = normal_tests
        
        if total_tests > 0:
            print(f"  📈 总计: {total_tests} (正常: {normal_tests}, 疑似错误: {flawed_tests})")
    
    # 打印汇总
    print("\n" + "=" * 60)
    print(f"{db_type} 数据汇总")
    print("=" * 60)
    
    print("\n🔍 需要关注的数据:")
    for model in ["qwen2.5-7b-instruct", "qwen2.5-3b-instruct"]:
        flawed = summary['flawed_by_model'].get(model, 0)
        normal = summary['normal_by_model'].get(model, 0)
        
        if flawed > 0:
            print(f"  ❌ {model}: {flawed} 个flawed测试需要清理（实际是72b的结果）")
        if normal > 0:
            print(f"  ✅ {model}: {normal} 个正常测试可以保留")
    
    # 检查72b是否包含了错误归属的数据
    model_72b = "qwen2.5-72b-instruct"
    total_72b = summary['total_by_model'].get(model_72b, 0)
    if total_72b > 0:
        print(f"\n  ⚠️ {model_72b}: 共{total_72b}个测试（可能包含7b/3b的错误数据）")
    
    # 分析test_groups
    if 'test_groups' in db:
        print("\n📋 Test Groups分析:")
        qwen_groups = defaultdict(list)
        for group_id, group_data in db['test_groups'].items():
            model = group_data.get('model', '')
            if 'qwen' in model.lower():
                prompt_type = group_data.get('prompt_type', '')
                qwen_groups[model].append({
                    'id': group_id,
                    'prompt_type': prompt_type,
                    'total': group_data.get('total_tests', 0)
                })
        
        for model in ["qwen2.5-7b-instruct", "qwen2.5-3b-instruct"]:
            if model in qwen_groups:
                flawed_groups = [g for g in qwen_groups[model] if g['prompt_type'].startswith('flawed_')]
                if flawed_groups:
                    print(f"  ⚠️ {model}: {len(flawed_groups)} 个flawed test_group需要清理")

if __name__ == "__main__":
    analyze_qwen_data()