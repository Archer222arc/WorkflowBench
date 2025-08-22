#!/usr/bin/env python3
"""完整测试Parquet存储功能"""

import os
import sys
from pathlib import Path
from datetime import datetime

# 设置环境变量
os.environ['STORAGE_FORMAT'] = 'parquet'

print("=" * 70)
print("              完整Parquet存储测试")
print("=" * 70)

# 1. 测试模块导入
print("\n1️⃣ 测试模块导入:")
try:
    # 测试ParquetCumulativeManager
    from parquet_cumulative_manager import ParquetCumulativeManager
    print("   ✅ 成功导入ParquetCumulativeManager")
    
    # 测试TestRecord
    from cumulative_test_manager import TestRecord
    print("   ✅ 成功导入TestRecord")
    
    # 创建manager实例
    manager = ParquetCumulativeManager()
    print("   ✅ 成功创建manager实例")
    
except Exception as e:
    print(f"   ❌ 导入失败: {e}")
    sys.exit(1)

# 2. 测试add_test_result_with_classification方法
print("\n2️⃣ 测试add_test_result_with_classification:")

# 创建TestRecord对象
record = TestRecord(
    model='test-model-parquet',
    task_type='simple_task',
    prompt_type='baseline'
)
record.success = True
record.execution_time = 2.5
record.difficulty = 'easy'
record.tool_success_rate = 0.8
record.turns = 10
record.tool_calls = ['tool1', 'tool2', 'tool3']
record.partial_success = False
record.error_message = None

# 记录前状态
incremental_dir = Path("pilot_bench_parquet_data/incremental")
before_files = list(incremental_dir.glob("*.parquet"))
before_count = len(before_files)
print(f"   调用前文件数: {before_count}")

# 调用方法
try:
    result = manager.add_test_result_with_classification(record)
    print(f"   add_test_result_with_classification返回: {result}")
except Exception as e:
    print(f"   ❌ 调用失败: {e}")
    import traceback
    traceback.print_exc()

# 检查是否创建了新文件
after_files = list(incremental_dir.glob("*.parquet"))
after_count = len(after_files)
print(f"   调用后文件数: {after_count}")

if after_count > before_count:
    # 找到新文件
    new_files = set(after_files) - set(before_files)
    for f in new_files:
        print(f"   ✅ 新文件: {f.name}")
        
        # 验证内容
        import pandas as pd
        df = pd.read_parquet(f)
        print(f"      包含 {len(df)} 条记录")
        if len(df) > 0:
            last_row = df.iloc[-1]
            print(f"      最后一条: model={last_row['model']}")
else:
    # 检查是否更新了现有文件
    for f in after_files:
        if f.stat().st_mtime > (datetime.now().timestamp() - 10):
            print(f"   ✅ 更新了文件: {f.name}")
            
            # 验证内容
            import pandas as pd
            df = pd.read_parquet(f)
            print(f"      包含 {len(df)} 条记录")
            if len(df) > 0:
                last_row = df.iloc[-1]
                print(f"      最后一条: model={last_row['model']}")
            break
    else:
        print("   ❌ 没有创建或更新文件")

# 3. 分析问题
print("\n3️⃣ 问题分析:")
print("   如果上面的直接调用成功了，但通过smart_batch_runner调用失败，")
print("   可能的原因：")
print("   1. smart_batch_runner没有正确传递TestRecord的所有字段")
print("   2. smart_batch_runner有其他逻辑阻止了数据保存")
print("   3. 可能有异常被静默捕获")

print("\n" + "=" * 70)
print("                     测试总结")
print("=" * 70)

if result and (after_count > before_count or any(f.stat().st_mtime > (datetime.now().timestamp() - 10) for f in after_files)):
    print("✅ ParquetCumulativeManager功能正常！")
    print("\n已完成的修复：")
    print("  1. ✅ 修复了ultra_parallel_runner的环境变量传递")
    print("  2. ✅ 修复了smart_batch_runner的导入问题")
    print("  3. ✅ 添加了add_test_result_with_classification方法")
    print("\n下一步：")
    print("  测试通过smart_batch_runner的完整流程")
else:
    print("❌ 仍有问题需要解决")