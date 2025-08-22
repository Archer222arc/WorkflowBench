#!/usr/bin/env python3
"""
完整集成的批量测试脚本
支持累积测试、断点续传、多难度级别、并行执行
"""

import argparse
import json
import os
import sys
import time
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict


# ===================== 配置 =====================
CUMULATIVE_RESULTS_DIR = Path("cumulative_test_results")
CUMULATIVE_RESULTS_DIR.mkdir(exist_ok=True)


# ===================== 数据类 =====================
@dataclass
class TestResult:
    """单个测试结果"""
    model: str
    task_type: str
    prompt_type: str
    difficulty_level: str
    task_complexity: str
    success: bool
    success_level: str = "failed"
    execution_time: float = 0.0
    error: str = ""
    workflow_id: str = ""
    timestamp: str = ""
    
    def to_dict(self):
        return asdict(self)


@dataclass
class TestConfig:
    """测试配置"""
    model: str
    task_types: List[str]
    prompt_types: List[str]
    difficulty: str = "easy"
    instances_per_type: int = 1
    test_flawed: bool = False
    save_logs: bool = True
    parallel: int = 4
    repeat_target: int = 100
    continue_test: bool = False


# ===================== 累积结果管理器 =====================
class CumulativeResultsManager:
    """管理累积测试结果"""
    
    def __init__(self, results_dir: Path = CUMULATIVE_RESULTS_DIR):
        self.results_dir = results_dir
        self.results_db_path = results_dir / "results_database.json"
        self.lock = threading.Lock()
        self.results_db = self._load_database()
    
    def _load_database(self) -> Dict:
        """加载或创建结果数据库"""
        if self.results_db_path.exists():
            with open(self.results_db_path, 'r') as f:
                return json.load(f)
        else:
            return {
                "created_at": datetime.now().isoformat(),
                "total_tests": 0,
                "models": {},
                "test_sessions": []
            }
    
    def save_database(self):
        """保存数据库（线程安全）"""
        with self.lock:
            with open(self.results_db_path, 'w') as f:
                json.dump(self.results_db, f, indent=2)
    
    def add_result(self, result: TestResult):
        """添加单个测试结果"""
        with self.lock:
            model = result.model
            if model not in self.results_db["models"]:
                self.results_db["models"][model] = {
                    "first_tested": datetime.now().isoformat(),
                    "total_tests": 0,
                    "results": {}
                }
            
            # 构建结果键
            key = f"{result.task_type}_{result.prompt_type}_{result.difficulty_level}"
            if result.task_type == "flawed":
                key = f"{result.task_type}_flawed_{result.prompt_type}"
            
            # 添加结果
            if key not in self.results_db["models"][model]["results"]:
                self.results_db["models"][model]["results"][key] = []
            
            self.results_db["models"][model]["results"][key].append(result.to_dict())
            self.results_db["models"][model]["total_tests"] += 1
            self.results_db["total_tests"] += 1
            
            # 定期保存
            if self.results_db["total_tests"] % 10 == 0:
                self.save_database()
    
    def get_progress(self, model: str, target_per_group: int) -> Dict:
        """获取模型的测试进度"""
        if model not in self.results_db["models"]:
            return {"groups": {}, "total": 0}
        
        model_data = self.results_db["models"][model]
        progress = {"groups": {}, "total": 0}
        
        for key, results in model_data["results"].items():
            completed = len(results)
            progress["groups"][key] = {
                "completed": completed,
                "target": target_per_group,
                "percentage": (completed / target_per_group * 100) if target_per_group > 0 else 0
            }
            progress["total"] += completed
        
        return progress


# ===================== 子进程测试运行器 =====================
class SubprocessTestRunner:
    """使用子进程运行测试以避免内存泄漏和进程挂起"""
    
    def __init__(self, results_dir: Path):
        self.results_dir = results_dir
        self.temp_dir = results_dir / "temp"
        self.temp_dir.mkdir(exist_ok=True)
    
    def create_test_script(self, config: TestConfig, batch_id: str) -> str:
        """创建在子进程中运行的测试脚本"""
        return f'''#!/usr/bin/env python3
import os
import sys
import json
import random
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, "{Path(__file__).parent}")

def run_tests():
    """运行测试批次"""
    from mdp_workflow_generator import MDPWorkflowGenerator
    from interactive_executor import InteractiveExecutor
    from flawed_workflow_generator import FlawedWorkflowGenerator
    from workflow_quality_test_flawed import ExecutionResult
    from dataclasses import asdict
    
    results = []
    
    try:
        # 初始化生成器
        generator = MDPWorkflowGenerator(
            model_path="checkpoints/best_model.pt"
        )
        
        # 加载任务库 - 根据难度级别
        difficulty = "{config.difficulty}"
        task_lib_path = f"mcp_generated_library/difficulty_versions/task_library_enhanced_v3_{{difficulty}}.json"
        
        if not Path(task_lib_path).exists():
            # 回退到默认
            task_lib_path = "mcp_generated_library/difficulty_versions/task_library_enhanced_v3_easy.json"
        
        with open(task_lib_path, 'r') as f:
            task_data = json.load(f)
        
        # 处理任务数据
        tasks = task_data.get('tasks', task_data) if isinstance(task_data, dict) else task_data
        
        # 按任务类型分组
        tasks_by_type = {{}}
        for task in tasks:
            task_type = task.get('task_type', 'unknown')
            if task_type not in tasks_by_type:
                tasks_by_type[task_type] = []
            tasks_by_type[task_type].append(task)
        
        # 运行测试
        task_types = {config.task_types}
        prompt_types = {config.prompt_types}
        instances_per_type = {config.instances_per_type}
        test_flawed = {config.test_flawed}
        
        # 缺陷生成器
        flawed_generator = None
        if test_flawed:
            flawed_generator = FlawedWorkflowGenerator(
                generator.tool_registry,
                tool_capability_manager=generator.tool_capability_manager
            )
        
        for task_type in task_types:
            # 获取任务实例
            available_tasks = tasks_by_type.get(task_type, [])
            if not available_tasks:
                print(f"警告: 没有找到任务类型 {{task_type}}")
                continue
            
            # 随机选择任务
            selected_tasks = random.sample(
                available_tasks, 
                min(instances_per_type, len(available_tasks))
            )
            
            for task_instance in selected_tasks:
                for prompt_type in prompt_types:
                    try:
                        # 生成工作流
                        workflow = generator.generate_workflow(
                            task_type=task_type,
                            task_instance=task_instance
                        )
                        
                        if not workflow:
                            continue
                        
                        # 如果需要，注入缺陷
                        if test_flawed and flawed_generator:
                            flaw_types = ['missing_step', 'wrong_order', 'infinite_loop']
                            flaw_type = random.choice(flaw_types)
                            workflow = flawed_generator.inject_specific_flaw(
                                workflow, flaw_type
                            )
                        
                        # 执行工作流
                        executor = InteractiveExecutor(
                            tool_registry=generator.tool_registry,
                            model="{config.model}"
                        )
                        
                        start_time = datetime.now()
                        execution_result = executor.execute_interactive(
                            initial_prompt=f"Execute {{task_type}}: {{task_instance.get('description', '')}}",
                            task_instance=task_instance,
                            workflow=workflow,
                            prompt_type=prompt_type
                        )
                        execution_time = (datetime.now() - start_time).total_seconds()
                        
                        # 构建结果
                        result = {{
                            "model": "{config.model}",
                            "task_type": task_type,
                            "prompt_type": prompt_type,
                            "difficulty_level": difficulty,
                            "task_complexity": task_instance.get('complexity', 'unknown'),
                            "success": execution_result.get('success', False) if isinstance(execution_result, dict) else False,
                            "success_level": execution_result.get('success_level', 'failed') if isinstance(execution_result, dict) else 'failed',
                            "execution_time": execution_time,
                            "workflow_id": workflow.get('workflow_id', 'unknown'),
                            "timestamp": datetime.now().isoformat()
                        }}
                        
                        results.append(result)
                        
                    except Exception as e:
                        print(f"测试失败: {{e}}")
                        results.append({{
                            "model": "{config.model}",
                            "task_type": task_type,
                            "prompt_type": prompt_type,
                            "difficulty_level": difficulty,
                            "task_complexity": task_instance.get('complexity', 'unknown'),
                            "success": False,
                            "error": str(e),
                            "timestamp": datetime.now().isoformat()
                        }})
        
    except Exception as e:
        print(f"批次执行失败: {{e}}")
    
    # 保存结果
    output_file = Path("{self.temp_dir}") / f"batch_{{'{batch_id}'}}_results.json"
    with open(output_file, 'w') as f:
        json.dump({{
            "batch_id": "{batch_id}",
            "results": results,
            "timestamp": datetime.now().isoformat()
        }}, f, indent=2)
    
    print(f"批次完成: {{len(results)}} 个测试")

if __name__ == "__main__":
    run_tests()
'''
    
    def run_batch(self, config: TestConfig, batch_id: str) -> Optional[List[TestResult]]:
        """在子进程中运行测试批次"""
        # 创建测试脚本
        script_content = self.create_test_script(config, batch_id)
        script_path = self.temp_dir / f"test_script_{batch_id}.py"
        
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        try:
            # 运行子进程
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=600  # 10分钟超时
            )
            
            if result.returncode != 0:
                print(f"批次 {batch_id} 执行失败")
                if result.stderr:
                    print(f"错误: {result.stderr}")
                return None
            
            # 读取结果
            result_file = self.temp_dir / f"batch_{batch_id}_results.json"
            if result_file.exists():
                with open(result_file, 'r') as f:
                    data = json.load(f)
                
                # 转换为 TestResult 对象
                results = []
                for r in data.get('results', []):
                    results.append(TestResult(**r))
                
                # 清理临时文件
                os.unlink(result_file)
                
                return results
            
            return None
            
        except subprocess.TimeoutExpired:
            print(f"批次 {batch_id} 超时")
            return None
        finally:
            # 清理脚本
            if script_path.exists():
                os.unlink(script_path)


# ===================== 主测试协调器 =====================
class BatchTestCoordinator:
    """协调批量测试执行"""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.manager = CumulativeResultsManager()
        self.runner = SubprocessTestRunner(CUMULATIVE_RESULTS_DIR)
        self.session_id = f"{config.model}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def calculate_needed_tests(self) -> Dict[str, int]:
        """计算需要的测试数量"""
        progress = self.manager.get_progress(self.config.model, self.config.repeat_target)
        needed = {}
        
        # 计算每个组合需要的测试
        for task_type in self.config.task_types:
            for prompt_type in self.config.prompt_types:
                key = f"{task_type}_{prompt_type}_{self.config.difficulty}"
                existing = progress["groups"].get(key, {}).get("completed", 0)
                remaining = max(0, self.config.repeat_target - existing)
                if remaining > 0:
                    needed[key] = remaining
        
        # 如果测试缺陷
        if self.config.test_flawed:
            for task_type in self.config.task_types:
                for flaw_type in ['missing_step', 'wrong_order', 'infinite_loop']:
                    key = f"{task_type}_flawed_{flaw_type}"
                    existing = progress["groups"].get(key, {}).get("completed", 0)
                    remaining = max(0, self.config.repeat_target - existing)
                    if remaining > 0:
                        needed[key] = remaining
        
        return needed
    
    def create_batches(self, needed: Dict[str, int]) -> List[TestConfig]:
        """创建测试批次"""
        batches = []
        
        # 按任务类型分组创建批次
        while sum(needed.values()) > 0:
            batch_task_types = []
            batch_size = 0
            
            for key, count in list(needed.items()):
                if count > 0 and batch_size < self.config.instances_per_type:
                    task_type = key.split('_')[0]
                    if task_type not in batch_task_types:
                        batch_task_types.append(task_type)
                        needed[key] -= 1
                        batch_size += 1
            
            if batch_task_types:
                batch_config = TestConfig(
                    model=self.config.model,
                    task_types=batch_task_types,
                    prompt_types=self.config.prompt_types,
                    difficulty=self.config.difficulty,
                    instances_per_type=1,
                    test_flawed=self.config.test_flawed,
                    save_logs=self.config.save_logs,
                    parallel=1
                )
                batches.append(batch_config)
        
        return batches
    
    def run(self):
        """运行批量测试"""
        print(f"\n{'='*60}")
        print(f"批量测试: {self.config.model}")
        print(f"{'='*60}")
        print(f"难度级别: {self.config.difficulty}")
        print(f"任务类型: {', '.join(self.config.task_types)}")
        print(f"提示类型: {', '.join(self.config.prompt_types)}")
        print(f"目标次数/组: {self.config.repeat_target}")
        print(f"并行度: {self.config.parallel}")
        
        # 显示当前进度
        progress = self.manager.get_progress(self.config.model, self.config.repeat_target)
        print(f"\n当前进度:")
        for key, info in sorted(progress["groups"].items()):
            print(f"  {key}: {info['completed']}/{info['target']} ({info['percentage']:.1f}%)")
        
        # 计算需要的测试
        needed = self.calculate_needed_tests()
        total_needed = sum(needed.values())
        
        if total_needed == 0:
            print(f"\n✅ 所有测试组已达到目标!")
            return
        
        print(f"\n需要补充: {total_needed} 个测试")
        
        # 确认
        if not self.config.continue_test:
            confirm = input("\n开始测试? (y/n) [y]: ").strip().lower() or "y"
            if confirm != "y":
                print("测试已取消")
                return
        
        # 创建批次
        batches = self.create_batches(needed)
        print(f"\n创建了 {len(batches)} 个测试批次")
        
        # 并行执行批次
        start_time = time.time()
        completed = 0
        failed = 0
        
        with ThreadPoolExecutor(max_workers=self.config.parallel) as executor:
            # 提交批次
            future_to_batch = {}
            for i, batch_config in enumerate(batches):
                batch_id = f"{self.session_id}_batch_{i:04d}"
                future = executor.submit(self.runner.run_batch, batch_config, batch_id)
                future_to_batch[future] = (batch_id, batch_config)
            
            # 处理结果
            for future in as_completed(future_to_batch):
                batch_id, batch_config = future_to_batch[future]
                try:
                    results = future.result()
                    if results:
                        # 保存结果
                        for result in results:
                            self.manager.add_result(result)
                        completed += len(results)
                        print(f"✓ 批次 {batch_id}: {len(results)} 个测试")
                    else:
                        failed += 1
                        print(f"✗ 批次 {batch_id}: 失败")
                except Exception as e:
                    failed += 1
                    print(f"✗ 批次 {batch_id}: {e}")
        
        # 最终保存
        self.manager.save_database()
        
        # 记录会话
        self.manager.results_db["test_sessions"].append({
            "session_id": self.session_id,
            "model": self.config.model,
            "timestamp": datetime.now().isoformat(),
            "num_tests": completed,
            "difficulty": self.config.difficulty
        })
        self.manager.save_database()
        
        # 总结
        elapsed = time.time() - start_time
        print(f"\n{'='*60}")
        print(f"测试完成")
        print(f"{'='*60}")
        print(f"耗时: {elapsed/60:.1f} 分钟")
        print(f"成功: {completed} 个测试")
        print(f"失败: {failed} 个批次")
        print(f"平均: {elapsed/max(completed, 1):.1f} 秒/测试")
        
        # 显示最新进度
        progress = self.manager.get_progress(self.config.model, self.config.repeat_target)
        print(f"\n最新进度:")
        for key, info in sorted(progress["groups"].items()):
            print(f"  {key}: {info['completed']}/{info['target']} ({info['percentage']:.1f}%)")


# ===================== 进度查看器 =====================
def view_progress(model: Optional[str] = None, target: int = 100):
    """查看测试进度"""
    manager = CumulativeResultsManager()
    
    print(f"\n{'='*80}")
    print("累积测试进度报告")
    print(f"{'='*80}")
    
    db = manager.results_db
    print(f"数据库创建: {db.get('created_at', 'N/A')}")
    print(f"总测试数: {db.get('total_tests', 0)}")
    print(f"模型数: {len(db.get('models', {}))}")
    
    # 显示每个模型
    models = db.get('models', {})
    for model_name, model_data in models.items():
        if model and model not in model_name:
            continue
        
        print(f"\n{'='*80}")
        print(f"模型: {model_name}")
        print(f"{'='*80}")
        
        results = model_data.get('results', {})
        
        # 统计
        total_tests = 0
        total_success = 0
        
        print(f"\n进度 (目标: {target}/组):")
        print(f"{'组合':<50} {'完成':<10} {'进度':<15} {'成功率'}")
        print("-" * 80)
        
        for key in sorted(results.keys()):
            tests = results[key]
            count = len(tests)
            success = sum(1 for t in tests if t.get('success', False))
            percent = (count / target * 100) if target > 0 else 0
            success_rate = (success / count * 100) if count > 0 else 0
            
            total_tests += count
            total_success += success
            
            status = "✅" if count >= target else "🔄"
            print(f"{key:<50} {count:>3}/{target:<3} {percent:>6.1f}% {status}  {success_rate:>5.1f}%")
        
        print("-" * 80)
        overall_success = (total_success / total_tests * 100) if total_tests > 0 else 0
        print(f"{'总计':<50} {total_tests:<10} {'':15} {overall_success:>5.1f}%")


# ===================== 主函数 =====================
def main():
    parser = argparse.ArgumentParser(description='完整集成的批量测试脚本')
    
    # 基础参数
    parser.add_argument('--model', type=str, default='qwen2.5-3b-instruct',
                       help='模型名称')
    parser.add_argument('--task-types', nargs='+',
                       default=['simple_task', 'data_pipeline', 'api_integration'],
                       help='要测试的任务类型')
    parser.add_argument('--prompt-types', nargs='+',
                       default=['baseline', 'optimal', 'cot'],
                       help='要测试的提示类型')
    parser.add_argument('--difficulty', type=str, default='easy',
                       choices=['very_easy', 'easy', 'medium', 'hard', 'very_hard'],
                       help='任务描述难度级别')
    
    # 测试控制
    parser.add_argument('--repeat', type=int, default=100,
                       help='每组目标测试数')
    parser.add_argument('--instances', type=int, default=10,
                       help='每批运行的实例数')
    parser.add_argument('--parallel', type=int, default=4,
                       help='并行测试数')
    parser.add_argument('--continue', dest='continue_test', action='store_true',
                       help='继续之前的测试')
    
    # 选项
    parser.add_argument('--test-flawed', action='store_true',
                       help='包含缺陷测试')
    parser.add_argument('--no-save-logs', action='store_true',
                       help='不保存详细日志')
    
    # 查看进度
    parser.add_argument('--view-progress', action='store_true',
                       help='仅查看进度')
    parser.add_argument('--target', type=int, default=100,
                       help='查看进度时的目标值')
    
    args = parser.parse_args()
    
    # 如果是查看进度
    if args.view_progress:
        view_progress(args.model, args.target)
        return
    
    # 创建测试配置
    config = TestConfig(
        model=args.model,
        task_types=args.task_types,
        prompt_types=args.prompt_types,
        difficulty=args.difficulty,
        instances_per_type=args.instances,
        test_flawed=args.test_flawed,
        save_logs=not args.no_save_logs,
        parallel=args.parallel,
        repeat_target=args.repeat,
        continue_test=args.continue_test
    )
    
    # 运行测试
    coordinator = BatchTestCoordinator(config)
    coordinator.run()


if __name__ == "__main__":
    main()