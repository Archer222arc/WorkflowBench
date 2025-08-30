#!/usr/bin/env python3
"""
Phase 2 Improvement: Simplified and Stable Scoring Mechanism
============================================================
将四个评分维度简化为两个正交维度：任务完成度和执行质量
"""

from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class SimplifiedScoringConfig:
    """简化的评分配置 - 只有两个正交维度"""
    # 主要维度权重
    task_achievement_weight: float = 0.7  # 任务完成度（结果导向）
    execution_quality_weight: float = 0.3  # 执行质量（过程导向）
    
    # 任务完成度子因素
    required_tools_weight: float = 0.6   # 必需工具使用率
    output_generated_weight: float = 0.4  # 输出生成情况
    
    # 执行质量子因素
    workflow_adherence_weight: float = 0.5  # 工作流遵循度
    efficiency_weight: float = 0.3          # 执行效率
    error_handling_weight: float = 0.2      # 错误处理能力


class StableScorer:
    """稳定的评分器 - 实现Phase 2改进"""
    
    def __init__(self, config: SimplifiedScoringConfig = None):
        self.config = config or SimplifiedScoringConfig()
        
    def calculate_stable_score(self, 
                             execution_result: Dict,
                             evaluation_context: Dict) -> Tuple[float, Dict]:
        """
        计算稳定的综合评分
        
        Args:
            execution_result: 执行结果，包含tool_calls等信息
            evaluation_context: 评估上下文，包含required_tools、workflow等
            
        Returns:
            (final_score, score_breakdown) - 最终分数和详细分解
        """
        # 1. 计算任务完成度 (0-1)
        task_achievement, ta_details = self._calculate_task_achievement(
            execution_result, evaluation_context
        )
        
        # 2. 计算执行质量 (0-1)
        execution_quality, eq_details = self._calculate_execution_quality(
            execution_result, evaluation_context
        )
        
        # 3. 使用几何平均数组合，避免极端值（添加安全检查）
        # 这比算术平均更稳定，因为它惩罚任何一个维度的低分
        try:
            # 确保输入值在有效范围内
            task_achievement = max(0.0, min(1.0, task_achievement or 0.0))
            execution_quality = max(0.0, min(1.0, execution_quality or 0.0))
            
            # 防止权重和为零
            weight_sum = self.config.task_achievement_weight + self.config.execution_quality_weight
            if weight_sum <= 0:
                weight_sum = 1.0
                
            final_score = np.power(
                np.power(task_achievement, self.config.task_achievement_weight) * 
                np.power(execution_quality, self.config.execution_quality_weight),
                1.0 / weight_sum
            )
            
            # 检查结果是否有效
            if not np.isfinite(final_score):
                logger.warning(f"无效的final_score: {final_score}, 使用默认值0.0")
                final_score = 0.0
            else:
                final_score = float(final_score)  # 确保返回Python float而不是numpy类型
                
        except Exception as e:
            logger.error(f"计算final_score时出错: {e}, 使用默认值0.0")
            final_score = 0.0
        
        # 4. 构建详细的分数分解
        score_breakdown = {
            'final_score': final_score,
            'task_achievement': task_achievement,
            'execution_quality': execution_quality,
            'task_achievement_details': ta_details,
            'execution_quality_details': eq_details,
            'scoring_method': 'geometric_mean',
            'config': {
                'task_achievement_weight': self.config.task_achievement_weight,
                'execution_quality_weight': self.config.execution_quality_weight
            }
        }
        
        return final_score, score_breakdown
    
    def _calculate_task_achievement(self, 
                                  execution_result: Dict,
                                  evaluation_context: Dict) -> Tuple[float, Dict]:
        """计算任务完成度分数"""
        tool_calls = execution_result.get('tool_calls', [])
        required_tools = set(evaluation_context.get('required_tools', []))
        used_tools = set(tool_calls)
        
        # 1. 必需工具使用率（使用Jaccard相似度）
        if required_tools:
            # Jaccard相似度：交集/并集，更稳定
            tool_score = len(required_tools & used_tools) / len(required_tools | used_tools)
        else:
            # 如果没有明确的必需工具，检查是否至少使用了一些工具
            tool_score = min(1.0, len(used_tools) / 3)  # 假设平均需要3个工具
        
        # 2. 输出生成检查
        output_indicators = ['output', 'export', 'write', 'save', 'create', 'generate', 'post']
        has_output = any(
            any(indicator in tool.lower() for indicator in output_indicators)
            for tool in tool_calls
        )
        output_score = 1.0 if has_output else 0.0
        
        # 3. 计算综合任务完成度
        task_achievement = (
            self.config.required_tools_weight * tool_score +
            self.config.output_generated_weight * output_score
        )
        
        details = {
            'tool_score': tool_score,
            'output_score': output_score,
            'required_tools': list(required_tools),
            'used_tools': list(used_tools),
            'matched_tools': list(required_tools & used_tools),
            'has_output': has_output
        }
        
        return task_achievement, details
    
    def _calculate_execution_quality(self,
                                   execution_result: Dict,
                                   evaluation_context: Dict) -> Tuple[float, Dict]:
        """计算执行质量分数"""
        tool_calls = execution_result.get('tool_calls', [])
        workflow = evaluation_context.get('workflow', {})
        
        # 1. 工作流遵循度
        if workflow and 'adherence_scores' in execution_result:
            # 如果有adherence scores，直接使用
            adherence_score = execution_result['adherence_scores'].get('overall_adherence', 0.5)
        elif workflow and 'optimal_sequence' in workflow:
            # 否则计算简单的序列匹配度
            optimal_seq = workflow['optimal_sequence']
            adherence_score = self._calculate_sequence_similarity(tool_calls, optimal_seq)
        else:
            # 没有工作流信息，使用默认值
            adherence_score = 0.5
        
        # 2. 执行效率
        if tool_calls:
            unique_tools = len(set(tool_calls))
            total_calls = len(tool_calls)
            # 效率 = unique/total，越接近1越好（避免重复）
            efficiency_score = unique_tools / total_calls
            
            # 同时考虑步数效率（太多或太少都不好）
            optimal_steps = evaluation_context.get('expected_tool_count', 4)
            step_efficiency = 1.0 - min(1.0, abs(total_calls - optimal_steps) / optimal_steps * 0.5)
            efficiency_score = (efficiency_score + step_efficiency) / 2
        else:
            efficiency_score = 0.0
        
        # 3. 错误处理能力（基于执行结果中的错误信息）
        error_score = 1.0  # 默认没有错误
        if 'error_message' in execution_result and execution_result['error_message']:
            error_score = 0.3  # 有错误但仍完成了部分任务
        if execution_result.get('success', False):
            error_score = min(1.0, error_score + 0.5)  # 成功完成加分
        
        # 4. 计算综合执行质量
        execution_quality = (
            self.config.workflow_adherence_weight * adherence_score +
            self.config.efficiency_weight * efficiency_score +
            self.config.error_handling_weight * error_score
        )
        
        details = {
            'adherence_score': adherence_score,
            'efficiency_score': efficiency_score,
            'error_score': error_score,
            'unique_tools': len(set(tool_calls)) if tool_calls else 0,
            'total_calls': len(tool_calls),
            'workflow_provided': bool(workflow)
        }
        
        return execution_quality, details
    
    def _calculate_sequence_similarity(self, actual_seq: List[str], expected_seq: List[str]) -> float:
        """计算序列相似度（使用编辑距离）"""
        if not expected_seq:
            return 0.5
        if not actual_seq:
            return 0.0
            
        # 使用Levenshtein距离的简化版本
        # 这里使用最长公共子序列（LCS）来计算相似度
        m, n = len(actual_seq), len(expected_seq)
        
        # 动态规划计算LCS
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if actual_seq[i-1] == expected_seq[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        
        lcs_length = dp[m][n]
        
        # 相似度 = 2 * LCS / (len(actual) + len(expected))
        similarity = 2.0 * lcs_length / (m + n)
        
        return similarity


class EnhancedMetricsCalculator:
    """增强的指标计算器 - 集成新的评分机制"""
    
    def __init__(self):
        self.scorer = StableScorer()
        
    def calculate_execution_metrics(self, 
                                  tool_calls: List[str],
                                  task_type: str,
                                  workflow: Optional[Dict] = None,
                                  adherence_scores: Optional[Dict] = None) -> Dict[str, float]:
        """
        计算执行质量指标 - 使用新的两维度评分系统
        """
        # 构建执行结果
        execution_result = {
            'tool_calls': tool_calls,
            'success': len(tool_calls) > 0,
            'adherence_scores': adherence_scores or {}
        }
        
        # 构建评估上下文
        expected_tools = {
            'simple_task': ['reader', 'processor'],
            'basic_task': ['reader', 'processor'],
            'data_pipeline': ['reader', 'validator', 'transformer', 'writer'],
            'api_integration': ['fetcher', 'parser', 'poster'],
            'multi_stage_pipeline': ['scanner', 'validator', 'transformer', 'aggregator', 'exporter']
        }
        
        evaluation_context = {
            'task_type': task_type,
            'required_tools': expected_tools.get(task_type, []),
            'expected_tool_count': len(expected_tools.get(task_type, [])),
            'workflow': workflow
        }
        
        # 使用新的评分器计算分数
        final_score, breakdown = self.scorer.calculate_stable_score(
            execution_result, evaluation_context
        )
        
        # 返回兼容的指标格式
        return {
            # 新的核心指标
            'final_score': final_score,
            'task_achievement': breakdown['task_achievement'],
            'execution_quality': breakdown['execution_quality'],
            
            # 详细分解（用于分析）
            'tool_score': breakdown['task_achievement_details']['tool_score'],
            'output_score': breakdown['task_achievement_details']['output_score'],
            'adherence_score': breakdown['execution_quality_details']['adherence_score'],
            'efficiency_score': breakdown['execution_quality_details']['efficiency_score'],
            'error_score': breakdown['execution_quality_details']['error_score'],
            
            # 保持向后兼容
            'task_completion': breakdown['task_achievement'],  # 映射到新指标
            'tool_diversity': breakdown['execution_quality_details']['efficiency_score'],
            'operation_coverage': breakdown['task_achievement_details']['output_score']
        }


# 测试和演示函数
def test_new_scoring_system():
    """测试新的评分系统"""
    print("🧪 Testing New Simplified Scoring System")
    print("=" * 60)
    
    calculator = EnhancedMetricsCalculator()
    
    # 测试场景
    test_cases = [
        {
            'name': 'Perfect Execution',
            'tool_calls': ['data_reader', 'data_validator', 'data_transformer', 'data_writer'],
            'task_type': 'data_pipeline',
            'expected_score': 0.9  # 应该得高分
        },
        {
            'name': 'Missing Output',
            'tool_calls': ['data_reader', 'data_validator', 'data_transformer'],
            'task_type': 'data_pipeline',
            'expected_score': 0.6  # 缺少输出，分数应该降低
        },
        {
            'name': 'Inefficient Execution',
            'tool_calls': ['data_reader', 'data_reader', 'data_validator', 'data_validator', 'data_writer'],
            'task_type': 'data_pipeline',
            'expected_score': 0.7  # 有重复，效率降低
        },
        {
            'name': 'Wrong Tools',
            'tool_calls': ['api_fetcher', 'json_parser', 'api_poster'],
            'task_type': 'data_pipeline',
            'expected_score': 0.4  # 使用错误工具，分数应该很低
        }
    ]
    
    for test in test_cases:
        metrics = calculator.calculate_execution_metrics(
            test['tool_calls'],
            test['task_type']
        )
        
        print(f"\n📋 {test['name']}:")
        print(f"   Tool Calls: {test['tool_calls']}")
        print(f"   Final Score: {metrics['final_score']:.2f}")
        print(f"   - Task Achievement: {metrics['task_achievement']:.2f}")
        print(f"   - Execution Quality: {metrics['execution_quality']:.2f}")
        print(f"   Expected Range: ~{test['expected_score']:.1f}")
        
        # 验证分数的合理性
        if abs(metrics['final_score'] - test['expected_score']) < 0.2:
            print("   ✅ Score is reasonable")
        else:
            print("   ⚠️ Score may need adjustment")
    
    print("\n✨ Scoring system test complete!")


# 集成到现有系统的示例
def integrate_with_workflow_tester():
    """展示如何集成到现有的WorkflowQualityTester"""
    
    # 这个函数展示了如何在现有代码中使用新的评分系统
    example_code = '''
    # 在WorkflowQualityTester._execute_single_test中：
    
    # 使用新的评分系统
    metrics_calculator = EnhancedMetricsCalculator()
    metrics = metrics_calculator.calculate_execution_metrics(
        tool_calls=tool_calls,
        task_type=task_type,
        workflow=workflow,
        adherence_scores=adherence_scores
    )
    
    # 判断成功的新标准（更稳定）
    success = metrics['final_score'] > 0.6  # 统一的成功阈值
    '''
    
    print("\n📝 Integration Example:")
    print(example_code)


if __name__ == "__main__":
    # 运行测试
    test_new_scoring_system()
    print("\n" + "="*60)
    integrate_with_workflow_tester()
