#!/usr/bin/env python3
"""
Comprehensive verification of all data integrity fixes
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime

def verify_all_fixes():
    """Verify all data integrity fixes are working"""
    
    print("=" * 60)
    print("Comprehensive Data Integrity Verification")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    all_checks_passed = True
    
    # 1. Check JSON database consistency
    print("\n1. Checking JSON Database...")
    json_path = Path('pilot_bench_cumulative_results/master_database.json')
    with open(json_path, 'r') as f:
        json_db = json.load(f)
    
    json_inconsistent = 0
    json_total = 0
    
    for model_name, model_data in json_db.get('models', {}).items():
        if 'by_prompt_type' not in model_data:
            continue
        for prompt_type, prompt_data in model_data['by_prompt_type'].items():
            if 'by_tool_success_rate' not in prompt_data:
                continue
            for rate, rate_data in prompt_data['by_tool_success_rate'].items():
                if 'by_difficulty' not in rate_data:
                    continue
                for diff, diff_data in rate_data['by_difficulty'].items():
                    if 'by_task_type' not in diff_data:
                        continue
                    for task, task_data in diff_data['by_task_type'].items():
                        json_total += 1
                        total = task_data.get('total', 0)
                        success = task_data.get('success', 0)
                        partial = task_data.get('partial', 0)
                        failed = task_data.get('failed', 0)
                        
                        if total != success + partial + failed:
                            json_inconsistent += 1
    
    if json_inconsistent == 0:
        print(f"   ✅ JSON: All {json_total} records are consistent")
    else:
        print(f"   ❌ JSON: {json_inconsistent}/{json_total} records are inconsistent")
        all_checks_passed = False
    
    # 2. Check Parquet database consistency
    print("\n2. Checking Parquet Database...")
    parquet_file = Path('pilot_bench_parquet_data/test_results.parquet')
    
    if parquet_file.exists():
        df = pd.read_parquet(parquet_file)
        
        # Check for nulls in critical fields
        null_checks = {
            'failed': df['failed'].isnull().sum(),
            'partial': df['partial'].isnull().sum(),
            'success_rate': df['success_rate'].isnull().sum(),
            'failure_rate': df['failure_rate'].isnull().sum()
        }
        
        for field, null_count in null_checks.items():
            if null_count == 0:
                print(f"   ✅ Parquet: No null values in '{field}' field")
            else:
                print(f"   ❌ Parquet: {null_count} null values in '{field}' field")
                all_checks_passed = False
        
        # Check consistency
        parquet_inconsistent = 0
        for idx in range(len(df)):
            row = df.iloc[idx]
            total = row.get('total', 0)
            success = row.get('success', 0) if pd.notna(row.get('success')) else 0
            partial = row.get('partial', 0) if pd.notna(row.get('partial')) else 0
            failed = row.get('failed', 0) if pd.notna(row.get('failed')) else 0
            
            if abs(total - (success + partial + failed)) > 0.01:
                parquet_inconsistent += 1
        
        if parquet_inconsistent == 0:
            print(f"   ✅ Parquet: All {len(df)} records are consistent")
        else:
            print(f"   ❌ Parquet: {parquet_inconsistent}/{len(df)} records are inconsistent")
            all_checks_passed = False
    else:
        print("   ⚠️ Parquet file does not exist")
    
    # 3. Check JSON-Parquet synchronization
    print("\n3. Checking JSON-Parquet Synchronization...")
    
    if parquet_file.exists():
        # Count total tests in both formats
        json_total_tests = 0
        json_total_success = 0
        json_total_failed = 0
        
        for model_name, model_data in json_db.get('models', {}).items():
            if 'by_prompt_type' not in model_data:
                continue
            for prompt_type, prompt_data in model_data['by_prompt_type'].items():
                if 'by_tool_success_rate' not in prompt_data:
                    continue
                for rate, rate_data in prompt_data['by_tool_success_rate'].items():
                    if 'by_difficulty' not in rate_data:
                        continue
                    for diff, diff_data in rate_data['by_difficulty'].items():
                        if 'by_task_type' not in diff_data:
                            continue
                        for task, task_data in diff_data['by_task_type'].items():
                            json_total_tests += task_data.get('total', 0)
                            json_total_success += task_data.get('success', 0)
                            json_total_failed += task_data.get('failed', 0)
        
        parquet_total_tests = df['total'].sum()
        parquet_total_success = df['success'].sum() if 'success' in df.columns else df['successful'].sum()
        parquet_total_failed = df['failed'].sum()
        
        sync_checks = [
            ('Total tests', json_total_tests, parquet_total_tests),
            ('Total success', json_total_success, parquet_total_success),
            ('Total failed', json_total_failed, parquet_total_failed)
        ]
        
        for name, json_val, parquet_val in sync_checks:
            if abs(json_val - parquet_val) < 10:  # Allow small differences due to rounding
                print(f"   ✅ {name}: JSON={json_val:.0f}, Parquet={parquet_val:.0f} (synchronized)")
            else:
                print(f"   ❌ {name}: JSON={json_val:.0f}, Parquet={parquet_val:.0f} (mismatch)")
                all_checks_passed = False
    
    # 4. Check file integrity
    print("\n4. Checking File Integrity...")
    
    # Check for file locks
    lock_file = Path('pilot_bench_parquet_data/test_results.parquet.lock')
    if lock_file.exists():
        print(f"   ⚠️ Lock file exists: {lock_file}")
        all_checks_passed = False
    else:
        print("   ✅ No lock files present")
    
    # Check Parquet file size
    if parquet_file.exists():
        file_size = parquet_file.stat().st_size
        if file_size > 1000:  # Should be at least 1KB
            print(f"   ✅ Parquet file size: {file_size/1024:.1f} KB")
        else:
            print(f"   ❌ Parquet file too small: {file_size} bytes")
            all_checks_passed = False
    
    # 5. Summary statistics
    print("\n5. Summary Statistics:")
    print("   " + "-" * 40)
    
    if json_total_tests > 0:
        success_rate = json_total_success / json_total_tests * 100
        failure_rate = json_total_failed / json_total_tests * 100
        
        print(f"   Total tests:    {json_total_tests}")
        print(f"   Successful:     {json_total_success} ({success_rate:.1f}%)")
        print(f"   Failed:         {json_total_failed} ({failure_rate:.1f}%)")
        print(f"   Partial:        {json_total_tests - json_total_success - json_total_failed}")
        
        if failure_rate > 70:
            print(f"   ⚠️ High failure rate detected: {failure_rate:.1f}%")
    
    # Final verdict
    print("\n" + "=" * 60)
    if all_checks_passed:
        print("✅ ALL INTEGRITY CHECKS PASSED!")
        print("The data consistency issues have been successfully resolved.")
    else:
        print("❌ SOME CHECKS FAILED")
        print("Please review the issues above and run additional fixes if needed.")
    print("=" * 60)
    
    return all_checks_passed

if __name__ == "__main__":
    success = verify_all_fixes()
    exit(0 if success else 1)