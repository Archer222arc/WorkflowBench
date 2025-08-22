#!/usr/bin/env python3
"""
测试文件锁是否正常工作
"""

import sys
import os
import time
import json
import random
from pathlib import Path
from multiprocessing import Process

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from file_lock_manager import get_file_lock

def worker_process(worker_id: int, num_updates: int = 5):
    """工作进程，模拟并发写入"""
    test_file = Path("test_concurrent_write.json")
    lock_manager = get_file_lock(test_file)
    
    print(f"Worker {worker_id} (PID {os.getpid()}) started")
    
    for i in range(num_updates):
        def update_func(data):
            """更新数据"""
            # 初始化结构
            if 'total_updates' not in data:
                data['total_updates'] = 0
            if 'workers' not in data:
                data['workers'] = {}
            
            # 更新计数
            data['total_updates'] += 1
            
            # 记录工作进程的更新
            worker_key = f"worker_{worker_id}"
            if worker_key not in data['workers']:
                data['workers'][worker_key] = {
                    'pid': os.getpid(),
                    'updates': 0
                }
            data['workers'][worker_key]['updates'] += 1
            
            print(f"  Worker {worker_id}: Update {i+1}/{num_updates} (total: {data['total_updates']})")
            return data
        
        # 尝试更新
        success = lock_manager.update_json_safe(update_func)
        if not success:
            print(f"  Worker {worker_id}: Failed to update {i+1}")
        
        # 随机延迟，模拟真实工作负载
        time.sleep(random.uniform(0.05, 0.15))
    
    print(f"Worker {worker_id} completed")

def test_concurrent_writes():
    """测试并发写入"""
    test_file = Path("test_concurrent_write.json")
    
    # 清理旧文件
    if test_file.exists():
        test_file.unlink()
    
    print("=== 测试文件锁并发写入 ===\n")
    
    # 创建多个工作进程
    num_workers = 4
    num_updates_per_worker = 5
    expected_total = num_workers * num_updates_per_worker
    
    print(f"启动 {num_workers} 个工作进程，每个进程更新 {num_updates_per_worker} 次")
    print(f"预期总更新次数: {expected_total}\n")
    
    # 启动工作进程
    processes = []
    for i in range(num_workers):
        p = Process(target=worker_process, args=(i, num_updates_per_worker))
        p.start()
        processes.append(p)
    
    # 等待所有进程完成
    for p in processes:
        p.join()
    
    print("\n所有工作进程已完成\n")
    
    # 验证结果
    if test_file.exists():
        with open(test_file, 'r') as f:
            final_data = json.load(f)
        
        print("=== 最终结果 ===")
        print(f"总更新次数: {final_data.get('total_updates', 0)} (预期: {expected_total})")
        
        if 'workers' in final_data:
            print("\n各工作进程统计:")
            for worker_id, stats in sorted(final_data['workers'].items()):
                print(f"  {worker_id}: {stats['updates']} 次更新 (PID: {stats['pid']})")
        
        # 验证数据一致性
        actual_total = final_data.get('total_updates', 0)
        if actual_total == expected_total:
            print("\n✅ 测试通过! 所有更新都成功记录，没有数据丢失")
        else:
            print(f"\n❌ 测试失败! 缺失 {expected_total - actual_total} 次更新")
    else:
        print("❌ 测试文件不存在")
    
    # 清理测试文件
    if test_file.exists():
        test_file.unlink()
    lock_file = test_file.with_suffix('.lock')
    if lock_file.exists():
        lock_file.unlink()

if __name__ == "__main__":
    test_concurrent_writes()