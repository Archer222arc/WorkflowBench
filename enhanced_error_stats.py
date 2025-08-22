#!/usr/bin/env python3
"""
增强版错误统计管理器
集成专注的AI分类器，将未分类错误归类到标准7种类型
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging

from focused_ai_classifier import FocusedAIClassifier, StandardErrorType, ErrorContext

logger = logging.getLogger(__name__)


@dataclass
class StandardErrorStats:
    """标准的7种错误统计"""
    tool_call_format_errors: int = 0
    timeout_errors: int = 0
    max_turns_errors: int = 0
    tool_selection_errors: int = 0
    parameter_config_errors: int = 0
    sequence_order_errors: int = 0
    dependency_errors: int = 0
    other_errors: int = 0  # 实在无法分类的
    
    total_errors: int = 0
    ai_classified_count: int = 0
    ai_avg_confidence: float = 0.0
    
    def add_error(self, error_type: StandardErrorType, confidence: float = 1.0):
        """添加错误到对应分类"""
        self.total_errors += 1
        
        if confidence > 0.3:  # 只统计置信度较高的AI分类
            self.ai_classified_count += 1
            # 更新平均置信度
            if self.ai_classified_count == 1:
                self.ai_avg_confidence = confidence
            else:
                self.ai_avg_confidence = ((self.ai_avg_confidence * (self.ai_classified_count - 1)) + confidence) / self.ai_classified_count
        
        # 增加对应类型的计数
        if error_type == StandardErrorType.TOOL_CALL_FORMAT:
            self.tool_call_format_errors += 1
        elif error_type == StandardErrorType.TIMEOUT:
            self.timeout_errors += 1
        elif error_type == StandardErrorType.MAX_TURNS:
            self.max_turns_errors += 1
        elif error_type == StandardErrorType.TOOL_SELECTION:
            self.tool_selection_errors += 1
        elif error_type == StandardErrorType.PARAMETER_CONFIG:
            self.parameter_config_errors += 1
        elif error_type == StandardErrorType.SEQUENCE_ORDER:
            self.sequence_order_errors += 1
        elif error_type == StandardErrorType.DEPENDENCY:
            self.dependency_errors += 1
        else:
            self.other_errors += 1
    
    def to_database_format(self) -> Dict[str, Any]:
        """转换为数据库存储格式（与现有格式兼容）"""
        return {
            "total_errors": self.total_errors,
            "tool_call_format_errors": self.tool_call_format_errors,
            "timeout_errors": self.timeout_errors,
            "max_turns_errors": self.max_turns_errors,
            "tool_selection_errors": self.tool_selection_errors,
            "parameter_config_errors": self.parameter_config_errors,
            "sequence_order_errors": self.sequence_order_errors,
            "dependency_errors": self.dependency_errors,
            "other_errors": self.other_errors,
            
            # AI分类元数据
            "ai_classified_errors": self.ai_classified_count,
            "ai_classification_confidence": self.ai_avg_confidence
        }
    
    def calculate_error_rates(self, total_tests: int) -> Dict[str, float]:
        """计算错误率"""
        if total_tests == 0:
            return {}
        
        return {
            "tool_selection_error_rate": self.tool_selection_errors / total_tests,
            "parameter_error_rate": self.parameter_config_errors / total_tests,
            "sequence_error_rate": self.sequence_order_errors / total_tests,
            "dependency_error_rate": self.dependency_errors / total_tests,
            "timeout_error_rate": self.timeout_errors / total_tests,
            "format_error_rate": self.tool_call_format_errors / total_tests,
            "max_turns_error_rate": self.max_turns_errors / total_tests,
            "other_error_rate": self.other_errors / total_tests
        }
    
    def verify_completeness(self) -> bool:
        """验证错误统计的完整性"""
        counted_errors = (
            self.tool_call_format_errors +
            self.timeout_errors +
            self.max_turns_errors +
            self.tool_selection_errors +
            self.parameter_config_errors +
            self.sequence_order_errors +
            self.dependency_errors +
            self.other_errors
        )
        
        return counted_errors == self.total_errors


class EnhancedErrorStatsManager:
    """增强版错误统计管理器"""
    
    def __init__(self, use_ai_classification: bool = True, model_name: str = "gpt-5-nano"):
        """
        初始化增强统计管理器
        
        Args:
            use_ai_classification: 是否使用AI分类未分类错误
            model_name: AI分类模型名称
        """
        self.use_ai_classification = use_ai_classification
        self.ai_classifier = None
        
        if use_ai_classification:
            try:
                self.ai_classifier = FocusedAIClassifier(model_name=model_name)
                logger.info(f"Enhanced error stats manager initialized with AI classifier: {model_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize AI classifier: {e}. Using rule-based classification only.")
                self.use_ai_classification = False
    
    def classify_error_from_test_result(self, test_result: Dict[str, Any]) -> Tuple[StandardErrorType, str, float]:
        """
        从测试结果中分类错误
        
        Args:
            test_result: 测试结果字典
            
        Returns:
            (错误类型, 分析原因, 置信度)
        """
        if test_result.get('success', True):
            return StandardErrorType.OTHER, "Test was successful", 1.0
        
        # 构建错误上下文
        context = ErrorContext(
            task_description=test_result.get('task_description', 'Unknown task'),
            task_type=test_result.get('task_type', 'unknown'),
            required_tools=test_result.get('required_tools', []),
            executed_tools=[call.get('tool', 'unknown') for call in test_result.get('tool_calls', [])],
            is_partial_success=test_result.get('success_level') == 'partial_success',
            tool_execution_results=test_result.get('tool_calls', []),
            execution_time=test_result.get('execution_time', 0.0),
            total_turns=test_result.get('turns', 0),
            error_message=test_result.get('error')
        )
        
        if self.use_ai_classification and self.ai_classifier:
            return self.ai_classifier.classify_error(context)
        else:
            return self._rule_based_classify(context)
    
    def _rule_based_classify(self, context: ErrorContext) -> Tuple[StandardErrorType, str, float]:
        """基于规则的分类（后备方案）"""
        if not context.error_message:
            return StandardErrorType.OTHER, "No error message", 0.2
        
        error_lower = context.error_message.lower()
        
        if 'timeout' in error_lower:
            return StandardErrorType.TIMEOUT, "Timeout detected", 0.9
        elif 'format' in error_lower and 'tool' in error_lower:
            return StandardErrorType.TOOL_CALL_FORMAT, "Format error detected", 0.8
        elif 'parameter' in error_lower:
            return StandardErrorType.PARAMETER_CONFIG, "Parameter error detected", 0.7
        elif 'sequence' in error_lower or 'order' in error_lower:
            return StandardErrorType.SEQUENCE_ORDER, "Sequence error detected", 0.7
        elif 'dependency' in error_lower:
            return StandardErrorType.DEPENDENCY, "Dependency error detected", 0.7
        elif 'tool' in error_lower and 'select' in error_lower:
            return StandardErrorType.TOOL_SELECTION, "Tool selection error detected", 0.7
        else:
            return StandardErrorType.OTHER, "Unclassified error", 0.3
    
    def process_test_batch(self, test_results: List[Dict[str, Any]]) -> StandardErrorStats:
        """
        处理一批测试结果，返回错误统计
        
        Args:
            test_results: 测试结果列表
            
        Returns:
            标准错误统计
        """
        stats = StandardErrorStats()
        
        for result in test_results:
            if not result.get('success', True):  # 只处理失败的测试
                error_type, reason, confidence = self.classify_error_from_test_result(result)
                stats.add_error(error_type, confidence)
                
                if confidence > 0.5:
                    logger.debug(f"Classified error as {error_type.value} (conf: {confidence:.2f}): {reason}")
        
        # 验证统计完整性
        if not stats.verify_completeness():
            logger.warning("Error statistics may be incomplete!")
        
        return stats


def demo_enhanced_stats():
    """演示增强版错误统计"""
    print("=== 增强版错误统计演示 ===\n")
    
    manager = EnhancedErrorStatsManager(
        use_ai_classification=True,
        model_name="gpt-5-nano"
    )
    
    # 模拟测试结果（包含那5个未分类的错误情况）
    sample_results = [
        {
            'success': False,
            'task_type': 'data_processing',
            'task_description': 'Process customer feedback and generate report',
            'required_tools': ['data_loader', 'analyzer', 'report_gen'],
            'tool_calls': [
                {'tool': 'data_loader', 'success': True},
                {'tool': 'analyzer', 'success': True},
                {'tool': 'report_gen', 'success': False, 'error': 'Missing analysis output'}
            ],
            'success_level': 'partial_success',
            'execution_time': 34.5,
            'turns': 8,
            'error': 'Report generation failed: Missing analysis output from previous step'
        },
        {
            'success': False,
            'task_type': 'document_processing',
            'task_description': 'Extract text from PDF',
            'required_tools': ['pdf_reader', 'text_extractor'],
            'tool_calls': [
                {'tool': 'image_analyzer', 'success': False, 'error': 'Cannot process PDF file'},
                {'tool': 'text_extractor', 'success': False, 'error': 'No input data'}
            ],
            'success_level': 'failure',
            'execution_time': 12.3,
            'turns': 4,
            'error': 'Wrong tool selection - used image_analyzer for PDF processing'
        },
        {
            'success': False,
            'task_type': 'simple_task',
            'task_description': 'Timeout test',
            'required_tools': ['slow_tool'],
            'tool_calls': [],
            'success_level': 'failure',
            'execution_time': 30.0,
            'turns': 1,
            'error': 'Timeout after 30 seconds'
        }
    ]
    
    # 处理测试结果
    stats = manager.process_test_batch(sample_results)
    
    print("错误分类结果:")
    db_format = stats.to_database_format()
    for key, value in db_format.items():
        if isinstance(value, (int, float)) and value > 0:
            if isinstance(value, float):
                print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: {value}")
    
    print(f"\n完整性检查: {'✅ 通过' if stats.verify_completeness() else '❌ 失败'}")
    print(f"AI分类占比: {stats.ai_classified_count}/{stats.total_errors}")


if __name__ == "__main__":
    demo_enhanced_stats()