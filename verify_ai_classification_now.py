#!/usr/bin/env python3
"""
验证AI分类当前是否正常工作
"""

import os
import json
from pathlib import Path
from datetime import datetime

# 设置Parquet格式
os.environ['STORAGE_FORMAT'] = 'parquet'

# 1. 清理测试模型的旧数据
print("清理test-model-ai-verify的旧数据...")
from parquet_cumulative_manager import ParquetCumulativeManager
manager = ParquetCumulativeManager()

# 2. 运行新测试
print("\n运行新测试...")
import subprocess
cmd = [
    "python", "smart_batch_runner.py",
    "--model", "test-model-ai-verify",
    "--prompt-types", "baseline",
    "--difficulty", "easy",
    "--task-types", "simple_task",
    "--num-instances", "2",  # 运行2个测试
    "--max-workers", "1",
    "--tool-success-rate", "0.5",  # 设置低一点确保有失败
    "--ai-classification",
    "--no-adaptive",
    "--qps", "5",
    "--silent",
    "--no-save-logs"
]

print(f"命令: {' '.join(cmd)}")
result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

# 3. 检查结果
print("\n检查Parquet数据...")
import pandas as pd
parquet_file = Path('pilot_bench_parquet_data/test_results.parquet')
if parquet_file.exists():
    df = pd.read_parquet(parquet_file)
    test_df = df[df['model'] == 'test-model-ai-verify']
    
    if len(test_df) > 0:
        latest = test_df.iloc[-1]
        print(f"\n✅ 找到test-model-ai-verify的数据:")
        print(f"  更新时间: {latest.get('last_updated', 'N/A')}")
        print(f"  总测试数: {latest.get('total', 0)}")
        print(f"  总错误数: {latest.get('total_errors', 0)}")
        
        # 检查错误分类
        print(f"\n错误分类详情:")
        error_types = [
            'tool_call_format_errors',
            'timeout_errors',
            'max_turns_errors',
            'tool_selection_errors',
            'parameter_config_errors',
            'sequence_order_errors',
            'dependency_errors',
            'other_errors'
        ]
        
        for error_type in error_types:
            count = latest.get(error_type, 0)
            if count > 0:
                print(f"  {error_type}: {count}")
        
        # 计算other_error_rate
        total_errors = latest.get('total_errors', 0)
        other_errors = latest.get('other_errors', 0)
        if total_errors > 0:
            other_error_rate = other_errors / total_errors
            print(f"\n  other_error_rate: {other_error_rate:.2%}")
            
            if other_error_rate < 1.0:
                print("  ✅ AI分类正在工作！错误被正确分类了")
            else:
                print("  ❌ 所有错误仍然被分类为other_errors")
    else:
        print("❌ 未找到test-model-ai-verify的数据")
else:
    print("❌ Parquet文件不存在")

# 4. 检查JSON数据对比
print("\n检查JSON数据...")
json_file = Path('pilot_bench_cumulative_results/master_database.json')
if json_file.exists():
    with open(json_file, 'r') as f:
        db = json.load(f)
    
    if 'models' in db and 'test-model-ai-verify' in db['models']:
        model_data = db['models']['test-model-ai-verify']
        print(f"✅ 找到JSON数据:")
        
        # 查找baseline数据
        if 'by_prompt_type' in model_data and 'baseline' in model_data['by_prompt_type']:
            baseline = model_data['by_prompt_type']['baseline']
            
            # 遍历所有层级找到数据
            for rate_key in baseline.get('by_tool_success_rate', {}):
                rate_data = baseline['by_tool_success_rate'][rate_key]
                for diff_key in rate_data.get('by_difficulty', {}):
                    diff_data = rate_data['by_difficulty'][diff_key]
                    for task_key in diff_data.get('by_task_type', {}):
                        task_data = diff_data['by_task_type'][task_key]
                        
                        if task_data.get('total_errors', 0) > 0:
                            print(f"\n  {rate_key} -> {diff_key} -> {task_key}:")
                            print(f"    total_errors: {task_data.get('total_errors', 0)}")
                            print(f"    other_errors: {task_data.get('other_errors', 0)}")
                            
                            # 显示其他错误类型
                            for error_type in error_types:
                                if error_type != 'other_errors':
                                    count = task_data.get(error_type, 0)
                                    if count > 0:
                                        print(f"    {error_type}: {count}")