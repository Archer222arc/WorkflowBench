#!/usr/bin/env python3
"""
测试部分加载功能是否正常工作
"""

import os
import sys
import json
import psutil
from pathlib import Path

def get_memory_usage():
    """获取当前进程的内存使用（MB）"""
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    return mem_info.rss / 1024 / 1024  # Convert to MB

def test_without_partial_loading():
    """测试不使用部分加载（传统方式）"""
    print("\n" + "="*60)
    print("测试1: 传统全量加载")
    print("="*60)
    
    initial_mem = get_memory_usage()
    print(f"初始内存: {initial_mem:.2f} MB")
    
    # 清除环境变量
    os.environ.pop('USE_PARTIAL_LOADING', None)
    os.environ.pop('TASK_LOAD_COUNT', None)
    
    # 导入并创建runner
    from batch_test_runner import BatchTestRunner
    
    runner = BatchTestRunner(debug=True, silent=False)
    runner._load_task_library(difficulty="easy")
    
    # 统计加载的任务
    total_tasks = sum(len(tasks) for tasks in runner.tasks_by_type.values())
    
    after_load_mem = get_memory_usage()
    memory_used = after_load_mem - initial_mem
    
    print(f"加载后内存: {after_load_mem:.2f} MB")
    print(f"内存增加: {memory_used:.2f} MB")
    print(f"加载任务数: {total_tasks}")
    
    for task_type, tasks in runner.tasks_by_type.items():
        print(f"  {task_type}: {len(tasks)} 个任务")
    
    return {
        'total_tasks': total_tasks,
        'memory_used': memory_used
    }

def test_with_partial_loading():
    """测试使用部分加载"""
    print("\n" + "="*60)
    print("测试2: 部分加载（20个/类型）")
    print("="*60)
    
    initial_mem = get_memory_usage()
    print(f"初始内存: {initial_mem:.2f} MB")
    
    # 设置环境变量启用部分加载
    os.environ['USE_PARTIAL_LOADING'] = 'true'
    os.environ['TASK_LOAD_COUNT'] = '20'
    
    # 重新导入以应用新的环境变量
    import importlib
    import batch_test_runner
    importlib.reload(batch_test_runner)
    
    from batch_test_runner import BatchTestRunner
    
    runner = BatchTestRunner(debug=True, silent=False)
    runner._load_task_library(difficulty="easy")
    
    # 统计加载的任务
    total_tasks = sum(len(tasks) for tasks in runner.tasks_by_type.values())
    
    after_load_mem = get_memory_usage()
    memory_used = after_load_mem - initial_mem
    
    print(f"加载后内存: {after_load_mem:.2f} MB")
    print(f"内存增加: {memory_used:.2f} MB")
    print(f"加载任务数: {total_tasks}")
    
    for task_type, tasks in runner.tasks_by_type.items():
        print(f"  {task_type}: {len(tasks)} 个任务")
    
    # 验证每个类型最多20个任务
    for task_type, tasks in runner.tasks_by_type.items():
        if len(tasks) > 20:
            print(f"❌ 错误：{task_type} 有 {len(tasks)} 个任务（应该 ≤ 20）")
    
    return {
        'total_tasks': total_tasks,
        'memory_used': memory_used
    }

def main():
    """主函数"""
    print("="*60)
    print("部分加载功能测试")
    print("="*60)
    
    # 测试1：全量加载
    result1 = test_without_partial_loading()
    
    # 测试2：部分加载
    result2 = test_with_partial_loading()
    
    # 对比结果
    print("\n" + "="*60)
    print("📊 对比结果")
    print("="*60)
    
    if result1 and result2:
        print(f"全量加载: {result1['total_tasks']} 任务, {result1['memory_used']:.2f} MB")
        print(f"部分加载: {result2['total_tasks']} 任务, {result2['memory_used']:.2f} MB")
        
        task_reduction = (1 - result2['total_tasks'] / result1['total_tasks']) * 100
        memory_reduction = (1 - result2['memory_used'] / result1['memory_used']) * 100 if result1['memory_used'] > 0 else 0
        
        print(f"\n任务减少: {task_reduction:.1f}%")
        print(f"内存减少: {memory_reduction:.1f}%")
        
        if result2['total_tasks'] < result1['total_tasks'] * 0.3:  # 少于30%的任务
            print("\n✅ 部分加载功能正常工作！")
        else:
            print("\n⚠️ 部分加载可能未生效")

if __name__ == "__main__":
    main()