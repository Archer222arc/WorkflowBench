#!/usr/bin/env python3
"""测试batch commit流程"""

import os
import sys
from pathlib import Path

# 设置环境变量
os.environ['STORAGE_FORMAT'] = 'parquet'

print("=" * 70)
print("        测试Smart Batch Runner的Commit流程")
print("=" * 70)

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 导入commit_to_database函数
from smart_batch_runner import commit_to_database

# 创建测试数据
test_results = [
    {
        'model': 'test-model',
        'task_type': 'simple_task',
        'prompt_type': 'baseline',
        'difficulty': 'easy',
        'success': True,
        'execution_time': 1.5,
        'turns': 10,
        'tool_calls': ['tool1', 'tool2'],
        'tool_success_rate': 0.8
    }
]

print("\n1️⃣ 调用commit_to_database...")
print(f"   传入 {len(test_results)} 个结果")

# 记录前状态
incremental_dir = Path("pilot_bench_parquet_data/incremental")
before_count = len(list(incremental_dir.glob("*.parquet")))
print(f"   调用前增量文件数: {before_count}")

# 调用commit_to_database
try:
    count = commit_to_database(
        results=test_results,
        model='test-model',
        difficulty='easy'
    )
    print(f"   ✅ 成功提交 {count} 个结果")
except Exception as e:
    print(f"   ❌ 提交失败: {e}")
    import traceback
    traceback.print_exc()

# 检查后状态
after_count = len(list(incremental_dir.glob("*.parquet")))
print(f"   调用后增量文件数: {after_count}")

print("\n2️⃣ 分析结果:")
if after_count == 0 and before_count > 0:
    print("   ✅ 增量文件已被合并到主文件（自动合并成功）")
elif after_count > before_count:
    print("   ✅ 创建了新的增量文件")
    print("   ℹ️ _flush_buffer可能没有被调用或合并条件未满足")
else:
    print("   ℹ️ 文件数无变化")

# 检查主文件
main_file = Path("pilot_bench_parquet_data/test_results.parquet")
if main_file.exists():
    import pandas as pd
    df = pd.read_parquet(main_file)
    print(f"\n3️⃣ 主文件状态:")
    print(f"   总记录数: {len(df)}")
    if 'model' in df.columns:
        test_model_count = len(df[df['model'] == 'test-model'])
        print(f"   test-model记录数: {test_model_count}")

print("\n" + "=" * 70)
print("结论:")
print("commit_to_database应该：")
print("  1. 创建TestRecord对象")
print("  2. 调用manager.add_test_result_with_classification()")
print("  3. 调用manager._flush_buffer()触发合并")
print("=" * 70)