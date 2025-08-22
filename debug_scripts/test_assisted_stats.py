#!/usr/bin/env python3
"""Test script to verify assisted statistics are being recorded"""

import json
from pathlib import Path
from batch_test_runner import BatchTestRunner
from batch_test_runner import TestTask

def main():
    # Initialize runner
    runner = BatchTestRunner(debug=False, silent=True)
    
    # Create a simple test task
    task = TestTask(
        model="qwen2.5-3b-instruct",
        task_type="basic_task",
        prompt_type="baseline",
        difficulty="very_easy",
        is_flawed=False,
        flaw_type=None,
        tool_success_rate=1.0,
        required_tools=["data_processing_parser", "data_processing_validator"]
    )
    
    # Run single test
    print("Running single test...")
    result = runner.run_single_test(
        task_type="basic_task",
        prompt_type="baseline",
        is_flawed=False,
        flaw_type=None,
        model="qwen2.5-3b-instruct",
        tool_success_rate=1.0
    )
    
    # Check if format_error_count is in result
    print(f"\nTest Result:")
    print(f"  Success: {result.get('success', False)}")
    print(f"  Turns: {result.get('turns', 0)}")
    print(f"  Format Error Count: {result.get('format_error_count', 'NOT FOUND')}")
    print(f"  Format Issues: {result.get('format_issues', 'NOT FOUND')}")
    
    # Check database for assisted statistics
    db_path = Path("pilot_bench_cumulative_results/master_database.json")
    if db_path.exists():
        with open(db_path, 'r') as f:
            data = json.load(f)
        
        # Get baseline stats
        baseline_stats = data.get("by_prompt_type", {}).get("baseline", {})
        print(f"\nDatabase Statistics for 'baseline' prompt_type:")
        print(f"  Total Tests: {baseline_stats.get('total_tests', 0)}")
        print(f"  Tests with Assistance: {baseline_stats.get('tests_with_assistance', 0)}")
        print(f"  Total Assisted Turns: {baseline_stats.get('total_assisted_turns', 0)}")
        print(f"  Avg Assisted Turns: {baseline_stats.get('avg_assisted_turns', 0.0)}")
        print(f"  Assisted Success: {baseline_stats.get('assisted_success', 0)}")
        print(f"  Assisted Failure: {baseline_stats.get('assisted_failure', 0)}")
        print(f"  Assistance Rate: {baseline_stats.get('assistance_rate', 0.0)}")

if __name__ == "__main__":
    main()