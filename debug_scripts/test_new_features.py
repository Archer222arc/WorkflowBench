#!/usr/bin/env python3
"""
测试新功能的脚本
"""

import subprocess
import sys

def run_test(command, description):
    """运行测试命令"""
    print(f"\n{'='*60}")
    print(f"测试: {description}")
    print(f"命令: {command}")
    print('='*60)
    
    result = subprocess.run(command, shell=True, capture_output=False, text=True)
    return result.returncode == 0

def main():
    tests = [
        # 测试1: 测试特定prompt类型
        ("python batch_test_runner.py --model qwen2.5-3b-instruct --count 1 --prompt-types baseline --task-types simple_task --difficulty very_easy --concurrent --workers 5 --silent", 
         "测试单一prompt类型(baseline)和单一任务类型"),
        
        # 测试2: 测试多个prompt类型
        ("python batch_test_runner.py --model qwen2.5-3b-instruct --count 1 --prompt-types baseline optimal --task-types simple_task basic_task --difficulty very_easy --concurrent --workers 5 --silent",
         "测试多个prompt类型和任务类型"),
        
        # 测试3: 测试所有flawed类型
        ("python batch_test_runner.py --model qwen2.5-3b-instruct --count 1 --prompt-types flawed --task-types simple_task --difficulty very_easy --concurrent --workers 5 --silent",
         "测试所有flawed类型"),
        
        # 测试4: 测试特定flawed类型
        ("python batch_test_runner.py --model qwen2.5-3b-instruct --count 1 --prompt-types flawed_tool_misuse --task-types simple_task --difficulty very_easy --concurrent --workers 5 --silent",
         "测试特定flawed类型(tool_misuse)"),
        
        # 测试5: 测试all选项
        ("python batch_test_runner.py --model qwen2.5-3b-instruct --count 1 --prompt-types all --task-types all --difficulty very_easy --concurrent --workers 10 --silent",
         "测试all选项（所有prompt和任务类型）"),
    ]
    
    print("\n开始测试新功能...")
    
    passed = 0
    failed = 0
    
    for command, description in tests:
        if run_test(command, description):
            print("✅ 测试通过")
            passed += 1
        else:
            print("❌ 测试失败")
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"测试完成: {passed} 通过, {failed} 失败")
    print('='*60)
    
    # 查看统计
    print("\n查看累积统计...")
    subprocess.run("python view_enhanced_statistics.py --model qwen2.5-3b-instruct", shell=True)

if __name__ == "__main__":
    main()