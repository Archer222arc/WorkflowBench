#!/usr/bin/env python3
"""
最终验证测试：确认所有修复都正常工作
"""

import json
from pathlib import Path
from batch_test_runner import BatchTestRunner, TestTask
from cumulative_test_manager import TestRecord

def test_final_verification():
    """最终验证测试"""
    print("=" * 60)
    print("最终验证测试")
    print("=" * 60)
    
    # 创建测试runner
    runner = BatchTestRunner(debug=True, silent=False)
    print("✅ BatchTestRunner初始化")
    print(f"   AI分类器: {'启用' if runner.ai_classifier else '未启用'}")
    print(f"   数据库更新: {'启用' if runner.enable_database_updates else '未启用'}")
    
    # 测试不同成功率以触发不同结果
    test_configs = [
        (0.9, "高成功率测试"),
        (0.5, "中成功率测试"),
        (0.2, "低成功率测试")
    ]
    
    results_summary = []
    
    for tool_success_rate, desc in test_configs:
        print(f"\n{'='*40}")
        print(f"{desc} (tool_success_rate={tool_success_rate})")
        print("="*40)
        
        task = TestTask(
            model='gpt-4o-mini',
            task_type='simple_task',
            prompt_type='baseline',
            difficulty='easy',
            tool_success_rate=tool_success_rate
        )
        
        # 运行测试
        result = runner.run_single_test(
            model=task.model,
            task_type=task.task_type,
            prompt_type=task.prompt_type,
            is_flawed=False,
            flaw_type=None,
            tool_success_rate=task.tool_success_rate
        )
        
        # 收集结果
        success = result.get('success', False)
        success_level = result.get('success_level', 'unknown')
        ai_category = result.get('ai_error_category') or result.get('_ai_error_category')
        tool_calls = result.get('tool_calls', [])
        executed_tools = result.get('executed_tools', [])
        required_tools = result.get('required_tools', [])
        
        print(f"结果:")
        print(f"  成功: {success}")
        print(f"  成功级别: {success_level}")
        print(f"  AI错误分类: {ai_category}")
        print(f"  工具调用数: {len(tool_calls)}")
        print(f"  成功执行数: {len(executed_tools)}")
        print(f"  必需工具数: {len(required_tools)}")
        
        # 验证逻辑
        checks = []
        
        # 1. executed_tools应该≤tool_calls
        if len(executed_tools) <= len(tool_calls):
            checks.append("✅ executed_tools ≤ tool_calls")
        else:
            checks.append("❌ executed_tools > tool_calls")
        
        # 2. AI分类应该是标准类别名
        valid_categories = [
            'timeout_errors', 'tool_call_format_errors', 'max_turns_errors',
            'tool_selection_errors', 'parameter_config_errors', 
            'sequence_order_errors', 'dependency_errors', 'other_errors'
        ]
        
        if ai_category is None and success:
            checks.append("✅ 成功案例无需AI分类")
        elif ai_category in valid_categories:
            checks.append(f"✅ AI分类使用标准类别: {ai_category}")
        elif ai_category and len(ai_category) > 50:
            checks.append(f"❌ AI分类返回长文本而非标准类别")
        elif not success and not ai_category:
            checks.append("⚠️ 失败案例未进行AI分类")
        
        # 3. checkpoint字段传递
        record = TestRecord(
            model=task.model,
            task_type=task.task_type,
            prompt_type=task.prompt_type,
            difficulty=task.difficulty
        )
        
        # 模拟checkpoint保存
        critical_fields = ['ai_error_category', '_ai_error_category', 'executed_tools']
        fields_present = []
        for field in critical_fields:
            if field in result:
                fields_present.append(field)
                if field == '_ai_error_category':
                    setattr(record, 'ai_error_category', result[field])
                else:
                    setattr(record, field, result[field])
        
        if 'ai_error_category' in fields_present or '_ai_error_category' in fields_present:
            checks.append("✅ AI分类字段可传递")
        
        if 'executed_tools' in fields_present:
            checks.append("✅ executed_tools字段可传递")
        
        # 打印验证结果
        print("\n验证检查:")
        for check in checks:
            print(f"  {check}")
        
        # 汇总
        results_summary.append({
            'desc': desc,
            'success': success,
            'ai_category': ai_category,
            'checks_passed': sum(1 for c in checks if c.startswith('✅')),
            'total_checks': len(checks)
        })
    
    # 最终汇总
    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)
    
    for summary in results_summary:
        print(f"{summary['desc']}:")
        print(f"  成功: {summary['success']}")
        print(f"  AI分类: {summary['ai_category']}")
        print(f"  通过检查: {summary['checks_passed']}/{summary['total_checks']}")
    
    # 总体结论
    all_passed = all(s['checks_passed'] == s['total_checks'] for s in results_summary)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有测试通过！修复验证成功！")
    else:
        print("⚠️ 部分检查未通过，请查看详情")
    print("=" * 60)

if __name__ == "__main__":
    test_final_verification()