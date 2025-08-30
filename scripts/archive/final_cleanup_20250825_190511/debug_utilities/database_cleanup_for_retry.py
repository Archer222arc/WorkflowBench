#!/usr/bin/env python3
"""
数据库清理工具 - 重测前清理指定模型的特定配置数据
确保重测时覆盖而不是累加数据
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

class DatabaseCleanupForRetry:
    """重测前的数据库清理工具"""
    
    def __init__(self, db_path: str = "pilot_bench_cumulative_results/master_database.json"):
        self.db_path = Path(db_path)
        self.backup_created = False
    
    def create_backup(self):
        """创建数据库备份"""
        if not self.backup_created and self.db_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.db_path.parent / f"master_database_backup_before_retry_cleanup_{timestamp}.json"
            
            import shutil
            shutil.copy2(self.db_path, backup_path)
            print(f"✅ 已创建备份: {backup_path}")
            self.backup_created = True
    
    def clean_model_prompt_data(self, model: str, prompt_types: List[str], 
                               difficulty: str = "easy", task_types: List[str] = None,
                               clean_timeouts: bool = True):
        """
        清理指定模型的特定prompt类型数据
        
        Args:
            model: 模型名称
            prompt_types: 要清理的prompt类型列表
            difficulty: 难度级别 (默认: "easy") 
            task_types: 任务类型列表 (默认: ["simple_task", "basic_task", "data_pipeline", "api_integration", "multi_stage_pipeline"])
            clean_timeouts: 是否同时清理明显的超时错误数据 (默认: True)
        """
        if not self.db_path.exists():
            print(f"❌ 数据库文件不存在: {self.db_path}")
            return False
        
        # 创建备份
        self.create_backup()
        
        # 默认任务类型
        if task_types is None:
            task_types = ["simple_task", "basic_task", "data_pipeline", "api_integration", "multi_stage_pipeline"]
        
        try:
            # 读取数据库
            with open(self.db_path, 'r', encoding='utf-8') as f:
                db = json.load(f)
            
            if model not in db.get('models', {}):
                print(f"⚠️  模型 {model} 在数据库中不存在")
                return True
            
            model_data = db['models'][model]
            by_prompt_type = model_data.get('by_prompt_type', {})
            
            cleaned_configs = []
            total_cleaned_tests = 0
            
            # 清理指定的prompt类型数据
            for prompt_type in prompt_types:
                if prompt_type in by_prompt_type:
                    prompt_data = by_prompt_type[prompt_type]
                    
                    # 清理 by_tool_success_rate/0.8/difficulty/task_type 层次
                    by_rate = prompt_data.get('by_tool_success_rate', {})
                    if '0.8' in by_rate:
                        rate_data = by_rate['0.8']
                        by_diff = rate_data.get('by_difficulty', {})
                        
                        if difficulty in by_diff:
                            diff_data = by_diff[difficulty]
                            by_task = diff_data.get('by_task_type', {})
                            
                            # 清理指定任务类型的数据
                            for task_type in task_types:
                                if task_type in by_task:
                                    task_data = by_task[task_type]
                                    total_tests = task_data.get('total', 0)
                                    
                                    if total_tests > 0:
                                        cleaned_configs.append(f"{prompt_type}/0.8/{difficulty}/{task_type}")
                                        total_cleaned_tests += total_tests
                                        
                                        # 删除该配置的所有数据
                                        del by_task[task_type]
                            
                            # 如果by_task_type为空，删除difficulty层
                            if not by_task:
                                del by_diff[difficulty]
                        
                        # 如果by_difficulty为空，删除rate层
                        if not by_diff:
                            del by_rate['0.8']
                    
                    # 如果by_tool_success_rate为空，删除prompt_type层
                    if not by_rate:
                        del by_prompt_type[prompt_type]
            
            # 重新计算模型的总测试数
            new_total_tests = self._recalculate_model_total(model_data)
            model_data['total_tests'] = new_total_tests
            
            # 清理overall_stats（重新计算）
            model_data['overall_stats'] = {}
            
            # 更新数据库时间戳
            db['last_updated'] = datetime.now().isoformat()
            
            # 保存数据库
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(db, f, indent=2, ensure_ascii=False)
            
            print(f"✅ 已清理模型 {model} 的数据:")
            print(f"   清理的配置: {len(cleaned_configs)} 个")
            print(f"   清理的测试数: {total_cleaned_tests} 个")
            for config in cleaned_configs:
                print(f"   - {config}")
            print(f"   模型新的总测试数: {new_total_tests}")
            
            return True
            
        except Exception as e:
            print(f"❌ 清理失败: {e}")
            return False
    
    def _recalculate_model_total(self, model_data: Dict[str, Any]) -> int:
        """重新计算模型的总测试数"""
        total = 0
        by_prompt_type = model_data.get('by_prompt_type', {})
        
        for prompt_type, prompt_data in by_prompt_type.items():
            by_rate = prompt_data.get('by_tool_success_rate', {})
            for rate, rate_data in by_rate.items():
                by_diff = rate_data.get('by_difficulty', {})
                for diff, diff_data in by_diff.items():
                    by_task = diff_data.get('by_task_type', {})
                    for task, task_data in by_task.items():
                        total += task_data.get('total', 0)
        
        return total
    
    def clean_failed_test_configs(self, failed_tests_config: Dict[str, Any]):
        """
        根据failed_tests_config.json清理对应的数据库配置
        
        Args:
            failed_tests_config: 失败测试配置字典
        """
        if 'active_session' not in failed_tests_config:
            print("❌ 无效的失败测试配置格式")
            return False
        
        active_session = failed_tests_config['active_session']
        failed_tests = active_session.get('failed_tests', {})
        
        total_cleaned = 0
        
        for model, test_list in failed_tests.items():
            for test in test_list:
                if test.get('status') == 'retrying':
                    prompt_types_str = test.get('prompt_types', '')
                    prompt_types = [pt.strip() for pt in prompt_types_str.split(',') if pt.strip()]
                    
                    if prompt_types:
                        print(f"\n🧹 清理模型 {model} 的重测数据...")
                        success = self.clean_model_prompt_data(
                            model=model,
                            prompt_types=prompt_types,
                            difficulty="easy",  # 从配置推断难度为easy
                            task_types=["simple_task", "basic_task", "data_pipeline", "api_integration", "multi_stage_pipeline"]
                        )
                        if success:
                            total_cleaned += 1
        
        print(f"\n✅ 完成清理，处理了 {total_cleaned} 个模型的重测数据")
        return total_cleaned > 0
    
    def clean_timeout_errors(self, timeout_threshold: float = 600.0):
        """
        清理数据库中明显的超时错误数据
        
        Args:
            timeout_threshold: 超时阈值（秒），默认600秒
        """
        if not self.db_path.exists():
            print(f"❌ 数据库文件不存在: {self.db_path}")
            return False
        
        # 创建备份
        self.create_backup()
        
        try:
            # 读取数据库
            with open(self.db_path, 'r', encoding='utf-8') as f:
                db = json.load(f)
            
            total_cleaned = 0
            timeout_configs = []
            
            for model_name, model_data in db.get('models', {}).items():
                by_prompt_type = model_data.get('by_prompt_type', {})
                
                for prompt_type, prompt_data in by_prompt_type.items():
                    by_rate = prompt_data.get('by_tool_success_rate', {})
                    
                    for rate, rate_data in by_rate.items():
                        by_diff = rate_data.get('by_difficulty', {})
                        
                        for diff, diff_data in by_diff.items():
                            by_task = diff_data.get('by_task_type', {})
                            
                            configs_to_remove = []
                            for task_type, task_data in by_task.items():
                                avg_execution_time = task_data.get('avg_execution_time', 0)
                                total_tests = task_data.get('total', 0)
                                success_rate = task_data.get('success_rate', 0)
                                
                                # 检测明显的超时错误：
                                # 1. 平均执行时间达到或接近超时阈值
                                # 2. 成功率为0（完全失败）
                                # 3. 有测试数据
                                if (avg_execution_time >= timeout_threshold and 
                                    success_rate == 0 and 
                                    total_tests > 0):
                                    
                                    config_id = f"{model_name}/{prompt_type}/{rate}/{diff}/{task_type}"
                                    timeout_configs.append({
                                        "config": config_id,
                                        "total_tests": total_tests,
                                        "avg_execution_time": avg_execution_time
                                    })
                                    configs_to_remove.append(task_type)
                                    total_cleaned += total_tests
                            
                            # 删除超时配置
                            for task_type in configs_to_remove:
                                del by_task[task_type]
                            
                            # 清理空的层级
                            if not by_task:
                                del by_diff[diff]
                        
                        if not by_diff:
                            del by_rate[rate]
                    
                    if not by_rate:
                        del by_prompt_type[prompt_type]
                
                # 重新计算模型的总测试数
                new_total_tests = self._recalculate_model_total(model_data)
                model_data['total_tests'] = new_total_tests
                
                # 清理overall_stats（重新计算）
                model_data['overall_stats'] = {}
            
            # 更新数据库时间戳
            db['last_updated'] = datetime.now().isoformat()
            
            # 保存数据库
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(db, f, indent=2, ensure_ascii=False)
            
            print(f"✅ 已清理明显的超时错误数据:")
            print(f"   清理的配置: {len(timeout_configs)} 个")
            print(f"   清理的测试数: {total_cleaned} 个")
            print(f"   超时阈值: {timeout_threshold}秒")
            
            if timeout_configs:
                print("\n清理的超时配置:")
                for config in timeout_configs:
                    print(f"   - {config['config']}: {config['total_tests']}个测试, 平均执行时间{config['avg_execution_time']}秒")
            
            return True
            
        except Exception as e:
            print(f"❌ 清理超时错误数据失败: {e}")
            return False

def main():
    """命令行接口"""
    import sys
    
    cleaner = DatabaseCleanupForRetry()
    
    if len(sys.argv) < 2:
        print("用法:")
        print("  python database_cleanup_for_retry.py clean_failed  # 根据failed_tests_config.json清理")
        print("  python database_cleanup_for_retry.py clean_model <model> <prompt_types>  # 清理指定模型")
        print("  python database_cleanup_for_retry.py clean_timeouts  # 清理明显的超时错误数据")
        return
    
    command = sys.argv[1]
    
    if command == "clean_failed":
        # 根据failed_tests_config.json清理
        config_path = Path("failed_tests_config.json")
        if not config_path.exists():
            print(f"❌ 找不到配置文件: {config_path}")
            return
        
        with open(config_path, 'r', encoding='utf-8') as f:
            failed_config = json.load(f)
        
        cleaner.clean_failed_test_configs(failed_config)
        
    elif command == "clean_model" and len(sys.argv) >= 4:
        # 清理指定模型
        model = sys.argv[2]
        prompt_types = sys.argv[3].split(',')
        
        cleaner.clean_model_prompt_data(
            model=model,
            prompt_types=prompt_types,
            difficulty="easy"
        )
        
    elif command == "clean_timeouts":
        # 清理明显的超时错误数据
        cleaner.clean_timeout_errors()
        
    else:
        print("❌ 无效的命令或参数")

if __name__ == "__main__":
    main()