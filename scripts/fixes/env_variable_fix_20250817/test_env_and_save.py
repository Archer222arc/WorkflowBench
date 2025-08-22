#!/usr/bin/env python3
"""测试环境变量和数据保存问题"""

import os
import sys
import time
from datetime import datetime

print("=" * 60)
print("环境变量和数据保存测试")
print("=" * 60)

# 1. 检查环境变量
print("\n1. 环境变量检查:")
storage_format = os.environ.get('STORAGE_FORMAT', 'json')
print(f"   STORAGE_FORMAT = '{storage_format}'")
print(f"   Python = {sys.executable}")
print(f"   PID = {os.getpid()}")

# 2. 测试导入
print("\n2. 模块导入测试:")
try:
    if storage_format.lower() == 'parquet':
        print("   尝试导入ParquetCumulativeManager...")
        from parquet_cumulative_manager import ParquetCumulativeManager as Manager
        print("   ✅ 成功导入ParquetCumulativeManager")
    else:
        print("   尝试导入EnhancedCumulativeManager...")
        from enhanced_cumulative_manager import EnhancedCumulativeManager as Manager
        print("   ✅ 成功导入EnhancedCumulativeManager")
        
    manager = Manager()
    print(f"   Manager类型: {type(manager).__name__}")
    
except Exception as e:
    print(f"   ❌ 导入失败: {e}")
    sys.exit(1)

# 3. 测试数据保存
print("\n3. 数据保存测试:")
try:
    from cumulative_test_manager import TestRecord
    
    # 创建测试记录（注意：TestRecord可能不接受tool_success_rate参数）
    test_record = TestRecord(
        model='test-model-env',
        task_type='simple_task',
        prompt_type='flawed_sequence_disorder',  # 使用5.3的prompt类型
        difficulty='easy'
    )
    
    # 设置其他属性
    test_record.timestamp = datetime.now().isoformat()
    test_record.success = True
    test_record.execution_time = 5.0
    test_record.turns = 10
    test_record.tool_calls = 5
    test_record.is_flawed = True
    test_record.flaw_type = 'sequence_disorder'
    
    print(f"   创建测试记录: model={test_record.model}, prompt={test_record.prompt_type}")
    
    # 尝试添加到数据库
    result = manager.add_test_result_with_classification(test_record)
    print(f"   添加结果: {result}")
    
    # 如果是Parquet，尝试刷新缓冲区
    if storage_format.lower() == 'parquet' and hasattr(manager, '_flush_buffer'):
        print("   刷新Parquet缓冲区...")
        manager._flush_buffer()
        print("   ✅ 缓冲区已刷新")
        
    # 保存数据库
    if hasattr(manager, 'save_database'):
        print("   保存数据库...")
        manager.save_database()
        print("   ✅ 数据库已保存")
        
except Exception as e:
    print(f"   ❌ 数据保存失败: {e}")
    import traceback
    traceback.print_exc()

# 4. 检查数据文件
print("\n4. 数据文件检查:")
from pathlib import Path

if storage_format.lower() == 'parquet':
    # 检查Parquet文件
    parquet_file = Path('pilot_bench_parquet_data/test_results.parquet')
    if parquet_file.exists():
        mod_time = datetime.fromtimestamp(parquet_file.stat().st_mtime)
        print(f"   Parquet文件最后修改: {mod_time.strftime('%H:%M:%S')}")
        
        # 检查增量文件
        inc_dir = Path('pilot_bench_parquet_data/incremental')
        if inc_dir.exists():
            inc_files = list(inc_dir.glob('*.parquet'))
            print(f"   增量文件数: {len(inc_files)}")
else:
    # 检查JSON文件
    json_file = Path('pilot_bench_cumulative_results/master_database.json')
    if json_file.exists():
        mod_time = datetime.fromtimestamp(json_file.stat().st_mtime)
        print(f"   JSON文件最后修改: {mod_time.strftime('%H:%M:%S')}")
        
print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)