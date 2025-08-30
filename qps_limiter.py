#!/usr/bin/env python3
"""
Global QPS Limiter - 全局QPS限制器
在实际API调用时控制请求速率，支持跨进程共享
"""

import time
import threading
from pathlib import Path
import json
import os
from typing import Optional

class QPSLimiter:
    """QPS限制器 - 在实际API调用时控制速率"""
    
    def __init__(self, qps: float = 10.0, provider: str = "default"):
        """
        Args:
            qps: 每秒请求数限制
            provider: API提供商（azure不限制）
        """
        self.qps = qps
        self.provider = provider
        self.min_interval = 0 if provider == "azure" else (1.0 / qps if qps > 0 else 0)
        
        # 线程锁
        self._lock = threading.Lock()
        self._last_request_time = 0
        
        # 共享文件路径（用于跨进程同步）
        self.shared_dir = Path("/tmp/qps_limiter")
        self.shared_dir.mkdir(exist_ok=True)
        self.state_file = self.shared_dir / f"{provider}_qps_state.json"
        
    def acquire(self):
        """获取执行权限，必要时等待"""
        if self.min_interval <= 0:
            # Azure或无限制
            return
            
        with self._lock:
            # 读取共享状态
            last_global_time = self._read_shared_state()
            
            # 使用最新的时间戳（本地或全局）
            last_time = max(self._last_request_time, last_global_time)
            
            # 计算需要等待的时间
            now = time.time()
            time_since_last = now - last_time
            
            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                # print(f"[QPS] 等待 {sleep_time:.3f}秒 (QPS={self.qps})")
                time.sleep(sleep_time)
            
            # 更新时间戳
            self._last_request_time = time.time()
            self._write_shared_state(self._last_request_time)
    
    def _read_shared_state(self) -> float:
        """读取共享的时间戳"""
        try:
            if self.state_file.exists():
                # 检查文件是否太旧（超过10秒认为是过期的）
                mtime = self.state_file.stat().st_mtime
                if time.time() - mtime > 10:
                    return 0
                    
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    return data.get('last_request_time', 0)
        except:
            pass
        return 0
    
    def _write_shared_state(self, timestamp: float):
        """写入共享的时间戳"""
        try:
            data = {
                'last_request_time': timestamp,
                'pid': os.getpid()
            }
            with open(self.state_file, 'w') as f:
                json.dump(data, f)
        except:
            pass

# 全局实例缓存
_limiters = {}

def get_qps_limiter(model: str, qps: Optional[float] = None, key_index: Optional[int] = None) -> QPSLimiter:
    """获取QPS限制器实例
    
    Args:
        model: 模型名称
        qps: QPS限制（如果为None，根据模型自动设置）
        key_index: API key索引（用于多key独立限流）
    
    Returns:
        QPSLimiter实例
    """
    global _limiters
    
    # 判断provider
    if any(x in model.lower() for x in ['deepseek', 'llama', 'gpt']):
        provider = "azure"
    elif "qwen" in model.lower():
        # 提取模型规模标识，避免不同模型冲突
        import re
        match = re.search(r'(\d+b)', model.lower())
        model_size = match.group(1) if match else 'unknown'
        
        # 为每个模型+key组合创建独立的provider标识
        # 这样不同模型不会共享同一个QPS限制器
        if key_index is not None:
            provider = f"ideallab_qwen_{model_size}_key{key_index}"
        else:
            provider = f"ideallab_qwen_{model_size}"
    elif any(x in model.lower() for x in ['o3', 'gemini', 'kimi']):
        # 闭源模型也支持独立key限流
        if key_index is not None:
            provider = f"ideallab_closed_key{key_index}"
        else:
            provider = "ideallab_closed"
    else:
        provider = "default"
    
    # 自动设置QPS
    if qps is None:
        if provider == "azure":
            qps = 0  # 无限制
        elif "ideallab" in provider:  # 包括所有ideallab相关的provider
            # 降低QPS避免限流：考虑到多个模型共享同一API key
            # 如果5个模型并发，每个模型只能用 10/5 = 2 QPS
            qps = 2  # 保守设置，避免服务器端限流
        else:
            qps = 20  # 默认20
    
    # 获取或创建limiter
    key = f"{provider}_{qps}"
    if key not in _limiters:
        _limiters[key] = QPSLimiter(qps, provider)
    
    return _limiters[key]