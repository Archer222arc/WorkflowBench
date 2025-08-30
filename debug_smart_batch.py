#!/usr/bin/env python3
"""
调试smart_batch_runner的错误脚本
用于捕获完整的traceback信息
"""

import os
import sys
import traceback

# 设置环境变量
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['USE_RESULT_COLLECTOR'] = 'true'
os.environ['STORAGE_FORMAT'] = 'json'
os.environ['USE_PARTIAL_LOADING'] = 'true'
os.environ['TASK_LOAD_COUNT'] = '5'
os.environ['SKIP_MODEL_LOADING'] = 'true'

try:
    # 导入smart_batch_runner模块
    from smart_batch_runner import run_batch_test_smart
    
    print("🔍 开始调试smart_batch_runner...")
    print("参数:")
    print("  model: qwen2.5-32b-instruct")
    print("  prompt_types: flawed_sequence_disorder") 
    print("  difficulty: easy")
    print("  num_instances: 5")
    print("  max_workers: 1")
    print()
    
    # 调用函数
    result = run_batch_test_smart(
        model="qwen2.5-32b-instruct",
        prompt_types="flawed_sequence_disorder",
        difficulty="easy", 
        task_types="all",
        num_instances=5,
        tool_success_rate=0.8,
        max_workers=1,
        adaptive=True
    )
    
    print(f"✅ 调试完成，结果: {result}")

except Exception as e:
    print(f"❌ 发生错误: {e}")
    print(f"错误类型: {type(e)}")
    print("\n📋 完整的traceback:")
    print("="*80)
    traceback.print_exc()
    print("="*80)
    
    # 额外的错误信息
    tb = traceback.extract_tb(e.__traceback__)
    print(f"\n🔍 错误发生在:")
    for frame in tb[-3:]:  # 显示最后3个调用栈
        print(f"  文件: {frame.filename}")
        print(f"  行号: {frame.lineno}")
        print(f"  函数: {frame.name}")
        print(f"  代码: {frame.line}")
        print()