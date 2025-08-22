#!/usr/bin/env python3
"""
测试AI分类在ultra_parallel_runner到smart_batch_runner的完整调用链
"""

import subprocess
import time
import os
import signal

def test_direct_smart_batch_runner():
    """直接测试smart_batch_runner"""
    print("=" * 60)
    print("测试1: 直接调用smart_batch_runner.py")
    print("=" * 60)
    
    cmd = [
        "python", "smart_batch_runner.py",
        "--model", "test-model",
        "--prompt-types", "baseline",
        "--difficulty", "easy",
        "--task-types", "simple_task",
        "--num-instances", "1",
        "--max-workers", "1",
        "--tool-success-rate", "0.8",
        "--ai-classification",  # 明确启用AI分类
        "--no-adaptive",
        "--qps", "5",
        "--silent"
    ]
    
    print(f"命令: {' '.join(cmd)}")
    
    # 启动进程并捕获输出
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    # 等待5秒收集输出
    time.sleep(5)
    
    # 终止进程
    proc.terminate()
    time.sleep(1)
    if proc.poll() is None:
        proc.kill()
    
    # 读取输出
    output = proc.stdout.read()
    
    # 检查是否有AI分类日志
    if "基于TXT文件的AI错误分类系统已启用" in output or "AI classifier initialized" in output:
        print("✅ AI分类已启用！")
    else:
        print("❌ AI分类未启用！")
    
    print("\n关键日志:")
    for line in output.split('\n'):
        if 'AI' in line or 'classifier' in line or 'gpt-5-nano' in line:
            print(f"  {line}")

def test_ultra_parallel_to_smart_batch():
    """测试通过ultra_parallel_runner调用"""
    print("\n" + "=" * 60)
    print("测试2: 通过ultra_parallel_runner.py调用")
    print("=" * 60)
    
    # 创建一个最小的配置
    cmd = [
        "python", "ultra_parallel_runner.py",
        "--models", "test-model",
        "--phase", "5.1",
        "--instances", "1",
        "--max-workers", "1",
        "--rate-mode", "fixed",
        "--qps", "5",
        "--silent"
    ]
    
    print(f"命令: {' '.join(cmd)}")
    
    # 启动进程
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    # 等待10秒收集输出
    time.sleep(10)
    
    # 终止进程
    proc.terminate()
    time.sleep(1)
    if proc.poll() is None:
        proc.kill()
    
    # 读取输出
    output = proc.stdout.read()
    
    # 查找smart_batch_runner的启动命令
    print("\n查找smart_batch_runner启动命令:")
    for line in output.split('\n'):
        if 'smart_batch_runner.py' in line:
            print(f"  {line}")
            if '--ai-classification' in line:
                print("  ✅ 找到 --ai-classification 参数")
            else:
                print("  ❌ 未找到 --ai-classification 参数")

def check_batch_test_logs():
    """检查最新的batch_test日志"""
    print("\n" + "=" * 60)
    print("测试3: 检查最新的batch_test日志")
    print("=" * 60)
    
    import glob
    logs = sorted(glob.glob("logs/batch_test_*.log"), key=os.path.getmtime, reverse=True)
    
    if logs:
        latest_log = logs[0]
        print(f"最新日志: {latest_log}")
        
        with open(latest_log, 'r') as f:
            content = f.read()
            
        # 查找AI分类相关日志
        found_ai = False
        for line in content.split('\n')[:100]:  # 只看前100行
            if 'AI' in line and 'classifier' in line:
                print(f"  找到: {line}")
                found_ai = True
        
        if not found_ai:
            print("  ❌ 未找到AI分类初始化日志")

if __name__ == "__main__":
    # 测试1：直接调用
    test_direct_smart_batch_runner()
    
    # 测试2：通过ultra_parallel调用
    # test_ultra_parallel_to_smart_batch()  # 暂时跳过，避免运行太久
    
    # 测试3：检查日志
    check_batch_test_logs()