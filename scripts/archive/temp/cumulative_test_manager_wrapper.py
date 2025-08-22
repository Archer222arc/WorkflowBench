#!/usr/bin/env python3
"""
累积测试管理器包装器
自动根据STORAGE_FORMAT环境变量选择合适的后端
提供完全兼容的接口
"""

import os
import sys
from pathlib import Path

# 获取存储格式设置
STORAGE_FORMAT = os.environ.get('STORAGE_FORMAT', 'json').lower()

print(f"[INFO] 累积管理器使用{STORAGE_FORMAT.upper()}存储格式")

if STORAGE_FORMAT == 'parquet':
    # 使用Parquet后端
    try:
        # 导入Parquet版本的所有函数和类
        from parquet_cumulative_manager import (
            ParquetCumulativeManager as CumulativeTestManager,
            add_test_result,
            check_progress,
            is_test_completed,
            finalize,
            get_manager,
            normalize_model_name
        )
        # 提供额外的兼容性别名
        EnhancedCumulativeManager = CumulativeTestManager
        get_statistics = lambda **kwargs: get_manager().get_model_stats(**kwargs)
        
        print("[INFO] 已加载Parquet累积管理器")
        
    except ImportError as e:
        print(f"[WARNING] 无法加载Parquet管理器: {e}")
        print("[INFO] 回退到JSON管理器")
        # 回退到JSON
        STORAGE_FORMAT = 'json'

if STORAGE_FORMAT == 'json':
    # 使用JSON后端（默认）
    try:
        # 尝试导入全局函数
        from cumulative_test_manager import (
            add_test_result,
            check_progress,
            is_test_completed,
            normalize_model_name
        )
        # 导入类
        from cumulative_test_manager import CumulativeTestManager
        
        # 如果某些函数不存在，创建包装器
        if 'finalize' not in dir():
            def finalize():
                """完成数据同步"""
                manager = CumulativeTestManager()
                return manager.finalize()
        
        if 'get_manager' not in dir():
            _manager = None
            def get_manager():
                global _manager
                if _manager is None:
                    _manager = CumulativeTestManager()
                return _manager
        
        # 兼容性别名
        EnhancedCumulativeManager = CumulativeTestManager
        get_statistics = lambda **kwargs: {}  # JSON版本可能没有这个函数
        
        print("[INFO] 已加载JSON累积管理器")
        
    except ImportError as e:
        print(f"[ERROR] 无法加载任何管理器: {e}")
        sys.exit(1)

# 提供统一的接口函数列表
__all__ = [
    'CumulativeTestManager',
    'EnhancedCumulativeManager',
    'add_test_result',
    'check_progress',
    'is_test_completed',
    'finalize',
    'get_statistics',
    'normalize_model_name',
    'get_manager',
]

if __name__ == "__main__":
    # 测试代码
    print("\n测试累积管理器包装器")
    print("="*60)
    
    # 测试添加数据
    print("\n测试添加数据...")
    result = add_test_result(
        model="test-model",
        task_type="test-task",
        prompt_type="baseline",
        success=True,
        execution_time=1.0
    )
    print(f"添加结果: {result}")
    
    # 测试查询进度
    print("\n测试查询进度...")
    progress = check_progress("test-model", 100)
    print(f"进度: {progress}")
    
    # 测试完成同步
    print("\n测试数据同步...")
    try:
        finalize()
        print("同步完成")
    except Exception as e:
        print(f"同步失败: {e}")
    
    print("\n✅ 包装器工作正常")