#!/usr/bin/env python3
"""
测试AI分类结果是否正确保存到Parquet
"""

import os
os.environ['STORAGE_FORMAT'] = 'parquet'

from batch_test_runner import BatchTestRunner, TestTask

# 创建runner，显式启用AI分类
runner = BatchTestRunner(
    debug=True,
    silent=False,
    save_logs=False,
    use_ai_classification=True  # 显式启用
)

print(f"AI分类器已初始化: {runner.ai_classifier is not None}")

# 创建一个会失败的测试任务
task = TestTask(
    model='gpt-4o-mini',
    task_type='simple_task',
    prompt_type='baseline',
    difficulty='easy',
    tool_success_rate=0.0  # 设置为0，确保失败
)

print(f"\n运行测试 (tool_success_rate=0.0，预期失败)...")

# 运行单个测试 - 使用正确的方法
runner._lazy_init()
results = runner.run_concurrent_batch([task], workers=1)

print(f"\n测试完成，结果数量: {len(results)}")

if results:
    result = results[0]
    print(f"测试成功: {result.get('success', False)}")
    print(f"成功级别: {result.get('success_level', 'unknown')}")
    print(f"错误消息: {result.get('error', 'None')}")

print("\n检查Parquet数据中的错误分类...")
from pathlib import Path
import pandas as pd

parquet_file = Path('pilot_bench_parquet_data/test_results.parquet')
if parquet_file.exists():
    df = pd.read_parquet(parquet_file)
    
    # 找最新的gpt-4o-mini记录
    gpt4_df = df[df['model'] == 'gpt-4o-mini']
    if len(gpt4_df) > 0:
        # 按last_updated排序找最新的
        gpt4_df = gpt4_df.sort_values('last_updated')
        latest = gpt4_df.iloc[-1]
        print(f"\n最新的gpt-4o-mini记录:")
        print(f"  task_type: {latest['task_type']}")
        print(f"  prompt_type: {latest['prompt_type']}")
        print(f"  last_updated: {latest['last_updated']}")
        print(f"  total_errors: {latest.get('total_errors', 0)}")
        print(f"  other_errors: {latest.get('other_errors', 0)}")
        print(f"  tool_selection_errors: {latest.get('tool_selection_errors', 0)}")
        print(f"  sequence_order_errors: {latest.get('sequence_order_errors', 0)}")
        print(f"  timeout_errors: {latest.get('timeout_errors', 0)}")
        
        # 查看所有错误相关字段
        error_fields = [col for col in latest.index if 'error' in col.lower()]
        print(f"\n所有错误相关字段:")
        for field in error_fields:
            value = latest[field]
            if pd.notna(value) and value != 0 and value != 0.0:
                print(f"  {field}: {value}")
