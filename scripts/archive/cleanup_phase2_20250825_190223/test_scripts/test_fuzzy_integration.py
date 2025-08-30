#!/usr/bin/env python3
"""
测试模糊匹配集成到Parquet系统
"""

import os
os.environ['STORAGE_FORMAT'] = 'parquet'

from parquet_cumulative_manager import ParquetCumulativeManager
from cumulative_test_manager import TestRecord

def test_fuzzy_matching():
    """测试各种错误类型的模糊匹配"""
    
    print("=" * 60)
    print("测试模糊错误匹配集成")
    print("=" * 60)
    
    # 创建管理器
    manager = ParquetCumulativeManager()
    
    # 测试用例：各种可能的AI分类结果变体
    test_cases = [
        # 标准名称
        ('timeout_errors', 'test-model-1', 'timeout_errors'),
        
        # 简化名称
        ('timeout', 'test-model-2', 'timeout_errors'),
        ('parameter', 'test-model-3', 'parameter_config_errors'),
        
        # 拼写错误
        ('timout error', 'test-model-4', 'timeout_errors'),
        ('paramter config', 'test-model-5', 'parameter_config_errors'),
        
        # 变体
        ('time-out', 'test-model-6', 'timeout_errors'),
        ('param_error', 'test-model-7', 'parameter_config_errors'),
        ('wrong_tool', 'test-model-8', 'tool_selection_errors'),
        
        # 描述性文本
        ('The model timed out after 10 minutes', 'test-model-9', 'timeout_errors'),
        ('Missing required parameter', 'test-model-10', 'parameter_config_errors'),
        ('Tool selection was incorrect', 'test-model-11', 'tool_selection_errors'),
    ]
    
    print("\n添加测试记录...")
    for ai_category, model_name, expected_error in test_cases:
        # 创建一个partial_success记录
        record = TestRecord(
            model=model_name,
            task_type='simple_task',
            prompt_type='optimal',
            difficulty='easy'
        )
        
        # 设置为partial_success并添加错误分类
        record.tool_success_rate = 0.8
        record.success = False
        record.partial_success = True
        record.success_level = 'partial_success'
        record.execution_time = 5.0
        record.turns = 10
        record.tool_calls = 5
        record.ai_error_category = ai_category  # 设置AI分类结果
        
        # 添加到管理器
        success = manager.add_test_result_with_classification(record)
        print(f"  {model_name}: AI分类='{ai_category}' -> 期望={expected_error}")
    
    # 刷新缓冲区
    print("\n刷新缓冲区...")
    manager._flush_buffer()
    
    # 验证结果
    print("\n验证Parquet数据...")
    import pandas as pd
    from pathlib import Path
    
    parquet_file = Path('pilot_bench_parquet_data/test_results.parquet')
    if parquet_file.exists():
        df = pd.read_parquet(parquet_file)
        
        print("\n错误分类结果:")
        print("-" * 40)
        
        for ai_category, model_name, expected_error in test_cases:
            model_df = df[df['model'] == model_name]
            if not model_df.empty:
                row = model_df.iloc[-1]
                
                # 检查期望的错误类型是否被正确计数
                error_count = row.get(expected_error, 0)
                status = "✓" if error_count > 0 else "✗"
                
                print(f"{status} {model_name}:")
                print(f"   输入: '{ai_category}'")
                print(f"   期望: {expected_error} = 1")
                print(f"   实际: {expected_error} = {error_count}")
                
                # 显示所有非零错误类型
                for error_type in ['timeout_errors', 'tool_selection_errors', 
                                  'parameter_config_errors', 'sequence_order_errors',
                                  'dependency_errors', 'tool_call_format_errors',
                                  'max_turns_errors', 'other_errors']:
                    if error_type in row and row[error_type] > 0:
                        if error_type != expected_error:
                            print(f"   ⚠️ {error_type} = {row[error_type]}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_fuzzy_matching()