#!/usr/bin/env python3
"""
测试难度参数修复是否有效
"""

from batch_test_runner import BatchTestRunner, TestTask

# 创建runner
runner = BatchTestRunner(debug=True, silent=False)

print("="*70)
print("测试难度参数修复")
print("="*70)

# 测试不同难度的任务加载
difficulties = ["very_easy", "easy", "medium"]

for difficulty in difficulties:
    print(f"\n测试难度: {difficulty}")
    print("-"*50)
    
    # 创建测试任务
    task = TestTask(
        model="test-model",
        task_type="simple_task",
        prompt_type="baseline",
        difficulty=difficulty,
        tool_success_rate=0.8
    )
    
    # 测试任务库加载
    runner._load_task_library(difficulty=difficulty)
    
    # 检查加载的任务
    if runner.tasks_by_type:
        total_tasks = sum(len(tasks) for tasks in runner.tasks_by_type.values())
        print(f"  ✓ 成功加载 {total_tasks} 个任务")
        print(f"  任务类型: {list(runner.tasks_by_type.keys())[:3]}...")
    else:
        print(f"  ✗ 无法加载任务库")
    
    # 检查当前难度
    if hasattr(runner, '_current_difficulty'):
        print(f"  当前难度设置: {runner._current_difficulty}")

print("\n" + "="*70)
print("修复验证完成")
print("-"*70)
print("修复要点:")
print("1. _load_task_library 现在接受 difficulty 参数")
print("2. 根据不同难度加载对应的任务库文件")
print("3. run_single_test 会检查并在需要时重新加载任务库")
print("4. 确保 very_easy、easy、medium 使用不同的任务库")