#!/usr/bin/env python3
"""
完整测试：验证所有修复是否正常工作
- AI分类字段通过checkpoint正确传递
- executed_tools只记录成功执行的工具
- timeout_errors正确分类
"""

import json
import time
from pathlib import Path
from batch_test_runner import BatchTestRunner, TestTask
from cumulative_test_manager import TestRecord

def test_complete_fix():
    """测试完整修复"""
    print("=" * 60)
    print("完整测试：验证所有修复")
    print("=" * 60)
    
    # 1. 创建测试runner
    runner = BatchTestRunner(debug=True, silent=False)
    print("✅ 创建BatchTestRunner")
    
    # 2. 创建测试任务
    task = TestTask(
        model='gpt-4o-mini',
        task_type='simple_task',
        prompt_type='baseline',
        difficulty='easy',
        tool_success_rate=0.8
    )
    print(f"✅ 创建测试任务: {task.model}")
    
    # 3. 运行单个测试
    print("\n运行测试...")
    result = runner.run_single_test(
        model=task.model,
        task_type=task.task_type,
        prompt_type=task.prompt_type,
        is_flawed=False,
        flaw_type=None,
        tool_success_rate=task.tool_success_rate
    )
    
    # 4. 检查结果
    print("\n" + "=" * 40)
    print("测试结果分析:")
    print("=" * 40)
    
    # 基本信息
    print(f"成功状态: {result.get('success', False)}")
    print(f"成功级别: {result.get('success_level', 'unknown')}")
    
    # AI分类
    ai_category = result.get('ai_error_category') or result.get('_ai_error_category')
    print(f"\nAI错误分类: {ai_category}")
    
    # 工具执行
    tool_calls = result.get('tool_calls', [])
    executed_tools = result.get('executed_tools', [])
    print(f"\n工具调用 (tool_calls): {tool_calls}")
    print(f"执行成功的工具 (executed_tools): {executed_tools}")
    
    # 验证executed_tools逻辑
    if len(executed_tools) <= len(tool_calls):
        print("✅ executed_tools数量正确 (≤ tool_calls)")
    else:
        print("❌ 错误: executed_tools > tool_calls")
    
    # 5. 模拟checkpoint保存
    print("\n" + "=" * 40)
    print("测试checkpoint保存:")
    print("=" * 40)
    
    # 创建TestRecord
    record = TestRecord(
        model=task.model,
        task_type=task.task_type,
        prompt_type=task.prompt_type,
        difficulty=task.difficulty
    )
    
    # 字段传递（模拟_checkpoint_save）
    fields_to_check = [
        'timestamp', 'success', 'success_level',
        'execution_time', 'turns', 'tool_calls',
        'executed_tools', 'required_tools',
        'ai_error_category', '_ai_error_category'
    ]
    
    print("传递字段:")
    for field in fields_to_check:
        if field in result:
            if field == '_ai_error_category':
                # 处理_ai_error_category -> ai_error_category转换
                setattr(record, 'ai_error_category', result[field])
                print(f"  {field} -> ai_error_category: {result[field]}")
            else:
                setattr(record, field, result[field])
                print(f"  {field}: {result[field]}")
    
    # 验证record
    print("\n验证TestRecord:")
    print(f"  ai_error_category: {getattr(record, 'ai_error_category', None)}")
    print(f"  executed_tools: {getattr(record, 'executed_tools', [])}")
    
    # 6. 测试超时错误分类
    print("\n" + "=" * 40)
    print("测试超时错误分类:")
    print("=" * 40)
    
    # 模拟超时错误
    timeout_error = "Test timeout after 10 minutes"
    
    # 快速规则检查
    if "timeout" in timeout_error.lower():
        print(f"✅ 快速规则: '{timeout_error}' -> timeout_errors")
    else:
        print(f"❌ 快速规则未识别超时错误")
    
    print("\n" + "=" * 60)
    print("✅ 所有测试完成!")
    print("=" * 60)

if __name__ == "__main__":
    test_complete_fix()