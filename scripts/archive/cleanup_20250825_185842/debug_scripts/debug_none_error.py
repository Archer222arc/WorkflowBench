#!/usr/bin/env python
"""
诊断NoneType比较错误的脚本
添加详细的traceback信息
"""
import traceback
import sys
import os

# 设置环境变量
os.environ['STORAGE_FORMAT'] = 'json'
os.environ['PYTHONFAULTHANDLER'] = '1'
os.environ['PYTHONUNBUFFERED'] = '1'
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

try:
    from smart_batch_runner import run_batch_test_smart
    
    print("开始诊断测试...")
    
    # 运行测试
    success = run_batch_test_smart(
        model="qwen2.5-7b-instruct",
        deployment="qwen-key0",
        prompt_types="optimal",
        difficulty="easy",
        task_types="simple_task",
        num_instances=1,
        adaptive=False,  # 使用非自适应模式
        tool_success_rate=0.8,
        batch_commit=True,
        checkpoint_interval=5,
        max_workers=2,
        qps=10,
        ai_classification=True
    )
    
    print(f"测试结果: {'成功' if success else '失败'}")
    
except Exception as e:
    print(f"❌ 捕获异常: {e}")
    print(f"异常类型: {type(e).__name__}")
    print("\n🔍 详细traceback:")
    traceback.print_exc()
    
    # 额外的错误信息
    if "'>' not supported between instances of 'NoneType' and 'int'" in str(e):
        print("\n🎯 确认这是NoneType比较错误！")
        print("正在分析调用栈...")
        
        # 获取traceback信息
        tb = traceback.format_exception(type(e), e, e.__traceback__)
        for i, line in enumerate(tb):
            if "batch_test_runner.py" in line and ">=" in line:
                print(f"🔍 可能的错误位置 {i}: {line.strip()}")
    
    sys.exit(1)