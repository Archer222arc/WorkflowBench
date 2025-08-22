#!/usr/bin/env python3
"""
Debug script to trace error classification data flow for DeepSeek tests
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime

def analyze_error_classification_flow():
    print("=" * 80)
    print("DeepSeek Error Classification Data Flow Analysis")
    print("=" * 80)
    
    # 1. Check Parquet data
    print("\n1. Current Parquet Data:")
    print("-" * 40)
    parquet_file = Path('pilot_bench_parquet_data/test_results.parquet')
    if parquet_file.exists():
        df = pd.read_parquet(parquet_file)
        deepseek_df = df[df['model'].str.contains('DeepSeek', na=False)]
        
        # Count records with errors
        error_records = deepseek_df[deepseek_df['total_errors'] > 0]
        print(f"Total DeepSeek records: {len(deepseek_df)}")
        print(f"Records with errors: {len(error_records)}")
        
        # Check error classification distribution
        if len(error_records) > 0:
            print("\nError classification distribution:")
            error_types = ['timeout_errors', 'tool_selection_errors', 'parameter_config_errors',
                          'sequence_order_errors', 'dependency_errors', 'tool_call_format_errors',
                          'max_turns_errors', 'other_errors']
            
            for error_type in error_types:
                if error_type in error_records.columns:
                    non_zero = error_records[error_records[error_type] > 0]
                    if len(non_zero) > 0:
                        print(f"  {error_type}: {len(non_zero)} records, total: {non_zero[error_type].sum()}")
    
    # 2. Check JSON data
    print("\n2. JSON Database Data:")
    print("-" * 40)
    json_file = Path('pilot_bench_cumulative_results/master_database.json')
    if json_file.exists():
        with open(json_file, 'r') as f:
            db = json.load(f)
        
        if 'models' in db:
            for model_name in ['DeepSeek-V3-0324', 'DeepSeek-R1-0528']:
                if model_name in db['models']:
                    model_data = db['models'][model_name]
                    print(f"\n{model_name}:")
                    
                    # Check experiment metrics
                    if 'experiment_metrics' in model_data:
                        metrics = model_data['experiment_metrics']
                        print("  Experiment metrics:")
                        for key in ['total_errors', 'timeout_errors', 'tool_selection_errors',
                                   'parameter_config_errors', 'sequence_order_errors']:
                            if key in metrics:
                                print(f"    {key}: {metrics[key]}")
                    
                    # Check by_prompt_type data
                    if 'by_prompt_type' in model_data:
                        for prompt_type in ['optimal', 'baseline']:
                            if prompt_type in model_data['by_prompt_type']:
                                prompt_data = model_data['by_prompt_type'][prompt_type]
                                print(f"\n  {prompt_type} prompt:")
                                
                                # Navigate to specific task types
                                if 'by_tool_success_rate' in prompt_data:
                                    for rate in prompt_data['by_tool_success_rate']:
                                        rate_data = prompt_data['by_tool_success_rate'][rate]
                                        if 'by_difficulty' in rate_data:
                                            for diff in rate_data['by_difficulty']:
                                                diff_data = rate_data['by_difficulty'][diff]
                                                if 'by_task_type' in diff_data:
                                                    for task in diff_data['by_task_type']:
                                                        task_data = diff_data['by_task_type'][task]
                                                        if task_data.get('total_errors', 0) > 0:
                                                            print(f"    {rate}/{diff}/{task}:")
                                                            print(f"      total_errors: {task_data.get('total_errors', 0)}")
                                                            for error_type in ['timeout_errors', 'tool_selection_errors',
                                                                             'parameter_config_errors']:
                                                                if error_type in task_data and task_data[error_type] > 0:
                                                                    print(f"      {error_type}: {task_data[error_type]}")
    
    # 3. Check recent test logs
    print("\n3. Recent Test Logs Analysis:")
    print("-" * 40)
    logs_dir = Path('logs')
    recent_logs = sorted(logs_dir.glob('batch_test_*.log'), key=lambda x: x.stat().st_mtime, reverse=True)[:5]
    
    for log_file in recent_logs:
        with open(log_file, 'r') as f:
            content = f.read()
        
        if 'DeepSeek' in content:
            # Count AI classification occurrences
            ai_class_count = content.count('[AI_DEBUG] AI分类结果:')
            partial_count = content.count('partial_success')
            
            if ai_class_count > 0 or partial_count > 0:
                print(f"\n{log_file.name}:")
                print(f"  AI classifications: {ai_class_count}")
                print(f"  Partial success: {partial_count}")
                
                # Extract AI classification results
                if '[AI_DEBUG] AI分类结果:' in content:
                    import re
                    pattern = r'\[AI_DEBUG\] AI分类结果: category=(\w+), confidence=([\d.]+)'
                    matches = re.findall(pattern, content)
                    if matches:
                        print("  Classifications found:")
                        categories = {}
                        for category, confidence in matches:
                            categories[category] = categories.get(category, 0) + 1
                        for cat, count in categories.items():
                            print(f"    {cat}: {count}")
    
    # 4. Check workflow results
    print("\n4. Recent Workflow Results:")
    print("-" * 40)
    results_dir = Path('workflow_quality_results/test_logs')
    if results_dir.exists():
        recent_results = sorted(results_dir.glob('deepseek*.json'), 
                               key=lambda x: x.stat().st_mtime, reverse=True)[:5]
        
        for result_file in recent_results:
            with open(result_file, 'r') as f:
                result = json.load(f)
            
            if result.get('success') == 'partial_success':
                print(f"\n{result_file.name}:")
                print(f"  Success: {result.get('success')}")
                print(f"  AI error category: {result.get('ai_error_category', 'N/A')}")
                print(f"  Error message: {result.get('error_message', 'N/A')[:100]}")
    
    print("\n" + "=" * 80)
    print("Analysis Complete")
    print("=" * 80)

if __name__ == "__main__":
    analyze_error_classification_flow()