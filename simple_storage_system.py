#!/usr/bin/env python3
"""
简化的存储系统 - 只保留最实用的模式
"""

import os
import json
from typing import List, Optional
from pathlib import Path


class SimpleStorage:
    """简化的存储系统 - 自动选择安全的存储方式"""
    
    def __init__(self):
        # 检测是否需要并发安全
        self.use_safe_mode = self._detect_concurrent_mode()
        
        if self.use_safe_mode:
            print("[INFO] 检测到并发环境，使用安全存储模式（ResultCollector）")
            self._init_safe_storage()
        else:
            print("[INFO] 单进程环境，使用直接存储模式")
            self._init_direct_storage()
    
    def _detect_concurrent_mode(self) -> bool:
        """自动检测是否需要并发安全模式"""
        # 检查环境变量
        if os.environ.get('USE_RESULT_COLLECTOR', '').lower() == 'true':
            return True
        
        # 检查是否有多个worker
        workers = int(os.environ.get('CUSTOM_WORKERS', '1'))
        if workers > 5:
            return True
        
        # 检查是否是ultra_parallel模式
        if 'ultra_parallel' in os.environ.get('RUN_MODE', ''):
            return True
        
        return False
    
    def _init_safe_storage(self):
        """初始化并发安全存储（ResultCollector）"""
        from result_collector import ResultCollector
        from result_merger import start_auto_merge
        
        self.collector = ResultCollector()
        self.pid = os.getpid()
        
        # 启动后台合并进程
        try:
            self.merger = start_auto_merge(interval=10)
            print("[INFO] 后台合并进程已启动（每10秒合并一次）")
        except:
            self.merger = None
    
    def _init_direct_storage(self):
        """初始化直接存储"""
        # 根据格式选择管理器
        storage_format = os.environ.get('STORAGE_FORMAT', 'json').lower()
        
        if storage_format == 'parquet':
            try:
                from parquet_cumulative_manager import ParquetCumulativeManager
                self.manager = ParquetCumulativeManager()
                print("[INFO] 使用Parquet存储格式")
            except ImportError:
                from enhanced_cumulative_manager import EnhancedCumulativeManager
                self.manager = EnhancedCumulativeManager(use_ai_classification=True)
                print("[INFO] Parquet不可用，使用JSON格式")
        else:
            from enhanced_cumulative_manager import EnhancedCumulativeManager
            self.manager = EnhancedCumulativeManager(use_ai_classification=True)
            print("[INFO] 使用JSON存储格式")
        
        self.collector = None
    
    def write_result(self, record) -> bool:
        """写入单个结果"""
        try:
            if self.use_safe_mode and self.collector:
                # 并发安全模式：写临时文件
                model = self._get_model_name(record)
                result_dict = self._to_dict(record)
                self.collector.add_batch_result(model, [result_dict], {'pid': self.pid})
            else:
                # 直接模式：写数据库
                if hasattr(self.manager, 'add_test_result_with_classification'):
                    self.manager.add_test_result_with_classification(record)
                else:
                    self.manager.add_test_result(record)
            return True
        except Exception as e:
            print(f"[ERROR] 写入失败: {e}")
            return False
    
    def write_batch(self, records: List) -> int:
        """批量写入"""
        if self.use_safe_mode and self.collector:
            # 并发安全模式：按模型分组批量写入
            records_by_model = {}
            for record in records:
                model = self._get_model_name(record)
                if model not in records_by_model:
                    records_by_model[model] = []
                records_by_model[model].append(self._to_dict(record))
            
            total = 0
            for model, model_records in records_by_model.items():
                try:
                    self.collector.add_batch_result(model, model_records, {'pid': self.pid})
                    total += len(model_records)
                except:
                    pass
            return total
        else:
            # 直接模式：逐个写入
            count = 0
            for record in records:
                if self.write_result(record):
                    count += 1
            return count
    
    def flush(self):
        """刷新缓冲"""
        if not self.use_safe_mode and hasattr(self.manager, '_flush_buffer'):
            self.manager._flush_buffer()
    
    def close(self):
        """关闭存储"""
        if self.use_safe_mode and self.merger:
            try:
                from result_merger import stop_auto_merge, force_merge
                stop_auto_merge()
                count = force_merge()
                print(f"[INFO] 最终合并完成: {count} 个文件")
            except:
                pass
    
    def _get_model_name(self, record) -> str:
        """获取模型名"""
        if hasattr(record, 'model'):
            return record.model
        elif isinstance(record, dict):
            return record.get('model', 'unknown')
        return 'unknown'
    
    def _to_dict(self, record) -> dict:
        """转换为字典"""
        if hasattr(record, '__dict__'):
            return record.__dict__
        elif isinstance(record, dict):
            return record
        return {'data': str(record)}


def create_storage() -> SimpleStorage:
    """创建存储实例"""
    return SimpleStorage()


# 为了兼容性，保留原来的接口
def create_storage_adapter(manager=None):
    """兼容旧接口"""
    storage = SimpleStorage()
    
    # 创建适配器
    class StorageAdapter:
        def __init__(self, storage):
            self.storage = storage
        
        def write_result(self, record) -> bool:
            return self.storage.write_result(record)
        
        def write_batch(self, records) -> int:
            return self.storage.write_batch(records)
        
        def flush(self):
            self.storage.flush()
        
        def close(self):
            self.storage.close()
    
    return StorageAdapter(storage)


if __name__ == "__main__":
    print("简化存储系统测试")
    print("=" * 50)
    
    # 创建存储
    storage = create_storage()
    
    # 测试写入
    test_record = {
        'model': 'test-model',
        'task_type': 'simple_task',
        'success': True,
        'score': 0.95
    }
    
    print("\n测试写入...")
    success = storage.write_result(test_record)
    print(f"结果: {success}")
    
    # 关闭
    storage.close()
    print("\n测试完成")