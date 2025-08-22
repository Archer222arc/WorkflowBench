#!/usr/bin/env python3
"""
测试Parquet保存函数是否正确保存所有51个字段
"""

import sys
from pathlib import Path
from datetime import datetime
import pandas as pd

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from parquet_cumulative_manager import ParquetCumulativeManager
from cumulative_test_manager import TestRecord

def test_save_all_fields():
    """测试保存函数是否包含所有字段"""
    
    print("测试Parquet保存函数的字段完整性")
    print("="*60)
    
    # 创建管理器
    manager = ParquetCumulativeManager()
    
    # 添加一些测试记录来生成统计
    print("\n1. 添加测试记录...")
    for i in range(5):
        record = TestRecord(
            model='test-model',
            task_type='test_task',
            prompt_type='test_prompt',
            success=(i < 3),  # 3个成功，2个失败
            execution_time=5.0 + i,
            turns=10 + i,
            tool_calls=5 + i
        )
        # 手动添加额外属性
        record.difficulty = 'easy'
        record.tool_success_rate = 0.8
        record.partial_success = (i == 3)  # 1个部分成功
        # 添加错误类型
        if not record.success and not record.partial_success:
            record.error_type = ['timeout', 'tool_selection', 'sequence'][i % 3]
        # 添加辅助信息
        if i % 2 == 0:
            record.assisted = True
            record.assisted_turns = 2
        
        manager.add_test_result_with_classification(record)
    
    print("  ✅ 添加了5条测试记录")
    
    # 刷新缓冲区
    print("\n2. 刷新缓冲区到磁盘...")
    manager._flush_buffer()
    print("  ✅ 数据已刷新到Parquet")
    
    # 读取并验证
    print("\n3. 验证保存的字段...")
    parquet_file = Path('pilot_bench_parquet_data/test_results.parquet')
    
    if parquet_file.exists():
        df = pd.read_parquet(parquet_file)
        
        # 查找刚刚添加的记录
        test_records = df[(df['model'] == 'test-model') & 
                         (df['prompt_type'] == 'test_prompt')]
        
        if not test_records.empty:
            record = test_records.iloc[0]
            
            # 所有应该存在的字段
            expected_fields = [
                # 标识字段
                'model', 'prompt_type', 'tool_success_rate', 'difficulty', 'task_type',
                # 基本统计
                'total', 'success', 'full_success', 'partial_success',
                'successful', 'partial', 'failed',
                # 成功率
                'success_rate', 'full_success_rate', 'partial_success_rate', 
                'partial_rate', 'failure_rate', 'weighted_success_score',
                # 执行指标
                'avg_execution_time', 'avg_turns', 'avg_tool_calls', 'tool_coverage_rate',
                # 质量分数
                'avg_workflow_score', 'avg_phase2_score', 'avg_quality_score', 'avg_final_score',
                # 错误统计
                'total_errors', 'tool_call_format_errors', 'timeout_errors', 'dependency_errors',
                'parameter_config_errors', 'tool_selection_errors', 'sequence_order_errors',
                'max_turns_errors', 'other_errors',
                # 错误率
                'tool_selection_error_rate', 'parameter_error_rate', 'sequence_error_rate',
                'dependency_error_rate', 'timeout_error_rate', 'format_error_rate',
                'max_turns_error_rate', 'other_error_rate',
                # 辅助统计
                'assisted_failure', 'assisted_success', 'total_assisted_turns',
                'tests_with_assistance', 'avg_assisted_turns', 'assisted_success_rate',
                'assistance_rate',
                # 时间戳
                'last_updated'
            ]
            
            print(f"  总期望字段数: {len(expected_fields)}")
            print(f"  实际字段数: {len(df.columns)}")
            
            # 检查每个字段
            missing_fields = []
            for field in expected_fields:
                if field not in df.columns:
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"\n  ❌ 缺少 {len(missing_fields)} 个字段:")
                for field in missing_fields:
                    print(f"    - {field}")
            else:
                print("\n  ✅ 所有51个字段都已保存!")
                
                # 显示一些值来验证
                print("\n  验证一些字段的值:")
                print(f"    total: {record['total']}")
                print(f"    success: {record['success']}")
                print(f"    successful: {record['successful']} (应该等于success)")
                print(f"    partial: {record['partial']}")
                print(f"    failed: {record['failed']}")
                print(f"    success_rate: {record['success_rate']:.2%}")
                print(f"    partial_rate: {record['partial_rate']:.2%}")
                print(f"    assistance_rate: {record['assistance_rate']:.2%}")
        else:
            print("  ❌ 未找到测试记录")
    else:
        print("  ❌ Parquet文件不存在")
    
    # 清理测试数据
    print("\n4. 清理测试数据...")
    if parquet_file.exists():
        df = pd.read_parquet(parquet_file)
        # 移除测试记录
        df = df[df['model'] != 'test-model']
        df.to_parquet(parquet_file, index=False)
        print("  ✅ 已清理测试数据")
    
    print("\n测试完成!")

if __name__ == "__main__":
    test_save_all_fields()