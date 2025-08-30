#!/usr/bin/env python3
"""
测试新的QPS控制机制
"""

import time
import threading
from qps_limiter import get_qps_limiter

def test_single_thread():
    """测试单线程QPS控制"""
    print("\n=== 测试单线程QPS控制 ===")
    
    # 测试QPS=10（每个请求间隔0.1秒）
    limiter = get_qps_limiter("qwen2.5-7b-instruct", qps=10)
    
    print(f"QPS设置: 10，期望间隔: 0.1秒")
    
    times = []
    for i in range(5):
        start = time.time()
        limiter.acquire()
        elapsed = time.time() - start
        times.append(elapsed)
        print(f"  请求 {i+1}: 等待了 {elapsed:.3f}秒")
        time.sleep(0.05)  # 模拟API调用时间
    
    avg_wait = sum(times[1:]) / len(times[1:]) if len(times) > 1 else 0
    print(f"平均等待时间: {avg_wait:.3f}秒")

def test_multi_thread():
    """测试多线程QPS控制"""
    print("\n=== 测试多线程QPS控制 ===")
    
    results = []
    lock = threading.Lock()
    
    def worker(thread_id):
        limiter = get_qps_limiter("qwen2.5-7b-instruct", qps=10)
        for i in range(3):
            start = time.time()
            limiter.acquire()
            elapsed = time.time() - start
            with lock:
                results.append((thread_id, i, elapsed))
                print(f"  线程{thread_id} 请求{i+1}: 等待了 {elapsed:.3f}秒")
            time.sleep(0.05)  # 模拟API调用
    
    # 启动3个线程
    threads = []
    for i in range(3):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
    
    # 等待所有线程完成
    for t in threads:
        t.join()
    
    print(f"总共 {len(results)} 个请求")

def test_azure_no_limit():
    """测试Azure模型无QPS限制"""
    print("\n=== 测试Azure模型（无限制） ===")
    
    limiter = get_qps_limiter("DeepSeek-V3-0324")
    
    times = []
    for i in range(5):
        start = time.time()
        limiter.acquire()
        elapsed = time.time() - start
        times.append(elapsed)
        print(f"  请求 {i+1}: 等待了 {elapsed:.3f}秒（应该是0）")
    
    avg_wait = sum(times) / len(times)
    print(f"平均等待时间: {avg_wait:.3f}秒（应该接近0）")

def test_cross_process():
    """测试跨进程QPS控制（通过文件共享）"""
    print("\n=== 测试跨进程共享 ===")
    
    import subprocess
    import os
    
    # 创建测试脚本
    test_script = '''
import time
from qps_limiter import get_qps_limiter
import sys

process_id = sys.argv[1]
limiter = get_qps_limiter("qwen2.5-7b-instruct", qps=10)

for i in range(3):
    start = time.time()
    limiter.acquire()
    elapsed = time.time() - start
    print(f"进程{process_id} 请求{i+1}: 等待{elapsed:.3f}秒")
    time.sleep(0.05)
'''
    
    # 保存测试脚本
    with open('/tmp/test_qps_process.py', 'w') as f:
        f.write(test_script)
    
    # 启动两个进程
    processes = []
    for i in range(2):
        p = subprocess.Popen(['python3', '/tmp/test_qps_process.py', str(i)], 
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        processes.append(p)
    
    # 等待完成并收集输出
    for i, p in enumerate(processes):
        stdout, stderr = p.communicate()
        print(f"进程{i}输出:")
        print(stdout)
        if stderr:
            print(f"错误: {stderr}")

def main():
    print("="*50)
    print("QPS控制机制测试")
    print("="*50)
    
    # 运行各项测试
    test_single_thread()
    test_multi_thread()
    test_azure_no_limit()
    test_cross_process()
    
    print("\n✅ 所有测试完成！")

if __name__ == "__main__":
    main()