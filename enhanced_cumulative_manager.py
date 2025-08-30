#!/usr/bin/env python3
"""Enhanced cumulative manager with real-time error classification"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from threading import Lock
from datetime import datetime
from pathlib import Path
import json

# V3版本：不再导入数据结构类，直接使用字典操作
# 支持存储格式选择
import os
storage_format = os.environ.get('STORAGE_FORMAT', 'json').lower()
if storage_format == 'parquet':
    try:
        from parquet_cumulative_manager import (
            ParquetCumulativeManager as CumulativeTestManager,
            TestRecord,
            add_test_result,
            check_progress,
            is_test_completed,
            finalize
        )
        print(f"[INFO] 使用Parquet存储格式")
    except ImportError:
        from cumulative_test_manager import CumulativeTestManager, TestRecord, normalize_model_name
        print(f"[INFO] Parquet不可用，使用JSON存储格式")
else:
    from cumulative_test_manager import CumulativeTestManager, TestRecord, normalize_model_name
    print(f"[INFO] 使用JSON存储格式")


@dataclass
class RuntimeErrorStats:
    """Runtime error statistics - lightweight in-memory tracking"""
    # Error categorization counts
    format_errors: int = 0
    timeout_errors: int = 0
    max_turns_errors: int = 0
    tool_selection_errors: int = 0
    parameter_errors: int = 0
    sequence_errors: int = 0
    dependency_errors: int = 0
    other_errors: int = 0
    total_errors: int = 0
    
    # Assisted statistics
    tests_with_assistance: int = 0
    total_assisted_turns: int = 0
    assisted_success: int = 0
    assisted_failure: int = 0
    
    def categorize_and_count(self, error_msg: str) -> str:
        """Categorize error and increment counter"""
        if not error_msg:
            return 'unknown'
        
        self.total_errors += 1
        error_lower = error_msg.lower()
        
        # Format errors
        if any(x in error_lower for x in ['format errors detected', 'format recognition issue', 
                                          'tool call format', 'understand tool call format']):
            self.format_errors += 1
            return 'format'
        
        # Max turns without tool calls (also format)
        if ('no tool calls' in error_lower and 'turns' in error_lower) or \
           ('max turns reached' in error_lower and 'no tool calls' in error_lower):
            self.format_errors += 1
            return 'format'
        
        # Pure max turns
        if 'max turns reached' in error_lower:
            self.max_turns_errors += 1
            return 'max_turns'
        
        # Agent-level timeout (not tool-level timeout)
        if ('test timeout after' in error_lower) or \
           ('timeout after' in error_lower and ('seconds' in error_lower or 'minutes' in error_lower)) or \
           ('agent timeout' in error_lower) or \
           ('execution timeout' in error_lower):
            self.timeout_errors += 1
            return 'timeout'
        
        # Tool selection
        if ('tool' in error_lower and ('select' in error_lower or 'choice' in error_lower)) or \
           'tool calls failed' in error_lower:
            self.tool_selection_errors += 1
            return 'tool_selection'
        
        # Parameter errors
        if any(x in error_lower for x in ['parameter', 'argument', 'invalid_input', 
                                          'permission_denied', 'validation failed']):
            self.parameter_errors += 1
            return 'parameter'
        
        # Sequence errors
        if any(x in error_lower for x in ['sequence', 'order', 'required tools not completed']):
            self.sequence_errors += 1
            return 'sequence'
        
        # Dependency errors
        if 'dependency' in error_lower or 'prerequisite' in error_lower:
            self.dependency_errors += 1
            return 'dependency'
        
        # Tool-level errors (not Agent errors) - for statistical completeness
        if any(tool_error in error_lower for tool_error in ['timeout', 'network_error', 'permission_denied', 
                                                           'file_not_found', 'operation_failed', 'resource_error']):
            self.other_errors += 1
            return 'tool_level_error'
        
        # Other
        self.other_errors += 1
        return 'other'
    
    def add_assisted_test(self, success: bool, format_turns: int):
        """Add assisted test statistics"""
        self.tests_with_assistance += 1
        self.total_assisted_turns += format_turns
        if success:
            self.assisted_success += 1
        else:
            self.assisted_failure += 1
    
    def to_error_metrics(self) -> Dict:
        """Convert to dictionary for database storage"""
        return {
            "total_errors": self.total_errors,
            "tool_call_format_errors": self.format_errors,
            "timeout_errors": self.timeout_errors,
            "max_turns_errors": self.max_turns_errors,
            "tool_selection_errors": self.tool_selection_errors,
            "parameter_config_errors": self.parameter_errors,
            "sequence_order_errors": self.sequence_errors,
            "dependency_errors": self.dependency_errors,
            "other_errors": self.other_errors
        }


class EnhancedCumulativeManager(CumulativeTestManager):
    """Enhanced manager with runtime error classification and V2 support"""
    
    def __init__(self, use_v2_model=True, use_ai_classification=True, db_suffix=''):
        super().__init__(db_suffix=db_suffix)
        # Runtime statistics (not persisted)
        self.runtime_stats = {}  # model -> prompt_type -> RuntimeErrorStats
        self.runtime_lock = Lock()
        
        # AI分类支持
        self.use_ai_classification = use_ai_classification
        self.ai_classifier = None
        if use_ai_classification:
            try:
                from focused_ai_classifier import FocusedAIClassifier
                self.ai_classifier = FocusedAIClassifier(model_name="gpt-5-nano")
                print(f"[INFO] Enhanced manager: AI错误分类系统已启用")
            except Exception as e:
                print(f"[ERROR] Failed to initialize AI classifier in manager: {e}")
                self.use_ai_classification = False
        
        # Buffer for batch updates
        self.update_buffer = []
        self.buffer_size = 3  # 减小缓冲区，更频繁地保存（原来是10）
        self.last_flush_time = datetime.now()
        self.flush_interval = 30  # 每30秒强制flush一次，即使缓冲区未满
        
        # Enable V2 model by default
        self.use_v2_model = use_v2_model
        
    def _get_record_attr(self, record, attr_name, default=None):
        """Safely get attribute from record whether it's dict or object"""
        if isinstance(record, dict):
            return record.get(attr_name, default)
        else:
            return getattr(record, attr_name, default)
    
    def add_test_result_with_classification(self, record: TestRecord) -> bool:
        """Add test result with real-time error classification"""
        with self.runtime_lock:
            # Get or create runtime stats
            model_name = self._get_record_attr(record, 'model', 'unknown')
            normalized_model = normalize_model_name(model_name)
            model_stats = self.runtime_stats.setdefault(normalized_model, {})
            
            # Determine effective prompt type
            is_flawed = self._get_record_attr(record, 'is_flawed', False)
            flaw_type = self._get_record_attr(record, 'flaw_type', None)
            prompt_type = self._get_record_attr(record, 'prompt_type', 'optimal')
            success = self._get_record_attr(record, 'success', False)
                
            if is_flawed and flaw_type:
                effective_prompt = f"flawed_{flaw_type}"
            else:
                effective_prompt = prompt_type
            
            prompt_stats = model_stats.setdefault(effective_prompt, RuntimeErrorStats())
            
            # Classify error if test failed or partial success (which also has errors)
            success_level = self._get_record_attr(record, 'success_level', '')
            has_errors = (not success or success_level == 'partial_success')
            
            if has_errors:
                error_type = 'unknown'
                
                # 首先检查是否已经有AI分类结果（由batch_test_runner提供）
                ai_error_category = self._get_record_attr(record, 'ai_error_category', None)
                    
                if ai_error_category:
                    # 使用batch_test_runner已经做好的AI分类
                    ai_category = str(ai_error_category).lower()
                    prompt_stats.total_errors += 1
                    
                    print(f"[AI-CLASSIFY-EXISTING] Using existing AI classification: {ai_category}")
                    
                    # 根据AI分类结果更新统计
                    if 'tool_selection' in ai_category:
                        prompt_stats.tool_selection_errors += 1
                        error_type = 'tool_selection_errors'
                    elif 'parameter' in ai_category or 'parameter_config' in ai_category:
                        prompt_stats.parameter_errors += 1
                        error_type = 'parameter_config_errors'
                    elif 'sequence' in ai_category or 'sequence_order' in ai_category:
                        prompt_stats.sequence_errors += 1
                        error_type = 'sequence_order_errors'
                    elif 'dependency' in ai_category:
                        prompt_stats.dependency_errors += 1
                        error_type = 'dependency_errors'
                    elif 'timeout' in ai_category:
                        prompt_stats.timeout_errors += 1
                        error_type = 'timeout_errors'
                    elif 'format' in ai_category or 'tool_call_format' in ai_category:
                        prompt_stats.format_errors += 1
                        error_type = 'tool_call_format_errors'
                    elif 'max_turns' in ai_category:
                        prompt_stats.max_turns_errors += 1
                        error_type = 'max_turns_errors'
                    else:
                        prompt_stats.other_errors += 1
                        error_type = 'other_errors'
                    
                    if hasattr(record, 'ai_confidence'):
                        task_type = self._get_record_attr(record, 'task_type', 'unknown')
                        ai_confidence = self._get_record_attr(record, 'ai_confidence', 0.0)
                        print(f"[AI-CLASSIFY-EXISTING] {normalized_model} {task_type}: {error_type} (confidence: {ai_confidence:.2f})")
                    
                # 如果没有现有分类，再使用自己的AI分类器
                elif self.use_ai_classification and self.ai_classifier:
                    try:
                        from focused_ai_classifier import ErrorContext
                        
                        # 构建错误上下文
                        # 对于partial success，如果没有明确错误消息，构建描述性消息
                        error_msg = self._get_record_attr(record, 'error_message', '')
                        if not error_msg and getattr(record, 'success_level', '') == 'partial_success':
                            format_count = getattr(record, 'format_error_count', 0)
                            if format_count > 0:
                                error_msg = f"Format issues detected: {format_count} format helps needed"
                            else:
                                error_msg = "Partial success - quality issues detected"
                        
                        context = ErrorContext(
                            task_description=getattr(record, 'task_description', 'Unknown task'),
                            task_type=self._get_record_attr(record, 'task_type', 'unknown'),
                            required_tools=getattr(record, 'required_tools', []),
                            executed_tools=getattr(record, 'executed_tools', []),
                            is_partial_success=(getattr(record, 'success_level', '') == 'partial_success'),
                            tool_execution_results=getattr(record, 'tool_calls', []),
                            execution_time=self._get_record_attr(record, 'execution_time', 0.0),
                            total_turns=getattr(record, 'turns', 0),
                            error_message=error_msg or "Unknown error"
                        )
                        
                        # 进行AI分类
                        category, reason, confidence = self.ai_classifier.classify_error(context)
                        
                        # 根据AI分类结果更新统计
                        error_type = category.value
                        prompt_stats.total_errors += 1
                        
                        if category.value == 'tool_selection_errors':
                            prompt_stats.tool_selection_errors += 1
                        elif category.value == 'parameter_config_errors':
                            prompt_stats.parameter_errors += 1
                        elif category.value == 'sequence_order_errors':
                            prompt_stats.sequence_errors += 1
                        elif category.value == 'dependency_errors':
                            prompt_stats.dependency_errors += 1
                        elif category.value == 'timeout_errors':
                            prompt_stats.timeout_errors += 1
                        elif category.value == 'tool_call_format_errors':
                            prompt_stats.format_errors += 1
                        elif category.value == 'max_turns_errors':
                            prompt_stats.max_turns_errors += 1
                        else:
                            prompt_stats.other_errors += 1
                        
                        task_type = self._get_record_attr(record, 'task_type', 'unknown')
                        print(f"[AI-CLASSIFY-NEW] {normalized_model} {task_type}: {error_type} (confidence: {confidence:.2f}) - {reason[:50]}")
                        
                    except Exception as e:
                        print(f"[ERROR] AI classification failed: {e}, falling back to rule-based")
                        import traceback
                        print(f"[DEBUG] Full traceback: {traceback.format_exc()}")
                        # 回退到基于规则的分类
                        error_msg = self._get_record_attr(record, 'error_message', None)
                        if error_msg:
                            error_type = prompt_stats.categorize_and_count(error_msg)
                        else:
                            prompt_stats.total_errors += 1
                            # 没有错误消息时，归类为other_errors
                            prompt_stats.other_errors += 1
                            error_type = 'other_errors'
                else:
                    # 使用基于规则的分类（原有逻辑）
                    error_msg = self._get_record_attr(record, 'error_message', None)
                    if error_msg:
                        error_type = prompt_stats.categorize_and_count(error_msg)
                    else:
                        prompt_stats.total_errors += 1
                        # 没有错误消息时，归类为other_errors
                        prompt_stats.other_errors += 1
                        error_type = 'other_errors'
                
                # 存储分类结果
                if not isinstance(record, dict):
                    record.error_classification = error_type
            
            # Track assisted statistics
            format_error_count = self._get_record_attr(record, 'format_error_count', 0)
            if format_error_count > 0:
                success = self._get_record_attr(record, 'success', False) or self._get_record_attr(record, 'partial_success', False)
                prompt_stats.add_assisted_test(success, format_error_count)
            
            # Add to buffer
            self.update_buffer.append(record)
            
            # Check if we should update database
            should_flush = False
            
            # 条件1：缓冲区满了
            if len(self.update_buffer) >= self.buffer_size:
                should_flush = True
                print(f"[INFO] Buffer full ({len(self.update_buffer)} records), triggering flush...")
            
            # 条件2：距离上次flush超过指定时间
            time_since_flush = (datetime.now() - self.last_flush_time).total_seconds()
            if time_since_flush >= self.flush_interval and self.update_buffer:
                should_flush = True
                print(f"[INFO] Time-based flush ({time_since_flush:.1f}s since last flush)...")
            
            if should_flush:
                self._flush_buffer()
                self.last_flush_time = datetime.now()
        
        return True
    
    def append_test_result(self, record: TestRecord) -> bool:
        """
        别名方法，为了兼容性
        调用 add_test_result_with_classification
        """
        return self.add_test_result_with_classification(record)
    
    def _flush_buffer(self):
        """Flush buffer to database with aggregated statistics"""
        if not self.update_buffer:
            return
        
        print(f"[INFO] Flushing {len(self.update_buffer)} records to database...")
        
        try:
            # Process each buffered record
            for i, record in enumerate(self.update_buffer):
                if self.use_v2_model:
                    # Use V2 model processing
                    self._add_test_result_v2(record)
                else:
                    # Call parent method to update basic statistics
                    super().add_test_result(record)
                
                # 每处理5条记录打印一次进度
                if (i + 1) % 5 == 0:
                    print(f"[INFO] Processed {i + 1}/{len(self.update_buffer)} records...")
            
            print(f"[INFO] All records processed, updating error metrics...")
            # Update error classifications in database
            self._update_error_metrics()
            
            # 重新计算total_tests基于实际的测试结果
            self._recalculate_total_tests()
            
            # Clear buffer BEFORE saving to avoid re-processing if save fails
            self.update_buffer.clear()
            
            # Save database with timeout protection
            print(f"[INFO] Saving database...")
            import time
            start_time = time.time()
            self.save_database()
            elapsed = time.time() - start_time
            print(f"[INFO] Database saved successfully in {elapsed:.2f}s")
            
        except Exception as e:
            print(f"[ERROR] Failed to flush buffer: {e}")
            import traceback
            traceback.print_exc()
            # 清空缓冲区以避免重复处理
            self.update_buffer.clear()
            raise  # 重新抛出异常让调用者知道出错了
    
    def _recalculate_total_tests(self):
        """重新计算每个模型的total_tests基于实际的测试结果"""
        for model_name in self.database["models"]:
            model_data = self.database["models"][model_name]
            
            # 检查model_data是否是字典（V3结构）还是ModelStatistics对象（V2结构）
            if not isinstance(model_data, dict):
                # 如果是ModelStatistics对象，跳过重新计算
                continue
            
            # 计算实际的测试数量
            actual_total = 0
            by_prompt_type = model_data.get('by_prompt_type', {})
            
            for prompt_type, prompt_data in by_prompt_type.items():
                by_tool_success = prompt_data.get('by_tool_success_rate', {})
                for rate, rate_data in by_tool_success.items():
                    by_diff = rate_data.get('by_difficulty', {})
                    for diff, diff_data in by_diff.items():
                        by_task = diff_data.get('by_task_type', {})
                        for task, task_data in by_task.items():
                            actual_total += task_data.get('total', 0)
            
            # 更新total_tests
            model_data['total_tests'] = actual_total
    
    def _update_error_metrics(self):
        """Update error metrics in database from runtime stats"""
        for model_name, model_prompts in self.runtime_stats.items():
            if model_name not in self.database["models"]:
                continue
            
            model_data = self.database["models"][model_name]
            
            # Update overall error metrics
            overall_errors = RuntimeErrorStats()
            for prompt_stats in model_prompts.values():
                overall_errors.format_errors += prompt_stats.format_errors
                overall_errors.timeout_errors += prompt_stats.timeout_errors
                overall_errors.max_turns_errors += prompt_stats.max_turns_errors
                overall_errors.tool_selection_errors += prompt_stats.tool_selection_errors
                overall_errors.parameter_errors += prompt_stats.parameter_errors
                overall_errors.sequence_errors += prompt_stats.sequence_errors
                overall_errors.dependency_errors += prompt_stats.dependency_errors
                overall_errors.other_errors += prompt_stats.other_errors
                overall_errors.total_errors += prompt_stats.total_errors
            
            # Only process dict-based model_data (V3 structure)
            # Skip any ModelStatistics objects from older versions
            if not isinstance(model_data, dict):
                continue
            
            # V3 structure - error metrics are handled in _add_test_result_v2
            # No need to update here as they're already in the dict structure
    
    def finalize(self):
        """Finalize and flush all pending updates"""
        with self.runtime_lock:
            if self.update_buffer:
                self._flush_buffer()
            
            # Save final statistics report
            self._save_runtime_report()
        
        # 保存数据库到文件
        self.save_database_enhanced()
    
    def _save_runtime_report(self):
        """Save runtime statistics report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 保存到runtime_reports目录，如果不存在则创建
        report_dir = Path("runtime_reports")
        report_dir.mkdir(exist_ok=True)
        report_file = report_dir / f"runtime_error_report_{timestamp}.json"
        
        report = {
            "timestamp": timestamp,
            "models": {}
        }
        
        for model_name, model_prompts in self.runtime_stats.items():
            model_report = {}
            for prompt_type, stats in model_prompts.items():
                model_report[prompt_type] = {
                    "total_errors": stats.total_errors,
                    "error_breakdown": {
                        "format": stats.format_errors,
                        "timeout": stats.timeout_errors,
                        "max_turns": stats.max_turns_errors,
                        "tool_selection": stats.tool_selection_errors,
                        "parameter": stats.parameter_errors,
                        "sequence": stats.sequence_errors,
                        "dependency": stats.dependency_errors,
                        "other": stats.other_errors
                    },
                    "assisted_stats": {
                        "tests_with_assistance": stats.tests_with_assistance,
                        "total_assisted_turns": stats.total_assisted_turns,
                        "assisted_success": stats.assisted_success,
                        "assisted_failure": stats.assisted_failure
                    }
                }
            report["models"][model_name] = model_report
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # 使用简单的字符串路径，避免relative_to的问题
        print(f"[INFO] Runtime error report saved to: {report_file}")
    
    def get_runtime_summary(self) -> Dict:
        """Get current runtime statistics summary"""
        with self.runtime_lock:
            summary = {}
            for model_name, model_prompts in self.runtime_stats.items():
                model_summary = {
                    "total_errors": 0,
                    "by_prompt_type": {}
                }
                
                for prompt_type, stats in model_prompts.items():
                    model_summary["total_errors"] += stats.total_errors
                    model_summary["by_prompt_type"][prompt_type] = {
                        "total_errors": stats.total_errors,
                        "format": stats.format_errors,
                        "timeout": stats.timeout_errors,
                        "max_turns": stats.max_turns_errors,
                        "assisted": stats.tests_with_assistance
                    }
                
                summary[model_name] = model_summary
            
            return summary
    
    def _add_test_result_v2(self, record: TestRecord):
        """Add test result using V2 model with hierarchical structure"""
        # 规范化模型名称
        model_name = self._get_record_attr(record, 'model', 'unknown')
        normalized_model = normalize_model_name(model_name)
        
        # 确保模型存在于数据库中 - 内层数据保护修复
        if normalized_model not in self.database["models"]:
            # 🔧 数据保护修复：先检查磁盘上是否有最新数据
            try:
                if self.db_file.exists():
                    # 重新加载磁盘数据，检查其他进程是否已创建此模型
                    with open(self.db_file, 'r', encoding='utf-8') as f:
                        latest_disk_data = json.load(f)
                    
                    if normalized_model in latest_disk_data.get("models", {}):
                        # 其他进程已创建，合并磁盘数据避免覆盖
                        self.database["models"][normalized_model] = latest_disk_data["models"][normalized_model]
                        print(f"[ENHANCED_DATA_PROTECTION] 合并来自磁盘的模型数据: {normalized_model}")
                    else:
                        # 真正的新模型，创建空结构
                        self.database["models"][normalized_model] = {
                            "model_name": normalized_model,
                            "first_test_time": datetime.now().isoformat(),
                            "last_test_time": datetime.now().isoformat(),
                            "total_tests": 0,
                            "overall_stats": {},
                            "by_prompt_type": {}
                        }
                        print(f"[ENHANCED_DATA_PROTECTION] 创建新模型结构: {normalized_model}")
                else:
                    # 数据库文件不存在，创建新模型
                    self.database["models"][normalized_model] = {
                        "model_name": normalized_model,
                        "first_test_time": datetime.now().isoformat(),
                        "last_test_time": datetime.now().isoformat(),
                        "total_tests": 0,
                        "overall_stats": {},
                        "by_prompt_type": {}
                    }
                    print(f"[ENHANCED_DATA_PROTECTION] 创建首个模型结构: {normalized_model}")
            except Exception as e:
                print(f"[ENHANCED_DATA_PROTECTION] 磁盘数据加载失败，使用内存数据: {e}")
                # 回退到原始逻辑
                self.database["models"][normalized_model] = {
                    "model_name": normalized_model,
                    "first_test_time": datetime.now().isoformat(),
                    "last_test_time": datetime.now().isoformat(),
                    "total_tests": 0,
                    "overall_stats": {},
                    "by_prompt_type": {}
                }
        
        model_data = self.database["models"][normalized_model]
        model_data["last_test_time"] = datetime.now().isoformat()
        # 注意：不在这里增加total_tests，而是基于实际的测试结果计算
        
        # 直接使用字典操作，不使用V2对象
        
        # 准备测试记录字典，包含所有关键字段
        # 处理record可能是dict或TestRecord对象的情况
        if isinstance(record, dict):
            test_dict = {
                'success': record.get('success', False),
                'partial_success': record.get('partial_success', False),
                'execution_time': record.get('execution_time', 0.0),
                'turns': record.get('turns', 0),
                'tool_calls': record.get('tool_calls', []),
                'error_message': record.get('error_message', None),
                # 添加关键的缺失字段
                'workflow_score': record.get('workflow_score', 0.0),
                'phase2_score': record.get('phase2_score', 0.0),
                'quality_score': record.get('quality_score', 0.0),
                'final_score': record.get('final_score', 0.0),
                'required_tools': record.get('required_tools', []),
                'executed_tools': record.get('executed_tools', []),
                'tool_coverage_rate': record.get('tool_coverage_rate', 0.0),
                'success_level': record.get('success_level', 'failure'),
                'task_instance': record.get('task_instance', {}),
                'format_error_count': record.get('format_error_count', 0),
                'tool_reliability': record.get('tool_reliability', 100.0)
            }
        else:
            test_dict = {
                'success': record.success,
                'partial_success': getattr(record, 'partial_success', False),
                'execution_time': record.execution_time,
                'turns': record.turns,
                'tool_calls': record.tool_calls if record.tool_calls else [],
                'error_message': record.error_message,
                # 添加关键的缺失字段
                'workflow_score': getattr(record, 'workflow_score', 0.0),
                'phase2_score': getattr(record, 'phase2_score', 0.0),
                'quality_score': getattr(record, 'quality_score', 0.0),
                'final_score': getattr(record, 'final_score', 0.0),
                'required_tools': getattr(record, 'required_tools', []),
                'executed_tools': getattr(record, 'executed_tools', []),
                'tool_coverage_rate': getattr(record, 'tool_coverage_rate', 0.0),
                'success_level': getattr(record, 'success_level', 'failure'),
                'task_instance': getattr(record, 'task_instance', {}),
                'format_error_count': getattr(record, 'format_error_count', 0),
                'tool_reliability': getattr(record, 'tool_reliability', 100.0)
            }
        
        # 获取tool_success_rate（可能需要从record属性中提取）
        if isinstance(record, dict):
            tool_success_rate = record.get('tool_success_rate', 1.0)
        else:
            tool_success_rate = getattr(record, 'tool_success_rate', 1.0)
        
        # 更新overall_stats
        if "overall_stats" not in model_data:
            model_data["overall_stats"] = {
                "total_success": 0,
                "total_partial": 0,
                "total_full": 0,
                "total_failure": 0,
                "success_rate": 0.0,
                "weighted_success_score": 0.0,
                "avg_execution_time": 0.0,
                "avg_turns": 0.0,
                "tool_coverage_rate": 0.0
            }
        
        # 更新统计（这些会在_recalculate_total_tests中重新计算）
        model_data["total_tests"] = model_data.get("total_tests", 0) + 1
        
        # 确定有效的prompt_type（与runtime_stats保持一致）
        if isinstance(record, dict):
            is_flawed = record.get('is_flawed', False)
            flaw_type = record.get('flaw_type', None)
            prompt_type = record.get('prompt_type', 'optimal')
        else:
            is_flawed = record.is_flawed
            flaw_type = record.flaw_type
            prompt_type = record.prompt_type
            
        if is_flawed and flaw_type:
            effective_prompt = f"flawed_{flaw_type}"
        else:
            effective_prompt = prompt_type
        
        # 更新层次结构
        if effective_prompt not in model_data["by_prompt_type"]:
            model_data["by_prompt_type"][effective_prompt] = {
                "by_tool_success_rate": {},
                "summary": {}
            }
        
        prompt_data = model_data["by_prompt_type"][effective_prompt]
        
        # 将tool_success_rate分桶（保留4位小数精度）
        rate_bucket = str(round(tool_success_rate, 4))
        
        if rate_bucket not in prompt_data["by_tool_success_rate"]:
            prompt_data["by_tool_success_rate"][rate_bucket] = {
                "by_difficulty": {}
            }
        
        rate_data = prompt_data["by_tool_success_rate"][rate_bucket]
        
        # 获取difficulty和task_type
        if isinstance(record, dict):
            difficulty = record.get('difficulty', 'easy')
            task_type = record.get('task_type', 'unknown')
        else:
            difficulty = record.difficulty
            task_type = record.task_type
        
        if difficulty not in rate_data["by_difficulty"]:
            rate_data["by_difficulty"][difficulty] = {
                "by_task_type": {}
            }
        
        diff_data = rate_data["by_difficulty"][difficulty]
        
        if task_type not in diff_data["by_task_type"]:
            diff_data["by_task_type"][task_type] = {}
        
        # 直接更新任务统计字典
        task_data = diff_data["by_task_type"][task_type]
        
        # 初始化统计字段（如果不存在）
        if "total" not in task_data:
            task_data.update({
                "total": 0,
                "success": 0,
                "partial": 0,
                "failed": 0,
                "success_rate": 0.0,
                "partial_rate": 0.0,
                "failure_rate": 0.0,
                "weighted_success_score": 0.0,
                "full_success_rate": 0.0,
                "partial_success_rate": 0.0,
                "avg_execution_time": 0.0,
                "avg_turns": 0.0,
                "avg_tool_calls": 0.0,
                "tool_coverage_rate": 0.0,
                "avg_workflow_score": 0.0,
                "avg_phase2_score": 0.0,
                "avg_quality_score": 0.0,
                "avg_final_score": 0.0,
                "total_errors": 0,
                "tool_call_format_errors": 0,
                "timeout_errors": 0,
                "dependency_errors": 0,
                "parameter_config_errors": 0,
                "tool_selection_errors": 0,
                "sequence_order_errors": 0,
                "max_turns_errors": 0,
                "other_errors": 0,
                "tool_selection_error_rate": 0.0,
                "parameter_error_rate": 0.0,
                "sequence_error_rate": 0.0,
                "dependency_error_rate": 0.0,
                "timeout_error_rate": 0.0,
                "format_error_rate": 0.0,
                "max_turns_error_rate": 0.0,
                "other_error_rate": 0.0,
                "assisted_failure": 0,
                "assisted_success": 0,
                "total_assisted_turns": 0,
                "tests_with_assistance": 0,
                "avg_assisted_turns": 0.0,
                "assisted_success_rate": 0.0,
                "assistance_rate": 0.0
            })
        
        # 更新统计
        task_data["total"] += 1
        # 安全获取success值，支持dict和对象
        success_value = record.get('success', False) if isinstance(record, dict) else getattr(record, 'success', False)
        if success_value:
            task_data["success"] += 1
            if test_dict.get("success_level") == "full_success":
                task_data.setdefault("full_success", 0)
                task_data["full_success"] += 1
            elif test_dict.get("success_level") == "partial_success":
                task_data.setdefault("partial_success", 0)
                task_data["partial_success"] += 1
                # 注意：partial_success计入success但也需要单独记录
                task_data.setdefault("partial", 0)
                task_data["partial"] += 1
        else:
            # 失败的情况
            task_data.setdefault("failed", 0)
            task_data["failed"] += 1
        
        # 更新辅助统计
        if test_dict.get("format_error_count", 0) > 0:
            task_data["tests_with_assistance"] += 1
            task_data["total_assisted_turns"] += test_dict["format_error_count"]
            # 使用之前计算的success_value，避免重复访问
            if success_value:
                task_data["assisted_success"] += 1
            else:
                task_data["assisted_failure"] += 1
        
        # 更新错误统计
        # 注意：partial_success也应该有错误类型，因为没有完全成功说明存在问题
        success_level = test_dict.get("success_level", "failure")
        
        if success_level != "full_success":  # full_success之外都应该有错误分类
            task_data["total_errors"] += 1
            
            # 首先检查是否已经有AI分类结果（由batch_test_runner提供）
            ai_error_category = self._get_record_attr(record, 'ai_error_category', None)
            if ai_error_category:
                # 使用batch_test_runner已经做好的AI分类
                ai_category = str(ai_error_category).lower()
                
                # 尝试使用模糊匹配确保正确分类
                try:
                    from fuzzy_error_matcher import FuzzyErrorMatcher
                    matched_error = FuzzyErrorMatcher.match_error_category(ai_category, threshold=0.6)
                    if matched_error:
                        print(f"[TASK-AI-CLASSIFY] Using fuzzy-matched AI classification: {ai_category} -> {matched_error}")
                        # 更新对应的错误计数
                        if matched_error == 'tool_selection_errors':
                            task_data["tool_selection_errors"] += 1
                        elif matched_error == 'parameter_config_errors':
                            task_data["parameter_config_errors"] += 1
                        elif matched_error == 'sequence_order_errors':
                            task_data["sequence_order_errors"] += 1
                        elif matched_error == 'dependency_errors':
                            task_data["dependency_errors"] += 1
                        elif matched_error == 'timeout_errors':
                            task_data["timeout_errors"] += 1
                        elif matched_error == 'tool_call_format_errors':
                            task_data["tool_call_format_errors"] += 1
                        elif matched_error == 'max_turns_errors':
                            task_data["max_turns_errors"] += 1
                        else:
                            task_data["other_errors"] += 1
                    else:
                        # 无法匹配，归为other_errors
                        print(f"[TASK-AI-CLASSIFY] Cannot match AI classification: {ai_category}, using other_errors")
                        task_data["other_errors"] += 1
                except ImportError:
                    # 如果没有fuzzy matcher，使用简单字符串匹配
                    print(f"[TASK-AI-CLASSIFY] Using existing AI classification (no fuzzy): {ai_category}")
                    
                    if 'tool_selection' in ai_category:
                        task_data["tool_selection_errors"] += 1
                    elif 'parameter' in ai_category or 'param' in ai_category:
                        task_data["parameter_config_errors"] += 1
                    elif 'sequence' in ai_category:
                        task_data["sequence_order_errors"] += 1
                    elif 'dependency' in ai_category:
                        task_data["dependency_errors"] += 1
                    elif 'timeout' in ai_category:
                        task_data["timeout_errors"] += 1
                    elif 'format' in ai_category or 'tool_call_format' in ai_category:
                        task_data["tool_call_format_errors"] += 1
                    elif 'max_turns' in ai_category:
                        task_data["max_turns_errors"] += 1
                    else:
                        task_data["other_errors"] += 1
                
                ai_confidence = self._get_record_attr(record, 'ai_confidence', None)
                if ai_confidence is not None:
                    task_type_str = self._get_record_attr(record, 'task_type', 'unknown')
                    print(f"[TASK-AI-CLASSIFY] {normalized_model} {task_type_str}: confidence={ai_confidence:.2f}")
            
            # 如果没有现有AI分类，检查是否为明显的format error
            else:
                # 智能检查是否为format error（不再过于激进）
                tool_calls = getattr(record, 'tool_calls', [])
                executed_tools = getattr(record, 'executed_tools', [])
                error_msg = getattr(record, 'error_message', '')
                
                # 更精确的格式错误检测条件
                is_format_error = False
                # 修复：处理tool_calls可能是int的情况
                if isinstance(tool_calls, int):
                    tool_calls_len = tool_calls
                elif tool_calls:
                    tool_calls_len = len(tool_calls)
                else:
                    tool_calls_len = 0
                
                if isinstance(executed_tools, int):
                    executed_tools_len = executed_tools
                elif executed_tools:
                    executed_tools_len = len(executed_tools)
                else:
                    executed_tools_len = 0
                
                if tool_calls_len == 0 and executed_tools_len == 0:
                    # 分析为什么没有工具调用
                    if error_msg:
                        error_lower = error_msg.lower()
                        # 只有明确的格式相关错误才归类为format error
                        format_indicators = [
                            'format errors detected', 'format recognition issue',
                            'tool call format', 'understand tool call format',
                            'invalid json', 'malformed', 'parse error',
                            'unable to parse', 'json syntax error'
                        ]
                        # 排除明显不是格式问题的情况
                        non_format_indicators = [
                            'timeout', 'connection', 'network', 'api error',
                            'service unavailable', 'rate limit', 'unauthorized',
                            'internal server error', 'bad gateway'
                        ]
                        
                        if any(indicator in error_lower for indicator in format_indicators):
                            is_format_error = True
                        elif any(indicator in error_lower for indicator in non_format_indicators):
                            # 明显是环境/API问题，不是格式问题
                            is_format_error = False
                        else:
                            # 没有明确错误消息或无法判断，保守地不归类为格式错误
                            # 让AI分类器或fallback逻辑来处理
                            is_format_error = False
                    else:
                        # 没有错误消息的情况，可能是环境问题
                        is_format_error = False
                
                if is_format_error:
                    task_data["tool_call_format_errors"] += 1
                    task_type_str = self._get_record_attr(record, 'task_type', 'unknown')
                    print(f"[FORMAT-ERROR-DETECTED] {normalized_model} {task_type_str}: Confirmed format error based on error message")
                elif self.use_ai_classification and self.ai_classifier:
                    # 使用AI分类器进行错误分类
                    try:
                        from focused_ai_classifier import ErrorContext
                        
                        # 构建错误上下文
                        error_msg = self._get_record_attr(record, 'error_message', '')
                        if not error_msg and success_level == 'partial_success':
                            format_count = getattr(record, 'format_error_count', 0)
                            if format_count > 0:
                                error_msg = f"Format issues detected: {format_count} format helps needed"
                            else:
                                error_msg = "Partial success - quality issues detected"
                        
                        task_type_str = self._get_record_attr(record, 'task_type', 'unknown')
                        context = ErrorContext(
                            task_description=self._get_record_attr(record, 'task_description', f'{task_type_str} task'),
                            task_type=self._get_record_attr(record, 'task_type', 'unknown'),
                            required_tools=getattr(record, 'required_tools', []),
                            executed_tools=getattr(record, 'executed_tools', []),
                            is_partial_success=(success_level == 'partial_success'),
                            tool_execution_results=getattr(record, 'execution_history', []),
                            execution_time=self._get_record_attr(record, 'execution_time', 0.0),
                            total_turns=self._get_record_attr(record, 'turns', 0),
                            error_message=error_msg
                        )
                        
                        category, reason, confidence = self.ai_classifier.classify_error(context)
                        error_type = category.value
                        
                        # 根据AI分类结果更新任务统计
                        if category.value == 'tool_selection_errors':
                            task_data["tool_selection_errors"] += 1
                        elif category.value == 'parameter_config_errors':
                            task_data["parameter_config_errors"] += 1
                        elif category.value == 'sequence_order_errors':
                            task_data["sequence_order_errors"] += 1
                        elif category.value == 'dependency_errors':
                            task_data["dependency_errors"] += 1
                        elif category.value == 'timeout_errors':
                            task_data["timeout_errors"] += 1
                        elif category.value == 'tool_call_format_errors':
                            task_data["tool_call_format_errors"] += 1
                        elif category.value == 'max_turns_errors':
                            task_data["max_turns_errors"] += 1
                        else:
                            task_data["other_errors"] += 1
                        
                        task_type_str = self._get_record_attr(record, 'task_type', 'unknown')
                        print(f"[AI-CLASSIFY-TASK] {normalized_model} {task_type_str}: {error_type} (confidence: {confidence:.2f})")
                        
                    except Exception as e:
                        print(f"[AI-CLASSIFY-TASK] Failed: {e}, using fallback classification")
                        # AI分类失败，使用fallback逻辑
                        self._apply_fallback_error_classification(task_data, record)
                else:
                    # 没有AI分类器，使用fallback逻辑
                    self._apply_fallback_error_classification(task_data, record)
        
        # 重新计算统计率（每次更新后都要计算）
        if task_data["total"] > 0:
            task_data["success_rate"] = task_data["success"] / task_data["total"]
            task_data["partial_rate"] = task_data.get("partial", 0) / task_data["total"]
            task_data["failure_rate"] = task_data.get("failed", 0) / task_data["total"]
            
            # 计算full_success和partial_success率
            full_success_count = task_data.get("full_success", 0)
            partial_success_count = task_data.get("partial_success", 0)
            task_data["full_success_rate"] = full_success_count / task_data["total"]
            task_data["partial_success_rate"] = partial_success_count / task_data["total"]
            
            # 计算weighted_success_score
            task_data["weighted_success_score"] = (full_success_count * 1.0 + partial_success_count * 0.5) / task_data["total"]
            
            # 计算错误率（基于总错误数，而不是总测试数）
            total = task_data["total"]
            total_errors = task_data.get("total_errors", 0)
            if total_errors > 0:
                task_data["tool_selection_error_rate"] = task_data.get("tool_selection_errors", 0) / total_errors
                task_data["parameter_error_rate"] = task_data.get("parameter_config_errors", 0) / total_errors
                task_data["sequence_error_rate"] = task_data.get("sequence_order_errors", 0) / total_errors
                task_data["dependency_error_rate"] = task_data.get("dependency_errors", 0) / total_errors
                task_data["timeout_error_rate"] = task_data.get("timeout_errors", 0) / total_errors
                task_data["format_error_rate"] = task_data.get("tool_call_format_errors", 0) / total_errors
                task_data["max_turns_error_rate"] = task_data.get("max_turns_errors", 0) / total_errors
                task_data["other_error_rate"] = task_data.get("other_errors", 0) / total_errors
            else:
                # 没有错误时，所有错误率都为0
                task_data["tool_selection_error_rate"] = 0.0
                task_data["parameter_error_rate"] = 0.0
                task_data["sequence_error_rate"] = 0.0
                task_data["dependency_error_rate"] = 0.0
                task_data["timeout_error_rate"] = 0.0
                task_data["format_error_rate"] = 0.0
                task_data["max_turns_error_rate"] = 0.0
                task_data["other_error_rate"] = 0.0
            
            # 计算辅助统计率
            if task_data.get("tests_with_assistance", 0) > 0:
                task_data["assisted_success_rate"] = task_data.get("assisted_success", 0) / task_data["tests_with_assistance"]
                task_data["avg_assisted_turns"] = task_data.get("total_assisted_turns", 0) / task_data["tests_with_assistance"]
            task_data["assistance_rate"] = task_data.get("tests_with_assistance", 0) / total
            
            # 使用增量平均更新执行统计
            n = task_data["total"]
            # 安全获取execution_time和turns
            exec_time = record.get('execution_time', 0) if isinstance(record, dict) else getattr(record, 'execution_time', 0)
            turns = record.get('turns', 0) if isinstance(record, dict) else getattr(record, 'turns', 0)
            task_data["avg_execution_time"] += (exec_time - task_data["avg_execution_time"]) / n
            task_data["avg_turns"] += (turns - task_data["avg_turns"]) / n
            # 处理tool_calls可能是int或list的情况
            tool_calls_count = 0
            # 安全获取tool_calls
            tool_calls = record.get('tool_calls', []) if isinstance(record, dict) else getattr(record, 'tool_calls', [])
            if tool_calls:
                if isinstance(tool_calls, (list, tuple)):
                    tool_calls_count = len(tool_calls)
                elif isinstance(tool_calls, int):
                    tool_calls_count = tool_calls
            task_data["avg_tool_calls"] += (tool_calls_count - task_data["avg_tool_calls"]) / n
            task_data["tool_coverage_rate"] += (test_dict.get("tool_coverage_rate", 0) - task_data["tool_coverage_rate"]) / n
            
            # 更新质量分数
            for score_key in ["workflow_score", "phase2_score", "quality_score", "final_score"]:
                avg_key = f"avg_{score_key}"
                score = test_dict.get(score_key, 0) or 0  # 确保不是None
                current_avg = task_data.get(avg_key, 0) or 0  # 确保不是None
                task_data[avg_key] = current_avg + (score - current_avg) / n
        
        # 更新prompt_type的summary
        self._update_prompt_summary(prompt_data)
    
    def _apply_fallback_error_classification(self, task_data: dict, record):
        """应用fallback分类逻辑"""
        
        # 优先检查format error: 如果工具调用次数为0，很可能是格式错误
        tool_calls = getattr(record, 'tool_calls', [])
        executed_tools = getattr(record, 'executed_tools', [])
        
        # 修复：处理可能是int的情况
        if isinstance(tool_calls, int):
            tool_calls_len = tool_calls
        elif tool_calls:
            tool_calls_len = len(tool_calls)
        else:
            tool_calls_len = 0
        
        if isinstance(executed_tools, int):
            executed_tools_len = executed_tools
        elif executed_tools:
            executed_tools_len = len(executed_tools)
        else:
            executed_tools_len = 0
        
        if tool_calls_len == 0 and executed_tools_len == 0:
            # 没有成功执行任何工具调用，这是典型的format error
            task_data["tool_call_format_errors"] += 1
            return
        
        # 使用传统的错误分类逻辑
        # 安全获取error_message
        error_msg = record.get('error_message', None) if isinstance(record, dict) else getattr(record, 'error_message', None)
        if error_msg:
            error_type = self._classify_error(error_msg)
            if error_type == "timeout":
                task_data["timeout_errors"] += 1
            elif error_type == "format":
                task_data["tool_call_format_errors"] += 1
            elif error_type == "max_turns":
                task_data["max_turns_errors"] += 1
            elif error_type == "tool_selection":
                task_data["tool_selection_errors"] += 1
            elif error_type == "parameter":
                task_data["parameter_config_errors"] += 1
            elif error_type == "sequence":
                task_data["sequence_order_errors"] += 1
            elif error_type == "dependency":
                task_data["dependency_errors"] += 1
            elif error_type in ["other", "tool_level_error", "unknown"]:
                task_data["other_errors"] += 1
        else:
            # 无错误消息但非full_success，检查execution_history中的工具级错误
            execution_history = getattr(record, 'execution_history', [])
            
            if execution_history:
                # 分析execution_history中的失败工具
                failed_tools = []
                for h in execution_history:
                    # 处理不同类型的execution_history条目
                    if hasattr(h, 'success'):
                        # ToolExecutionResult对象
                        if not getattr(h, 'success', True):
                            failed_tools.append(h)
                    elif isinstance(h, dict):
                        # 字典格式
                        if not h.get('success', True):
                            failed_tools.append(h)
                
                if failed_tools:
                    # 有工具执行失败，按最主要的错误类型分类
                    error_types = []
                    for failed in failed_tools:
                        if hasattr(failed, 'error'):
                            error = failed.error or ''
                        else:
                            error = failed.get('error', '')
                        if error:
                            error_types.append(self._classify_error(error))
                    
                    if error_types:
                        # 选择最常见的错误类型
                        from collections import Counter
                        most_common_error = Counter(error_types).most_common(1)[0][0]
                        
                        if most_common_error == "timeout":
                            task_data["timeout_errors"] += 1
                        elif most_common_error == "format":
                            # 再次检查是否确实是格式错误
                            if self._is_confirmed_format_error([most_common_error]):
                                task_data["tool_call_format_errors"] += 1
                            else:
                                # 不确定的格式错误，归类为其他错误
                                task_data["other_errors"] += 1
                        elif most_common_error == "max_turns":
                            task_data["max_turns_errors"] += 1
                        elif most_common_error == "tool_selection":
                            task_data["tool_selection_errors"] += 1
                        elif most_common_error == "parameter":
                            task_data["parameter_config_errors"] += 1
                        elif most_common_error == "sequence":
                            task_data["sequence_order_errors"] += 1
                        elif most_common_error == "dependency":
                            task_data["dependency_errors"] += 1
                        else:
                            task_data["other_errors"] += 1
                    else:
                        # 无法分类的错误，不归为other_errors
                        # task_data["other_errors"] += 1
                        pass  # 跳过未分类的错误
                else:
                    # 没有工具失败，但非full_success，不归为other_errors
                    # task_data["other_errors"] += 1
                    pass  # 跳过未分类的错误
            else:
                # 没有execution_history，无法进一步分析，不归为other_errors
                # task_data["other_errors"] += 1
                pass  # 跳过未分类的错误
    
    def _update_prompt_summary(self, prompt_data):
        """更新prompt_type级别的汇总统计"""
        summary = prompt_data.get("summary", {})
        
        # 初始化summary如果不存在
        if not summary:
            summary = {
                "total": 0,
                "success": 0,
                "success_rate": 0.0,
                "weighted_success_score": 0.0,
                "full_success_rate": 0.0,
                "partial_success_rate": 0.0,
                "failure_rate": 0.0,
                "assisted_failure": 0,
                "assisted_success": 0,
                "total_assisted_turns": 0,
                "tests_with_assistance": 0,
                "avg_assisted_turns": 0.0,
                "assisted_success_rate": 0.0,
                "assistance_rate": 0.0,
                "avg_execution_time": 0.0,
                "avg_turns": 0.0,
                "avg_tool_calls": 0.0,
                "tool_coverage_rate": 0.0,
                "avg_workflow_score": 0.0,
                "avg_phase2_score": 0.0,
                "avg_quality_score": 0.0,
                "avg_final_score": 0.0,
                "total_errors": 0,
                "tool_call_format_errors": 0,
                "timeout_errors": 0,
                "dependency_errors": 0,
                "parameter_config_errors": 0,
                "tool_selection_errors": 0,
                "sequence_order_errors": 0,
                "max_turns_errors": 0,
                "other_errors": 0,
                "tool_selection_error_rate": 0.0,
                "parameter_error_rate": 0.0,
                "sequence_error_rate": 0.0,
                "dependency_error_rate": 0.0,
                "timeout_error_rate": 0.0,
                "format_error_rate": 0.0,
                "max_turns_error_rate": 0.0
            }
        
        # 从所有task_type聚合数据
        total = 0
        success = 0
        full_success = 0
        partial_success = 0
        
        for rate_data in prompt_data.get("by_tool_success_rate", {}).values():
            for diff_data in rate_data.get("by_difficulty", {}).values():
                for task_data in diff_data.get("by_task_type", {}).values():
                    total += task_data.get("total", 0)
                    success += task_data.get("success", 0)
                    full_success += task_data.get("full_success", 0)
                    partial_success += task_data.get("partial_success", 0)
        
        # 更新汇总
        summary["total"] = total
        summary["success"] = success
        if total > 0:
            summary["success_rate"] = success / total
            summary["weighted_success_score"] = (full_success * 1.0 + partial_success * 0.5) / total
            summary["full_success_rate"] = full_success / total
            summary["partial_success_rate"] = partial_success / total
            summary["failure_rate"] = 1.0 - summary["success_rate"]
        
        prompt_data["summary"] = summary
    
    def _classify_error(self, error_msg: str) -> str:
        """Classify error message into specific error type"""
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
        
        # Agent-level timeout (not tool-level timeout)
        if ('test timeout after' in error_lower) or \
           ('timeout after' in error_lower and ('seconds' in error_lower or 'minutes' in error_lower)) or \
           ('agent timeout' in error_lower) or \
           ('execution timeout' in error_lower):
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
        
        # Tool-level errors (not Agent errors) - for statistical completeness
        if any(tool_error in error_lower for tool_error in ['timeout', 'network_error', 'permission_denied', 
                                                           'file_not_found', 'operation_failed', 'resource_error']):
            return 'tool_level_error'
        
        # Other
        return 'other'# 添加辅助方法到文件末尾

    def _is_confirmed_format_error(self, error_types: list) -> bool:
        """确认是否是真正的格式错误"""
        # 这个方法可以根据具体情况进一步优化
        # 目前先返回True保持现有行为，但可以后续改进
        return True
    
    def save_database_enhanced(self):
        """增强的数据库保存方法 - 更强的数据保护，避免卡死"""
        import time
        import os
        
        print(f"[SAVE_ENHANCED] 开始增强保存，时间: {datetime.now().strftime('%H:%M:%S')}")
        
        # 设置保存超时时间，避免无限等待
        MAX_SAVE_TIME = 30  # 30秒超时
        start_time = time.time()
        
        try:
            # 先尝试使用父类的安全保存方法
            if hasattr(self, 'file_lock') and self.file_lock:
                # 有文件锁的情况下，使用非阻塞机制
                print(f"[SAVE_ENHANCED] 使用文件锁机制保存")
                
                def timeout_update_func(current_data):
                    # 检查是否超时
                    if time.time() - start_time > MAX_SAVE_TIME:
                        raise TimeoutError(f"保存操作超时({MAX_SAVE_TIME}秒)")
                    
                    # 智能合并逻辑
                    if current_data and isinstance(current_data, dict):
                        merged_models = self.database.get("models", {}).copy()
                        
                        # 保留磁盘上其他进程写入的数据
                        for model_name, disk_model_data in current_data.get("models", {}).items():
                            if model_name not in merged_models:
                                merged_models[model_name] = disk_model_data
                                print(f"[SAVE_ENHANCED] 保留其他进程的模型数据: {model_name}")
                            else:
                                # 合并prompt_type数据
                                memory_model = merged_models[model_name]
                                if isinstance(memory_model, dict) and isinstance(disk_model_data, dict):
                                    memory_prompts = memory_model.get("by_prompt_type", {})
                                    disk_prompts = disk_model_data.get("by_prompt_type", {})
                                    
                                    # 保留磁盘上的新prompt_type
                                    for prompt_type, disk_prompt_data in disk_prompts.items():
                                        if prompt_type not in memory_prompts:
                                            memory_prompts[prompt_type] = disk_prompt_data
                                            print(f"[SAVE_ENHANCED] 保留{model_name}的新prompt_type: {prompt_type}")
                                    
                                    memory_model["by_prompt_type"] = memory_prompts
                        
                        self.database["models"] = merged_models
                    
                    return self._serialize_database()
                
                # 尝试安全更新
                success = self.file_lock.update_json_safe(timeout_update_func)
                if success:
                    print(f"[SAVE_ENHANCED] 文件锁保存成功")
                    return
                else:
                    print(f"[SAVE_ENHANCED] 文件锁保存失败，使用备用方法")
            
            # 备用保存方法：非阻塞原子写入
            self._save_database_atomic_safe()
            
        except Exception as e:
            print(f"[SAVE_ENHANCED] 保存过程出现异常: {e}")
            # 最后的备用方法：直接调用父类方法
            try:
                super().save_database()
                print(f"[SAVE_ENHANCED] 使用父类备用方法保存成功")
            except Exception as e2:
                print(f"[SAVE_ENHANCED] 所有保存方法都失败: {e2}")
                raise
    
    def _save_database_atomic_safe(self):
        """原子安全保存 - 非阻塞版本"""
        import tempfile
        import shutil
        
        print(f"[ATOMIC_SAFE] 开始原子安全保存")
        
        with self.lock:
            # 更新时间戳
            self.database["last_updated"] = datetime.now().isoformat()
            
            # 如果存在数据库文件，先读取并合并
            if self.db_file.exists():
                try:
                    with open(self.db_file, 'r', encoding='utf-8') as f:
                        disk_data = json.load(f)
                    
                    # 简单的数据合并：保留磁盘上其他进程添加的模型
                    if "models" in disk_data:
                        for model_name, disk_model_data in disk_data["models"].items():
                            if model_name not in self.database.get("models", {}):
                                self.database["models"][model_name] = disk_model_data
                                print(f"[ATOMIC_SAFE] 合并磁盘模型: {model_name}")
                                
                except Exception as e:
                    print(f"[ATOMIC_SAFE] 合并磁盘数据时出错(继续保存): {e}")
            
            # 使用临时文件原子写入
            try:
                # 创建临时文件在同一目录下
                temp_fd, temp_path = tempfile.mkstemp(
                    dir=self.db_file.parent, 
                    suffix='.tmp', 
                    prefix=f'{self.db_file.stem}_'
                )
                
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                    json.dump(self._serialize_database(), f, indent=2, ensure_ascii=False)
                
                # 原子替换
                shutil.move(temp_path, self.db_file)
                print(f"[ATOMIC_SAFE] 原子保存成功")
                
            except Exception as e:
                # 清理临时文件
                try:
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                except:
                    pass
                raise e
