#!/usr/bin/env python3
"""
存储适配器 - 统一的存储接口
提供数据库直写和ResultCollector两种模式的统一接口
"""

import os
from typing import Dict, List, Optional, Any
from pathlib import Path

class StorageAdapter:
    """存储适配器基类"""
    
    def write_result(self, record) -> bool:
        """写入单个结果"""
        raise NotImplementedError
    
    def write_batch(self, records: List) -> int:
        """批量写入结果"""
        count = 0
        for record in records:
            if self.write_result(record):
                count += 1
        return count
    
    def flush(self) -> None:
        """刷新缓冲区"""
        pass
    
    def close(self) -> None:
        """关闭存储"""
        pass


class DirectDatabaseAdapter(StorageAdapter):
    """直接写数据库的适配器"""
    
    def __init__(self, manager):
        """
        Args:
            manager: EnhancedCumulativeManager实例
        """
        self.manager = manager
    
    def write_result(self, record) -> bool:
        """直接写入数据库"""
        try:
            # 判断是否使用分类方法
            if hasattr(self.manager, 'add_test_result_with_classification'):
                self.manager.add_test_result_with_classification(record)
            elif hasattr(self.manager, 'append_test_result'):
                self.manager.append_test_result(record)
            else:
                self.manager.add_test_result(record)
            return True
        except Exception as e:
            print(f"[ERROR] 写入数据库失败: {e}")
            return False
    
    def flush(self) -> None:
        """刷新数据库缓冲"""
        if hasattr(self.manager, '_flush_buffer'):
            self.manager._flush_buffer()


class ResultCollectorAdapter(StorageAdapter):
    """通过ResultCollector写临时文件的适配器"""
    
    def __init__(self):
        """初始化ResultCollector"""
        from result_collector import ResultCollector
        self.collector = ResultCollector()
        self.pid = os.getpid()
    
    def write_result(self, record) -> bool:
        """写入临时文件"""
        try:
            # 获取模型名
            if hasattr(record, 'model'):
                model = record.model
            elif isinstance(record, dict):
                model = record.get('model', 'unknown')
            else:
                model = 'unknown'
            
            # 转换为字典格式
            if hasattr(record, '__dict__'):
                result_dict = record.__dict__
            elif isinstance(record, dict):
                result_dict = record
            else:
                result_dict = {'data': str(record)}
            
            # 调用ResultCollector
            self.collector.add_batch_result(
                model, 
                [result_dict], 
                {'pid': self.pid}
            )
            return True
            
        except Exception as e:
            print(f"[ERROR] 写入ResultCollector失败: {e}")
            return False
    
    def write_batch(self, records: List) -> int:
        """批量写入（优化版）"""
        try:
            # 按模型分组
            records_by_model = {}
            for record in records:
                # 获取模型名
                if hasattr(record, 'model'):
                    model = record.model
                elif isinstance(record, dict):
                    model = record.get('model', 'unknown')
                else:
                    model = 'unknown'
                
                if model not in records_by_model:
                    records_by_model[model] = []
                
                # 转换格式
                if hasattr(record, '__dict__'):
                    result_dict = record.__dict__
                elif isinstance(record, dict):
                    result_dict = record
                else:
                    result_dict = {'data': str(record)}
                
                records_by_model[model].append(result_dict)
            
            # 批量写入
            total_count = 0
            for model, model_records in records_by_model.items():
                self.collector.add_batch_result(
                    model,
                    model_records,
                    {'pid': self.pid}
                )
                total_count += len(model_records)
            
            return total_count
            
        except Exception as e:
            print(f"[ERROR] 批量写入失败: {e}")
            return 0


class HybridAdapter(StorageAdapter):
    """混合模式适配器 - 同时写数据库和临时文件"""
    
    def __init__(self, manager):
        """
        Args:
            manager: 数据库管理器
        """
        self.db_adapter = DirectDatabaseAdapter(manager)
        self.collector_adapter = ResultCollectorAdapter()
    
    def write_result(self, record) -> bool:
        """同时写入两个存储"""
        db_success = self.db_adapter.write_result(record)
        collector_success = self.collector_adapter.write_result(record)
        return db_success or collector_success
    
    def write_batch(self, records: List) -> int:
        """批量写入两个存储"""
        db_count = self.db_adapter.write_batch(records)
        collector_count = self.collector_adapter.write_batch(records)
        return max(db_count, collector_count)
    
    def flush(self) -> None:
        """刷新两个存储"""
        self.db_adapter.flush()
        self.collector_adapter.flush()


def create_storage_adapter(manager=None) -> StorageAdapter:
    """
    工厂方法：创建存储适配器（简化版）
    
    Args:
        manager: 数据库管理器（为了兼容性保留）
    
    Returns:
        StorageAdapter实例
    """
    # 使用简化的存储系统
    try:
        from simple_storage_system import SimpleStorage
        storage = SimpleStorage()
        
        # 创建适配器包装
        class SimpleStorageAdapter(StorageAdapter):
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
        
        return SimpleStorageAdapter(storage)
        
    except ImportError as e:
        print(f"[WARNING] 无法导入简化存储系统: {e}")
        # 回退到基础逻辑
        if os.environ.get('USE_RESULT_COLLECTOR', '').lower() == 'true':
            print("[INFO] 使用ResultCollector模式（仅临时文件）")
            return ResultCollectorAdapter()
        elif manager:
            print("[INFO] 使用直接数据库模式")
            return DirectDatabaseAdapter(manager)
        else:
            raise ValueError("必须提供manager或启用ResultCollector模式")


if __name__ == "__main__":
    # 测试代码
    print("存储适配器测试")
    
    # 测试ResultCollector模式
    os.environ['USE_RESULT_COLLECTOR'] = 'true'
    adapter = create_storage_adapter()
    
    # 测试写入
    test_record = {
        'model': 'test-model',
        'success': True,
        'score': 0.95
    }
    
    success = adapter.write_result(test_record)
    print(f"写入结果: {success}")
    
    # 批量写入
    records = [test_record for _ in range(5)]
    count = adapter.write_batch(records)
    print(f"批量写入: {count} 条记录")