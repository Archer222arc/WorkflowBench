#!/usr/bin/env python3
"""
完整验证存储流程：从测试到保存的所有51个字段
"""
import os
import sys
from pathlib import Path
import pandas as pd

# 强制使用Parquet模式
os.environ['STORAGE_FORMAT'] = 'parquet'

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# 导入必要的模块（模拟smart_batch_runner.py的逻辑）
storage_format = os.environ.get('STORAGE_FORMAT', 'json').lower()
print(f"存储格式: {storage_format}")

if storage_format == 'parquet':
    from parquet_cumulative_manager import ParquetCumulativeManager as EnhancedCumulativeManager
    print("✅ 使用ParquetCumulativeManager")
else:
    from enhanced_cumulative_manager import EnhancedCumulativeManager
    print("使用EnhancedCumulativeManager")

from cumulative_test_manager import TestRecord

def validate_full_flow():
    """验证完整的数据流"""
    
    print("\n" + "="*60)
    print("验证测试脚本的完整存储流程")
    print("="*60)
    
    # 1. 创建manager（模拟smart_batch_runner.py的_save_results_to_database）
    manager = EnhancedCumulativeManager()
    
    # 2. 创建测试记录（模拟实际测试）
    print("\n1. 创建测试记录...")
    records = []
    for i in range(10):
        record = TestRecord(
            model='validation-model',
            task_type='validation_task',
            prompt_type='validation_prompt',
            success=(i < 6),  # 60%成功率
            execution_time=5.0 + i,
            turns=10 + i,
            tool_calls=3 + i
        )
        # 添加额外属性
        record.difficulty = 'easy'
        record.tool_success_rate = 0.8
        record.partial_success = (i == 6)
        
        # 添加工具覆盖信息
        record.required_tools = ['tool1', 'tool2', 'tool3']
        record.executed_tools = ['tool1', 'tool2'] if i < 5 else ['tool1']
        
        # 添加错误信息
        if not record.success and not record.partial_success:
            record.error_type = ['timeout', 'tool_selection', 'sequence', 'parameter'][i % 4]
        
        # 添加辅助信息
        if i % 3 == 0:
            record.assisted = True
            record.assisted_turns = 2
        
        # 添加分数
        if i < 6:
            record.workflow_score = 0.8 + i * 0.02
            record.phase2_score = 0.75 + i * 0.02
            record.quality_score = 0.77 + i * 0.02
            record.final_score = 0.78 + i * 0.02
        
        records.append(record)
    
    print(f"  创建了 {len(records)} 条测试记录")
    
    # 3. 保存记录（模拟_save_results_to_database）
    print("\n2. 保存记录到manager...")
    for record in records:
        manager.add_test_result_with_classification(record)
    
    # 4. 刷新缓冲区
    print("\n3. 刷新缓冲区...")
    manager._flush_buffer()
    print("  ✅ 数据已刷新")
    
    # 5. 验证保存的数据
    print("\n4. 验证保存的数据...")
    parquet_file = Path('pilot_bench_parquet_data/test_results.parquet')
    
    if parquet_file.exists():
        df = pd.read_parquet(parquet_file)
        
        # 查找刚保存的记录
        test_records = df[(df['model'] == 'validation-model') & 
                         (df['prompt_type'] == 'validation_prompt')]
        
        if not test_records.empty:
            record = test_records.iloc[0]
            
            # 所有51个字段
            all_fields = [
                # 标识字段 (5)
                'model', 'prompt_type', 'tool_success_rate', 'difficulty', 'task_type',
                # 基本统计 (7)
                'total', 'success', 'full_success', 'partial_success',
                'successful', 'partial', 'failed',
                # 成功率 (6)
                'success_rate', 'full_success_rate', 'partial_success_rate', 
                'partial_rate', 'failure_rate', 'weighted_success_score',
                # 执行指标 (4)
                'avg_execution_time', 'avg_turns', 'avg_tool_calls', 'tool_coverage_rate',
                # 质量分数 (4)
                'avg_workflow_score', 'avg_phase2_score', 'avg_quality_score', 'avg_final_score',
                # 错误统计 (9)
                'total_errors', 'tool_call_format_errors', 'timeout_errors', 'dependency_errors',
                'parameter_config_errors', 'tool_selection_errors', 'sequence_order_errors',
                'max_turns_errors', 'other_errors',
                # 错误率 (8)
                'tool_selection_error_rate', 'parameter_error_rate', 'sequence_error_rate',
                'dependency_error_rate', 'timeout_error_rate', 'format_error_rate',
                'max_turns_error_rate', 'other_error_rate',
                # 辅助统计 (7)
                'assisted_failure', 'assisted_success', 'total_assisted_turns',
                'tests_with_assistance', 'avg_assisted_turns', 'assisted_success_rate',
                'assistance_rate',
                # 时间戳 (1)
                'last_updated'
            ]
            
            print(f"\n  字段完整性检查:")
            print(f"  期望字段数: {len(all_fields)}")
            print(f"  实际字段数: {len(df.columns)}")
            
            missing_fields = []
            for field in all_fields:
                if field not in df.columns:
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"\n  ❌ 缺少 {len(missing_fields)} 个字段:")
                for field in missing_fields:
                    print(f"    - {field}")
            else:
                print("\n  ✅ 所有51个字段都已保存!")
                
                # 验证值
                print("\n  数据值验证:")
                print(f"    total: {record['total']}")
                print(f"    success: {record['success']} | successful: {record['successful']}")
                print(f"    partial: {record['partial']} | partial_rate: {record['partial_rate']:.2%}")
                print(f"    failed: {record['failed']}")
                print(f"    success_rate: {record['success_rate']:.2%}")
                print(f"    tool_coverage_rate: {record['tool_coverage_rate']:.2%}")
                print(f"    avg_execution_time: {record['avg_execution_time']:.1f}")
                
                # 检查错误率
                if record['total_errors'] > 0:
                    print(f"\n    错误率字段:")
                    for err_field in ['tool_selection_error_rate', 'parameter_error_rate', 
                                     'sequence_error_rate', 'timeout_error_rate']:
                        if err_field in record:
                            val = record[err_field]
                            if pd.notna(val):
                                print(f"      {err_field}: {val:.2%}")
                
                # 检查辅助统计
                if record['assistance_rate'] > 0:
                    print(f"\n    辅助统计:")
                    print(f"      assistance_rate: {record['assistance_rate']:.2%}")
                    print(f"      assisted_success_rate: {record['assisted_success_rate']:.2%}")
                    print(f"      avg_assisted_turns: {record['avg_assisted_turns']:.1f}")
            
            # 清理测试数据
            print("\n5. 清理测试数据...")
            df = df[df['model'] != 'validation-model']
            df.to_parquet(parquet_file, index=False)
            print("  ✅ 已清理")
            
        else:
            print("  ❌ 未找到测试记录")
    else:
        print("  ❌ Parquet文件不存在")
    
    print("\n" + "="*60)
    print("验证完成!")
    print("="*60)

if __name__ == "__main__":
    validate_full_flow()