#!/usr/bin/env python3
"""测试workflow生成是否正常"""

import json
import sys
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from mdp_workflow_generator import MDPWorkflowGenerator

def test_workflow_generation():
    """测试workflow生成"""
    print("初始化MDPWorkflowGenerator...")
    generator = MDPWorkflowGenerator()
    
    # 加载任务库
    task_lib_path = Path("mcp_generated_library/difficulty_versions/task_library_enhanced_v3_easy.json")
    if not task_lib_path.exists():
        print(f"任务库文件不存在: {task_lib_path}")
        return False
    
    with open(task_lib_path, 'r') as f:
        data = json.load(f)
    
    tasks = data.get('tasks', [])
    print(f"加载了 {len(tasks)} 个任务")
    
    if not tasks:
        print("没有任务可用")
        return False
    
    # 测试第一个任务
    task = tasks[0]
    task_id = task.get('instance_id') or task.get('id', 'unknown')
    print(f"\n测试任务: {task_id}")
    print(f"任务类型: {task.get('task_type')}")
    
    # 创建task_dict
    task_dict = {
        'id': task_id,
        'description': task.get('description', ''),
        'task_type': task.get('task_type'),
        'required_tools': task.get('required_tools', []),
        'expected_outputs': task.get('expected_outputs', {})
    }
    
    # 生成workflow
    print("\n生成workflow...")
    try:
        workflow = generator.generate_workflow(
            task.get('task_type'),
            task_instance=task_dict
        )
        
        if workflow:
            print("✅ Workflow生成成功")
            print(f"   步骤数: {len(workflow.get('optimal_sequence', []))}")
            return True
        else:
            print("❌ Workflow生成失败")
            return False
    except Exception as e:
        print(f"❌ 生成时出错: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_workflow_generation()
    sys.exit(0 if success else 1)