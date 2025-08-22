#!/usr/bin/env python3
"""
V2 data structure with hierarchical organization and proper field propagation
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class TaskTypeStatsV2:
    """Statistics for a specific task type with complete field tracking"""
    total: int = 0
    success: int = 0
    failure: int = 0
    full_success: int = 0
    partial_success: int = 0
    
    # Execution metrics
    total_execution_time: float = 0.0
    total_turns: int = 0
    total_tool_calls: int = 0
    
    # Score metrics
    total_workflow_score: float = 0.0
    total_phase2_score: float = 0.0
    total_quality_score: float = 0.0
    total_final_score: float = 0.0
    
    # Tool coverage metrics
    tool_coverage_sum: float = 0.0
    
    # Error metrics
    total_errors: int = 0
    tool_call_format_errors: int = 0
    timeout_errors: int = 0
    dependency_errors: int = 0
    parameter_config_errors: int = 0
    tool_selection_errors: int = 0
    sequence_order_errors: int = 0
    max_turns_errors: int = 0
    other_errors: int = 0
    
    # Assisted metrics
    assisted_failure: int = 0
    assisted_success: int = 0
    total_assisted_turns: int = 0
    tests_with_assistance: int = 0
    
    def update_from_test(self, test_record: Dict):
        """Update statistics from a single test record"""
        n = self.total + 1
        self.total = n
        
        # Update success metrics based on success_level
        success_level = test_record.get('success_level', 'failure')
        if success_level == 'full_success':
            self.success += 1
            self.full_success += 1
        elif success_level == 'partial_success':
            self.success += 1
            self.partial_success += 1
        else:
            self.failure += 1
        
        # Update execution metrics
        self.total_execution_time += test_record.get('execution_time', 0)
        self.total_turns += test_record.get('turns', 0)
        self.total_tool_calls += len(test_record.get('tool_calls', []))
        
        # Update score metrics using incremental averaging
        self.total_workflow_score += test_record.get('workflow_score', 0)
        self.total_phase2_score += test_record.get('phase2_score', 0)
        self.total_quality_score += test_record.get('quality_score', 0)
        self.total_final_score += test_record.get('final_score', 0)
        
        # Update tool coverage - use provided value or calculate
        if 'tool_coverage_rate' in test_record and test_record['tool_coverage_rate'] is not None:
            self.tool_coverage_sum += test_record['tool_coverage_rate']
        else:
            # Calculate from required_tools and executed_tools
            required = test_record.get('required_tools', [])
            executed = test_record.get('executed_tools', [])
            if required:
                coverage = len(set(required) & set(executed)) / len(required)
                self.tool_coverage_sum += coverage
        
        # Update error metrics if test failed
        if not test_record.get('success', False):
            self.total_errors += 1
            error_msg = test_record.get('error_message', '').lower() if test_record.get('error_message') else ''
            
            if 'format' in error_msg or 'tool call format' in error_msg:
                self.tool_call_format_errors += 1
            elif 'timeout' in error_msg:
                self.timeout_errors += 1
            elif 'dependency' in error_msg:
                self.dependency_errors += 1
            elif 'parameter' in error_msg:
                self.parameter_config_errors += 1
            elif 'tool selection' in error_msg:
                self.tool_selection_errors += 1
            elif 'sequence' in error_msg:
                self.sequence_order_errors += 1
            elif 'max turns' in error_msg:
                self.max_turns_errors += 1
            else:
                self.other_errors += 1
        
        # Update assisted metrics
        if test_record.get('format_error_count', 0) > 0:
            self.tests_with_assistance += 1
            self.total_assisted_turns += test_record.get('format_error_count', 0)
            if test_record.get('success', False):
                self.assisted_success += 1
            else:
                self.assisted_failure += 1
    
    def to_dict(self) -> Dict:
        """Convert to dictionary with calculated rates"""
        if self.total == 0:
            return {
                'total': 0,
                'success': 0,
                'success_rate': 0.0,
                'tool_coverage_rate': 0.0
            }
        
        return {
            'total': self.total,
            'success': self.success,
            'success_rate': self.success / self.total if self.total > 0 else 0.0,
            'weighted_success_score': (self.full_success * 1.0 + self.partial_success * 0.5) / self.total if self.total > 0 else 0.0,
            'full_success_rate': self.full_success / self.total if self.total > 0 else 0.0,
            'partial_success_rate': self.partial_success / self.total if self.total > 0 else 0.0,
            'failure_rate': self.failure / self.total if self.total > 0 else 0.0,
            'avg_execution_time': self.total_execution_time / self.total if self.total > 0 else 0.0,
            'avg_turns': self.total_turns / self.total if self.total > 0 else 0.0,
            'avg_tool_calls': self.total_tool_calls / self.total if self.total > 0 else 0.0,
            'tool_coverage_rate': self.tool_coverage_sum / self.total if self.total > 0 else 0.0,
            'avg_workflow_score': self.total_workflow_score / self.total if self.total > 0 else 0.0,
            'avg_phase2_score': self.total_phase2_score / self.total if self.total > 0 else 0.0,
            'avg_quality_score': self.total_quality_score / self.total if self.total > 0 else 0.0,
            'avg_final_score': self.total_final_score / self.total if self.total > 0 else 0.0,
            'total_errors': self.total_errors,
            'tool_call_format_errors': self.tool_call_format_errors,
            'timeout_errors': self.timeout_errors,
            'dependency_errors': self.dependency_errors,
            'parameter_config_errors': self.parameter_config_errors,
            'tool_selection_errors': self.tool_selection_errors,
            'sequence_order_errors': self.sequence_order_errors,
            'max_turns_errors': self.max_turns_errors,
            'tool_selection_error_rate': self.tool_selection_errors / self.total_errors if self.total_errors > 0 else 0.0,
            'parameter_error_rate': self.parameter_config_errors / self.total_errors if self.total_errors > 0 else 0.0,
            'sequence_error_rate': self.sequence_order_errors / self.total_errors if self.total_errors > 0 else 0.0,
            'dependency_error_rate': self.dependency_errors / self.total_errors if self.total_errors > 0 else 0.0,
            'timeout_error_rate': self.timeout_errors / self.total_errors if self.total_errors > 0 else 0.0,
            'format_error_rate': self.tool_call_format_errors / self.total_errors if self.total_errors > 0 else 0.0,
            'max_turns_error_rate': self.max_turns_errors / self.total_errors if self.total_errors > 0 else 0.0,
            'assisted_failure': self.assisted_failure,
            'assisted_success': self.assisted_success,
            'total_assisted_turns': self.total_assisted_turns,
            'tests_with_assistance': self.tests_with_assistance,
            'avg_assisted_turns': self.total_assisted_turns / self.tests_with_assistance if self.tests_with_assistance > 0 else 0.0,
            'assisted_success_rate': self.assisted_success / (self.assisted_success + self.assisted_failure) if (self.assisted_success + self.assisted_failure) > 0 else 0.0,
            'assistance_rate': self.tests_with_assistance / self.total if self.total > 0 else 0.0
        }


@dataclass
class DifficultyStatsV2:
    """Statistics for a specific difficulty level"""
    by_task_type: Dict[str, TaskTypeStatsV2] = field(default_factory=dict)
    
    def get_or_create_task_type(self, task_type: str) -> TaskTypeStatsV2:
        if task_type not in self.by_task_type:
            self.by_task_type[task_type] = TaskTypeStatsV2()
        return self.by_task_type[task_type]


@dataclass
class ToolSuccessRateStatsV2:
    """Statistics for a specific tool success rate"""
    by_difficulty: Dict[str, DifficultyStatsV2] = field(default_factory=dict)
    
    def get_or_create_difficulty(self, difficulty: str) -> DifficultyStatsV2:
        if difficulty not in self.by_difficulty:
            self.by_difficulty[difficulty] = DifficultyStatsV2()
        return self.by_difficulty[difficulty]


@dataclass
class PromptTypeStatsV2:
    """Statistics for a specific prompt type"""
    by_tool_success_rate: Dict[float, ToolSuccessRateStatsV2] = field(default_factory=dict)
    
    def get_or_create_rate_bucket(self, tool_success_rate: float) -> ToolSuccessRateStatsV2:
        # Round to 4 decimal places for bucketing
        rate_bucket = round(tool_success_rate, 4)
        if rate_bucket not in self.by_tool_success_rate:
            self.by_tool_success_rate[rate_bucket] = ToolSuccessRateStatsV2()
        return self.by_tool_success_rate[rate_bucket]


@dataclass
class ModelStatisticsV2:
    """Complete statistics for a model with hierarchical structure"""
    model_name: str
    by_prompt_type: Dict[str, PromptTypeStatsV2] = field(default_factory=dict)
    
    def get_or_create_prompt_type(self, prompt_type: str) -> PromptTypeStatsV2:
        if prompt_type not in self.by_prompt_type:
            self.by_prompt_type[prompt_type] = PromptTypeStatsV2()
        return self.by_prompt_type[prompt_type]
    
    def update_from_test(self, prompt_type: str, tool_success_rate: float, 
                        difficulty: str, task_type: str, test_record: Dict):
        """Update statistics from a test record"""
        prompt_stats = self.get_or_create_prompt_type(prompt_type)
        rate_stats = prompt_stats.get_or_create_rate_bucket(tool_success_rate)
        diff_stats = rate_stats.get_or_create_difficulty(difficulty)
        task_stats = diff_stats.get_or_create_task_type(task_type)
        
        # Update the task type statistics
        task_stats.update_from_test(test_record)
    
    def get_task_stats(self, prompt_type: str, tool_success_rate: float,
                      difficulty: str, task_type: str) -> Optional[TaskTypeStatsV2]:
        """Get statistics for a specific task configuration"""
        if prompt_type not in self.by_prompt_type:
            return None
        
        prompt_stats = self.by_prompt_type[prompt_type]
        rate_bucket = round(tool_success_rate, 4)
        
        if rate_bucket not in prompt_stats.by_tool_success_rate:
            return None
        
        rate_stats = prompt_stats.by_tool_success_rate[rate_bucket]
        
        if difficulty not in rate_stats.by_difficulty:
            return None
        
        diff_stats = rate_stats.by_difficulty[difficulty]
        
        if task_type not in diff_stats.by_task_type:
            return None
        
        return diff_stats.by_task_type[task_type]
    
    def get_overall_stats(self) -> Dict:
        """Calculate overall statistics across all tests"""
        total_tests = 0
        total_success = 0
        total_full = 0
        total_partial = 0
        total_failure = 0
        total_execution_time = 0
        total_turns = 0
        tool_coverage_sum = 0
        
        for prompt_stats in self.by_prompt_type.values():
            for rate_stats in prompt_stats.by_tool_success_rate.values():
                for diff_stats in rate_stats.by_difficulty.values():
                    for task_stats in diff_stats.by_task_type.values():
                        total_tests += task_stats.total
                        total_success += task_stats.success
                        total_full += task_stats.full_success
                        total_partial += task_stats.partial_success
                        total_failure += task_stats.failure
                        total_execution_time += task_stats.total_execution_time
                        total_turns += task_stats.total_turns
                        tool_coverage_sum += task_stats.tool_coverage_sum
        
        if total_tests == 0:
            return {
                'total_success': 0,
                'total_partial': 0,
                'total_full': 0,
                'total_failure': 0,
                'success_rate': 0.0,
                'weighted_success_score': 0.0,
                'avg_execution_time': 0.0,
                'avg_turns': 0.0,
                'tool_coverage_rate': 0.0
            }
        
        return {
            'total_success': total_success,
            'total_partial': total_partial,
            'total_full': total_full,
            'total_failure': total_failure,
            'success_rate': total_success / total_tests,
            'weighted_success_score': (total_full * 1.0 + total_partial * 0.5) / total_tests,
            'avg_execution_time': total_execution_time / total_tests,
            'avg_turns': total_turns / total_tests,
            'tool_coverage_rate': tool_coverage_sum / total_tests
        }
    
    def get_prompt_type_summary(self, prompt_type: str) -> Dict:
        """Get summary statistics for a specific prompt type"""
        if prompt_type not in self.by_prompt_type:
            return {}
        
        prompt_stats = self.by_prompt_type[prompt_type]
        
        # Aggregate across all tool success rates, difficulties, and task types
        total = 0
        success = 0
        full_success = 0
        partial_success = 0
        failure = 0
        total_execution_time = 0
        total_turns = 0
        total_tool_calls = 0
        tool_coverage_sum = 0
        total_workflow_score = 0
        total_phase2_score = 0
        total_quality_score = 0
        total_final_score = 0
        
        # Error metrics
        total_errors = 0
        tool_call_format_errors = 0
        timeout_errors = 0
        dependency_errors = 0
        parameter_config_errors = 0
        tool_selection_errors = 0
        sequence_order_errors = 0
        max_turns_errors = 0
        
        # Assisted metrics
        assisted_failure = 0
        assisted_success = 0
        total_assisted_turns = 0
        tests_with_assistance = 0
        
        for rate_stats in prompt_stats.by_tool_success_rate.values():
            for diff_stats in rate_stats.by_difficulty.values():
                for task_stats in diff_stats.by_task_type.values():
                    total += task_stats.total
                    success += task_stats.success
                    full_success += task_stats.full_success
                    partial_success += task_stats.partial_success
                    failure += task_stats.failure
                    total_execution_time += task_stats.total_execution_time
                    total_turns += task_stats.total_turns
                    total_tool_calls += task_stats.total_tool_calls
                    tool_coverage_sum += task_stats.tool_coverage_sum
                    total_workflow_score += task_stats.total_workflow_score
                    total_phase2_score += task_stats.total_phase2_score
                    total_quality_score += task_stats.total_quality_score
                    total_final_score += task_stats.total_final_score
                    
                    # Aggregate errors
                    total_errors += task_stats.total_errors
                    tool_call_format_errors += task_stats.tool_call_format_errors
                    timeout_errors += task_stats.timeout_errors
                    dependency_errors += task_stats.dependency_errors
                    parameter_config_errors += task_stats.parameter_config_errors
                    tool_selection_errors += task_stats.tool_selection_errors
                    sequence_order_errors += task_stats.sequence_order_errors
                    max_turns_errors += task_stats.max_turns_errors
                    
                    # Aggregate assisted metrics
                    assisted_failure += task_stats.assisted_failure
                    assisted_success += task_stats.assisted_success
                    total_assisted_turns += task_stats.total_assisted_turns
                    tests_with_assistance += task_stats.tests_with_assistance
        
        if total == 0:
            return {}
        
        return {
            'total': total,
            'success': success,
            'success_rate': success / total,
            'weighted_success_score': (full_success * 1.0 + partial_success * 0.5) / total,
            'full_success_rate': full_success / total,
            'partial_success_rate': partial_success / total,
            'failure_rate': failure / total,
            'assisted_failure': assisted_failure,
            'assisted_success': assisted_success,
            'total_assisted_turns': total_assisted_turns,
            'tests_with_assistance': tests_with_assistance,
            'avg_assisted_turns': total_assisted_turns / tests_with_assistance if tests_with_assistance > 0 else 0.0,
            'assisted_success_rate': assisted_success / (assisted_success + assisted_failure) if (assisted_success + assisted_failure) > 0 else 0.0,
            'assistance_rate': tests_with_assistance / total,
            'avg_execution_time': total_execution_time / total,
            'avg_turns': total_turns / total,
            'avg_tool_calls': total_tool_calls / total,
            'tool_coverage_rate': tool_coverage_sum / total,
            'avg_workflow_score': total_workflow_score / total,
            'avg_phase2_score': total_phase2_score / total,
            'avg_quality_score': total_quality_score / total,
            'avg_final_score': total_final_score / total,
            'total_errors': total_errors,
            'tool_call_format_errors': tool_call_format_errors,
            'timeout_errors': timeout_errors,
            'dependency_errors': dependency_errors,
            'parameter_config_errors': parameter_config_errors,
            'tool_selection_errors': tool_selection_errors,
            'sequence_order_errors': sequence_order_errors,
            'max_turns_errors': max_turns_errors,
            'tool_selection_error_rate': tool_selection_errors / total_errors if total_errors > 0 else 0.0,
            'parameter_error_rate': parameter_config_errors / total_errors if total_errors > 0 else 0.0,
            'sequence_error_rate': sequence_order_errors / total_errors if total_errors > 0 else 0.0,
            'dependency_error_rate': dependency_errors / total_errors if total_errors > 0 else 0.0,
            'timeout_error_rate': timeout_errors / total_errors if total_errors > 0 else 0.0,
            'format_error_rate': tool_call_format_errors / total_errors if total_errors > 0 else 0.0,
            'max_turns_error_rate': max_turns_errors / total_errors if total_errors > 0 else 0.0
        }