#!/usr/bin/env python3
"""
自动失败维护系统
- 自动检测和维护失败记录
- 智能重测策略
- 基于现有进度的增量重测
- 与现有系统无缝集成
"""

import json
import os
import sys
import time
import subprocess
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, asdict
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))
from enhanced_failed_tests_manager import EnhancedFailedTestsManager
from enhanced_progress_manager import EnhancedProgressManager
from database_utils import load_database, get_completed_count, get_all_models_from_database, get_model_test_summary

@dataclass
class RetryStrategy:
    """重试策略配置"""
    max_retries: int = 3
    retry_delay: int = 300  # 5分钟
    backoff_multiplier: float = 1.5
    priority_models: List[str] = None
    skip_models: List[str] = None
    retry_on_timeout: bool = True
    retry_on_api_error: bool = True
    retry_on_format_error: bool = False
    
    def __post_init__(self):
        if self.priority_models is None:
            self.priority_models = []
        if self.skip_models is None:
            self.skip_models = []

@dataclass
class AutoRetestConfig:
    """自动重测配置"""
    enabled: bool = True
    include_partial_failures: bool = True
    retest_timeout_failures: bool = True
    retest_api_failures: bool = True
    retest_format_failures: bool = False
    # 新的重测逻辑：基于完全失败 + 平均执行时间达到上限
    complete_failure_threshold: float = 0.0  # 成功率为0（完全失败）
    max_execution_time: float = 300.0        # 最大执行时间阈值（秒）
    cooldown_hours: int = 2                  # 重测冷却期
    batch_size: int = 5                      # 重测批次大小
    # 保留旧配置以向后兼容（已弃用）
    minimum_completion_rate: float = 0.8     # 已弃用
    maximum_failure_rate: float = 0.3        # 已弃用
    
class AutoFailureMaintenanceSystem:
    """自动失败维护系统"""
    
    def __init__(self, 
                 config_file: str = "auto_maintenance_config.json",
                 enable_auto_retry: bool = True):
        self.config_file = Path(config_file)
        self.failed_manager = EnhancedFailedTestsManager()
        self.progress_manager = EnhancedProgressManager()
        self.enable_auto_retry = enable_auto_retry
        self.lock = threading.Lock()
        self._load_config()
        
        # 监控线程
        self._monitoring = False
        self._monitor_thread = None
        
    def _load_config(self):
        """加载配置文件"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                self.retry_strategy = RetryStrategy(**config_data.get("retry_strategy", {}))
                self.auto_retest_config = AutoRetestConfig(**config_data.get("auto_retest", {}))
            except Exception as e:
                print(f"加载配置失败: {e}")
                self._create_default_config()
        else:
            self._create_default_config()
    
    def _create_default_config(self):
        """创建默认配置"""
        self.retry_strategy = RetryStrategy()
        self.auto_retest_config = AutoRetestConfig()
        self._save_config()
    
    def _save_config(self):
        """保存配置文件"""
        config_data = {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "retry_strategy": asdict(self.retry_strategy),
            "auto_retest": asdict(self.auto_retest_config)
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
    
    def analyze_test_completion(self, models: List[str] = None) -> Dict[str, Any]:
        """分析测试完成情况"""
        db = load_database()
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "models_analyzed": [],
            "completion_summary": {},
            "failure_patterns": {},
            "retry_recommendations": []
        }
        
        if not models:
            models = list(db.get("models", {}).keys())
        
        for model in models:
            model_analysis = self._analyze_model_completion(model, db)
            analysis["models_analyzed"].append(model)
            analysis["completion_summary"][model] = model_analysis
            
            # 检测失败模式
            failure_pattern = self._detect_failure_patterns(model, model_analysis)
            if failure_pattern:
                analysis["failure_patterns"][model] = failure_pattern
            
            # 生成重试建议
            retry_rec = self._generate_retry_recommendation(model, model_analysis)
            if retry_rec:
                analysis["retry_recommendations"].append(retry_rec)
        
        return analysis
    
    def _analyze_model_completion(self, model: str, db: Dict) -> Dict[str, Any]:
        """分析单个模型的完成情况"""
        model_data = db.get("models", {}).get(model, {})
        
        if not model_data:
            return {"status": "no_data", "completion_rate": 0.0}
        
        # 统计各个维度的完成情况和执行时间
        total_tests = 0
        completed_tests = 0
        failed_tests = 0
        total_execution_time = 0.0
        execution_time_count = 0
        complete_failure_configs = []
        high_execution_time_configs = []
        
        # V3数据库结构分析
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
                                        avg_exec_time = task_data.get("avg_execution_time", 0.0)
                                        
                                        total_tests += total
                                        completed_tests += success
                                        failed_tests += (total - success)
                                        
                                        # 统计执行时间
                                        if avg_exec_time > 0:
                                            total_execution_time += avg_exec_time * total
                                            execution_time_count += total
                                        
                                        # 检查完全失败（成功率为0）
                                        if total > 0 and success == 0:
                                            config_id = f"{prompt_type}/{rate}/{difficulty}/{task_type}"
                                            complete_failure_configs.append({
                                                "config": config_id,
                                                "total_tests": total,
                                                "avg_execution_time": avg_exec_time
                                            })
                                        
                                        # 检查高执行时间
                                        if avg_exec_time >= self.auto_retest_config.max_execution_time:
                                            config_id = f"{prompt_type}/{rate}/{difficulty}/{task_type}"
                                            high_execution_time_configs.append({
                                                "config": config_id,
                                                "total_tests": total,
                                                "success_tests": success,
                                                "avg_execution_time": avg_exec_time
                                            })
        
        completion_rate = completed_tests / total_tests if total_tests > 0 else 0.0
        failure_rate = failed_tests / total_tests if total_tests > 0 else 0.0
        avg_execution_time = total_execution_time / execution_time_count if execution_time_count > 0 else 0.0
        
        # 新的重测逻辑：基于完全失败 + 平均执行时间达到上限
        needs_retry_complete_failure = len(complete_failure_configs) > 0
        needs_retry_high_execution_time = avg_execution_time >= self.auto_retest_config.max_execution_time
        needs_retry = needs_retry_complete_failure or needs_retry_high_execution_time
        
        return {
            "status": "analyzed",
            "total_tests": total_tests,
            "completed_tests": completed_tests,
            "failed_tests": failed_tests,
            "completion_rate": completion_rate,
            "failure_rate": failure_rate,
            "avg_execution_time": avg_execution_time,
            "complete_failure_configs": complete_failure_configs,
            "high_execution_time_configs": high_execution_time_configs,
            "needs_retry": needs_retry,
            "needs_retry_complete_failure": needs_retry_complete_failure,
            "needs_retry_high_execution_time": needs_retry_high_execution_time,
            # 保留旧的逻辑以向后兼容
            "needs_retry_legacy": completion_rate < self.auto_retest_config.minimum_completion_rate or 
                                 failure_rate > self.auto_retest_config.maximum_failure_rate
        }
    
    def _detect_failure_patterns(self, model: str, analysis: Dict) -> Optional[Dict]:
        """检测失败模式（新逻辑：基于完全失败+高执行时间）"""
        if analysis.get("status") != "analyzed":
            return None
        
        patterns = {}
        
        # 完全失败模式
        if analysis.get("needs_retry_complete_failure", False):
            patterns["complete_failure"] = {
                "description": "存在完全失败的配置（成功率为0）",
                "configs": analysis.get("complete_failure_configs", []),
                "severity": "high",
                "recommendation": "需要重测完全失败的配置"
            }
        
        # 高执行时间模式
        if analysis.get("needs_retry_high_execution_time", False):
            patterns["high_execution_time"] = {
                "description": f"平均执行时间超过阈值（{self.auto_retest_config.max_execution_time}秒）",
                "avg_execution_time": analysis.get("avg_execution_time", 0),
                "configs": analysis.get("high_execution_time_configs", []),
                "severity": "medium",
                "recommendation": "可能存在性能问题或超时问题，建议重测"
            }
        
        # 保留旧的失败率检查以向后兼容
        if analysis["failure_rate"] > self.auto_retest_config.maximum_failure_rate:
            patterns["high_failure_rate_legacy"] = {
                "severity": "high",
                "failure_rate": analysis["failure_rate"],
                "threshold": self.auto_retest_config.maximum_failure_rate,
                "description": "遗留逻辑：高失败率模式（已弃用）",
                "severity": "low"
            }
        
        # 低完成率模式
        if analysis["completion_rate"] < self.auto_retest_config.minimum_completion_rate:
            patterns["low_completion_rate"] = {
                "severity": "medium",
                "completion_rate": analysis["completion_rate"],
                "threshold": self.auto_retest_config.minimum_completion_rate
            }
        
        return patterns if patterns else None
    
    def _generate_retry_recommendation(self, model: str, analysis: Dict) -> Optional[Dict]:
        """生成重试建议"""
        if not analysis.get("needs_retry"):
            return None
        
        recommendation = {
            "model": model,
            "priority": "normal",
            "reason": [],
            "suggested_configs": []
        }
        
        # 优先级判断
        if model in self.retry_strategy.priority_models:
            recommendation["priority"] = "high"
        
        # 判断重试原因
        if analysis["completion_rate"] < self.auto_retest_config.minimum_completion_rate:
            recommendation["reason"].append(f"低完成率: {analysis['completion_rate']:.1%}")
        
        if analysis["failure_rate"] > self.auto_retest_config.maximum_failure_rate:
            recommendation["reason"].append(f"高失败率: {analysis['failure_rate']:.1%}")
        
        # 建议配置
        recommendation["suggested_configs"] = self._suggest_retry_configs(model, analysis)
        
        return recommendation
    
    def _suggest_retry_configs(self, model: str, analysis: Dict) -> List[Dict]:
        """建议重试配置"""
        configs = []
        
        # 基础重试配置
        base_config = {
            "model": model,
            "prompt_types": "baseline",
            "difficulty": "easy",
            "task_types": "all",
            "num_instances": 20,
            "tool_success_rate": 0.8
        }
        
        # 如果失败率很高，降低难度
        if analysis["failure_rate"] > 0.5:
            base_config["difficulty"] = "easy"
            base_config["num_instances"] = 10
        
        configs.append(base_config)
        
        # 如果是重要模型，添加更全面的测试
        if model in self.retry_strategy.priority_models:
            comprehensive_config = base_config.copy()
            comprehensive_config.update({
                "prompt_types": "baseline,cot,optimal",
                "num_instances": 50
            })
            configs.append(comprehensive_config)
        
        return configs
    
    def get_incomplete_tests(self, models: List[str] = None) -> Dict[str, List[Dict]]:
        """获取未完成的测试配置"""
        incomplete_tests = defaultdict(list)
        
        if not models:
            db = load_database()
            models = list(db.get("models", {}).keys())
        
        # 标准测试配置
        standard_configs = [
            {"prompt_type": "baseline", "difficulty": "easy", "task_type": "simple_task", "num_instances": 20},
            {"prompt_type": "baseline", "difficulty": "easy", "task_type": "basic_task", "num_instances": 20},
            {"prompt_type": "cot", "difficulty": "easy", "task_type": "simple_task", "num_instances": 20},
            {"prompt_type": "optimal", "difficulty": "easy", "task_type": "simple_task", "num_instances": 20},
        ]
        
        for model in models:
            for config in standard_configs:
                completed = get_completed_count(
                    model=model,
                    prompt_type=config["prompt_type"],
                    difficulty=config["difficulty"],
                    task_type=config["task_type"]
                )
                
                if completed < config["num_instances"]:
                    missing = config["num_instances"] - completed
                    test_config = config.copy()
                    test_config.update({
                        "model": model,
                        "missing_count": missing,
                        "completed_count": completed
                    })
                    incomplete_tests[model].append(test_config)
        
        return dict(incomplete_tests)
    
    def auto_maintain_failures(self) -> Dict[str, Any]:
        """自动维护失败记录"""
        if not self.auto_retest_config.enabled:
            return {"status": "disabled"}
        
        print("🔧 开始自动失败维护...")
        
        # 分析当前状态
        analysis = self.analyze_test_completion()
        
        # 获取未完成测试
        incomplete_tests = self.get_incomplete_tests()
        
        # 生成维护计划
        maintenance_plan = {
            "timestamp": datetime.now().isoformat(),
            "analysis_summary": {
                "models_analyzed": len(analysis["models_analyzed"]),
                "models_with_failures": len(analysis["failure_patterns"]),
                "retry_recommendations": len(analysis["retry_recommendations"])
            },
            "actions_taken": [],
            "incomplete_tests": incomplete_tests
        }
        
        # 执行自动重试（如果启用）
        if self.enable_auto_retry and analysis["retry_recommendations"]:
            retry_results = self._execute_auto_retries(analysis["retry_recommendations"])
            maintenance_plan["actions_taken"].extend(retry_results)
        
        # 更新失败记录
        self._update_failure_records(analysis, incomplete_tests)
        
        print(f"✅ 自动维护完成，分析了 {len(analysis['models_analyzed'])} 个模型")
        if analysis["retry_recommendations"]:
            print(f"📋 生成了 {len(analysis['retry_recommendations'])} 个重试建议")
        
        return maintenance_plan
    
    def _execute_auto_retries(self, recommendations: List[Dict]) -> List[Dict]:
        """执行自动重试"""
        results = []
        
        # 按优先级排序
        recommendations.sort(key=lambda x: 0 if x["priority"] == "high" else 1)
        
        for rec in recommendations[:self.auto_retest_config.batch_size]:
            if rec["model"] in self.retry_strategy.skip_models:
                continue
            
            for config in rec["suggested_configs"]:
                result = self._execute_single_retry(config)
                results.append(result)
                
                # 添加延迟避免过载
                time.sleep(self.retry_strategy.retry_delay)
        
        return results
    
    def _execute_single_retry(self, config: Dict) -> Dict:
        """执行单个重试"""
        print(f"🔄 执行重试: {config['model']}")
        
        # 构建命令
        cmd = [
            "python", "smart_batch_runner.py",
            "--model", config["model"],
            "--prompt-types", config["prompt_types"],
            "--difficulty", config["difficulty"],
            "--task-types", config["task_types"],
            "--num-instances", str(config["num_instances"]),
            "--tool-success-rate", str(config.get("tool_success_rate", 0.8)),
            "--max-workers", "1",
            "--no-save-logs"
        ]
        
        start_time = datetime.now()
        try:
            # 记录重试开始
            self.failed_manager.mark_test_for_retry(
                config["model"], 
                f"{config['prompt_types']}_{config['difficulty']}"
            )
            
            # 执行测试
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
            
            success = result.returncode == 0
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # 记录结果
            if success:
                self.failed_manager.record_test_success(
                    config["model"],
                    f"{config['prompt_types']}_{config['difficulty']}",
                    was_retry=True
                )
            
            return {
                "model": config["model"],
                "config": config,
                "success": success,
                "duration": duration,
                "stdout": result.stdout[-500:] if result.stdout else "",
                "stderr": result.stderr[-500:] if result.stderr else ""
            }
            
        except subprocess.TimeoutExpired:
            return {
                "model": config["model"],
                "config": config,
                "success": False,
                "duration": 1800,
                "error": "timeout"
            }
        except Exception as e:
            return {
                "model": config["model"],
                "config": config,
                "success": False,
                "duration": 0,
                "error": str(e)
            }
    
    def _update_failure_records(self, analysis: Dict, incomplete_tests: Dict):
        """更新失败记录"""
        for model, patterns in analysis["failure_patterns"].items():
            for pattern_type, pattern_data in patterns.items():
                self.failed_manager.record_test_failure(
                    model=model,
                    group_name=f"auto_detected_{pattern_type}",
                    prompt_types="multiple",
                    test_type="pattern_detection",
                    failure_reason=f"{pattern_type}: {pattern_data}",
                    context={"analysis": analysis, "incomplete": incomplete_tests.get(model, [])}
                )
    
    def generate_retest_script(self, models: List[str] = None, 
                             output_file: str = "auto_retest_incomplete.sh") -> str:
        """生成重测脚本"""
        incomplete_tests = self.get_incomplete_tests(models)
        
        if not incomplete_tests:
            print("没有未完成的测试需要重测")
            return None
        
        script_content = f'''#!/bin/bash

# 自动生成的重测脚本 - 基于现有进度
# 生成时间: {datetime.now().isoformat()}
# 涉及模型: {len(incomplete_tests)}

set -e

echo "开始基于现有进度的自动重测..."
echo "涉及 {len(incomplete_tests)} 个模型"
echo ""

'''
        
        test_count = 0
        for model, tests in incomplete_tests.items():
            if model in self.retry_strategy.skip_models:
                continue
            
            script_content += f'''
echo "=== 处理模型: {model} ==="
echo "未完成测试: {len(tests)} 个配置"
'''
            
            for test_config in tests:
                test_count += 1
                missing = test_config["missing_count"]
                
                script_content += f'''
echo "  配置 {test_count}: {test_config['prompt_type']} / {test_config['task_type']}"
echo "    需要补充: {missing} 个测试"

python smart_batch_runner.py \\
    --model "{model}" \\
    --prompt-types "{test_config['prompt_type']}" \\
    --difficulty "{test_config['difficulty']}" \\
    --task-types "{test_config['task_type']}" \\
    --num-instances {missing} \\
    --tool-success-rate 0.8 \\
    --max-workers 2 \\
    --adaptive \\
    --no-save-logs

echo ""
'''
        
        script_content += f'''
echo "重测完成！"
echo "总共处理了 {test_count} 个测试配置"

# 生成状态报告
echo ""
echo "=== 最终状态报告 ==="
python auto_failure_maintenance_system.py status
'''
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        os.chmod(output_file, 0o755)
        print(f"✅ 生成重测脚本: {output_file}")
        print(f"📊 涉及 {len(incomplete_tests)} 个模型，{test_count} 个测试配置")
        
        return output_file
    
    def start_monitoring(self, interval: int = 3600):
        """启动自动监控"""
        if self._monitoring:
            print("监控已经在运行")
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval,),
            daemon=True
        )
        self._monitor_thread.start()
        print(f"🔍 启动自动监控，间隔 {interval//60} 分钟")
    
    def stop_monitoring(self):
        """停止自动监控"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        print("🛑 停止自动监控")
    
    def _monitoring_loop(self, interval: int):
        """监控循环"""
        while self._monitoring:
            try:
                print(f"🔍 执行定期检查 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                maintenance_result = self.auto_maintain_failures()
                
                # 如果发现需要处理的问题，生成报告
                if maintenance_result.get("retry_recommendations"):
                    self._generate_monitoring_report(maintenance_result)
                
            except Exception as e:
                print(f"监控检查出错: {e}")
            
            time.sleep(interval)
    
    def _generate_monitoring_report(self, maintenance_result: Dict):
        """生成监控报告"""
        report_file = f"auto_maintenance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(maintenance_result, f, indent=2, ensure_ascii=False)
        
        print(f"📋 生成监控报告: {report_file}")
    
    def show_status(self):
        """显示系统状态"""
        print("=" * 60)
        print("🔧 自动失败维护系统状态")
        print("=" * 60)
        
        # 显示配置
        print("⚙️  配置信息:")
        print(f"  自动重试: {'启用' if self.enable_auto_retry else '禁用'}")
        print(f"  自动重测: {'启用' if self.auto_retest_config.enabled else '禁用'}")
        print(f"  最小完成率阈值: {self.auto_retest_config.minimum_completion_rate:.1%}")
        print(f"  最大失败率阈值: {self.auto_retest_config.maximum_failure_rate:.1%}")
        print(f"  重试批次大小: {self.auto_retest_config.batch_size}")
        print()
        
        # 分析当前状态
        analysis = self.analyze_test_completion()
        print("📊 当前状态分析:")
        print(f"  已分析模型: {len(analysis['models_analyzed'])}")
        print(f"  发现失败模式: {len(analysis['failure_patterns'])}")
        print(f"  重试建议: {len(analysis['retry_recommendations'])}")
        print()
        
        # 显示详细分析
        if analysis["failure_patterns"]:
            print("🔴 检测到的失败模式:")
            for model, patterns in analysis["failure_patterns"].items():
                print(f"  {model}:")
                for pattern_type, data in patterns.items():
                    print(f"    - {pattern_type}: {data}")
        
        # 显示重试建议
        if analysis["retry_recommendations"]:
            print()
            print("📋 重试建议:")
            for rec in analysis["retry_recommendations"]:
                print(f"  {rec['model']} ({rec['priority']}): {', '.join(rec['reason'])}")
        
        # 显示未完成测试
        incomplete = self.get_incomplete_tests()
        if incomplete:
            print()
            print("⏳ 未完成的测试:")
            for model, tests in incomplete.items():
                total_missing = sum(t["missing_count"] for t in tests)
                print(f"  {model}: {len(tests)} 个配置，缺少 {total_missing} 个测试")
        
        print()
        print("💡 可用操作:")
        print("  python auto_failure_maintenance_system.py maintain   # 执行自动维护")
        print("  python auto_failure_maintenance_system.py retest    # 生成重测脚本") 
        print("  python auto_failure_maintenance_system.py monitor   # 启动监控")

def main():
    """命令行接口"""
    import sys
    
    system = AutoFailureMaintenanceSystem()
    
    if len(sys.argv) < 2:
        system.show_status()
        return
    
    command = sys.argv[1]
    
    if command == "status":
        system.show_status()
    elif command == "maintain":
        result = system.auto_maintain_failures()
        print(f"维护完成，处理了 {len(result.get('actions_taken', []))} 个操作")
    elif command == "retest":
        models = sys.argv[2:] if len(sys.argv) > 2 else None
        script = system.generate_retest_script(models)
        if script:
            print(f"运行重测脚本: ./{script}")
    elif command == "monitor":
        try:
            system.start_monitoring()
            print("监控已启动，按 Ctrl+C 停止")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            system.stop_monitoring()
    elif command == "incomplete":
        incomplete = system.get_incomplete_tests()
        for model, tests in incomplete.items():
            total_missing = sum(t["missing_count"] for t in tests)
            print(f"{model}: {len(tests)} 个配置，缺少 {total_missing} 个测试")
    else:
        print(f"未知命令: {command}")
        print("可用命令: status, maintain, retest, monitor, incomplete")

if __name__ == "__main__":
    main()