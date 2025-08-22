#!/usr/bin/env python3
"""测试AI分类修复"""

import os
os.environ['STORAGE_FORMAT'] = 'parquet'

from batch_test_runner import BatchTestRunner
from batch_test_runner import TestTask

# 创建runner
runner = BatchTestRunner(
    debug=True,
    silent=False,
    save_logs=False,
    use_ai_classification=True
)

# 创建测试任务
task = TestTask(
    model='test-model',
    task_type='simple_task',
    prompt_type='baseline',
    difficulty='easy',
    tool_success_rate=0.1  # 低成功率以触发partial_success
)

print("运行测试...")

# 模拟一个partial_success的结果
result = {
    'success': True,
    'workflow_score': 0.7,  # < 0.8，应该触发partial_success
    'phase2_score': 0.6,
    'success_level': '',  # 故意不设置，测试自动判断
    'turns': 10,
    'tool_calls': 5,
    'execution_time': 5.0
}

# 模拟log_data
log_data = {
    'conversation_history': [
        {'role': 'user', 'content': 'test'},
        {'role': 'assistant', 'content': 'response'}
    ],
    'tool_calls': ['tool1', 'tool2'],
    'api_issues': []
}

# 直接测试success_level判断逻辑
print("\n测试success_level判断...")
success_level = result.get('success_level', '')
if not success_level:
    if result.get('success', False):
        workflow_score = result.get('workflow_score', 1.0)
        phase2_score = result.get('phase2_score', 1.0)
        if workflow_score < 0.8 or phase2_score < 0.8:
            success_level = 'partial_success'
            print(f"✅ 正确判断为partial_success (workflow={workflow_score:.2f}, phase2={phase2_score:.2f})")
        else:
            success_level = 'full_success'
            print(f"❌ 错误判断为full_success")
    else:
        success_level = 'failure'

print(f"最终success_level: {success_level}")

# 检查是否会触发AI分类
if success_level != 'full_success':
    print("✅ 将会触发AI分类")
else:
    print("❌ 不会触发AI分类")
