#!/usr/bin/env python3
"""
查看Parquet数据文件的内容
"""

import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path
import json
import sys

def view_parquet_data(format="table"):
    """查看Parquet数据"""
    parquet_file = Path("pilot_bench_parquet_data/test_results.parquet")
    
    if not parquet_file.exists():
        print(f"❌ Parquet文件不存在: {parquet_file}")
        return
    
    # 读取Parquet文件
    df = pd.read_parquet(parquet_file)
    
    print(f"📊 Parquet数据文件: {parquet_file}")
    print(f"📏 数据量: {len(df)} 条记录")
    print(f"📋 列: {list(df.columns)}")
    print("-" * 80)
    
    if format == "table":
        # 表格格式显示
        print("\n最近10条记录：")
        print(df.tail(10).to_string())
        
    elif format == "summary":
        # 汇总统计
        print("\n📈 模型统计：")
        model_stats = df.groupby('model').agg({
            'success': ['count', 'sum', 'mean'],
            'execution_time': 'mean'
        }).round(3)
        print(model_stats)
        
        print("\n📊 按任务类型统计：")
        task_stats = df.groupby('task_type').agg({
            'success': ['count', 'sum', 'mean']
        }).round(3)
        print(task_stats)
        
        print("\n🎯 按Prompt类型统计：")
        prompt_stats = df.groupby('prompt_type').agg({
            'success': ['count', 'sum', 'mean']
        }).round(3)
        print(prompt_stats)
        
    elif format == "json":
        # 导出为JSON查看
        json_data = df.tail(5).to_dict('records')
        print("\n最近5条记录（JSON格式）：")
        print(json.dumps(json_data, indent=2, default=str))
    
    # 检查增量文件
    incremental_dir = Path("pilot_bench_parquet_data/incremental")
    if incremental_dir.exists():
        incremental_files = list(incremental_dir.glob("*.parquet"))
        if incremental_files:
            print(f"\n📁 未合并的增量文件: {len(incremental_files)} 个")
            for f in incremental_files[:5]:  # 只显示前5个
                print(f"   - {f.name}")

def export_to_json():
    """将Parquet导出为JSON（用于查看）"""
    parquet_file = Path("pilot_bench_parquet_data/test_results.parquet")
    
    if not parquet_file.exists():
        print(f"❌ Parquet文件不存在")
        return
    
    df = pd.read_parquet(parquet_file)
    
    # 转换为层次化JSON结构（类似master_database.json）
    result = {
        "version": "3.0",
        "models": {},
        "summary": {
            "total_tests": len(df),
            "total_success": int(df['success'].sum()),
            "models_tested": df['model'].unique().tolist()
        }
    }
    
    # 按模型分组
    for model in df['model'].unique():
        model_df = df[df['model'] == model]
        result['models'][model] = {
            "total_tests": len(model_df),
            "success_rate": float(model_df['success'].mean()),
            "by_prompt_type": {}
        }
        
        # 按prompt_type分组
        for prompt_type in model_df['prompt_type'].unique():
            prompt_df = model_df[model_df['prompt_type'] == prompt_type]
            result['models'][model]['by_prompt_type'][prompt_type] = {
                "total": len(prompt_df),
                "successful": int(prompt_df['success'].sum()),
                "success_rate": float(prompt_df['success'].mean())
            }
    
    # 保存为JSON文件
    output_file = Path("pilot_bench_parquet_data/test_results.parquet.as.json")
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"✅ 已导出到: {output_file}")
    return output_file

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="查看Parquet数据")
    parser.add_argument("--format", choices=["table", "summary", "json"], 
                       default="summary", help="显示格式")
    parser.add_argument("--export", action="store_true", 
                       help="导出为JSON文件")
    
    args = parser.parse_args()
    
    if args.export:
        export_to_json()
    else:
        view_parquet_data(args.format)