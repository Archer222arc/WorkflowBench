#!/usr/bin/env python3
"""
将5.5提示敏感性测试结果转换为标准格式
基于convert_5_4_to_standard_format.py修改
"""

import pandas as pd
from datetime import datetime

def convert_5_5_to_standard():
    """转换5.5数据到标准格式"""
    print("🔄 转换5.5提示敏感性测试数据到标准格式...")
    
    # 读取原始数据
    df = pd.read_csv('5_5_prompt_sensitivity_results.csv')
    
    # 转换为标准格式
    standard_data = []
    
    for _, row in df.iterrows():
        # 计算完全成功数和部分成功数
        full_success = max(0, row['successful'] - row['partial'])
        
        record = {
            'experiment': '5.5',
            'experiment_name': '提示敏感性测试',
            'model': row['model'],
            'prompt_type': row['prompt_type'],
            'tool_success_rate': row['tool_success_rate'],
            'difficulty': row['difficulty'],
            'total_tests': row['total_tests'],
            'effective_total': row['effective_total'],
            'full_success': full_success,
            'partial_success': row['partial'],
            'total_success': row['successful'],
            'failed': row['failed'],
            'timeout_failures': row['timeout_failures'],
            'full_success_rate': full_success / row['effective_total'] if row['effective_total'] > 0 else 0,
            'partial_success_rate': row['partial'] / row['effective_total'] if row['effective_total'] > 0 else 0,
            'total_success_rate': row['successful'] / row['effective_total'] if row['effective_total'] > 0 else 0,
            'failure_rate': (row['failed'] - row['timeout_failures']) / row['effective_total'] if row['effective_total'] > 0 else 0,
            'avg_execution_time': row['avg_execution_time'],
            'timeout_errors': row['timeout_errors'],
            'tool_selection_errors': row['tool_selection_errors'],
            'parameter_errors': row['parameter_errors'],
            'execution_errors': row['execution_errors'],
            'other_errors': row['other_errors'],
            'test_date': '2025-08-31',
            'notes': f"提示类型: {row['prompt_type']}"
        }
        
        standard_data.append(record)
    
    # 创建DataFrame并保存
    standard_df = pd.DataFrame(standard_data)
    
    # 保存标准格式CSV
    output_file = '5_5_prompt_sensitivity_standard_format.csv'
    standard_df.to_csv(output_file, index=False)
    
    print(f"✅ 标准格式数据已保存: {output_file}")
    print(f"📊 转换了 {len(standard_df)} 条记录")
    
    # 显示统计信息
    print("\n📈 数据统计:")
    print(f"  实验: 5.5 提示敏感性测试")
    print(f"  模型数: {len(standard_df['model'].unique())}")
    print(f"  提示类型: {list(standard_df['prompt_type'].unique())}")
    print(f"  总测试数: {standard_df['total_tests'].sum()}")
    print(f"  有效测试数: {standard_df['effective_total'].sum()}")
    print(f"  平均成功率: {standard_df['total_success_rate'].mean()*100:.1f}%")
    
    return output_file

def main():
    """主函数"""
    try:
        convert_5_5_to_standard()
        print("\n🎉 5.5数据标准化转换完成！")
    except Exception as e:
        print(f"❌转换过程出错: {e}")
        raise

if __name__ == "__main__":
    main()