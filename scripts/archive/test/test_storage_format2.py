import os
import sys
from pathlib import Path
from datetime import datetime

# 设置环境变量
os.environ['STORAGE_FORMAT'] = 'parquet'

# 导入
storage_format = os.environ.get('STORAGE_FORMAT', 'json').lower()
print(f"Storage format: {storage_format}")

if storage_format == 'parquet':
    from parquet_cumulative_manager import ParquetCumulativeManager as EnhancedCumulativeManager
    print("✅ Using ParquetCumulativeManager")
else:
    from enhanced_cumulative_manager import EnhancedCumulativeManager
    print("Using JSON format")

# 创建管理器
manager = EnhancedCumulativeManager()
print(f"Manager type: {type(manager).__name__}")

# 创建一个模拟的测试记录
class TestRecord:
    def __init__(self):
        self.model = 'test-model-2024'
        self.task_type = 'simple_task'
        self.prompt_type = 'optimal'
        self.difficulty = 'easy'
        self.tool_success_rate = 0.8
        self.success = True
        self.execution_time = 2.5
        self.turns = 10
        self.tool_calls = 5
        self.workflow_score = 0.9
        self.phase2_score = 0.85
        self.quality_score = 0.8
        self.final_score = 0.85

# 添加测试记录
record = TestRecord()
result = manager.add_test_result_with_classification(record)
print(f"Add result: {result}")

# 检查缓存
if hasattr(manager, '_summary_cache'):
    print(f"Cache size: {len(manager._summary_cache)}")
    for key in manager._summary_cache:
        print(f"  Cache key: {key}")
        print(f"  Total tests: {manager._summary_cache[key]['total']}")

# 强制刷新
print("\n强制刷新缓冲区...")
if hasattr(manager, '_flush_buffer'):
    manager._flush_buffer()

# 检查Parquet文件
parquet_file = Path('pilot_bench_parquet_data/test_results.parquet')
if parquet_file.exists():
    import pandas as pd
    df = pd.read_parquet(parquet_file)
    print(f"\n✅ Parquet文件状态:")
    print(f"  记录数: {len(df)}")
    print(f"  最后修改: {datetime.fromtimestamp(parquet_file.stat().st_mtime)}")
    
    # 查找我们刚添加的记录
    test_records = df[df['model'] == 'test-model-2024']
    if len(test_records) > 0:
        print(f"  ✅ 找到测试记录: {len(test_records)}条")
    else:
        print(f"  ❌ 没有找到测试记录")
