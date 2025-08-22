#!/usr/bin/env python3
"""
调试测试失败问题
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from batch_test_runner import BatchTestRunner

def debug_test():
    """调试单个测试"""
    print("\n开始调试测试...")
    print("测试参数:")
    print("  模型: qwen2.5-3b-instruct")
    print("  任务类型: simple_task")
    print("  提示类型: baseline")
    print("  缺陷: 否")
    print("  工具成功率: 0.8")
    
    # 创建运行器
    runner = BatchTestRunner(debug=True, silent=False)
    
    # 初始化
    runner._lazy_init()
    
    # 运行单个测试
    result = runner.run_single_test(
        model="qwen2.5-3b-instruct",
        task_type="simple_task", 
        prompt_type="baseline",
        is_flawed=False,
        flaw_type=None,
        timeout=30,
        tool_success_rate=0.8
    )
    
    print("\n测试结果:")
    print(f"成功: {result.get('success', False)}")
    print(f"成功级别: {result.get('success_level', 'None')}")
    print(f"错误: {result.get('error', 'None')}")
    print(f"执行时间: {result.get('execution_time', 0):.2f}秒")
    print(f"轮数: {result.get('turns', 0)}")
    print(f"工具调用: {len(result.get('tool_calls', []))}")
    print(f"Workflow Score: {result.get('workflow_score', 0):.3f}")
    print(f"Phase2 Score: {result.get('phase2_score', 0):.3f}")
    print(f"Quality Score: {result.get('quality_score', 0):.3f}")
    print(f"Final Score: {result.get('final_score', 0):.3f}")
    
    print("\n详细信息:")
    for key in ['task_type', 'prompt_type', 'is_flawed', 'flaw_type', 'tool_success_rate']:
        if key in result:
            print(f"  {key}: {result[key]}")
    
    # 显示所有键
    print("\n返回的所有键:")
    for key in sorted(result.keys()):
        if key not in ['tool_calls', 'error']:
            print(f"  {key}: {result[key]}")
    
    return result

if __name__ == "__main__":
    debug_test()