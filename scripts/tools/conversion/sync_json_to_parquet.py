#!/usr/bin/env python3
"""
将JSON数据库同步到Parquet格式
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from parquet_cumulative_manager import ParquetCumulativeManager

def sync_json_to_parquet():
    """将JSON数据同步到Parquet"""
    
    # 读取JSON数据
    json_file = Path('pilot_bench_cumulative_results/master_database.json')
    if not json_file.exists():
        print("❌ JSON文件不存在")
        return
    
    print("📖 读取JSON数据...")
    with open(json_file, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    # 创建Parquet管理器
    print("🔧 初始化Parquet管理器...")
    manager = ParquetCumulativeManager()
    
    # 统计信息
    total_records = 0
    models_processed = []
    
    # 遍历所有模型数据
    if 'models' in json_data:
        for model_name, model_data in json_data['models'].items():
            print(f"\n处理模型: {model_name}")
            model_records = 0
            
            # 遍历prompt_type
            for prompt_type, prompt_data in model_data.get('by_prompt_type', {}).items():
                
                # 遍历tool_success_rate
                for tool_rate, rate_data in prompt_data.get('by_tool_success_rate', {}).items():
                    
                    # 遍历difficulty
                    for difficulty, diff_data in rate_data.get('by_difficulty', {}).items():
                        
                        # 遍历task_type
                        for task_type, task_data in diff_data.get('by_task_type', {}).items():
                            
                            # 只处理有数据的记录
                            if task_data.get('total', 0) > 0:
                                # 构建汇总记录 - 匹配ParquetCumulativeManager的结构
                                total = task_data.get('total', 0)
                                successful = task_data.get('successful', 0)
                                partial = task_data.get('partial', 0)
                                
                                summary = {
                                    'model': model_name,
                                    'prompt_type': prompt_type,
                                    'tool_success_rate': float(tool_rate),
                                    'difficulty': difficulty,
                                    'task_type': task_type,
                                    
                                    # 计数器 (ParquetCumulativeManager期望的字段)
                                    'total': total,
                                    'success': successful,  # JSON中的successful -> success
                                    'full_success': successful - partial,  # 完全成功 = 成功 - 部分成功
                                    'partial_success': partial,
                                    
                                    # 累加器（用于计算平均值）
                                    '_total_execution_time': task_data.get('avg_execution_time', 0.0) * total,
                                    '_total_turns': task_data.get('avg_turns', 0.0) * total,
                                    '_total_tool_calls': task_data.get('avg_tool_calls', 0.0) * total,
                                    '_total_tool_coverage': task_data.get('tool_coverage_rate', 0.0) * total,
                                    '_total_workflow_score': task_data.get('avg_workflow_score', 0.0) * total,
                                    '_total_phase2_score': task_data.get('avg_phase2_score', 0.0) * total,
                                    '_total_quality_score': task_data.get('avg_quality_score', 0.0) * total,
                                    '_total_final_score': task_data.get('avg_final_score', 0.0) * total,
                                    
                                    # 已计算的率（可选，_flush_summary_to_disk会重新计算）
                                    'success_rate': task_data.get('success_rate', 0.0),
                                    'partial_rate': task_data.get('partial_rate', 0.0),
                                    'failure_rate': task_data.get('failure_rate', 0.0),
                                    'weighted_success_score': task_data.get('weighted_success_score', 0.0),
                                    
                                    # 错误计数（初始化为0）
                                    'total_errors': 0,
                                    'tool_call_format_errors': 0,
                                    'timeout_errors': 0,
                                    'dependency_errors': 0,
                                    'parameter_config_errors': 0,
                                    'tool_selection_errors': 0,
                                    'sequence_order_errors': 0,
                                    'max_turns_errors': 0,
                                    'other_errors': 0,
                                    
                                    # 辅助统计（初始化为0）
                                    'assisted_failure': 0,
                                    'assisted_success': 0,
                                    'total_assisted_turns': 0,
                                    'tests_with_assistance': 0,
                                }
                                
                                # 添加到缓存
                                key = f"{model_name}|{prompt_type}|{tool_rate}|{difficulty}|{task_type}"
                                if not hasattr(manager, '_summary_cache'):
                                    manager._summary_cache = {}
                                manager._summary_cache[key] = summary
                                
                                model_records += 1
                                total_records += 1
            
            if model_records > 0:
                print(f"  ✅ 添加了 {model_records} 条记录")
                models_processed.append(model_name)
    
    # 刷新到磁盘
    if total_records > 0:
        print(f"\n💾 将 {total_records} 条记录写入Parquet...")
        manager._flush_buffer()
        
        # 验证写入
        parquet_file = Path('pilot_bench_parquet_data/test_results.parquet')
        if parquet_file.exists():
            df = pd.read_parquet(parquet_file)
            print(f"\n✅ 成功！Parquet文件现有 {len(df)} 条记录")
            print(f"   处理的模型: {', '.join(models_processed)}")
            
            # 显示一些样本数据
            print("\n📊 样本数据:")
            for model in models_processed[:3]:
                model_df = df[df['model'] == model]
                if len(model_df) > 0:
                    print(f"   {model}: {len(model_df)} 条记录")
                    sample = model_df.iloc[0]
                    print(f"     - {sample['prompt_type']}/{sample['difficulty']}/{sample['task_type']}: "
                          f"总数={sample['total']:.0f}, 成功率={sample['success_rate']:.1%}")
    else:
        print("⚠️ 没有找到需要同步的数据")

if __name__ == "__main__":
    sync_json_to_parquet()