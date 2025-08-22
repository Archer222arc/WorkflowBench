#!/usr/bin/env python3
"""Simple test to analyze error classification issue"""

import json
from pathlib import Path

# Read the master database
db_path = Path("pilot_bench_cumulative_results/master_database.json")
with open(db_path, 'r') as f:
    data = json.load(f)

print("Current Database Analysis")
print("="*60)

# Check test groups
test_groups = data.get('test_groups', {})
total_groups = len(test_groups)
total_tests = 0
total_failures = 0

# Analyze each group
group_summary = {}
for group_key, group_data in test_groups.items():
    stats = group_data.get('statistics', {})
    total = stats.get('total', 0)
    failures = stats.get('failure', 0)
    
    total_tests += total
    total_failures += failures
    
    # Extract group components
    parts = group_key.split('_')
    if 'flawed' in parts:
        # Find flawed type
        flawed_idx = parts.index('flawed')
        if flawed_idx + 1 < len(parts):
            if parts[flawed_idx + 2] == 'flawed':
                # Format: model_task_flawed_difficulty_flawed_type
                prompt_type = f"flawed_{parts[-1]}"
            else:
                prompt_type = 'flawed'
        else:
            prompt_type = 'flawed'
    else:
        # Find prompt type (baseline, cot, optimal)
        for pt in ['baseline', 'cot', 'optimal']:
            if pt in parts:
                prompt_type = pt
                break
        else:
            prompt_type = 'unknown'
    
    if prompt_type not in group_summary:
        group_summary[prompt_type] = {'total': 0, 'failures': 0}
    
    group_summary[prompt_type]['total'] += total
    group_summary[prompt_type]['failures'] += failures

print(f"\nOverall Statistics:")
print(f"  Total test groups: {total_groups}")
print(f"  Total tests run: {total_tests}")
print(f"  Total failures: {total_failures}")
print(f"  Overall failure rate: {total_failures/total_tests*100:.1f}%" if total_tests > 0 else "N/A")

print(f"\nBy Prompt Type Summary:")
for prompt_type in sorted(group_summary.keys()):
    stats = group_summary[prompt_type]
    failure_rate = stats['failures'] / stats['total'] * 100 if stats['total'] > 0 else 0
    print(f"  {prompt_type:30s}: {stats['failures']:3d}/{stats['total']:3d} failures ({failure_rate:5.1f}%)")

# Check model statistics
print(f"\nModel-Level Statistics:")
models = data.get('models', {})
for model_name, model_data in models.items():
    print(f"\n  Model: {model_name}")
    
    # Check old format fields
    if 'total_tests' in model_data:
        print(f"    Total tests (old format): {model_data.get('total_tests', 0)}")
        print(f"    Total failures (old format): {model_data.get('total_failure', 0)}")
    
    # Check new format fields
    if 'overall_errors' in model_data:
        overall_errors = model_data['overall_errors']
        print(f"    Overall errors (new format):")
        print(f"      total_errors: {overall_errors.get('total_errors', 0)}")
        
        # Count categorized errors
        categorized = sum([
            overall_errors.get('tool_call_format_errors', 0),
            overall_errors.get('max_turns_errors', 0),
            overall_errors.get('timeout_errors', 0),
            overall_errors.get('tool_selection_errors', 0),
            overall_errors.get('parameter_config_errors', 0),
            overall_errors.get('sequence_order_errors', 0),
            overall_errors.get('dependency_errors', 0),
            overall_errors.get('other_errors', 0)
        ])
        print(f"      Categorized errors: {categorized}")
        print(f"      Uncategorized: {overall_errors.get('total_errors', 0) - categorized}")
    
    # Check prompt-level statistics
    by_prompt = model_data.get('by_prompt_type', {})
    if by_prompt:
        print(f"    Prompt-level statistics:")
        for prompt_type, prompt_data in by_prompt.items():
            # Extract counts from different formats
            if isinstance(prompt_data, dict):
                if 'total_tests' in prompt_data:
                    total = prompt_data['total_tests']
                    failures = prompt_data.get('total_failure', 0)
                elif 'success_metrics' in prompt_data:
                    metrics = prompt_data['success_metrics']
                    total = metrics.get('total_tests', 0)
                    failures = metrics.get('failure', 0)
                else:
                    total = prompt_data.get('total', 0)
                    failures = prompt_data.get('failures', 0)
                
                if total > 0:
                    print(f"      {prompt_type}: {failures}/{total} failures")
                    
                    # Check error metrics
                    if 'error_metrics' in prompt_data:
                        err_metrics = prompt_data['error_metrics']
                        total_errors = err_metrics.get('total_errors', 0)
                        if total_errors > 0:
                            print(f"        Error metrics: {total_errors} total errors")

print("\n" + "="*60)
print("Analysis Complete")

# Identify the discrepancy
print("\nDISCREPANCY ANALYSIS:")
print(f"  Test groups report: {total_failures} failures")
print(f"  Model statistics report: {models.get('qwen2.5-3b-instruct', {}).get('total_failure', 0)} failures")

# Check if instances are stored
has_instances = False
for group_key, group_data in test_groups.items():
    instances = group_data.get('instances', [])
    if instances:
        has_instances = True
        break

print(f"  Test instances stored: {'Yes' if has_instances else 'No (this is why errors are not classified)'}")

if not has_instances:
    print("\nROOT CAUSE:")
    print("  The CumulativeTestManager is not storing test instances to save space.")
    print("  Without instances, error messages cannot be passed to the error classifier.")
    print("  This is why all errors show as 0 in the classification statistics.")
    print("\nSOLUTION:")
    print("  Need to either:")
    print("  1. Store instances (will increase database size)")
    print("  2. Classify errors immediately during test execution and store only counts")
    print("  3. Use a separate error tracking mechanism during batch execution")