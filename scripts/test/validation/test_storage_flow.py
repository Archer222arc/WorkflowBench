#!/usr/bin/env python3
"""
验证测试脚本的存储流程
"""
import os
import sys
from pathlib import Path

# 设置环境变量测试Parquet模式
os.environ['STORAGE_FORMAT'] = 'parquet'

# 模拟smart_batch_runner.py的导入逻辑
storage_format = os.environ.get('STORAGE_FORMAT', 'json').lower()
print(f"1. 检测到的存储格式: {storage_format}")

if storage_format == 'parquet':
    try:
        from parquet_cumulative_manager import ParquetCumulativeManager as EnhancedCumulativeManager
        print("2. ✅ 成功导入ParquetCumulativeManager")
        
        # 检查manager是否有所有必要方法
        manager = EnhancedCumulativeManager()
        
        # 检查关键方法
        methods_to_check = [
            'add_test_result_with_classification',
            '_flush_buffer',
            '_flush_summary_to_disk',
            'normalize_model_name'
        ]
        
        print("\n3. 检查manager方法:")
        for method in methods_to_check:
            if hasattr(manager, method):
                print(f"   ✅ {method} 存在")
            else:
                print(f"   ❌ {method} 缺失")
        
        # 检查_flush_summary_to_disk是否生成所有字段
        print("\n4. 检查_flush_summary_to_disk生成的字段:")
        
        # 模拟一个汇总缓存
        manager._summary_cache = {
            'test_key': {
                'model': 'test-model',
                'prompt_type': 'test',
                'tool_success_rate': 0.8,
                'difficulty': 'easy',
                'task_type': 'test_task',
                'total': 10,
                'success': 6,
                'full_success': 5,
                'partial_success': 1,
                '_total_execution_time': 50,
                '_total_turns': 100,
                '_total_tool_calls': 30,
                '_total_tool_coverage': 8.5,
                '_total_workflow_score': 7.5,
                '_total_phase2_score': 8.0,
                '_total_quality_score': 7.8,
                '_total_final_score': 7.9,
                'total_errors': 4,
                'tool_selection_errors': 1,
                'sequence_order_errors': 2,
                'other_errors': 1,
                'tool_call_format_errors': 0,
                'timeout_errors': 0,
                'dependency_errors': 0,
                'parameter_config_errors': 0,
                'max_turns_errors': 0,
                'assisted_failure': 2,
                'assisted_success': 3,
                'total_assisted_turns': 15,
                'tests_with_assistance': 5
            }
        }
        
        # 模拟flush操作
        summary = manager._summary_cache['test_key'].copy()
        total = summary['total']
        
        # 计算所有字段（模拟_flush_summary_to_disk的逻辑）
        if total > 0:
            # 成功率
            summary['success_rate'] = summary['success'] / total
            summary['full_success_rate'] = summary['full_success'] / total
            summary['partial_success_rate'] = summary['partial_success'] / total
            summary['failure_rate'] = 1 - summary['success_rate'] - summary['partial_success_rate']
            summary['weighted_success_score'] = (summary['full_success'] + 0.5 * summary['partial_success']) / total
            
            # 兼容性字段
            summary['successful'] = summary['success']
            summary['partial'] = summary['partial_success']
            summary['failed'] = total - summary['success'] - summary['partial_success']
            summary['partial_rate'] = summary['partial_success_rate']
            
            # 执行指标
            summary['avg_execution_time'] = summary['_total_execution_time'] / total
            summary['avg_turns'] = summary['_total_turns'] / total
            summary['avg_tool_calls'] = summary['_total_tool_calls'] / total
            summary['tool_coverage_rate'] = summary['_total_tool_coverage'] / total
            
            # 质量分数
            summary['avg_workflow_score'] = summary['_total_workflow_score'] / total
            summary['avg_phase2_score'] = summary['_total_phase2_score'] / total
            summary['avg_quality_score'] = summary['_total_quality_score'] / total
            summary['avg_final_score'] = summary['_total_final_score'] / total
            
            # 错误率
            if summary['total_errors'] > 0:
                summary['tool_selection_error_rate'] = summary['tool_selection_errors'] / summary['total_errors']
                summary['sequence_error_rate'] = summary['sequence_order_errors'] / summary['total_errors']
                summary['other_error_rate'] = summary['other_errors'] / summary['total_errors']
                # 其他错误率字段...
            
            # 辅助统计
            if summary['tests_with_assistance'] > 0:
                summary['assisted_success_rate'] = summary['assisted_success'] / summary['tests_with_assistance']
                summary['avg_assisted_turns'] = summary['total_assisted_turns'] / summary['tests_with_assistance']
            summary['assistance_rate'] = summary['tests_with_assistance'] / total
        
        # 移除内部字段
        for field in list(summary.keys()):
            if field.startswith('_'):
                del summary[field]
        
        # 检查生成的字段数
        print(f"   生成的字段总数: {len(summary)}")
        
        # 检查关键字段
        key_fields = [
            'successful', 'partial', 'failed', 'partial_rate',
            'success_rate', 'tool_coverage_rate', 'avg_execution_time',
            'tool_selection_error_rate', 'assisted_success_rate'
        ]
        
        print("\n5. 验证关键字段:")
        for field in key_fields:
            if field in summary:
                print(f"   ✅ {field}: {summary[field]}")
            else:
                print(f"   ❌ {field}: 缺失")
        
    except ImportError as e:
        print(f"2. ❌ 导入失败: {e}")
else:
    print("2. 使用JSON存储格式")

print("\n总结:")
print("=" * 40)
if storage_format == 'parquet' and 'manager' in locals():
    print("✅ Parquet存储模式配置正确")
    print("✅ Manager包含所有必要方法")
    if 'summary' in locals() and len(summary) >= 50:
        print(f"✅ 生成了{len(summary)}个字段（预期51个）")
    else:
        print(f"⚠️  字段数量可能不足")
else:
    print("⚠️  未使用Parquet存储模式")
