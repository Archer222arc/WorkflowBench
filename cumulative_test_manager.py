#!/usr/bin/env python3
"""
PILOT-Bench 累积测试管理系统
支持任意方式的测试，所有结果自动累积
只保存统计数据，不保存实例细节
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from old_data_structures.cumulative_data_structure import ModelStatistics

from dataclasses import dataclass, asdict, field
import hashlib
from threading import Lock
try:
    from file_lock_manager import get_file_lock
    FILE_LOCK_AVAILABLE = True
except ImportError:
    FILE_LOCK_AVAILABLE = False

# 使用纯字典结构，不再导入数据结构类
# V3版本：所有数据都是字典格式，直接操作

# 累积结果存储路径
CUMULATIVE_DB_PATH = Path("pilot_bench_cumulative_results")
CUMULATIVE_DB_PATH.mkdir(exist_ok=True)

def normalize_model_name(model_name: str) -> str:
    """
    规范化模型名称，将同一模型的不同实例映射到主名称
    例如：deepseek-v3-0324-2 -> DeepSeek-V3-0324
    包括处理并行实例（-2, -3等后缀）
    """
    import re
    model_name_lower = model_name.lower()
    
    # 首先处理并行实例后缀（-2, -3等）
    # 只对DeepSeek、Llama、Grok等已知使用并行实例的模型去除后缀
    if any(base in model_name_lower for base in ['deepseek', 'llama', 'grok']):
        # 移除 -数字 后缀
        model_name_cleaned = re.sub(r'-\d+$', '', model_name)
        model_name_lower = model_name_cleaned.lower()
    else:
        model_name_cleaned = model_name
    
    # DeepSeek V3 系列
    if 'deepseek-v3' in model_name_lower or 'deepseek_v3' in model_name_lower:
        return 'DeepSeek-V3-0324'
    
    # DeepSeek R1 系列
    if 'deepseek-r1' in model_name_lower or 'deepseek_r1' in model_name_lower:
        return 'DeepSeek-R1-0528'
    
    # Llama 3.3 系列
    if 'llama-3.3' in model_name_lower or 'llama_3.3' in model_name_lower:
        return 'Llama-3.3-70B-Instruct'
    
    # Grok 系列
    if 'grok-3' in model_name_lower or 'grok_3' in model_name_lower:
        return 'grok-3'
    
    # Qwen 系列 - 根据参数规模确定具体模型（不去除后缀）
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
    
    # 其他模型返回清理后的名称
    return model_name_cleaned

@dataclass
class TestRecord:
    """单个测试记录"""
    # 基本信息
    model: str
    task_type: str
    prompt_type: str
    difficulty: str = "easy"
    
    # 测试结果
    success: bool = False
    partial_success: bool = False
    execution_time: float = 0.0
    error_message: Optional[str] = None
    
    # 错误分类信息
    format_recognition_errors: int = 0
    instruction_following_errors: int = 0
    tool_selection_errors: int = 0
    parameter_config_errors: int = 0
    sequence_order_errors: int = 0
    dependency_errors: int = 0
    
    # 缺陷信息（如果有）
    is_flawed: bool = False
    flaw_type: Optional[str] = None
    
    # 元数据
    timestamp: str = ""
    task_id: Optional[str] = None
    session_id: Optional[str] = None
    test_instance: int = 0  # 第几次测试
    
    # 执行细节（新增）
    turns: int = 0  # 执行轮数
    tool_calls: List = field(default_factory=list)  # 工具调用列表
    success_level: str = "failure"  # full_success, partial_success, failure
    execution_status: str = "failure"  # 与success_level相同，用于兼容性
    
    # 新增的重要字段
    format_error_count: int = 0  # 格式错误计数
    api_issues: List = field(default_factory=list)  # API层面的问题
    executed_tools: List = field(default_factory=list)  # 实际执行的工具
    required_tools: List = field(default_factory=list)  # 任务要求的工具
    execution_history: List = field(default_factory=list)  # 工具执行历史
    
    # 分数指标（如果有）
    workflow_score: Optional[float] = None
    phase2_score: Optional[float] = None
    quality_score: Optional[float] = None
    final_score: Optional[float] = None
    tool_reliability: float = 0.8  # 工具可靠性设置
    
    def get_key(self) -> str:
        """生成唯一键"""
        parts = [self.model, self.task_type, self.prompt_type, self.difficulty]
        if self.is_flawed and self.flaw_type:
            parts.extend(["flawed", self.flaw_type])
        return "_".join(parts)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)

class CumulativeTestManager:
    """累积测试管理器"""
    
    def __init__(self, db_suffix=''):
        # 支持自定义数据库文件后缀（用于区分闭源/开源模型）
        if db_suffix:
            self.db_file = CUMULATIVE_DB_PATH / f"master_database{db_suffix}.json"
        else:
            self.db_file = CUMULATIVE_DB_PATH / "master_database.json"
        self.lock = Lock()  # 线程锁
        
        # 添加文件锁（如果可用）
        if FILE_LOCK_AVAILABLE:
            self.file_lock = get_file_lock(self.db_file)
        else:
            self.file_lock = None
        self.database = self._load_database()
        
    def _load_database(self) -> Dict:
        """加载数据库"""
        if self.db_file.exists():
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # V3版本：不再反序列化models，保持字典格式
                # 注释掉反序列化以避免创建ModelStatistics对象
                # if "models" in data:
                #     self._deserialize_models(data)
                return data
            except Exception as e:
                # 如果加载失败，创建备份
                backup_file = self.db_file.with_suffix('.backup')
                self.db_file.rename(backup_file)
                print(f"数据库损坏，已备份到: {backup_file}，错误: {e}")
                return self._create_empty_database()
        else:
            return self._create_empty_database()
    
    # V3版本：已移除所有反序列化方法
    # 数据直接以字典格式存储和使用，不再转换为对象
    
    def _create_empty_database(self) -> Dict:
        """创建空数据库 - V3纯字典结构"""
        return {
            "version": "3.0",
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "test_groups": {},  # 保留用于兼容
            "models": {},  # 纯字典格式的模型统计
            "summary": {
                "total_tests": 0,
                "total_success": 0,
                "total_partial": 0,
                "total_failure": 0,
                "models_tested": [],
                "last_test_time": None
            }
        }
    
    def save_database(self):
        """保存数据库（原子操作，支持文件锁）"""
        self.database["last_updated"] = datetime.now().isoformat()
        
        if self.file_lock:
            # 使用文件锁进行多进程安全写入
            def update_func(current_data):
                # 忽略当前数据，直接使用内存中的数据
                return self._serialize_database()
            
            success = self.file_lock.update_json_safe(update_func)
            if not success:
                print("[警告] 使用文件锁保存失败，回退到普通保存")
                self._save_database_fallback()
        else:
            self._save_database_fallback()
    
    def _save_database_fallback(self):
        """回退的保存方法（无文件锁）"""
        with self.lock:
            # 先写入临时文件
            temp_file = self.db_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                # 使用自定义序列化器处理ModelStatistics对象
                json.dump(self._serialize_database(), f, indent=2, ensure_ascii=False)
            
            # 原子替换
            temp_file.replace(self.db_file)
    
    def clear_database(self):
        """清除数据库中的所有记录"""
        # 备份当前数据库（在锁外进行）
        if self.db_file.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.db_file.parent / f"master_database_backup_{timestamp}.json"
            import shutil
            shutil.copy(self.db_file, backup_file)
            print(f"[INFO] 已备份当前数据库到: {backup_file}")
        
        # 创建新的空数据库
        with self.lock:
            self.database = self._create_empty_database()
        
        # 保存数据库（save_database会自己获取锁）
        self.save_database()
        print(f"[INFO] 已清除累积记录数据库")
    
    def add_test_result(self, record: TestRecord) -> bool:
        """添加测试结果 - 只保存统计，不保存实例"""
        with self.lock:
            # 添加时间戳
            if not record.timestamp:
                record.timestamp = datetime.now().isoformat()
            
            # 初始化模型统计（如果需要）
            model = normalize_model_name(record.model)  # 规范化模型名称
            if model not in self.database["models"]:
                # 使用V3字典格式而不是ModelStatistics对象
                self.database["models"][model] = {
                    "model_name": model,
                    "first_test_time": datetime.now().isoformat(),
                    "last_test_time": datetime.now().isoformat(),
                    "total_tests": 0,
                    "overall_stats": {},
                    "by_prompt_type": {}
                }
                # 更新已测试模型列表
                if model not in self.database["summary"]["models_tested"]:
                    self.database["summary"]["models_tested"].append(model)
            
            # 构建测试记录字典
            test_dict = {
                "model": model,  # 使用规范化后的模型名称
                "task_type": record.task_type,
                "prompt_type": record.prompt_type,
                "difficulty": record.difficulty,
                "success": record.success,
                "success_level": self._determine_success_level(record),
                "execution_time": record.execution_time,
                "error_message": record.error_message,
                "is_flawed": record.is_flawed,
                "flaw_type": record.flaw_type,
                "timestamp": record.timestamp,
                "turns": record.turns,
                "tool_calls": record.tool_calls,
                # Scores (if available)
                "workflow_score": record.workflow_score,
                "phase2_score": record.phase2_score,
                "quality_score": record.quality_score,
                "final_score": record.final_score,
                # Tool reliability (default 0.8) - 重要：用于新层次结构
                "tool_reliability": record.tool_reliability,
                # 新增：重要的字段
                "format_error_count": record.format_error_count,
                "api_issues": record.api_issues,
                "executed_tools": record.executed_tools,
                "required_tools": record.required_tools,
                "tool_coverage_rate": getattr(record, 'tool_coverage_rate', 0.0),  # 添加tool_coverage_rate
            }
            
            # 更新模型统计（保持字典格式）
            model_data = self.database["models"][model]
            if isinstance(model_data, dict):
                # V3格式 - 直接更新字典
                model_data["last_test_time"] = datetime.now().isoformat()
                # 注意：这里不更新其他字段，由enhanced_cumulative_manager处理
            else:
                # 旧格式 - ModelStatistics对象
                model_data.update_from_test(test_dict)
            
            # 更新全局摘要
            self._update_global_summary_v2()
            
            # 保持向后兼容性 - 更新旧格式的test_groups（但不存储实例）
            # 如果没有test_groups字段，跳过这部分
            if "test_groups" not in self.database:
                # v2.1版本不需要test_groups
                pass
            else:
                key = record.get_key()
                if key not in self.database["test_groups"]:
                    self.database["test_groups"][key] = {
                    "model": model,  # 使用规范化后的模型名称
                    "task_type": record.task_type,
                    "prompt_type": record.prompt_type,
                    "difficulty": record.difficulty,
                    "is_flawed": record.is_flawed,
                    "flaw_type": record.flaw_type,
                    "statistics": {
                        "total": 0,
                        "success": 0,
                        "partial_success": 0,
                        "failure": 0,
                        "success_rate": 0.0,
                        "avg_execution_time": 0.0
                    },
                    "instances": []  # 空列表 - 不存储实例
                }
            
                # 只更新统计
                group = self.database["test_groups"][key]
                stats = group["statistics"]
                stats["total"] += 1
                if record.success:
                    stats["success"] += 1
                elif record.partial_success:
                    stats["partial_success"] += 1
                else:
                    stats["failure"] = stats["total"] - stats["success"] - stats["partial_success"]
                
                stats["success_rate"] = (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
                
                # 更新平均执行时间
                if record.execution_time > 0:
                    # 使用增量平均值计算
                    n = stats["total"]
                    stats["avg_execution_time"] = ((n - 1) * stats["avg_execution_time"] + record.execution_time) / n
            
            # 自动保存 - 现在使用统一的save_database方法（支持文件锁）
            # 需要在锁外调用save_database，因为save_database内部会获取锁
            pass  # 退出锁后再保存
        
        # 在锁外保存，避免死锁
        self.save_database()
        return True
    
    def _determine_success_level(self, record: TestRecord) -> str:
        """确定成功级别。如果有execution_status，优先使用。"""
        # 优先使用execution_status（来自InteractiveExecutor）
        if record.execution_status and record.execution_status != "failure":
            return record.execution_status
        
        # 退回到旧的逻辑
        if record.success:
            return "full_success"
        elif record.partial_success:
            return "partial_success"
        else:
            return "failure"
    
    def _serialize_database(self) -> Dict:
        """序列化数据库，将数据类转换为字典"""
        result = dict(self.database)
        
        # 序列化models部分
        if "models" in result:
            serialized_models = {}
            for model_name, model_stats in result["models"].items():
                if isinstance(model_stats, dict):
                    # V3版本：已经是字典格式
                    serialized_models[model_name] = model_stats
                elif isinstance(model_stats, dict):
                    # 如果是V2字典，确保它有正确的overall_stats结构
                    if 'overall_stats' not in model_stats:
                        # 从V2字典构建overall_stats
                        model_stats['overall_stats'] = {
                            'total_success': model_stats.get('total_success', 0),
                            'total_partial': 0,  # V2可能没有这个字段
                            'total_full': 0,  # V2可能没有这个字段
                            'total_failure': model_stats.get('total_failure', 0),
                            'success_rate': model_stats.get('overall_success_rate', 0.0),
                            'weighted_success_score': 0.0,  # V2可能没有这个字段
                            'avg_execution_time': model_stats.get('avg_execution_time', 0.0),
                            'avg_turns': 0.0,  # V2可能没有这个字段
                            'tool_coverage_rate': model_stats.get('tool_coverage_rate', 0.0)  # 从V2获取
                        }
                    elif 'tool_coverage_rate' not in model_stats['overall_stats']:
                        # 如果overall_stats存在但缺少tool_coverage_rate，添加它
                        model_stats['overall_stats']['tool_coverage_rate'] = model_stats.get('tool_coverage_rate', 0.0)
                    serialized_models[model_name] = model_stats
                else:
                    serialized_models[model_name] = model_stats
            result["models"] = serialized_models
        
        return result
    
    # V3版本：已移除所有序列化方法
    # 数据直接以字典格式存储和使用
    def _serialize_model_stats_v3(self, stats, use_v2_if_available: bool = True) -> Dict:
        """序列化模型统计对象 - V3版本，支持新层次结构"""
        result = {
            "model_name": stats.model_name,
            "first_test_time": stats.first_test_time,
            "last_test_time": stats.last_test_time,
            "total_tests": stats.overall_success.total_tests,
            "overall_stats": {
                "total_success": stats.overall_success.total_success,
                "total_partial": stats.overall_success.partial_success,
                "total_full": stats.overall_success.full_success,
                "total_failure": stats.overall_success.failure,
                "success_rate": stats.overall_success.success_rate,
                "weighted_success_score": stats.overall_success.weighted_success_score,
                "avg_execution_time": stats.overall_execution.avg_execution_time,
                "avg_turns": stats.overall_execution.avg_turns,
                "tool_coverage_rate": stats.overall_execution.tool_coverage_rate
            },
            "by_prompt_type": {}
        }
        
        # 构建新的层次结构：prompt_type -> tool_success_rate -> difficulty -> task_type
        # 从现有数据中重组 - 这里正确处理多种工具成功率
        by_prompt_type = {}
        
        # 保存所有遇到的tool_reliability值
        if not hasattr(stats, '_tool_rates_by_prompt'):
            stats._tool_rates_by_prompt = {}
        
        # 处理prompt_type统计
        for prompt_type, prompt_stats in stats.by_prompt_type.items():
            if prompt_type not in by_prompt_type:
                by_prompt_type[prompt_type] = {
                    "by_tool_success_rate": {},
                    "summary": self._serialize_prompt_stats({prompt_type: prompt_stats})[prompt_type]
                }
        
        # 处理task_type统计
        for task_type, task_stats in stats.by_task_type.items():
            # 默认放在baseline -> 0.8 -> easy -> task_type
            prompt_type = "baseline"
            tool_rate = "0.8"  # 默认值
            
            if prompt_type not in by_prompt_type:
                by_prompt_type[prompt_type] = {
                    "by_tool_success_rate": {},
                    "summary": {}
                }
            
            if tool_rate not in by_prompt_type[prompt_type]["by_tool_success_rate"]:
                by_prompt_type[prompt_type]["by_tool_success_rate"][tool_rate] = {
                    "by_difficulty": {
                        "easy": {
                            "by_task_type": {}
                        }
                    }
                }
            
            location = by_prompt_type[prompt_type]["by_tool_success_rate"][tool_rate]["by_difficulty"]["easy"]["by_task_type"]
            location[task_type] = self._serialize_task_stats({task_type: task_stats})[task_type]
        
        # 处理flaw_type统计（将其作为flawed_xxx的prompt_type）
        for flaw_type, flaw_stats in stats.by_flaw_type.items():
            prompt_type = f"flawed_{flaw_type}"
            tool_rate = "0.8"  # 默认值
            
            if prompt_type not in by_prompt_type:
                by_prompt_type[prompt_type] = {
                    "by_tool_success_rate": {},
                    "summary": self._serialize_flaw_stats({flaw_type: flaw_stats})[flaw_type]
                }
            
            if tool_rate not in by_prompt_type[prompt_type]["by_tool_success_rate"]:
                by_prompt_type[prompt_type]["by_tool_success_rate"][tool_rate] = {
                    "by_difficulty": {
                        "easy": {
                            "by_task_type": {}
                        }
                    }
                }
        
        result["by_prompt_type"] = by_prompt_type
        
        # 如果有V2数据，优先使用V2数据
        if use_v2_if_available and hasattr(stats, '_v2_data'):
            v2_data = stats._v2_data
            if 'by_prompt_type' in v2_data:
                result['by_prompt_type'] = v2_data['by_prompt_type']
        
        return result
    
    def _serialize_task_stats(self, task_stats: Dict) -> Dict:
        """序列化任务类型统计"""
        result = {}
        for task_type, stats in task_stats.items():
            result[task_type] = {
                "total": stats.success_metrics.total_tests,
                "success": stats.success_metrics.total_success,
                "success_rate": stats.success_metrics.success_rate,
                "weighted_success_score": stats.success_metrics.weighted_success_score,
                "full_success_rate": stats.success_metrics.full_success_rate,
                "partial_success_rate": stats.success_metrics.partial_success_rate,
                "failure_rate": stats.success_metrics.failure_rate,
                # Execution metrics
                "avg_execution_time": stats.execution_metrics.avg_execution_time,
                "avg_turns": stats.execution_metrics.avg_turns,
                "avg_tool_calls": stats.execution_metrics.avg_tool_calls,
                "tool_coverage_rate": stats.execution_metrics.tool_coverage_rate,
                # Score metrics
                "avg_workflow_score": stats.score_metrics.workflow_scores.mean,
                "avg_phase2_score": stats.score_metrics.phase2_scores.mean,
                "avg_quality_score": stats.score_metrics.quality_scores.mean,
                "avg_final_score": stats.score_metrics.final_scores.mean,
                # 完整的错误统计
                "total_errors": stats.error_metrics.total_errors,
                "tool_call_format_errors": stats.error_metrics.tool_call_format_errors,
                "timeout_errors": stats.error_metrics.timeout_errors,
                "dependency_errors": stats.error_metrics.dependency_errors,
                "parameter_config_errors": stats.error_metrics.parameter_config_errors,
                "tool_selection_errors": stats.error_metrics.tool_selection_errors,
                "sequence_order_errors": stats.error_metrics.sequence_order_errors,
                "max_turns_errors": stats.error_metrics.max_turns_errors,
                
                # 完整的错误率
                "tool_selection_error_rate": stats.error_metrics.tool_selection_error_rate,
                "parameter_error_rate": stats.error_metrics.parameter_error_rate,
                "sequence_error_rate": stats.error_metrics.sequence_error_rate,
                "dependency_error_rate": stats.error_metrics.dependency_error_rate,
                "timeout_error_rate": stats.error_metrics.timeout_error_rate,
                "format_error_rate": stats.error_metrics.format_error_rate,
                "max_turns_error_rate": stats.error_metrics.max_turns_error_rate,
                
                # Assisted统计
                "assisted_failure": stats.success_metrics.assisted_failure,
                "assisted_success": stats.success_metrics.assisted_success,
                "total_assisted_turns": stats.success_metrics.total_assisted_turns,
                "tests_with_assistance": stats.success_metrics.tests_with_assistance,
                "avg_assisted_turns": stats.success_metrics.avg_assisted_turns,
                "assisted_success_rate": stats.success_metrics.assisted_success_rate,
                "assistance_rate": stats.success_metrics.assistance_rate
            }
        return result
    
    def _serialize_prompt_stats(self, prompt_stats: Dict) -> Dict:
        """序列化提示类型统计"""
        result = {}
        for prompt_type, stats in prompt_stats.items():
            result[prompt_type] = {
                "total": stats.success_metrics.total_tests,
                "success": stats.success_metrics.total_success,
                "success_rate": stats.success_metrics.success_rate,
                "weighted_success_score": stats.success_metrics.weighted_success_score,
                "full_success_rate": stats.success_metrics.full_success_rate,
                "partial_success_rate": stats.success_metrics.partial_success_rate,
                "failure_rate": stats.success_metrics.failure_rate,
                
                # Assisted统计
                "assisted_failure": stats.success_metrics.assisted_failure,
                "assisted_success": stats.success_metrics.assisted_success,
                "total_assisted_turns": stats.success_metrics.total_assisted_turns,
                "tests_with_assistance": stats.success_metrics.tests_with_assistance,
                "avg_assisted_turns": stats.success_metrics.avg_assisted_turns,
                "assisted_success_rate": stats.success_metrics.assisted_success_rate,
                "assistance_rate": stats.success_metrics.assistance_rate,
                
                # Execution metrics
                "avg_execution_time": stats.execution_metrics.avg_execution_time,
                "avg_turns": stats.execution_metrics.avg_turns,
                "avg_tool_calls": stats.execution_metrics.avg_tool_calls,
                "tool_coverage_rate": stats.execution_metrics.tool_coverage_rate,
                # Score metrics
                "avg_workflow_score": stats.score_metrics.workflow_scores.mean,
                "avg_phase2_score": stats.score_metrics.phase2_scores.mean,
                "avg_quality_score": stats.score_metrics.quality_scores.mean,
                "avg_final_score": stats.score_metrics.final_scores.mean,
                
                # 完整的错误统计（所有7种类型）
                "total_errors": stats.error_metrics.total_errors,
                "tool_call_format_errors": stats.error_metrics.tool_call_format_errors,
                "timeout_errors": stats.error_metrics.timeout_errors,
                "dependency_errors": stats.error_metrics.dependency_errors,
                "parameter_config_errors": stats.error_metrics.parameter_config_errors,
                "tool_selection_errors": stats.error_metrics.tool_selection_errors,
                "sequence_order_errors": stats.error_metrics.sequence_order_errors,
                "max_turns_errors": stats.error_metrics.max_turns_errors,
                
                # 完整的错误率
                "tool_selection_error_rate": stats.error_metrics.tool_selection_error_rate,
                "parameter_error_rate": stats.error_metrics.parameter_error_rate,
                "sequence_error_rate": stats.error_metrics.sequence_error_rate,
                "dependency_error_rate": stats.error_metrics.dependency_error_rate,
                "timeout_error_rate": stats.error_metrics.timeout_error_rate,
                "format_error_rate": stats.error_metrics.format_error_rate,
                "max_turns_error_rate": stats.error_metrics.max_turns_error_rate
            }
        return result
    
    def _serialize_flaw_stats(self, flaw_stats: Dict) -> Dict:
        """序列化缺陷类型统计"""
        result = {}
        for flaw_type, stats in flaw_stats.items():
            result[flaw_type] = {
                "total": stats.success_metrics.total_tests,
                "success": stats.success_metrics.total_success,
                "success_rate": stats.success_metrics.success_rate,
                "robustness_score": stats.robustness_score,
                "weighted_success_score": stats.success_metrics.weighted_success_score,
                "full_success_rate": stats.success_metrics.full_success_rate,
                "partial_success_rate": stats.success_metrics.partial_success_rate,
                "failure_rate": stats.success_metrics.failure_rate,
                # Execution metrics
                "avg_execution_time": stats.execution_metrics.avg_execution_time,
                "avg_turns": stats.execution_metrics.avg_turns,
                "avg_tool_calls": stats.execution_metrics.avg_tool_calls,
                "tool_coverage_rate": stats.execution_metrics.tool_coverage_rate,
                # Score metrics
                "avg_workflow_score": stats.score_metrics.workflow_scores.mean,
                "avg_phase2_score": stats.score_metrics.phase2_scores.mean,
                "avg_quality_score": stats.score_metrics.quality_scores.mean,
                "avg_final_score": stats.score_metrics.final_scores.mean,
                # 完整的错误统计
                "total_errors": stats.error_metrics.total_errors,
                "tool_call_format_errors": stats.error_metrics.tool_call_format_errors,
                "timeout_errors": stats.error_metrics.timeout_errors,
                "dependency_errors": stats.error_metrics.dependency_errors,
                "parameter_config_errors": stats.error_metrics.parameter_config_errors,
                "tool_selection_errors": stats.error_metrics.tool_selection_errors,
                "sequence_order_errors": stats.error_metrics.sequence_order_errors,
                "max_turns_errors": stats.error_metrics.max_turns_errors,
                
                # 完整的错误率
                "tool_selection_error_rate": stats.error_metrics.tool_selection_error_rate,
                "parameter_error_rate": stats.error_metrics.parameter_error_rate,
                "sequence_error_rate": stats.error_metrics.sequence_error_rate,
                "dependency_error_rate": stats.error_metrics.dependency_error_rate,
                "timeout_error_rate": stats.error_metrics.timeout_error_rate,
                "format_error_rate": stats.error_metrics.format_error_rate,
                "max_turns_error_rate": stats.error_metrics.max_turns_error_rate,
                
                # Assisted统计
                "assisted_failure": stats.success_metrics.assisted_failure,
                "assisted_success": stats.success_metrics.assisted_success,
                "total_assisted_turns": stats.success_metrics.total_assisted_turns,
                "tests_with_assistance": stats.success_metrics.tests_with_assistance,
                "avg_assisted_turns": stats.success_metrics.avg_assisted_turns,
                "assisted_success_rate": stats.success_metrics.assisted_success_rate,
                "assistance_rate": stats.success_metrics.assistance_rate
            }
        return result
    def _serialize_difficulty_stats(self, diff_stats: Dict) -> Dict:
        """序列化难度统计"""
        result = {}
        for difficulty, stats in diff_stats.items():
            result[difficulty] = {
                "total": stats.success_metrics.total_tests,
                "success": stats.success_metrics.total_success,
                "success_rate": stats.success_metrics.success_rate
            }
        return result
    
    def _update_group_statistics(self, key: str):
        """更新组统计"""
        group = self.database["test_groups"][key]
        instances = group["instances"]
        
        if not instances:
            return
        
        # 计算统计
        total = len(instances)
        success = sum(1 for inst in instances if inst["success"])
        partial = sum(1 for inst in instances if inst["partial_success"])
        failure = total - success - partial
        
        # 计算平均执行时间
        times = [inst["execution_time"] for inst in instances if inst["execution_time"] > 0]
        avg_time = sum(times) / len(times) if times else 0
        
        # 更新统计
        group["statistics"] = {
            "total": total,
            "success": success,
            "partial_success": partial,
            "failure": failure,
            "success_rate": success / total * 100 if total > 0 else 0,
            "partial_rate": partial / total * 100 if total > 0 else 0,
            "failure_rate": failure / total * 100 if total > 0 else 0,
            "avg_execution_time": avg_time
        }
    
    def _update_global_summary(self):
        """更新全局摘要 - 旧版本，保持向后兼容"""
        total_tests = 0
        total_success = 0
        total_partial = 0
        total_failure = 0
        models = set()
        
        for group in self.database["test_groups"].values():
            stats = group["statistics"]
            total_tests += stats["total"]
            total_success += stats["success"]
            total_partial += stats["partial_success"]
            total_failure += stats["failure"]
            models.add(group["model"])
        
        self.database["summary"]["total_tests"] = total_tests
        self.database["summary"]["total_success"] = total_success
        self.database["summary"]["total_partial"] = total_partial
        self.database["summary"]["total_failure"] = total_failure
        self.database["summary"]["overall_success_rate"] = total_success / total_tests * 100 if total_tests > 0 else 0
        self.database["summary"]["models_tested"] = sorted(list(models))
        self.database["summary"]["last_test_time"] = datetime.now().isoformat()
    
    def _update_global_summary_v2(self):
        """更新全局摘要 - 使用新的统计结构"""
        total_tests = 0
        total_success = 0
        total_partial = 0
        total_failure = 0
        
        # 从新的models结构中计算
        for model_name, model_stats in self.database["models"].items():
            if isinstance(model_stats, dict):
                # V3: 从字典格式中获取统计
                total_tests += model_stats.get("total_tests", 0)
                if "overall_stats" in model_stats:
                    total_success += model_stats["overall_stats"].get("total_success", 0)
                    total_partial += model_stats["overall_stats"].get("total_partial", 0)
                    total_failure += model_stats["overall_stats"].get("total_failure", 0)
        
        # 只在有新数据时才更新，避免清零
        if total_tests > 0 or self.database["summary"]["total_tests"] == 0:
            self.database["summary"]["total_tests"] = total_tests
            self.database["summary"]["total_success"] = total_success
            self.database["summary"]["total_partial"] = total_partial
            self.database["summary"]["total_failure"] = total_failure
            self.database["summary"]["overall_success_rate"] = (total_success + total_partial) / total_tests * 100 if total_tests > 0 else 0
        
        self.database["summary"]["last_test_time"] = datetime.now().isoformat()
    
    def get_test_count(self, model: str, task_type: str, prompt_type: str, 
                       difficulty: str = "easy", flaw_type: Optional[str] = None) -> int:
        """获取特定组合的测试次数"""
        parts = [model, task_type, prompt_type, difficulty]
        if flaw_type:
            parts.extend(["flawed", flaw_type])
        key = "_".join(parts)
        
        if key in self.database["test_groups"]:
            return self.database["test_groups"][key]["statistics"]["total"]
        return 0
    
    def needs_more_tests(self, model: str, task_type: str, prompt_type: str,
                         difficulty: str = "easy", flaw_type: Optional[str] = None,
                         target_count: int = 100) -> bool:
        """检查是否需要更多测试"""
        current_count = self.get_test_count(model, task_type, prompt_type, difficulty, flaw_type)
        return current_count < target_count
    
    def get_remaining_tests(self, model: str, target_count: int = 100) -> List[Dict]:
        """获取剩余需要测试的组合"""
        remaining = []
        
        # 定义所有可能的组合
        task_types = ["simple_task", "basic_task", "data_pipeline", "api_integration", "multi_stage_pipeline"]
        prompt_types = ["baseline", "optimal", "cot"]
        flaw_types = ["sequence_disorder", "tool_misuse", "parameter_error", "missing_step",
                      "redundant_operations", "logical_inconsistency", "semantic_drift"]
        
        # 检查正常测试
        for task_type in task_types:
            for prompt_type in prompt_types:
                count = self.get_test_count(model, task_type, prompt_type)
                if count < target_count:
                    remaining.append({
                        "task_type": task_type,
                        "prompt_type": prompt_type,
                        "is_flawed": False,
                        "flaw_type": None,
                        "current_count": count,
                        "needed": target_count - count
                    })
        
        # 检查缺陷测试
        for task_type in task_types:
            for flaw_type in flaw_types:
                count = self.get_test_count(model, task_type, "baseline", "easy", flaw_type)
                if count < target_count:
                    remaining.append({
                        "task_type": task_type,
                        "prompt_type": "baseline",
                        "is_flawed": True,
                        "flaw_type": flaw_type,
                        "current_count": count,
                        "needed": target_count - count
                    })
        
        return remaining
    
    def get_progress_report(self, model: Optional[str] = None) -> Dict:
        """生成进度报告 - 优先使用新的models结构"""
        report = {
            "summary": self.database["summary"].copy(),
            "models": {}
        }
        
        # 优先从新的models结构获取数据
        if "models" in self.database and self.database["models"]:
            for model_name, model_stats in self.database["models"].items():
                if model and model_name != model:
                    continue
                
                if False:  # V3: no ModelStatistics
                    # 从ModelStatistics对象提取统计
                    report["models"][model_name] = {
                        "total_tests": model_stats.overall_success.total_tests,
                        "total_success": model_stats.overall_success.total_success,
                        "by_task_type": self._serialize_task_stats(model_stats.by_task_type),
                        "by_prompt_type": self._serialize_prompt_stats(model_stats.by_prompt_type),
                        "by_flaw_type": self._serialize_flaw_stats(model_stats.by_flaw_type)
                    }
                elif isinstance(model_stats, dict):
                    # 已序列化的数据
                    report["models"][model_name] = {
                        "total_tests": model_stats.get("total_tests", 0),
                        "total_success": model_stats.get("total_success", 0),
                        "by_task_type": model_stats.get("by_task_type", {}),
                        "by_prompt_type": model_stats.get("by_prompt_type", {}),
                        "by_flaw_type": model_stats.get("by_flaw_type", {})
                    }
        
        # 如果新结构没有数据，回退到旧的test_groups
        if not report["models"] and "test_groups" in self.database:
            for key, group in self.database["test_groups"].items():
                if model and group["model"] != model:
                    continue
                
                model_name = group["model"]
                if model_name not in report["models"]:
                    report["models"][model_name] = {
                        "total_tests": 0,
                        "total_success": 0,
                        "by_task_type": {},
                        "by_prompt_type": {},
                        "by_flaw_type": {}
                    }
                
                model_report = report["models"][model_name]
                stats = group["statistics"]
                
                # 更新总计
                model_report["total_tests"] += stats["total"]
                model_report["total_success"] += stats["success"]
                
                # 按任务类型统计
                task_type = group["task_type"]
                if task_type not in model_report["by_task_type"]:
                    model_report["by_task_type"][task_type] = {"total": 0, "success": 0}
                model_report["by_task_type"][task_type]["total"] += stats["total"]
                model_report["by_task_type"][task_type]["success"] += stats["success"]
                
                # 按提示类型统计
                if not group["is_flawed"]:
                    prompt_type = group["prompt_type"]
                    if prompt_type not in model_report["by_prompt_type"]:
                        model_report["by_prompt_type"][prompt_type] = {"total": 0, "success": 0}
                    model_report["by_prompt_type"][prompt_type]["total"] += stats["total"]
                    model_report["by_prompt_type"][prompt_type]["success"] += stats["success"]
                
                # 按缺陷类型统计
                if group["is_flawed"] and group["flaw_type"]:
                    flaw_type = group["flaw_type"]
                    if flaw_type not in model_report["by_flaw_type"]:
                        model_report["by_flaw_type"][flaw_type] = {"total": 0, "success": 0}
                    model_report["by_flaw_type"][flaw_type]["total"] += stats["total"]
                    model_report["by_flaw_type"][flaw_type]["success"] += stats["success"]
        
        return report
    
    def export_for_report_generation(self) -> Dict:
        """导出用于报告生成的数据"""
        export_data = {
            "metadata": {
                "export_time": datetime.now().isoformat(),
                "database_version": self.database.get("version", "1.0"),
                "total_tests": self.database["summary"]["total_tests"]
            },
            "results": {}
        }
        
        # 转换为报告生成器期望的格式
        for key, group in self.database["test_groups"].items():
            export_data["results"][key] = {
                "total": group["statistics"]["total"],
                "success": group["statistics"]["success"],
                "partial_success": group["statistics"]["partial_success"],
                "model": group["model"],
                "task_type": group["task_type"],
                "prompt_type": group["prompt_type"],
                "difficulty": group["difficulty"],
                "is_flawed": group["is_flawed"],
                "flaw_type": group["flaw_type"],
                "success_rate": group["statistics"]["success_rate"],
                "avg_execution_time": group["statistics"]["avg_execution_time"]
            }
        
        return export_data

# 便捷函数
def add_test_result(model: str, task_type: str, prompt_type: str,
                   success: bool, execution_time: float = 0.0,
                   difficulty: str = "easy", is_flawed: bool = False,
                   flaw_type: Optional[str] = None, error_message: Optional[str] = None,
                   partial_success: bool = False,
                   format_recognition_errors: int = 0,
                   instruction_following_errors: int = 0,
                   tool_selection_errors: int = 0,
                   parameter_config_errors: int = 0,
                   sequence_order_errors: int = 0,
                   dependency_errors: int = 0) -> bool:
    """快速添加测试结果"""
    manager = CumulativeTestManager()
    
    record = TestRecord(
        model=model,
        task_type=task_type,
        prompt_type=prompt_type,
        difficulty=difficulty,
        success=success,
        partial_success=partial_success,
        execution_time=execution_time,
        error_message=error_message,
        is_flawed=is_flawed,
        flaw_type=flaw_type,
        format_recognition_errors=format_recognition_errors,
        instruction_following_errors=instruction_following_errors,
        tool_selection_errors=tool_selection_errors,
        parameter_config_errors=parameter_config_errors,
        sequence_order_errors=sequence_order_errors,
        dependency_errors=dependency_errors
    )
    
    return manager.add_test_result(record)

def check_progress(model: str, target_count: int = 100) -> Dict:
    """检查模型的测试进度"""
    manager = CumulativeTestManager()
    remaining = manager.get_remaining_tests(model, target_count)
    
    total_needed = sum(item["needed"] for item in remaining)
    total_completed = target_count * len(remaining) - total_needed if remaining else 0
    
    return {
        "model": model,
        "target_per_combination": target_count,
        "total_combinations": len(remaining),
        "total_needed": total_needed,
        "total_completed": total_completed,
        "completion_rate": total_completed / (total_completed + total_needed) * 100 if total_needed > 0 else 100,
        "remaining_tests": remaining
    }

def get_model_report(model: str) -> Dict:
    """获取模型的详细报告"""
    manager = CumulativeTestManager()
    return manager.get_progress_report(model)

class EnhancedCumulativeManager(CumulativeTestManager):
    """增强版累积测试管理器 - 支持新的层次结构"""
    
    def __init__(self, buffer_size: int = 10):
        super().__init__()
        self.buffer_size = buffer_size
        self.buffer = []  # 测试结果缓冲
        self.v2_models = {}  # 存储V2模型数据
        
        # 检查并升级数据库版本
        if self.database.get("version", "2.0") < "3.0":
            self._upgrade_to_v3()
    
    def _upgrade_to_v3(self):
        """升级数据库到V3版本"""
        self.database["version"] = "3.0"
        # 初始化V2模型数据
        for model_name in self.database.get("models", {}):
            if model_name not in self.v2_models:
                self.v2_models[model_name] = {}  # V3: dict format
    
    def add_test_result_with_classification(self, record: TestRecord) -> bool:
        """添加带分类的测试结果（支持新层次）"""
        # 更新V2模型数据
        model = record.model
        if model not in self.v2_models:
            try:
                from old_data_structures.cumulative_data_structure import ModelStatistics
                self.v2_models[model] = ModelStatistics(model_name=model)
            except ImportError:
                self.v2_models[model] = {}  # fallback to dict
        
        # 构建测试字典
        test_dict = {
            "model": record.model,
            "task_type": record.task_type,
            "prompt_type": record.prompt_type,
            "difficulty": record.difficulty,
            "tool_reliability": record.tool_reliability,  # 关键：传递tool_reliability
            "success_level": record.success_level if hasattr(record, 'success_level') else 
                           ("full_success" if record.success else "failure"),
            "execution_time": record.execution_time,
            "turns": record.turns,
            "tool_calls": record.tool_calls,
            "required_tools": getattr(record, 'required_tools', []),  # 添加required_tools
            "executed_tools": getattr(record, 'executed_tools', getattr(record, 'tool_calls', [])),  # 添加executed_tools
            "tool_coverage_rate": getattr(record, 'tool_coverage_rate', 0.0),  # 添加tool_coverage_rate
            "workflow_score": getattr(record, 'workflow_score', None),
            "phase2_score": getattr(record, 'phase2_score', None),
            "quality_score": getattr(record, 'quality_score', None),
            "final_score": getattr(record, 'final_score', None),
            "format_error_count": getattr(record, 'format_error_count', 0),
            "is_flawed": record.is_flawed,
            "flaw_type": record.flaw_type,
            "timestamp": record.timestamp or datetime.now().isoformat()
        }
        
        # 使用V2模型更新
        if hasattr(self.v2_models[model], 'update_from_test'):
            self.v2_models[model].update_from_test(test_dict)
        else:
            # v2_models是字典，跳过更新
            pass
        
        # 添加到缓冲
        self.buffer.append(record)
        
        # 如果缓冲满了，刷新到数据库
        if len(self.buffer) >= self.buffer_size:
            self._flush_buffer()
        
        # 调用父类方法保存（保持向后兼容）
        return super().add_test_result(record)
    
    def _flush_buffer(self):
        """刷新缓冲区"""
        if not self.buffer:
            return
        
        # 清空缓冲
        self.buffer.clear()
        
        # 保存V2模型数据到数据库
        self._save_v2_models()
        
        # 保存数据库
        self.save_database()
    
    def _save_v2_models(self):
        """保存V2模型数据到数据库"""
        for model_name, v2_model in self.v2_models.items():
            # 将V2模型序列化并保存到数据库
            v2_dict = v2_model.to_dict()
            # 调试输出
            if model_name == 'gpt-4o-mini':
                print(f"[DEBUG] Saving V2 model {model_name}: tool_coverage_rate = {v2_dict.get('tool_coverage_rate', 'NOT FOUND')}")
                if 'overall_stats' in v2_dict:
                    print(f"[DEBUG] V2 overall_stats.tool_coverage_rate = {v2_dict['overall_stats'].get('tool_coverage_rate', 'NOT FOUND')}")
            self.database["models"][model_name] = v2_dict
    
    def finalize(self):
        """完成并刷新所有缓冲数据"""
        self._flush_buffer()
        # 确保V2数据已保存
        if self.v2_models:
            self._save_v2_models()
            self.save_database()
    
    def get_statistics_by_hierarchy(self, model: str, prompt_type: str = None,
                                   tool_rate: float = None, difficulty: str = None,
                                   task_type: str = None) -> Dict:
        """按层次获取统计数据"""
        if model not in self.database["models"]:
            return {}
        
        model_data = self.database["models"][model]
        
        # 如果是ModelStatistics对象，序列化它
        if False:  # V3: no ModelStatistics
            model_data = self._serialize_model_stats_v3(model_data)
        
        # 如果只指定模型，返回模型级别统计
        if not prompt_type:
            return model_data
        
        # 导航到prompt类型
        if "by_prompt_type" not in model_data or prompt_type not in model_data["by_prompt_type"]:
            return {}
        prompt_data = model_data["by_prompt_type"][prompt_type]
        
        # 如果只指定到prompt类型
        if tool_rate is None:
            return prompt_data
        
        # 导航到工具成功率
        rate_key = str(tool_rate)
        if "by_tool_success_rate" not in prompt_data or rate_key not in prompt_data["by_tool_success_rate"]:
            return {}
        rate_data = prompt_data["by_tool_success_rate"][rate_key]
        
        # 如果只指定到工具成功率
        if not difficulty:
            return rate_data
        
        # 导航到难度
        if "by_difficulty" not in rate_data or difficulty not in rate_data["by_difficulty"]:
            return {}
        diff_data = rate_data["by_difficulty"][difficulty]
        
        # 如果只指定到难度
        if not task_type:
            return diff_data
        
        # 导航到任务类型
        if "by_task_type" not in diff_data or task_type not in diff_data["by_task_type"]:
            return {}
        
        return diff_data["by_task_type"][task_type]

if __name__ == "__main__":
    # 示例使用
    print("PILOT-Bench 累积测试管理系统")
    print("="*60)
    
    # 添加一些测试结果示例
    add_test_result(
        model="qwen2.5-3b-instruct",
        task_type="simple_task",
        prompt_type="baseline",
        success=True,
        execution_time=2.5
    )
    
    # 检查进度
    progress = check_progress("qwen2.5-3b-instruct", target_count=100)
    print(f"\n模型进度: {progress['model']}")
    print(f"完成率: {progress['completion_rate']:.1f}%")
    print(f"剩余测试: {progress['total_needed']}个")
