#!/usr/bin/env python3
"""
测试错误计数修复效果
验证所有非full_success的测试都会被正确计入错误
"""

import os
os.environ['STORAGE_FORMAT'] = 'parquet'

from parquet_cumulative_manager import ParquetCumulativeManager
from cumulative_test_manager import TestRecord

def test_error_counting():
    """测试错误计数是否正确"""
    
    print("=" * 60)
    print("测试错误计数修复")
    print("=" * 60)
    
    # 创建管理器
    manager = ParquetCumulativeManager()
    
    # 测试场景1：失败的测试（没有error_message）
    print("\n场景1：失败的测试（无error_message）")
    record1 = TestRecord(
        model='test-error-counting',
        task_type='api_integration',
        prompt_type='optimal',
        difficulty='easy'
    )
    record1.tool_success_rate = 0.8
    record1.success = False
    record1.partial_success = False
    record1.success_level = 'failure'
    record1.execution_time = 10.0
    record1.turns = 10
    record1.tool_calls = 0  # 没有工具调用
    record1.executed_tools = []
    # 注意：没有error_message
    
    success = manager.add_test_result_with_classification(record1)
    print(f"  添加记录: {'✅' if success else '❌'}")
    
    # 测试场景2：部分成功（有辅助）
    print("\n场景2：部分成功（有辅助，应计入错误）")
    record2 = TestRecord(
        model='test-error-counting',
        task_type='api_integration',
        prompt_type='optimal',
        difficulty='easy'
    )
    record2.tool_success_rate = 0.8
    record2.success = True
    record2.partial_success = True
    record2.success_level = 'partial_success'
    record2.execution_time = 10.0
    record2.turns = 10
    record2.tool_calls = 1
    record2.format_error_count = 3  # 有辅助
    record2.error_message = None  # 没有明确的错误消息
    
    success = manager.add_test_result_with_classification(record2)
    print(f"  添加记录: {'✅' if success else '❌'}")
    
    # 测试场景3：完全成功（不应计入错误）
    print("\n场景3：完全成功（不应计入错误）")
    record3 = TestRecord(
        model='test-error-counting',
        task_type='api_integration',
        prompt_type='optimal',
        difficulty='easy'
    )
    record3.tool_success_rate = 0.8
    record3.success = True
    record3.partial_success = False
    record3.success_level = 'full_success'
    record3.execution_time = 5.0
    record3.turns = 5
    record3.tool_calls = 3
    
    success = manager.add_test_result_with_classification(record3)
    print(f"  添加记录: {'✅' if success else '❌'}")
    
    # 刷新缓冲区
    manager._flush_buffer()
    print("\n✅ 刷新缓冲区成功")
    
    # 验证结果
    print("\n验证统计结果...")
    
    # 查询统计
    from parquet_data_manager import ParquetDataManager
    pdm = ParquetDataManager()
    df = pdm.query_model_stats(model_name='test-error-counting')
    
    if not df.empty:
        latest = df.iloc[-1]
        
        # 检查关键指标
        total = latest.get('total', 0)
        success = latest.get('success', 0)
        full_success = latest.get('full_success', 0)
        partial_success = latest.get('partial_success', 0)
        failed = latest.get('failed', 0)
        total_errors = latest.get('total_errors', 0)
        format_errors = latest.get('tool_call_format_errors', 0)
        other_errors = latest.get('other_errors', 0)
        tests_with_assistance = latest.get('tests_with_assistance', 0)
        assisted_success = latest.get('assisted_success', 0)
        assisted_failure = latest.get('assisted_failure', 0)
        
        print(f"\n统计结果:")
        print(f"  总测试数: {total} (期望: 3)")
        print(f"  成功数: {success} (期望: 2)")
        print(f"  完全成功: {full_success} (期望: 1)")
        print(f"  部分成功: {partial_success} (期望: 1)")
        print(f"  失败数: {failed} (期望: 1)")
        print(f"  总错误数: {total_errors} (期望: 2) ← 关键指标")
        print(f"  格式错误: {format_errors} (期望: 1)")
        print(f"  其他错误: {other_errors} (期望: 1)")
        print(f"  有辅助的测试: {tests_with_assistance} (期望: 1)")
        print(f"  辅助成功: {assisted_success} (期望: 1)")
        print(f"  辅助失败: {assisted_failure} (期望: 0)")
        
        # 验证关键点
        checks = []
        checks.append(("总数正确", total == 3))
        checks.append(("成功数正确", success == 2))
        checks.append(("失败数正确", failed == 1))
        checks.append(("总错误数正确", total_errors == 2))  # 最重要！
        checks.append(("格式错误正确", format_errors == 1))
        checks.append(("其他错误正确", other_errors == 1))
        checks.append(("辅助统计正确", tests_with_assistance == 1))
        
        print("\n验证结果:")
        all_passed = True
        for check_name, passed in checks:
            status = "✅" if passed else "❌"
            print(f"  {status} {check_name}")
            if not passed:
                all_passed = False
        
        if all_passed:
            print("\n🎉 所有测试通过！错误计数逻辑已修复")
            print("   - 失败的测试即使没有error_message也会计入错误")
            print("   - 部分成功的测试也会计入错误")
            print("   - 只有完全成功的测试不计入错误")
        else:
            print("\n⚠️  部分测试失败，请检查修复")
        
        # 显示完整数据（用于调试）
        if not all_passed:
            print("\n完整数据（调试用）:")
            important_fields = [
                'total', 'success', 'full_success', 'partial_success', 'failed',
                'total_errors', 'tool_call_format_errors', 'timeout_errors',
                'parameter_config_errors', 'tool_selection_errors', 'sequence_order_errors',
                'max_turns_errors', 'other_errors',
                'tests_with_assistance', 'assisted_success', 'assisted_failure'
            ]
            for field in important_fields:
                if field in latest:
                    print(f"  {field}: {latest[field]}")
        
        return all_passed
    else:
        print("❌ 未找到测试数据")
        return False

if __name__ == "__main__":
    import sys
    success = test_error_counting()
    sys.exit(0 if success else 1)