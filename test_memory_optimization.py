#!/usr/bin/env python3
"""
测试内存优化效果 - 验证使用预生成workflow的内存节省
"""

import psutil
import os
import json
import time
from pathlib import Path
from datetime import datetime

def get_memory_usage():
    """获取当前进程的内存使用（MB）"""
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    return mem_info.rss / 1024 / 1024  # Convert to MB

def test_without_pregenerated():
    """测试不使用预生成workflow（需要加载MDPWorkflowGenerator）"""
    print("\n" + "="*60)
    print("测试1: 不使用预生成workflow（动态生成）")
    print("="*60)
    
    initial_mem = get_memory_usage()
    print(f"初始内存: {initial_mem:.2f} MB")
    
    # 导入并初始化MDPWorkflowGenerator
    from mdp_workflow_generator import MDPWorkflowGenerator
    
    print("正在初始化MDPWorkflowGenerator...")
    start_time = time.time()
    generator = MDPWorkflowGenerator(
        model_path="checkpoints/best_model.pt",
        use_embeddings=True
    )
    init_time = time.time() - start_time
    
    after_init_mem = get_memory_usage()
    memory_increase = after_init_mem - initial_mem
    
    print(f"初始化完成，耗时: {init_time:.2f}秒")
    print(f"初始化后内存: {after_init_mem:.2f} MB")
    print(f"内存增加: {memory_increase:.2f} MB")
    
    # 生成一个workflow测试
    print("\n生成一个测试workflow...")
    task_instance = {
        'id': 'test_001',
        'description': 'Test task',
        'task_type': 'simple_task',
        'required_tools': ['file_operations_reader', 'data_processing_parser'],
        'expected_outputs': {}
    }
    
    workflow = generator.generate_workflow(
        task_type='simple_task',
        task_instance=task_instance
    )
    
    if workflow:
        print(f"✅ Workflow生成成功，包含 {len(workflow.get('optimal_sequence', []))} 个步骤")
    else:
        print("❌ Workflow生成失败")
    
    final_mem = get_memory_usage()
    print(f"最终内存: {final_mem:.2f} MB")
    print(f"总内存使用: {final_mem - initial_mem:.2f} MB")
    
    return {
        'initial_memory': initial_mem,
        'after_init_memory': after_init_mem,
        'final_memory': final_mem,
        'memory_increase': memory_increase,
        'total_memory': final_mem - initial_mem
    }

def test_with_pregenerated():
    """测试使用预生成workflow（不需要MDPWorkflowGenerator）"""
    print("\n" + "="*60)
    print("测试2: 使用预生成workflow（内存优化）")
    print("="*60)
    
    initial_mem = get_memory_usage()
    print(f"初始内存: {initial_mem:.2f} MB")
    
    # 检查预生成的workflow文件
    workflow_file = Path("mcp_generated_library/difficulty_versions/task_library_enhanced_v3_easy_with_workflows.json")
    
    if not workflow_file.exists():
        print(f"❌ 预生成文件不存在: {workflow_file}")
        return None
    
    print(f"加载预生成的workflow文件...")
    start_time = time.time()
    
    with open(workflow_file, 'r') as f:
        data = json.load(f)
    
    load_time = time.time() - start_time
    
    tasks = data.get('tasks', data if isinstance(data, list) else [])
    
    after_load_mem = get_memory_usage()
    memory_increase = after_load_mem - initial_mem
    
    print(f"加载完成，耗时: {load_time:.2f}秒")
    print(f"加载了 {len(tasks)} 个任务")
    print(f"加载后内存: {after_load_mem:.2f} MB")
    print(f"内存增加: {memory_increase:.2f} MB")
    
    # 检查workflow是否存在
    workflows_found = 0
    for task in tasks[:10]:  # 检查前10个任务
        if 'workflow' in task:
            workflows_found += 1
    
    print(f"\n✅ 前10个任务中有 {workflows_found} 个包含预生成的workflow")
    
    # 显示一个示例workflow
    if workflows_found > 0:
        for task in tasks:
            if 'workflow' in task:
                workflow = task['workflow']
                print(f"示例workflow包含 {len(workflow.get('optimal_sequence', []))} 个步骤")
                break
    
    # 创建轻量级mock generator（仅用于tool_registry）
    print("\n创建轻量级MockGenerator...")
    # 加载工具注册表（轻量级）
    tool_registry_path = Path("mcp_generated_library/tool_registry_consolidated.json")
    if tool_registry_path.exists():
        with open(tool_registry_path, 'r') as f:
            tool_registry_data = json.load(f)
        print(f"  加载了 {len(tool_registry_data.get('tools', []))} 个工具定义")
    
    class MockGenerator:
        def __init__(self):
            self.full_tool_registry = tool_registry_data
    
    mock_gen = MockGenerator()
    
    final_mem = get_memory_usage()
    print(f"最终内存: {final_mem:.2f} MB")
    print(f"总内存使用: {final_mem - initial_mem:.2f} MB")
    
    return {
        'initial_memory': initial_mem,
        'after_load_memory': after_load_mem,
        'final_memory': final_mem,
        'memory_increase': memory_increase,
        'total_memory': final_mem - initial_mem
    }

def main():
    """主函数"""
    print("="*60)
    print("内存优化效果测试")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # 测试1：不使用预生成（传统方式）
    result1 = test_without_pregenerated()
    
    # 等待一下让内存稳定
    time.sleep(2)
    
    # 测试2：使用预生成（优化方式）
    result2 = test_with_pregenerated()
    
    # 对比结果
    print("\n" + "="*60)
    print("📊 内存优化效果对比")
    print("="*60)
    
    if result1 and result2:
        traditional_mem = result1['memory_increase']
        optimized_mem = result2['memory_increase'] if result2 else 0
        
        print(f"传统方式（动态生成）: {traditional_mem:.2f} MB")
        print(f"优化方式（预生成）  : {optimized_mem:.2f} MB")
        print(f"内存节省: {traditional_mem - optimized_mem:.2f} MB")
        print(f"节省比例: {((traditional_mem - optimized_mem) / traditional_mem * 100):.1f}%")
        
        # 估算25个并发进程的内存使用
        print("\n" + "="*60)
        print("📈 25个并发进程的预估内存使用")
        print("="*60)
        print(f"传统方式: {traditional_mem * 25:.2f} MB ({traditional_mem * 25 / 1024:.2f} GB)")
        print(f"优化方式: {optimized_mem * 25:.2f} MB ({optimized_mem * 25 / 1024:.2f} GB)")
        print(f"总节省  : {(traditional_mem - optimized_mem) * 25:.2f} MB ({(traditional_mem - optimized_mem) * 25 / 1024:.2f} GB)")
        
        if traditional_mem * 25 / 1024 > 8 and optimized_mem * 25 / 1024 < 2:
            print("\n✅ 优化成功！内存使用从 >8GB 降到 <2GB")
        elif optimized_mem < traditional_mem:
            print(f"\n✅ 优化有效！内存使用减少了 {((traditional_mem - optimized_mem) / traditional_mem * 100):.1f}%")
        else:
            print("\n⚠️ 优化效果不明显，需要进一步检查")

if __name__ == "__main__":
    main()