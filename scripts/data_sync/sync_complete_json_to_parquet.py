#!/usr/bin/env python3
"""
完整的JSON到Parquet同步脚本
保留所有字段，确保数据完整性
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import shutil

def sync_json_to_parquet_complete():
    """从JSON完整同步到Parquet，保留所有字段"""
    
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
    
    # 提取所有记录，保留完整字段
    records = []
    
    for model_name, model_data in json_data.get('models', {}).items():
        # 跳过llama-4-scout-17b
        if 'llama-4' in model_name.lower():
            print(f"  ⚠️ 跳过模型: {model_name}")
            continue
            
        for prompt_type, prompt_data in model_data.get('by_prompt_type', {}).items():
            # 跳过无效的单独flawed记录（没有具体类型的）
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
                        
                        # 创建完整记录，包含所有字段
                        record = {
                            # 标识字段
                            'model': model_name,
                            'prompt_type': prompt_type,
                            'tool_success_rate': float(tool_rate),
                            'difficulty': difficulty,
                            'task_type': task_type,
                            
                            # 基本统计字段（从JSON中的successful/partial/failed映射）
                            'total': task_data.get('total', 0),
                            'success': task_data.get('success', 0),
                            'full_success': task_data.get('full_success', 0),
                            'partial_success': task_data.get('partial_success', 0),
                            
                            # 如果JSON中使用了不同的字段名，进行映射
                            'successful': task_data.get('successful', task_data.get('success', 0)),
                            'partial': task_data.get('partial', task_data.get('partial_success', 0)),
                            'failed': task_data.get('failed', 0),
                            
                            # 成功率字段
                            'success_rate': task_data.get('success_rate', 0.0),
                            'full_success_rate': task_data.get('full_success_rate', 0.0),
                            'partial_success_rate': task_data.get('partial_success_rate', 0.0),
                            'partial_rate': task_data.get('partial_rate', task_data.get('partial_success_rate', 0.0)),
                            'failure_rate': task_data.get('failure_rate', 0.0),
                            'weighted_success_score': task_data.get('weighted_success_score', 0.0),
                            
                            # 执行指标
                            'avg_execution_time': task_data.get('avg_execution_time', 0.0),
                            'avg_turns': task_data.get('avg_turns', 0.0),
                            'avg_tool_calls': task_data.get('avg_tool_calls', 0.0),
                            'tool_coverage_rate': task_data.get('tool_coverage_rate', 0.0),
                            
                            # 质量分数
                            'avg_workflow_score': task_data.get('avg_workflow_score', 0.0),
                            'avg_phase2_score': task_data.get('avg_phase2_score', 0.0),
                            'avg_quality_score': task_data.get('avg_quality_score', 0.0),
                            'avg_final_score': task_data.get('avg_final_score', 0.0),
                            
                            # 错误统计
                            'total_errors': task_data.get('total_errors', 0),
                            'tool_call_format_errors': task_data.get('tool_call_format_errors', 0),
                            'timeout_errors': task_data.get('timeout_errors', 0),
                            'dependency_errors': task_data.get('dependency_errors', 0),
                            'parameter_config_errors': task_data.get('parameter_config_errors', 0),
                            'tool_selection_errors': task_data.get('tool_selection_errors', 0),
                            'sequence_order_errors': task_data.get('sequence_order_errors', 0),
                            'max_turns_errors': task_data.get('max_turns_errors', 0),
                            'other_errors': task_data.get('other_errors', 0),
                            
                            # 错误率
                            'tool_selection_error_rate': task_data.get('tool_selection_error_rate', 0.0),
                            'parameter_error_rate': task_data.get('parameter_error_rate', 0.0),
                            'sequence_error_rate': task_data.get('sequence_error_rate', 0.0),
                            'dependency_error_rate': task_data.get('dependency_error_rate', 0.0),
                            'timeout_error_rate': task_data.get('timeout_error_rate', 0.0),
                            'format_error_rate': task_data.get('format_error_rate', 0.0),
                            'max_turns_error_rate': task_data.get('max_turns_error_rate', 0.0),
                            'other_error_rate': task_data.get('other_error_rate', 0.0),
                            
                            # 辅助统计
                            'assisted_failure': task_data.get('assisted_failure', 0),
                            'assisted_success': task_data.get('assisted_success', 0),
                            'total_assisted_turns': task_data.get('total_assisted_turns', 0),
                            'tests_with_assistance': task_data.get('tests_with_assistance', 0),
                            'avg_assisted_turns': task_data.get('avg_assisted_turns', 0.0),
                            'assisted_success_rate': task_data.get('assisted_success_rate', 0.0),
                            'assistance_rate': task_data.get('assistance_rate', 0.0),
                            
                            # 时间戳
                            'last_updated': task_data.get('last_updated', datetime.now().isoformat())
                        }
                        
                        records.append(record)
    
    print(f"✅ 提取了 {len(records)} 条记录")
    
    if records:
        # 创建DataFrame
        df = pd.DataFrame(records)
        
        # 显示字段统计
        print(f"\n📊 字段统计:")
        print(f"  总字段数: {len(df.columns)}")
        
        # 按类别显示字段
        categories = {
            '标识字段': ['model', 'prompt_type', 'tool_success_rate', 'difficulty', 'task_type'],
            '基本统计': ['total', 'success', 'full_success', 'partial_success', 'successful', 'partial', 'failed'],
            '成功率': ['success_rate', 'full_success_rate', 'partial_success_rate', 'failure_rate', 'weighted_success_score'],
            '执行指标': ['avg_execution_time', 'avg_turns', 'avg_tool_calls', 'tool_coverage_rate'],
            '质量分数': ['avg_workflow_score', 'avg_phase2_score', 'avg_quality_score', 'avg_final_score'],
            '错误统计': ['total_errors', 'tool_call_format_errors', 'timeout_errors', 'dependency_errors', 
                        'parameter_config_errors', 'tool_selection_errors', 'sequence_order_errors', 
                        'max_turns_errors', 'other_errors'],
            '错误率': ['tool_selection_error_rate', 'parameter_error_rate', 'sequence_error_rate',
                      'dependency_error_rate', 'timeout_error_rate', 'format_error_rate', 
                      'max_turns_error_rate', 'other_error_rate'],
            '辅助统计': ['assisted_failure', 'assisted_success', 'total_assisted_turns',
                        'tests_with_assistance', 'avg_assisted_turns', 'assisted_success_rate', 'assistance_rate']
        }
        
        for category, fields in categories.items():
            existing = [f for f in fields if f in df.columns]
            print(f"\n  {category}: {len(existing)}/{len(fields)} 字段")
            if len(existing) < len(fields):
                missing = set(fields) - set(existing)
                print(f"    缺失: {missing}")
        
        # 保存到Parquet
        df.to_parquet(parquet_file, index=False)
        print(f"\n✅ 已保存到Parquet: {parquet_file}")
        print(f"  文件大小: {parquet_file.stat().st_size / 1024:.1f} KB")
        
        # 验证
        print(f"\n📊 验证结果:")
        df_verify = pd.read_parquet(parquet_file)
        print(f"  记录数: {len(df_verify)}")
        print(f"  字段数: {len(df_verify.columns)}")
        print(f"  模型数: {len(df_verify['model'].unique())}")
        
        # 数据质量检查
        print(f"\n✅ 数据质量检查:")
        if 'llama-4-scout-17b' in df_verify['model'].values:
            print(f"  ❌ 包含llama-4-scout-17b")
        else:
            print(f"  ✅ 不包含llama-4-scout-17b")
            
        if 'unknown' in df_verify['task_type'].values:
            print(f"  ❌ 包含unknown task_type")
        else:
            print(f"  ✅ 不包含unknown task_type")
            
        if 'flawed' in df_verify['prompt_type'].values:
            print(f"  ❌ 包含单独的flawed prompt_type")
        else:
            print(f"  ✅ 不包含单独的flawed prompt_type")
        
        # 检查关键字段的非零值
        key_fields = ['total_errors', 'avg_workflow_score', 'assisted_success', 'tool_selection_errors']
        print(f"\n  关键字段非零记录数:")
        for field in key_fields:
            if field in df_verify.columns:
                non_zero = df_verify[df_verify[field] != 0]
                percentage = (len(non_zero) / len(df_verify)) * 100
                print(f"    {field}: {len(non_zero)}/{len(df_verify)} ({percentage:.1f}%)")
    else:
        print("❌ 没有找到有效记录")

if __name__ == "__main__":
    sync_json_to_parquet_complete()