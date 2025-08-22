#!/usr/bin/env python3
"""Debug actual error messages in test records"""

# Let's add some debug output to see what error messages are being passed
import sys
import traceback
from enhanced_cumulative_manager import EnhancedCumulativeManager

# Monkey patch the AI classification part to see what's happening
original_add_test_result = EnhancedCumulativeManager._add_test_result

def debug_add_test_result(self, record):
    """Debug version that shows error messages"""
    print(f"DEBUG: Processing record for {record.model} {record.task_type}")
    print(f"  success: {record.success}")
    print(f"  success_level: {getattr(record, 'success_level', 'None')}")
    print(f"  error_message: '{record.error_message}'")
    print(f"  format_error_count: {getattr(record, 'format_error_count', 0)}")
    
    # Check if this has errors
    has_errors = (not record.success or 
                 hasattr(record, 'success_level') and getattr(record, 'success_level', '') == 'partial_success')
    
    if has_errors:
        # Show what error message would be constructed
        error_msg = record.error_message
        if not error_msg and getattr(record, 'success_level', '') == 'partial_success':
            format_count = getattr(record, 'format_error_count', 0)
            if format_count > 0:
                error_msg = f"Format issues detected: {format_count} format helps needed"
            else:
                error_msg = "Partial success - quality issues detected"
        
        print(f"  constructed_error_msg: '{error_msg}'")
        print(f"  would_trigger_timeout: {'timeout' in (error_msg or '').lower()}")
        print("")
    
    # Call original method
    return original_add_test_result(self, record)

EnhancedCumulativeManager._add_test_result = debug_add_test_result

print("Monkey patched EnhancedCumulativeManager for debugging")
print("Now run a test to see what error messages are being processed:")
print("python smart_batch_runner.py --model gpt-4o-mini --prompt-types baseline --difficulty easy --task-types simple_task --num-instances 1 --tool-success-rate 0.1 --max-workers 1 --ai-classification --no-save-logs")