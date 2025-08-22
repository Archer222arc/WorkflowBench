#!/usr/bin/env python3
"""
测试失败场景的AI分类
"""

import json
import time
from pathlib import Path
from batch_test_runner import BatchTestRunner, TestTask

def test_failure_classification():
    """测试失败场景的AI分类"""
    print("=" * 60)
    print("测试失败场景的AI分类")
    print("=" * 60)
    
    # 创建测试runner
    runner = BatchTestRunner(debug=True, silent=False)
    print("✅ 创建BatchTestRunner")
    
    # 创建测试任务 - 使用低成功率触发失败
    task = TestTask(
        model='gpt-4o-mini',
        task_type='simple_task',
        prompt_type='baseline',
        difficulty='easy',
        tool_success_rate=0.3  # 低成功率，容易失败
    )
    print(f"✅ 创建测试任务: {task.model}, tool_success_rate={task.tool_success_rate}")
    
    # 运行多个测试找到失败案例
    print("\n运行测试寻找失败案例...")
    
    for i in range(5):
        print(f"\n测试 {i+1}/5:")
        result = runner.run_single_test(
            model=task.model,
            task_type=task.task_type,
            prompt_type=task.prompt_type,
            is_flawed=False,
            flaw_type=None,
            tool_success_rate=task.tool_success_rate
        )
        
        # 检查结果
        success = result.get('success', False)
        success_level = result.get('success_level', 'unknown')
        ai_category = result.get('ai_error_category') or result.get('_ai_error_category')
        
        print(f"  成功: {success}")
        print(f"  成功级别: {success_level}")
        print(f"  AI错误分类: {ai_category}")
        
        # 如果失败，显示详细信息
        if not success or success_level in ['failure', 'partial_success']:
            print("\n  📌 发现失败/部分成功案例！")
            print(f"  工具调用: {result.get('tool_calls', [])}")
            print(f"  执行成功的工具: {result.get('executed_tools', [])}")
            print(f"  必需工具: {result.get('required_tools', [])}")
            
            # 验证executed_tools逻辑
            tool_calls = result.get('tool_calls', [])
            executed_tools = result.get('executed_tools', [])
            
            if len(executed_tools) < len(tool_calls):
                print(f"  ✅ 正确: executed_tools ({len(executed_tools)}) < tool_calls ({len(tool_calls)})")
            elif len(executed_tools) == len(tool_calls):
                print(f"  ✅ 正确: executed_tools ({len(executed_tools)}) = tool_calls ({len(tool_calls)})")
            else:
                print(f"  ❌ 错误: executed_tools ({len(executed_tools)}) > tool_calls ({len(tool_calls)})")
            
            # 如果有AI分类，显示详情
            if ai_category:
                print(f"\n  🔍 AI分类详情:")
                print(f"     类别: {ai_category}")
                
                # 检查分类是否合理
                if ai_category == 'timeout_errors' and 'timeout' in str(result.get('error_message', '')).lower():
                    print(f"     ✅ 正确分类为timeout_errors")
                elif ai_category == 'tool_selection_errors':
                    print(f"     ✅ 工具选择错误")
                elif ai_category == 'parameter_config_errors':
                    print(f"     ✅ 参数配置错误")
                elif ai_category == 'other_errors':
                    print(f"     ⚠️ 分类为other_errors，可能需要更细分")
                
    print("\n" + "=" * 60)
    print("✅ 测试完成!")
    print("=" * 60)

if __name__ == "__main__":
    test_failure_classification()