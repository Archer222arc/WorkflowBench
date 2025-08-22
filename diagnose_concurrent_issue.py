#!/usr/bin/env python3
"""诊断并发问题的脚本"""

import sys
import threading
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

def diagnose_concurrent_initialization():
    """诊断并发初始化问题"""
    print("=" * 60)
    print("诊断并发初始化问题")
    print("=" * 60)
    
    # 1. 检查MDPWorkflowGenerator是否线程安全
    print("\n1. 检查MDPWorkflowGenerator线程安全性：")
    from mdp_workflow_generator import MDPWorkflowGenerator
    
    generators = []
    def create_generator(idx):
        print(f"  线程{idx}: 创建MDPWorkflowGenerator...")
        start = time.time()
        try:
            gen = MDPWorkflowGenerator()
            generators.append(gen)
            print(f"  线程{idx}: 成功 ({time.time()-start:.2f}秒)")
        except Exception as e:
            print(f"  线程{idx}: 失败 - {e}")
    
    # 测试2个并发创建
    threads = []
    for i in range(2):
        t = threading.Thread(target=create_generator, args=(i,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join(timeout=30)
    
    if len(generators) == 2:
        print(f"  ✅ 创建了{len(generators)}个实例")
        print(f"  是否是同一实例: {generators[0] is generators[1]}")
    else:
        print(f"  ❌ 只创建了{len(generators)}个实例")
    
    # 2. 检查BatchTestRunner的并发问题
    print("\n2. 检查BatchTestRunner并发初始化：")
    from batch_test_runner import BatchTestRunner
    
    runners = []
    def create_runner(idx):
        print(f"  线程{idx}: 创建BatchTestRunner...")
        start = time.time()
        try:
            runner = BatchTestRunner(debug=False, silent=True)
            runners.append(runner)
            print(f"  线程{idx}: 成功 ({time.time()-start:.2f}秒)")
        except Exception as e:
            print(f"  线程{idx}: 失败 - {e}")
    
    threads = []
    for i in range(2):
        t = threading.Thread(target=create_runner, args=(i,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join(timeout=30)
    
    print(f"  创建了{len(runners)}个BatchTestRunner实例")
    
    # 3. 检查数据管理器
    print("\n3. 检查数据管理器状态：")
    from enhanced_cumulative_manager import EnhancedCumulativeManager
    
    manager = EnhancedCumulativeManager()
    print(f"  管理器类型: {type(manager).__name__}")
    print(f"  有_flush_buffer方法: {hasattr(manager, '_flush_buffer')}")
    print(f"  有finalize方法: {hasattr(manager, 'finalize')}")
    
    # 4. 检查环境变量
    print("\n4. 检查环境变量：")
    import os
    print(f"  STORAGE_FORMAT: {os.environ.get('STORAGE_FORMAT', 'json')}")
    
    # 5. 检查进程状态
    print("\n5. 检查资源使用：")
    import psutil
    process = psutil.Process()
    print(f"  CPU使用率: {process.cpu_percent()}%")
    print(f"  内存使用: {process.memory_info().rss / 1024 / 1024:.1f} MB")
    print(f"  线程数: {process.num_threads()}")
    
    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)

if __name__ == "__main__":
    diagnose_concurrent_initialization()