#!/usr/bin/env python3
"""
增强的进度管理系统
- 细粒度的进度跟踪
- 支持失败重测的进度状态
- 与失败测试管理器集成
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enhanced_failed_tests_manager import EnhancedFailedTestsManager

@dataclass
class StepProgress:
    """步骤进度"""
    step_id: str
    step_name: str
    status: str  # pending, running, completed, failed, skipped
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    progress_percentage: float = 0.0
    total_models: int = 0
    completed_models: int = 0
    failed_models: int = 0
    skipped_models: int = 0
    current_model: str = ""
    current_group: str = ""
    substeps: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.substeps is None:
            self.substeps = {}

@dataclass
class ModelProgress:
    """模型进度"""
    model_name: str
    status: str  # pending, running, completed, failed, retrying
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    completed_groups: List[str] = None
    failed_groups: List[str] = None
    retrying_groups: List[str] = None
    current_group: str = ""
    total_groups: int = 0
    
    def __post_init__(self):
        if self.completed_groups is None:
            self.completed_groups = []
        if self.failed_groups is None:
            self.failed_groups = []
        if self.retrying_groups is None:
            self.retrying_groups = []

class EnhancedProgressManager:
    """增强的进度管理器"""
    
    def __init__(self, progress_file="enhanced_progress.json", 
                 legacy_progress_file="test_progress.txt"):
        self.progress_file = Path(progress_file)
        self.legacy_progress_file = Path(legacy_progress_file)
        self.failed_manager = EnhancedFailedTestsManager()
        self._load_progress()
    
    def _load_progress(self):
        """加载进度文件"""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    self.progress = json.load(f)
            except Exception as e:
                print(f"加载进度文件失败: {e}")
                self._create_empty_progress()
        else:
            # 尝试从旧格式转换
            self._migrate_from_legacy()
    
    def _create_empty_progress(self):
        """创建空的进度结构"""
        self.progress = {
            "version": "2.0",
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "session_info": {
                "session_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
                "test_mode": "unknown",  # auto, debug, full_auto
                "concurrent_strategy": "unknown",  # adaptive, fixed, ultra_parallel
                "checkpoint_interval": 20
            },
            "overall_progress": {
                "current_step": "",
                "total_steps": 5,
                "completed_steps": 0,
                "failed_steps": 0,
                "overall_percentage": 0.0,
                "estimated_remaining_time": None
            },
            "steps": {},  # step_id -> StepProgress
            "models": {},  # model_name -> ModelProgress
            "retry_tracking": {
                "total_retries": 0,
                "successful_retries": 0,
                "failed_retries": 0,
                "models_with_retries": []
            },
            "statistics": {
                "total_tests_planned": 0,
                "total_tests_completed": 0,
                "total_tests_failed": 0,
                "completion_rate": 0.0,
                "failure_rate": 0.0
            }
        }
    
    def _migrate_from_legacy(self):
        """从旧格式迁移"""
        self._create_empty_progress()
        
        if self.legacy_progress_file.exists():
            try:
                legacy_data = {}
                with open(self.legacy_progress_file, 'r') as f:
                    for line in f:
                        if '=' in line:
                            key, value = line.strip().split('=', 1)
                            legacy_data[key] = value
                
                # 转换基本信息
                if 'STEP' in legacy_data:
                    step_id = f"5.{legacy_data['STEP']}"
                    self.progress["overall_progress"]["current_step"] = step_id
                
                if 'MODEL_INDEX' in legacy_data:
                    # 可以根据模型索引推断当前模型
                    pass
                
                print("✅ 已从旧格式迁移进度数据")
                
            except Exception as e:
                print(f"迁移旧进度数据失败: {e}")
    
    def _save_progress(self):
        """保存进度文件"""
        self.progress["last_updated"] = datetime.now().isoformat()
        
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(self.progress, f, indent=2, ensure_ascii=False)
        
        # 同时更新旧格式文件以保持兼容性
        self._update_legacy_format()
    
    def _update_legacy_format(self):
        """更新旧格式文件以保持兼容性"""
        current_step = self.progress["overall_progress"]["current_step"]
        if current_step.startswith("5."):
            step_num = current_step.split(".")[1]
            
            # 找到当前模型索引
            model_index = 0
            current_model = ""
            for i, (model_name, model_progress) in enumerate(self.progress["models"].items()):
                if model_progress["status"] in ["running", "pending"]:
                    model_index = i
                    current_model = model_name
                    break
            
            with open(self.legacy_progress_file, 'w') as f:
                f.write(f"STEP={step_num}\n")
                f.write(f"MODEL_INDEX={model_index}\n")
                f.write(f"SUBSTEP=AUTO_ENHANCED\n")
    
    def start_step(self, step_id: str, step_name: str, models: List[str]):
        """开始一个步骤"""
        step_progress = StepProgress(
            step_id=step_id,
            step_name=step_name,
            status="running",
            start_time=datetime.now().isoformat(),
            total_models=len(models)
        )
        
        self.progress["steps"][step_id] = asdict(step_progress)
        self.progress["overall_progress"]["current_step"] = step_id
        
        # 初始化模型进度
        for model in models:
            if model not in self.progress["models"]:
                model_progress = ModelProgress(
                    model_name=model,
                    status="pending"
                )
                self.progress["models"][model] = asdict(model_progress)
        
        self._save_progress()
        print(f"🚀 开始步骤: {step_id} - {step_name}")
        print(f"   模型数量: {len(models)}")
    
    def start_model_testing(self, model: str, groups: List[str]):
        """开始模型测试"""
        if model in self.progress["models"]:
            model_progress = self.progress["models"][model]
            model_progress.update({
                "status": "running",
                "start_time": datetime.now().isoformat(),
                "total_groups": len(groups),
                "current_group": groups[0] if groups else ""
            })
        
        # 更新当前步骤的当前模型
        current_step = self.progress["overall_progress"]["current_step"]
        if current_step in self.progress["steps"]:
            self.progress["steps"][current_step]["current_model"] = model
        
        self._save_progress()
        print(f"📋 开始模型测试: {model}")
        print(f"   测试组数量: {len(groups)}")
    
    def complete_model_group(self, model: str, group: str, success: bool = True):
        """完成模型组测试"""
        if model not in self.progress["models"]:
            return
        
        model_progress = self.progress["models"][model]
        
        if success:
            if group not in model_progress["completed_groups"]:
                model_progress["completed_groups"].append(group)
            # 从失败和重试列表中移除
            if group in model_progress["failed_groups"]:
                model_progress["failed_groups"].remove(group)
            if group in model_progress["retrying_groups"]:
                model_progress["retrying_groups"].remove(group)
        else:
            if group not in model_progress["failed_groups"]:
                model_progress["failed_groups"].append(group)
            # 从完成列表中移除
            if group in model_progress["completed_groups"]:
                model_progress["completed_groups"].remove(group)
        
        # 更新模型状态
        total_groups = model_progress["total_groups"]
        completed = len(model_progress["completed_groups"])
        failed = len(model_progress["failed_groups"])
        
        if completed + failed >= total_groups:
            if failed == 0:
                model_progress["status"] = "completed"
                model_progress["end_time"] = datetime.now().isoformat()
            else:
                model_progress["status"] = "failed"
        
        self._update_step_progress()
        self._save_progress()
        
        status_icon = "✅" if success else "❌"
        print(f"{status_icon} {model} - {group}: {'完成' if success else '失败'}")
    
    def start_retry(self, model: str, group: str):
        """开始重试"""
        if model not in self.progress["models"]:
            return
        
        model_progress = self.progress["models"][model]
        
        # 添加到重试列表
        if group not in model_progress["retrying_groups"]:
            model_progress["retrying_groups"].append(group)
        
        # 从失败列表移除
        if group in model_progress["failed_groups"]:
            model_progress["failed_groups"].remove(group)
        
        # 更新重试统计
        retry_tracking = self.progress["retry_tracking"]
        retry_tracking["total_retries"] += 1
        if model not in retry_tracking["models_with_retries"]:
            retry_tracking["models_with_retries"].append(model)
        
        model_progress["status"] = "retrying"
        
        self._save_progress()
        print(f"🔄 开始重试: {model} - {group}")
    
    def _update_step_progress(self):
        """更新步骤进度"""
        current_step = self.progress["overall_progress"]["current_step"]
        if current_step not in self.progress["steps"]:
            return
        
        step_progress = self.progress["steps"][current_step]
        
        # 统计模型状态
        completed_models = 0
        failed_models = 0
        
        for model_name, model_progress in self.progress["models"].items():
            if model_progress["status"] == "completed":
                completed_models += 1
            elif model_progress["status"] == "failed":
                failed_models += 1
        
        step_progress["completed_models"] = completed_models
        step_progress["failed_models"] = failed_models
        
        total_models = step_progress["total_models"]
        if total_models > 0:
            step_progress["progress_percentage"] = (completed_models / total_models) * 100
        
        # 检查步骤是否完成
        if completed_models + failed_models >= total_models:
            step_progress["status"] = "completed" if failed_models == 0 else "failed"
            step_progress["end_time"] = datetime.now().isoformat()
    
    def get_failed_tests_for_retry(self) -> Dict[str, List[str]]:
        """获取需要重试的失败测试"""
        failed_tests = {}
        
        for model_name, model_progress in self.progress["models"].items():
            if model_progress["failed_groups"]:
                failed_tests[model_name] = model_progress["failed_groups"].copy()
        
        return failed_tests
    
    def has_failed_tests(self) -> bool:
        """检查是否有失败的测试"""
        for model_progress in self.progress["models"].values():
            if model_progress["failed_groups"]:
                return True
        return False
    
    def show_progress_summary(self):
        """显示进度概要"""
        print("=" * 60)
        print("📊 测试进度概要")
        print("=" * 60)
        
        overall = self.progress["overall_progress"]
        print(f"当前步骤: {overall['current_step']}")
        print(f"总体进度: {overall['overall_percentage']:.1f}%")
        print()
        
        # 显示步骤进度
        print("📋 步骤进度:")
        for step_id, step_progress in self.progress["steps"].items():
            status_icon = {
                "pending": "⏸️",
                "running": "🔄", 
                "completed": "✅",
                "failed": "❌",
                "skipped": "⏭️"
            }.get(step_progress["status"], "❓")
            
            print(f"  {status_icon} {step_id}: {step_progress['step_name']}")
            print(f"      进度: {step_progress['progress_percentage']:.1f}% "
                  f"({step_progress['completed_models']}/{step_progress['total_models']})")
            
            if step_progress["failed_models"] > 0:
                print(f"      失败: {step_progress['failed_models']} 个模型")
        
        print()
        
        # 显示模型状态
        print("🤖 模型状态:")
        status_counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "retrying": 0}
        
        for model_name, model_progress in self.progress["models"].items():
            status = model_progress["status"]
            status_counts[status] += 1
            
            status_icon = {
                "pending": "⏸️",
                "running": "🔄",
                "completed": "✅", 
                "failed": "❌",
                "retrying": "🔄"
            }.get(status, "❓")
            
            completed = len(model_progress["completed_groups"])
            failed = len(model_progress["failed_groups"])
            retrying = len(model_progress["retrying_groups"])
            total = model_progress["total_groups"]
            
            print(f"  {status_icon} {model_name}: {completed}/{total} 完成")
            if failed > 0:
                print(f"      ❌ 失败: {failed} 个组")
            if retrying > 0:
                print(f"      🔄 重试中: {retrying} 个组")
        
        print()
        print("📈 统计:")
        for status, count in status_counts.items():
            if count > 0:
                print(f"  {status}: {count} 个模型")
        
        # 显示重试信息
        retry_tracking = self.progress["retry_tracking"]
        if retry_tracking["total_retries"] > 0:
            print()
            print("🔄 重试统计:")
            print(f"  总重试次数: {retry_tracking['total_retries']}")
            print(f"  成功重试: {retry_tracking['successful_retries']}")
            print(f"  失败重试: {retry_tracking['failed_retries']}")
            print(f"  涉及模型: {len(retry_tracking['models_with_retries'])}")
    
    def show_detailed_progress(self):
        """显示详细进度"""
        self.show_progress_summary()
        print()
        
        # 显示当前活动
        current_step = self.progress["overall_progress"]["current_step"]
        if current_step in self.progress["steps"]:
            step_progress = self.progress["steps"][current_step]
            if step_progress["current_model"]:
                print(f"🎯 当前正在测试:")
                print(f"   模型: {step_progress['current_model']}")
                if step_progress["current_group"]:
                    print(f"   测试组: {step_progress['current_group']}")
        
        # 显示失败的测试
        failed_tests = self.get_failed_tests_for_retry()
        if failed_tests:
            print()
            print("❌ 失败的测试 (可重试):")
            for model, groups in failed_tests.items():
                print(f"  {model}: {', '.join(groups)}")
    
    def generate_retry_plan(self) -> Dict[str, Any]:
        """生成重试计划"""
        failed_tests = self.get_failed_tests_for_retry()
        
        if not failed_tests:
            return {"has_retries": False}
        
        retry_plan = {
            "has_retries": True,
            "total_models": len(failed_tests),
            "total_groups": sum(len(groups) for groups in failed_tests.values()),
            "retry_schedule": []
        }
        
        for model, groups in failed_tests.items():
            for group in groups:
                retry_plan["retry_schedule"].append({
                    "model": model,
                    "group": group,
                    "priority": "high" if "structure" in group.lower() else "normal"
                })
        
        return retry_plan

def main():
    """命令行接口"""
    import sys
    
    manager = EnhancedProgressManager()
    
    if len(sys.argv) < 2:
        manager.show_progress_summary()
        return
    
    command = sys.argv[1]
    
    if command == "summary":
        manager.show_progress_summary()
    elif command == "detailed": 
        manager.show_detailed_progress()
    elif command == "retry-plan":
        plan = manager.generate_retry_plan()
        if plan["has_retries"]:
            print(f"需要重试: {plan['total_models']} 个模型, {plan['total_groups']} 个组")
            for item in plan["retry_schedule"]:
                print(f"  {item['model']} - {item['group']} ({item['priority']})")
        else:
            print("没有需要重试的测试")
    else:
        print(f"未知命令: {command}")
        print("可用命令: summary, detailed, retry-plan")

if __name__ == "__main__":
    main()