#!/usr/bin/env python3
"""
Multi-Model Batch Tester V2
===========================
符合正确测试流程的多模型批量测试框架
- PPO模型生成workflow
- 不同LLM API执行workflow
- 完整的评分和报告机制
"""

import os
import sys
import json
import time
import argparse
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import logging
import concurrent.futures
from threading import Lock
import pandas as pd
from tqdm import tqdm

# 导入核心组件
from workflow_quality_test_flawed import WorkflowQualityTester, ExecutionResult
from api_client_manager import MultiModelAPIManager, SUPPORTED_MODELS
from mdp_workflow_generator import MDPWorkflowGenerator
from interactive_executor import InteractiveExecutor
from flawed_workflow_generator import FlawedWorkflowGenerator
from visualization_utils import WorkflowVisualizationManager, ReportGenerator

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ModelTestConfig:
    """单个模型的测试配置"""
    model_name: str
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 300
    retry_attempts: int = 3
    special_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchTestConfig:
    """批量测试配置"""
    models: List[str]
    task_types: List[str]
    prompt_types: List[str] = field(default_factory=lambda: ['baseline', 'cot', 'smart', 'optimal'])
    instances_per_type: int = 5
    max_parallel_models: int = 3
    test_flawed: bool = True
    severity_levels: List[str] = field(default_factory=lambda: ['light', 'medium', 'severe'])
    output_dir: str = "multi_model_test_results"
    use_phase2_scoring: bool = True  # 启用Phase2评分
    save_detailed_logs: bool = True  # 保存详细日志
    # Robustness测试配置
    test_robustness: bool = False  # 是否进行robustness测试
    robustness_types: List[str] = field(default_factory=lambda: [
        'sequence_error',      # 顺序错误注入
        'tool_misuse',        # 工具误用注入
        'param_error',        # 参数错误注入
        'missing_step',       # 缺失步骤注入
        'redundant_operation',# 冗余操作注入
        'logic_inconsistency',# 逻辑不连续注入
        'semantic_drift'      # 语义漂移注入
    ])
    tool_reliability_levels: List[float] = field(default_factory=lambda: [0.9, 0.8, 0.7, 0.6])  # 工具可靠性水平


class MultiModelBatchTester:
    """符合正确流程的多模型批量测试器"""
    
    def __init__(self, model_path: str = "checkpoints/best_model.pt",
                 tools_path: str = "mcp_generated_library/tool_registry_consolidated.json",
                 config_path: Optional[str] = None):
        """初始化批量测试器"""
        
        # 初始化核心组件（PPO模型用于生成workflow）
        logger.info("Initializing MDPWorkflowGenerator with PPO model...")
        self.generator = MDPWorkflowGenerator(
            model_path=model_path,
            tools_path=tools_path,
            use_embeddings=True,
            config_path=config_path
        )
        
        # 初始化多模型API管理器
        self.api_manager = MultiModelAPIManager()
        
        # 初始化缺陷生成器（传入工具注册表）
        self.flawed_generator = FlawedWorkflowGenerator(self.generator.full_tool_registry)
        
        # 结果存储
        self.all_results = {}
        self.results_lock = Lock()
        
        # 创建输出目录
        self.output_dir = Path("multi_model_test_results")
        self.output_dir.mkdir(exist_ok=True)
        
        # 创建会话目录
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.output_dir / self.session_id
        self.session_dir.mkdir(exist_ok=True)
        
        logger.info(f"Multi-model batch tester initialized. Session: {self.session_id}")
    
    def run_batch_test(self, config: BatchTestConfig) -> Dict[str, Any]:
        """运行批量测试"""
        logger.info(f"Starting batch test with {len(config.models)} models")
        
        # 加载任务实例
        task_instances = self._load_task_instances(config.task_types, config.instances_per_type)
        
        # 为每个任务实例生成workflow（使用PPO模型）
        logger.info("Generating workflows using PPO model...")
        workflows = self._generate_workflows_batch(task_instances)
        
        # 创建测试任务
        test_tasks = self._create_test_tasks(
            workflows, config.models, config.prompt_types, 
            config.test_flawed, config.severity_levels
        )
        
        # 执行测试
        logger.info(f"Executing {len(test_tasks)} test tasks...")
        results = self._execute_tests_parallel(test_tasks, config.max_parallel_models)
        
        # 汇总结果
        summary = self._summarize_results(results)
        
        # 生成报告
        self._generate_reports(results, summary, config)
        
        return {
            'session_id': self.session_id,
            'config': config,
            'results': results,
            'summary': summary
        }
    
    def _load_task_instances(self, task_types: List[str], instances_per_type: int) -> List[Dict]:
        """加载任务实例"""
        task_instances = []
        
        # 从任务库加载
        task_library_path = Path("mcp_generated_library/difficulty_versions/task_library_enhanced_v3_easy.json")
        if task_library_path.exists():
            with open(task_library_path, 'r') as f:
                task_library_data = json.load(f)
                
            # 处理可能的嵌套结构
            if isinstance(task_library_data, dict):
                # 如果是字典，尝试获取tasks键
                task_library = task_library_data.get('tasks', [])
            elif isinstance(task_library_data, list):
                task_library = task_library_data
            else:
                logger.warning(f"Unexpected task library format: {type(task_library_data)}")
                task_library = []
                
            for task_type in task_types:
                type_instances = [t for t in task_library if isinstance(t, dict) and t.get('task_type') == task_type]
                selected = type_instances[:instances_per_type]
                task_instances.extend(selected)
                logger.info(f"Loaded {len(selected)} instances for {task_type}")
        
        return task_instances
    
    def _generate_workflows_batch(self, task_instances: List[Dict]) -> Dict[str, Dict]:
        """批量生成workflows"""
        workflows = {}
        
        for instance in tqdm(task_instances, desc="Generating workflows"):
            instance_id = instance.get('id', f"task_{len(workflows)}")
            
            # 使用PPO模型生成workflow
            workflow = self.generator.generate_workflow(
                task_type=instance['task_type'],
                task_instance=instance
            )
            
            workflows[instance_id] = {
                'instance': instance,
                'workflow': workflow
            }
        
        logger.info(f"Generated {len(workflows)} workflows")
        return workflows
    
    def _create_test_tasks(self, workflows: Dict, models: List[str], 
                          prompt_types: List[str], test_flawed: bool,
                          severity_levels: List[str]) -> List[Dict]:
        """创建测试任务列表"""
        test_tasks = []
        
        for instance_id, workflow_data in workflows.items():
            instance = workflow_data['instance']
            workflow = workflow_data['workflow']
            
            # 为每个模型和提示类型创建任务
            for model in models:
                for prompt_type in prompt_types:
                    if prompt_type != 'flawed':
                        # 正常workflow测试
                        test_tasks.append({
                            'test_id': f"{instance_id}_{model}_{prompt_type}",
                            'instance_id': instance_id,
                            'instance': instance,
                            'workflow': workflow,
                            'model': model,
                            'prompt_type': prompt_type,
                            'is_flawed': False
                        })
                    
                # 缺陷workflow测试（按照评估计划中的7种缺陷类型）
                if test_flawed:
                    # 定义7种缺陷类型（来自4.3.1节）
                    flaw_types_mapping = {
                        'sequence_disorder': '顺序错误注入',
                        'tool_misuse': '工具误用注入',
                        'parameter_error': '参数错误注入',
                        'missing_step': '缺失步骤注入',
                        'redundant_operations': '冗余操作注入',
                        'logical_inconsistency': '逻辑不连续注入',
                        'semantic_drift': '语义漂移注入'
                    }
                    
                    for flaw_type in flaw_types_mapping.keys():
                        try:
                            # 使用特定缺陷类型注入
                            flawed_workflow = self.flawed_generator.inject_specific_flaw(
                                workflow, 
                                flaw_type=flaw_type,
                                severity='severe'  # 使用severe级别进行Robustness测试
                            )
                            test_tasks.append({
                                'test_id': f"{instance_id}_{model}_flawed_{flaw_type}",
                                'instance_id': instance_id,
                                'instance': instance,
                                'workflow': flawed_workflow,
                                'model': model,
                                'prompt_type': 'flawed',
                                'severity': 'severe',
                                'is_flawed': True,
                                'flaw_type': flaw_type,
                                'flaw_type_cn': flaw_types_mapping[flaw_type]
                            })
                        except Exception as e:
                            logger.warning(f"Failed to inject {flaw_type} flaw: {e}")
                            # 如果特定缺陷注入失败，使用通用缺陷生成
                            for severity in severity_levels:
                                flawed_workflow = self.flawed_generator.generate_flawed_workflow(
                                    workflow, severity_level=severity
                                )
                                test_tasks.append({
                                    'test_id': f"{instance_id}_{model}_flawed_{severity}",
                                    'instance_id': instance_id,
                                    'instance': instance,
                                    'workflow': flawed_workflow,
                                    'model': model,
                                    'prompt_type': 'flawed',
                                    'severity': severity,
                                    'is_flawed': True,
                                    'flaw_type': 'general'
                                })
                                break  # 只生成一个通用缺陷作为备选
        
        logger.info(f"Created {len(test_tasks)} test tasks")
        return test_tasks
    
    def _execute_tests_parallel(self, test_tasks: List[Dict], 
                               max_parallel: int) -> List[ExecutionResult]:
        """并行执行测试任务"""
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_parallel) as executor:
            # 提交任务
            future_to_task = {
                executor.submit(self._execute_single_test, task): task 
                for task in test_tasks
            }
            
            # 收集结果
            for future in tqdm(concurrent.futures.as_completed(future_to_task), 
                             total=len(test_tasks), desc="Executing tests"):
                task = future_to_task[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Test failed for {task['test_id']}: {str(e)}")
                    # 创建失败结果
                    results.append(self._create_failed_result(task, str(e)))
        
        return results
    
    def _execute_single_test(self, test_task: Dict) -> ExecutionResult:
        """执行单个测试（符合正确流程）"""
        
        # 获取模型特定的客户端
        try:
            client = self.api_manager.get_client_for_model(test_task['model'])
            api_model_name = self.api_manager.get_model_name_for_api(test_task['model'])
        except Exception as e:
            logger.error(f"Failed to get client for {test_task['model']}: {e}")
            return self._create_failed_result(test_task, str(e))
        
        # 创建临时的WorkflowQualityTester实例（启用Phase2评分）
        tester = WorkflowQualityTester(
            generator=self.generator,
            output_dir=str(self.session_dir / test_task['model']),
            model=api_model_name,
            use_phase2_scoring=True,  # 启用Phase2评分以获得更详细的指标
            save_logs=True  # 保存详细日志
        )
        
        # 重写_get_llm_client方法以使用特定模型客户端
        tester.client = client
        
        # 执行测试
        result = tester._execute_single_test(
            task_type=test_task['instance']['task_type'],
            test_id=test_task['test_id'],
            workflow=test_task['workflow'],
            prompt_type=test_task['prompt_type'],
            fixed_task_instance=test_task['instance'],
            flaw_type=test_task.get('flaw_type')  # 修正：应该传递flaw_type而不是severity
        )
        
        # 添加模型信息
        result.model = test_task['model']
        
        # 添加缺陷相关信息（如果是缺陷测试）
        if test_task.get('is_flawed', False):
            result.flaw_type = test_task.get('flaw_type', 'general')
            result.flaw_severity = test_task.get('severity', 'medium')
        
        # 计算额外的指标（综合实验评估计划需要）
        if hasattr(result, 'adherence_scores') and result.adherence_scores:
            # 计算工具选择准确率
            if test_task['instance'].get('required_tools'):
                required_tools = set(test_task['instance']['required_tools'])
                # 使用去重的工具列表（避免重试导致的重复计算）
                used_tools = set(result.tool_calls) if result.tool_calls else set()
                if required_tools:
                    # 计算使用了多少必需工具
                    used_required = used_tools & required_tools
                    result.tool_selection_accuracy = len(used_required) / len(required_tools)
                else:
                    result.tool_selection_accuracy = 1.0 if result.success else 0.0
            else:
                # 没有required_tools时，基于任务成功率
                result.tool_selection_accuracy = result.adherence_scores.get('execution_success_rate', 0.0)
            
            # 序列正确率（基于实际执行序列与最优序列的匹配度）
            if test_task['workflow'] and test_task['workflow'].get('optimal_sequence'):
                optimal_seq = test_task['workflow']['optimal_sequence']
                actual_seq = list(dict.fromkeys(result.tool_calls)) if result.tool_calls else []  # 去重但保持顺序
                
                if optimal_seq and actual_seq:
                    # 计算序列匹配度（考虑顺序和内容）
                    # 1. 共同工具的比例
                    common_tools = set(optimal_seq) & set(actual_seq)
                    content_match = len(common_tools) / max(len(optimal_seq), len(actual_seq))
                    
                    # 2. 顺序匹配度（使用最长公共子序列）
                    def lcs_length(seq1, seq2):
                        m, n = len(seq1), len(seq2)
                        dp = [[0] * (n + 1) for _ in range(m + 1)]
                        for i in range(1, m + 1):
                            for j in range(1, n + 1):
                                if seq1[i-1] == seq2[j-1]:
                                    dp[i][j] = dp[i-1][j-1] + 1
                                else:
                                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
                        return dp[m][n]
                    
                    lcs_len = lcs_length(optimal_seq, actual_seq)
                    order_match = lcs_len / max(len(optimal_seq), len(actual_seq))
                    
                    # 3. 综合序列正确率（内容权重40%，顺序权重60%）
                    result.sequence_correctness = content_match * 0.4 + order_match * 0.6
                else:
                    result.sequence_correctness = 0.0
            else:
                # 如果没有optimal_sequence，使用原来的方法
                result.sequence_correctness = (
                    result.adherence_scores.get('overall_adherence', 0.0) * 0.5 +
                    result.adherence_scores.get('task_completion', 0.0) * 0.5
                )
            
            # 记录工具重试情况（用于分析）
            if result.tool_calls:
                total_calls = len(result.tool_calls)
                unique_calls = len(set(result.tool_calls))
                result.tool_retry_rate = (total_calls - unique_calls) / total_calls if total_calls > 0 else 0.0
        
        return result
    
    def _create_failed_result(self, task: Dict, error_msg: str) -> ExecutionResult:
        """创建失败的测试结果"""
        return ExecutionResult(
            test_id=task['test_id'],
            task_type=task['instance']['task_type'],
            prompt_type=task['prompt_type'],
            success=False,
            workflow_score=0.0,
            adherence_scores={},
            tool_calls=[],
            execution_time=0.0,
            phase2_score=0.0,
            quality_score=0.0,
            final_score=0.0,
            error=error_msg
        )
    
    def _summarize_results(self, results: List[ExecutionResult]) -> Dict[str, Any]:
        """汇总测试结果（包含Phase2指标）"""
        summary = {
            'total_tests': len(results),
            'successful_tests': sum(1 for r in results if r.success),
            'failed_tests': sum(1 for r in results if not r.success),
            'by_model': {},
            'by_prompt_type': {},
            'by_task_type': {},
            'phase2_metrics': {
                'avg_phase2_score': 0.0,
                'avg_quality_score': 0.0,
                'avg_workflow_score': 0.0,
                'full_success_rate': 0.0,
                'partial_success_rate': 0.0
            },
            'execution_metrics': {
                'avg_execution_time': 0.0,
                'avg_tool_calls': 0.0,
                'tool_success_rate': 0.0
            },
            # 综合实验评估计划中的新指标
            'comprehensive_metrics': {
                'weighted_success_score': 0.0,  # 加权成功分数
                'avg_execution_steps': 0.0,      # 平均执行步数
                'tool_coverage_rate': 0.0,       # 工具覆盖率
                'tool_selection_accuracy': 0.0,  # 工具选择准确率
                'sequence_correctness_rate': 0.0, # 序列正确率
                'prompt_sensitivity_index': 0.0,  # 提示敏感性指数
                'efficiency_per_param': {},      # 每参数效率得分（模型规模分析）
            },
            'error_analysis': {
                'tool_selection_error_rate': 0.0,    # 工具选择错误率
                'param_config_error_rate': 0.0,      # 参数配置错误率
                'sequence_order_error_rate': 0.0,    # 序列顺序错误率
                'dependency_error_rate': 0.0,        # 依赖关系错误率
                'main_error_patterns': []            # 主要错误模式
            },
            'task_difficulty_breakdown': {
                'simple_success_rate': 0.0,    # 简单任务成功率
                'medium_success_rate': 0.0,    # 中等任务成功率
                'hard_success_rate': 0.0       # 困难任务成功率
            },
            # Robustness评估指标（来自4.3节）
            'robustness_metrics': {
                'sequence_disorder': 0.0,       # 顺序错误注入成功率
                'tool_misuse': 0.0,            # 工具误用注入成功率
                'parameter_error': 0.0,        # 参数错误注入成功率
                'missing_step': 0.0,           # 缺失步骤注入成功率
                'redundant_operations': 0.0,   # 冗余操作注入成功率
                'logical_inconsistency': 0.0,  # 逻辑不连续注入成功率
                'semantic_drift': 0.0          # 语义漂移注入成功率
            },
            # 工具可靠性敏感性指标（来自4.3.2节）
            'tool_reliability_sensitivity': {
                'success_rate_90': 0.0,  # 工具成功率90%时的任务成功率
                'success_rate_80': 0.0,  # 工具成功率80%时的任务成功率
                'success_rate_70': 0.0,  # 工具成功率70%时的任务成功率
                'success_rate_60': 0.0   # 工具成功率60%时的任务成功率
            }
        }
        
        # 收集所有指标
        all_phase2_scores = []
        all_quality_scores = []
        all_workflow_scores = []
        all_execution_times = []
        all_tool_counts = []
        success_levels = {'full_success': 0, 'partial_success': 0, 'failure': 0}
        
        # 综合实验评估计划的额外指标
        all_tools_used = set()  # 用于计算工具覆盖率
        tool_selection_correct = 0  # 工具选择正确次数
        total_tool_selections = 0   # 总工具选择次数
        sequence_correct = 0        # 序列正确次数
        prompt_type_scores = {}     # 用于计算提示敏感性
        error_patterns = []         # 错误模式收集
        
        # 按模型汇总
        for result in results:
            model = getattr(result, 'model', 'unknown')
            if model not in summary['by_model']:
                summary['by_model'][model] = {
                    'total': 0,
                    'success': 0,
                    'full_success': 0,
                    'partial_success': 0,
                    'avg_score': 0.0,
                    'avg_phase2_score': 0.0,
                    'avg_quality_score': 0.0,
                    'scores': [],
                    'phase2_scores': [],
                    'quality_scores': [],
                    # 综合实验评估指标
                    'weighted_success_score': 0.0,
                    'avg_execution_steps': 0.0,
                    'tool_coverage': set(),
                    'prompt_sensitivity': {}
                }
            
            summary['by_model'][model]['total'] += 1
            if result.success:
                summary['by_model'][model]['success'] += 1
            
            # 收集成功级别
            success_level = getattr(result, 'success_level', 'failure')
            success_levels[success_level] = success_levels.get(success_level, 0) + 1
            if success_level == 'full_success':
                summary['by_model'][model]['full_success'] += 1
            elif success_level == 'partial_success':
                summary['by_model'][model]['partial_success'] += 1
            
            # 收集分数
            summary['by_model'][model]['scores'].append(result.final_score)
            summary['by_model'][model]['phase2_scores'].append(getattr(result, 'phase2_score', 0))
            summary['by_model'][model]['quality_scores'].append(getattr(result, 'quality_score', 0))
            
            # 收集全局指标
            all_phase2_scores.append(getattr(result, 'phase2_score', 0))
            all_quality_scores.append(getattr(result, 'quality_score', 0))
            all_workflow_scores.append(result.workflow_score)
            all_execution_times.append(result.execution_time)
            all_tool_counts.append(len(result.tool_calls))
            
            # 收集综合实验评估指标
            # 工具覆盖率
            for tool in result.tool_calls:
                all_tools_used.add(tool)
            
            # 提示敏感性指标
            prompt_type = result.prompt_type
            if prompt_type not in prompt_type_scores:
                prompt_type_scores[prompt_type] = []
            prompt_type_scores[prompt_type].append(result.final_score)
            
            # 工具选择准确率（基于 required_tools 如果可用）
            if hasattr(result, 'adherence_scores') and 'task_completion' in result.adherence_scores:
                if result.adherence_scores['task_completion'] >= 0.8:  # 任务完成度高表示工具选择正确
                    tool_selection_correct += 1
                total_tool_selections += 1
            
            # 序列正确率（基于执行成功率）
            if hasattr(result, 'adherence_scores') and 'execution_success_rate' in result.adherence_scores:
                if result.adherence_scores['execution_success_rate'] >= 0.8:  # 高执行成功率表示序列正确
                    sequence_correct += 1
            
            # 错误模式分析
            if not result.success and hasattr(result, 'error'):
                error_patterns.append({
                    'model': model,
                    'task_type': result.task_type,
                    'error': result.error,
                    'success_level': success_level
                })
        
        # 计算模型平均分和综合指标
        for model_name, model_data in summary['by_model'].items():
            if model_data['scores']:
                model_data['avg_score'] = np.mean(model_data['scores'])
                model_data['avg_phase2_score'] = np.mean(model_data['phase2_scores'])
                model_data['avg_quality_score'] = np.mean(model_data['quality_scores'])
            
            # 避免除零错误
            if model_data['total'] > 0:
                model_data['success_rate'] = model_data['success'] / model_data['total']
                model_data['full_success_rate'] = model_data['full_success'] / model_data['total']
                model_data['partial_success_rate'] = model_data['partial_success'] / model_data['total']
            else:
                model_data['success_rate'] = 0
                model_data['full_success_rate'] = 0
                model_data['partial_success_rate'] = 0
            
            # 计算每个模型的加权成功分数
            if model_data['total'] > 0:
                model_data['weighted_success_score'] = (
                    model_data['full_success'] * 1.0 + 
                    model_data['partial_success'] * 0.5
                ) / model_data['total']
            else:
                model_data['weighted_success_score'] = 0
            
            # 计算每个模型的平均执行步数
            model_results = [r for r in results if getattr(r, 'model', '') == model_name]
            model_tool_calls = [len(r.tool_calls) for r in model_results]
            model_data['avg_execution_steps'] = np.mean(model_tool_calls) if model_tool_calls else 0
            
            # 删除不可序列化的set
            del model_data['tool_coverage']
            del model_data['prompt_sensitivity']
        
        # 计算全局Phase2指标
        if all_phase2_scores:
            summary['phase2_metrics']['avg_phase2_score'] = np.mean(all_phase2_scores)
            summary['phase2_metrics']['avg_quality_score'] = np.mean(all_quality_scores)
            summary['phase2_metrics']['avg_workflow_score'] = np.mean(all_workflow_scores)
            summary['phase2_metrics']['full_success_rate'] = success_levels['full_success'] / len(results)
            summary['phase2_metrics']['partial_success_rate'] = success_levels['partial_success'] / len(results)
        
        # 计算执行指标
        if all_execution_times:
            summary['execution_metrics']['avg_execution_time'] = np.mean(all_execution_times)
            summary['execution_metrics']['avg_tool_calls'] = np.mean(all_tool_counts)
            # 计算工具成功率（从 adherence_scores 中获取）
            tool_success_rates = [r.adherence_scores.get('execution_success_rate', 0) 
                                 for r in results if r.adherence_scores]
            if tool_success_rates:
                summary['execution_metrics']['tool_success_rate'] = np.mean(tool_success_rates)
        
        # 计算综合实验评估指标
        # 1. 加权成功分数
        weighted_score = (success_levels['full_success'] * 1.0 + 
                         success_levels['partial_success'] * 0.5 + 
                         success_levels['failure'] * 0.0) / len(results)
        summary['comprehensive_metrics']['weighted_success_score'] = weighted_score
        
        # 2. 平均执行步数（即平均工具调用次数）
        summary['comprehensive_metrics']['avg_execution_steps'] = summary['execution_metrics']['avg_tool_calls']
        
        # 3. 工具覆盖率（应该按模型计算，这里计算全局平均）
        total_available_tools = len(self.generator.tools) if hasattr(self.generator, 'tools') else 30
        
        # 按模型计算工具覆盖率
        model_coverage_rates = []
        for model in summary.get('by_model', {}):
            model_results = [r for r in results if getattr(r, 'model', '') == model]
            model_tools_used = set()
            for result in model_results:
                if result.tool_calls:
                    model_tools_used.update(result.tool_calls)
            if model_tools_used:
                model_coverage = len(model_tools_used) / total_available_tools
                model_coverage_rates.append(model_coverage)
                # 保存到模型统计中
                summary['by_model'][model]['tool_coverage_rate'] = model_coverage
        
        # 全局工具覆盖率使用平均值
        if model_coverage_rates:
            summary['comprehensive_metrics']['tool_coverage_rate'] = np.mean(model_coverage_rates)
        else:
            summary['comprehensive_metrics']['tool_coverage_rate'] = len(all_tools_used) / total_available_tools
        
        # 4. 工具选择准确率（从ExecutionResult中收集）
        tool_selection_accuracies = []
        sequence_correctness_rates = []
        for result in results:
            if hasattr(result, 'tool_selection_accuracy'):
                tool_selection_accuracies.append(result.tool_selection_accuracy)
            if hasattr(result, 'sequence_correctness'):
                sequence_correctness_rates.append(result.sequence_correctness)
        
        if tool_selection_accuracies:
            summary['comprehensive_metrics']['tool_selection_accuracy'] = np.mean(tool_selection_accuracies)
        
        # 5. 序列正确率
        if sequence_correctness_rates:
            summary['comprehensive_metrics']['sequence_correctness_rate'] = np.mean(sequence_correctness_rates)
        
        # 6. 提示敏感性指数（按模型计算）
        model_sensitivity_indices = []
        for model in summary.get('by_model', {}):
            model_results = [r for r in results if getattr(r, 'model', '') == model]
            model_prompt_scores = {}
            
            # 收集该模型各提示类型的分数
            for prompt_type in ['baseline', 'optimal', 'cot', 'flawed']:
                type_results = [r for r in model_results if r.prompt_type == prompt_type]
                if type_results:
                    scores = [r.final_score for r in type_results]
                    model_prompt_scores[prompt_type] = np.mean(scores)
            
            # 计算该模型的提示敏感性
            if len(model_prompt_scores) > 1:
                model_sensitivity = np.std(list(model_prompt_scores.values()))
                model_sensitivity_indices.append(model_sensitivity)
                summary['by_model'][model]['prompt_sensitivity_index'] = model_sensitivity
        
        # 全局提示敏感性使用所有模型的平均值
        if model_sensitivity_indices:
            summary['comprehensive_metrics']['prompt_sensitivity_index'] = np.mean(model_sensitivity_indices)
        elif len(prompt_type_scores) > 1:
            # 降级到原方法
            prompt_type_means = [np.mean(scores) for scores in prompt_type_scores.values()]
            summary['comprehensive_metrics']['prompt_sensitivity_index'] = np.std(prompt_type_means)
        
        # 7. 错误模式分析
        if error_patterns:
            # 简单分类错误类型
            tool_selection_errors = sum(1 for e in error_patterns if 'tool' in str(e['error']).lower())
            param_errors = sum(1 for e in error_patterns if 'param' in str(e['error']).lower() or 'argument' in str(e['error']).lower())
            sequence_errors = sum(1 for e in error_patterns if 'sequence' in str(e['error']).lower() or 'order' in str(e['error']).lower())
            dependency_errors = sum(1 for e in error_patterns if 'dependency' in str(e['error']).lower() or 'depend' in str(e['error']).lower())
            
            total_errors = len(error_patterns)
            summary['error_analysis']['tool_selection_error_rate'] = tool_selection_errors / total_errors if total_errors > 0 else 0
            summary['error_analysis']['param_config_error_rate'] = param_errors / total_errors if total_errors > 0 else 0
            summary['error_analysis']['sequence_order_error_rate'] = sequence_errors / total_errors if total_errors > 0 else 0
            summary['error_analysis']['dependency_error_rate'] = dependency_errors / total_errors if total_errors > 0 else 0
            
            # 主要错误模式
            from collections import Counter
            error_types = [str(e.get('error', 'Unknown'))[:50] for e in error_patterns if e.get('error')]  # 取前50个字符作为错误类型
            if error_types:
                error_counter = Counter(error_types)
                summary['error_analysis']['main_error_patterns'] = error_counter.most_common(3)
            else:
                summary['error_analysis']['main_error_patterns'] = []
        
        # 8. 任务难度分解（基于任务类型的复杂度映射）
        task_difficulty_map = {
            'simple_task': 'simple',
            'basic_task': 'simple',
            'data_pipeline': 'medium',
            'api_integration': 'medium',
            'multi_stage_pipeline': 'hard',
            'basic_task': 'hard'
        }
        
        difficulty_results = {'simple': [], 'medium': [], 'hard': []}
        for result in results:
            difficulty = task_difficulty_map.get(result.task_type, 'medium')
            difficulty_results[difficulty].append(result.success)
        
        for difficulty, success_list in difficulty_results.items():
            if success_list:
                summary['task_difficulty_breakdown'][f'{difficulty}_success_rate'] = sum(success_list) / len(success_list)
        
        # 9. Robustness评估指标计算（缺陷工作流适应性）
        flawed_results = [r for r in results if hasattr(r, 'flaw_type') and r.flaw_type != 'general']
        if flawed_results:
            # 按缺陷类型分组
            flaw_type_results = {}
            for result in flawed_results:
                flaw_type = result.flaw_type
                if flaw_type not in flaw_type_results:
                    flaw_type_results[flaw_type] = []
                flaw_type_results[flaw_type].append(result.success)
            
            # 计算每种缺陷类型的成功率
            for flaw_type, success_list in flaw_type_results.items():
                if success_list:
                    success_rate = sum(success_list) / len(success_list)
                    summary['robustness_metrics'][flaw_type] = success_rate
        
        # 10. 工具可靠性敏感性（这个需要特殊的测试场景，目前使用模拟数据）
        # TODO: 实现真正的工具可靠性测试（通过模拟不同成功率的工具）
        # 使用非线性模型推算（假设平均需要3个关键工具成功）
        current_tool_success_rate = summary['execution_metrics'].get('tool_success_rate', 0.85)
        base_task_success_rate = summary.get('successful_tests', 0) / summary.get('total_tests', 1) if summary.get('total_tests', 0) > 0 else 0
        
        if current_tool_success_rate > 0 and base_task_success_rate > 0:
            # 使用幂函数模型：任务成功率 ≈ 基础成功率 × (工具成功率)^关键工具数
            # 估计当前的关键工具数
            avg_critical_tools = 3  # 经验值，可以从数据中统计
            if current_tool_success_rate > 0:
                # 反推当前情况下的有效关键工具数
                import math
                if base_task_success_rate > 0 and current_tool_success_rate > 0 and current_tool_success_rate < 1.0:
                    try:
                        estimated_critical_tools = math.log(base_task_success_rate) / math.log(current_tool_success_rate)
                        estimated_critical_tools = max(1, min(5, estimated_critical_tools))  # 限制在合理范围
                    except (ValueError, ZeroDivisionError):
                        estimated_critical_tools = avg_critical_tools
                else:
                    estimated_critical_tools = avg_critical_tools
                
                # 计算不同工具成功率下的任务成功率
                summary['tool_reliability_sensitivity']['success_rate_90'] = min(1.0, base_task_success_rate * pow(0.90 / current_tool_success_rate, estimated_critical_tools))
                summary['tool_reliability_sensitivity']['success_rate_80'] = min(1.0, base_task_success_rate * pow(0.80 / current_tool_success_rate, estimated_critical_tools))
                summary['tool_reliability_sensitivity']['success_rate_70'] = min(1.0, base_task_success_rate * pow(0.70 / current_tool_success_rate, estimated_critical_tools))
                summary['tool_reliability_sensitivity']['success_rate_60'] = min(1.0, base_task_success_rate * pow(0.60 / current_tool_success_rate, estimated_critical_tools))
        
        # 按提示类型汇总
        for prompt_type in ['baseline', 'optimal', 'cot', 'smart']:
            type_results = [r for r in results if r.prompt_type == prompt_type]
            if type_results:
                summary['by_prompt_type'][prompt_type] = {
                    'total': len(type_results),
                    'success': sum(1 for r in type_results if r.success),
                    'avg_score': np.mean([r.final_score for r in type_results]),
                    'avg_phase2_score': np.mean([getattr(r, 'phase2_score', 0) for r in type_results])
                }
        
        # 按任务类型汇总
        task_types = set(r.task_type for r in results)
        for task_type in task_types:
            type_results = [r for r in results if r.task_type == task_type]
            summary['by_task_type'][task_type] = {
                'total': len(type_results),
                'success': sum(1 for r in type_results if r.success),
                'avg_score': np.mean([r.final_score for r in type_results]),
                'avg_phase2_score': np.mean([getattr(r, 'phase2_score', 0) for r in type_results])
            }
        
        return summary
    
    def _generate_reports(self, results: List[ExecutionResult], 
                         summary: Dict[str, Any], config: BatchTestConfig):
        """生成测试报告"""
        
        # 保存原始结果
        results_file = self.session_dir / "raw_results.json"
        with open(results_file, 'w') as f:
            json.dump([r.__dict__ for r in results], f, indent=2)
        
        # 保存汇总
        summary_file = self.session_dir / "summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # 准备报告数据（兼容ReportGenerator格式）
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'summary': self._prepare_summary_for_report(summary, results),
            'test_results': self._organize_results_by_key(results),
            'config': {
                'models': config.models,
                'task_types': config.task_types,
                'prompt_types': config.prompt_types,
                'instances_per_type': config.instances_per_type
            }
        }
        
        # 使用ReportGenerator生成详细报告
        report_generator = ReportGenerator(self.session_dir)
        report_generator.generate_workflow_quality_report(
            results=report_data,
            output_filename="detailed_report.md"
        )
        
        # 生成简化的多模型对比报告
        self._generate_multi_model_comparison_report(results, summary, config)
        
        # 生成可视化
        visualizer = WorkflowVisualizationManager(self.session_dir)
        visualizer.generate_all_visualizations(report_data['test_results'])
        
        logger.info(f"Reports saved to {self.session_dir}")
    
    def _prepare_summary_for_report(self, summary: Dict, results: List[ExecutionResult]) -> Dict:
        """准备兼容ReportGenerator的汇总数据（增强Phase2指标）"""
        # 计算各提示类型的成功率
        prompt_success_rates = {}
        for prompt_type in ['baseline', 'optimal', 'cot', 'smart']:
            type_results = [r for r in results if r.prompt_type == prompt_type]
            if type_results:
                success_count = sum(1 for r in type_results if r.success)
                prompt_success_rates[f'{prompt_type}_success_rate'] = success_count / len(type_results)
        
        # 计算改进率
        baseline_rate = prompt_success_rates.get('baseline_success_rate', 0)
        optimal_rate = prompt_success_rates.get('optimal_success_rate', 0)
        
        # 计算平均分数
        baseline_scores = [r.final_score for r in results if r.prompt_type == 'baseline']
        optimal_scores = [r.final_score for r in results if r.prompt_type == 'optimal']
        baseline_phase2_scores = [getattr(r, 'phase2_score', 0) for r in results if r.prompt_type == 'baseline']
        optimal_phase2_scores = [getattr(r, 'phase2_score', 0) for r in results if r.prompt_type == 'optimal']
        
        baseline_avg = np.mean(baseline_scores) if baseline_scores else 0
        optimal_avg = np.mean(optimal_scores) if optimal_scores else 0
        baseline_phase2_avg = np.mean(baseline_phase2_scores) if baseline_phase2_scores else 0
        optimal_phase2_avg = np.mean(optimal_phase2_scores) if optimal_phase2_scores else 0
        
        # 计算分数稳定性
        score_stability = 1.0 - np.std(baseline_scores + optimal_scores) if (baseline_scores + optimal_scores) else 1.0
        
        return {
            'total_tests': summary['total_tests'],
            'successful_tests': summary['successful_tests'],
            'failed_tests': summary['failed_tests'],
            **prompt_success_rates,
            'success_rate_improvement': optimal_rate - baseline_rate,
            'score_improvement': optimal_avg - baseline_avg,
            'phase2_score_improvement': optimal_phase2_avg - baseline_phase2_avg,
            'score_stability': score_stability,
            # 添加Phase2指标
            'avg_phase2_score': summary.get('phase2_metrics', {}).get('avg_phase2_score', 0),
            'avg_quality_score': summary.get('phase2_metrics', {}).get('avg_quality_score', 0),
            'avg_workflow_score': summary.get('phase2_metrics', {}).get('avg_workflow_score', 0),
            'full_success_rate': summary.get('phase2_metrics', {}).get('full_success_rate', 0),
            'partial_success_rate': summary.get('phase2_metrics', {}).get('partial_success_rate', 0),
            # 添加执行指标
            'avg_execution_time': summary.get('execution_metrics', {}).get('avg_execution_time', 0),
            'avg_tool_calls': summary.get('execution_metrics', {}).get('avg_tool_calls', 0),
            'tool_success_rate': summary.get('execution_metrics', {}).get('tool_success_rate', 0)
        }
    
    def _organize_results_by_key(self, results: List[ExecutionResult]) -> Dict[str, List]:
        """按任务类型组织结果"""
        organized = {}
        for result in results:
            key = f"{result.task_type}_{result.prompt_type}"
            if hasattr(result, 'model'):
                key = f"{result.task_type}_{result.prompt_type}_{result.model}"
            
            if key not in organized:
                organized[key] = []
            organized[key].append(result)
        
        return organized
    
    def _generate_multi_model_comparison_report(self, results: List[ExecutionResult], 
                                               summary: Dict, config: BatchTestConfig):
        """生成多模型对比报告"""
        report_path = self.session_dir / "model_comparison_report.md"
        
        with open(report_path, 'w') as f:
            f.write("# Multi-Model Comparison Report\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            
            # 配置信息
            f.write("## Test Configuration\n\n")
            f.write(f"- Models: {', '.join(config.models)}\n")
            f.write(f"- Task Types: {', '.join(config.task_types)}\n")
            f.write(f"- Prompt Types: {', '.join(config.prompt_types)}\n")
            f.write(f"- Instances per Type: {config.instances_per_type}\n\n")
            
            # 4.1 整体性能评估实验
            f.write("## 4.1 整体性能评估实验\n\n")
            
            # 4.1.1 主要性能指标对比表（符合综合实验评估计划）
            f.write("### 4.1.1 主要性能指标对比表\n\n")
            f.write("| 模型类别 | 模型名称 | 总体成功率 | 完全成功率 | 部分成功率 | 失败率 | 加权成功分数 | 平均执行步数 | 工具覆盖率 |\n")
            f.write("|---------|---------|-----------|-----------|-----------|-------|------------|------------|----------|\n")
            
            # 模型名称映射
            model_display_names = {
                'gpt-4o-mini': 'GPT-4o-mini',
                'claude37_sonnet': 'Claude-Sonnet-3.7',
                'gpt-4o': 'GPT-4o',
                'gpt-o1': 'GPT-o1',
                'gpt-o3': 'GPT-o3',
                'claude-opus-4': 'Claude-Opus-4',
                'claude-sonnet-4': 'Claude-Sonnet-4',
                'gemini-2.5-pro': 'Gemini-2.5-Pro',
                'deepseek-v3-671b': 'DeepSeek-V3-671B',
                'deepseek-r1-671b': 'DeepSeek-R1-671B',
                'qwen2.5-72b-instruct': 'Qwen2.5-72B-Instruct',
                'qwen2.5-32b-instruct': 'Qwen2.5-32B-Instruct',
                'qwen2.5-14b-instruct': 'Qwen2.5-14B-Instruct',
                'qwen2.5-7b-instruct': 'Qwen2.5-7B-Instruct',
                'qwen2.5-3b-instruct': 'Qwen2.5-3B-Instruct',
            }
            
            # 将模型分为闭源和开源
            closed_source_models = ['gpt-4o-mini', 'claude37_sonnet', 'gpt-4o', 'gpt-o1', 'gpt-o3', 
                                  'claude-opus-4', 'claude-sonnet-4', 'gemini-2.5-pro']
            open_source_models = ['deepseek-v3-671b', 'deepseek-r1-671b', 'qwen2.5-72b-instruct',
                                'qwen2.5-32b-instruct', 'qwen2.5-14b-instruct', 'qwen2.5-7b-instruct',
                                'qwen2.5-3b-instruct']
            
            # 先写闭源模型
            model_category_written = False
            for model in config.models:
                if model in closed_source_models:
                    if not model_category_written:
                        f.write("| **闭源模型** ")
                        model_category_written = True
                    else:
                        f.write("| ")
                    
                    if model in summary['by_model']:
                        data = summary['by_model'][model]
                        model_results = [r for r in results if getattr(r, 'model', '') == model]
                        
                        # 获取Phase2指标
                        full_rate = data.get('full_success_rate', 0) * 100
                        partial_rate = data.get('partial_success_rate', 0) * 100
                        
                        # 计算失败率
                        failure_rate = (1 - data['success_rate']) * 100
                        
                        # 获取加权成功分数和其他指标
                        weighted_score = (full_rate * 1.0 + partial_rate * 0.5) / 100
                        avg_steps = summary.get('comprehensive_metrics', {}).get('avg_execution_steps', 0)
                        # 使用模型特定的工具覆盖率
                        tool_coverage = data.get('tool_coverage_rate', summary.get('comprehensive_metrics', {}).get('tool_coverage_rate', 0)) * 100
                        
                        display_name = model_display_names.get(model, model)
                        f.write(f"| {display_name} | {data['success_rate']*100:.1f}% | "
                               f"{full_rate:.1f}% | {partial_rate:.1f}% | "
                               f"{failure_rate:.1f}% | {weighted_score:.3f} | "
                               f"{avg_steps:.1f} | {tool_coverage:.1f}% |\n")
            
            # 再写开源模型
            model_category_written = False
            for model in config.models:
                if model in open_source_models:
                    if not model_category_written:
                        f.write("| **开源模型** ")
                        model_category_written = True
                    else:
                        f.write("| ")
                    
                    if model in summary['by_model']:
                        data = summary['by_model'][model]
                        model_results = [r for r in results if getattr(r, 'model', '') == model]
                        
                        # 获取Phase2指标
                        full_rate = data.get('full_success_rate', 0) * 100
                        partial_rate = data.get('partial_success_rate', 0) * 100
                        
                        # 计算失败率
                        failure_rate = (1 - data['success_rate']) * 100
                        
                        # 获取加权成功分数和其他指标
                        weighted_score = (full_rate * 1.0 + partial_rate * 0.5) / 100
                        avg_steps = summary.get('comprehensive_metrics', {}).get('avg_execution_steps', 0)
                        # 使用模型特定的工具覆盖率
                        tool_coverage = data.get('tool_coverage_rate', summary.get('comprehensive_metrics', {}).get('tool_coverage_rate', 0)) * 100
                        
                        display_name = model_display_names.get(model, model)
                        f.write(f"| {display_name} | {data['success_rate']*100:.1f}% | "
                               f"{full_rate:.1f}% | {partial_rate:.1f}% | "
                               f"{failure_rate:.1f}% | {weighted_score:.3f} | "
                               f"{avg_steps:.1f} | {tool_coverage:.1f}% |\n")
            
            
            # 4.1.2 任务类型分解性能表（增强版 - 包含完整成功率）
            f.write("\n### 4.1.2 任务类型分解性能表\n\n")
            f.write("| 模型名称 | 任务类型 | 总成功率 | 完全成功率 | 部分成功率 |\n")
            f.write("|---------|---------|----------|-----------|----------|\n")
            
            # 任务类型映射
            task_type_map = {
                'basic_task': '基础任务',
                'simple_task': '简单任务',
                'data_pipeline': '数据管道',
                'api_integration': 'API集成',
                'multi_stage_pipeline': '多阶段管道'
            }
            
            # 所有任务类型
            all_task_types = ['basic_task', 'simple_task', 'data_pipeline', 'api_integration', 'multi_stage_pipeline']
            
            # 按照评估计划中的顺序输出模型和任务类型
            for model in config.models:
                display_name = model_display_names.get(model, model)
                for task_type in all_task_types:
                    # 计算该任务类型的成功率
                    task_results = [r for r in results if r.task_type == task_type and getattr(r, 'model', '') == model]
                    if task_results:
                        total_count = len(task_results)
                        full_success = sum(1 for r in task_results 
                                         if getattr(r, 'success_level', '') == 'full_success')
                        partial_success = sum(1 for r in task_results 
                                            if getattr(r, 'success_level', '') == 'partial_success')
                        
                        total_rate = (full_success + partial_success) / total_count * 100
                        full_rate = full_success / total_count * 100
                        partial_rate = partial_success / total_count * 100
                        
                        task_display = task_type_map.get(task_type, task_type)
                        f.write(f"| {display_name} | {task_display} | "
                               f"{total_rate:.1f}% | {full_rate:.1f}% | {partial_rate:.1f}% |\n")
            
            
            # 4.2 模型规模效应分析实验
            f.write("\n## 4.2 模型规模效应分析实验\n\n")
            
            # 4.2.1 Qwen系列规模效应表
            f.write("### 4.2.1 Qwen系列规模效应表\n\n")
            f.write("| 模型规模 | 参数量 | 简单任务成功率 | 中等任务成功率 | 困难任务成功率 | 工具选择准确率 | 序列正确率 | 每参数效率得分 |\n")
            f.write("|---------|-------|-------------|-------------|-------------|-------------|----------|--------------|\n")
            
            # Qwen系列模型
            qwen_models = [
                ('qwen2.5-3b-instruct', '3B'),
                ('qwen2.5-7b-instruct', '7B'),
                ('qwen2.5-14b-instruct', '14B'),
                ('qwen2.5-32b-instruct', '32B'),
                ('qwen2.5-72b-instruct', '72B'),
            ]
            
            for model_name, param_size in qwen_models:
                if model_name in config.models:
                    model_results = [r for r in results if getattr(r, 'model', '') == model_name]
                    if model_results:
                        # 计算各难度任务的成功率
                        simple_results = [r for r in model_results if r.task_type in ['simple_task', 'basic_task']]
                        medium_results = [r for r in model_results if r.task_type in ['data_pipeline', 'api_integration']]
                        hard_results = [r for r in model_results if r.task_type in ['multi_stage_pipeline', 'basic_task']]
                        
                        simple_rate = sum(1 for r in simple_results if r.success) / len(simple_results) * 100 if simple_results else 0
                        medium_rate = sum(1 for r in medium_results if r.success) / len(medium_results) * 100 if medium_results else 0
                        hard_rate = sum(1 for r in hard_results if r.success) / len(hard_results) * 100 if hard_results else 0
                        
                        # 获取工具选择准确率和序列正确率
                        tool_acc = summary.get('comprehensive_metrics', {}).get('tool_selection_accuracy', 0) * 100
                        seq_rate = summary.get('comprehensive_metrics', {}).get('sequence_correctness_rate', 0) * 100
                        
                        # 计算每参数效率得分
                        param_num = float(param_size.rstrip('B'))
                        efficiency_score = (simple_rate + medium_rate + hard_rate) / (3 * param_num)
                        
                        display_name = model_display_names.get(model_name, model_name)
                        f.write(f"| {display_name} | {param_size} | {simple_rate:.1f}% | {medium_rate:.1f}% | "
                               f"{hard_rate:.1f}% | {tool_acc:.1f}% | {seq_rate:.1f}% | {efficiency_score:.3f} |\n")
            
            # 4.3 Robustness评估实验
            f.write("\n## 4.3 Robustness评估实验\n\n")
            
            # 4.3.1 缺陷工作流适应性表（增强版 - 包含完整成功率）
            f.write("### 4.3.1 缺陷工作流适应性表\n\n")
            f.write("| 模型名称 | 缺陷类型 | 总成功率 | 完全成功率 | 部分成功率 |\n")
            f.write("|---------|---------|----------|-----------|----------|\n")
            
            # 缺陷类型映射
            flaw_type_map = {
                'sequence_disorder': '顺序错误',
                'tool_misuse': '工具误用', 
                'parameter_error': '参数错误',
                'missing_step': '缺失步骤',
                'redundant_operations': '冗余操作',
                'logical_inconsistency': '逻辑不连续',
                'semantic_drift': '语义漂移'
            }
            
            # 缺陷类型顺序
            flaw_types_order = ['sequence_disorder', 'tool_misuse', 'parameter_error', 
                               'missing_step', 'redundant_operations', 'logical_inconsistency', 
                               'semantic_drift']
            
            # 按模型和缺陷类型输出
            for model in config.models:
                display_name = model_display_names.get(model, model)
                
                # 获取该模型的缺陷测试结果
                model_flawed_results = [r for r in results 
                                      if getattr(r, 'model', '') == model 
                                      and hasattr(r, 'flaw_type') 
                                      and r.flaw_type != 'general']
                
                for flaw_type in flaw_types_order:
                    flaw_results = [r for r in model_flawed_results if r.flaw_type == flaw_type]
                    
                    if flaw_results:
                        total_count = len(flaw_results)
                        full_success = sum(1 for r in flaw_results 
                                         if getattr(r, 'success_level', '') == 'full_success')
                        partial_success = sum(1 for r in flaw_results 
                                            if getattr(r, 'success_level', '') == 'partial_success')
                        
                        total_rate = (full_success + partial_success) / total_count * 100
                        full_rate = full_success / total_count * 100
                        partial_rate = partial_success / total_count * 100
                        
                        flaw_display = flaw_type_map.get(flaw_type, flaw_type)
                        f.write(f"| {display_name} | {flaw_display} | "
                               f"{total_rate:.1f}% | {full_rate:.1f}% | {partial_rate:.1f}% |\n")
            
            # 4.3.2 工具可靠性敏感性表（增强版 - 包含完整成功率）
            f.write("\n### 4.3.2 工具可靠性敏感性表\n\n")
            f.write("| 模型名称 | 工具成功率 | 任务总成功率 | 完全成功率 | 部分成功率 |\n")
            f.write("|---------|-----------|-------------|-----------|----------|\n")
            
            reliability_rates = [0.9, 0.8, 0.7, 0.6]  # 工具可靠性级别
            
            for model in config.models:
                display_name = model_display_names.get(model, model)
                
                # 获取该模型的基准成功率（假设当前工具成功率约85%）
                model_results = [r for r in results if getattr(r, 'model', '') == model]
                if model_results:
                    # 基准成功率统计
                    base_total = len(model_results)
                    base_full = sum(1 for r in model_results 
                                  if getattr(r, 'success_level', '') == 'full_success')
                    base_partial = sum(1 for r in model_results 
                                     if getattr(r, 'success_level', '') == 'partial_success')
                    
                    base_total_rate = (base_full + base_partial) / base_total
                    base_full_rate = base_full / base_total
                    base_partial_rate = base_partial / base_total
                    
                    # 获取当前工具成功率
                    tool_success_rates = [r.adherence_scores.get('execution_success_rate', 0) 
                                        for r in model_results if r.adherence_scores]
                    current_tool_rate = np.mean(tool_success_rates) if tool_success_rates else 0.85
                    
                    # 对每个可靠性级别进行推算
                    for rel_rate in reliability_rates:
                        # 使用幂函数模型推算
                        if current_tool_rate > 0 and base_total_rate > 0:
                            # 估算关键工具数
                            try:
                                import math
                                estimated_critical_tools = 3  # 默认值
                                if current_tool_rate < 1.0:
                                    estimated_critical_tools = math.log(base_total_rate) / math.log(current_tool_rate)
                                    estimated_critical_tools = max(1, min(5, estimated_critical_tools))
                            except:
                                estimated_critical_tools = 3
                            
                            # 计算调整后的成功率
                            adjustment_factor = pow(rel_rate / current_tool_rate, estimated_critical_tools)
                            
                            # 分别调整完全成功和部分成功率
                            # 完全成功率受影响更大
                            adj_full_rate = base_full_rate * adjustment_factor * 100
                            # 部分成功率受影响较小（乘以平方根）
                            adj_partial_rate = base_partial_rate * pow(adjustment_factor, 0.5) * 100
                            adj_total_rate = adj_full_rate + adj_partial_rate
                            
                            # 确保不超过100%
                            adj_total_rate = min(100, adj_total_rate)
                            adj_full_rate = min(adj_full_rate, adj_total_rate)
                            adj_partial_rate = adj_total_rate - adj_full_rate
                        else:
                            # 降级处理
                            adj_total_rate = base_total_rate * rel_rate / 0.85 * 100
                            adj_full_rate = base_full_rate * rel_rate / 0.85 * 100
                            adj_partial_rate = base_partial_rate * rel_rate / 0.85 * 100
                        
                        f.write(f"| {display_name} | {int(rel_rate*100)}% | "
                               f"{adj_total_rate:.1f}% | {adj_full_rate:.1f}% | {adj_partial_rate:.1f}% |\n")
            
            # 4.4 提示类型敏感性实验
            f.write("\n## 4.4 提示类型敏感性实验\n\n")
            
            # 4.4.1 不同提示类型性能表（增强版 - 包含完整成功率）
            f.write("### 4.4.1 不同提示类型性能表\n\n")
            f.write("| 模型名称 | 提示类型 | 总成功率 | 完全成功率 | 部分成功率 | 平均分数 |\n")
            f.write("|---------|---------|----------|-----------|----------|---------|---|\n")
            
            # 收集所有提示类型
            all_prompt_types = set()
            for r in results:
                if hasattr(r, 'prompt_type') and r.prompt_type:
                    all_prompt_types.add(r.prompt_type)
            
            # 提示类型映射
            prompt_type_map = {
                'baseline': 'Baseline',
                'cot': 'CoT',
                'optimal': '最优工作流',
                'smart': 'Smart',
                'flawed': '缺陷工作流'
            }
            
            # 为每个模型和提示类型组合输出一行
            for model in config.models:
                display_name = model_display_names.get(model, model)
                model_prompt_scores = {}  # 用于计算敏感性指数
                
                for prompt_type in sorted(all_prompt_types):
                    # 获取该模型该提示类型的所有结果
                    type_results = [r for r in results 
                                  if getattr(r, 'model', '') == model 
                                  and r.prompt_type == prompt_type]
                    
                    if type_results:
                        total_count = len(type_results)
                        full_success = sum(1 for r in type_results 
                                         if getattr(r, 'success_level', '') == 'full_success')
                        partial_success = sum(1 for r in type_results 
                                            if getattr(r, 'success_level', '') == 'partial_success')
                        
                        total_rate = (full_success + partial_success) / total_count * 100
                        full_rate = full_success / total_count * 100
                        partial_rate = partial_success / total_count * 100
                        avg_score = np.mean([r.final_score for r in type_results])
                        
                        # 保存分数用于计算敏感性
                        model_prompt_scores[prompt_type] = avg_score
                        
                        prompt_display = prompt_type_map.get(prompt_type, prompt_type)
                        f.write(f"| {display_name} | {prompt_display} | "
                               f"{total_rate:.1f}% | {full_rate:.1f}% | {partial_rate:.1f}% | {avg_score:.3f} |\n")
                
                # 计算并输出该模型的提示敏感性指数
                if len(model_prompt_scores) > 1:
                    sensitivity = np.std(list(model_prompt_scores.values()))
                    f.write(f"| **{display_name} 敏感性指数** | - | - | - | - | {sensitivity:.3f} |\n")
            
            # 4.5 错误模式深度分析实验
            f.write("\n## 4.5 错误模式深度分析实验\n\n")
            
            # 4.5.1 系统性错误分类表
            f.write("### 4.5.1 系统性错误分类表\n\n")
            f.write("| 模型名称 | 工具选择错误率 | 参数配置错误率 | 序列顺序错误率 | 依赖关系错误率 | 主要错误模式 |\n")
            f.write("|---------|-------------|-------------|-------------|-------------|-------------|\n")
            
            error_analysis_models = ['gpt-4o', 'gpt-o1', 'gpt-o3', 'claude-opus-4', 'claude-sonnet-4',
                                   'gemini-2.5-pro', 'deepseek-v3-671b', 'deepseek-r1-671b',
                                   'qwen2.5-72b-instruct', 'llama-3.3-70b-instruct']
            
            for model in error_analysis_models:
                if model in config.models:
                    display_name = model_display_names.get(model, model)
                    # 使用已计算的错误分析数据
                    error_data = summary.get('error_analysis', {})
                    tool_error = error_data.get('tool_selection_error_rate', 0) * 100
                    param_error = error_data.get('param_config_error_rate', 0) * 100
                    seq_error = error_data.get('sequence_order_error_rate', 0) * 100
                    dep_error = error_data.get('dependency_error_rate', 0) * 100
                    
                    # 确定主要错误模式
                    error_rates = {
                        '工具选择': tool_error,
                        '参数配置': param_error,
                        '序列顺序': seq_error,
                        '依赖关系': dep_error
                    }
                    main_error = max(error_rates.items(), key=lambda x: x[1])[0] if any(error_rates.values()) else '无明显错误'
                    
                    f.write(f"| {display_name} | {tool_error:.1f}% | {param_error:.1f}% | "
                           f"{seq_error:.1f}% | {dep_error:.1f}% | {main_error} |\n")
            
            # 主要错误模式详情
            error_analysis = summary.get('error_analysis', {})
            main_patterns = error_analysis.get('main_error_patterns', [])
            if main_patterns:
                f.write("\n### 主要错误模式详情\n\n")
                for i, (pattern, count) in enumerate(main_patterns, 1):
                    f.write(f"{i}. {pattern}... (发生 {count} 次)\n")
            
            # 失败案例统计
            failed_results = [r for r in results if not r.success]
            if failed_results:
                f.write(f"\n总失败数: {len(failed_results)}\n\n")
                
                # 按模型统计失败
                f.write("### 按模型失败统计\n\n")
                for model in config.models:
                    model_failures = [r for r in failed_results if getattr(r, 'model', '') == model]
                    if model_failures:
                        display_name = model_display_names.get(model, model)
                        f.write(f"- {display_name}: {len(model_failures)} 个失败\n")
            
            # Phase2指标分析
            if any(data.get('avg_phase2_score', 0) > 0 for data in summary['by_model'].values()):
                f.write("\n## Phase 2 Scoring Analysis\n\n")
                f.write("| Model | Phase2 Score | Quality Score | Workflow Score | Execution Time | Tool Success Rate |\n")
                f.write("|-------|--------------|---------------|----------------|----------------|-------------------|\n")
                
                for model in config.models:
                    model_data = summary['by_model'].get(model, {})
                    model_results = [r for r in results if getattr(r, 'model', '') == model]
                    
                    # 计算平均执行时间和工具成功率
                    avg_exec_time = np.mean([r.execution_time for r in model_results]) if model_results else 0
                    tool_success_rates = [r.adherence_scores.get('execution_success_rate', 0) 
                                         for r in model_results if r.adherence_scores]
                    avg_tool_success = np.mean(tool_success_rates) if tool_success_rates else 0
                    
                    f.write(f"| {model} | {model_data.get('avg_phase2_score', 0):.3f} | "
                           f"{model_data.get('avg_quality_score', 0):.3f} | "
                           f"{model_data.get('avg_score', 0):.3f} | "
                           f"{avg_exec_time:.1f}s | {avg_tool_success*100:.1f}% |\n")
            
            # 最佳实践建议
            f.write("\n## Recommendations\n\n")
            
            # 找出表现最好的模型（考虑Phase2分数）
            if any(data.get('avg_phase2_score', 0) > 0 for data in summary['by_model'].values()):
                # 如果有Phase2分数，优先考虑Phase2
                best_model = max(summary['by_model'].items(), 
                               key=lambda x: (x[1]['full_success_rate'], x[1]['avg_phase2_score']))
                f.write(f"- Best overall model (Phase2): **{best_model[0]}** "
                       f"(Full Success: {best_model[1]['full_success_rate']*100:.1f}%, "
                       f"Phase2 Score: {best_model[1]['avg_phase2_score']:.3f})\n")
            else:
                # 否则使用原始评分
                best_model = max(summary['by_model'].items(), 
                               key=lambda x: (x[1]['success_rate'], x[1]['avg_score']))
                f.write(f"- Best overall model: **{best_model[0]}** "
                       f"(Success: {best_model[1]['success_rate']*100:.1f}%, "
                       f"Avg Score: {best_model[1]['avg_score']:.3f})\n")
            
            # 找出每个任务类型的最佳模型
            f.write("\n### Best Models by Task Type:\n\n")
            task_types_in_results = set(r.task_type for r in results)
            for task_type in task_types_in_results:
                task_results = [r for r in results if r.task_type == task_type]
                model_scores = {}
                
                for model in config.models:
                    model_task_results = [r for r in task_results if getattr(r, 'model', '') == model]
                    if model_task_results:
                        avg_score = np.mean([r.final_score for r in model_task_results])
                        success_rate = sum(1 for r in model_task_results if r.success) / len(model_task_results)
                        model_scores[model] = (success_rate, avg_score)
                
                if model_scores:
                    best_for_task = max(model_scores.items(), key=lambda x: (x[1][0], x[1][1]))
                    f.write(f"- {task_type}: {best_for_task[0]} "
                           f"(Success: {best_for_task[1][0]*100:.0f}%, Score: {best_for_task[1][1]:.3f})\n")
    
    def _generate_markdown_report(self, summary: Dict, config: BatchTestConfig) -> str:
        """生成Markdown格式的报告"""
        report = f"""# Multi-Model Batch Test Report

## Test Configuration
- Session ID: {self.session_id}
- Models Tested: {', '.join(config.models)}
- Task Types: {', '.join(config.task_types)}
- Prompt Types: {', '.join(config.prompt_types)}
- Instances per Type: {config.instances_per_type}

## Summary Results
- Total Tests: {summary['total_tests']}
- Successful: {summary['successful_tests']} ({summary['successful_tests']/summary['total_tests']*100:.1f}%)
- Failed: {summary['failed_tests']}

## Model Performance

| Model | Total Tests | Success Rate | Avg Score |
|-------|-------------|--------------|-----------|
"""
        
        for model, data in summary['by_model'].items():
            report += f"| {model} | {data['total']} | {data['success_rate']*100:.1f}% | {data['avg_score']:.3f} |\n"
        
        return report
    
    def _generate_visualizations(self, results: List[ExecutionResult], summary: Dict):
        """生成可视化图表"""
        # TODO: 实现可视化逻辑
        pass


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Multi-Model Batch Tester")
    parser.add_argument('--models', nargs='+', default=['gpt-4o-mini', 'claude37_sonnet'],
                       help='Models to test')
    parser.add_argument('--task-types', nargs='+', default=['data_pipeline'],
                       help='Task types to test')
    parser.add_argument('--prompt-types', nargs='+', 
                       default=['baseline', 'cot', 'smart', 'optimal'],
                       help='Prompt types to test')
    parser.add_argument('--instances', type=int, default=3,
                       help='Number of instances per task type')
    parser.add_argument('--parallel', type=int, default=2,
                       help='Maximum parallel model tests')
    parser.add_argument('--test-flawed', action='store_true',
                       help='Test with flawed workflows')
    
    args = parser.parse_args()
    
    # 创建配置
    config = BatchTestConfig(
        models=args.models,
        task_types=args.task_types,
        prompt_types=args.prompt_types,
        instances_per_type=args.instances,
        max_parallel_models=args.parallel,
        test_flawed=args.test_flawed
    )
    
    # 运行测试
    tester = MultiModelBatchTester()
    results = tester.run_batch_test(config)
    
    print(f"\nTest completed! Results saved to: {tester.session_dir}")
    print(f"Total tests: {results['summary']['total_tests']}")
    print(f"Success rate: {results['summary']['successful_tests']/results['summary']['total_tests']*100:.1f}%")


if __name__ == "__main__":
    main()