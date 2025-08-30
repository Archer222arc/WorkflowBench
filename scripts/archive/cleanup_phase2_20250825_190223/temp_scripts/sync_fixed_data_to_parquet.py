#!/usr/bin/env python3
"""
Sync the fixed JSON data to Parquet to ensure consistency
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime

def sync_to_parquet():
    """Sync fixed JSON data to Parquet"""
    
    print("=" * 60)
    print("Syncing Fixed Data to Parquet")
    print("=" * 60)
    
    # 1. Load JSON database
    json_path = Path('pilot_bench_cumulative_results/master_database.json')
    with open(json_path, 'r') as f:
        json_db = json.load(f)
    
    # 2. Load existing Parquet
    parquet_file = Path('pilot_bench_parquet_data/test_results.parquet')
    if parquet_file.exists():
        df = pd.read_parquet(parquet_file)
        # Backup
        backup_path = parquet_file.parent / f"test_results_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
        df.to_parquet(backup_path, index=False)
        print(f"✅ Backed up Parquet to {backup_path.name}")
    else:
        # Create new DataFrame with all columns
        df = pd.DataFrame()
    
    # 3. Update Parquet with fixed data
    updated_count = 0
    
    for idx in range(len(df)):
        row = df.iloc[idx]
        model = row['model']
        prompt_type = row['prompt_type']
        tool_success_rate = str(row['tool_success_rate'])
        difficulty = row['difficulty']
        task_type = row['task_type']
        
        # Find corresponding JSON data
        try:
            if model in json_db.get('models', {}):
                model_data = json_db['models'][model]
                
                if 'by_prompt_type' in model_data and prompt_type in model_data['by_prompt_type']:
                    prompt_data = model_data['by_prompt_type'][prompt_type]
                    
                    if 'by_tool_success_rate' in prompt_data and tool_success_rate in prompt_data['by_tool_success_rate']:
                        rate_data = prompt_data['by_tool_success_rate'][tool_success_rate]
                        
                        if 'by_difficulty' in rate_data and difficulty in rate_data['by_difficulty']:
                            diff_data = rate_data['by_difficulty'][difficulty]
                            
                            if 'by_task_type' in diff_data and task_type in diff_data['by_task_type']:
                                task_data = diff_data['by_task_type'][task_type]
                                
                                # Update critical fields
                                df.at[idx, 'failed'] = task_data.get('failed', 0)
                                df.at[idx, 'partial'] = task_data.get('partial', 0)
                                df.at[idx, 'success'] = task_data.get('success', 0)
                                df.at[idx, 'successful'] = task_data.get('success', 0)  # Duplicate field
                                df.at[idx, 'total'] = task_data.get('total', 0)
                                df.at[idx, 'success_rate'] = task_data.get('success_rate', 0.0)
                                df.at[idx, 'partial_rate'] = task_data.get('partial_rate', 0.0)
                                df.at[idx, 'failure_rate'] = task_data.get('failure_rate', 0.0)
                                
                                updated_count += 1
                                
        except Exception as e:
            print(f"⚠️ Error updating row {idx}: {e}")
    
    # 4. Save updated Parquet
    df.to_parquet(parquet_file, index=False)
    print(f"\n✅ Updated {updated_count} records in Parquet")
    
    # 5. Verify consistency
    print("\n" + "=" * 60)
    print("Verifying Parquet Consistency")
    print("=" * 60)
    
    df_verify = pd.read_parquet(parquet_file)
    
    # Check consistency
    inconsistent = 0
    for idx in range(len(df_verify)):
        row = df_verify.iloc[idx]
        total = row.get('total', 0)
        success = row.get('success', 0) if pd.notna(row.get('success')) else 0
        partial = row.get('partial', 0) if pd.notna(row.get('partial')) else 0
        failed = row.get('failed', 0) if pd.notna(row.get('failed')) else 0
        
        if abs(total - (success + partial + failed)) > 0.01:  # Allow small floating point errors
            inconsistent += 1
            if inconsistent <= 5:
                print(f"Inconsistent: {row['model']}/{row['prompt_type']}")
                print(f"  total={total}, success={success}, partial={partial}, failed={failed}")
    
    if inconsistent == 0:
        print("✅ All Parquet records are consistent!")
    else:
        print(f"⚠️ {inconsistent} records still inconsistent in Parquet")
    
    # 6. Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Parquet records: {len(df_verify)}")
    print(f"Updated records: {updated_count}")
    print(f"Null 'failed' fields: {df_verify['failed'].isnull().sum()}")
    print(f"Null 'partial' fields: {df_verify['partial'].isnull().sum()}")
    
    # Calculate totals
    total_tests = df_verify['total'].sum()
    total_success = df_verify['success'].sum() if 'success' in df_verify.columns else df_verify['successful'].sum()
    total_partial = df_verify['partial'].sum() if 'partial' in df_verify.columns else 0
    total_failed = df_verify['failed'].sum() if 'failed' in df_verify.columns else 0
    
    print(f"\nAggregate Statistics:")
    print(f"Total tests: {total_tests:.0f}")
    print(f"Total success: {total_success:.0f}")
    print(f"Total partial: {total_partial:.0f}")
    print(f"Total failed: {total_failed:.0f}")
    
    return updated_count

if __name__ == "__main__":
    count = sync_to_parquet()
    print(f"\n✅ Sync complete! Updated {count} records.")