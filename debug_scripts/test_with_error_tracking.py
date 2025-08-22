#!/usr/bin/env python3
"""Run batch tests with enhanced error tracking"""

import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict

# 在导入batch_test_runner之前设置环境
import os
os.environ['PYTHONPATH'] = '/Users/ruichengao/WorkflowBench/scale_up/scale_up:' + os.environ.get('PYTHONPATH', '')

@dataclass
class ErrorTracker:
    """Track errors locally during test execution"""
    total_tests: int = 0
    total_failures: int = 0
    
    # Error categorization
    error_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    error_messages: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # By prompt type tracking
    by_prompt_type: Dict[str, Dict] = field(default_factory=lambda: defaultdict(lambda: {
        'total': 0, 'failures': 0, 'errors': defaultdict(int), 'messages': []
    }))
    
    def categorize_error(self, error_msg: str) -> str:
        """Categorize error message"""
        if not error_msg:
            return 'unknown'
            
        error_lower = error_msg.lower()
        
        # Format errors
        if any(x in error_lower for x in ['format errors detected', 'format recognition issue', 
                                          'tool call format', 'understand tool call format']):
            return 'format'
        
        # Max turns without tool calls (also format)
        if ('no tool calls' in error_lower and 'turns' in error_lower) or \
           ('max turns reached' in error_lower and 'no tool calls' in error_lower):
            return 'format'
        
        # Pure max turns
        if 'max turns reached' in error_lower:
            return 'max_turns'
        
        # Timeout
        if 'timeout' in error_lower:
            return 'timeout'
        
        # Tool selection
        if ('tool' in error_lower and ('select' in error_lower or 'choice' in error_lower)) or \
           'tool calls failed' in error_lower:
            return 'tool_selection'
        
        # Parameter errors
        if any(x in error_lower for x in ['parameter', 'argument', 'invalid_input', 
                                          'permission_denied', 'validation failed']):
            return 'parameter'
        
        # Sequence errors
        if any(x in error_lower for x in ['sequence', 'order', 'required tools not completed']):
            return 'sequence'
        
        # Dependency errors
        if 'dependency' in error_lower or 'prerequisite' in error_lower:
            return 'dependency'
        
        return 'other'
    
    def add_result(self, task, result):
        """Add a test result"""
        self.total_tests += 1
        
        # Determine effective prompt type
        if task.is_flawed and task.flaw_type:
            prompt_type = f"flawed_{task.flaw_type}"
        else:
            prompt_type = task.prompt_type
        
        self.by_prompt_type[prompt_type]['total'] += 1
        
        # Check for failure
        if not result.get('success', False):
            self.total_failures += 1
            self.by_prompt_type[prompt_type]['failures'] += 1
            
            # Get error message
            error_msg = result.get('error')
            if not error_msg:
                if result.get('turns', 0) >= 10:
                    error_msg = f"Max turns reached ({result.get('turns', 0)})"
                else:
                    error_msg = 'Unknown error'
            
            # Store and categorize
            self.error_messages[error_msg] += 1
            self.by_prompt_type[prompt_type]['messages'].append(error_msg)
            
            error_type = self.categorize_error(error_msg)
            self.error_counts[error_type] += 1
            self.by_prompt_type[prompt_type]['errors'][error_type] += 1
    
    def print_summary(self):
        """Print detailed summary"""
        print("\n" + "="*80)
        print("ERROR TRACKING SUMMARY")
        print("="*80)
        
        print(f"\nOverall:")
        print(f"  Total Tests: {self.total_tests}")
        print(f"  Total Failures: {self.total_failures}")
        print(f"  Success Rate: {(self.total_tests - self.total_failures) / self.total_tests * 100:.1f}%" if self.total_tests > 0 else "N/A")
        
        print(f"\nError Categories:")
        total_categorized = sum(self.error_counts.values())
        for error_type in sorted(self.error_counts.keys()):
            count = self.error_counts[error_type]
            pct = count / self.total_failures * 100 if self.total_failures > 0 else 0
            print(f"  {error_type:15s}: {count:3d} ({pct:5.1f}%)")
        
        unclassified = self.total_failures - total_categorized
        if unclassified > 0:
            print(f"  {'UNCLASSIFIED':15s}: {unclassified:3d}")
        
        print(f"\nBy Prompt Type:")
        for prompt_type in sorted(self.by_prompt_type.keys()):
            stats = self.by_prompt_type[prompt_type]
            if stats['total'] > 0:
                failure_rate = stats['failures'] / stats['total'] * 100
                print(f"\n  {prompt_type}:")
                print(f"    Tests: {stats['total']}, Failures: {stats['failures']} ({failure_rate:.1f}%)")
                
                if stats['errors']:
                    print(f"    Error Breakdown:")
                    for error_type in sorted(stats['errors'].keys()):
                        count = stats['errors'][error_type]
                        print(f"      {error_type}: {count}")
        
        print(f"\nTop Error Messages:")
        for i, (msg, count) in enumerate(sorted(self.error_messages.items(), 
                                               key=lambda x: x[1], reverse=True)[:10], 1):
            print(f"  {i}. ({count}x) {msg[:100]}")
        
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = Path(f"error_analysis_{timestamp}.json")
        
        output_data = {
            'timestamp': timestamp,
            'summary': {
                'total_tests': self.total_tests,
                'total_failures': self.total_failures,
                'success_rate': (self.total_tests - self.total_failures) / self.total_tests if self.total_tests > 0 else 0
            },
            'error_categories': dict(self.error_counts),
            'by_prompt_type': {
                k: {
                    'total': v['total'],
                    'failures': v['failures'],
                    'error_breakdown': dict(v['errors']),
                    'sample_messages': v['messages'][:5]  # Save first 5 messages as sample
                }
                for k, v in self.by_prompt_type.items()
            },
            'all_error_messages': dict(self.error_messages)
        }
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\nDetailed analysis saved to: {output_file}")


def main():
    """Main entry point"""
    # Import batch_test_runner
    from batch_test_runner import BatchTestRunner, TestTask
    
    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser(description='Run batch tests with error tracking')
    parser.add_argument('--model', type=str, default='qwen2.5-3b-instruct', help='Model to test')
    parser.add_argument('--count', type=int, default=1, help='Tests per combination')
    parser.add_argument('--difficulty', type=str, default='very_easy', help='Difficulty')
    parser.add_argument('--concurrent', action='store_true', help='Run concurrently')
    parser.add_argument('--workers', type=int, default=3, help='Worker count')
    parser.add_argument('--qps', type=float, default=5.0, help='QPS limit')
    parser.add_argument('--smart', action='store_true', help='Smart selection')
    parser.add_argument('--silent', action='store_true', help='Silent mode')
    parser.add_argument('--debug', action='store_true', help='Debug mode')
    
    args = parser.parse_args()
    
    # Create runner
    runner = BatchTestRunner(debug=args.debug, silent=args.silent)
    runner._lazy_init()
    
    # Create error tracker
    tracker = ErrorTracker()
    
    # Hook into runner to track errors
    original_run_single = runner.run_single_test
    
    def tracked_run_single(task):
        result = original_run_single(task)
        tracker.add_result(task, result)
        return result
    
    runner.run_single_test = tracked_run_single
    
    # Create test tasks
    print(f"Creating test tasks for model: {args.model}")
    
    # Get test combinations
    task_types = ['basic_task', 'simple_task', 'api_integration', 'data_pipeline', 'multi_stage_pipeline']
    prompt_types = ['baseline', 'cot', 'optimal']
    flaw_types = ['sequence_disorder', 'tool_misuse', 'parameter_error', 'missing_step',
                  'redundant_operations', 'logical_inconsistency', 'semantic_drift']
    
    test_tasks = []
    
    # Create normal tests
    for task_type in task_types:
        for prompt_type in prompt_types:
            for _ in range(args.count):
                test_tasks.append(TestTask(
                    model=args.model,
                    task_type=task_type,
                    prompt_type=prompt_type,
                    difficulty=args.difficulty,
                    is_flawed=False,
                    flaw_type=None
                ))
    
    # Create flawed tests
    for task_type in task_types:
        for flaw_type in flaw_types:
            for _ in range(args.count):
                test_tasks.append(TestTask(
                    model=args.model,
                    task_type=task_type,
                    prompt_type='flawed',
                    difficulty=args.difficulty,
                    is_flawed=True,
                    flaw_type=flaw_type
                ))
    
    print(f"Created {len(test_tasks)} test tasks")
    
    # Run tests
    if args.concurrent:
        print(f"Running tests concurrently with {args.workers} workers...")
        results = runner.run_concurrent_batch(
            test_tasks, 
            workers=args.workers,
            qps_limit=args.qps
        )
    else:
        print(f"Running tests sequentially...")
        results = []
        for task in test_tasks:
            result = runner.run_single_test(task)
            results.append(result)
    
    # Print tracking summary
    tracker.print_summary()
    
    # Print original summary
    success_count = sum(1 for r in results if r.get('success', False))
    print(f"\n{'='*60}")
    print(f"Test Complete!")
    print(f"Success: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)")
    print(f"Model: {args.model}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()