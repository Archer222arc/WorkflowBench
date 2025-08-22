#!/usr/bin/env python3
"""
微量全面测试脚本
用最少的测试样本覆盖所有主要功能点
"""

import subprocess
import sys
import time
from datetime import datetime

def run_command(cmd):
    """运行命令并显示输出"""
    print(f"\n{'='*60}")
    print(f"运行: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        print(f"❌ 命令执行失败")
        return False
    return True

def main():
    model = sys.argv[1] if len(sys.argv) > 1 else "qwen2.5-3b-instruct"
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                     微量全面测试计划                         ║
╠══════════════════════════════════════════════════════════════╣
║ 模型: {model:<53} ║
║ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S'):<50} ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    start_time = time.time()
    tests = []
    
    # 测试1: 覆盖不同复杂度的任务类型（easy描述难度）
    # simple_task(easy复杂度), data_pipeline(medium复杂度), multi_stage_pipeline(hard复杂度)
    print("\n[1/6] 不同任务类型复杂度测试（easy描述）")
    tests.append({
        "name": "任务类型复杂度覆盖",
        "cmd": [
            "python", "run_real_test.py",
            "--model", model,
            "--task-types", "simple_task", "data_pipeline", "multi_stage_pipeline",
            "--prompt-types", "baseline", "optimal", "cot",
            "--instances", "1",
            "--difficulty", "easy",
            "--merge"
        ]
    })
    
    # 测试2: 中等描述难度测试（覆盖easy和medium复杂度任务）
    print("\n[2/6] 中等描述难度测试")
    tests.append({
        "name": "中等描述难度",
        "cmd": [
            "python", "run_real_test.py",
            "--model", model,
            "--task-types", "basic_task", "api_integration",  # easy和medium复杂度
            "--prompt-types", "baseline",
            "--instances", "1",
            "--difficulty", "medium",
            "--merge"
        ]
    })
    
    # 测试3: 困难描述测试（包含hard复杂度任务）
    print("\n[3/6] 困难描述测试")
    tests.append({
        "name": "困难描述+hard任务",
        "cmd": [
            "python", "run_real_test.py",
            "--model", model,
            "--task-types", "multi_stage_pipeline",  # hard复杂度任务
            "--prompt-types", "optimal",
            "--instances", "1",
            "--difficulty", "hard",
            "--merge"
        ]
    })
    
    # 测试4: 极困难描述测试（测试描述理解能力）
    print("\n[4/6] 极困难描述测试")
    tests.append({
        "name": "极困难描述",
        "cmd": [
            "python", "run_real_test.py",
            "--model", model,
            "--task-types", "simple_task",  # 用简单任务测试极难描述
            "--prompt-types", "cot",
            "--instances", "1",
            "--difficulty", "very_hard",
            "--merge"
        ]
    })
    
    # 测试5: 缺陷工作流测试
    print("\n[5/6] 缺陷工作流测试")
    tests.append({
        "name": "缺陷工作流",
        "cmd": [
            "python", "run_real_test.py",
            "--model", model,
            "--task-types", "data_pipeline",  # medium复杂度
            "--prompt-types", "baseline",
            "--instances", "1",
            "--test-flawed",
            "--merge"
        ]
    })
    
    # 执行所有测试
    results = []
    for i, test in enumerate(tests):
        print(f"\n[{i+1}/{len(tests)}] 执行: {test['name']}")
        success = run_command(test["cmd"])
        results.append({
            "name": test["name"],
            "success": success
        })
        
        if not success:
            print(f"⚠️  {test['name']} 失败，继续下一个测试")
    
    # 测试6: 查看进度
    print("\n[6/6] 查看测试进度")
    run_command(["python", "view_test_progress.py", "--model", model])
    
    # 总结
    elapsed = time.time() - start_time
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                        测试完成总结                          ║
╠══════════════════════════════════════════════════════════════╣
║ 总耗时: {f'{elapsed/60:.1f} 分钟':<51} ║
║ 测试结果:                                                    ║""")
    
    for result in results:
        status = "✅ 成功" if result["success"] else "❌ 失败"
        print(f"║   - {result['name']:<30} {status:<20} ║")
    
    print(f"""╚══════════════════════════════════════════════════════════════╝
    
💡 提示:
1. 使用 'python view_test_progress.py --model {model}' 查看详细进度
2. 使用 'python test_model_100x_cumulative.py --model {model} --continue' 继续累积测试
3. 测试结果已保存在 cumulative_test_results/ 目录
    """)

if __name__ == "__main__":
    main()