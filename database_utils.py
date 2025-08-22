#!/usr/bin/env python3
"""
数据库工具函数
避免循环导入问题
支持JSON和Parquet两种存储格式
"""

import json
import os
from typing import Dict, List, Optional, Any
from pathlib import Path

def load_database(db_path="pilot_bench_cumulative_results/master_database.json") -> Dict:
    """加载测试数据库 - 支持JSON和Parquet格式"""
    storage_format = os.environ.get('STORAGE_FORMAT', 'json').lower()
    
    if storage_format == 'parquet':
        # Parquet模式：从Parquet文件构建数据库结构
        parquet_file = Path("pilot_bench_parquet_data/test_results.parquet")
        if not parquet_file.exists():
            # 如果Parquet文件不存在，返回空数据库结构
            return {
                "version": "3.0",
                "models": {},
                "summary": {"total_tests": 0}
            }
        
        try:
            import pandas as pd
            df = pd.read_parquet(parquet_file)
            
            # 构建与JSON相同的数据结构
            db = {
                "version": "3.0",
                "models": {},
                "summary": {
                    "total_tests": len(df),
                    "total_success": int(df['success'].sum()) if 'success' in df.columns else 0
                }
            }
            
            # 按模型分组构建层次结构
            if not df.empty:
                for model in df['model'].unique():
                    model_df = df[df['model'] == model]
                    db['models'][model] = {
                        "by_prompt_type": {}
                    }
                    
                    for prompt_type in model_df['prompt_type'].unique():
                        prompt_df = model_df[model_df['prompt_type'] == prompt_type]
                        db['models'][model]['by_prompt_type'][prompt_type] = {
                            "by_tool_success_rate": {}
                        }
                        
                        # 按tool_success_rate分组
                        for rate in prompt_df['tool_success_rate'].unique():
                            rate_key = str(round(rate, 4))  # 4位小数精度
                            rate_df = prompt_df[prompt_df['tool_success_rate'] == rate]
                            db['models'][model]['by_prompt_type'][prompt_type]['by_tool_success_rate'][rate_key] = {
                                "by_difficulty": {}
                            }
                            
                            for difficulty in rate_df['difficulty'].unique():
                                diff_df = rate_df[rate_df['difficulty'] == difficulty]
                                db['models'][model]['by_prompt_type'][prompt_type]['by_tool_success_rate'][rate_key]['by_difficulty'][difficulty] = {
                                    "by_task_type": {}
                                }
                                
                                for task_type in diff_df['task_type'].unique():
                                    task_df = diff_df[diff_df['task_type'] == task_type]
                                    db['models'][model]['by_prompt_type'][prompt_type]['by_tool_success_rate'][rate_key]['by_difficulty'][difficulty]['by_task_type'][task_type] = {
                                        "total": len(task_df),
                                        "successful": int(task_df['success'].sum())
                                    }
            
            return db
            
        except Exception as e:
            print(f"[WARNING] 加载Parquet数据失败: {e}")
            return {"version": "3.0", "models": {}, "summary": {"total_tests": 0}}
    
    else:
        # JSON模式：原有逻辑
        if not os.path.exists(db_path):
            return {}
        with open(db_path, 'r') as f:
            return json.load(f)

def get_completed_count(model: str, prompt_type: str, difficulty: str, task_type: str, 
                       tool_success_rate: float = 0.8) -> int:
    """获取特定配置下已完成的测试数量 - 支持新的层次结构"""
    db = load_database()
    count = 0
    
    # 检查数据库版本
    version = db.get("version", "2.0")
    
    if version >= "3.0":
        # V3版本：使用新的层次结构
        # model -> prompt_type -> tool_success_rate -> difficulty -> task_type
        if "models" in db and model in db["models"]:
            model_data = db["models"][model]
            if "by_prompt_type" in model_data and prompt_type in model_data["by_prompt_type"]:
                prompt_data = model_data["by_prompt_type"][prompt_type]
                # 直接使用原始值（通常是0.6, 0.7, 0.8, 0.9）
                rate_key = str(tool_success_rate)
                if "by_tool_success_rate" in prompt_data and rate_key in prompt_data["by_tool_success_rate"]:
                    rate_data = prompt_data["by_tool_success_rate"][rate_key]
                    if "by_difficulty" in rate_data and difficulty in rate_data["by_difficulty"]:
                        diff_data = rate_data["by_difficulty"][difficulty]
                        if "by_task_type" in diff_data and task_type in diff_data["by_task_type"]:
                            task_data = diff_data["by_task_type"][task_type]
                            count = task_data.get("total", 0)
    else:
        # V2版本：使用旧的test_groups结构
        # 构建group key
        if prompt_type.startswith("flawed_"):
            group_key = f"{model}_flawed_{difficulty}"
            flaw_type = prompt_type.replace("flawed_", "")
        else:
            group_key = f"{model}_{prompt_type}_{difficulty}"
            flaw_type = None
        
        test_groups = db.get("test_groups", {})
        if group_key in test_groups:
            for record in test_groups[group_key].get("test_records", []):
                if record.get("task_type") == task_type:
                    if flaw_type:
                        if record.get("flaw_type") == flaw_type:
                            count += 1
                    else:
                        count += 1
    
    return count

def get_all_models_from_database() -> List[str]:
    """获取数据库中所有模型"""
    db = load_database()
    return list(db.get("models", {}).keys())

def get_model_test_summary(model: str) -> Dict[str, Any]:
    """获取模型测试总结"""
    db = load_database()
    
    if "models" not in db or model not in db["models"]:
        return {"status": "not_found"}
    
    model_data = db["models"][model]
    
    # 统计总体数据
    total_tests = 0
    total_success = 0
    
    if "by_prompt_type" in model_data:
        for prompt_type, prompt_data in model_data["by_prompt_type"].items():
            if "by_tool_success_rate" in prompt_data:
                for rate, rate_data in prompt_data["by_tool_success_rate"].items():
                    if "by_difficulty" in rate_data:
                        for difficulty, diff_data in rate_data["by_difficulty"].items():
                            if "by_task_type" in diff_data:
                                for task_type, task_data in diff_data["by_task_type"].items():
                                    total = task_data.get("total", 0)
                                    success = task_data.get("success", 0)
                                    total_tests += total
                                    total_success += success
    
    completion_rate = total_success / total_tests if total_tests > 0 else 0.0
    failure_rate = (total_tests - total_success) / total_tests if total_tests > 0 else 0.0
    
    return {
        "status": "analyzed",
        "total_tests": total_tests,
        "total_success": total_success,
        "total_failures": total_tests - total_success,
        "completion_rate": completion_rate,
        "failure_rate": failure_rate
    }