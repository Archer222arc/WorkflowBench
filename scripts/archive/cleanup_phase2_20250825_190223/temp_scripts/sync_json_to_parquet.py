#!/usr/bin/env python3
"""
从JSON同步数据到Parquet格式
"""
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import numpy as np

def extract_summaries_from_json(db):
    """从JSON数据库提取汇总记录"""
    summaries = []
    
    for model_name, model_data in db.get('models', {}).items():
        if 'by_prompt_type' not in model_data:
            continue
            
        for prompt_type, prompt_data in model_data['by_prompt_type'].items():
            if 'by_tool_success_rate' not in prompt_data:
                continue
                
            for tool_rate, rate_data in prompt_data['by_tool_success_rate'].items():
                if 'by_difficulty' not in rate_data:
                    continue
                    
                for difficulty, diff_data in rate_data['by_difficulty'].items():
                    if 'by_task_type' not in diff_data:
                        continue
                        
                    for task_type, task_data in diff_data['by_task_type'].items():
                        # 创建汇总记录
                        summary = {
                            'model': model_name,
                            'prompt_type': prompt_type,
                            'difficulty': difficulty,
                            'task_type': task_type,
                            'tool_success_rate': float(tool_rate),
                            'total': task_data.get('total', 0),
                            'success': task_data.get('success', 0),
                            'partial': task_data.get('partial', 0),
                            'failed': task_data.get('failed', 0),
                            'success_rate': task_data.get('success_rate', 0),
                            'partial_rate': task_data.get('partial_rate', 0),
                            'failure_rate': task_data.get('failure_rate', 0),
                            'weighted_success_score': task_data.get('weighted_success_score', 0),
                            'avg_execution_time': task_data.get('avg_execution_time', 0),
                            'avg_turns': task_data.get('avg_turns', 0),
                            'avg_tool_calls': task_data.get('avg_tool_calls', 0),
                            'tool_coverage_rate': task_data.get('tool_coverage_rate', 0),
                            'last_updated': datetime.now().isoformat()
                        }
                        
                        # 添加缺陷类型（如果是缺陷测试）
                        if 'flawed' in prompt_type:
                            summary['is_flawed'] = True
                            summary['flaw_type'] = prompt_type.replace('flawed_', '')
                        else:
                            summary['is_flawed'] = False
                            summary['flaw_type'] = None
                        
                        summaries.append(summary)
    
    return summaries

def main():
    # 读取JSON数据库
    json_path = Path('pilot_bench_cumulative_results/master_database.json')
    if not json_path.exists():
        print("❌ JSON数据库不存在")
        return
    
    with open(json_path, 'r') as f:
        db = json.load(f)
    
    print("📖 读取JSON数据库...")
    
    # 提取汇总记录
    summaries = extract_summaries_from_json(db)
    print(f"✅ 提取了 {len(summaries)} 条汇总记录")
    
    if not summaries:
        print("❌ 没有找到汇总记录")
        return
    
    # 转换为DataFrame
    df = pd.DataFrame(summaries)
    
    # 确保数值类型正确
    numeric_columns = ['total', 'success', 'partial', 'failed', 'success_rate', 
                      'partial_rate', 'failure_rate', 'weighted_success_score',
                      'avg_execution_time', 'avg_turns', 'avg_tool_calls', 
                      'tool_coverage_rate', 'tool_success_rate']
    
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # 创建Parquet目录
    parquet_dir = Path('pilot_bench_parquet_data')
    parquet_dir.mkdir(exist_ok=True)
    
    # 备份现有的Parquet文件
    parquet_path = parquet_dir / 'test_results.parquet'
    if parquet_path.exists():
        backup_path = parquet_dir / f"test_results_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
        parquet_path.rename(backup_path)
        print(f"✅ 备份现有Parquet文件到: {backup_path}")
    
    # 保存新的Parquet文件
    df.to_parquet(parquet_path, index=False)
    print(f"✅ 保存了 {len(df)} 条记录到Parquet文件")
    
    # 显示统计
    print("\n📊 数据统计:")
    print(f"  模型数: {df['model'].nunique()}")
    print(f"  提示类型数: {df['prompt_type'].nunique()}")
    
    # 按模型统计
    print("\n按模型统计:")
    model_stats = df.groupby('model').agg({
        'total': 'sum',
        'success': 'sum'
    })
    
    for model, row in model_stats.iterrows():
        total = row['total']
        success = row['success']
        rate = (success / total * 100) if total > 0 else 0
        print(f"  {model}: {total}个测试, 成功率={rate:.1f}%")
    
    # 统计缺陷测试
    flawed_df = df[df['is_flawed'] == True]
    if len(flawed_df) > 0:
        print(f"\n缺陷测试统计:")
        print(f"  总缺陷测试: {flawed_df['total'].sum()}")
        print(f"  缺陷类型数: {flawed_df['flaw_type'].nunique()}")
    
    # 保存JSON格式的Parquet内容（用于查看）
    json_preview_path = parquet_dir / 'test_results.parquet.as.json'
    df.to_json(json_preview_path, orient='records', indent=2, force_ascii=False)
    print(f"\n✅ 保存JSON预览到: {json_preview_path}")
    
    print("\n✅ JSON到Parquet同步完成！")

if __name__ == "__main__":
    main()