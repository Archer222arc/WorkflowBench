#!/usr/bin/env python3
"""
正确迁移JSON汇总数据到Parquet格式
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime

print("=" * 70)
print("          JSON到Parquet数据迁移")
print("=" * 70)

# 路径设置
json_path = Path("pilot_bench_cumulative_results/master_database.json")
parquet_path = Path("pilot_bench_parquet_data/test_results.parquet")
backup_path = parquet_path.with_suffix('.parquet.backup_migration')

if not json_path.exists():
    print("❌ JSON文件不存在")
    exit(1)

# 1. 读取JSON数据
print("\n1️⃣ 读取JSON数据...")
with open(json_path, 'r') as f:
    json_data = json.load(f)

print(f"   版本: {json_data.get('version', 'unknown')}")
print(f"   模型数: {len(json_data.get('models', {}))}")

# 2. 提取汇总记录
print("\n2️⃣ 提取汇总记录...")
records = []

for model_name, model_data in json_data.get('models', {}).items():
    # 提取overall_stats
    if 'overall_stats' in model_data:
        overall = model_data['overall_stats']
        record = {
            'model': model_name,
            'prompt_type': 'overall',
            'tool_success_rate': None,
            'difficulty': 'overall',
            'task_type': 'overall',
            # 汇总统计
            'total': overall.get('total_tests', 0),
            'successful': overall.get('total_success', 0),
            'partial': overall.get('total_partial', 0),
            'failed': overall.get('total_failure', 0),
            'success_rate': overall.get('success_rate', 0),
            'partial_rate': overall.get('partial_rate', 0),
            'failure_rate': overall.get('failure_rate', 0),
            'weighted_success_score': overall.get('weighted_success_score', 0),
            'avg_execution_time': overall.get('avg_execution_time', 0),
            'avg_turns': overall.get('avg_turns', 0),
            'tool_coverage_rate': overall.get('tool_coverage_rate', 0),
            'avg_tool_calls': overall.get('avg_tool_calls', 0),
            'source': 'master_database.json',
            'import_time': datetime.now().isoformat()
        }
        records.append(record)
    
    # 提取细粒度统计
    if 'by_prompt_type' in model_data:
        for prompt_type, prompt_data in model_data['by_prompt_type'].items():
            # prompt级别汇总
            if isinstance(prompt_data, dict) and 'total_tests' in prompt_data:
                record = {
                    'model': model_name,
                    'prompt_type': prompt_type,
                    'tool_success_rate': None,
                    'difficulty': 'all',
                    'task_type': 'all',
                    'total': prompt_data.get('total_tests', 0),
                    'successful': prompt_data.get('total_success', 0),
                    'success_rate': prompt_data.get('success_rate', 0),
                    'source': 'master_database.json',
                    'import_time': datetime.now().isoformat()
                }
                records.append(record)
            
            # 更细粒度的统计
            if 'by_tool_success_rate' in prompt_data:
                for rate, rate_data in prompt_data['by_tool_success_rate'].items():
                    if 'by_difficulty' in rate_data:
                        for diff, diff_data in rate_data['by_difficulty'].items():
                            if 'by_task_type' in diff_data:
                                for task, task_data in diff_data['by_task_type'].items():
                                    # 创建一条汇总记录
                                    record = {
                                        'model': model_name,
                                        'prompt_type': prompt_type,
                                        'tool_success_rate': float(rate),
                                        'difficulty': diff,
                                        'task_type': task,
                                        # 汇总统计字段
                                        'total': task_data.get('total', 0),
                                        'successful': task_data.get('successful', 0),
                                        'partial': task_data.get('partial', 0),
                                        'failed': task_data.get('failed', 0),
                                        'success_rate': task_data.get('success_rate', 0),
                                        'partial_rate': task_data.get('partial_rate', 0),
                                        'failure_rate': task_data.get('failure_rate', 0),
                                        'weighted_success_score': task_data.get('weighted_success_score', 0),
                                        'avg_execution_time': task_data.get('avg_execution_time', 0),
                                        'avg_turns': task_data.get('avg_turns', 0),
                                        'tool_coverage_rate': task_data.get('tool_coverage_rate', 0),
                                        'avg_tool_calls': task_data.get('avg_tool_calls', 0),
                                        # 元数据
                                        'source': 'master_database.json',
                                        'import_time': datetime.now().isoformat()
                                    }
                                    records.append(record)

print(f"   提取了 {len(records)} 条汇总记录")

# 3. 备份现有文件
if parquet_path.exists():
    print("\n3️⃣ 备份现有Parquet文件...")
    import shutil
    shutil.copy2(parquet_path, backup_path)
    print(f"   ✅ 备份到: {backup_path.name}")

# 4. 保存到Parquet
print("\n4️⃣ 保存到Parquet...")
df = pd.DataFrame(records)

# 确保数据类型正确
numeric_columns = ['total', 'successful', 'partial', 'failed', 
                  'success_rate', 'partial_rate', 'failure_rate',
                  'weighted_success_score', 'avg_execution_time', 
                  'avg_turns', 'tool_coverage_rate', 'avg_tool_calls']

for col in numeric_columns:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

df.to_parquet(parquet_path, index=False)
print(f"   ✅ 保存了 {len(df)} 条记录")

# 5. 验证
print("\n5️⃣ 验证迁移结果...")
verify_df = pd.read_parquet(parquet_path)
print(f"   记录数: {len(verify_df)}")
print(f"   模型数: {verify_df['model'].nunique()}")

# 显示示例
print("\n   示例记录:")
sample = verify_df[verify_df['difficulty'] != 'overall'].head(3)
for _, row in sample.iterrows():
    print(f"     {row['model']} | {row['prompt_type']} | {row['difficulty']} | {row['task_type']}")
    print(f"       总计: {row['total']}, 成功率: {row['success_rate']:.2%}")

print("\n" + "=" * 70)
print("迁移完成！")
print(f"数据已保存到: {parquet_path}")
print("\n注意：这是汇总统计数据，不是单个测试记录")
print("=" * 70)