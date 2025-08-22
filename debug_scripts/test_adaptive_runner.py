#!/usr/bin/env python3
"""
测试自适应限流的批量测试运行器
"""

import subprocess
import sys

def run_test(mode: str, workers: int = 10, qps: float = 10.0):
    """运行测试并显示对比"""
    
    print(f"\n{'='*60}")
    print(f"Running test with {mode} mode")
    print(f"{'='*60}\n")
    
    if mode == "adaptive":
        cmd = [
            "python", "batch_test_runner.py",
            "--model", "qwen2.5-3b-instruct",
            "--count", "2",
            "--difficulty", "very_easy",
            "--adaptive",  # 使用自适应模式
            "--workers", str(workers),  # 初始worker数
            "--qps", str(qps),  # 初始QPS
            "--smart",
            "--silent"
        ]
    elif mode == "fixed":
        cmd = [
            "python", "batch_test_runner.py",
            "--model", "qwen2.5-3b-instruct",
            "--count", "2", 
            "--difficulty", "very_easy",
            "--concurrent",  # 使用固定并发
            "--workers", str(workers),
            "--qps", str(qps),
            "--smart",
            "--silent"
        ]
    else:
        cmd = [
            "python", "batch_test_runner.py",
            "--model", "qwen2.5-3b-instruct",
            "--count", "2",
            "--difficulty", "very_easy",
            "--smart",
            "--silent"
        ]
    
    print(f"Command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # 显示输出
    if result.stdout:
        print("\nOutput:")
        print(result.stdout)
    
    if result.stderr:
        print("\nErrors:")
        print(result.stderr)
    
    return result.returncode


def main():
    print("="*60)
    print("Adaptive Rate Limiting Test")
    print("="*60)
    
    print("\n### 测试场景说明 ###")
    print("1. 串行模式: 最慢但最稳定")
    print("2. 固定并发模式: 快但容易触发限流")
    print("3. 自适应模式: 自动调整速度避免限流")
    
    # 测试不同模式
    modes = [
        ("serial", None, None),
        ("fixed", 10, 10.0),
        ("adaptive", 10, 10.0)
    ]
    
    for mode, workers, qps in modes:
        try:
            if workers:
                returncode = run_test(mode, workers, qps)
            else:
                returncode = run_test(mode)
            
            if returncode == 0:
                print(f"✓ {mode} mode completed successfully")
            else:
                print(f"✗ {mode} mode failed with code {returncode}")
        except Exception as e:
            print(f"✗ {mode} mode failed with error: {e}")
    
    print("\n" + "="*60)
    print("测试完成！")
    print("\n### 使用建议 ###")
    print("1. 开始使用自适应模式: --adaptive")
    print("2. 设置保守的初始值: --workers 3 --qps 5")
    print("3. 系统会自动根据限流情况调整速度")
    print("4. 查看日志文件了解详细的调整过程")
    print("\n示例命令:")
    print("python batch_test_runner.py --model qwen2.5-3b-instruct --count 10 --adaptive --workers 3 --qps 5 --smart --silent")


if __name__ == "__main__":
    main()