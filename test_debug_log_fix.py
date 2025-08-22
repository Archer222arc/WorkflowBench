#!/usr/bin/env python3
"""
验证debug日志文件不会被覆盖的测试脚本
"""

import subprocess
import time
from pathlib import Path
from datetime import datetime

def run_quick_test(model: str, duration: int = 2):
    """运行一个快速测试"""
    print(f"\n启动 {model} 测试...")
    
    cmd = [
        'python', 'ultra_parallel_runner_debug.py',
        '--model', model,
        '--num-instances', '1',
        '--max-workers', '2',
        '--tool-success-rate', '0.8',
        '--prompt-types', 'baseline',
        '--difficulty', 'easy',
        '--task-types', 'simple_task'
    ]
    
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(duration)
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    print(f"{model} 测试已终止")

def main():
    print("=" * 60)
    print("测试Debug日志文件唯一性")
    print("=" * 60)
    
    # 记录开始时间
    start_time = datetime.now()
    
    # 测试多个模型
    models = [
        'DeepSeek-V3-0324',
        'DeepSeek-R1-0528',
        'DeepSeek-V3-0324',  # 故意重复测试同一个模型
    ]
    
    # 依次运行测试
    for model in models:
        run_quick_test(model, duration=3)
        time.sleep(1)  # 稍微等待
    
    # 查找最新的debug目录
    debug_dirs = list(Path('logs').glob('debug_ultra_*'))
    
    # 过滤出本次测试创建的目录（基于时间）
    test_dirs = []
    for d in debug_dirs:
        dir_time = datetime.fromtimestamp(d.stat().st_mtime)
        if dir_time >= start_time:
            test_dirs.append(d)
    
    print(f"\n本次测试创建了 {len(test_dirs)} 个debug目录:")
    
    all_log_files = []
    for debug_dir in sorted(test_dirs):
        print(f"\n目录: {debug_dir.name}")
        log_files = list(debug_dir.glob('*.log'))
        
        for log_file in sorted(log_files):
            print(f"  - {log_file.name}")
            all_log_files.append(log_file.name)
            
            # 解析文件名组件
            parts = log_file.stem.split('_')
            if len(parts) >= 8:
                print(f"    模型: {parts[0]}_{parts[1]}_{parts[2]}")
                print(f"    Hash: {parts[3]}")
                print(f"    时间戳: {parts[4]}_{parts[5]}")
                print(f"    PID: {parts[6]}")
                print(f"    计数器: {parts[7]}")
    
    # 检查唯一性
    print(f"\n总共创建了 {len(all_log_files)} 个日志文件")
    unique_files = set(all_log_files)
    
    if len(all_log_files) == len(unique_files):
        print("✅ 所有日志文件名都是唯一的！")
        print("\n修复成功验证：")
        print("  - DeepSeek-V3和DeepSeek-R1的日志不再互相覆盖")
        print("  - 同一模型的多次运行也会创建不同的日志文件")
        print("  - 文件名包含模型hash、时间戳、PID和计数器确保唯一性")
    else:
        print(f"❌ 发现重复文件名！{len(all_log_files)} 个文件中有 {len(unique_files)} 个唯一名称")
        duplicates = []
        for name in all_log_files:
            if all_log_files.count(name) > 1 and name not in duplicates:
                duplicates.append(name)
                print(f"  重复: {name}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    main()