#!/usr/bin/env python3
"""
数据保存包装器 - 确保数据定期保存
"""
import os
import sys
import time
import threading
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# 导入manager
storage_format = os.environ.get('STORAGE_FORMAT', 'json').lower()
if storage_format == 'parquet':
    try:
        from parquet_cumulative_manager import ParquetCumulativeManager as Manager
        print("[INFO] 使用Parquet存储格式")
    except ImportError:
        from enhanced_cumulative_manager import EnhancedCumulativeManager as Manager
        print("[INFO] 使用JSON存储格式")
else:
    from enhanced_cumulative_manager import EnhancedCumulativeManager as Manager
    print("[INFO] 使用JSON存储格式")

def periodic_flush(manager, interval=30):
    """定期刷新数据"""
    while True:
        time.sleep(interval)
        try:
            if hasattr(manager, '_flush_buffer'):
                manager._flush_buffer()
                print(f"[FLUSH] 数据已刷新到磁盘")
            if hasattr(manager, 'save_database'):
                manager.save_database()
                print(f"[SAVE] 数据库已保存")
        except Exception as e:
            print(f"[ERROR] 刷新失败: {e}")

# 创建全局manager实例
global_manager = Manager()

# 启动定期刷新线程
flush_thread = threading.Thread(target=periodic_flush, args=(global_manager, 30))
flush_thread.daemon = True
flush_thread.start()

print("[INFO] 定期刷新线程已启动（每30秒刷新）")
