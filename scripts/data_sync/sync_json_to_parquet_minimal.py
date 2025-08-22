#!/usr/bin/env python3
"""
最小化的JSON到Parquet同步脚本
只同步JSON中实际存在的字段，不添加虚假的零值
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import shutil

def sync_json_to_parquet_minimal():
    """从JSON同步到Parquet，只保留实际存在的字段"""
    
    # 文件路径
    json_file = Path('pilot_bench_cumulative_results/master_database.json')
    parquet_file = Path('pilot_bench_parquet_data/test_results.parquet')
    backup_dir = Path('pilot_bench_parquet_data/backups')
    backup_dir.mkdir(exist_ok=True)
    
    if not json_file.exists():
        print("❌ JSON文件不存在")
        return
    
    # 备份现有Parquet文件
    if parquet_file.exists():
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = backup_dir / f'test_results_{timestamp}.parquet'
        shutil.copy2(parquet_file, backup_file)
        print(f"✅ 已备份Parquet: {backup_file.name}")
    
    print("📖 读取JSON数据...")
    with open(json_file, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    # 提取所有记录，只保留JSON中实际存在的字段
    records = []
    
    for model_name, model_data in json_data.get('models', {}).items():
        # 跳过llama-4-scout-17b
        if 'llama-4' in model_name.lower():
            continue
            
        for prompt_type, prompt_data in model_data.get('by_prompt_type', {}).items():
            # 跳过无效的单独flawed记录
            if prompt_type == 'flawed':
                continue
                
            for tool_rate, rate_data in prompt_data.get('by_tool_success_rate', {}).items():
                for difficulty, diff_data in rate_data.get('by_difficulty', {}).items():
                    for task_type, task_data in diff_data.get('by_task_type', {}).items():
                        # 跳过unknown task_type
                        if task_type == 'unknown':
                            continue
                            
                        if not isinstance(task_data, dict):
                            continue
                        
                        # 创建记录，只包含JSON中实际存在的字段
                        record = {
                            # 标识字段
                            'model': model_name,
                            'prompt_type': prompt_type,
                            'tool_success_rate': float(tool_rate),
                            'difficulty': difficulty,
                            'task_type': task_type,
                            
                            # JSON中实际存在的统计字段
                            'total': task_data.get('total', 0),
                            'successful': task_data.get('successful', 0),
                            'partial': task_data.get('partial', 0),
                            'failed': task_data.get('failed', 0),
                            'success_rate': task_data.get('success_rate', 0.0),
                            'partial_rate': task_data.get('partial_rate', 0.0),
                            'failure_rate': task_data.get('failure_rate', 0.0),
                            'weighted_success_score': task_data.get('weighted_success_score', 0.0),
                            'avg_execution_time': task_data.get('avg_execution_time', 0.0),
                            'avg_turns': task_data.get('avg_turns', 0.0),
                            'tool_coverage_rate': task_data.get('tool_coverage_rate', 0.0),
                            'avg_tool_calls': task_data.get('avg_tool_calls', 0.0),
                            
                            # 时间戳
                            'last_updated': datetime.now().isoformat()
                        }
                        
                        records.append(record)
    
    print(f"✅ 提取了 {len(records)} 条记录")
    
    if records:
        # 创建DataFrame
        df = pd.DataFrame(records)
        
        # 显示统计
        print(f"\n📊 数据统计:")
        print(f"  记录数: {len(df)}")
        print(f"  字段数: {len(df.columns)}")
        print(f"  模型数: {len(df['model'].unique())}")
        
        # 显示模型列表
        print(f"\n模型列表:")
        for model in sorted(df['model'].unique()):
            count = len(df[df['model'] == model])
            print(f"  - {model}: {count} 条记录")
        
        # 检查数据质量
        print(f"\n数据质量检查:")
        if 'llama-4-scout-17b' in df['model'].values:
            print("  ❌ 包含llama-4-scout-17b")
        else:
            print("  ✅ 不包含llama-4-scout-17b")
            
        if 'unknown' in df['task_type'].values:
            print("  ❌ 包含unknown task_type")
        else:
            print("  ✅ 不包含unknown task_type")
            
        if 'flawed' in df['prompt_type'].values:
            print("  ❌ 包含单独的flawed prompt_type")
        else:
            print("  ✅ 不包含单独的flawed prompt_type")
        
        # 保存到Parquet
        df.to_parquet(parquet_file, index=False)
        print(f"\n✅ 已保存到Parquet: {parquet_file}")
        print(f"  文件大小: {parquet_file.stat().st_size / 1024:.1f} KB")
        
        # 验证
        print(f"\n📊 验证结果:")
        df_verify = pd.read_parquet(parquet_file)
        print(f"  记录数: {len(df_verify)}")
        print(f"  字段数: {len(df_verify.columns)}")
        
        # 显示字段列表
        print(f"\n实际保存的字段:")
        for field in df_verify.columns:
            non_zero = len(df_verify[df_verify[field] != 0]) if field not in ['model', 'prompt_type', 'difficulty', 'task_type', 'last_updated'] else '---'
            if non_zero != '---' and non_zero > 0:
                print(f"  ✅ {field}: {non_zero} 个非零值")
            elif non_zero == 0:
                print(f"  ⚠️ {field}: 全部为0")
            else:
                print(f"  📝 {field}: 文本字段")
    else:
        print("❌ 没有找到有效记录")

if __name__ == "__main__":
    sync_json_to_parquet_minimal()