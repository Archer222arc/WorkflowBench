#!/usr/bin/env python3
"""
测试存储格式是否正确工作
"""

import os
import sys
from pathlib import Path

print("=" * 60)
print("存储格式测试")
print("=" * 60)

# 1. 检查环境变量
storage_format = os.environ.get('STORAGE_FORMAT', 'json').lower()
print(f"1. 环境变量 STORAGE_FORMAT = {storage_format}")

# 2. 尝试导入相应的管理器
sys.path.insert(0, str(Path(__file__).parent))

if storage_format == 'parquet':
    try:
        from parquet_cumulative_manager import ParquetCumulativeManager as Manager
        print("2. ✅ 成功导入ParquetCumulativeManager")
    except ImportError as e:
        print(f"2. ❌ 导入ParquetCumulativeManager失败: {e}")
        from enhanced_cumulative_manager import EnhancedCumulativeManager as Manager
        print("   回退到EnhancedCumulativeManager")
else:
    from enhanced_cumulative_manager import EnhancedCumulativeManager as Manager
    print("2. ✅ 使用EnhancedCumulativeManager (JSON)")

# 3. 创建manager实例
from cumulative_test_manager import TestRecord

manager = Manager()
print(f"3. Manager类型: {type(manager).__name__}")

# 4. 创建测试记录
record = TestRecord(
    model='test-model',
    task_type='simple_task',
    prompt_type='baseline',
    difficulty='easy'
)
record.tool_success_rate = 0.8
record.success = True
record.execution_time = 2.5
record.turns = 5
record.tool_calls = 3

# 5. 添加记录
success = manager.add_test_result_with_classification(record)
print(f"4. 添加记录: {'✅ 成功' if success else '❌ 失败'}")

# 6. 检查文件
if storage_format == 'parquet':
    # 检查Parquet文件
    parquet_dir = Path('pilot_bench_parquet_data/incremental')
    if parquet_dir.exists():
        files = list(parquet_dir.glob('*.parquet'))
        print(f"5. Parquet增量文件: {len(files)}个")
        if files:
            latest = max(files, key=lambda f: f.stat().st_mtime)
            print(f"   最新文件: {latest.name}")
    else:
        print(f"5. ❌ Parquet目录不存在: {parquet_dir}")
        
    # 强制刷新
    if hasattr(manager, '_flush_buffer'):
        manager._flush_buffer()
        print("6. 已强制刷新缓冲区")
        
        # 再次检查
        files = list(parquet_dir.glob('*.parquet'))
        print(f"7. 刷新后Parquet文件: {len(files)}个")
else:
    # 检查JSON文件
    json_path = Path('pilot_bench_cumulative_results/master_database.json')
    if json_path.exists():
        import json
        with open(json_path, 'r') as f:
            db = json.load(f)
        test_model_data = db['models'].get('test-model', {})
        if test_model_data:
            total = test_model_data.get('overall_stats', {}).get('total_tests', 0)
            print(f"5. JSON数据库中test-model: {total}个测试")
        else:
            print(f"5. JSON数据库中没有test-model")
    else:
        print(f"5. ❌ JSON文件不存在")

print("=" * 60)
print("测试完成")
print("=" * 60)