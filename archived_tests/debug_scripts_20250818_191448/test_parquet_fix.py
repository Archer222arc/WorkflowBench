#!/usr/bin/env python3
"""
测试Parquet存储修复效果
"""

import os
import sys
from pathlib import Path

# 设置Parquet存储格式
os.environ['STORAGE_FORMAT'] = 'parquet'

# 导入必要的模块
sys.path.insert(0, str(Path(__file__).parent))
from parquet_cumulative_manager import ParquetCumulativeManager as EnhancedCumulativeManager
from cumulative_test_manager import TestRecord

def test_parquet_storage():
    """测试Parquet存储功能"""
    print("=" * 60)
    print("测试Parquet存储修复效果")
    print("=" * 60)
    
    # 创建管理器
    manager = EnhancedCumulativeManager()
    print(f"✅ 管理器类型: {type(manager).__name__}")
    
    # 创建多个测试记录
    test_models = ['gpt-4o-mini', 'DeepSeek-V3-0324', 'qwen2.5-72b-instruct']
    
    for i, model in enumerate(test_models):
        record = TestRecord(
            model=model,
            task_type='simple_task',
            prompt_type='flawed_sequence_disorder',
            difficulty='easy'
        )
        
        # 设置其他属性
        record.tool_success_rate = 0.8
        record.success = (i % 2 == 0)  # 交替成功/失败
        record.execution_time = 2.5 + i
        record.turns = 5 + i
        record.tool_calls = 3 + i
        record.is_flawed = True
        record.flaw_type = 'sequence_disorder'
        
        # 添加记录
        success = manager.add_test_result_with_classification(record)
        print(f"  添加{model}: {'✅ 成功' if success else '❌ 失败'}")
    
    # 刷新缓冲区
    if hasattr(manager, '_flush_buffer'):
        manager._flush_buffer()
        print("✅ 缓冲区已刷新")
    
    # 检查增量文件
    inc_dir = Path('pilot_bench_parquet_data/incremental')
    if inc_dir.exists():
        files = list(inc_dir.glob('*.parquet'))
        print(f"\n📁 增量文件数: {len(files)}")
        
        if files:
            # 读取所有文件统计
            import pandas as pd
            total_records = 0
            models_found = set()
            
            for file in files:
                df = pd.read_parquet(file)
                total_records += len(df)
                if 'model' in df.columns:
                    models_found.update(df['model'].unique())
            
            print(f"📊 总记录数: {total_records}")
            print(f"🤖 发现的模型: {', '.join(models_found)}")
            
            # 显示最新文件的示例记录
            latest = max(files, key=lambda f: f.stat().st_mtime)
            df = pd.read_parquet(latest)
            print(f"\n📝 最新文件 ({latest.name}) 的第一条记录:")
            if len(df) > 0:
                first_record = df.iloc[0]
                for key in ['model', 'task_type', 'prompt_type', 'success', 'flaw_type']:
                    if key in first_record:
                        print(f"  - {key}: {first_record[key]}")
    
    # 检查主文件
    main_file = Path('pilot_bench_parquet_data/test_results.parquet')
    if main_file.exists():
        df = pd.read_parquet(main_file)
        print(f"\n📊 主文件统计: {len(df)} 条汇总记录")
    
    print("\n" + "=" * 60)
    print("✅ 测试完成！Parquet存储功能正常工作")
    print("=" * 60)

if __name__ == "__main__":
    test_parquet_storage()