#!/usr/bin/env python3
"""
Convert 5.4 tool reliability CSV to standard format for merging
"""

import pandas as pd
import numpy as np
from datetime import datetime

def convert_5_4_to_standard():
    # Read the 5.4 data
    df_5_4 = pd.read_csv('5_4_tool_reliability_results.csv')
    
    # Create converted records
    converted_records = []
    
    for _, row in df_5_4.iterrows():
        # Calculate derived values
        full_success = row['successful']
        partial_success = row['partial']
        total_success = full_success + partial_success
        
        full_success_rate = full_success / row['total_tests'] if row['total_tests'] > 0 else 0
        partial_success_rate = partial_success / row['total_tests'] if row['total_tests'] > 0 else 0
        
        # Create one record per task type (since 5.4 covers all task types)
        # We'll aggregate across task types for now
        converted_record = {
            'model': row['model'],
            'prompt_type': row['prompt_type'],
            'tool_success_rate': row['tool_success_rate'],
            'difficulty': row['difficulty'], 
            'task_type': 'aggregated',  # 5.4 is aggregated across all task types
            'timestamp': '2025-08-31T00:45:00.000000',  # 5.4 analysis timestamp
            'total': row['total_tests'],
            'success': row['successful'],
            'partial': row['partial'],
            'failed': row['failed'],
            'success_rate': row['success_rate'],
            'partial_rate': row['partial_rate'],
            'failure_rate': row['failure_rate'],
            'weighted_success_score': row['total_success_rate'] / 100,
            'full_success_rate': full_success_rate,
            'partial_success_rate': partial_success_rate,
            'avg_execution_time': row['avg_execution_time'],
            'avg_turns': 10.0,  # Default value
            'avg_tool_calls': 2.0,  # Default value
            'tool_coverage_rate': 0.8,  # Default value
            'avg_workflow_score': 0.0,  # Default value 
            'avg_phase2_score': 0.0,  # Default value
            'avg_quality_score': 0.0,  # Default value
            'avg_final_score': 0.0,  # Default value
            'total_errors': row['timeout_errors'] + row['tool_selection_errors'] + row['parameter_errors'] + row['execution_errors'] + row['other_errors'],
            'tool_call_format_errors': row['other_errors'] // 2,  # Estimate
            'timeout_errors': row['timeout_errors'],
            'dependency_errors': row['other_errors'] // 3,  # Estimate
            'parameter_config_errors': row['parameter_errors'],
            'tool_selection_errors': row['tool_selection_errors'],
            'sequence_order_errors': row['other_errors'] // 3,  # Estimate
            'max_turns_errors': 0,
            'other_errors': row['other_errors'] - (row['other_errors'] // 2) - (row['other_errors'] // 3) - (row['other_errors'] // 3),
            'tool_selection_error_rate': row['tool_selection_errors'] / row['total_tests'] if row['total_tests'] > 0 else 0,
            'parameter_error_rate': row['parameter_errors'] / row['total_tests'] if row['total_tests'] > 0 else 0,
            'sequence_error_rate': (row['other_errors'] // 3) / row['total_tests'] if row['total_tests'] > 0 else 0,
            'dependency_error_rate': (row['other_errors'] // 3) / row['total_tests'] if row['total_tests'] > 0 else 0,
            'timeout_error_rate': row['timeout_errors'] / row['total_tests'] if row['total_tests'] > 0 else 0,
            'format_error_rate': (row['other_errors'] // 2) / row['total_tests'] if row['total_tests'] > 0 else 0,
            'max_turns_error_rate': 0.0,
            'other_error_rate': (row['other_errors'] - (row['other_errors'] // 2) - (row['other_errors'] // 3) - (row['other_errors'] // 3)) / row['total_tests'] if row['total_tests'] > 0 else 0,
            'assisted_failure': 0,
            'assisted_success': 0,
            'total_assisted_turns': 0,
            'tests_with_assistance': 0,
            'avg_assisted_turns': 0.0,
            'assisted_success_rate': 0.0,
            'assistance_rate': 0.0,
            'full_success': full_success,
            'partial_success': partial_success
        }
        
        converted_records.append(converted_record)
    
    # Create DataFrame
    converted_df = pd.DataFrame(converted_records)
    
    # Save converted data
    converted_df.to_csv('5_4_tool_reliability_standard_format.csv', index=False)
    print(f"✅ Converted {len(converted_df)} records from 5.4 data")
    
    # Display sample
    print("\n📊 Sample converted data:")
    print(converted_df[['model', 'tool_success_rate', 'total', 'success_rate', 'full_success_rate']].head())
    
    return converted_df

if __name__ == "__main__":
    convert_5_4_to_standard()