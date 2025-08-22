#!/usr/bin/env python3
"""
测试Parquet统计修复效果
验证Parquet现在使用与enhanced相同的统计方法
"""

import os
import sys
from pathlib import Path

# 设置Parquet存储格式
os.environ['STORAGE_FORMAT'] = 'parquet'

def test_parquet_statistics():
    """测试Parquet统计计算是否与enhanced一致"""
    
    print("=" * 60)
    print("测试Parquet统计修复效果")
    print("=" * 60)
    
    # 导入管理器
    from parquet_cumulative_manager import ParquetCumulativeManager
    from cumulative_test_manager import TestRecord
    
    # 创建管理器
    manager = ParquetCumulativeManager()
    print("✅ 创建ParquetCumulativeManager成功")
    
    # 创建测试记录
    test_records = []
    
    # 1. 完全成功的记录
    record1 = TestRecord(
        model='test-model-stats',
        task_type='simple_task',
        prompt_type='baseline',
        difficulty='easy'
    )
    record1.tool_success_rate = 0.8
    record1.success = True
    record1.success_level = 'full_success'
    record1.execution_time = 2.5
    record1.turns = 5
    record1.tool_calls = 3
    record1.required_tools = ['tool1', 'tool2', 'tool3']
    record1.executed_tools = ['tool1', 'tool2', 'tool3']
    record1.tool_coverage_rate = 1.0
    record1.workflow_score = 0.9
    record1.phase2_score = 0.85
    record1.quality_score = 0.88
    record1.final_score = 0.87
    record1.error_message = None
    test_records.append(record1)
    
    # 2. 部分成功的记录（有format error）
    record2 = TestRecord(
        model='test-model-stats',
        task_type='simple_task',
        prompt_type='baseline',
        difficulty='easy'
    )
    record2.tool_success_rate = 0.8
    record2.success = True
    record2.success_level = 'partial_success'
    record2.partial_success = True
    record2.execution_time = 4.0
    record2.turns = 8
    record2.tool_calls = 2
    record2.required_tools = ['tool1', 'tool2', 'tool3']
    record2.executed_tools = ['tool1', 'tool2']
    record2.tool_coverage_rate = 0.67
    record2.workflow_score = 0.6
    record2.phase2_score = 0.5
    record2.quality_score = 0.55
    record2.final_score = 0.55
    record2.format_error_count = 2  # 有辅助
    record2.error_message = "Format errors detected"
    record2.ai_error_category = 'format'  # AI分类结果
    test_records.append(record2)
    
    # 3. 失败的记录（timeout）
    record3 = TestRecord(
        model='test-model-stats',
        task_type='simple_task',
        prompt_type='baseline',
        difficulty='easy'
    )
    record3.tool_success_rate = 0.8
    record3.success = False
    record3.partial_success = False  # 明确设置为False
    record3.success_level = 'failure'  # 明确设置失败级别
    record3.execution_time = 10.0
    record3.turns = 10
    record3.tool_calls = 1
    record3.required_tools = ['tool1', 'tool2', 'tool3']
    record3.executed_tools = ['tool1']
    record3.tool_coverage_rate = 0.33
    record3.workflow_score = 0.2
    record3.phase2_score = 0.1
    record3.quality_score = 0.15
    record3.final_score = 0.15
    record3.error_message = "Test timeout after 10 minutes"
    record3.ai_error_category = 'timeout'
    test_records.append(record3)
    
    # 添加所有测试记录
    print("\n添加测试记录...")
    for i, record in enumerate(test_records, 1):
        success = manager.add_test_result_with_classification(record)
        print(f"  记录 {i}: {'✅' if success else '❌'}")
    
    # 刷新缓冲区
    manager._flush_buffer()
    print("\n✅ 刷新缓冲区成功")
    
    # 检查统计结果
    print("\n验证统计计算...")
    
    # 从缓存或数据库获取统计
    from parquet_data_manager import ParquetDataManager
    pdm = ParquetDataManager()
    df = pdm.query_model_stats(model_name='test-model-stats')
    
    if not df.empty:
        print(f"\n找到 {len(df)} 条汇总记录")
        
        # 检查最新的汇总
        latest = df.iloc[-1]
        
        # 验证关键统计
        checks = []
        
        # 1. 成功统计
        total = latest.get('total', 0)
        success = latest.get('success', 0)
        full_success = latest.get('full_success', 0)
        partial_success = latest.get('partial_success', 0)
        failed = latest.get('failed', 0)
        
        checks.append(("总数", total == 3, f"{total} (期望: 3)"))
        checks.append(("成功数", success == 2, f"{success} (期望: 2)"))
        checks.append(("完全成功", full_success == 1, f"{full_success} (期望: 1)"))
        checks.append(("部分成功", partial_success == 1, f"{partial_success} (期望: 1)"))
        checks.append(("失败数", failed == 1, f"{failed} (期望: 1)"))
        
        # 2. 成功率
        success_rate = latest.get('success_rate', 0)
        weighted_score = latest.get('weighted_success_score', 0)
        
        checks.append(("成功率", abs(success_rate - 0.667) < 0.01, f"{success_rate:.3f} (期望: 0.667)"))
        checks.append(("加权成功分", abs(weighted_score - 0.5) < 0.01, f"{weighted_score:.3f} (期望: 0.5)"))
        
        # 3. 执行统计（平均值）
        avg_time = latest.get('avg_execution_time', 0)
        avg_turns = latest.get('avg_turns', 0)
        avg_calls = latest.get('avg_tool_calls', 0)
        tool_coverage = latest.get('tool_coverage_rate', 0)
        
        checks.append(("平均执行时间", abs(avg_time - 5.5) < 0.1, f"{avg_time:.1f} (期望: 5.5)"))
        checks.append(("平均轮数", abs(avg_turns - 7.67) < 0.1, f"{avg_turns:.1f} (期望: 7.67)"))
        checks.append(("平均工具调用", abs(avg_calls - 2.0) < 0.1, f"{avg_calls:.1f} (期望: 2.0)"))
        checks.append(("工具覆盖率", abs(tool_coverage - 0.667) < 0.01, f"{tool_coverage:.3f} (期望: 0.667)"))
        
        # 4. 质量分数
        avg_workflow = latest.get('avg_workflow_score', 0)
        avg_phase2 = latest.get('avg_phase2_score', 0)
        avg_quality = latest.get('avg_quality_score', 0)
        avg_final = latest.get('avg_final_score', 0)
        
        checks.append(("workflow分数", abs(avg_workflow - 0.567) < 0.01, f"{avg_workflow:.3f} (期望: 0.567)"))
        checks.append(("phase2分数", abs(avg_phase2 - 0.483) < 0.01, f"{avg_phase2:.3f} (期望: 0.483)"))
        checks.append(("quality分数", abs(avg_quality - 0.527) < 0.01, f"{avg_quality:.3f} (期望: 0.527)"))
        checks.append(("final分数", abs(avg_final - 0.523) < 0.01, f"{avg_final:.3f} (期望: 0.523)"))
        
        # 5. 错误统计
        total_errors = latest.get('total_errors', 0)
        format_errors = latest.get('tool_call_format_errors', 0)
        timeout_errors = latest.get('timeout_errors', 0)
        
        checks.append(("总错误数", total_errors == 2, f"{total_errors} (期望: 2)"))
        checks.append(("格式错误", format_errors == 1, f"{format_errors} (期望: 1)"))
        checks.append(("超时错误", timeout_errors == 1, f"{timeout_errors} (期望: 1)"))
        
        # 6. 错误率（基于总错误）
        format_rate = latest.get('format_error_rate', 0)
        timeout_rate = latest.get('timeout_error_rate', 0)
        
        checks.append(("格式错误率", abs(format_rate - 0.5) < 0.01, f"{format_rate:.3f} (期望: 0.5)"))
        checks.append(("超时错误率", abs(timeout_rate - 0.5) < 0.01, f"{timeout_rate:.3f} (期望: 0.5)"))
        
        # 7. 辅助统计
        tests_with_assist = latest.get('tests_with_assistance', 0)
        assisted_success = latest.get('assisted_success', 0)
        assisted_turns = latest.get('total_assisted_turns', 0)
        assistance_rate = latest.get('assistance_rate', 0)
        
        checks.append(("辅助测试数", tests_with_assist == 1, f"{tests_with_assist} (期望: 1)"))
        checks.append(("辅助成功数", assisted_success == 1, f"{assisted_success} (期望: 1)"))
        checks.append(("辅助轮数", assisted_turns == 2, f"{assisted_turns} (期望: 2)"))
        checks.append(("辅助率", abs(assistance_rate - 0.333) < 0.01, f"{assistance_rate:.3f} (期望: 0.333)"))
        
        # 显示测试结果
        print("\n测试结果:")
        print("-" * 50)
        
        all_passed = True
        for check_name, passed, value in checks:
            status = "✅" if passed else "❌"
            print(f"  {status} {check_name}: {value}")
            if not passed:
                all_passed = False
        
        print("-" * 50)
        if all_passed:
            print("\n🎉 所有测试通过！Parquet统计计算与enhanced完全一致")
        else:
            print("\n⚠️  部分测试失败，请检查统计计算逻辑")
        
        # 显示完整的汇总数据（用于调试）
        print("\n完整汇总数据（调试用）:")
        important_fields = [
            'total', 'success', 'full_success', 'partial_success', 'failed',
            'success_rate', 'weighted_success_score',
            'avg_execution_time', 'avg_turns', 'avg_tool_calls', 'tool_coverage_rate',
            'avg_workflow_score', 'avg_phase2_score', 'avg_quality_score', 'avg_final_score',
            'total_errors', 'tool_call_format_errors', 'timeout_errors',
            'format_error_rate', 'timeout_error_rate',
            'tests_with_assistance', 'assisted_success', 'total_assisted_turns', 'assistance_rate'
        ]
        
        for field in important_fields:
            if field in latest:
                value = latest[field]
                if isinstance(value, float):
                    print(f"  {field}: {value:.3f}")
                else:
                    print(f"  {field}: {value}")
        
        return all_passed
    else:
        print("❌ 未找到测试数据")
        return False

if __name__ == "__main__":
    success = test_parquet_statistics()
    sys.exit(0 if success else 1)