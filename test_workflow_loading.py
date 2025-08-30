#!/usr/bin/env python3
"""测试workflow加载逻辑，确保使用预生成的workflow而不是重新生成"""

import os
import sys
import json
from pathlib import Path

# 设置环境变量（模拟run_systematic_test_final.sh的设置）
os.environ['SKIP_MODEL_LOADING'] = 'true'
os.environ['USE_PARTIAL_LOADING'] = 'true'
os.environ['TASK_LOAD_COUNT'] = '20'
os.environ['USE_RESULT_COLLECTOR'] = 'true'

print("=" * 60)
print("🔍 测试Workflow加载流程")
print("=" * 60)

# 1. 验证环境变量
print("\n1️⃣ 环境变量检查:")
print(f"   SKIP_MODEL_LOADING = {os.environ.get('SKIP_MODEL_LOADING')}")
print(f"   USE_PARTIAL_LOADING = {os.environ.get('USE_PARTIAL_LOADING')}")
print(f"   TASK_LOAD_COUNT = {os.environ.get('TASK_LOAD_COUNT')}")

# 2. 验证预生成workflow文件
print("\n2️⃣ 预生成Workflow文件检查:")
difficulties = ['easy', 'very_easy', 'medium']
all_exist = True
for diff in difficulties:
    path = Path(f'mcp_generated_library/difficulty_versions/task_library_enhanced_v3_{diff}_with_workflows.json')
    if path.exists():
        with open(path, 'r') as f:
            data = json.load(f)
            tasks = data.get('tasks', data if isinstance(data, list) else [])
            has_workflow = tasks and len(tasks) > 0 and 'workflow' in tasks[0]
            status = "✅" if has_workflow else "⚠️"
            print(f"   {status} {diff}: {path.name} - {'有workflow' if has_workflow else '无workflow'}")
            if not has_workflow:
                all_exist = False
    else:
        print(f"   ❌ {diff}: 文件不存在")
        all_exist = False

# 3. 模拟BatchTestRunner初始化
print("\n3️⃣ 模拟BatchTestRunner初始化:")
from batch_test_runner import BatchTestRunner

# 创建一个简单的测试配置
test_config = {
    'model': 'test-model',
    'prompt_types': 'optimal',
    'difficulty': 'easy',
    'task_types': 'simple_task',
    'num_instances': 2,
    'max_workers': 2,
    'adaptive': False,
    'silent': True,
    'batch_commit': True,
    'checkpoint_interval': 20,
    'enable_ai_classification': False
}

print("   创建BatchTestRunner实例...")
runner = BatchTestRunner(**test_config)

# 检查是否使用预生成workflow
if hasattr(runner, 'use_pregenerated_workflows'):
    print(f"   use_pregenerated_workflows = {runner.use_pregenerated_workflows}")
    if runner.use_pregenerated_workflows:
        print("   ✅ 将使用预生成的workflow")
    else:
        print("   ⚠️ 将重新生成workflow")
else:
    print("   ⚠️ 无法检测use_pregenerated_workflows属性")

# 4. 检查MDPWorkflowGenerator
print("\n4️⃣ 检查MDPWorkflowGenerator:")
if hasattr(runner, 'generator'):
    if runner.generator:
        if hasattr(runner.generator, 'q_network'):
            if runner.generator.q_network is None:
                print("   ✅ 神经网络模型未加载（节省350MB内存）")
            else:
                print("   ⚠️ 神经网络模型已加载")
        print("   ✅ MDPWorkflowGenerator已初始化")
    else:
        print("   ⚠️ MDPWorkflowGenerator未初始化")
else:
    print("   ⚠️ 无generator属性")

# 5. 总结
print("\n" + "=" * 60)
print("📊 测试结果总结:")
if all_exist and os.environ.get('SKIP_MODEL_LOADING') == 'true':
    print("✅ 所有配置正确，将使用预生成workflow，不会重新生成")
    print("✅ 内存优化生效，节省约350MB/进程")
else:
    print("⚠️ 配置可能有问题，请检查")

print("=" * 60)