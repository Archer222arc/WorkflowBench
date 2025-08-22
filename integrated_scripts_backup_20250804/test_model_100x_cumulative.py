#!/usr/bin/env python3
"""
单模型100次重复测试 - 支持累积结果存储
- 自动保存到累积结果文件夹
- 支持断点续传
- 支持no-save-log功能减少日志文件
- 使用子进程隔离避免挂起问题
"""

import os
import sys
import json
import time
import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import hashlib
import threading

sys.path.insert(0, str(Path(__file__).parent))


# 累积结果目录
CUMULATIVE_RESULTS_DIR = Path("cumulative_test_results")
CHECKPOINT_DIR = CUMULATIVE_RESULTS_DIR / "checkpoints"
RESULTS_DB = CUMULATIVE_RESULTS_DIR / "results_database.json"


class CumulativeResultsManager:
    """管理累积测试结果"""
    
    def __init__(self):
        # 创建必要的目录
        CUMULATIVE_RESULTS_DIR.mkdir(exist_ok=True)
        CHECKPOINT_DIR.mkdir(exist_ok=True)
        
        # 加载现有结果数据库
        self.results_db = self._load_results_db()
        
        # 添加线程锁以防止并发写入
        import threading
        self._write_lock = threading.Lock()
    
    def _load_results_db(self) -> Dict:
        """加载结果数据库"""
        if RESULTS_DB.exists():
            try:
                with open(RESULTS_DB, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                print(f"警告: 结果数据库损坏 ({e}), 创建备份并重置...")
                # 备份损坏的文件
                import shutil
                backup_path = RESULTS_DB.with_suffix('.json.corrupted')
                shutil.copy(RESULTS_DB, backup_path)
                print(f"损坏的文件已备份到: {backup_path}")
        
        # 创建新的数据库
        return {
            "created_at": datetime.now().isoformat(),
            "total_tests": 0,
            "total_api_calls": 0,
            "models": {},
            "test_sessions": []
        }
    
    def _save_results_db(self):
        """保存结果数据库 - 使用原子写入和线程锁避免并发损坏"""
        import tempfile
        import shutil
        import os
        
        # 使用线程锁防止并发写入
        with self._write_lock:
            # 先写入临时文件
            temp_fd, temp_path = tempfile.mkstemp(dir=str(CUMULATIVE_RESULTS_DIR))
            try:
                with os.fdopen(temp_fd, 'w') as f:
                    json.dump(self.results_db, f, indent=2)
                
                # 原子替换
                shutil.move(temp_path, str(RESULTS_DB))
            except Exception as e:
                # 清理临时文件
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise e
    
    def get_existing_results(self, model: str, task_type: str, 
                           prompt_type: str) -> List[Dict]:
        """获取已存在的测试结果"""
        if model not in self.results_db["models"]:
            return []
        
        model_data = self.results_db["models"][model]
        key = f"{task_type}_{prompt_type}"
        
        return model_data.get("results", {}).get(key, [])
    
    def add_results(self, model: str, results: List[Dict], session_id: str):
        """添加新的测试结果 - 使用锁保护整个操作"""
        with self._write_lock:
            # 重新加载最新数据以防止覆盖其他线程的更改
            self.results_db = self._load_results_db()
            
            if model not in self.results_db["models"]:
                self.results_db["models"][model] = {
                    "first_tested": datetime.now().isoformat(),
                    "total_tests": 0,
                    "results": {}
                }
            
            model_data = self.results_db["models"][model]
            
            # 按任务和提示类型组织结果
            for result in results:
                task_type = result.get("task_type", "unknown")
                prompt_type = result.get("prompt_type", "unknown")
                key = f"{task_type}_{prompt_type}"
                
                if key not in model_data["results"]:
                    model_data["results"][key] = []
                
                # 添加会话信息
                result["session_id"] = session_id
                result["timestamp"] = datetime.now().isoformat()
                
                model_data["results"][key].append(result)
            
            # 更新统计
            model_data["total_tests"] += len(results)
            model_data["last_tested"] = datetime.now().isoformat()
            self.results_db["total_tests"] += len(results)
            self.results_db["total_api_calls"] += len(results)
            
            # 记录会话
            self.results_db["test_sessions"].append({
                "session_id": session_id,
                "model": model,
                "timestamp": datetime.now().isoformat(),
                "num_tests": len(results)
            })
            
            self._save_results_db()
    
    def get_test_progress(self, model: str, target_per_group: int = 100) -> Dict:
        """获取测试进度"""
        if model not in self.results_db["models"]:
            return {"total": 0, "groups": {}}
        
        model_data = self.results_db["models"][model]
        progress = {
            "total": model_data["total_tests"],
            "groups": {}
        }
        
        for key, results in model_data.get("results", {}).items():
            progress["groups"][key] = {
                "completed": len(results),
                "target": target_per_group,
                "remaining": max(0, target_per_group - len(results))
            }
        
        return progress
    
    def generate_progress_report(self, model: str, target_per_group: int = 100) -> str:
        """生成进度报告"""
        progress = self.get_test_progress(model, target_per_group)
        
        report = f"\n{'='*60}\n"
        report += f"模型 {model} 的测试进度\n"
        report += f"{'='*60}\n"
        report += f"总测试数: {progress['total']}\n\n"
        
        if progress['groups']:
            report += "各组进度:\n"
            for group, stats in sorted(progress['groups'].items()):
                completed = stats['completed']
                target = stats['target']
                percent = (completed / target * 100) if target > 0 else 0
                report += f"  {group:<30} {completed:>3}/{target:<3} ({percent:>5.1f}%)\n"
        else:
            report += "暂无测试数据\n"
        
        return report


class SubprocessTestRunner:
    """使用子进程运行测试以避免挂起"""
    
    def __init__(self, results_dir: Path):
        self.results_dir = results_dir
        self.temp_dir = results_dir / "temp"
        self.temp_dir.mkdir(exist_ok=True)
    
    def create_test_script(self, model: str, config: Dict) -> str:
        """创建在子进程中运行的测试脚本"""
        task_types = config.get('task_types', [])
        prompt_types = config.get('prompt_types', [])
        instances_per_type = config.get('instances_per_type', 1)
        test_flawed = config.get('test_flawed', False)
        difficulty = config.get('difficulty', 'easy')
        
        script_content = f'''#!/usr/bin/env python3
import os
import sys
import json
import time
import random
from pathlib import Path
from datetime import datetime
from dataclasses import asdict

# 添加项目路径
sys.path.insert(0, "{Path(__file__).parent}")

def run_tests():
    """运行实际测试"""
    print("初始化测试环境...")
    
    try:
        # 导入必要的模块
        from workflow_quality_test_flawed import WorkflowQualityTester, ExecutionResult
        from mdp_workflow_generator import MDPWorkflowGenerator
        from flawed_workflow_generator import FlawedWorkflowGenerator
        from api_client_manager import MultiModelAPIManager
        
        # 测试配置
        model = "{model}"
        task_types = {task_types}
        prompt_types = {prompt_types}
        instances_per_type = {instances_per_type}
        test_flawed = {test_flawed}
        
        # 初始化组件
        print("加载工具和任务库...")
        
        # 尝试初始化真实的工作流生成器
        try:
            # 设置环境变量禁用 faiss
            import os as os_module
            os_module.environ['FAISS_NO_AVX2'] = '1'
            os_module.environ['OMP_NUM_THREADS'] = '1'
            
            from mdp_workflow_generator import MDPWorkflowGenerator
            generator = MDPWorkflowGenerator(
                model_path="checkpoints/best_model.pt",
                tools_path="mcp_generated_library/tool_registry_consolidated.json",
                use_embeddings=False
            )
            print("使用 MDPWorkflowGenerator（禁用嵌入）")
        except Exception as e:
            print(f"MDPWorkflowGenerator 初始化失败: {{e}}")
            # 如果失败，使用轻量级版本
            from lightweight_workflow_generator import LightweightWorkflowGenerator
            generator = LightweightWorkflowGenerator(
                tools_path="mcp_generated_library/tool_registry_consolidated.json"
            )
            print("回退到轻量级工作流生成器")
        
        # 加载任务库 - 根据难度级别选择文件
        difficulty = "{difficulty}"
        task_lib_path = f"mcp_generated_library/difficulty_versions/task_library_enhanced_v3_{{difficulty}}.json"
        
        if not Path(task_lib_path).exists():
            # 如果不存在指定难度的文件，尝试其他路径
            print(f"警告: 未找到 {{difficulty}} 难度的任务库，尝试其他路径...")
            alternative_paths = [
                "mcp_generated_library/difficulty_versions/task_library_enhanced_v3_easy.json",
                "mcp_generated_library/task_library_all_difficulties.json",
                "mcp_generated_library/task_library_enhanced_v3.json",
                "mcp_generated_library/task_library.json"
            ]
            for alt_path in alternative_paths:
                if Path(alt_path).exists():
                    task_lib_path = alt_path
                    break
        
        print(f"加载任务库: {{task_lib_path}}")
        with open(task_lib_path, 'r') as f:
            task_data = json.load(f)
        
        # 处理任务数据格式
        tasks = task_data.get('tasks', task_data) if isinstance(task_data, dict) else task_data
        
        # 按任务类型索引
        task_library = {{}}
        for task in tasks:
            task_type = task.get('task_type', 'unknown')
            if task_type not in task_library:
                task_library[task_type] = {{}}
                task_library[task_type]['instances'] = []
            task_library[task_type]['instances'].append(task)
        
        # 加载工具注册表 - 使用统一的 consolidated 版本
        with open("mcp_generated_library/tool_registry_consolidated.json", 'r') as f:
            tool_registry = json.load(f)
        
        # 初始化缺陷生成器
        if test_flawed:
            flawed_generator = FlawedWorkflowGenerator(tool_registry)
        
        # 初始化API管理器
        api_manager = MultiModelAPIManager()
        
        # 初始化测试器（暂时不使用，直接在循环中处理）
        # tester = WorkflowQualityTester(generator)
        
        # 运行测试
        results = []
        
        for task_type in task_types:
            print(f"\\n测试任务类型: {{task_type}}")
            
            # 获取任务实例
            if task_type in task_library:
                instances = task_library[task_type].get("instances", [])
                task_instances = instances[:instances_per_type] if instances else [
                    {{"description": f"Test instance {{i+1}} for {{task_type}}", "parameters": {{}}}}
                    for i in range(instances_per_type)
                ]
            else:
                task_instances = [
                    {{"description": f"Test instance {{i+1}} for {{task_type}}", "parameters": {{}}}}
                    for i in range(instances_per_type)
                ]
            
            for instance_idx, instance in enumerate(task_instances):
                for prompt_type in prompt_types:
                    try:
                        # 生成工作流
                        workflow = generator.generate_workflow(
                            task_type=task_type,
                            task_instance=instance.get("description", "")
                        )
                        
                        if workflow:
                            # 运行真实的测试
                            try:
                                # 创建执行器
                                from interactive_executor import InteractiveExecutor
                                
                                # InteractiveExecutor 需要 tool_registry 和 llm_client
                                executor = InteractiveExecutor(
                                    tool_registry=tool_registry,
                                    model=model
                                )
                                
                                # 执行工作流
                                # 构建初始提示
                                initial_prompt = f"Execute {{task_type}}: {{instance.get('description', '')}}"
                                
                                # 执行交互式工作流
                                execution_result = executor.execute_interactive(
                                    initial_prompt=initial_prompt,
                                    task_instance=instance,
                                    workflow=workflow,
                                    prompt_type=prompt_type
                                )
                                
                                # 处理执行结果
                                if isinstance(execution_result, dict):
                                    # 提取结果信息
                                    result = {{
                                        "model": model,
                                        "task_type": task_type,
                                        "prompt_type": prompt_type,
                                        "success": execution_result.get("success", False),
                                        "success_level": execution_result.get("success_level", "failed"),
                                        "final_score": execution_result.get("score", 0.0),
                                        "execution_time": execution_result.get("execution_time", 0.0),
                                        "tool_calls": len(execution_result.get("tool_calls", [])),
                                        "workflow_id": workflow.get("workflow_id", "unknown"),
                                        "error": execution_result.get("error")
                                    }}
                                else:
                                    # 处理其他类型的结果
                                    result = {{
                                        "model": model,
                                        "task_type": task_type,
                                        "prompt_type": prompt_type,
                                        "success": False,
                                        "success_level": "failed",
                                        "final_score": 0.0,
                                        "execution_time": 0.0,
                                        "tool_calls": 0,
                                        "workflow_id": workflow.get("workflow_id", "unknown"),
                                        "error": "Unexpected result type"
                                    }}
                            except Exception as e:
                                print(f"  执行测试时出错: {{e}}")
                                # 如果执行失败，创建错误结果
                                result = {{
                                    "model": model,
                                    "task_type": task_type,
                                    "prompt_type": prompt_type,
                                    "success": False,
                                    "success_level": "failed",
                                    "final_score": 0.0,
                                    "execution_time": 0.0,
                                    "tool_calls": 0,
                                    "workflow_id": workflow.get("workflow_id", "unknown"),
                                    "error": str(e)
                                }}
                            
                            # 转换结果
                            if hasattr(result, '__dataclass_fields__'):
                                result_dict = asdict(result)
                            else:
                                result_dict = result
                            
                            results.append(result_dict)
                            print(f"  完成: {{task_type}}_{{prompt_type}} ({{instance_idx+1}}/{{len(task_instances)}})")
                        
                    except Exception as e:
                        print(f"  测试失败: {{e}}")
                        error_result = {{
                            "model": model,
                            "task_type": task_type,
                            "prompt_type": prompt_type,
                            "success": False,
                            "error": str(e)
                        }}
                        results.append(error_result)
        
        # 缺陷测试
        if test_flawed:
            flaw_types = ["sequence_disorder", "tool_misuse", "parameter_error", 
                         "missing_step", "redundant_operations", 
                         "logical_inconsistency", "semantic_drift"]
            
            for task_type in task_types:
                print(f"\\n缺陷测试任务类型: {{task_type}}")
                
                # 获取任务实例
                if task_type in task_library:
                    instances = task_library[task_type].get("instances", [])
                    task_instances = instances[:instances_per_type] if instances else [
                        {{"description": f"Test instance {{i+1}} for {{task_type}}", "parameters": {{}}}}
                        for i in range(instances_per_type)
                    ]
                else:
                    task_instances = [
                        {{"description": f"Test instance {{i+1}} for {{task_type}}", "parameters": {{}}}}
                        for i in range(instances_per_type)
                    ]
                
                for instance_idx, instance in enumerate(task_instances):
                    for flaw_type in flaw_types:
                        try:
                            # 生成工作流
                            workflow = generator.generate_workflow(
                                task_type=task_type,
                                task_instance=instance.get("description", "")
                            )
                            
                            if workflow:
                                # 注入缺陷
                                # FlawedWorkflowGenerator 使用 inject_specific_flaw 方法
                                flawed_workflow = flawed_generator.inject_specific_flaw(
                                    workflow, 
                                    flaw_type, 
                                    "medium"
                                )
                                
                                # 运行真实的缺陷测试
                                try:
                                    # 创建执行器
                                    from interactive_executor import InteractiveExecutor
                                    
                                    # InteractiveExecutor 需要 tool_registry 和 llm_client
                                    executor = InteractiveExecutor(
                                        tool_registry=tool_registry,
                                        model=model
                                    )
                                    
                                    # 执行缺陷工作流
                                    # 构建初始提示
                                    initial_prompt = f"Execute {{task_type}}: {{instance.get('description', '')}}"
                                    
                                    # 执行交互式工作流
                                    execution_result = executor.execute_interactive(
                                        initial_prompt=initial_prompt,
                                        task_instance=instance,
                                        workflow=flawed_workflow,
                                        prompt_type="flawed_" + flaw_type
                                    )
                                    
                                    # 处理缺陷测试结果
                                    if isinstance(execution_result, dict):
                                        # 提取结果信息
                                        result = {{
                                            "model": model,
                                            "task_type": task_type,
                                            "prompt_type": "flawed_" + flaw_type,
                                            "flaw_type": flaw_type,
                                            "success": execution_result.get("success", False),
                                            "success_level": execution_result.get("success_level", "failed"),
                                            "final_score": execution_result.get("score", 0.0),
                                            "execution_time": execution_result.get("execution_time", 0.0),
                                            "tool_calls": len(execution_result.get("tool_calls", [])),
                                            "workflow_id": flawed_workflow.get("workflow_id", "unknown"),
                                            "error": execution_result.get("error")
                                        }}
                                    else:
                                        # 处理其他类型的结果
                                        result = {{
                                            "model": model,
                                            "task_type": task_type,
                                            "prompt_type": "flawed_" + flaw_type,
                                            "flaw_type": flaw_type,
                                            "success": False,
                                            "success_level": "failed",
                                            "final_score": 0.0,
                                            "execution_time": 0.0,
                                            "tool_calls": 0,
                                            "workflow_id": flawed_workflow.get("workflow_id", "unknown"),
                                            "error": "Unexpected result type"
                                        }}
                                except Exception as e:
                                    print(f"  缺陷测试执行出错: {{e}}")
                                    # 如果执行失败，创建错误结果
                                    result = {{
                                        "model": model,
                                        "task_type": task_type,
                                        "prompt_type": "flawed_" + flaw_type,
                                        "flaw_type": flaw_type,
                                        "success": False,
                                        "success_level": "failed",
                                        "final_score": 0.0,
                                        "execution_time": 0.0,
                                        "tool_calls": 0,
                                        "workflow_id": flawed_workflow.get("workflow_id", "unknown"),
                                        "error": str(e)
                                    }}
                                
                                # 转换结果
                                if hasattr(result, '__dataclass_fields__'):
                                    result_dict = asdict(result)
                                else:
                                    result_dict = result
                                
                                result_dict["flaw_type"] = flaw_type
                                results.append(result_dict)
                                print(f"  完成: {{task_type}}_flawed_{{flaw_type}} ({{instance_idx+1}}/{{len(task_instances)}})")
                        
                        except Exception as e:
                            print(f"  缺陷测试失败: {{e}}")
                            error_result = {{
                                "model": model,
                                "task_type": task_type,
                                "prompt_type": "flawed_" + flaw_type,
                                "flaw_type": flaw_type,
                                "success": False,
                                "error": str(e)
                            }}
                            results.append(error_result)
        
        # 保存结果
        output_file = Path("{self.temp_dir}") / f"batch_{{datetime.now().strftime('%Y%m%d_%H%M%S')}}.json"
        with open(output_file, 'w') as f:
            json.dump({{
                "model": model,
                "results": results,
                "summary": {{
                    "total_tests": len(results),
                    "successful_tests": sum(1 for r in results if r.get("success", False)),
                    "failed_tests": sum(1 for r in results if not r.get("success", False))
                }}
            }}, f, indent=2)
        
        print(f"\\n结果已保存到: {{output_file}}")
        print(f"总计完成 {{len(results)}} 个测试")
        
    except Exception as e:
        print(f"\\n测试错误: {{e}}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    sys.exit(0)

if __name__ == "__main__":
    run_tests()
'''
        return script_content
        
    def run_batch_test(self, model: str, config: Dict, session_id: str) -> Optional[str]:
        """在子进程中运行测试批次"""
        # 创建测试脚本
        script_content = self.create_test_script(model, config)
        script_path = self.temp_dir / f"test_script_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
        
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        try:
            # 运行子进程
            print(f"\n启动测试批次...")
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=600  # 10分钟超时
            )
            
            if result.returncode == 0:
                print("✅ 批次成功完成")
                if result.stdout:
                    print(result.stdout.strip())
                
                # 查找结果文件
                for file in self.temp_dir.glob("batch_*.json"):
                    if file.stat().st_mtime > time.time() - 300:  # 5分钟内的文件
                        return str(file)
                
                return None
            else:
                print("❌ 批次失败")
                if result.stderr:
                    print("错误信息:")
                    print(result.stderr)
                return None
                
        except subprocess.TimeoutExpired:
            print("❌ 批次超时")
            return None
        finally:
            # 清理脚本
            if script_path.exists():
                os.unlink(script_path)
        
class BatchTestConfig:
    """批次测试配置"""
    def __init__(self, models: List[str], task_types: List[str], 
                 prompt_types: List[str], instances_per_type: int,
                 test_flawed: bool = False, max_parallel_models: int = 4,
                 difficulty: str = 'easy'):
        self.models = models
        self.task_types = task_types
        self.prompt_types = prompt_types
        self.instances_per_type = instances_per_type
        self.test_flawed = test_flawed
        self.max_parallel_models = max_parallel_models
        self.difficulty = difficulty


def select_model() -> str:
    """选择要测试的模型"""
    models = [
        ("DeepSeek-V3-671B", "最强开源模型，671B参数"),
        ("DeepSeek-R1-671B", "推理增强版，671B参数"),
        ("qwen2.5-32b-instruct", "Qwen中型模型，32B参数"),
        ("qwen2.5-14b-instruct", "Qwen小型模型，14B参数"),
        ("qwen2.5-7b-instruct", "Qwen轻量模型，7B参数"),
        ("qwen2.5-3b-instruct", "Qwen超轻量模型，3B参数"),
    ]
    
    print("\n可用的开源模型:")
    for i, (model, desc) in enumerate(models, 1):
        print(f"{i}. {model:<25} - {desc}")
    
    choice = input("\n选择模型 (1-6) [1]: ").strip() or "1"
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(models):
            return models[idx][0]
    except:
        pass
    
    print("使用默认模型")
    return models[0][0]


def calculate_needed_tests(model: str, target_per_group: int, 
                          task_types: List[str], prompt_types: List[str],
                          include_flawed: bool = True) -> Dict:
    """计算需要的测试数量"""
    manager = CumulativeResultsManager()
    progress = manager.get_test_progress(model, target_per_group)
    
    needed = {
        "normal": {},
        "flawed": {},
        "total": 0
    }
    
    # 计算正常测试需求
    for task_type in task_types:
        for prompt_type in prompt_types:
            key = f"{task_type}_{prompt_type}"
            existing = progress['groups'].get(key, {}).get('completed', 0)
            remaining = max(0, target_per_group - existing)
            if remaining > 0:
                needed["normal"][key] = remaining
                needed["total"] += remaining
    
    # 计算缺陷测试需求（如果需要）
    if include_flawed:
        flaw_types = ["sequence_disorder", "tool_misuse", "parameter_error", 
                     "missing_step", "redundant_operations", 
                     "logical_inconsistency", "semantic_drift"]
        
        for task_type in task_types:
            for flaw_type in flaw_types:
                key = f"{task_type}_flawed_{flaw_type}"
                existing = progress['groups'].get(key, {}).get('completed', 0)
                remaining = max(0, target_per_group - existing)
                if remaining > 0:
                    needed["flawed"][key] = remaining
                    needed["total"] += remaining
    
    return needed


def run_tests_in_subprocess(model: str, config: Dict, manager: CumulativeResultsManager, 
                           session_id: str, save_logs: bool = False):
    """在子进程中运行测试"""
    runner = SubprocessTestRunner(CUMULATIVE_RESULTS_DIR)
    
    # 运行测试
    result_file = runner.run_batch_test(model, config, session_id)
    
    if result_file:
        try:
            # 加载结果
            with open(result_file, 'r') as f:
                data = json.load(f)
            
            results = data.get('results', [])
            
            # 处理结果
            simplified_results = []
            for result in results:
                # 提取简化结果
                simplified = {
                    "model": result.get("model", model),
                    "task_type": result.get("task_type"),
                    "prompt_type": result.get("prompt_type"),
                    "success": result.get("success", False),
                    "success_level": result.get("success_level", "failed"),
                    "final_score": result.get("final_score", 0.0),
                    "execution_time": result.get("execution_time", 0.0),
                    "tool_calls": result.get("tool_calls", 0),
                    "flaw_type": result.get("flaw_type")
                }
                simplified_results.append(simplified)
            
            # 保存到累积数据库
            manager.add_results(model, simplified_results, session_id)
            
            # 清理结果文件
            os.unlink(result_file)
            
            return len(simplified_results)
        except Exception as e:
            print(f"处理结果时出错: {e}")
            return 0
    
    return 0


def main():
    parser = argparse.ArgumentParser(description='单模型100次重复测试（支持累积）')
    parser.add_argument('--model', type=str, help='指定模型名称')
    parser.add_argument('--repeat', type=int, default=100, 
                       help='每组重复次数 (默认: 100)')
    parser.add_argument('--no-save-logs', action='store_true',
                       help='不保存详细日志文件')
    parser.add_argument('--task-types', nargs='+',
                       default=['simple_task', 'data_pipeline', 'api_integration'],
                       help='要测试的任务类型')
    parser.add_argument('--prompt-types', nargs='+',
                       default=['baseline', 'optimal', 'cot'],
                       help='要测试的提示类型')
    parser.add_argument('--difficulty', type=str, default='easy',
                       choices=['very_easy', 'easy', 'medium', 'hard', 'very_hard'],
                       help='任务难度级别 (默认: easy)')
    parser.add_argument('--no-flawed', action='store_true',
                       help='不进行缺陷测试')
    parser.add_argument('--continue', dest='continue_test', action='store_true',
                       help='继续之前的测试')
    parser.add_argument('--instances', type=int, default=None,
                       help='每个任务类型的实例数（覆盖自动计算）')
    parser.add_argument('--parallel', type=int, default=4,
                       help='并行测试的数量（默认: 4）')
    
    args = parser.parse_args()
    
    print("="*60)
    print("单模型累积测试系统")
    print("="*60)
    
    # 显示累积结果状态
    manager = CumulativeResultsManager()
    print(f"\n累积结果目录: {CUMULATIVE_RESULTS_DIR}")
    print(f"已累积测试数: {manager.results_db['total_tests']}")
    print(f"已测试模型数: {len(manager.results_db['models'])}")
    
    # 选择模型
    if args.model:
        model = args.model
        print(f"\n使用指定模型: {model}")
    else:
        model = select_model()
    
    # 显示当前进度
    print(manager.generate_progress_report(model, args.repeat))
    
    # 计算需要的测试
    needed = calculate_needed_tests(
        model, args.repeat, 
        args.task_types, 
        args.prompt_types,
        not args.no_flawed
    )
    
    if needed["total"] == 0:
        print(f"\n✅ {model} 的所有测试组已达到 {args.repeat} 次!")
        print("无需额外测试。")
        return
    
    print(f"\n需要补充的测试:")
    print(f"- 正常测试: {sum(needed['normal'].values())} 个")
    print(f"- 缺陷测试: {sum(needed['flawed'].values())} 个")
    print(f"- 总计: {needed['total']} 个")
    print(f"- 预计时间: {needed['total'] * 10 / 60:.1f} 分钟")
    
    # 确认
    if not args.continue_test:
        confirm = input(f"\n开始测试? (y/n) [y]: ").strip().lower() or "y"
        if confirm != "y":
            print("测试已取消")
            return
    
    # 创建测试配置
    # 如果用户指定了instances，使用该值；否则自动计算
    if args.instances is not None:
        instances_per_type = args.instances
    else:
        # 注意：这里需要计算每个组合需要的确切数量
        # 为简化，我们运行一批测试，然后筛选需要的
        instances_per_type = min(10, max(needed["normal"].values()) if needed["normal"] else 0)
        if instances_per_type == 0:
            instances_per_type = min(10, max(needed["flawed"].values()) if needed["flawed"] else 0)
    
    config = BatchTestConfig(
        models=[model],
        task_types=args.task_types,
        prompt_types=args.prompt_types,
        instances_per_type=instances_per_type,
        test_flawed=not args.no_flawed and sum(needed["flawed"].values()) > 0,
        max_parallel_models=args.parallel,  # 使用用户指定的并行度
        difficulty=args.difficulty
    )
    
    # 运行测试
    print(f"\n开始测试批次 (每组 {instances_per_type} 个)...")
    print(f"日志保存: {'否' if args.no_save_logs else '是'}")
    print(f"并行度: {args.parallel}")
    
    session_id = f"{model}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    start_time = time.time()
    
    try:
        # 使用子进程运行测试
        test_config = {
            'task_types': args.task_types,
            'prompt_types': args.prompt_types,
            'instances_per_type': instances_per_type,
            'test_flawed': not args.no_flawed and sum(needed["flawed"].values()) > 0,
            'difficulty': args.difficulty
        }
        
        # 在子进程中运行
        num_completed = run_tests_in_subprocess(
            model, test_config, manager, session_id, 
            save_logs=not args.no_save_logs
        )
        
        elapsed = time.time() - start_time
        
        print(f"\n✓ 批次完成! 耗时: {elapsed/60:.1f} 分钟")
        print(f"完成 {num_completed} 个测试")
        
        # 显示更新后的进度
        print("生成进度报告...")
        progress_report = manager.generate_progress_report(model, args.repeat)
        print(progress_report)
        
        # 如果还需要更多测试，提示继续
        remaining = calculate_needed_tests(
            model, args.repeat, 
            args.task_types, 
            args.prompt_types,
            not args.no_flawed
        )
        
        if remaining["total"] > 0:
            print(f"\n还需要 {remaining['total']} 个测试达到目标")
            print("可以使用 --continue 参数继续测试")
        
    except KeyboardInterrupt:
        print("\n测试被中断")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        main()
        print("\n程序正常完成")
    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        print(f"\n程序错误: {e}")
        import traceback
        traceback.print_exc()
    
    # 正常退出，不需要强制
    print("\n程序结束")
    sys.exit(0)