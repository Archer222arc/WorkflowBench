#!/usr/bin/env python3
"""
线程强制终止机制
使用ctypes强制终止Python线程（谨慎使用）
"""

import threading
import time
import ctypes
import logging
from typing import Optional, Callable, Any

logger = logging.getLogger(__name__)

class ThreadWithKill(threading.Thread):
    """可以被强制终止的线程"""
    
    def __init__(self, target: Callable, args=(), kwargs=None):
        super().__init__(target=target, args=args, kwargs=kwargs or {})
        self._result = None
        self._exception = None
        self._target_func = target
        self._args = args
        self._kwargs = kwargs or {}
        
    def run(self):
        """运行目标函数并捕获结果或异常"""
        try:
            self._result = self._target_func(*self._args, **self._kwargs)
        except Exception as e:
            self._exception = e
            
    def get_result(self):
        """获取执行结果"""
        if self._exception:
            raise self._exception
        return self._result
    
    def force_kill(self):
        """强制终止线程（危险操作）"""
        if not self.is_alive():
            return
            
        # 获取线程ID
        tid = self.ident
        if tid is None:
            return
            
        # 使用ctypes强制抛出异常来终止线程
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
            ctypes.c_long(tid),
            ctypes.py_object(SystemExit)
        )
        
        if res == 0:
            logger.warning(f"Thread {tid} does not exist")
        elif res > 1:
            # 如果影响了多个线程，撤销操作
            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), None)
            logger.error(f"Failed to kill thread {tid}")
        else:
            logger.info(f"Thread {tid} killed successfully")


def run_with_timeout(func: Callable, timeout_seconds: int, *args, **kwargs) -> Any:
    """
    运行函数并在超时时强制终止
    
    Args:
        func: 要执行的函数
        timeout_seconds: 超时时间（秒）
        *args, **kwargs: 传递给函数的参数
        
    Returns:
        函数执行结果
        
    Raises:
        TimeoutError: 如果执行超时
    """
    # 创建可终止的线程
    thread = ThreadWithKill(target=func, args=args, kwargs=kwargs)
    thread.daemon = True
    thread.start()
    
    # 等待线程完成或超时
    thread.join(timeout=timeout_seconds)
    
    if thread.is_alive():
        # 尝试强制终止
        logger.warning(f"Function {func.__name__} exceeded timeout of {timeout_seconds}s, forcing termination...")
        thread.force_kill()
        
        # 再等待一小段时间
        thread.join(timeout=5)
        
        if thread.is_alive():
            logger.error(f"Failed to terminate thread for {func.__name__}")
        
        raise TimeoutError(f"Function {func.__name__} timed out after {timeout_seconds} seconds")
    
    # 获取结果
    return thread.get_result()


class TimeoutGuard:
    """超时守护器 - 监控并终止超时的操作"""
    
    def __init__(self, timeout_seconds: int):
        self.timeout_seconds = timeout_seconds
        self.start_time = None
        self.monitor_thread = None
        self.target_thread = None
        self.completed = False
        
    def start(self, target_thread: threading.Thread):
        """开始监控指定线程"""
        self.target_thread = target_thread
        self.start_time = time.time()
        self.completed = False
        
        def monitor():
            while not self.completed:
                if time.time() - self.start_time > self.timeout_seconds:
                    logger.warning(f"Timeout guard triggered after {self.timeout_seconds}s")
                    if self.target_thread and self.target_thread.is_alive():
                        # 这里可以记录或采取其他措施
                        logger.error(f"Thread {self.target_thread.ident} is still running after timeout")
                    break
                time.sleep(1)
        
        self.monitor_thread = threading.Thread(target=monitor)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
    def stop(self):
        """停止监控"""
        self.completed = True
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)


# 测试代码
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    def slow_function(duration):
        """模拟慢速函数"""
        print(f"Starting slow function for {duration} seconds...")
        time.sleep(duration)
        print("Slow function completed")
        return f"Completed after {duration} seconds"
    
    # 测试正常完成
    print("\n测试1: 正常完成")
    try:
        result = run_with_timeout(slow_function, 5, 2)
        print(f"Result: {result}")
    except TimeoutError as e:
        print(f"Timeout: {e}")
    
    # 测试超时终止
    print("\n测试2: 超时终止")
    try:
        result = run_with_timeout(slow_function, 3, 10)
        print(f"Result: {result}")
    except TimeoutError as e:
        print(f"Timeout: {e}")