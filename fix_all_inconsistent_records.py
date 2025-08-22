#!/usr/bin/env python3
"""
Fix all inconsistent records in the database by properly calculating failed counts
"""

import json
from pathlib import Path
from datetime import datetime

def fix_all_inconsistent_records():
    """Fix all records where total != success + partial + failed"""
    
    print("=" * 60)
    print("Fixing All Inconsistent Records in Database")
    print("=" * 60)
    
    # 1. Load database
    json_path = Path('pilot_bench_cumulative_results/master_database.json')
    
    # Backup first
    backup_path = json_path.parent / f"master_database.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_path, 'r') as f:
        db = json.load(f)
    
    with open(backup_path, 'w') as f:
        json.dump(db, f, indent=2)
    print(f"✅ Backed up to {backup_path.name}")
    
    # 2. Fix all inconsistent records
    fixed_count = 0
    total_records = 0
    
    for model_name, model_data in db.get('models', {}).items():
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
                        total_records += 1
                        
                        # Get current values
                        total = task_data.get('total', 0)
                        success = task_data.get('success', 0)
                        partial = task_data.get('partial', 0)
                        failed = task_data.get('failed', 0)
                        
                        # Check if inconsistent
                        if total != success + partial + failed:
                            # Calculate correct failed count
                            correct_failed = total - success - partial
                            
                            # Ensure non-negative
                            if correct_failed < 0:
                                print(f"⚠️ Negative failed count for {model_name}/{prompt_type}/{rate}/{diff}/{task}")
                                print(f"   total={total}, success={success}, partial={partial}")
                                # Adjust total if needed
                                task_data['total'] = success + partial
                                correct_failed = 0
                            
                            # Update failed count
                            task_data['failed'] = correct_failed
                            
                            # Recalculate rates
                            if total > 0:
                                task_data['success_rate'] = success / total
                                task_data['partial_rate'] = partial / total
                                task_data['failure_rate'] = correct_failed / total
                            else:
                                task_data['success_rate'] = 0.0
                                task_data['partial_rate'] = 0.0
                                task_data['failure_rate'] = 0.0
                            
                            fixed_count += 1
                            
                            if fixed_count <= 5:  # Show first 5 fixes as examples
                                print(f"Fixed: {model_name}/{prompt_type}/{rate}/{diff}/{task}")
                                print(f"  Before: total={total}, success={success}, partial={partial}, failed={failed}")
                                print(f"  After:  total={total}, success={success}, partial={partial}, failed={correct_failed}")
    
    # 3. Update last_updated timestamp
    db['last_updated'] = datetime.now().isoformat()
    
    # 4. Save fixed database
    with open(json_path, 'w') as f:
        json.dump(db, f, indent=2)
    
    print(f"\n✅ Fixed {fixed_count} out of {total_records} records")
    
    # 5. Verify fix
    print("\n" + "=" * 60)
    print("Verifying Fix")
    print("=" * 60)
    
    # Re-check consistency
    inconsistent = 0
    for model_name, model_data in db.get('models', {}).items():
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
                        total = task_data.get('total', 0)
                        success = task_data.get('success', 0)
                        partial = task_data.get('partial', 0)
                        failed = task_data.get('failed', 0)
                        
                        if total != success + partial + failed:
                            inconsistent += 1
    
    if inconsistent == 0:
        print("✅ All records are now consistent!")
        print(f"   Total records: {total_records}")
        print(f"   All have: total = success + partial + failed")
    else:
        print(f"⚠️ Still {inconsistent} inconsistent records remaining")
    
    # 6. Show summary statistics
    print("\n" + "=" * 60)
    print("Summary Statistics")
    print("=" * 60)
    
    total_tests = 0
    total_success = 0
    total_partial = 0
    total_failed = 0
    
    for model_name, model_data in db.get('models', {}).items():
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
                        total_tests += task_data.get('total', 0)
                        total_success += task_data.get('success', 0)
                        total_partial += task_data.get('partial', 0)
                        total_failed += task_data.get('failed', 0)
    
    print(f"Total tests: {total_tests}")
    print(f"Total success: {total_success}")
    print(f"Total partial: {total_partial}")
    print(f"Total failed: {total_failed}")
    print(f"Overall success rate: {total_success/total_tests*100:.1f}%" if total_tests > 0 else "N/A")
    print(f"Overall failure rate: {total_failed/total_tests*100:.1f}%" if total_tests > 0 else "N/A")
    
    return fixed_count, total_records

if __name__ == "__main__":
    fixed, total = fix_all_inconsistent_records()
    print(f"\n✅ Complete! Fixed {fixed}/{total} records.")