#!/usr/bin/env python3
"""调试Parquet保存问题"""

import os
import sys
from pathlib import Path

# 设置环境变量
os.environ['STORAGE_FORMAT'] = 'parquet'

print("=" * 60)
print("调试Parquet保存")
print("=" * 60)

# 1. 测试导入
print("\n1. 测试导入:")
try:
    from parquet_cumulative_manager import ParquetCumulativeManager
    print("   ✅ 成功导入ParquetCumulativeManager")
    
    # 创建实例
    manager = ParquetCumulativeManager()
    print("   ✅ 成功创建manager实例")
    
    # 检查manager的属性
    print(f"   数据目录: {manager.manager.data_dir}")
    print(f"   增量目录: {manager.manager.incremental_dir}")
    print(f"   进程ID: {manager.manager.process_id}")
    
except Exception as e:
    print(f"   ❌ 导入失败: {e}")
    sys.exit(1)

# 2. 测试添加数据
print("\n2. 测试添加数据:")
test_result = {
    'model': 'test-model',
    'task_type': 'simple_task',
    'prompt_type': 'baseline',
    'success': True,
    'execution_time': 1.23,
    'difficulty': 'easy',
    'tool_success_rate': 0.8,
    'turns': 5,
    'tool_calls': ['tool1', 'tool2']
}

try:
    # 记录文件数量
    before_count = len(list(manager.manager.incremental_dir.glob("*.parquet")))
    print(f"   添加前文件数: {before_count}")
    
    # 添加测试结果
    success = manager.add_test_result(**test_result)
    print(f"   add_test_result返回: {success}")
    
    # 检查是否创建了新文件
    after_count = len(list(manager.manager.incremental_dir.glob("*.parquet")))
    print(f"   添加后文件数: {after_count}")
    
    if after_count > before_count:
        # 找到新文件
        latest = max(manager.manager.incremental_dir.glob("*.parquet"), 
                    key=lambda f: f.stat().st_mtime)
        print(f"   ✅ 新文件: {latest.name}")
        
        # 读取验证
        import pandas as pd
        df = pd.read_parquet(latest)
        print(f"   文件包含 {len(df)} 条记录")
        if len(df) > 0:
            print(f"   最后一条: model={df.iloc[-1]['model']}")
    else:
        print(f"   ❌ 没有创建新文件")
        
except Exception as e:
    print(f"   ❌ 添加失败: {e}")
    import traceback
    traceback.print_exc()

# 3. 检查smart_batch_runner的调用链
print("\n3. 分析smart_batch_runner调用链:")
print("   smart_batch_runner.py")
print("     -> 导入 ParquetCumulativeManager (✅ 已修复)")
print("     -> SmartBatchRunner.__init__()")
print("       -> self.manager = EnhancedCumulativeManager()")
print("     -> process_batch()")
print("       -> self.manager.add_test_result()")
print("         -> ParquetCumulativeManager.add_test_result()")
print("           -> self.manager.append_test_result()")
print("             -> 写入Parquet文件")

print("\n4. 可能的问题:")
print("   - smart_batch_runner是否正确创建了manager实例？")
print("   - process_batch是否真的调用了add_test_result？")
print("   - 是否有异常被静默捕获？")