#!/usr/bin/env python3
"""
安全数据库管理器 - 防止数据覆盖和卡死的综合保护机制
"""

import os
import json
import time
import hashlib
import threading
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from contextlib import contextmanager
from filelock import FileLock, Timeout

logger = logging.getLogger(__name__)

class SafeDatabaseManager:
    """
    安全数据库管理器
    
    核心特性:
    1. 非阻塞文件锁 - 避免无限等待
    2. 原子写入操作 - 防止文件损坏
    3. 数据完整性检查 - 检测并发冲突
    4. 优雅降级机制 - 冲突时的合理处理
    """
    
    def __init__(self, db_path: str, lock_timeout: float = 10.0, 
                 max_retry: int = 3, backup_enabled: bool = True):
        """
        初始化安全数据库管理器
        
        Args:
            db_path: 数据库文件路径
            lock_timeout: 文件锁超时时间（秒）
            max_retry: 最大重试次数
            backup_enabled: 是否启用自动备份
        """
        self.db_path = Path(db_path)
        self.lock_path = Path(f"{db_path}.lock")
        self.temp_path = Path(f"{db_path}.tmp")
        self.lock_timeout = lock_timeout
        self.max_retry = max_retry
        self.backup_enabled = backup_enabled
        
        # 创建目录
        self.db_path.parent.mkdir(exist_ok=True, parents=True)
        
        # 内存缓存和版本控制
        self._cache = None
        self._cache_hash = None
        self._cache_lock = threading.RLock()
        
        logger.info(f"SafeDatabaseManager initialized: {db_path}")
        logger.info(f"Lock timeout: {lock_timeout}s, Max retry: {max_retry}")
    
    def _calculate_hash(self, data: Dict[str, Any]) -> str:
        """计算数据的哈希值用于版本控制"""
        json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(json_str.encode('utf-8')).hexdigest()[:16]
    
    def _create_backup(self, data: Dict[str, Any]) -> Optional[Path]:
        """创建数据备份"""
        if not self.backup_enabled:
            return None
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = self.db_path.parent / "backups"
            backup_dir.mkdir(exist_ok=True)
            
            backup_path = backup_dir / f"{self.db_path.stem}_backup_{timestamp}.json"
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Backup created: {backup_path}")
            return backup_path
        except Exception as e:
            logger.warning(f"Failed to create backup: {e}")
            return None
    
    @contextmanager
    def _acquire_lock(self):
        """获取非阻塞文件锁"""
        file_lock = FileLock(self.lock_path)
        try:
            with file_lock.acquire(timeout=self.lock_timeout):
                yield
        except Timeout:
            logger.warning(f"Failed to acquire lock within {self.lock_timeout}s")
            raise
    
    def _load_from_disk(self) -> Dict[str, Any]:
        """从磁盘加载数据"""
        if not self.db_path.exists():
            logger.info(f"Database file not found, creating new: {self.db_path}")
            return {}
        
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load database: {e}")
            # 尝试从备份恢复
            return self._recover_from_backup()
    
    def _recover_from_backup(self) -> Dict[str, Any]:
        """从备份恢复数据"""
        backup_dir = self.db_path.parent / "backups"
        if not backup_dir.exists():
            logger.warning("No backup directory found, returning empty database")
            return {}
        
        # 查找最新的备份
        backups = list(backup_dir.glob(f"{self.db_path.stem}_backup_*.json"))
        if not backups:
            logger.warning("No backup files found, returning empty database")
            return {}
        
        latest_backup = max(backups, key=lambda p: p.stat().st_mtime)
        logger.info(f"Recovering from backup: {latest_backup}")
        
        try:
            with open(latest_backup, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to recover from backup: {e}")
            return {}
    
    def _atomic_write(self, data: Dict[str, Any]) -> bool:
        """原子写入数据"""
        try:
            # 1. 写入临时文件
            with open(self.temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # 2. 原子性重命名
            self.temp_path.replace(self.db_path)
            
            logger.debug(f"Atomic write completed: {self.db_path}")
            return True
            
        except Exception as e:
            logger.error(f"Atomic write failed: {e}")
            # 清理临时文件
            if self.temp_path.exists():
                try:
                    self.temp_path.unlink()
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup temp file: {cleanup_error}")
            return False
    
    def load_database(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        安全加载数据库
        
        Args:
            use_cache: 是否使用内存缓存
            
        Returns:
            数据库内容
        """
        with self._cache_lock:
            if use_cache and self._cache is not None:
                return self._cache.copy()
        
        for attempt in range(self.max_retry):
            try:
                with self._acquire_lock():
                    data = self._load_from_disk()
                    
                    # 更新缓存
                    with self._cache_lock:
                        self._cache = data.copy()
                        self._cache_hash = self._calculate_hash(data)
                    
                    return data.copy()
                    
            except Timeout:
                if attempt < self.max_retry - 1:
                    wait_time = (attempt + 1) * 0.5  # 递增等待
                    logger.warning(f"Lock timeout, retrying in {wait_time}s... ({attempt + 1}/{self.max_retry})")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to load database after {self.max_retry} attempts")
                    # 优雅降级：返回缓存或空数据
                    with self._cache_lock:
                        if self._cache is not None:
                            logger.warning("Using cached data as fallback")
                            return self._cache.copy()
                    return {}
        
        return {}
    
    def save_database(self, data: Dict[str, Any], force_save: bool = False) -> bool:
        """
        安全保存数据库
        
        Args:
            data: 要保存的数据
            force_save: 强制保存（忽略版本冲突）
            
        Returns:
            是否保存成功
        """
        current_hash = self._calculate_hash(data)
        
        for attempt in range(self.max_retry):
            try:
                with self._acquire_lock():
                    # 检查数据一致性（除非强制保存）
                    if not force_save:
                        disk_data = self._load_from_disk()
                        disk_hash = self._calculate_hash(disk_data)
                        
                        # 检测冲突
                        with self._cache_lock:
                            if self._cache_hash is not None and disk_hash != self._cache_hash:
                                logger.warning("Data conflict detected, attempting merge")
                                merged_data = self._merge_data(self._cache, disk_data, data)
                                if merged_data is not None:
                                    data = merged_data
                                    current_hash = self._calculate_hash(data)
                                else:
                                    logger.error("Data merge failed, forcing save")
                                    # 继续使用原数据，但创建冲突备份
                                    self._create_backup(disk_data)
                    
                    # 创建备份
                    if self.backup_enabled:
                        self._create_backup(data)
                    
                    # 原子写入
                    if self._atomic_write(data):
                        # 更新缓存
                        with self._cache_lock:
                            self._cache = data.copy()
                            self._cache_hash = current_hash
                        
                        logger.debug(f"Database saved successfully")
                        return True
                    else:
                        logger.error("Atomic write failed")
                        return False
                        
            except Timeout:
                if attempt < self.max_retry - 1:
                    wait_time = (attempt + 1) * 0.5
                    logger.warning(f"Lock timeout, retrying in {wait_time}s... ({attempt + 1}/{self.max_retry})")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to save database after {self.max_retry} attempts")
                    return False
        
        return False
    
    def _merge_data(self, cached_data: Dict[str, Any], disk_data: Dict[str, Any], 
                   new_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        智能合并数据冲突
        
        Args:
            cached_data: 缓存的数据
            disk_data: 磁盘上的数据
            new_data: 要保存的新数据
            
        Returns:
            合并后的数据，失败时返回None
        """
        try:
            # 简单的合并策略：以新数据为基础，合并磁盘数据中的新增模型
            merged = new_data.copy()
            
            disk_models = disk_data.get('models', {})
            new_models = merged.get('models', {})
            
            # 合并模型数据
            for model_name, model_data in disk_models.items():
                if model_name not in new_models:
                    # 新增的模型，直接添加
                    new_models[model_name] = model_data
                    logger.info(f"Merged new model from disk: {model_name}")
                else:
                    # 存在的模型，合并prompt_type
                    existing_model = new_models[model_name]
                    disk_prompts = model_data.get('by_prompt_type', {})
                    existing_prompts = existing_model.get('by_prompt_type', {})
                    
                    for prompt_type, prompt_data in disk_prompts.items():
                        if prompt_type not in existing_prompts:
                            existing_prompts[prompt_type] = prompt_data
                            logger.info(f"Merged new prompt type for {model_name}: {prompt_type}")
            
            merged['models'] = new_models
            
            # 更新汇总统计
            merged['summary'] = self._calculate_summary(merged.get('models', {}))
            
            return merged
            
        except Exception as e:
            logger.error(f"Data merge failed: {e}")
            return None
    
    def _calculate_summary(self, models: Dict[str, Any]) -> Dict[str, Any]:
        """计算汇总统计"""
        total_tests = 0
        total_success = 0
        total_failure = 0
        models_tested = []
        
        for model_name, model_data in models.items():
            overall_stats = model_data.get('overall_stats', {})
            model_total = overall_stats.get('total_tests', 0)
            if model_total > 0:
                models_tested.append(model_name)
                total_tests += model_total
                # 简单估算成功数
                success_rate = overall_stats.get('success_rate', 0)
                total_success += int(model_total * success_rate / 100)
        
        total_failure = total_tests - total_success
        
        return {
            'total_tests': total_tests,
            'total_success': total_success,
            'total_failure': total_failure,
            'models_tested': models_tested,
            'last_test_time': datetime.now().isoformat()
        }
    
    def cleanup_old_backups(self, keep_days: int = 7, keep_count: int = 10):
        """清理旧的备份文件"""
        backup_dir = self.db_path.parent / "backups"
        if not backup_dir.exists():
            return
        
        # 按时间排序的备份文件
        backups = list(backup_dir.glob(f"{self.db_path.stem}_backup_*.json"))
        backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        
        # 保留最新的keep_count个文件
        keep_by_count = backups[:keep_count]
        
        # 保留keep_days天内的文件
        cutoff_time = time.time() - (keep_days * 24 * 60 * 60)
        keep_by_time = [b for b in backups if b.stat().st_mtime > cutoff_time]
        
        # 合并保留列表
        keep_files = set(keep_by_count + keep_by_time)
        
        # 删除其他文件
        deleted_count = 0
        for backup in backups:
            if backup not in keep_files:
                try:
                    backup.unlink()
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete backup {backup}: {e}")
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old backup files")


# 使用示例和工厂函数
def create_safe_database_manager(db_path: str, **kwargs) -> SafeDatabaseManager:
    """创建安全数据库管理器的工厂函数"""
    return SafeDatabaseManager(db_path, **kwargs)


if __name__ == "__main__":
    # 测试代码
    import tempfile
    
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        test_db_path = f.name
    
    manager = SafeDatabaseManager(test_db_path, lock_timeout=2.0)
    
    # 测试基本操作
    test_data = {"test": "data", "models": {"test_model": {"total_tests": 10}}}
    
    print("Testing safe database manager...")
    success = manager.save_database(test_data)
    print(f"Save result: {success}")
    
    loaded_data = manager.load_database()
    print(f"Loaded data: {loaded_data}")
    
    # 清理
    import os
    try:
        os.unlink(test_db_path)
        os.unlink(test_db_path + ".lock")
    except:
        pass
    
    print("Test completed")