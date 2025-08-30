#!/usr/bin/env python3
"""
增强的失败测试自动管理器
- 自动检测和记录测试失败
- 维护失败记录状态
- 支持进度同步和状态更新
"""

import json
import os
import time
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from contextlib import contextmanager

@dataclass
class FailedTest:
    """失败测试记录"""
    model: str
    group_name: str
    prompt_types: str
    test_type: str
    failure_reason: str
    failure_time: str
    retry_count: int = 0
    max_retries: int = 3
    status: str = "failed"  # failed, retrying, completed, abandoned
    
    def to_dict(self):
        return asdict(self)

@dataclass 
class TestProgress:
    """测试进度记录"""
    step: str
    model_index: int
    substep: str
    current_model: str = ""
    current_group: str = ""
    total_models: int = 0
    completed_models: int = 0
    failed_models: List[str] = None
    
    def __post_init__(self):
        if self.failed_models is None:
            self.failed_models = []

class EnhancedFailedTestsManager:
    """增强的失败测试管理器"""
    
    def __init__(self, config_file=None, progress_file=None, model_type=None):
        # 根据模型类型选择配置文件
        if config_file is None:
            # 优先使用环境变量中的模型类型
            if model_type is None:
                model_type = os.environ.get('MODEL_TYPE', 'opensource')
            
            if model_type == 'closed_source':
                config_file = "failed_tests_config_closed_source.json"
            else:
                config_file = "failed_tests_config_opensource.json"
        
        if progress_file is None:
            if model_type is None:
                model_type = os.environ.get('MODEL_TYPE', 'opensource')
            
            if model_type == 'closed_source':
                progress_file = "test_progress_closed_source.txt"
            else:
                progress_file = "test_progress_opensource.txt"
        
        self.config_file = Path(config_file)
        self.progress_file = Path(progress_file)
        self.model_type = model_type or os.environ.get('MODEL_TYPE', 'opensource')
        self.lock = threading.Lock()
        self._load_config()
        
    def _load_config(self):
        """加载配置文件"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                self._create_empty_config()
        else:
            self._create_empty_config()
    
    def _create_empty_config(self):
        """创建空的配置文件结构"""
        self.config = {
            "version": "2.0",
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "active_session": {
                "session_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
                "start_time": datetime.now().isoformat(),
                "status": "active",  # active, completed, paused
                "total_failed_tests": 0,
                "failed_tests": {},  # model -> [FailedTest]
                "completed_retests": {},
                "abandoned_tests": {}
            },
            "progress_tracking": {
                "current_step": "",
                "current_model": "",
                "completed_steps": [],
                "failed_steps": [],
                "retry_queue": []
            },
            "statistics": {
                "total_tests_run": 0,
                "total_failures": 0,
                "total_retries": 0,
                "total_recoveries": 0,
                "failure_rate": 0.0,
                "recovery_rate": 0.0
            }
        }
    
    def _save_config(self):
        """保存配置文件"""
        with self.lock:
            self.config["last_updated"] = datetime.now().isoformat()
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def record_test_failure(self, model: str, group_name: str, prompt_types: str, 
                          test_type: str, failure_reason: str, context: Dict = None):
        """记录测试失败"""
        failed_test = FailedTest(
            model=model,
            group_name=group_name,
            prompt_types=prompt_types,
            test_type=test_type,
            failure_reason=failure_reason,
            failure_time=datetime.now().isoformat()
        )
        
        session = self.config["active_session"]
        if model not in session["failed_tests"]:
            session["failed_tests"][model] = []
        
        session["failed_tests"][model].append(failed_test.to_dict())
        session["total_failed_tests"] += 1
        
        # 更新统计
        stats = self.config["statistics"]
        stats["total_failures"] += 1
        stats["total_tests_run"] = stats.get("total_tests_run", 0) + 1
        if stats["total_tests_run"] > 0:
            stats["failure_rate"] = stats["total_failures"] / stats["total_tests_run"]
        
        self._save_config()
        
        print(f"🔴 记录失败: {model} - {group_name}")
        print(f"   原因: {failure_reason}")
        print(f"   时间: {failed_test.failure_time}")
        
        return failed_test
    
    def record_test_success(self, model: str, group_name: str, was_retry: bool = False):
        """记录测试成功（特别是重测成功）"""
        if was_retry:
            session = self.config["active_session"]
            if model not in session["completed_retests"]:
                session["completed_retests"][model] = []
            
            session["completed_retests"][model].append({
                "group_name": group_name,
                "completed_time": datetime.now().isoformat(),
                "retry_success": True
            })
            
            # 更新统计
            stats = self.config["statistics"]
            stats["total_recoveries"] += 1
            if stats["total_failures"] > 0:
                stats["recovery_rate"] = stats["total_recoveries"] / stats["total_failures"]
            
            print(f"🟢 重测成功: {model} - {group_name}")
        
        self._save_config()
    
    def get_failed_tests_for_model(self, model: str) -> List[Dict]:
        """获取某个模型的失败测试"""
        session = self.config["active_session"]
        return session["failed_tests"].get(model, [])
    
    def get_all_failed_models(self) -> List[str]:
        """获取所有有失败测试的模型"""
        session = self.config["active_session"]
        return list(session["failed_tests"].keys())
    
    def has_failed_tests(self) -> bool:
        """检查是否有失败的测试"""
        session = self.config["active_session"]
        return session["total_failed_tests"] > 0
    
    def get_retry_queue(self) -> List[Dict]:
        """获取重试队列"""
        retry_queue = []
        session = self.config["active_session"]
        
        for model, failed_tests in session["failed_tests"].items():
            for test in failed_tests:
                # 包含状态为 "failed" 或 "retrying" 的测试，且未超过最大重试次数
                if test["status"] in ["failed", "retrying"] and test["retry_count"] < test["max_retries"]:
                    retry_queue.append({
                        "model": model,
                        "test": test,
                        "priority": test["retry_count"]  # 重试次数少的优先
                    })
        
        # 按优先级排序
        retry_queue.sort(key=lambda x: x["priority"])
        return retry_queue
    
    def mark_test_for_retry(self, model: str, group_name: str):
        """标记测试为重试状态"""
        session = self.config["active_session"]
        if model in session["failed_tests"]:
            for test in session["failed_tests"][model]:
                if test["group_name"] == group_name:
                    test["status"] = "retrying"
                    test["retry_count"] += 1
                    test["last_retry_time"] = datetime.now().isoformat()
                    break
        
        # 更新统计
        stats = self.config["statistics"]
        stats["total_retries"] += 1
        
        self._save_config()
    
    def abandon_test(self, model: str, group_name: str, reason: str):
        """放弃测试（超过最大重试次数）"""
        session = self.config["active_session"]
        if model in session["failed_tests"]:
            for test in session["failed_tests"][model]:
                if test["group_name"] == group_name:
                    test["status"] = "abandoned"
                    test["abandon_reason"] = reason
                    test["abandon_time"] = datetime.now().isoformat()
                    
                    # 移动到放弃列表
                    if model not in session["abandoned_tests"]:
                        session["abandoned_tests"][model] = []
                    session["abandoned_tests"][model].append(test)
                    break
        
        self._save_config()
        print(f"🚫 放弃测试: {model} - {group_name} ({reason})")
    
    def update_progress(self, step: str, model_index: int, substep: str, 
                       current_model: str = "", current_group: str = ""):
        """更新测试进度"""
        progress = self.config["progress_tracking"]
        progress.update({
            "current_step": step,
            "current_model": current_model,
            "current_group": current_group,
            "model_index": model_index,
            "substep": substep,
            "last_update": datetime.now().isoformat()
        })
        
        self._save_config()
    
    def generate_retry_script(self, output_file: str = "auto_retry_failed_tests.sh"):
        """生成自动重试脚本"""
        retry_queue = self.get_retry_queue()
        
        if not retry_queue:
            print("没有需要重试的测试")
            return
        
        script_content = f'''#!/bin/bash

# 自动生成的失败测试重试脚本
# 生成时间: {datetime.now().isoformat()}
# 待重试测试数: {len(retry_queue)}

set -e

echo "开始自动重试失败的测试..."
echo "总共 {len(retry_queue)} 个测试需要重试"
echo ""

'''
        
        for i, item in enumerate(retry_queue, 1):
            model = item["model"]
            test = item["test"]
            
            script_content += f'''
echo "=== 重试 {i}/{len(retry_queue)}: {model} - {test["group_name"]} ==="
echo "重试原因: {test["failure_reason"]}"
echo "重试次数: {test["retry_count"] + 1}/{test["max_retries"]}"

# 标记为重试状态
python3 -c "
from enhanced_failed_tests_manager import EnhancedFailedTestsManager
manager = EnhancedFailedTestsManager()
manager.mark_test_for_retry('{model}', '{test["group_name"]}')
"

# 执行重试
if python ultra_parallel_runner.py \\
    --model "{model}" \\
    --prompt-types "{test["prompt_types"]}" \\
    --difficulty easy \\
    --task-types all \\
    --num-instances 20; then
    
    echo "✅ 重试成功: {model} - {test["group_name"]}"
    
    # 标记为成功
    python3 -c "
from enhanced_failed_tests_manager import EnhancedFailedTestsManager
manager = EnhancedFailedTestsManager()
manager.record_test_success('{model}', '{test["group_name"]}', was_retry=True)
"
else
    echo "❌ 重试失败: {model} - {test["group_name"]}"
    
    # 检查是否需要放弃
    python3 -c "
from enhanced_failed_tests_manager import EnhancedFailedTestsManager
manager = EnhancedFailedTestsManager()
test = manager.get_failed_tests_for_model('{model}')
for t in test:
    if t['group_name'] == '{test["group_name"]}' and t['retry_count'] >= t['max_retries']:
        manager.abandon_test('{model}', '{test["group_name"]}', 'Max retries exceeded')
        break
"
fi

echo ""
'''
        
        script_content += '''
echo "自动重试完成"
echo ""
echo "查看最终状态:"
python3 -c "
from enhanced_failed_tests_manager import EnhancedFailedTestsManager
manager = EnhancedFailedTestsManager()
print(f'总失败数: {manager.config[\"statistics\"][\"total_failures\"]}')
print(f'总恢复数: {manager.config[\"statistics\"][\"total_recoveries\"]}')
print(f'恢复率: {manager.config[\"statistics\"][\"recovery_rate\"]:.1%}')
"
'''
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        os.chmod(output_file, 0o755)
        print(f"✅ 生成重试脚本: {output_file}")
        return output_file
    
    def show_status_report(self):
        """显示状态报告"""
        print("=" * 50)
        print("📊 失败测试管理器状态报告")
        print("=" * 50)
        
        session = self.config["active_session"]
        stats = self.config["statistics"]
        
        print(f"会话ID: {session['session_id']}")
        print(f"会话状态: {session['status']}")
        print(f"开始时间: {session['start_time']}")
        print()
        
        print("📈 统计信息:")
        print(f"  总测试数: {stats['total_tests_run']}")
        print(f"  总失败数: {stats['total_failures']}")
        print(f"  总重试数: {stats['total_retries']}")
        print(f"  总恢复数: {stats['total_recoveries']}")
        print(f"  失败率: {stats['failure_rate']:.1%}")
        print(f"  恢复率: {stats['recovery_rate']:.1%}")
        print()
        
        if session["failed_tests"]:
            print("🔴 失败的模型和测试:")
            for model, tests in session["failed_tests"].items():
                active_failures = [t for t in tests if t["status"] == "failed"]
                if active_failures:
                    print(f"  {model}: {len(active_failures)} 个失败测试")
                    for test in active_failures:
                        print(f"    - {test['group_name']} ({test['failure_reason']})")
        
        retry_queue = self.get_retry_queue()
        if retry_queue:
            print(f"\n⏳ 待重试队列: {len(retry_queue)} 个测试")
        
        if session.get("completed_retests"):
            print(f"\n🟢 成功重测: {len(session['completed_retests'])} 个模型")
        
        if session.get("abandoned_tests"):
            print(f"\n🚫 已放弃: {len(session['abandoned_tests'])} 个模型")

def main():
    """命令行接口"""
    import sys
    
    manager = EnhancedFailedTestsManager()
    
    if len(sys.argv) < 2:
        manager.show_status_report()
        return
    
    command = sys.argv[1]
    
    if command == "status":
        manager.show_status_report()
    elif command == "retry":
        script_file = manager.generate_retry_script()
        print(f"运行重试脚本: ./{script_file}")
    elif command == "queue":
        retry_queue = manager.get_retry_queue()
        print(f"重试队列: {len(retry_queue)} 个测试")
        for item in retry_queue:
            test = item["test"]
            print(f"  {item['model']} - {test['group_name']} (重试 {test['retry_count']}/{test['max_retries']})")
    else:
        print(f"未知命令: {command}")
        print("可用命令: status, retry, queue")

if __name__ == "__main__":
    main()