#!/usr/bin/env python3
"""
V3数据结构处理模块 - 纯字典格式
不使用任何Python类对象，确保完全的JSON兼容性
"""

from typing import Dict, Any, Optional
from datetime import datetime


class DataStructureV3:
    """V3数据结构的辅助方法（注意：只操作字典，不创建对象）"""
    
    @staticmethod
    def create_empty_database() -> Dict:
        """创建空的V3数据库结构"""
        return {
            "version": "3.0",
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "test_groups": {},  # 保留用于兼容
            "models": {},
            "summary": {
                "total_tests": 0,
                "total_success": 0,
                "total_partial": 0,
                "total_failure": 0,
                "models_tested": [],
                "last_test_time": None
            }
        }
    
    @staticmethod
    def create_empty_model(model_name: str) -> Dict:
        """创建空的模型数据结构"""
        return {
            "model_name": model_name,
            "first_test_time": datetime.now().isoformat(),
            "last_test_time": datetime.now().isoformat(),
            "total_tests": 0,
            "overall_stats": DataStructureV3.create_empty_stats(),
            "by_prompt_type": {}
        }
    
    @staticmethod
    def create_empty_stats() -> Dict:
        """创建空的统计结构"""
        return {
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
    
    @staticmethod
    def create_empty_task_stats() -> Dict:
        """创建空的任务类型统计"""
        return {
            # 基础统计
            "total": 0,
            "success": 0,
            "success_rate": 0.0,
            "weighted_success_score": 0.0,
            "full_success_rate": 0.0,
            "partial_success_rate": 0.0,
            "failure_rate": 0.0,
            
            # 执行统计
            "avg_execution_time": 0.0,
            "avg_turns": 0.0,
            "avg_tool_calls": 0.0,
            "tool_coverage_rate": 0.0,
            
            # 质量分数
            "avg_workflow_score": 0.0,
            "avg_phase2_score": 0.0,
            "avg_quality_score": 0.0,
            "avg_final_score": 0.0,
            
            # 错误统计
            "total_errors": 0,
            "tool_call_format_errors": 0,
            "timeout_errors": 0,
            "dependency_errors": 0,
            "parameter_config_errors": 0,
            "tool_selection_errors": 0,
            "sequence_order_errors": 0,
            "max_turns_errors": 0,
            "other_errors": 0,
            
            # 错误率
            "tool_selection_error_rate": 0.0,
            "parameter_error_rate": 0.0,
            "sequence_error_rate": 0.0,
            "dependency_error_rate": 0.0,
            "timeout_error_rate": 0.0,
            "format_error_rate": 0.0,
            "max_turns_error_rate": 0.0,
            "other_error_rate": 0.0,
            
            # 辅助统计
            "assisted_failure": 0,
            "assisted_success": 0,
            "total_assisted_turns": 0,
            "tests_with_assistance": 0,
            "avg_assisted_turns": 0.0,
            "assisted_success_rate": 0.0,
            "assistance_rate": 0.0
        }
    
    @staticmethod
    def get_or_create_path(data: Dict, path: list, default_factory=dict) -> Dict:
        """
        获取或创建嵌套路径
        
        Args:
            data: 根字典
            path: 路径列表，如 ['by_prompt_type', 'baseline', 'by_tool_success_rate', '0.8']
            default_factory: 创建新节点的工厂函数
        
        Returns:
            路径末端的字典
        """
        current = data
        for key in path:
            if key not in current:
                current[key] = default_factory()
            current = current[key]
        return current
    
    @staticmethod
    def update_task_stats(stats: Dict, test_result: Dict):
        """
        更新任务统计（增量更新）
        
        Args:
            stats: 要更新的统计字典
            test_result: 测试结果字典
        """
        # 更新计数
        stats["total"] += 1
        
        # 成功统计
        if test_result.get("success"):
            stats["success"] += 1
            if test_result.get("success_level") == "full_success":
                stats.setdefault("full_success", 0)
                stats["full_success"] += 1
            elif test_result.get("success_level") == "partial_success":
                stats.setdefault("partial_success", 0) 
                stats["partial_success"] += 1
        
        # 辅助统计
        if test_result.get("format_error_count", 0) > 0:
            stats["tests_with_assistance"] += 1
            stats["total_assisted_turns"] += test_result.get("format_error_count", 0)
            if test_result.get("success"):
                stats["assisted_success"] += 1
            else:
                stats["assisted_failure"] += 1
        
        # 错误统计
        if not test_result.get("success"):
            stats["total_errors"] += 1
            error_msg = test_result.get("error_message", "")
            if "timeout" in error_msg.lower():
                stats["timeout_errors"] += 1
            elif "format" in error_msg.lower():
                stats["tool_call_format_errors"] += 1
            # 可以添加更多错误分类
        
        # 重新计算率
        if stats["total"] > 0:
            stats["success_rate"] = stats["success"] / stats["total"]
            stats["failure_rate"] = 1.0 - stats["success_rate"]
            
            # 计算加权成功分数
            full = stats.get("full_success", 0)
            partial = stats.get("partial_success", 0)
            stats["weighted_success_score"] = (full * 1.0 + partial * 0.5) / stats["total"]
            
            # 错误率
            if stats["total_errors"] > 0:
                stats["timeout_error_rate"] = stats["timeout_errors"] / stats["total"]
                stats["format_error_rate"] = stats["tool_call_format_errors"] / stats["total"]
            
            # 辅助率
            if stats["tests_with_assistance"] > 0:
                stats["assistance_rate"] = stats["tests_with_assistance"] / stats["total"]
                stats["avg_assisted_turns"] = stats["total_assisted_turns"] / stats["tests_with_assistance"]
                assisted_total = stats["assisted_success"] + stats["assisted_failure"]
                if assisted_total > 0:
                    stats["assisted_success_rate"] = stats["assisted_success"] / assisted_total
        
        # 更新执行统计（使用增量平均）
        n = stats["total"]
        if n > 0:
            # 增量更新平均值: new_avg = old_avg + (new_value - old_avg) / n
            exec_time = test_result.get("execution_time", 0)
            stats["avg_execution_time"] += (exec_time - stats["avg_execution_time"]) / n
            
            turns = test_result.get("turns", 0)
            stats["avg_turns"] += (turns - stats["avg_turns"]) / n
            
            tool_calls = len(test_result.get("tool_calls", []))
            stats["avg_tool_calls"] += (tool_calls - stats["avg_tool_calls"]) / n
            
            coverage = test_result.get("tool_coverage_rate", 0)
            stats["tool_coverage_rate"] += (coverage - stats["tool_coverage_rate"]) / n
            
            # 质量分数
            for score_key in ["workflow_score", "phase2_score", "quality_score", "final_score"]:
                avg_key = f"avg_{score_key}"
                score = test_result.get(score_key, 0)
                stats[avg_key] += (score - stats[avg_key]) / n
    
    @staticmethod
    def recalculate_model_totals(model_data: Dict):
        """重新计算模型的总体统计"""
        if not isinstance(model_data, dict):
            return
        
        # 重置总体统计
        overall = DataStructureV3.create_empty_stats()
        total_tests = 0
        
        # 遍历所有层次结构累加统计
        for prompt_type, prompt_data in model_data.get("by_prompt_type", {}).items():
            if not isinstance(prompt_data, dict):
                continue
                
            for rate, rate_data in prompt_data.get("by_tool_success_rate", {}).items():
                if not isinstance(rate_data, dict):
                    continue
                    
                for diff, diff_data in rate_data.get("by_difficulty", {}).items():
                    if not isinstance(diff_data, dict):
                        continue
                        
                    for task, task_data in diff_data.get("by_task_type", {}).items():
                        if not isinstance(task_data, dict):
                            continue
                        
                        # 累加测试数
                        task_total = task_data.get("total", 0)
                        total_tests += task_total
                        
                        # 累加成功数
                        overall["total_success"] += task_data.get("success", 0)
                        overall["total_full"] += task_data.get("full_success", 0)
                        overall["total_partial"] += task_data.get("partial_success", 0)
                        overall["total_failure"] += task_total - task_data.get("success", 0)
        
        # 更新模型总数
        model_data["total_tests"] = total_tests
        
        # 计算总体率
        if total_tests > 0:
            overall["success_rate"] = overall["total_success"] / total_tests
            overall["weighted_success_score"] = (
                overall["total_full"] * 1.0 + overall["total_partial"] * 0.5
            ) / total_tests
        
        # 更新overall_stats
        model_data["overall_stats"] = overall
    
    @staticmethod
    def validate_structure(data: Dict) -> bool:
        """验证数据结构是否符合V3规范"""
        if not isinstance(data, dict):
            return False
        
        # 检查版本
        if data.get("version") != "3.0":
            return False
        
        # 检查必要字段
        required_fields = ["created_at", "last_updated", "models", "summary"]
        for field in required_fields:
            if field not in data:
                return False
        
        # 检查models是字典
        if not isinstance(data["models"], dict):
            return False
        
        # 检查每个model是字典
        for model_name, model_data in data["models"].items():
            if not isinstance(model_data, dict):
                print(f"Model {model_name} is not a dict: {type(model_data)}")
                return False
        
        return True