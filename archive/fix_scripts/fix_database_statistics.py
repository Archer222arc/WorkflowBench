#!/usr/bin/env python3
"""修复数据库中的统计问题"""

import json
from pathlib import Path
from enhanced_cumulative_manager import EnhancedCumulativeManager

def fix_error_rates():
    """修复错误率计算问题"""
    # Load database
    db_path = Path('pilot_bench_cumulative_results/master_database.json')
    
    # Create backup
    backup_path = f"{db_path.parent}/master_database_backup_{db_path.stat().st_mtime:.0f}.json"
    if db_path.exists():
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f'数据库已备份到: {backup_path}')
    
    with open(db_path, 'r') as f:
        db = json.load(f)

    print('=== 修复数据库统计问题 ===')
    print()
    
    fixes_applied = 0

    for model_name, model_data in db.get('models', {}).items():
        print(f'处理模型: {model_name}')
        
        # Fix 1: Recalculate overall_stats
        total_tests = 0
        total_success = 0
        total_full_success = 0
        total_partial_success = 0
        total_errors = 0
        total_execution_time = 0
        total_turns = 0
        total_tool_calls = 0
        total_tool_coverage = 0
        test_count_for_averages = 0
        
        # Collect all error types
        all_error_counts = {
            'tool_selection_errors': 0,
            'parameter_config_errors': 0,
            'sequence_order_errors': 0,
            'dependency_errors': 0,
            'timeout_errors': 0,
            'tool_call_format_errors': 0,
            'max_turns_errors': 0,
            'other_errors': 0
        }
        
        for prompt_type, prompt_data in model_data.get('by_prompt_type', {}).items():
            for tool_rate, rate_data in prompt_data.get('by_tool_success_rate', {}).items():
                for diff, diff_data in rate_data.get('by_difficulty', {}).items():
                    for task, task_data in diff_data.get('by_task_type', {}).items():
                        
                        # Fix 2: Recalculate error rates for this task
                        task_total_errors = task_data.get('total_errors', 0)
                        
                        if task_total_errors > 0:
                            # Recalculate error rates
                            task_data["tool_selection_error_rate"] = task_data.get("tool_selection_errors", 0) / task_total_errors
                            task_data["parameter_error_rate"] = task_data.get("parameter_config_errors", 0) / task_total_errors
                            task_data["sequence_error_rate"] = task_data.get("sequence_order_errors", 0) / task_total_errors
                            task_data["dependency_error_rate"] = task_data.get("dependency_errors", 0) / task_total_errors
                            task_data["timeout_error_rate"] = task_data.get("timeout_errors", 0) / task_total_errors
                            task_data["format_error_rate"] = task_data.get("tool_call_format_errors", 0) / task_total_errors
                            task_data["max_turns_error_rate"] = task_data.get("max_turns_errors", 0) / task_total_errors
                            task_data["other_error_rate"] = task_data.get("other_errors", 0) / task_total_errors
                            
                            # Verify rates sum to 1
                            rate_sum = (task_data["tool_selection_error_rate"] + 
                                      task_data["parameter_error_rate"] + 
                                      task_data["sequence_error_rate"] + 
                                      task_data["dependency_error_rate"] + 
                                      task_data["timeout_error_rate"] + 
                                      task_data["format_error_rate"] + 
                                      task_data["max_turns_error_rate"] + 
                                      task_data["other_error_rate"])
                            
                            if abs(rate_sum - 1.0) > 0.001:
                                print(f'  ❌ {tool_rate}->{diff}->{task}: 错误率总和 {rate_sum:.3f} != 1.0')
                            else:
                                print(f'  ✅ {tool_rate}->{diff}->{task}: 错误率已修复')
                                fixes_applied += 1
                        else:
                            # No errors - all rates should be 0
                            task_data["tool_selection_error_rate"] = 0.0
                            task_data["parameter_error_rate"] = 0.0
                            task_data["sequence_error_rate"] = 0.0
                            task_data["dependency_error_rate"] = 0.0
                            task_data["timeout_error_rate"] = 0.0
                            task_data["format_error_rate"] = 0.0
                            task_data["max_turns_error_rate"] = 0.0
                            task_data["other_error_rate"] = 0.0
                        
                        # Aggregate for overall stats
                        total_tests += task_data.get('total', 0)
                        total_success += task_data.get('success', 0)
                        # Assume full_success = success - partial_success for now
                        # This may need adjustment based on actual data structure
                        task_success = task_data.get('success', 0)
                        task_partial = task_data.get('partial_success', 0)
                        task_full = task_success - task_partial
                        total_full_success += task_full
                        total_partial_success += task_partial
                        total_errors += task_data.get('total_errors', 0)
                        
                        # Aggregate error types
                        for error_type in all_error_counts:
                            all_error_counts[error_type] += task_data.get(error_type, 0)
                        
                        # Aggregate execution metrics
                        task_total = task_data.get('total', 0)
                        if task_total > 0:
                            total_execution_time += task_data.get('avg_execution_time', 0) * task_total
                            total_turns += task_data.get('avg_turns', 0) * task_total
                            total_tool_calls += task_data.get('avg_tool_calls', 0) * task_total
                            total_tool_coverage += task_data.get('tool_coverage_rate', 0) * task_total
                            test_count_for_averages += task_total
        
        # Fix 3: Update overall_stats
        if total_tests > 0:
            model_data["overall_stats"] = {
                "total": total_tests,
                "success": total_success,
                "full_success": total_full_success,
                "partial_success": total_partial_success,
                "total_errors": total_errors,
                "success_rate": total_success / total_tests,
                "full_success_rate": total_full_success / total_tests,
                "partial_success_rate": total_partial_success / total_tests,
                "failure_rate": (total_tests - total_success) / total_tests,
                "weighted_success_score": (total_full_success * 1.0 + total_partial_success * 0.5) / total_tests,
                "avg_execution_time": total_execution_time / test_count_for_averages if test_count_for_averages > 0 else 0.0,
                "avg_turns": total_turns / test_count_for_averages if test_count_for_averages > 0 else 0.0,
                "avg_tool_calls": total_tool_calls / test_count_for_averages if test_count_for_averages > 0 else 0.0,
                "tool_coverage_rate": total_tool_coverage / test_count_for_averages if test_count_for_averages > 0 else 0.0,
                **all_error_counts,  # Add error counts
                **{f"{error_type.replace('_errors', '_error_rate')}": count / total_errors if total_errors > 0 else 0.0 
                   for error_type, count in all_error_counts.items()},  # Add error rates
            }
            print(f'  ✅ overall_stats 已修复: total={total_tests}, success={total_success}, errors={total_errors}')
            fixes_applied += 1
        else:
            print(f'  ⚠️  {model_name}: 没有测试数据')
        
        print()
    
    # Save fixed database
    with open(db_path, 'w') as f:
        json.dump(db, f, indent=2)
    
    print(f'=== 修复完成 ===')
    print(f'应用了 {fixes_applied} 个修复')
    print(f'数据库已保存')
    return fixes_applied

if __name__ == "__main__":
    fix_error_rates()