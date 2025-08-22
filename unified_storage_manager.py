#!/usr/bin/env python3
"""
统一存储管理器
自动同步Parquet和JSON格式，确保master_database.json始终是最新的
"""

import os
import json
from pathlib import Path
from datetime import datetime
import threading
import time

class UnifiedStorageManager:
    """
    统一的存储管理器，支持：
    1. Parquet格式高性能存储
    2. 自动同步到master_database.json
    3. 保持向后兼容性
    """
    
    def __init__(self):
        self.storage_format = os.environ.get('STORAGE_FORMAT', 'json').lower()
        self.json_path = Path("pilot_bench_cumulative_results/master_database.json")
        self.parquet_dir = Path("pilot_bench_parquet_data")
        
        # 确保目录存在
        self.json_path.parent.mkdir(exist_ok=True)
        
        # 初始化管理器
        if self.storage_format == 'parquet':
            from parquet_cumulative_manager import ParquetCumulativeManager
            self.manager = ParquetCumulativeManager()
            print(f"[INFO] 使用Parquet存储（带JSON同步）")
            
            # 启动后台同步线程
            self._start_sync_thread()
        else:
            from cumulative_test_manager import CumulativeTestManager
            self.manager = CumulativeTestManager()
            print(f"[INFO] 使用JSON存储")
    
    def _start_sync_thread(self):
        """启动后台同步线程，定期将Parquet数据同步到JSON"""
        def sync_worker():
            while True:
                try:
                    # 每30秒同步一次
                    time.sleep(30)
                    self._sync_to_json()
                except Exception as e:
                    print(f"[WARNING] 同步失败: {e}")
        
        thread = threading.Thread(target=sync_worker, daemon=True)
        thread.start()
    
    def _sync_to_json(self):
        """将Parquet数据同步到master_database.json"""
        if self.storage_format == 'parquet':
            try:
                # 导出到JSON
                self.manager.export_to_json(self.json_path)
                print(f"[INFO] 已同步Parquet数据到 {self.json_path}")
            except Exception as e:
                print(f"[ERROR] 同步到JSON失败: {e}")
    
    def add_test_result(self, **kwargs):
        """添加测试结果"""
        result = self.manager.add_test_result(**kwargs)
        
        # 如果是Parquet模式，立即同步关键更新
        if self.storage_format == 'parquet' and result:
            # 每10个测试同步一次
            if hasattr(self, '_test_count'):
                self._test_count += 1
            else:
                self._test_count = 1
            
            if self._test_count % 10 == 0:
                self._sync_to_json()
        
        return result
    
    def finalize(self):
        """完成并同步所有数据"""
        self.manager.finalize()
        
        # 最终同步
        if self.storage_format == 'parquet':
            self._sync_to_json()
            print(f"[INFO] 最终数据已同步到 {self.json_path}")
    
    def check_progress(self, model: str, target_count: int = 100):
        """检查进度"""
        return self.manager.check_progress(model, target_count)
    
    def is_test_completed(self, **kwargs):
        """检查测试是否已完成"""
        return self.manager.is_test_completed(**kwargs)

# 创建全局实例
_global_unified_manager = None

def get_unified_manager():
    """获取统一管理器"""
    global _global_unified_manager
    if _global_unified_manager is None:
        _global_unified_manager = UnifiedStorageManager()
    return _global_unified_manager

# 导出兼容接口
def add_test_result(**kwargs):
    """添加测试结果"""
    return get_unified_manager().add_test_result(**kwargs)

def check_progress(model: str, target_count: int = 100):
    """检查进度"""
    return get_unified_manager().check_progress(model, target_count)

def is_test_completed(**kwargs):
    """检查测试是否完成"""
    return get_unified_manager().is_test_completed(**kwargs)

def finalize():
    """完成并同步"""
    return get_unified_manager().finalize()

if __name__ == "__main__":
    # 测试
    print(f"当前存储格式: {os.environ.get('STORAGE_FORMAT', 'json')}")
    
    # 测试添加数据
    result = add_test_result(
        model="test-model",
        task_type="simple_task",
        prompt_type="optimal",
        success=True,
        execution_time=10.5
    )
    print(f"添加结果: {result}")
    
    # 完成并同步
    finalize()
    
    # 检查JSON文件
    if Path("pilot_bench_cumulative_results/master_database.json").exists():
        print("✅ master_database.json 存在")
    
    # 检查Parquet文件
    if Path("pilot_bench_parquet_data/test_results.parquet").exists():
        print("✅ Parquet文件存在")