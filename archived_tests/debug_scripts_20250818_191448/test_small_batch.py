#!/usr/bin/env python3
"""小规模测试batch_test_runner"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from batch_test_runner import BatchTestRunner, TestTask

# 创建runner
runner = BatchTestRunner(debug=True, silent=False)

# 创建单个测试任务
task = TestTask(
    model='gpt-4o-mini',
    task_type='simple_task', 
    prompt_type='baseline',
    difficulty='easy',
    tool_success_rate=0.8,
    timeout=600,
    is_flawed=False,
    flaw_type=None
)

print("开始运行单个测试...")
try:
    # 运行单个测试
    result = runner.run_single_test(
        model=task.model,
        task_type=task.task_type,
        prompt_type=task.prompt_type,
        is_flawed=task.is_flawed,
        flaw_type=task.flaw_type,
        timeout=task.timeout,
        tool_success_rate=task.tool_success_rate,
        difficulty=task.difficulty
    )
    
    print(f"测试完成: success={result.get('success')}")
    print(f"错误: {result.get('error', 'None')}")
    print(f"执行时间: {result.get('execution_time', 0):.1f}秒")
    
except Exception as e:
    print(f"测试失败: {e}")
    import traceback
    traceback.print_exc()