#!/usr/bin/env python3
"""
文件锁管理器 - 防止多进程并发写入冲突
使用fcntl实现文件锁（Unix/Linux/MacOS）
"""

import os
import time
import fcntl
import json
from pathlib import Path
from contextlib import contextmanager
from typing import Any, Dict, Optional
import tempfile
import shutil

class FileLockManager:
    """文件锁管理器，支持多进程安全的文件读写"""
    
    def __init__(self, file_path: Path, timeout: float = 30.0, retry_interval: float = 0.1):
        """
        初始化文件锁管理器
        
        Args:
            file_path: 要锁定的文件路径
            timeout: 获取锁的超时时间（秒）
            retry_interval: 重试间隔（秒）
        """
        self.file_path = Path(file_path)
        self.lock_path = self.file_path.with_suffix('.lock')
        self.timeout = timeout
        self.retry_interval = retry_interval
        
    @contextmanager
    def acquire_lock(self):
        """获取文件锁的上下文管理器"""
        lock_file = None
        lock_acquired = False
        start_time = time.time()
        
        try:
            # 创建锁文件
            while time.time() - start_time < self.timeout:
                try:
                    # 打开或创建锁文件
                    lock_file = open(self.lock_path, 'w')
                    # 尝试获取独占锁（非阻塞）
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    lock_acquired = True
                    break
                except (IOError, OSError):
                    # 锁被其他进程持有，等待并重试
                    if lock_file:
                        lock_file.close()
                    time.sleep(self.retry_interval)
            
            if not lock_acquired:
                raise TimeoutError(f"无法在 {self.timeout} 秒内获取文件锁: {self.lock_path}")
            
            # 写入进程信息（用于调试）
            lock_file.write(f"{os.getpid()}\n")
            lock_file.flush()
            
            yield  # 在这里执行被保护的代码
            
        finally:
            # 释放锁
            if lock_file and lock_acquired:
                try:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                except:
                    pass
                lock_file.close()
            
            # 清理锁文件（可选）
            try:
                if self.lock_path.exists():
                    self.lock_path.unlink()
            except:
                pass
    
    def read_json_safe(self) -> Dict[str, Any]:
        """安全地读取JSON文件"""
        with self.acquire_lock():
            if not self.file_path.exists():
                return {}
            
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    def write_json_safe(self, data: Dict[str, Any]) -> bool:
        """安全地写入JSON文件（原子操作）"""
        with self.acquire_lock():
            try:
                # 创建临时文件
                temp_fd, temp_path = tempfile.mkstemp(
                    dir=self.file_path.parent,
                    prefix=f".{self.file_path.stem}_",
                    suffix='.tmp'
                )
                
                # 写入数据到临时文件
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                # 原子替换
                shutil.move(temp_path, self.file_path)
                return True
                
            except Exception as e:
                print(f"[ERROR] 写入文件失败: {e}")
                # 清理临时文件
                if Path(temp_path).exists():
                    Path(temp_path).unlink()
                return False
    
    def update_json_safe(self, update_func) -> bool:
        """
        安全地更新JSON文件
        
        Args:
            update_func: 接收当前数据并返回更新后数据的函数
        
        Returns:
            是否更新成功
        """
        with self.acquire_lock():
            try:
                # 读取当前数据
                if self.file_path.exists():
                    with open(self.file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                else:
                    data = {}
                
                # 应用更新
                updated_data = update_func(data)
                
                # 写入更新后的数据（原子操作）
                temp_fd, temp_path = tempfile.mkstemp(
                    dir=self.file_path.parent,
                    prefix=f".{self.file_path.stem}_",
                    suffix='.tmp'
                )
                
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                    json.dump(updated_data, f, indent=2, ensure_ascii=False)
                
                # 原子替换
                shutil.move(temp_path, self.file_path)
                return True
                
            except Exception as e:
                print(f"[ERROR] 更新文件失败: {e}")
                # 清理临时文件
                if 'temp_path' in locals() and Path(temp_path).exists():
                    Path(temp_path).unlink()
                return False


class CrossPlatformFileLock:
    """跨平台文件锁实现（回退方案）"""
    
    def __init__(self, file_path: Path, timeout: float = 30.0, retry_interval: float = 0.1):
        """使用基于文件的锁，兼容Windows"""
        self.file_path = Path(file_path)
        self.lock_path = self.file_path.with_suffix('.lock')
        self.timeout = timeout
        self.retry_interval = retry_interval
    
    @contextmanager
    def acquire_lock(self):
        """获取文件锁（跨平台版本）"""
        lock_acquired = False
        start_time = time.time()
        
        try:
            while time.time() - start_time < self.timeout:
                try:
                    # 尝试创建锁文件（原子操作）
                    fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                    os.write(fd, f"{os.getpid()}\n".encode())
                    os.close(fd)
                    lock_acquired = True
                    break
                except FileExistsError:
                    # 锁文件已存在，检查是否过期
                    if self._is_lock_stale():
                        # 锁文件过期，尝试删除
                        try:
                            self.lock_path.unlink()
                        except:
                            pass
                    time.sleep(self.retry_interval)
            
            if not lock_acquired:
                raise TimeoutError(f"无法在 {self.timeout} 秒内获取文件锁: {self.lock_path}")
            
            yield
            
        finally:
            # 释放锁
            if lock_acquired:
                try:
                    self.lock_path.unlink()
                except:
                    pass
    
    def _is_lock_stale(self, max_age: float = 60.0) -> bool:
        """检查锁文件是否过期"""
        try:
            stat = self.lock_path.stat()
            age = time.time() - stat.st_mtime
            return age > max_age
        except:
            return False


def get_file_lock(file_path: Path, **kwargs) -> Any:
    """
    获取适合当前平台的文件锁
    
    Args:
        file_path: 文件路径
        **kwargs: 传递给锁构造函数的参数
    
    Returns:
        文件锁实例
    """
    try:
        # 尝试导入fcntl（Unix/Linux/MacOS）
        import fcntl
        return FileLockManager(file_path, **kwargs)
    except ImportError:
        # Windows或其他不支持fcntl的平台
        return CrossPlatformFileLock(file_path, **kwargs)


if __name__ == "__main__":
    # 测试文件锁
    import sys
    import random
    
    test_file = Path("test_lock.json")
    lock_manager = get_file_lock(test_file)
    
    def update_counter(data):
        """更新计数器"""
        if 'counter' not in data:
            data['counter'] = 0
        data['counter'] += 1
        data[f'process_{os.getpid()}'] = data.get(f'process_{os.getpid()}', 0) + 1
        return data
    
    # 模拟并发更新
    print(f"进程 {os.getpid()} 开始测试...")
    
    for i in range(5):
        success = lock_manager.update_json_safe(update_counter)
        if success:
            print(f"进程 {os.getpid()} 成功更新 (第{i+1}次)")
        else:
            print(f"进程 {os.getpid()} 更新失败 (第{i+1}次)")
        
        # 随机延迟
        time.sleep(random.uniform(0.1, 0.3))
    
    # 读取最终结果
    final_data = lock_manager.read_json_safe()
    print(f"进程 {os.getpid()} 看到的最终数据: {final_data}")