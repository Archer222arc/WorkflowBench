#!/usr/bin/env python3
"""
统一的存储后端管理器
支持JSON和Parquet两种存储格式
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

# 存储后端接口
class StorageBackend(ABC):
    """存储后端抽象基类"""
    
    @abstractmethod
    def add_test_result(self, **kwargs) -> bool:
        """添加测试结果"""
        pass
    
    @abstractmethod
    def get_model_stats(self, model: str = None) -> Dict:
        """获取模型统计"""
        pass
    
    @abstractmethod
    def check_progress(self, model: str, target_count: int = 100) -> Dict:
        """检查进度"""
        pass
    
    @abstractmethod
    def is_test_completed(self, **kwargs) -> bool:
        """检查测试是否完成"""
        pass
    
    @abstractmethod
    def finalize(self):
        """完成数据同步"""
        pass
    
    @abstractmethod
    def get_backend_name(self) -> str:
        """获取后端名称"""
        pass


class JSONBackend(StorageBackend):
    """JSON存储后端"""
    
    def __init__(self):
        # 延迟导入，避免循环依赖
        from cumulative_test_manager import CumulativeTestManager
        self.manager = CumulativeTestManager()
    
    def add_test_result(self, **kwargs) -> bool:
        """添加测试结果"""
        return self.manager.add_test_result(**kwargs)
    
    def get_model_stats(self, model: str = None) -> Dict:
        """获取模型统计"""
        if model:
            return self.manager.get_model_stats(model)
        return {}
    
    def check_progress(self, model: str, target_count: int = 100) -> Dict:
        """检查进度"""
        return self.manager.check_progress(model, target_count)
    
    def is_test_completed(self, **kwargs) -> bool:
        """检查测试是否完成"""
        return self.manager.is_test_completed(**kwargs)
    
    def finalize(self):
        """完成数据同步"""
        self.manager.finalize()
    
    def get_backend_name(self) -> str:
        return "JSON"


class ParquetBackend(StorageBackend):
    """Parquet存储后端"""
    
    def __init__(self):
        # 检查是否已安装必要的库
        try:
            import pandas as pd
            import pyarrow
        except ImportError:
            print("⚠️ 警告：Parquet后端需要安装pandas和pyarrow")
            print("运行: pip install pandas pyarrow")
            sys.exit(1)
        
        from parquet_cumulative_manager import ParquetCumulativeManager
        self.manager = ParquetCumulativeManager()
    
    def add_test_result(self, **kwargs) -> bool:
        """添加测试结果"""
        return self.manager.add_test_result(**kwargs)
    
    def get_model_stats(self, model: str = None) -> Dict:
        """获取模型统计"""
        return self.manager.get_model_stats(model)
    
    def check_progress(self, model: str, target_count: int = 100) -> Dict:
        """检查进度"""
        return self.manager.check_progress(model, target_count)
    
    def is_test_completed(self, **kwargs) -> bool:
        """检查测试是否完成"""
        return self.manager.is_test_completed(**kwargs)
    
    def finalize(self):
        """完成数据同步"""
        self.manager.finalize()
    
    def get_backend_name(self) -> str:
        return "Parquet"


class StorageBackendManager:
    """存储后端管理器单例"""
    
    _instance = None
    _backend = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._backend is None:
            self._initialize_backend()
    
    def _initialize_backend(self):
        """初始化存储后端"""
        # 从环境变量读取存储格式
        storage_format = os.environ.get('STORAGE_FORMAT', 'json').lower()
        
        # 也支持从命令行参数读取
        if '--storage-format' in sys.argv:
            idx = sys.argv.index('--storage-format')
            if idx + 1 < len(sys.argv):
                storage_format = sys.argv[idx + 1].lower()
        
        # 创建对应的后端
        if storage_format == 'parquet':
            print(f"[INFO] 使用Parquet存储后端")
            self._backend = ParquetBackend()
        else:
            print(f"[INFO] 使用JSON存储后端")
            self._backend = JSONBackend()
    
    def get_backend(self) -> StorageBackend:
        """获取当前存储后端"""
        if self._backend is None:
            self._initialize_backend()
        return self._backend
    
    def switch_backend(self, backend_type: str):
        """切换存储后端"""
        backend_type = backend_type.lower()
        if backend_type == 'parquet':
            self._backend = ParquetBackend()
        elif backend_type == 'json':
            self._backend = JSONBackend()
        else:
            raise ValueError(f"不支持的存储后端: {backend_type}")
        print(f"[INFO] 已切换到{self._backend.get_backend_name()}存储后端")
    
    @classmethod
    def reset(cls):
        """重置管理器（用于测试）"""
        cls._instance = None
        cls._backend = None


# 全局函数（兼容原有接口）
def get_storage_backend() -> StorageBackend:
    """获取存储后端实例"""
    return StorageBackendManager().get_backend()

def add_test_result(**kwargs) -> bool:
    """添加测试结果"""
    return get_storage_backend().add_test_result(**kwargs)

def check_progress(model: str, target_count: int = 100) -> Dict:
    """检查进度"""
    return get_storage_backend().check_progress(model, target_count)

def is_test_completed(**kwargs) -> bool:
    """检查测试是否完成"""
    return get_storage_backend().is_test_completed(**kwargs)

def finalize():
    """完成数据同步"""
    get_storage_backend().finalize()

def get_model_stats(model: str = None) -> Dict:
    """获取模型统计"""
    return get_storage_backend().get_model_stats(model)


# 环境检查和设置
def check_and_setup_environment():
    """检查并设置环境"""
    storage_format = os.environ.get('STORAGE_FORMAT', 'json').lower()
    
    print("="*60)
    print("存储后端配置")
    print("="*60)
    print(f"当前存储格式: {storage_format.upper()}")
    
    if storage_format == 'parquet':
        # 检查Parquet依赖
        try:
            import pandas
            import pyarrow
            print("✅ Parquet依赖已安装")
            
            # 检查数据目录
            parquet_dir = Path("pilot_bench_parquet_data")
            if parquet_dir.exists():
                parquet_files = list(parquet_dir.glob("*.parquet"))
                if parquet_files:
                    print(f"✅ 找到{len(parquet_files)}个Parquet文件")
                else:
                    print("⚠️ Parquet目录存在但没有数据文件")
            else:
                print("⚠️ Parquet数据目录不存在，将在首次写入时创建")
                
        except ImportError as e:
            print(f"❌ 缺少Parquet依赖: {e}")
            print("请运行: pip install pandas pyarrow")
            return False
    else:
        # 检查JSON数据
        json_db = Path("pilot_bench_cumulative_results/master_database.json")
        if json_db.exists():
            print(f"✅ JSON数据库存在")
            # 检查文件大小
            size_mb = json_db.stat().st_size / (1024 * 1024)
            print(f"   文件大小: {size_mb:.2f} MB")
            if size_mb > 50:
                print("⚠️ JSON文件较大，建议切换到Parquet格式")
        else:
            print("⚠️ JSON数据库不存在，将在首次写入时创建")
    
    print("="*60)
    return True


if __name__ == "__main__":
    # 测试代码
    print("存储后端管理器测试")
    print("="*60)
    
    # 检查环境
    if not check_and_setup_environment():
        sys.exit(1)
    
    # 测试当前后端
    backend = get_storage_backend()
    print(f"\n当前使用: {backend.get_backend_name()}后端")
    
    # 测试基本功能
    print("\n测试添加数据...")
    success = add_test_result(
        model="gpt-4o-mini",
        task_type="test_task",
        prompt_type="baseline",
        success=True,
        execution_time=1.5
    )
    print(f"添加结果: {'✅ 成功' if success else '❌ 失败'}")
    
    # 测试查询
    print("\n测试查询进度...")
    progress = check_progress("gpt-4o-mini", 100)
    print(f"进度: {progress}")
    
    # 测试切换后端
    print("\n测试切换后端...")
    manager = StorageBackendManager()
    
    # 切换到另一个后端
    current = backend.get_backend_name()
    new_backend = 'parquet' if current == 'JSON' else 'json'
    
    print(f"切换到{new_backend.upper()}...")
    manager.switch_backend(new_backend)
    
    new_backend_obj = manager.get_backend()
    print(f"当前后端: {new_backend_obj.get_backend_name()}")
    
    print("\n✅ 测试完成！")