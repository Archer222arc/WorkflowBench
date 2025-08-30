#!/usr/bin/env python3
"""
合并器锁机制 - 确保只有一个ResultMerger实例在运行
"""

import os
import time
import fcntl
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class MergerLock:
    """使用文件锁确保只有一个合并器运行"""
    
    def __init__(self, lock_file: str = "temp_results/.merger.lock"):
        self.lock_file = Path(lock_file)
        self.lock_file.parent.mkdir(exist_ok=True)
        self.lock_fd = None
        self.has_lock = False
    
    def acquire(self, timeout: int = 0) -> bool:
        """
        尝试获取锁
        
        Args:
            timeout: 等待超时时间（秒），0表示立即返回
            
        Returns:
            是否成功获取锁
        """
        try:
            # 打开或创建锁文件
            self.lock_fd = open(self.lock_file, 'w')
            
            if timeout == 0:
                # 非阻塞模式
                fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.has_lock = True
                # 写入进程信息
                self.lock_fd.write(f"{os.getpid()}\n")
                self.lock_fd.flush()
                logger.info(f"获得合并器锁 (PID: {os.getpid()})")
                return True
            else:
                # 带超时的等待
                start_time = time.time()
                while time.time() - start_time < timeout:
                    try:
                        fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        self.has_lock = True
                        self.lock_fd.write(f"{os.getpid()}\n")
                        self.lock_fd.flush()
                        logger.info(f"获得合并器锁 (PID: {os.getpid()})")
                        return True
                    except IOError:
                        time.sleep(0.1)
                return False
                
        except IOError:
            # 无法获取锁
            if self.lock_fd:
                self.lock_fd.close()
                self.lock_fd = None
            return False
        except Exception as e:
            logger.error(f"获取锁失败: {e}")
            if self.lock_fd:
                self.lock_fd.close()
                self.lock_fd = None
            return False
    
    def release(self):
        """释放锁"""
        if self.has_lock and self.lock_fd:
            try:
                fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
                self.lock_fd.close()
                logger.info(f"释放合并器锁 (PID: {os.getpid()})")
            except Exception as e:
                logger.error(f"释放锁失败: {e}")
            finally:
                self.lock_fd = None
                self.has_lock = False
    
    def is_locked(self) -> bool:
        """检查锁是否被占用"""
        try:
            fd = open(self.lock_file, 'w')
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(fd, fcntl.LOCK_UN)
            fd.close()
            return False
        except IOError:
            return True
        except Exception:
            return False
    
    def get_lock_owner(self) -> int:
        """获取持有锁的进程PID"""
        try:
            if self.lock_file.exists():
                with open(self.lock_file, 'r') as f:
                    pid = f.read().strip()
                    if pid:
                        return int(pid)
        except Exception:
            pass
        return -1
    
    def __enter__(self):
        """上下文管理器入口"""
        self.acquire()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.release()


# 全局锁实例
_merger_lock = None

def get_merger_lock() -> MergerLock:
    """获取全局合并器锁实例"""
    global _merger_lock
    if _merger_lock is None:
        _merger_lock = MergerLock()
    return _merger_lock


if __name__ == "__main__":
    # 测试锁机制
    print("测试合并器锁...")
    
    lock = get_merger_lock()
    
    # 测试1：获取锁
    if lock.acquire():
        print(f"✅ 成功获取锁 (PID: {os.getpid()})")
        
        # 测试2：检查锁状态
        print(f"锁是否被占用: {lock.is_locked()}")
        print(f"锁持有者PID: {lock.get_lock_owner()}")
        
        # 测试3：尝试再次获取（应该失败）
        lock2 = MergerLock()
        if not lock2.acquire():
            print("✅ 正确：无法获取已被占用的锁")
        
        # 释放锁
        lock.release()
        print("✅ 锁已释放")
    
    # 测试4：使用上下文管理器
    print("\n使用上下文管理器测试...")
    with get_merger_lock() as lock:
        print(f"✅ 在with块中持有锁 (PID: {os.getpid()})")
    print("✅ 离开with块，锁自动释放")