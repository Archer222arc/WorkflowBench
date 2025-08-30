#!/usr/bin/env python3
"""Enhanced batch test runner with local error statistics tracking"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict
from dataclasses import dataclass, field, asdict

from batch_test_runner import BatchTestRunner
from cumulative_data_structure import ErrorMetrics, ModelStatistics, PromptTypeStats

@dataclass
class LocalErrorStats:
    """Local error statistics tracker"""
    total_tests: int = 0
    total_failures: int = 0
    
    # Error categorization
    format_errors: int = 0
    timeout_errors: int = 0
    max_turns_errors: int = 0
    tool_selection_errors: int = 0
    parameter_errors: int = 0
    sequence_errors: int = 0
    dependency_errors: int = 0
    other_errors: int = 0
    
    # Error messages
    error_messages: Dict[str, int] = field(default_factory=dict)
    
    # By prompt type
    by_prompt_type: Dict[str, Dict] = field(default_factory=lambda: defaultdict(lambda: {
        'total': 0, 'failures': 0, 'errors': defaultdict(int)
    }))
    
    def add_test(self, prompt_type: str, is_flawed: bool, flaw_type: str = None):
        """Add a test record"""
        self.total_tests += 1
        
        # Determine effective prompt type
        if is_flawed and flaw_type:
            effective_prompt = f"flawed_{flaw_type}"
        else:
            effective_prompt = prompt_type
            
        self.by_prompt_type[effective_prompt]['total'] += 1
    
    def add_error(self, error_msg: str, prompt_type: str, is_flawed: bool, flaw_type: str = None):
        """Add and categorize an error"""
        self.total_failures += 1
        
        # Determine effective prompt type
        if is_flawed and flaw_type:
            effective_prompt = f"flawed_{flaw_type}"
        else:
            effective_prompt = prompt_type
            
        self.by_prompt_type[effective_prompt]['failures'] += 1
        
        # Store error message
        if error_msg:
            self.error_messages[error_msg] = self.error_messages.get(error_msg, 0) + 1
            
            # Categorize error
            error_lower = error_msg.lower()
            error_type = self._categorize_error(error_lower)
            
            # Update counts
            if error_type == 'format':
                self.format_errors += 1
            elif error_type == 'timeout':
                self.timeout_errors += 1
            elif error_type == 'max_turns':
                self.max_turns_errors += 1
            elif error_type == 'tool_selection':
                self.tool_selection_errors += 1
            elif error_type == 'parameter':
                self.parameter_errors += 1
            elif error_type == 'sequence':
                self.sequence_errors += 1
            elif error_type == 'dependency':
                self.dependency_errors += 1
            else:
                self.other_errors += 1
                
            # Update prompt-level error counts
            self.by_prompt_type[effective_prompt]['errors'][error_type] += 1
    
    def _categorize_error(self, error_lower: str) -> str:
        """Categorize error message"""
        if 'format errors detected' in error_lower or 'format recognition issue' in error_lower:
            return 'format'
        elif 'tool call format' in error_lower or 'understand tool call format' in error_lower:
            return 'format'
        elif ('no tool calls' in error_lower and 'turns' in error_lower) or ('max turns reached' in error_lower and 'no tool calls' in error_lower):
            return 'format'
        elif 'max turns reached' in error_lower:
            return 'max_turns'
        elif 'timeout' in error_lower:
            return 'timeout'
        elif ('tool' in error_lower and ('select' in error_lower or 'choice' in error_lower)) or 'tool calls failed' in error_lower:
            return 'tool_selection'
        elif ('parameter' in error_lower or 'argument' in error_lower or 'invalid_input' in error_lower or 
              'permission_denied' in error_lower or 'validation failed' in error_lower):
            return 'parameter'
        elif ('sequence' in error_lower or 'order' in error_lower or 'required tools not completed' in error_lower):
            return 'sequence'
        elif 'dependency' in error_lower or 'prerequisite' in error_lower:
            return 'dependency'
        else:
            return 'other'
    
    def get_summary(self) -> Dict:
        """Get summary statistics"""
        return {
            'total_tests': self.total_tests,
            'total_failures': self.total_failures,
            'success_rate': (self.total_tests - self.total_failures) / self.total_tests if self.total_tests > 0 else 0,
            'error_breakdown': {
                'format': self.format_errors,
                'timeout': self.timeout_errors,
                'max_turns': self.max_turns_errors,
                'tool_selection': self.tool_selection_errors,
                'parameter': self.parameter_errors,
                'sequence': self.sequence_errors,
                'dependency': self.dependency_errors,
                'other': self.other_errors
            },
            'unclassified_errors': self.total_failures - sum([
                self.format_errors, self.timeout_errors, self.max_turns_errors,
                self.tool_selection_errors, self.parameter_errors,
                self.sequence_errors, self.dependency_errors, self.other_errors
            ]),
            'by_prompt_type': dict(self.by_prompt_type),
            'top_errors': sorted(self.error_messages.items(), key=lambda x: x[1], reverse=True)[:10]
        }


class EnhancedBatchTestRunner(BatchTestRunner):
    """Enhanced batch test runner with local error tracking"""
    
    def __init__(self, debug=False, silent=False, use_ai_classification=False):
        super().__init__(debug=debug, silent=silent, use_ai_classification=use_ai_classification)
        self.local_stats = LocalErrorStats()
    
    def run_single_test(self, task):
        """Override to track local statistics"""
        # Track test start
        self.local_stats.add_test(
            prompt_type=task.prompt_type,
            is_flawed=task.is_flawed,
            flaw_type=task.flaw_type
        )
        
        # Run the test
        result = super().run_single_test(task)
        
        # Track errors
        if not result.get('success', False):
            error_msg = result.get('error')
            if not error_msg:
                # Try to determine error from result
                if result.get('turns', 0) >= 10:
                    error_msg = f"Max turns reached ({result.get('turns', 0)})"
                else:
                    error_msg = 'Unknown error'
            
            self.local_stats.add_error(
                error_msg=error_msg,
                prompt_type=task.prompt_type,
                is_flawed=task.is_flawed,
                flaw_type=task.flaw_type
            )
        
        return result
    
    def print_error_statistics(self):
        """Print detailed error statistics"""
        summary = self.local_stats.get_summary()
        
        print("\n" + "="*80)
        print("ERROR STATISTICS ANALYSIS")
        print("="*80)
        
        print(f"\nOverall Statistics:")
        print(f"  Total Tests: {summary['total_tests']}")
        print(f"  Total Failures: {summary['total_failures']}")
        print(f"  Success Rate: {summary['success_rate']:.1%}")
        print(f"  Unclassified Errors: {summary['unclassified_errors']}")
        
        print(f"\nError Breakdown:")
        for error_type, count in summary['error_breakdown'].items():
            if count > 0:
                pct = count / summary['total_failures'] * 100 if summary['total_failures'] > 0 else 0
                print(f"  {error_type:15s}: {count:3d} ({pct:5.1f}%)")
        
        print(f"\nBy Prompt Type:")
        for prompt_type, stats in sorted(summary['by_prompt_type'].items()):
            if stats['total'] > 0:
                failure_rate = stats['failures'] / stats['total'] * 100
                print(f"\n  {prompt_type}:")
                print(f"    Tests: {stats['total']}, Failures: {stats['failures']} ({failure_rate:.1f}%)")
                if stats['errors']:
                    print(f"    Error Types:")
                    for error_type, count in sorted(stats['errors'].items()):
                        print(f"      {error_type}: {count}")
        
        if summary['top_errors']:
            print(f"\nTop Error Messages:")
            for i, (msg, count) in enumerate(summary['top_errors'], 1):
                print(f"  {i}. ({count}x) {msg[:100]}")
        
        # Save to file
        stats_file = Path("local_error_statistics.json")
        with open(stats_file, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"\nDetailed statistics saved to: {stats_file}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced batch test runner')
    parser.add_argument('--model', type=str, required=True, help='Model to test')
    parser.add_argument('--count', type=int, default=2, help='Number of tests per combination')
    parser.add_argument('--difficulty', type=str, default='very_easy', help='Difficulty level')
    parser.add_argument('--concurrent', action='store_true', help='Run tests concurrently')
    parser.add_argument('--workers', type=int, default=5, help='Number of concurrent workers')
    parser.add_argument('--qps', type=float, default=10.0, help='Queries per second limit')
    parser.add_argument('--smart', action='store_true', help='Use smart test selection')
    parser.add_argument('--silent', action='store_true', help='Silent mode')
    parser.add_argument('--clear', action='store_true', help='Clear previous results')
    parser.add_argument('--debug', action='store_true', help='Debug mode')
    
    args = parser.parse_args()
    
    # Create enhanced runner
    runner = EnhancedBatchTestRunner(
        debug=args.debug,
        silent=args.silent
    )
    
    # Initialize and create test tasks
    runner._lazy_init()
    runner.test_tasks = runner.create_test_tasks(
        model=args.model,
        test_count=args.count,
        difficulty=args.difficulty,
        smart_selection=args.smart
    )
    
    # Run tests
    if args.concurrent:
        results = runner.run_tests_concurrent(
            runner.test_tasks,
            max_workers=args.workers,
            qps_limit=args.qps
        )
    else:
        results = runner.run_tests_sequential(runner.test_tasks)
    
    # Print enhanced statistics
    runner.print_error_statistics()
    
    # Also print the original summary
    success_count = sum(1 for r in results if r.get('success', False))
    print(f"\n{'='*60}")
    print(f"Test Complete!")
    print(f"Success: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)")
    print(f"Model: {args.model}")
    print(f"Difficulty: {args.difficulty}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()