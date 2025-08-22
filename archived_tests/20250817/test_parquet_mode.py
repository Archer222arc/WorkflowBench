#!/usr/bin/env python3
"""测试Parquet模式是否正常工作"""

import os
import sys

# 设置环境变量
os.environ['STORAGE_FORMAT'] = 'parquet'

print("测试Parquet存储模式...")
print("=" * 50)

# 导入管理器
try:
    from unified_storage_manager import UnifiedStorageManager
    
    manager = UnifiedStorageManager()
    print(f"✅ 存储格式: {manager.storage_format}")
    
    if manager.storage_format == 'parquet':
        print("✅ Parquet模式已激活")
        
        # 测试添加数据
        result = manager.add_test_result(
            model="test-model",
            task_type="simple_task", 
            prompt_type="optimal",
            success=True,
            execution_time=1.0
        )
        
        if result:
            print("✅ 测试数据添加成功")
        else:
            print("❌ 测试数据添加失败")
            
        # 检查文件
        from pathlib import Path
        if Path("pilot_bench_parquet_data").exists():
            print("✅ Parquet目录存在")
    else:
        print("❌ Parquet模式未激活")
        
except Exception as e:
    print(f"❌ 错误: {e}")

print("=" * 50)
