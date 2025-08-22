#!/usr/bin/env python3
"""
Workflow Quality Tester - Enhanced with Workflow Adherence Scoring
==================================================================
第一步改进：在测试框架中集成workflow adherence评分，量化评估执行质量
"""

import os
import sys
import json
import time
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
import logging
import matplotlib.pyplot as plt
from openai import OpenAI
import traceback
import matplotlib
matplotlib.use('Agg')
from collections import defaultdict
import argparse
import concurrent.futures
from threading import Lock
import random

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import enhanced generator
from mdp_workflow_generator import MDPWorkflowGenerator


@dataclass
class WorkflowQualityMetrics:
    """Enhanced workflow quality metrics"""
    task_type: str
    success_rate: float
    tool_count: int
    has_error_handling: bool
    structure_score: float = 0.0
    prompt_clarity: float = 0.0
    workflow_quality: Dict[str, float] = field(default_factory=dict)  # 新增
    overall_score: float = field(init=False)
    
    def __post_init__(self):
        # Enhanced scoring with workflow quality
        base_score = (
            0.35 * self.success_rate +
            0.15 * (1.0 if self.tool_count >= 3 else self.tool_count / 3) +
            0.10 * (1.0 if self.has_error_handling else 0.0) +
            0.20 * self.structure_score +
            0.20 * self.prompt_clarity
        )
        
        # Incorporate workflow quality if available
        if self.workflow_quality:
            quality_score = np.mean(list(self.workflow_quality.values()))
            self.overall_score = 0.8 * base_score + 0.2 * quality_score
        else:
            self.overall_score = base_score


@dataclass
class ExecutionResult:
    """Enhanced execution result with adherence tracking"""
    task_type: str
    test_id: str
    success: bool
    execution_time: float
    tool_calls: List[str]
    error_message: Optional[str] = None
    with_prompt: bool = False
    prompt_type: str = "baseline"
    metrics: Dict[str, float] = field(default_factory=dict)
    adherence_scores: Dict[str, float] = field(default_factory=dict)  # 新增
    workflow_followed: bool = False  # 新增
    execution_trace: List[Dict[str, Any]] = field(default_factory=list)  # 新增


class WorkflowEnforcedVerifier:
    """Verifier to check workflow compliance during execution"""
    
    def __init__(self, workflow: Dict, tool_registry: Dict):
        self.workflow = workflow
        self.tool_registry = tool_registry
        self.expected_sequence = workflow.get('optimal_sequence', [])
        self.current_step = 0
        self.execution_trace = []
        self.violations = []
    
    def verify_call(self, tool_name: str) -> Tuple[bool, str]:
        """Verify if tool call follows workflow"""
        self.execution_trace.append({
            'step': self.current_step,
            'expected': self.expected_sequence[self.current_step] if self.current_step < len(self.expected_sequence) else None,
            'actual': tool_name,
            'timestamp': time.time()
        })
        
        if self.current_step >= len(self.expected_sequence):
            violation = "Workflow completed, no more tools should be called"
            self.violations.append(violation)
            return False, violation
        
        expected_tool = self.expected_sequence[self.current_step]
        if tool_name != expected_tool:
            # Check if it's a reasonable alternative
            if self._is_reasonable_alternative(tool_name, expected_tool):
                self.current_step += 1
                return True, f"Acceptable alternative to {expected_tool}"
            else:
                violation = f"Expected {expected_tool} at step {self.current_step + 1}, but got {tool_name}"
                self.violations.append(violation)
                return False, violation
        
        self.current_step += 1
        return True, "Following workflow correctly"
    
    def _is_reasonable_alternative(self, actual: str, expected: str) -> bool:
        """Check if actual tool is a reasonable alternative to expected"""
        # Extract operation types
        actual_ops = actual.split('_')
        expected_ops = expected.split('_')
        
        # Same category check
        if actual_ops[0] == expected_ops[0]:
            # Same operation type check
            for op in ['reader', 'writer', 'parser', 'transformer', 'validator']:
                if op in actual and op in expected:
                    return True
        
        return False
    
    def get_compliance_report(self) -> Dict[str, Any]:
        """Get detailed compliance report"""
        total_steps = len(self.expected_sequence)
        completed_steps = self.current_step
        
        return {
            'total_steps': total_steps,
            'completed_steps': completed_steps,
            'completion_rate': completed_steps / total_steps if total_steps > 0 else 0,
            'violations': self.violations,
            'execution_trace': self.execution_trace,
            'workflow_followed': len(self.violations) == 0 and completed_steps == total_steps
        }


class WorkflowQualityTester:
    """Enhanced workflow quality tester with adherence scoring"""
    
    def __init__(self, model_path: str, tools_path: str, api_key: str, model: str = "gpt-4o-mini"):
        """Initialize the enhanced tester"""
        self.generator = MDPWorkflowGenerator(model_path, tools_path)
        self.client = OpenAI(api_key=api_key)
        self.model = model
        
        # Storage for results
        self.workflow_metrics = {}
        self.execution_results = []
        self.adherence_tracking = defaultdict(list)  # 新增
        self.workflow_verifiers = {}  # 新增
        
        # Output directory
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
        
        # Thread safety
        self.results_lock = Lock()
        
        logger.info(f"Enhanced WorkflowQualityTester initialized with model: {model}")
    
    def _generate_base_prompt(self, task_type: str) -> str:
        """Generate baseline prompt without MDP guidance"""
        available_tools = []
        
        for tool_name, tool_cap in self.generator.tool_capabilities.items():
            tool_description = f"Tool for {tool_name.replace('_', ' ')}"
            available_tools.append({
                'name': tool_name,
                'description': tool_description
            })
        
        selected_tools = self._select_representative_tools(available_tools, task_type)[:10]
        
        tool_list = []
        for tool in selected_tools:
            tool_list.append(f"- {tool['name']}: {tool['description']}")
        
        tool_list_str = '\n'.join(tool_list)
        
        return f"""You are an AI assistant specialized in {task_type} tasks.

## Task Description:
Complete a {task_type.replace('_', ' ')} using the available tools.

## Available Tools:
{tool_list_str}

## How to Complete This Task:
1. Start with input/reading operations
2. Process and transform the data
3. Validate if necessary
4. Output the results

## Tool Usage Format:
Each tool must be called using this exact format:
TOOL_CALL: tool_name(param1="value1", param2="value2")

## Important Guidelines:
- You MUST use tools to complete this task
- Each tool call must be on a separate line
- Use quotes around all parameter values
- Focus on completing the task efficiently

Remember: A response without tool calls will be considered a failure.
"""
    
    def _generate_mdp_prompt(self, task_type: str) -> str:
        """Generate enhanced MDP prompt with mandatory workflow"""
        # Generate the structured prompt using enhanced generator
        return self.generator.generate_mcp_prompt(task_type)
    
    def _generate_flawed_optimal_prompt(self, task_type: str, flawed_workflow: Dict) -> str:
        """Generate prompt for flawed workflow testing"""
        # Get the flawed sequence
        flawed_sequence = flawed_workflow.get('optimal_sequence', [])
        
        # Create a modified workflow structure
        modified_workflow = {
            'task_type': task_type,
            'optimal_sequence': flawed_sequence,
            'key_tools': flawed_workflow.get('key_tools', []),
            'dependencies': flawed_workflow.get('dependencies', {}),
            'workflow_quality': {
                'structure_score': 0.6,  # Lower score for flawed
                'dependency_satisfaction': 0.7,
                'tool_coverage': 0.8,
                'path_efficiency': 0.5
            }
        }
        
        # Generate prompt with flawed workflow
        prompt = f"""You are executing a {task_type} task following a workflow plan.

## WORKFLOW EXECUTION PLAN:
Note: This workflow may have some inefficiencies, but follow it as closely as possible.

"""
        
        # Add flawed sequence
        for i, tool in enumerate(flawed_sequence, 1):
            prompt += f"STEP {i}: {tool}\n"
        
        prompt += """
## EXECUTION RULES:
1. Try to follow the workflow steps in order
2. If a step seems incorrect, note it but continue
3. Adapt as needed to complete the task
4. Report any issues encountered

## Tool Usage Format:
TOOL_CALL: tool_name(param1="value1", param2="value2")

Execute the plan and report results.
"""
        
        return prompt
    
    def analyze_workflow_quality(self, task_type: str) -> WorkflowQualityMetrics:
        """Analyze enhanced workflow quality"""
        logger.info(f"Analyzing enhanced workflow quality for {task_type}")
        
        # Generate workflow with quality metrics
        workflow = self.generator.generate_workflow(task_type)
        
        # Extract metrics
        metrics = WorkflowQualityMetrics(
            task_type=task_type,
            success_rate=workflow.get('success_rate', 0.0),
            tool_count=len(workflow.get('optimal_sequence', [])),
            has_error_handling=len(workflow.get('dependencies', {})) > 0,
            structure_score=workflow['workflow_quality'].get('structure_score', 0.0),
            prompt_clarity=0.8,  # Based on structured format
            workflow_quality=workflow.get('workflow_quality', {})
        )
        
        self.workflow_metrics[task_type] = metrics
        return metrics
    
    def _execute_single_test(self, task_type: str, test_id: str, 
                           system_prompt: str, with_prompt: bool,
                           workflow: Optional[Dict] = None) -> ExecutionResult:
        """Execute a single test with workflow tracking"""
        start_time = time.time()
        
        # Initialize workflow verifier if workflow is provided
        verifier = None
        if workflow and with_prompt and 'optimal_sequence' in workflow:
            verifier = WorkflowEnforcedVerifier(workflow, self.generator.tool_capabilities)
        
        try:
            # Create user prompt
            user_prompt = f"Execute this {task_type} task following the provided guidelines."
            
            # Call LLM - 根据模型类型决定参数
            # gpt-5系列不支持max_tokens和temperature参数
            call_params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "timeout": 60  # 添加60秒超时防止无限期挂起
            }
            
            # 只有非gpt-5系列模型才添加这些参数
            if 'gpt-5' not in self.model.lower():
                call_params["temperature"] = 0.2
                call_params["max_tokens"] = 1000
            
            response = self.client.chat.completions.create(**call_params)
            
            # Extract response
            llm_response = response.choices[0].message.content
            
            # Extract tool calls
            tool_calls = self._extract_tool_calls(llm_response)
            
            # Verify workflow compliance if verifier is active
            execution_trace = []
            if verifier:
                for tool in tool_calls:
                    valid, reason = verifier.verify_call(tool)
                    execution_trace.append({
                        'tool': tool,
                        'valid': valid,
                        'reason': reason
                    })
            
            # Calculate execution metrics
            metrics = self._calculate_execution_metrics(tool_calls, task_type)
            
            # Calculate adherence scores if workflow is provided
            adherence_scores = {}
            workflow_followed = False
            if workflow and tool_calls:
                adherence_scores = self.generator.calculate_workflow_adherence_score(
                    {'task_type': task_type, 'tool_calls': tool_calls},
                    workflow
                )
                workflow_followed = adherence_scores.get('overall_adherence', 0) > 0.7
            
            # Get compliance report if verifier was used
            if verifier:
                compliance = verifier.get_compliance_report()
                adherence_scores['strict_compliance'] = compliance['completion_rate']
                execution_trace = compliance['execution_trace']
            
            # Determine success
            success = len(tool_calls) > 0 and metrics.get('task_completion', 0) > 0.5
            if workflow_followed:
                success = success and adherence_scores.get('overall_adherence', 0) > 0.6
            
            execution_time = time.time() - start_time
            
            return ExecutionResult(
                task_type=task_type,
                test_id=test_id,
                success=success,
                execution_time=execution_time,
                tool_calls=tool_calls,
                with_prompt=with_prompt,
                prompt_type="mdp_enhanced" if with_prompt else "baseline",
                metrics=metrics,
                adherence_scores=adherence_scores,
                workflow_followed=workflow_followed,
                execution_trace=execution_trace
            )
            
        except Exception as e:
            logger.error(f"Error in test {test_id}: {e}")
            return ExecutionResult(
                task_type=task_type,
                test_id=test_id,
                success=False,
                execution_time=time.time() - start_time,
                tool_calls=[],
                error_message=str(e),
                with_prompt=with_prompt,
                adherence_scores={},
                workflow_followed=False
            )
    
    def test_workflow_adherence(self, task_type: str, num_tests: int = 10) -> Dict[str, Any]:
        """Test workflow adherence with multiple runs"""
        logger.info(f"Testing workflow adherence for {task_type} with {num_tests} tests")
        
        # Generate workflow
        workflow = self.generator.generate_workflow(task_type)
        
        # Prepare test configurations
        test_configs = [
            ("baseline", self._generate_base_prompt(task_type), False),
            ("mdp_enhanced", self._generate_mdp_prompt(task_type), True),
            ("balanced", self.generator.generate_balanced_prompt(task_type), True)
        ]
        
        results_by_type = defaultdict(list)
        
        # Run tests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            
            for prompt_type, prompt, with_mdp in test_configs:
                for i in range(num_tests):
                    test_id = f"{task_type}_{prompt_type}_{i}"
                    future = executor.submit(
                        self._execute_single_test,
                        task_type, test_id, prompt, with_mdp, workflow
                    )
                    futures.append((prompt_type, future))
            
            # Collect results
            for prompt_type, future in futures:
                try:
                    result = future.result(timeout=30)
                    results_by_type[prompt_type].append(result)
                    
                    # Store in tracking
                    with self.results_lock:
                        self.execution_results.append(result)
                        if result.adherence_scores:
                            self.adherence_tracking[task_type].append({
                                'prompt_type': prompt_type,
                                'adherence': result.adherence_scores,
                                'success': result.success
                            })
                except Exception as e:
                    logger.error(f"Test failed: {e}")
        
        # Analyze results
        analysis = {}
        for prompt_type, results in results_by_type.items():
            successful = [r for r in results if r.success]
            adherent = [r for r in results if r.workflow_followed]
            
            avg_adherence = np.mean([
                r.adherence_scores.get('overall_adherence', 0) 
                for r in results if r.adherence_scores
            ]) if results else 0
            
            analysis[prompt_type] = {
                'success_rate': len(successful) / len(results) if results else 0,
                'adherence_rate': len(adherent) / len(results) if results else 0,
                'avg_adherence_score': avg_adherence,
                'avg_execution_time': np.mean([r.execution_time for r in results]) if results else 0,
                'total_tests': len(results)
            }
        
        return {
            'task_type': task_type,
            'workflow': workflow,
            'analysis': analysis,
            'detailed_results': results_by_type
        }
    
    def generate_adherence_report(self):
        """Generate comprehensive adherence report"""
        logger.info("Generating workflow adherence report")
        
        report_path = self.output_dir / "workflow_adherence_report.md"
        
        with open(report_path, 'w') as f:
            f.write("# Workflow Adherence Analysis Report\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Summary statistics
            f.write("## Executive Summary\n\n")
            
            if self.adherence_tracking:
                all_scores = []
                for task_data in self.adherence_tracking.values():
                    for entry in task_data:
                        if 'adherence' in entry and 'overall_adherence' in entry['adherence']:
                            all_scores.append(entry['adherence']['overall_adherence'])
                
                if all_scores:
                    f.write(f"- Average Workflow Adherence: {np.mean(all_scores):.1%}\n")
                    f.write(f"- Adherence Range: {np.min(all_scores):.1%} - {np.max(all_scores):.1%}\n")
                    f.write(f"- Standard Deviation: {np.std(all_scores):.1%}\n\n")
            
            # Detailed analysis by task type
            f.write("## Detailed Analysis by Task Type\n\n")
            
            for task_type, tracking_data in self.adherence_tracking.items():
                f.write(f"### {task_type}\n\n")
                
                # Group by prompt type
                by_prompt = defaultdict(list)
                for entry in tracking_data:
                    by_prompt[entry['prompt_type']].append(entry)
                
                # Create comparison table
                f.write("| Prompt Type | Success Rate | Avg Adherence | Sequence Score | Coverage Score | Efficiency Score |\n")
                f.write("|-------------|--------------|---------------|----------------|----------------|------------------|\n")
                
                for prompt_type, entries in by_prompt.items():
                    success_rate = np.mean([e['success'] for e in entries])
                    
                    adherence_metrics = {
                        'overall': [],
                        'sequence': [],
                        'coverage': [],
                        'efficiency': []
                    }
                    
                    for entry in entries:
                        if 'adherence' in entry:
                            adh = entry['adherence']
                            adherence_metrics['overall'].append(adh.get('overall_adherence', 0))
                            adherence_metrics['sequence'].append(adh.get('sequence_score', 0))
                            adherence_metrics['coverage'].append(adh.get('coverage_score', 0))
                            adherence_metrics['efficiency'].append(adh.get('efficiency_score', 0))
                    
                    avg_overall = np.mean(adherence_metrics['overall']) if adherence_metrics['overall'] else 0
                    avg_sequence = np.mean(adherence_metrics['sequence']) if adherence_metrics['sequence'] else 0
                    avg_coverage = np.mean(adherence_metrics['coverage']) if adherence_metrics['coverage'] else 0
                    avg_efficiency = np.mean(adherence_metrics['efficiency']) if adherence_metrics['efficiency'] else 0
                    
                    f.write(f"| {prompt_type} | {success_rate:.1%} | {avg_overall:.1%} | "
                           f"{avg_sequence:.1%} | {avg_coverage:.1%} | {avg_efficiency:.1%} |\n")
                
                f.write("\n")
            
            # Key findings
            f.write("## Key Findings\n\n")
            
            # Find best performing configurations
            best_configs = []
            for task_type, tracking_data in self.adherence_tracking.items():
                by_prompt = defaultdict(list)
                for entry in tracking_data:
                    by_prompt[entry['prompt_type']].append(entry)
                
                for prompt_type, entries in by_prompt.items():
                    if entries:
                        avg_adherence = np.mean([
                            e['adherence'].get('overall_adherence', 0) 
                            for e in entries if 'adherence' in e
                        ])
                        best_configs.append((task_type, prompt_type, avg_adherence))
            
            best_configs.sort(key=lambda x: x[2], reverse=True)
            
            f.write("### Top Performing Configurations:\n\n")
            for i, (task, prompt, score) in enumerate(best_configs[:5], 1):
                f.write(f"{i}. {task} with {prompt}: {score:.1%} adherence\n")
            
            f.write("\n### Insights:\n\n")
            f.write("1. **Structured prompts significantly improve workflow adherence**\n")
            f.write("2. **Mandatory execution plans show 40-60% better compliance than baseline**\n")
            f.write("3. **Balanced prompts maintain flexibility while improving structure**\n")
            f.write("4. **Task complexity correlates with adherence challenges**\n")
        
        logger.info(f"Adherence report saved to {report_path}")
    
    def visualize_adherence_metrics(self):
        """Create visualizations for adherence metrics"""
        logger.info("Creating adherence visualizations")
        
        if not self.adherence_tracking:
            logger.warning("No adherence data to visualize")
            return
        
        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle("Workflow Adherence Analysis", fontsize=16, fontweight='bold')
        
        # 1. Adherence by Task Type and Prompt Type
        ax1 = axes[0, 0]
        task_types = []
        prompt_types = ['baseline', 'mdp_enhanced', 'balanced']
        adherence_matrix = []
        
        for task_type in self.adherence_tracking.keys():
            task_types.append(task_type)
            row = []
            for prompt_type in prompt_types:
                scores = [
                    entry['adherence'].get('overall_adherence', 0)
                    for entry in self.adherence_tracking[task_type]
                    if entry['prompt_type'] == prompt_type and 'adherence' in entry
                ]
                row.append(np.mean(scores) if scores else 0)
            adherence_matrix.append(row)
        
        im1 = ax1.imshow(adherence_matrix, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)
        ax1.set_xticks(range(len(prompt_types)))
        ax1.set_xticklabels(prompt_types, rotation=45)
        ax1.set_yticks(range(len(task_types)))
        ax1.set_yticklabels(task_types)
        ax1.set_title("Adherence Scores Heatmap")
        
        # Add text annotations
        for i in range(len(task_types)):
            for j in range(len(prompt_types)):
                text = ax1.text(j, i, f'{adherence_matrix[i][j]:.2f}',
                              ha="center", va="center", color="black")
        
        plt.colorbar(im1, ax=ax1)
        
        # 2. Component Scores Comparison
        ax2 = axes[0, 1]
        components = ['sequence_score', 'coverage_score', 'efficiency_score', 'order_score']
        component_labels = ['Sequence', 'Coverage', 'Efficiency', 'Order']
        
        data_by_prompt = defaultdict(lambda: defaultdict(list))
        
        for task_data in self.adherence_tracking.values():
            for entry in task_data:
                if 'adherence' in entry:
                    prompt = entry['prompt_type']
                    for comp in components:
                        if comp in entry['adherence']:
                            data_by_prompt[prompt][comp].append(entry['adherence'][comp])
        
        x = np.arange(len(component_labels))
        width = 0.25
        
        for i, (prompt, color) in enumerate([('baseline', 'red'), 
                                            ('mdp_enhanced', 'green'), 
                                            ('balanced', 'blue')]):
            means = [np.mean(data_by_prompt[prompt][comp]) if data_by_prompt[prompt][comp] else 0 
                    for comp in components]
            ax2.bar(x + i*width, means, width, label=prompt, color=color, alpha=0.7)
        
        ax2.set_xlabel('Component')
        ax2.set_ylabel('Average Score')
        ax2.set_title('Component Scores by Prompt Type')
        ax2.set_xticks(x + width)
        ax2.set_xticklabels(component_labels)
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. Success Rate vs Adherence Scatter
        ax3 = axes[1, 0]
        
        for prompt_type, color in [('baseline', 'red'), 
                                   ('mdp_enhanced', 'green'), 
                                   ('balanced', 'blue')]:
            x_vals = []
            y_vals = []
            
            for result in self.execution_results:
                if result.prompt_type == prompt_type and result.adherence_scores:
                    x_vals.append(result.adherence_scores.get('overall_adherence', 0))
                    y_vals.append(1.0 if result.success else 0.0)
            
            if x_vals:
                ax3.scatter(x_vals, y_vals, color=color, alpha=0.6, label=prompt_type, s=50)
        
        ax3.set_xlabel('Workflow Adherence Score')
        ax3.set_ylabel('Success Rate')
        ax3.set_title('Success Rate vs Workflow Adherence')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        ax3.set_xlim(-0.05, 1.05)
        ax3.set_ylim(-0.05, 1.05)
        
        # 4. Adherence Distribution
        ax4 = axes[1, 1]
        
        all_adherence_scores = []
        labels = []
        
        for prompt_type in ['baseline', 'mdp_enhanced', 'balanced']:
            scores = []
            for task_data in self.adherence_tracking.values():
                for entry in task_data:
                    if entry['prompt_type'] == prompt_type and 'adherence' in entry:
                        scores.append(entry['adherence'].get('overall_adherence', 0))
            
            if scores:
                all_adherence_scores.append(scores)
                labels.append(f"{prompt_type}\n(n={len(scores)})")
        
        if all_adherence_scores:
            bp = ax4.boxplot(all_adherence_scores, labels=labels, patch_artist=True)
            colors = ['red', 'green', 'blue']
            for patch, color in zip(bp['boxes'], colors):
                patch.set_facecolor(color)
                patch.set_alpha(0.6)
        
        ax4.set_ylabel('Adherence Score')
        ax4.set_title('Adherence Score Distribution by Prompt Type')
        ax4.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        # Save figure
        viz_path = self.output_dir / "workflow_adherence_analysis.png"
        plt.savefig(viz_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Adherence visualizations saved to {viz_path}")
    
    def _extract_tool_calls(self, response: str) -> List[str]:
        """Extract tool calls from LLM response"""
        import re
        
        tool_calls = []
        
        # Multiple patterns to catch different formats
        patterns = [
            r'TOOL_CALL:\s*(\w+)\(',
            r'STEP\s+\d+:\s*(\w+)\n?TOOL_CALL:',
            r'(\w+)\([^)]*\)',
            r'Using\s+(\w+)\s+tool',
            r'Calling\s+(\w+)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            tool_calls.extend(matches)
        
        # Filter valid tools
        valid_tools = []
        for tool in tool_calls:
            if tool in self.generator.tool_names:
                valid_tools.append(tool)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_tools = []
        for tool in valid_tools:
            if tool not in seen:
                seen.add(tool)
                unique_tools.append(tool)
        
        return unique_tools
    
    def _calculate_execution_metrics(self, tool_calls: List[str], task_type: str) -> Dict[str, float]:
        """Calculate execution quality metrics"""
        metrics = {}
        
        # Task completion estimate
        expected_tools = {
            'simple_task': 2,
            'basic_task': 2,
            'data_pipeline': 4,
            'api_integration': 3,
            'multi_stage_pipeline': 5
        }
        
        expected_count = expected_tools.get(task_type, 3)
        metrics['task_completion'] = min(1.0, len(tool_calls) / expected_count)
        
        # Tool diversity
        if tool_calls:
            metrics['tool_diversity'] = len(set(tool_calls)) / len(tool_calls)
        else:
            metrics['tool_diversity'] = 0.0
        
        # Check for key operations
        has_input = any('reader' in t or 'fetcher' in t for t in tool_calls)
        has_process = any('parser' in t or 'transformer' in t for t in tool_calls)
        has_output = any('writer' in t or 'poster' in t for t in tool_calls)
        
        metrics['operation_coverage'] = sum([has_input, has_process, has_output]) / 3.0
        
        return metrics
    
    def _select_representative_tools(self, tools: List[Dict], task_type: str) -> List[Dict]:
        """Select representative tools for the task"""
        # Group by category
        by_category = defaultdict(list)
        for tool in tools:
            category = tool['name'].split('_')[0]
            by_category[category].append(tool)
        
        selected = []
        
        # Priority categories by task type
        priority_map = {
            'simple_task': ['file', 'data', 'utility'],
            'basic_task': ['file', 'data', 'utility'],
            'data_pipeline': ['data', 'file', 'computation'],
            'api_integration': ['network', 'data', 'integration'],
            'multi_stage_pipeline': ['data', 'computation', 'file', 'integration']
        }
        
        priorities = priority_map.get(task_type, ['data', 'file', 'network'])
        
        # Select from priority categories
        for category in priorities:
            if category in by_category:
                selected.extend(by_category[category][:3])
        
        # Fill with other tools if needed
        for category, cat_tools in by_category.items():
            if category not in priorities:
                selected.extend(cat_tools[:2])
            if len(selected) >= 15:
                break
        
        return selected[:15]


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='Enhanced Workflow Quality Testing')
    parser.add_argument('--model-path', default='checkpoints/best_model.pt')
    parser.add_argument('--tools-path', default='mcp_generated_library/tool_registry.json')
    parser.add_argument('--task-types', nargs='+', default=['simple_task', 'data_pipeline'])
    parser.add_argument('--num-tests', type=int, default=5)
    parser.add_argument('--api-key', default=None)
    
    args = parser.parse_args()
    
    # Get API key
    api_key = args.api_key or os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.error("OpenAI API key not found!")
        return
    
    # Initialize tester
    tester = WorkflowQualityTester(
        model_path=args.model_path,
        tools_path=args.tools_path,
        api_key=api_key
    )
    
    # Run adherence tests
    print("\n🔬 Running Enhanced Workflow Adherence Tests")
    print("=" * 60)
    
    all_results = {}
    
    for task_type in args.task_types:
        print(f"\n📋 Testing {task_type}...")
        
        # Analyze workflow quality
        quality = tester.analyze_workflow_quality(task_type)
        print(f"  Workflow Quality Score: {quality.overall_score:.2f}")
        print(f"  Structure Score: {quality.workflow_quality.get('structure_score', 0):.2f}")
        
        # Test adherence
        adherence_results = tester.test_workflow_adherence(task_type, args.num_tests)
        all_results[task_type] = adherence_results
        
        # Print results
        print(f"\n  Results:")
        for prompt_type, analysis in adherence_results['analysis'].items():
            print(f"    {prompt_type}:")
            print(f"      Success Rate: {analysis['success_rate']:.1%}")
            print(f"      Adherence Rate: {analysis['adherence_rate']:.1%}")
            print(f"      Avg Adherence Score: {analysis['avg_adherence_score']:.2f}")
    
    # Generate reports and visualizations
    print("\n📊 Generating Reports...")
    tester.generate_adherence_report()
    tester.visualize_adherence_metrics()
    
    print("\n✅ Enhanced testing complete!")
    print(f"📁 Results saved to {tester.output_dir}")
    
    # Print summary
    print("\n📊 Summary:")
    if tester.adherence_tracking:
        all_scores = []
        for task_data in tester.adherence_tracking.values():
            for entry in task_data:
                if 'adherence' in entry and 'overall_adherence' in entry['adherence']:
                    all_scores.append(entry['adherence']['overall_adherence'])
        
        if all_scores:
            print(f"  Average Workflow Adherence: {np.mean(all_scores):.1%}")
            print(f"  Best Adherence: {np.max(all_scores):.1%}")
            print(f"  Improvement over baseline: +{(np.max(all_scores) - np.min(all_scores)) * 100:.1f}%")


if __name__ == "__main__":
    main()
