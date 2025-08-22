import os
import sys

# 设置环境变量
os.environ['STORAGE_FORMAT'] = 'parquet'

# 导入smart_batch_runner的逻辑
storage_format = os.environ.get('STORAGE_FORMAT', 'json').lower()
print(f"Storage format: {storage_format}")

if storage_format == 'parquet':
    try:
        from parquet_cumulative_manager import ParquetCumulativeManager as EnhancedCumulativeManager
        print("✅ Using ParquetCumulativeManager")
    except ImportError as e:
        print(f"❌ Failed to import ParquetCumulativeManager: {e}")
        from enhanced_cumulative_manager import EnhancedCumulativeManager
        print("⚠️ Falling back to JSON")
else:
    from enhanced_cumulative_manager import EnhancedCumulativeManager
    print("Using JSON format")

# 创建实例测试
manager = EnhancedCumulativeManager()
print(f"Manager type: {type(manager).__name__}")
print(f"Has _flush_buffer: {hasattr(manager, '_flush_buffer')}")

# 测试添加数据
from cumulative_test_manager import TestRecord
record = TestRecord(
    model='test-model',
    task_type='simple_task',
    prompt_type='baseline',
    difficulty='easy',
    tool_success_rate=0.8,
    success=True,
    execution_time=1.0,
    turns=5,
    tool_calls=3
)

result = manager.add_test_result_with_classification(record)
print(f"Add result: {result}")

# 手动刷新
if hasattr(manager, '_flush_buffer'):
    manager._flush_buffer()
    print("Buffer flushed")
