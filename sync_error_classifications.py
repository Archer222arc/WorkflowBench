#!/usr/bin/env python3
"""Sync error classifications from JSON to Parquet"""

import json
import pandas as pd
from pathlib import Path

def sync_error_classifications():
    # Load JSON database
    json_path = Path('pilot_bench_cumulative_results/master_database.json')
    with open(json_path, 'r') as f:
        json_db = json.load(f)
    
    # Load Parquet file
    parquet_path = Path('pilot_bench_parquet_data/test_results.parquet')
    if not parquet_path.exists():
        print("Parquet file not found")
        return
    
    df = pd.read_parquet(parquet_path)
    print(f"Loaded {len(df)} records from Parquet")
    
    # Find records in JSON with error classifications
    updates = 0
    for model_name, model_data in json_db.get('models', {}).items():
        for prompt_type, prompt_data in model_data.get('by_prompt_type', {}).items():
            for rate, rate_data in prompt_data.get('by_tool_success_rate', {}).items():
                for diff, diff_data in rate_data.get('by_difficulty', {}).items():
                    for task, task_data in diff_data.get('by_task_type', {}).items():
                        # Check if this has error classifications
                        if task_data.get('total_errors', 0) > 0:
                            # Find corresponding Parquet record
                            mask = (
                                (df['model'] == model_name) &
                                (df['prompt_type'] == prompt_type) &
                                (df['tool_success_rate'] == float(rate)) &
                                (df['difficulty'] == diff) &
                                (df['task_type'] == task)
                            )
                            
                            if mask.any():
                                # Update error classifications
                                for error_type in ['tool_selection_errors', 'parameter_config_errors', 
                                                 'sequence_order_errors', 'dependency_errors', 
                                                 'timeout_errors', 'tool_call_format_errors', 
                                                 'max_turns_errors', 'other_errors']:
                                    df.loc[mask, error_type] = task_data.get(error_type, 0)
                                
                                updates += 1
                                print(f"Updated {model_name}/{task}: {task_data.get('total_errors')} errors")
    
    if updates > 0:
        # Save updated Parquet
        df.to_parquet(parquet_path, index=False)
        print(f"\nSaved {updates} updated records to Parquet")
    else:
        print("\nNo updates needed")
    
    # Verify
    df_new = pd.read_parquet(parquet_path)
    error_df = df_new[df_new['total_errors'] > 0]
    print(f"\nRecords with errors after sync: {len(error_df)}")
    for idx, row in error_df.iterrows():
        if row.get('tool_selection_errors', 0) > 0 or row.get('parameter_config_errors', 0) > 0 or row.get('sequence_order_errors', 0) > 0:
            print(f"  {row['model']}/{row['task_type']}: errors properly classified")

if __name__ == '__main__':
    sync_error_classifications()
