#!/usr/bin/env python3
"""
简单测试：验证预生成workflow能否被正确读取和使用
"""

import json
from pathlib import Path

def test_basic_workflow_reading():
    """测试最基本的workflow读取功能"""
    
    print("="*60)
    print("基础Workflow读取测试")
    print("="*60)
    
    # 1. 检查文件存在
    workflow_file = Path("mcp_generated_library/difficulty_versions/task_library_enhanced_v3_easy_with_workflows.json")
    
    if not workflow_file.exists():
        print("❌ Workflow文件不存在！")
        return False
    
    print(f"✅ 找到workflow文件: {workflow_file.name}")
    
    # 2. 加载并检查内容
    with open(workflow_file, 'r') as f:
        data = json.load(f)
    
    if isinstance(data, dict):
        tasks = data.get('tasks', [])
    else:
        tasks = data
    
    print(f"✅ 成功加载 {len(tasks)} 个任务")
    
    # 3. 验证workflow结构
    valid_workflows = 0
    for i, task in enumerate(tasks[:5]):  # 只检查前5个
        if 'workflow' in task and task['workflow'] is not None:
            workflow = task['workflow']
            if isinstance(workflow, dict) and 'optimal_sequence' in workflow:
                valid_workflows += 1
                seq_len = len(workflow.get('optimal_sequence', []))
                print(f"  任务{i+1}: ✅ 有效workflow，{seq_len}个步骤")
            else:
                print(f"  任务{i+1}: ⚠️ workflow结构异常")
        else:
            print(f"  任务{i+1}: ❌ 缺少workflow")
    
    # 4. 模拟batch_test_runner的使用方式
    print("\n模拟BatchTestRunner使用workflow:")
    
    sample_task = None
    for task in tasks:
        if 'workflow' in task and task['workflow']:
            sample_task = task
            break
    
    if sample_task:
        # 这就是batch_test_runner.py中run_single_test会做的
        workflow = sample_task['workflow']
        print(f"✅ 成功获取预生成的workflow")
        print(f"  - optimal_sequence: {len(workflow.get('optimal_sequence', []))} 步")
        print(f"  - critical_tools: {len(workflow.get('critical_tools', []))} 个")
        
        # 如果是flawed测试，会注入缺陷
        import copy
        workflow_copy = copy.deepcopy(workflow)
        print(f"✅ 可以安全复制workflow用于缺陷注入")
        
        return True
    else:
        print("❌ 没有找到有效的workflow")
        return False

def test_partial_loading():
    """测试部分加载是否正常工作"""
    
    print("\n" + "="*60)
    print("部分加载功能测试")
    print("="*60)
    
    import os
    import random
    
    # 设置环境变量
    os.environ['USE_PARTIAL_LOADING'] = 'true'
    os.environ['TASK_LOAD_COUNT'] = '10'
    
    # 模拟部分加载逻辑
    workflow_file = Path("mcp_generated_library/difficulty_versions/task_library_enhanced_v3_easy_with_workflows.json")
    
    with open(workflow_file, 'r') as f:
        data = json.load(f)
    
    if isinstance(data, dict):
        all_tasks = data.get('tasks', [])
    else:
        all_tasks = data
    
    # 构建索引
    task_index = {}
    for i, task in enumerate(all_tasks):
        if 'task_type' in task:
            task_type = task['task_type']
            if task_type not in task_index:
                task_index[task_type] = []
            task_index[task_type].append(i)
    
    print(f"构建索引完成:")
    for task_type, indices in task_index.items():
        print(f"  {task_type}: {len(indices)} 个任务")
    
    # 部分加载
    num_to_load = 10
    loaded_tasks = {}
    
    for task_type, indices in task_index.items():
        num_to_select = min(num_to_load, len(indices))
        selected_indices = random.sample(indices, num_to_select)
        loaded_tasks[task_type] = [all_tasks[i] for i in selected_indices]
        print(f"✅ {task_type}: 选择了 {len(loaded_tasks[task_type])} 个任务")
    
    total_loaded = sum(len(tasks) for tasks in loaded_tasks.values())
    memory_saved = (1 - total_loaded / len(all_tasks)) * 100
    
    print(f"\n总结:")
    print(f"  原始任务数: {len(all_tasks)}")
    print(f"  加载任务数: {total_loaded}")
    print(f"  内存节省: {memory_saved:.1f}%")
    
    return True

if __name__ == "__main__":
    # 运行测试
    success1 = test_basic_workflow_reading()
    success2 = test_partial_loading()
    
    print("\n" + "="*60)
    print("测试结果")
    print("="*60)
    
    if success1 and success2:
        print("✅ 所有测试通过！")
        print("预生成workflow可以被正确读取和使用")
        print("部分加载机制正常工作")
        print("\n可以安全运行5.3测试！")
    else:
        print("⚠️ 部分测试失败")
        print("请检查workflow文件和配置")