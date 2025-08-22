#!/usr/bin/env python3
"""
查看Parquet数据文件内容
"""

import pandas as pd
from pathlib import Path
import json

def view_parquet_data():
    """查看Parquet数据"""
    parquet_file = Path('pilot_bench_parquet_data/test_results.parquet')
    
    if not parquet_file.exists():
        print("❌ Parquet文件不存在")
        return
    
    try:
        # 读取Parquet文件
        df = pd.read_parquet(parquet_file)
        
        print("=" * 80)
        print("📊 Parquet数据文件内容")
        print("=" * 80)
        print(f"总记录数: {len(df)}")
        print(f"字段数: {len(df.columns)}")
        print(f"\n字段列表: {list(df.columns)}")
        
        # 按模型分组统计
        print("\n" + "=" * 80)
        print("📈 按模型统计")
        print("=" * 80)
        model_stats = df.groupby('model').agg({
            'total': 'sum',
            'success': 'sum',
            'success_rate': 'mean'
        }).round(3)
        print(model_stats.to_string())
        
        # 按prompt_type分组统计
        print("\n" + "=" * 80)
        print("📝 按Prompt类型统计")
        print("=" * 80)
        prompt_stats = df.groupby('prompt_type').agg({
            'total': 'sum',
            'success': 'sum',
            'success_rate': 'mean'
        }).round(3)
        print(prompt_stats.to_string())
        
        # 显示最近的记录
        print("\n" + "=" * 80)
        print("🕐 最近5条记录")
        print("=" * 80)
        recent = df.tail(5)[['model', 'prompt_type', 'difficulty', 'task_type', 'total', 'success_rate']]
        print(recent.to_string())
        
        # 导出为JSON（可选）
        export_json = input("\n是否导出为JSON格式？(y/n): ").strip().lower()
        if export_json == 'y':
            json_file = parquet_file.with_suffix('.json')
            df.to_json(json_file, orient='records', indent=2)
            print(f"✅ 已导出到: {json_file}")
            
    except Exception as e:
        print(f"❌ 读取Parquet文件失败: {e}")
        print(f"错误类型: {type(e).__name__}")

if __name__ == "__main__":
    view_parquet_data()