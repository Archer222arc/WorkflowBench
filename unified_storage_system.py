#!/usr/bin/env python3
"""
统一存储系统 - 集成所有存储模式
支持：JSON直写、Parquet直写、ResultCollector、SmartCollector等
"""

import os
import json
import time
from enum import Enum
from typing import Dict, List, Optional, Any
from pathlib import Path
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class StorageMode(Enum):
    """存储模式枚举"""
    JSON_DIRECT = "json_direct"           # 模式1: JSON直接写入
    PARQUET_DIRECT = "parquet_direct"     # 模式2: Parquet直接写入
    RESULT_COLLECTOR = "result_collector" # 模式3: ResultCollector临时文件
    SMART_COLLECTOR = "smart_collector"   # 模式4: 智能收集器（自适应）
    HYBRID = "hybrid"                      # 模式5: 混合模式


class StorageConfig:
    """存储配置"""
    
    @staticmethod
    def get_mode() -> StorageMode:
        """根据环境变量确定存储模式"""
        
        # 检查显式模式设置
        mode_str = os.environ.get('STORAGE_MODE', '').lower()
        if mode_str:
            try:
                return StorageMode(mode_str)
            except ValueError:
                pass
        
        # 向后兼容：检查旧的环境变量
        if os.environ.get('USE_SMART_COLLECTOR', '').lower() == 'true':
            return StorageMode.SMART_COLLECTOR
        
        if os.environ.get('USE_RESULT_COLLECTOR', '').lower() == 'true':
            return StorageMode.RESULT_COLLECTOR
        
        # 检查存储格式
        storage_format = os.environ.get('STORAGE_FORMAT', 'json').lower()
        if storage_format == 'parquet':
            return StorageMode.PARQUET_DIRECT
        
        # 默认JSON直写
        return StorageMode.JSON_DIRECT
    
    @staticmethod
    def get_options() -> Dict[str, Any]:
        """获取存储选项"""
        return {
            'batch_size': int(os.environ.get('STORAGE_BATCH_SIZE', '100')),
            'flush_interval': int(os.environ.get('STORAGE_FLUSH_INTERVAL', '60')),
            'temp_dir': os.environ.get('STORAGE_TEMP_DIR', 'temp_results'),
            'enable_compression': os.environ.get('STORAGE_COMPRESSION', '').lower() == 'true',
            'enable_backup': os.environ.get('STORAGE_BACKUP', '').lower() == 'true',
            'merge_interval': int(os.environ.get('MERGE_INTERVAL', '10')),
        }


class BaseStorage(ABC):
    """存储接口基类"""
    
    @abstractmethod
    def write_result(self, record) -> bool:
        """写入单个结果"""
        pass
    
    @abstractmethod
    def write_batch(self, records: List) -> int:
        """批量写入"""
        pass
    
    def flush(self) -> None:
        """刷新缓冲区"""
        pass
    
    def close(self) -> None:
        """关闭存储"""
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {}


class JSONDirectStorage(BaseStorage):
    """JSON直接写入存储"""
    
    def __init__(self, options: Dict[str, Any]):
        self.options = options
        self._init_manager()
    
    def _init_manager(self):
        """初始化JSON管理器"""
        from enhanced_cumulative_manager import EnhancedCumulativeManager
        self.manager = EnhancedCumulativeManager(
            use_ai_classification=True
        )
        logger.info("JSONDirectStorage initialized")
    
    def write_result(self, record) -> bool:
        """写入单个结果到JSON数据库"""
        try:
            if hasattr(self.manager, 'add_test_result_with_classification'):
                self.manager.add_test_result_with_classification(record)
            else:
                self.manager.add_test_result(record)
            return True
        except Exception as e:
            logger.error(f"JSON write failed: {e}")
            return False
    
    def write_batch(self, records: List) -> int:
        """批量写入JSON"""
        count = 0
        for record in records:
            if self.write_result(record):
                count += 1
        return count
    
    def flush(self):
        """刷新JSON缓冲"""
        if hasattr(self.manager, '_flush_buffer'):
            self.manager._flush_buffer()
        if hasattr(self.manager, 'save_database'):
            self.manager.save_database()


class ParquetDirectStorage(BaseStorage):
    """Parquet直接写入存储"""
    
    def __init__(self, options: Dict[str, Any]):
        self.options = options
        self._init_manager()
    
    def _init_manager(self):
        """初始化Parquet管理器"""
        try:
            from parquet_cumulative_manager import ParquetCumulativeManager
            self.manager = ParquetCumulativeManager()
            logger.info("ParquetDirectStorage initialized")
        except ImportError:
            logger.warning("Parquet not available, falling back to JSON")
            from enhanced_cumulative_manager import EnhancedCumulativeManager
            self.manager = EnhancedCumulativeManager(use_ai_classification=True)
    
    def write_result(self, record) -> bool:
        """写入单个结果到Parquet"""
        try:
            if hasattr(self.manager, 'add_test_result_with_classification'):
                self.manager.add_test_result_with_classification(record)
            else:
                self.manager.add_test_result(record)
            return True
        except Exception as e:
            logger.error(f"Parquet write failed: {e}")
            return False
    
    def write_batch(self, records: List) -> int:
        """批量写入Parquet"""
        count = 0
        for record in records:
            if self.write_result(record):
                count += 1
        
        # Parquet需要定期flush以保存数据
        if count > 0 and count % self.options.get('batch_size', 100) == 0:
            self.flush()
        
        return count
    
    def flush(self):
        """刷新Parquet缓冲"""
        if hasattr(self.manager, '_flush_buffer'):
            self.manager._flush_buffer()


class ResultCollectorStorage(BaseStorage):
    """ResultCollector临时文件存储"""
    
    def __init__(self, options: Dict[str, Any]):
        self.options = options
        self._init_collector()
        self._init_merger()
    
    def _init_collector(self):
        """初始化ResultCollector"""
        from result_collector import ResultCollector
        self.collector = ResultCollector()
        self.pid = os.getpid()
        logger.info("ResultCollectorStorage initialized")
    
    def _init_merger(self):
        """初始化ResultMerger（后台合并进程）"""
        try:
            from result_merger import start_auto_merge
            interval = self.options.get('merge_interval', 10)
            self.merger = start_auto_merge(interval=interval)
            logger.info(f"ResultMerger started with {interval}s interval")
        except Exception as e:
            logger.warning(f"Failed to start ResultMerger: {e}")
            self.merger = None
    
    def write_result(self, record) -> bool:
        """写入单个结果到临时文件"""
        try:
            # 获取模型名
            if hasattr(record, 'model'):
                model = record.model
            elif isinstance(record, dict):
                model = record.get('model', 'unknown')
            else:
                model = 'unknown'
            
            # 转换为字典
            if hasattr(record, '__dict__'):
                result_dict = record.__dict__
            elif isinstance(record, dict):
                result_dict = record
            else:
                result_dict = {'data': str(record)}
            
            # 写入collector
            self.collector.add_batch_result(
                model,
                [result_dict],
                {'pid': self.pid}
            )
            return True
            
        except Exception as e:
            logger.error(f"ResultCollector write failed: {e}")
            return False
    
    def write_batch(self, records: List) -> int:
        """批量写入临时文件（优化版）"""
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
            try:
                self.collector.add_batch_result(
                    model,
                    model_records,
                    {'pid': self.pid}
                )
                total_count += len(model_records)
            except Exception as e:
                logger.error(f"Batch write failed for {model}: {e}")
        
        return total_count
    
    def close(self):
        """关闭存储，执行最终合并"""
        if self.merger:
            try:
                from result_merger import stop_auto_merge, force_merge
                stop_auto_merge()
                count = force_merge()
                logger.info(f"Final merge completed: {count} files")
            except Exception as e:
                logger.error(f"Final merge failed: {e}")


class SmartCollectorStorage(BaseStorage):
    """智能收集器存储（自适应）"""
    
    def __init__(self, options: Dict[str, Any]):
        self.options = options
        self._init_collector()
    
    def _init_collector(self):
        """初始化智能收集器"""
        try:
            from smart_result_collector import SmartResultCollector
            from result_collector_adapter import create_adaptive_collector
            
            # 根据规模创建合适的收集器
            scale = os.environ.get('COLLECTOR_SCALE', 'medium')
            if scale == 'small':
                self.collector = create_adaptive_collector(
                    max_memory_results=10,
                    max_time_seconds=30
                )
            elif scale == 'large':
                self.collector = create_adaptive_collector(
                    max_memory_results=1000,
                    max_time_seconds=300
                )
            else:
                self.collector = create_adaptive_collector()
            
            logger.info(f"SmartCollectorStorage initialized (scale={scale})")
            
        except ImportError:
            logger.warning("SmartCollector not available, using ResultCollector")
            from result_collector import ResultCollector
            self.collector = ResultCollector()
    
    def write_result(self, record) -> bool:
        """智能写入（自动决定写内存还是磁盘）"""
        try:
            # SmartCollector会自动决定存储位置
            if hasattr(self.collector, 'add_result'):
                triggered = self.collector.add_result(record)
                if triggered:
                    logger.debug("Smart trigger: flushing to disk")
            else:
                # 回退到批量接口
                model = getattr(record, 'model', 'unknown')
                result_dict = record.__dict__ if hasattr(record, '__dict__') else record
                self.collector.add_batch_result(model, [result_dict], {'pid': os.getpid()})
            return True
        except Exception as e:
            logger.error(f"SmartCollector write failed: {e}")
            return False
    
    def write_batch(self, records: List) -> int:
        """批量智能写入"""
        count = 0
        for record in records:
            if self.write_result(record):
                count += 1
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """获取收集器统计"""
        if hasattr(self.collector, 'get_stats'):
            return self.collector.get_stats()
        return {}


class HybridStorage(BaseStorage):
    """混合存储（多个存储后端）"""
    
    def __init__(self, options: Dict[str, Any], backends: List[BaseStorage]):
        self.options = options
        self.backends = backends
        logger.info(f"HybridStorage initialized with {len(backends)} backends")
    
    def write_result(self, record) -> bool:
        """写入所有后端"""
        success = False
        for backend in self.backends:
            if backend.write_result(record):
                success = True
        return success
    
    def write_batch(self, records: List) -> int:
        """批量写入所有后端"""
        max_count = 0
        for backend in self.backends:
            count = backend.write_batch(records)
            max_count = max(max_count, count)
        return max_count
    
    def flush(self):
        """刷新所有后端"""
        for backend in self.backends:
            backend.flush()
    
    def close(self):
        """关闭所有后端"""
        for backend in self.backends:
            backend.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """汇总所有后端统计"""
        stats = {}
        for i, backend in enumerate(self.backends):
            backend_stats = backend.get_stats()
            stats[f'backend_{i}'] = {
                'type': backend.__class__.__name__,
                'stats': backend_stats
            }
        return stats


class UnifiedStorageSystem:
    """统一存储系统 - 工厂类"""
    
    @staticmethod
    def create(custom_mode: Optional[StorageMode] = None) -> BaseStorage:
        """
        创建存储实例
        
        Args:
            custom_mode: 自定义模式（可选，否则从环境变量读取）
        
        Returns:
            BaseStorage实例
        """
        mode = custom_mode or StorageConfig.get_mode()
        options = StorageConfig.get_options()
        
        logger.info(f"Creating storage system: mode={mode.value}")
        
        if mode == StorageMode.JSON_DIRECT:
            return JSONDirectStorage(options)
        
        elif mode == StorageMode.PARQUET_DIRECT:
            return ParquetDirectStorage(options)
        
        elif mode == StorageMode.RESULT_COLLECTOR:
            return ResultCollectorStorage(options)
        
        elif mode == StorageMode.SMART_COLLECTOR:
            return SmartCollectorStorage(options)
        
        elif mode == StorageMode.HYBRID:
            # 混合模式：同时使用多个后端
            backends = []
            
            # 添加直接写入后端
            storage_format = os.environ.get('STORAGE_FORMAT', 'json').lower()
            if storage_format == 'parquet':
                backends.append(ParquetDirectStorage(options))
            else:
                backends.append(JSONDirectStorage(options))
            
            # 添加collector后端
            if os.environ.get('ENABLE_COLLECTOR', '').lower() == 'true':
                backends.append(ResultCollectorStorage(options))
            
            return HybridStorage(options, backends)
        
        else:
            raise ValueError(f"Unknown storage mode: {mode}")
    
    @staticmethod
    def print_config():
        """打印当前配置"""
        mode = StorageConfig.get_mode()
        options = StorageConfig.get_options()
        
        print("=" * 60)
        print("统一存储系统配置")
        print("=" * 60)
        print(f"模式: {mode.value}")
        print(f"选项:")
        for key, value in options.items():
            print(f"  {key}: {value}")
        print("=" * 60)


def create_storage(manager=None) -> BaseStorage:
    """
    便捷函数：创建存储实例
    
    Args:
        manager: 数据库管理器（为了向后兼容）
    
    Returns:
        BaseStorage实例
    """
    return UnifiedStorageSystem.create()


if __name__ == "__main__":
    # 测试代码
    print("统一存储系统测试")
    
    # 打印配置
    UnifiedStorageSystem.print_config()
    
    # 创建存储
    storage = UnifiedStorageSystem.create()
    print(f"\n创建的存储类型: {storage.__class__.__name__}")
    
    # 测试写入
    test_record = {
        'model': 'test-model',
        'task_type': 'simple_task',
        'success': True,
        'score': 0.95
    }
    
    print(f"\n测试写入单个记录...")
    success = storage.write_result(test_record)
    print(f"结果: {success}")
    
    print(f"\n测试批量写入...")
    records = [test_record.copy() for _ in range(5)]
    count = storage.write_batch(records)
    print(f"写入数量: {count}")
    
    # 获取统计
    stats = storage.get_stats()
    if stats:
        print(f"\n统计信息: {stats}")
    
    # 关闭
    storage.close()
    print("\n测试完成")