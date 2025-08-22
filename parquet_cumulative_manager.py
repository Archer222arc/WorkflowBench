#!/usr/bin/env python3
"""
基于Parquet的累积测试管理器
替代原有的cumulative_test_manager.py
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import hashlib
import os
from parquet_data_manager import ParquetDataManager, SafeWriteManager

class ParquetCumulativeManager:
    """
    基于Parquet的累积测试管理器
    完全兼容原有接口，但使用Parquet存储
    """
    
    def __init__(self, use_ai_classification=False, db_suffix=''):
        """
        初始化管理器
        
        Args:
            use_ai_classification: 是否使用AI分类（为了兼容，忽略此参数）
            db_suffix: 数据库后缀（为了兼容，忽略此参数）
        """
        self.manager = ParquetDataManager()
        self.safe_writer = SafeWriteManager(self.manager)
        
        # 兼容性属性
        self.use_ai_classification = use_ai_classification
        self.db_suffix = db_suffix
        
        # 恢复未完成的事务
        recovered = self.safe_writer.recover_transactions()
        if recovered > 0:
            print(f"[INFO] 恢复了 {recovered} 条未完成的记录")
    
    def normalize_model_name(self, model_name: str) -> str:
        """
        规范化模型名称（与原系统保持一致）
        包括处理并行实例（-2, -3等后缀）
        更宽松的匹配策略，兼容大小写差异
        """
        import re
        
        # 保存原始名称用于调试
        original_name = model_name
        model_name_lower = model_name.lower()
        
        # 首先处理并行实例后缀（-2, -3等）
        # 只对DeepSeek、Llama、Grok等已知使用并行实例的模型去除后缀
        if any(base in model_name_lower for base in ['deepseek', 'llama', 'grok']):
            # 移除 -数字 后缀
            model_name_cleaned = re.sub(r'-\d+$', '', model_name)
            model_name_lower = model_name_cleaned.lower()
        else:
            model_name_cleaned = model_name
        
        # DeepSeek V3 系列 - 更宽松的匹配
        if any(pattern in model_name_lower for pattern in ['deepseek-v3', 'deepseek_v3', 'deepseekv3']):
            if original_name != 'DeepSeek-V3-0324':
                print(f"[PARQUET_NORMALIZE] Normalizing '{original_name}' -> 'DeepSeek-V3-0324'")
            return 'DeepSeek-V3-0324'
        
        # DeepSeek R1 系列 - 更宽松的匹配
        if any(pattern in model_name_lower for pattern in ['deepseek-r1', 'deepseek_r1', 'deepseekr1']):
            if original_name != 'DeepSeek-R1-0528':
                print(f"[PARQUET_NORMALIZE] Normalizing '{original_name}' -> 'DeepSeek-R1-0528'")
            return 'DeepSeek-R1-0528'
        
        # Llama 3.3 系列 - 更宽松的匹配
        if any(pattern in model_name_lower for pattern in ['llama-3.3', 'llama_3.3', 'llama3.3', 'llama-3-3']):
            if original_name != 'Llama-3.3-70B-Instruct':
                print(f"[PARQUET_NORMALIZE] Normalizing '{original_name}' -> 'Llama-3.3-70B-Instruct'")
            return 'Llama-3.3-70B-Instruct'
        
        # Grok 系列
        if 'grok-3' in model_name_lower or 'grok_3' in model_name_lower:
            return 'grok-3'
        
        # Qwen 系列（不去除后缀，因为它们是不同的模型）
        if 'qwen' in model_name_lower:
            if '72b' in model_name_lower:
                return 'qwen2.5-72b-instruct'
            elif '32b' in model_name_lower:
                return 'qwen2.5-32b-instruct'
            elif '14b' in model_name_lower:
                return 'qwen2.5-14b-instruct'
            elif '7b' in model_name_lower:
                return 'qwen2.5-7b-instruct'
            elif '3b' in model_name_lower:
                return 'qwen2.5-3b-instruct'
        
        return model_name_cleaned
    
    def add_test_result(self, 
                       model: str,
                       task_type: str,
                       prompt_type: str,
                       success: bool,
                       execution_time: float = 0.0,
                       difficulty: str = "easy",
                       tool_success_rate: float = 0.8,
                       partial_success: bool = False,
                       error_message: Optional[str] = None,
                       turns: int = 0,
                       tool_calls: List = None,
                       **kwargs) -> bool:
        """
        添加测试结果（兼容原接口）
        """
        # 规范化模型名
        model = self.normalize_model_name(model)
        
        # 构建测试记录
        test_record = {
            # 基本信息
            'model': model,
            'task_type': task_type,
            'prompt_type': prompt_type,
            'difficulty': difficulty,
            'tool_success_rate': tool_success_rate,
            
            # 测试结果
            'success': success,
            'partial_success': partial_success,
            'execution_time': execution_time,
            'error_message': error_message,
            
            # 执行细节
            'turns': turns,
            'tool_calls': len(tool_calls) if tool_calls else 0,
            
            # 元数据
            'timestamp': datetime.now().isoformat(),
            'test_id': self._generate_test_id(model, task_type, prompt_type),
            
            # 额外参数
            **kwargs
        }
        
        # 追加到Parquet（增量写入，不会覆盖）
        return self.manager.append_test_result(test_record)
    
    def batch_add_results(self, results: List[Dict]) -> bool:
        """
        批量添加测试结果
        """
        # 规范化所有模型名
        for result in results:
            if 'model' in result:
                result['model'] = self.normalize_model_name(result['model'])
            
            # 添加默认值
            result.setdefault('difficulty', 'easy')
            result.setdefault('tool_success_rate', 0.8)
            result.setdefault('timestamp', datetime.now().isoformat())
            result.setdefault('test_id', self._generate_test_id(
                result.get('model', ''),
                result.get('task_type', ''),
                result.get('prompt_type', '')
            ))
        
        # 批量写入
        return self.manager.batch_append_results(results)
    
    def get_model_stats(self, model: str = None) -> Dict:
        """
        获取模型统计（兼容原接口）
        """
        model = self.normalize_model_name(model) if model else None
        df = self.manager.query_model_stats(model_name=model)
        return self.manager.compute_statistics(df)
    
    def get_statistics_by_hierarchy(self, 
                                   model: str,
                                   prompt_type: str = None,
                                   tool_rate: float = None,
                                   difficulty: str = None,
                                   task_type: str = None) -> Dict:
        """
        按层次获取统计数据（兼容原接口）
        """
        model = self.normalize_model_name(model)
        
        # 查询数据
        df = self.manager.query_model_stats(
            model_name=model,
            prompt_type=prompt_type,
            tool_success_rate=tool_rate
        )
        
        # 进一步过滤
        if difficulty:
            df = df[df['difficulty'] == difficulty]
        if task_type:
            df = df[df['task_type'] == task_type]
        
        # 返回统计
        return self.manager.compute_statistics(df)
    
    def check_progress(self, model: str, target_count: int = 100) -> Dict:
        """
        检查测试进度（兼容原接口）
        """
        model = self.normalize_model_name(model)
        stats = self.get_model_stats(model)
        
        current = stats.get('total_tests', 0)
        return {
            'model': model,
            'current': current,
            'target': target_count,
            'completion_rate': (current / target_count * 100) if target_count > 0 else 0,
            'remaining': max(0, target_count - current)
        }
    
    def is_test_completed(self, 
                         model: str,
                         task_type: str,
                         prompt_type: str,
                         difficulty: str = "easy",
                         tool_success_rate: float = 0.8) -> bool:
        """
        检查特定测试是否已完成（兼容原接口）
        """
        model = self.normalize_model_name(model)
        
        # 查询是否存在
        df = self.manager.query_model_stats(
            model_name=model,
            prompt_type=prompt_type,
            tool_success_rate=tool_success_rate
        )
        
        if not df.empty:
            df = df[(df['difficulty'] == difficulty) & (df['task_type'] == task_type)]
            return not df.empty
        
        return False
    
    def _flush_buffer(self):
        """
        刷新缓冲区（兼容enhanced_cumulative_manager接口）
        被smart_batch_runner在批次结束时调用
        """
        # 刷新所有缓存的汇总到磁盘
        if hasattr(self, '_summary_cache') and self._summary_cache:
            self._flush_summary_to_disk()  # 刷新所有
            print(f"[INFO] 已将 {len(self._summary_cache)} 个汇总写入Parquet")
            self._summary_cache.clear()  # 清空缓存
        return True
    
    def finalize(self):
        """
        完成并刷新所有缓冲数据（兼容原接口）
        """
        # 刷新待写入数据
        self.safe_writer.flush_pending_writes()
        
        # 合并增量数据
        self.manager.consolidate_incremental_data()
        
        print("[INFO] 数据已同步到Parquet存储")
    
    def export_to_json(self, output_path: Path = None):
        """
        导出为JSON格式（用于兼容性）
        """
        output_path = output_path or Path("pilot_bench_cumulative_results/master_database.json")
        return self.manager.export_to_json(output_path)
    
    def add_test_result_with_classification(self, record) -> bool:
        """
        从TestRecord对象提取数据
        但不保存单个记录，而是更新或创建汇总
        """
        try:
            # 提取关键信息用于查找对应的汇总
            model = self.normalize_model_name(record.model)
            task_type = record.task_type
            prompt_type = record.prompt_type
            difficulty = getattr(record, 'difficulty', 'easy')
            tool_success_rate = getattr(record, 'tool_success_rate', 0.8)
            
            # 创建组合键
            key = f"{model}|{prompt_type}|{tool_success_rate}|{difficulty}|{task_type}"
            
            # 检查是否已有该组的汇总
            if not hasattr(self, '_summary_cache'):
                self._summary_cache = {}
            
            if key not in self._summary_cache:
                # 初始化新的汇总
                self._summary_cache[key] = {
                    'model': model,
                    'prompt_type': prompt_type,
                    'tool_success_rate': tool_success_rate,
                    'difficulty': difficulty,
                    'task_type': task_type,
                    # 计数器
                    'total': 0,
                    'success': 0,
                    'full_success': 0,
                    'partial_success': 0,
                    'partial': 0,
                    'failed': 0,
                    # 累加器（用于计算平均值）
                    '_total_execution_time': 0,
                    '_total_turns': 0,
                    '_total_tool_calls': 0,
                    '_total_tool_coverage': 0,
                    '_total_workflow_score': 0,
                    '_total_phase2_score': 0,
                    '_total_quality_score': 0,
                    '_total_final_score': 0,
                    # 错误计数
                    'total_errors': 0,
                    'tool_call_format_errors': 0,
                    'timeout_errors': 0,
                    'dependency_errors': 0,
                    'parameter_config_errors': 0,
                    'tool_selection_errors': 0,
                    'sequence_order_errors': 0,
                    'max_turns_errors': 0,
                    'other_errors': 0,
                    # 辅助统计
                    'assisted_failure': 0,
                    'assisted_success': 0,
                    'total_assisted_turns': 0,
                    'tests_with_assistance': 0,
                }
            
            # 更新汇总
            summary = self._summary_cache[key]
            summary['total'] += 1
            
            # 判断成功级别
            success_level = getattr(record, 'success_level', None)
            if success_level is None:
                # 如果没有success_level，根据success和partial_success判断
                if record.success:
                    if getattr(record, 'partial_success', False):
                        success_level = 'partial_success'
                    else:
                        success_level = 'full_success'
                elif getattr(record, 'partial_success', False):
                    success_level = 'partial_success'
                else:
                    success_level = 'failure'
            
            # 根据成功级别更新计数（互斥关系）
            if success_level == "full_success":
                summary['success'] += 1
                summary['full_success'] += 1
            elif success_level == "partial_success":
                summary['partial_success'] += 1
                summary['partial'] = summary.get('partial', 0) + 1
                # 注意：partial_success不计入success
            else:  # failure
                summary['failed'] = summary.get('failed', 0) + 1
            
            # 累加用于平均值的数据
            if hasattr(record, 'execution_time') and record.execution_time:
                summary['_total_execution_time'] += record.execution_time
            if hasattr(record, 'turns') and record.turns:
                summary['_total_turns'] += record.turns
            if hasattr(record, 'tool_calls'):
                tool_calls = record.tool_calls
                if isinstance(tool_calls, list):
                    tool_calls = len(tool_calls)
                if tool_calls:
                    summary['_total_tool_calls'] += tool_calls
            
            # 工具覆盖率
            if hasattr(record, 'tool_coverage_rate') and record.tool_coverage_rate:
                summary['_total_tool_coverage'] += record.tool_coverage_rate
            elif hasattr(record, 'required_tools') and hasattr(record, 'executed_tools'):
                req = record.required_tools
                exec = record.executed_tools
                if req and isinstance(req, list):
                    coverage = len(set(req) & set(exec)) / len(req) if exec else 0
                    summary['_total_tool_coverage'] += coverage
            
            # 分数
            if hasattr(record, 'workflow_score') and record.workflow_score:
                summary['_total_workflow_score'] += record.workflow_score
            if hasattr(record, 'phase2_score') and record.phase2_score:
                summary['_total_phase2_score'] += record.phase2_score
            if hasattr(record, 'quality_score') and record.quality_score:
                summary['_total_quality_score'] += record.quality_score
            if hasattr(record, 'final_score') and record.final_score:
                summary['_total_final_score'] += record.final_score
            
            # 错误统计（与enhanced一致：非full_success都算错误）
            # success_level已在前面判断过，直接使用
            # 只要不是full_success，就有错误
            if success_level != 'full_success':
                summary['total_errors'] += 1
                print(f"[PARQUET_DEBUG] Processing error for {record.model}, success_level={success_level}")
                print(f"[PARQUET_DEBUG] Record has ai_error_category: {hasattr(record, 'ai_error_category')}")
                print(f"[PARQUET_DEBUG] Record attributes: {[attr for attr in dir(record) if not attr.startswith('_')]}")
                if hasattr(record, 'ai_error_category'):
                    print(f"[PARQUET_DEBUG] ai_error_category value: {getattr(record, 'ai_error_category', None)}")
                else:
                    print(f"[PARQUET_DEBUG] WARNING: No ai_error_category in record for {success_level} test!")
                
                # 尝试分类错误
                error_type = None
                
                # 1. 优先使用AI分类（如果存在）
                if hasattr(record, 'ai_error_category') and record.ai_error_category:
                    error_type = record.ai_error_category
                    print(f"[PARQUET_DEBUG] Found ai_error_category: {error_type}")
                elif hasattr(record, 'error_type') and record.error_type:
                    error_type = record.error_type
                    print(f"[PARQUET_DEBUG] Found error_type: {error_type}")
                elif hasattr(record, 'error_classification') and record.error_classification:
                    error_type = record.error_classification
                    print(f"[PARQUET_DEBUG] Found error_classification: {error_type}")
                
                # 2. 如果没有AI分类，检查是否是格式错误（工具调用为0）
                if not error_type:
                    tool_calls = getattr(record, 'tool_calls', 0)
                    executed_tools = getattr(record, 'executed_tools', [])
                    
                    # 处理tool_calls可能是int或list的情况
                    if isinstance(tool_calls, list):
                        tool_calls_count = len(tool_calls)
                    else:
                        tool_calls_count = tool_calls if tool_calls else 0
                    
                    if isinstance(executed_tools, list):
                        executed_tools_count = len(executed_tools)
                    else:
                        executed_tools_count = executed_tools if executed_tools else 0
                    
                    # 如果没有任何工具调用，可能是格式错误
                    if tool_calls_count == 0 and executed_tools_count == 0:
                        error_msg = getattr(record, 'error_message', '')
                        if error_msg:
                            error_lower = error_msg.lower()
                            format_indicators = [
                                'format errors detected', 'format recognition issue',
                                'tool call format', 'understand tool call format',
                                'invalid json', 'malformed', 'parse error'
                            ]
                            if any(indicator in error_lower for indicator in format_indicators):
                                error_type = 'format'
                        # 如果没有error_message但工具调用为0，也可能是格式问题
                        if not error_type and success_level == 'failure':
                            error_type = 'format'  # 默认认为是格式错误
                
                # 3. 如果还没有分类，尝试从error_message分析
                if not error_type and hasattr(record, 'error_message') and record.error_message:
                    # 分析error_message
                    error_type = self._classify_error_message(record.error_message)
                
                # 3. 根据错误类型更新统计 - 使用模糊匹配
                if error_type:
                    # 检查是否已经是标准错误类型（以_errors结尾）
                    standard_error_types = [
                        'timeout_errors', 'tool_selection_errors', 'parameter_config_errors',
                        'sequence_order_errors', 'dependency_errors', 'tool_call_format_errors',
                        'max_turns_errors', 'other_errors'
                    ]
                    
                    if error_type in standard_error_types:
                        # 如果已经是标准错误类型，直接使用
                        summary[error_type] += 1
                        print(f"[PARQUET_DEBUG] Direct match for standard error type '{error_type}', count now: {summary[error_type]}")
                    else:
                        # 导入模糊匹配器
                        try:
                            from fuzzy_error_matcher import FuzzyErrorMatcher
                            
                            # 使用模糊匹配，阈值设为0.6以提高容错性
                            matched_error = FuzzyErrorMatcher.match_error_category(error_type, threshold=0.6)
                            
                            if matched_error:
                                # 更新对应的错误计数
                                summary[matched_error] += 1
                                print(f"[PARQUET_DEBUG] Fuzzy matched '{error_type}' -> {matched_error}, count now: {summary[matched_error]}")
                            else:
                                # 如果模糊匹配也失败，尝试从文本中提取
                                extracted_error = FuzzyErrorMatcher.extract_error_from_text(error_type)
                                if extracted_error:
                                    summary[extracted_error] += 1
                                    print(f"[PARQUET_DEBUG] Extracted '{extracted_error}' from '{error_type}', count now: {summary[extracted_error]}")
                                else:
                                    # 只有真正无法识别时才归为other_errors
                                    summary['other_errors'] += 1
                                    print(f"[PARQUET_DEBUG] Unable to match '{error_type}' -> other_errors")
                        except ImportError:
                            # 如果无法导入模糊匹配器，回退到原始的简单匹配
                            error_type = str(error_type).lower()
                            print(f"[PARQUET_DEBUG] Fallback to simple matching for: '{error_type}'")
                            # 原始的简单匹配逻辑
                            if 'timeout' in error_type:
                                summary['timeout_errors'] += 1
                                print(f"[PARQUET_DEBUG] Matched as timeout_errors")
                            elif 'dependency' in error_type:
                                summary['dependency_errors'] += 1
                                print(f"[PARQUET_DEBUG] Matched as dependency_errors")
                            elif 'parameter' in error_type or 'parameter_config' in error_type or 'param' in error_type:
                                summary['parameter_config_errors'] += 1
                                print(f"[PARQUET_DEBUG] Matched as parameter_config_errors, count now: {summary['parameter_config_errors']}")
                            elif 'tool_selection' in error_type or 'tool_select' in error_type or 'wrong_tool' in error_type:
                                summary['tool_selection_errors'] += 1
                                print(f"[PARQUET_DEBUG] Matched as tool_selection_errors, count now: {summary['tool_selection_errors']}")
                            elif 'sequence' in error_type or 'sequence_order' in error_type or 'order' in error_type:
                                summary['sequence_order_errors'] += 1
                                print(f"[PARQUET_DEBUG] Matched as sequence_order_errors, count now: {summary['sequence_order_errors']}")
                            elif 'max_turns' in error_type or 'turn_limit' in error_type or 'too_many' in error_type:
                                summary['max_turns_errors'] += 1
                                print(f"[PARQUET_DEBUG] Matched as max_turns_errors, count now: {summary['max_turns_errors']}")
                            elif 'format' in error_type or 'tool_call_format' in error_type or 'malformed' in error_type:
                                summary['tool_call_format_errors'] += 1
                                print(f"[PARQUET_DEBUG] Matched as tool_call_format_errors, count now: {summary['tool_call_format_errors']}")
                            else:
                                # 只有当有明确的错误类型但无法匹配时，才归为other_errors
                                summary['other_errors'] += 1
                                print(f"[PARQUET_DEBUG] Unknown error_type '{error_type}' -> other_errors")
                else:
                    # 如果没有错误分类，说明错误没有被AI分类器分析
                    # 这种情况不应该归为other_errors，而是表示"未分类的错误"
                    # 我们可以跳过，或者记录到一个特殊的"unclassified_errors"字段
                    print(f"[PARQUET_DEBUG] No error classification available, skipping error categorization")
            # 辅助统计（与enhanced一致）
            format_error_count = getattr(record, 'format_error_count', 0)
            if format_error_count > 0:
                summary['tests_with_assistance'] += 1
                summary['total_assisted_turns'] += format_error_count
                if record.success:
                    summary['assisted_success'] += 1
                else:
                    summary['assisted_failure'] += 1
            elif hasattr(record, 'assisted') and record.assisted:
                summary['tests_with_assistance'] += 1
                if record.success:
                    summary['assisted_success'] += 1
                else:
                    summary['assisted_failure'] += 1
                if hasattr(record, 'assisted_turns'):
                    summary['total_assisted_turns'] += record.assisted_turns
            
            # 每N次更新后刷新到磁盘
            if summary['total'] % 10 == 0:
                self._flush_summary_to_disk(key)
            
            return True
            
        except Exception as e:
            print(f"[ERROR] add_test_result_with_classification失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _flush_summary_to_disk(self, key: str = None):
        """
        将缓存的汇总数据写入Parquet文件
        """
        if not hasattr(self, '_summary_cache') or not self._summary_cache:
            return
        
        keys_to_flush = [key] if key else list(self._summary_cache.keys())
        
        for k in keys_to_flush:
            if k not in self._summary_cache:
                continue
                
            summary = self._summary_cache[k].copy()
            
            # 计算率和平均值
            total = summary['total']
            if total > 0:
                # 成功率
                summary['success_rate'] = summary['success'] / total
                summary['full_success_rate'] = summary['full_success'] / total
                summary['partial_success_rate'] = summary['partial_success'] / total
                summary['failure_rate'] = 1 - summary['success_rate'] - summary['partial_success_rate']
                summary['weighted_success_score'] = (summary['full_success'] + 0.5 * summary['partial_success']) / total
                
                # 添加兼容性字段（与JSON保持一致）
                summary['successful'] = summary['success']  # successful是success的别名
                summary['partial'] = summary.get('partial', summary['partial_success'])  # partial是partial_success的别名
                # failed字段已经在add_test_result_with_classification中正确设置，不需要重新计算
                # 保持failed的值不变，避免出现负数
                summary['partial_rate'] = summary['partial_success_rate']  # partial_rate是partial_success_rate的别名
                
                # 计算平均值（简单平均，与enhanced最终效果一致）
                summary['avg_execution_time'] = summary['_total_execution_time'] / total if '_total_execution_time' in summary else 0
                summary['avg_turns'] = summary['_total_turns'] / total if '_total_turns' in summary else 0
                summary['avg_tool_calls'] = summary['_total_tool_calls'] / total if '_total_tool_calls' in summary else 0
                summary['tool_coverage_rate'] = summary['_total_tool_coverage'] / total if '_total_tool_coverage' in summary else 0
                summary['avg_workflow_score'] = summary['_total_workflow_score'] / total if '_total_workflow_score' in summary else 0
                summary['avg_phase2_score'] = summary['_total_phase2_score'] / total if '_total_phase2_score' in summary else 0
                summary['avg_quality_score'] = summary['_total_quality_score'] / total if '_total_quality_score' in summary else 0
                summary['avg_final_score'] = summary['_total_final_score'] / total if '_total_final_score' in summary else 0
                
                # 错误率（基于总错误数，与enhanced一致）
                total_errors = summary.get('total_errors', 0)
                
                # Debug: 打印错误统计信息
                if total_errors > 0:
                    print(f"[FLUSH_DEBUG] Summary for {summary.get('model')}-{summary.get('task_type')}:")
                    print(f"  total_errors={total_errors}")
                    print(f"  sequence_order_errors={summary.get('sequence_order_errors', 0)}")
                    print(f"  dependency_errors={summary.get('dependency_errors', 0)}")
                    print(f"  tool_selection_errors={summary.get('tool_selection_errors', 0)}")
                    print(f"  parameter_config_errors={summary.get('parameter_config_errors', 0)}")
                    print(f"  other_errors={summary.get('other_errors', 0)}")
                
                if total_errors > 0:
                    summary['tool_selection_error_rate'] = summary.get('tool_selection_errors', 0) / total_errors
                    summary['parameter_error_rate'] = summary.get('parameter_config_errors', 0) / total_errors
                    summary['sequence_error_rate'] = summary.get('sequence_order_errors', 0) / total_errors
                    summary['dependency_error_rate'] = summary.get('dependency_errors', 0) / total_errors
                    summary['timeout_error_rate'] = summary.get('timeout_errors', 0) / total_errors
                    summary['format_error_rate'] = summary.get('tool_call_format_errors', 0) / total_errors
                    summary['max_turns_error_rate'] = summary.get('max_turns_errors', 0) / total_errors
                    summary['other_error_rate'] = summary.get('other_errors', 0) / total_errors
                else:
                    # 没有错误时，所有错误率都为0
                    summary['tool_selection_error_rate'] = 0.0
                    summary['parameter_error_rate'] = 0.0
                    summary['sequence_error_rate'] = 0.0
                    summary['dependency_error_rate'] = 0.0
                    summary['timeout_error_rate'] = 0.0
                    summary['format_error_rate'] = 0.0
                    summary['max_turns_error_rate'] = 0.0
                    summary['other_error_rate'] = 0.0
                
                # 辅助统计率（与enhanced一致）
                tests_with_assist = summary.get('tests_with_assistance', 0)
                if tests_with_assist > 0:
                    summary['assisted_success_rate'] = summary.get('assisted_success', 0) / tests_with_assist
                    summary['avg_assisted_turns'] = summary.get('total_assisted_turns', 0) / tests_with_assist
                else:
                    summary['assisted_success_rate'] = 0.0
                    summary['avg_assisted_turns'] = 0.0
                summary['assistance_rate'] = tests_with_assist / total
            
            # 移除内部累加器字段
            for field in list(summary.keys()):
                if field.startswith('_'):
                    del summary[field]
            
            # Debug: 检查写入前的数据
            if summary.get('total_errors', 0) > 0:
                print(f"[WRITE_DEBUG] Before writing to Parquet for {summary.get('model')}-{summary.get('task_type')}:")
                print(f"  sequence_order_errors={summary.get('sequence_order_errors', 0)}")
                print(f"  dependency_errors={summary.get('dependency_errors', 0)}")
                print(f"  other_errors={summary.get('other_errors', 0)}")
            
            # 写入Parquet
            self.manager.append_summary_record(summary)
    
    def _generate_test_id(self, model: str, task_type: str, prompt_type: str) -> str:
        """生成测试ID"""
        content = f"{model}_{task_type}_{prompt_type}_{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def get_runtime_summary(self) -> Dict:
        """Get current runtime statistics summary
        
        兼容EnhancedCumulativeManager的接口
        返回运行时统计摘要
        """
        # ParquetCumulativeManager不跟踪运行时错误统计
        # 返回空的统计结构以保持兼容性
        return {}
    
    def save_database(self):
        """Save database (compatibility method)
        
        ParquetCumulativeManager自动保存，无需显式调用
        但保留此方法以保持兼容性
        """
        # 刷新缓冲区以确保数据已保存
        self._flush_buffer()
        return True
    
    def get_progress_report(self, model: str) -> Dict:
        """Get progress report for a model
        
        兼容EnhancedCumulativeManager的接口
        返回模型的进度报告
        """
        # 查询该模型的所有汇总数据
        model = self.normalize_model_name(model)
        df = self.manager.query_model_stats(model_name=model)
        
        if df.empty:
            return {
                "model": model,
                "total_tests": 0,
                "completed": 0,
                "progress": "0%"
            }
        
        # 计算总测试数（所有汇总记录的total字段之和）
        total_tests = df['total'].sum() if 'total' in df.columns else 0
        
        return {
            "model": model,
            "total_tests": int(total_tests),
            "completed": int(total_tests),  # 对于汇总数据，completed等于total
            "progress": "100%" if total_tests > 0 else "0%"
        }
    
    def _classify_error_message(self, error_message: str) -> str:
        """
        分析错误消息进行分类（与enhanced一致）
        """
        if not error_message:
            return 'unknown'
        
        error_lower = error_message.lower()
        
        # Format errors
        if any(x in error_lower for x in ['format errors detected', 'format recognition issue', 
                                          'tool call format', 'understand tool call format',
                                          'invalid json', 'malformed', 'parse error']):
            return 'format'
        
        # Max turns without tool calls (also format)
        if ('no tool calls' in error_lower and 'turns' in error_lower) or \
           ('max turns reached' in error_lower and 'no tool calls' in error_lower):
            return 'format'
        
        # Pure max turns
        if 'max turns reached' in error_lower:
            return 'max_turns'
        
        # Agent-level timeout
        if ('test timeout after' in error_lower) or \
           ('timeout after' in error_lower and ('seconds' in error_lower or 'minutes' in error_lower)):
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
        if any(x in error_lower for x in ['dependency', 'prerequisite', 'missing requirement']):
            return 'dependency'
        
        return 'other'


# 全局实例（兼容原有代码）
_global_manager = None

def get_manager():
    """获取全局管理器实例"""
    global _global_manager
    if _global_manager is None:
        _global_manager = ParquetCumulativeManager()
    return _global_manager

# 兼容原有的函数接口
def add_test_result(**kwargs):
    """添加测试结果（兼容原接口）"""
    return get_manager().add_test_result(**kwargs)

def check_progress(model: str, target_count: int = 100):
    """检查进度（兼容原接口）"""
    return get_manager().check_progress(model, target_count)

def is_test_completed(**kwargs):
    """检查测试是否完成（兼容原接口）"""
    return get_manager().is_test_completed(**kwargs)

def finalize():
    """完成数据同步（兼容原接口）"""
    return get_manager().finalize()


if __name__ == "__main__":
    # 测试代码
    print("Parquet累积管理器测试")
    print("="*60)
    
    manager = ParquetCumulativeManager()
    
    # 测试添加数据
    print("\n1. 测试添加单条记录...")
    success = manager.add_test_result(
        model="gpt-4o-mini",
        task_type="simple_task",
        prompt_type="baseline",
        success=True,
        execution_time=2.5,
        difficulty="easy",
        tool_success_rate=0.8
    )
    print(f"  结果: {'✅ 成功' if success else '❌ 失败'}")
    
    # 测试批量添加
    print("\n2. 测试批量添加...")
    results = [
        {
            'model': 'deepseek-v3-0324-2',  # 测试规范化
            'task_type': 'complex_task',
            'prompt_type': 'cot',
            'success': True,
            'execution_time': 5.0
        },
        {
            'model': 'qwen2.5-72b-instruct',
            'task_type': 'simple_task',
            'prompt_type': 'baseline',
            'success': False,
            'execution_time': 3.0
        }
    ]
    success = manager.batch_add_results(results)
    print(f"  结果: {'✅ 成功' if success else '❌ 失败'}")
    
    # 测试查询
    print("\n3. 测试查询统计...")
    stats = manager.get_model_stats('DeepSeek-V3-0324')  # 应该包含规范化后的数据
    print(f"  DeepSeek-V3-0324 统计:")
    print(f"    总测试数: {stats.get('total_tests', 0)}")
    print(f"    成功率: {stats.get('success_rate', 0):.2%}")
    
    # 测试进度检查
    print("\n4. 测试进度检查...")
    progress = manager.check_progress('gpt-4o-mini', target_count=100)
    print(f"  gpt-4o-mini 进度:")
    print(f"    当前: {progress['current']}/{progress['target']}")
    print(f"    完成率: {progress['completion_rate']:.1f}%")
    
    # 测试数据同步
    print("\n5. 测试数据同步...")
    manager.finalize()
    print("  ✅ 数据已同步")
    
    print("\n✅ 所有测试完成！")