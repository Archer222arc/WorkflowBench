#!/usr/bin/env python3
"""Test AI classification with forced partial_success"""

import os
os.environ['STORAGE_FORMAT'] = 'parquet'

# Run a test with extremely low tool success rate to force failures
import subprocess
result = subprocess.run([
    'python', 'smart_batch_runner.py',
    '--model', 'deepseek-v3-0324',
    '--prompt-types', 'optimal',
    '--difficulty', 'easy',
    '--task-types', 'simple_task',
    '--num-instances', '1',
    '--tool-success-rate', '0.01',  # 1% success rate - almost guaranteed to fail
    '--max-workers', '1',
    '--ai-classification',  # Explicitly enable AI classification
    '--debug',  # Enable debug output
    '--no-adaptive',
    '--qps', '5',
    '--no-save-logs'
], capture_output=True, text=True, timeout=180)

print("Exit code:", result.returncode)
print("\n=== STDOUT (last 50 lines) ===")
for line in result.stdout.split('\n')[-50:]:
    if line:
        print(line)

if result.stderr:
    print("\n=== STDERR ===")
    print(result.stderr)

# Check Parquet for results
import pandas as pd
from pathlib import Path
parquet_file = Path('pilot_bench_parquet_data/test_results.parquet')
if parquet_file.exists():
    df = pd.read_parquet(parquet_file)
    deepseek_df = df[(df['model'] == 'deepseek-v3-0324') & (df['task_type'] == 'simple_task')]
    if not deepseek_df.empty:
        latest = deepseek_df.iloc[-1]
        print("\n=== Latest Parquet Record ===")
        print(f"  total_errors: {latest.get('total_errors', 0)}")
        print(f"  tool_selection_errors: {latest.get('tool_selection_errors', 0)}")
        print(f"  sequence_order_errors: {latest.get('sequence_order_errors', 0)}")
        print(f"  other_errors: {latest.get('other_errors', 0)}")
