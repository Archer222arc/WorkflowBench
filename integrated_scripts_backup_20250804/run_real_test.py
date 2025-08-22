#!/usr/bin/env python3
"""
运行真实测试的脚本
完全在子进程中隔离，避免主进程加载问题库
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

def create_test_script(model: str, task_types: list, prompt_types: list, 
                      instances: int, test_flawed: bool = False, difficulty: str = "easy") -> str:
    """创建测试脚本内容"""
    return f'''#!/usr/bin/env python3
import os
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, "{Path(__file__).parent}")

def run_test():
    """运行真实测试"""
    print("初始化测试环境...")
    
    # 导入必要的模块
    from workflow_quality_test_flawed import WorkflowQualityTester
    from api_client_manager import MultiModelAPIManager
    from mdp_workflow_generator import MDPWorkflowGenerator
    
    # 配置
    model = "{model}"
    task_types = {task_types}
    prompt_types = {prompt_types}
    instances_per_type = {instances}
    
    # 初始化 API 管理器
    api_manager = MultiModelAPIManager()
    
    # 初始化工作流生成器
    try:
        generator = MDPWorkflowGenerator(
            model_path="checkpoints/best_model.pt"
            # tools_path 使用默认值: mcp_generated_library/tool_registry_consolidated.json
        )
    except Exception as e:
        print(f"工作流生成器初始化失败: {{e}}")
        return
    
    # 初始化测试器
    tester = WorkflowQualityTester(generator)
    
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
    
    # 运行测试
    results = []
    
    for task_type in task_types:
        print(f"\\n测试任务类型: {{task_type}}")
        
        # 获取任务实例
        if task_type in task_library:
            instances = task_library[task_type].get("instances", [])[:instances_per_type]
        else:
            print(f"  警告: 任务类型 {{task_type}} 不在任务库中")
            instances = [{{"description": f"Test {{task_type}}", "parameters": {{}}}}]
        
        for idx, instance in enumerate(instances):
            for prompt_type in prompt_types:
                try:
                    print(f"  测试 {{task_type}}_{{prompt_type}} ({{idx+1}}/{{len(instances)}})")
                    
                    # 生成工作流
                    # instance 可能是字符串或字典
                    if isinstance(instance, str):
                        task_description = instance
                    else:
                        task_description = instance.get("description", "")
                    
                    workflow = generator.generate_workflow(
                        task_type=task_type,
                        task_instance=instance  # 传递完整的任务实例字典
                    )
                    
                    if not workflow:
                        print(f"    无法生成工作流")
                        continue
                    
                    # 创建执行器
                    from interactive_executor import InteractiveExecutor
                    executor = InteractiveExecutor(
                        tool_registry=generator.tool_registry,
                        model=model
                    )
                    
                    # 执行工作流
                    initial_prompt = f"Execute {{task_type}}: {{task_description}}"
                    execution_result = executor.execute_interactive(
                        initial_prompt=initial_prompt,
                        task_instance=instance,
                        workflow=workflow,
                        prompt_type=prompt_type
                    )
                    
                    # 处理结果
                    if isinstance(execution_result, dict):
                        result = {{
                            "model": model,
                            "task_type": task_type,
                            "prompt_type": prompt_type,
                            "success": execution_result.get("success", False),
                            "success_level": execution_result.get("success_level", "failed"),
                            "final_score": execution_result.get("score", 0.0),
                            "execution_time": execution_result.get("execution_time", 0.0),
                            "tool_calls": len(execution_result.get("tool_calls", [])),
                            "workflow_id": workflow.get("workflow_id", "unknown")
                        }}
                    else:
                        result = {{
                            "model": model,
                            "task_type": task_type,
                            "prompt_type": prompt_type,
                            "success": False,
                            "error": "Unexpected result type"
                        }}
                    
                    # 添加到结果
                    results.append(result)
                    
                except Exception as e:
                    print(f"    测试失败: {{e}}")
                    error_result = {{
                        "model": model,
                        "task_type": task_type,
                        "prompt_type": prompt_type,
                        "success": False,
                        "error": str(e)
                    }}
                    results.append(error_result)
    
    # 保存结果
    output_dir = Path("test_results")
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"results_{{model}}_{{timestamp}}.json"
    
    with open(output_file, 'w') as f:
        json.dump({{
            "model": model,
            "timestamp": timestamp,
            "results": results,
            "summary": {{
                "total": len(results),
                "success": sum(1 for r in results if r.get("success", False))
            }}
        }}, f, indent=2)
    
    print(f"\\n结果已保存到: {{output_file}}")
    print(f"总测试: {{len(results)}}, 成功: {{sum(1 for r in results if r.get('success', False))}}")

if __name__ == "__main__":
    run_test()
'''

def run_real_test(model: str, task_types: list, prompt_types: list, 
                 instances: int, test_flawed: bool = False, difficulty: str = "easy"):
    """运行真实测试"""
    print("="*60)
    print("运行真实工作流测试")
    print("="*60)
    print(f"模型: {model}")
    print(f"任务类型: {', '.join(task_types)}")
    print(f"提示类型: {', '.join(prompt_types)}")
    print(f"每类实例数: {instances}")
    print(f"难度级别: {difficulty}")
    
    # 创建临时测试脚本
    temp_script = Path("temp_test_script.py")
    script_content = create_test_script(model, task_types, prompt_types, instances, test_flawed, difficulty)
    
    with open(temp_script, 'w') as f:
        f.write(script_content)
    
    try:
        # 在子进程中运行
        print("\n在子进程中运行测试...")
        result = subprocess.run(
            [sys.executable, str(temp_script)],
            capture_output=True,
            text=True,
            timeout=600  # 10分钟超时
        )
        
        if result.returncode == 0:
            print("\n✅ 测试成功完成")
            if result.stdout:
                print(result.stdout)
        else:
            print("\n❌ 测试失败")
            if result.stderr:
                print("错误信息:")
                print(result.stderr)
        
        return result.returncode
        
    except subprocess.TimeoutExpired:
        print("\n❌ 测试超时")
        return 1
    finally:
        # 清理临时脚本
        if temp_script.exists():
            os.unlink(temp_script)

def merge_to_cumulative(results_file: Path):
    """将结果合并到累积数据库"""
    cumulative_dir = Path("cumulative_test_results")
    cumulative_dir.mkdir(exist_ok=True)
    
    results_db_path = cumulative_dir / "results_database.json"
    
    # 加载结果
    with open(results_file, 'r') as f:
        test_data = json.load(f)
    
    # 加载累积数据库
    if results_db_path.exists():
        with open(results_db_path, 'r') as f:
            db = json.load(f)
    else:
        db = {
            "created_at": datetime.now().isoformat(),
            "total_tests": 0,
            "models": {},
            "test_sessions": []
        }
    
    # 合并结果
    model = test_data["model"]
    if model not in db["models"]:
        db["models"][model] = {
            "first_tested": datetime.now().isoformat(),
            "total_tests": 0,
            "results": {}
        }
    
    model_data = db["models"][model]
    
    # 添加结果
    for result in test_data["results"]:
        task_type = result.get("task_type", "unknown")
        prompt_type = result.get("prompt_type", "unknown")
        key = f"{task_type}_{prompt_type}"
        
        if key not in model_data["results"]:
            model_data["results"][key] = []
        
        model_data["results"][key].append(result)
    
    # 更新统计
    model_data["total_tests"] += len(test_data["results"])
    model_data["last_tested"] = datetime.now().isoformat()
    db["total_tests"] += len(test_data["results"])
    
    # 记录会话
    db["test_sessions"].append({
        "session_id": test_data["timestamp"],
        "model": model,
        "timestamp": datetime.now().isoformat(),
        "num_tests": len(test_data["results"])
    })
    
    # 保存
    with open(results_db_path, 'w') as f:
        json.dump(db, f, indent=2)
    
    print(f"\n结果已合并到累积数据库")

def main():
    parser = argparse.ArgumentParser(description='运行真实工作流测试')
    parser.add_argument('--model', type=str, default="qwen2.5-3b-instruct",
                       help='模型名称')
    parser.add_argument('--task-types', nargs='+',
                       default=['simple_task', 'data_pipeline', 'api_integration'],
                       help='要测试的任务类型')
    parser.add_argument('--prompt-types', nargs='+',
                       default=['baseline', 'optimal', 'cot'],
                       help='要测试的提示类型')
    parser.add_argument('--instances', type=int, default=2,
                       help='每个任务类型的实例数')
    parser.add_argument('--difficulty', type=str, default='easy',
                       choices=['very_easy', 'easy', 'medium', 'hard', 'very_hard'],
                       help='任务难度级别')
    parser.add_argument('--test-flawed', action='store_true',
                       help='包含缺陷测试')
    parser.add_argument('--merge', action='store_true',
                       help='将结果合并到累积数据库')
    
    args = parser.parse_args()
    
    # 运行测试
    exit_code = run_real_test(
        args.model,
        args.task_types,
        args.prompt_types,
        args.instances,
        args.test_flawed,
        args.difficulty
    )
    
    # 如果成功且需要合并
    if exit_code == 0 and args.merge:
        # 查找最新的结果文件
        results_dir = Path("test_results")
        if results_dir.exists():
            results_files = sorted(results_dir.glob(f"results_{args.model}_*.json"))
            if results_files:
                latest_file = results_files[-1]
                print(f"\n合并结果文件: {latest_file}")
                merge_to_cumulative(latest_file)
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())