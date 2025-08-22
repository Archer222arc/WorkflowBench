#!/usr/bin/env python3
"""Debug script to trace error classification issues"""

import json
from pathlib import Path
from cumulative_data_structure import ErrorMetrics

def test_error_classification():
    """Test error classification logic"""
    
    # Test various error messages
    test_cases = [
        ("Max turns reached (10)", "max_turns"),
        ("Tool call format errors detected", "format"),
        ("Model doesn't understand tool call format", "format"),
        ("No tool calls in 10 turns", "format"),
        ("Tool selection failed", "tool_selection"),
        ("Invalid parameter configuration", "parameter"),
        ("Sequence order violation", "sequence"),
        ("Dependency not met", "dependency"),
        ("Connection timeout", "timeout"),
        ("Unknown error", "other")
    ]
    
    errors = ErrorMetrics()
    
    print("Testing error classification:")
    print("-" * 60)
    
    for error_msg, expected_type in test_cases:
        # Reset counters
        errors = ErrorMetrics()
        
        # Classify error
        errors.categorize_error(error_msg)
        
        # Check classification
        result_type = None
        if errors.tool_call_format_errors > 0:
            result_type = "format"
        elif errors.max_turns_errors > 0:
            result_type = "max_turns"
        elif errors.timeout_errors > 0:
            result_type = "timeout"
        elif errors.tool_selection_errors > 0:
            result_type = "tool_selection"
        elif errors.parameter_config_errors > 0:
            result_type = "parameter"
        elif errors.sequence_order_errors > 0:
            result_type = "sequence"
        elif errors.dependency_errors > 0:
            result_type = "dependency"
        elif errors.other_errors > 0:
            result_type = "other"
        
        status = "✓" if result_type == expected_type else "✗"
        print(f"{status} '{error_msg}' -> {result_type} (expected: {expected_type})")
        
        if result_type != expected_type:
            print(f"  Details: total_errors={errors.total_errors}, format={errors.tool_call_format_errors}, "
                  f"max_turns={errors.max_turns_errors}, timeout={errors.timeout_errors}, "
                  f"tool_sel={errors.tool_selection_errors}, param={errors.parameter_config_errors}, "
                  f"seq={errors.sequence_order_errors}, dep={errors.dependency_errors}, other={errors.other_errors}")

def check_database_errors():
    """Check errors in the actual database"""
    
    db_path = Path("pilot_bench_cumulative_results/master_database.json")
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return
        
    with open(db_path, 'r') as f:
        data = json.load(f)
    
    print("\n\nDatabase Error Analysis:")
    print("-" * 60)
    
    # Check test groups for error messages
    test_groups = data.get('test_groups', {})
    
    # Count tests with and without errors
    tests_with_errors = 0
    tests_without_errors = 0
    error_messages = {}
    
    for group_key, group_data in test_groups.items():
        stats = group_data.get('statistics', {})
        failures = stats.get('failure', 0)
        
        if failures > 0:
            print(f"\nGroup: {group_key}")
            print(f"  Failures: {failures}")
            
            # Check if there are instances (in old format)
            instances = group_data.get('instances', [])
            if instances:
                for inst in instances[:3]:  # Check first 3 instances
                    if 'error' in inst:
                        error_msg = inst['error']
                        error_messages[error_msg] = error_messages.get(error_msg, 0) + 1
                        print(f"  Error: {error_msg}")
    
    print(f"\n\nError Message Summary:")
    for msg, count in sorted(error_messages.items(), key=lambda x: x[1], reverse=True):
        print(f"  {count}x: {msg}")
    
    # Check model-level statistics
    models = data.get('models', {})
    for model_name, model_data in models.items():
        print(f"\n\nModel: {model_name}")
        
        # Check if using new format
        if 'overall_errors' in model_data:
            overall_errors = model_data['overall_errors']
            print(f"  Overall errors (new format):")
            print(f"    total_errors: {overall_errors.get('total_errors', 0)}")
            print(f"    tool_call_format_errors: {overall_errors.get('tool_call_format_errors', 0)}")
            print(f"    max_turns_errors: {overall_errors.get('max_turns_errors', 0)}")
            print(f"    timeout_errors: {overall_errors.get('timeout_errors', 0)}")
        else:
            print(f"  Using old format - no detailed error tracking")
            
        # Check prompt-level statistics
        by_prompt = model_data.get('by_prompt_type', {})
        for prompt_type, prompt_data in by_prompt.items():
            if 'error_metrics' in prompt_data:
                error_metrics = prompt_data['error_metrics']
                total = error_metrics.get('total_errors', 0)
                if total > 0:
                    print(f"\n  {prompt_type}:")
                    print(f"    total_errors: {total}")
                    print(f"    format: {error_metrics.get('tool_call_format_errors', 0)}")
                    print(f"    max_turns: {error_metrics.get('max_turns_errors', 0)}")
                    print(f"    timeout: {error_metrics.get('timeout_errors', 0)}")

if __name__ == "__main__":
    test_error_classification()
    check_database_errors()