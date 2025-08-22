#!/usr/bin/env python3
"""
自适应限流管理器 - 动态调整并发和QPS以避免限流
"""

import time
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import deque
from datetime import datetime, timedelta
import logging

@dataclass
class RateLimitStats:
    """限流统计信息"""
    success_count: int = 0
    rate_limit_count: int = 0
    other_error_count: int = 0
    last_rate_limit_time: Optional[datetime] = None
    recent_requests: deque = field(default_factory=lambda: deque(maxlen=100))
    
    @property
    def rate_limit_ratio(self) -> float:
        """计算限流比例"""
        total = self.success_count + self.rate_limit_count + self.other_error_count
        if total == 0:
            return 0
        return self.rate_limit_count / total
    
    @property
    def success_ratio(self) -> float:
        """计算成功比例"""
        total = self.success_count + self.rate_limit_count + self.other_error_count
        if total == 0:
            return 1.0
        return self.success_count / total


class AdaptiveRateLimiter:
    """
    自适应限流器
    - 动态调整并发数和QPS
    - 监控限流情况并自动降速
    - 成功运行后逐步提速
    """
    
    def __init__(
        self,
        initial_workers: int = 5,
        initial_qps: int = 10,
        min_workers: int = 1,
        max_workers: int = 20,
        min_qps: int = 1,
        max_qps: int = 50,
        backoff_factor: float = 0.5,
        recovery_factor: float = 1.2,
        stable_threshold: int = 20,
        logger: Optional[logging.Logger] = None,
        api_provider: str = None
    ):
        """
        初始化自适应限流器
        
        Args:
            initial_workers: 初始并发数
            initial_qps: 初始QPS
            min_workers: 最小并发数
            max_workers: 最大并发数
            min_qps: 最小QPS
            max_qps: 最大QPS
            backoff_factor: 遇到限流时的退避因子 (0.5 = 减半)
            recovery_factor: 成功后的恢复因子 (1.2 = 增加20%)
            stable_threshold: 稳定运行多少次后开始提速
            api_provider: API提供商（如'idealab'，会使用更保守的设置）
        """
        # 根据API提供商调整默认值
        self.api_provider = api_provider
        if api_provider and 'idealab' in api_provider.lower():
            # idealab API适度保守但不要太保守
            initial_workers = min(initial_workers, 5)  # 从2提高到5
            initial_qps = min(initial_qps, 10)  # 从3提高到10
            max_workers = min(max_workers, 15)  # 从5提高到15
            max_qps = min(max_qps, 25)  # 从10提高到25
            backoff_factor = 0.5  # 温和降速
            recovery_factor = 1.5  # 适度提速
            stable_threshold = 10  # 适度稳定后提速
        elif api_provider and 'azure' in api_provider.lower():
            # Azure API可以处理极高并发
            initial_workers = max(initial_workers, 80)  # 起始就用80并发
            initial_qps = max(initial_qps, 150)  # 起始150 QPS
            max_workers = max(max_workers, 150)  # 允许150个并发
            max_qps = max(max_qps, 300)  # 允许300 QPS
            backoff_factor = 0.95  # 几乎不降速（只降5%）
            recovery_factor = 3.0  # 极其激进的提速（三倍）
            stable_threshold = 1  # 立即提速（1次成功就提速）
            
        self.current_workers = initial_workers
        self.current_qps = initial_qps
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.min_qps = min_qps
        self.max_qps = max_qps
        self.backoff_factor = backoff_factor
        self.recovery_factor = recovery_factor
        self.stable_threshold = stable_threshold
        
        self.stats = RateLimitStats()
        self.lock = threading.Lock()
        self.logger = logger or logging.getLogger(__name__)
        
        # 状态追踪
        self.consecutive_successes = 0
        self.consecutive_rate_limits = 0
        self.last_adjustment_time = datetime.now()
        self.adjustment_cooldown = timedelta(seconds=5)  # 更短的调整冷却时间（原10秒）
        
        # 自动恢复机制
        self.last_rate_limit_time = datetime.now()
        self.auto_recovery_interval = timedelta(seconds=30)  # 30秒后自动尝试恢复
        self.recovery_attempts = 0
        
        # 请求间隔控制
        self.last_request_time = 0
        self.request_interval = 1.0 / self.current_qps if self.current_qps > 0 else 0
        
    def record_success(self):
        """记录成功请求"""
        with self.lock:
            self.stats.success_count += 1
            self.stats.recent_requests.append(('success', datetime.now()))
            self.consecutive_successes += 1
            self.consecutive_rate_limits = 0
            
            # 检查是否应该自动恢复（距离上次限流超过30秒）
            now = datetime.now()
            if now - self.last_rate_limit_time > self.auto_recovery_interval:
                if self.current_workers < self.max_workers or self.current_qps < self.max_qps:
                    self._auto_recover()
                    return
            
            # 降低连续成功的要求（原来是stable_threshold，现在减半）
            reduced_threshold = max(3, self.stable_threshold // 2)  # 最少3次成功就可以尝试提速
            if self.consecutive_successes >= reduced_threshold:
                self._try_speed_up()
    
    def record_rate_limit(self, error_msg: str = ""):
        """记录限流错误"""
        with self.lock:
            self.stats.rate_limit_count += 1
            self.stats.last_rate_limit_time = datetime.now()
            self.stats.recent_requests.append(('rate_limit', datetime.now()))
            self.consecutive_rate_limits += 1
            self.consecutive_successes = 0
            
            # 记录限流时间用于自动恢复
            self.last_rate_limit_time = datetime.now()
            self.recovery_attempts = 0  # 重置恢复尝试次数
            
            # 立即降速
            self._slow_down()
            
            self.logger.warning(f"Rate limit hit! Adjusting: workers={self.current_workers}, qps={self.current_qps}")
    
    def record_error(self, error_msg: str = ""):
        """记录其他错误"""
        with self.lock:
            self.stats.other_error_count += 1
            self.stats.recent_requests.append(('error', datetime.now()))
            # 其他错误不影响速度调整
    
    def _slow_down(self):
        """降低速度"""
        now = datetime.now()
        if now - self.last_adjustment_time < self.adjustment_cooldown:
            return  # 冷却期内不调整
        
        # Azure API使用极其温和的降速
        if self.api_provider and 'azure' in self.api_provider.lower():
            factor = 0.95  # Azure只降5%
        else:
            # 其他API的温和降速策略
            if self.consecutive_rate_limits == 1:
                factor = 0.9  # 首次限流，非常温和降速
            elif self.consecutive_rate_limits == 2:
                factor = 0.75  # 第二次，温和降速
            elif self.consecutive_rate_limits == 3:
                factor = 0.6  # 第三次，中等降速
            else:
                factor = max(0.5, self.backoff_factor)  # 多次限流也不要降得太狠
        
        old_workers = self.current_workers
        old_qps = self.current_qps
        
        # 调整并发数和QPS
        self.current_workers = max(
            self.min_workers,
            int(self.current_workers * factor)
        )
        self.current_qps = max(
            self.min_qps,
            int(self.current_qps * factor)
        )
        
        # 更新请求间隔
        self.request_interval = 1.0 / self.current_qps if self.current_qps > 0 else 0
        
        self.last_adjustment_time = now
        self.consecutive_successes = 0
        
        self.logger.info(
            f"Slowing down: workers {old_workers}→{self.current_workers}, "
            f"QPS {old_qps}→{self.current_qps}"
        )
    
    def _try_speed_up(self):
        """尝试提速"""
        now = datetime.now()
        # 缩短冷却时间，允许更频繁的提速
        speed_up_cooldown = timedelta(seconds=3)  # 提速只需要3秒冷却
        if now - self.last_adjustment_time < speed_up_cooldown:
            return
        
        # 降低成功率要求（原0.8，现在0.7）
        if self.stats.success_ratio < 0.7:
            return  # 成功率不够高，不提速
        
        old_workers = self.current_workers
        old_qps = self.current_qps
        
        # 逐步提速
        self.current_workers = min(
            self.max_workers,
            int(self.current_workers * self.recovery_factor)
        )
        self.current_qps = min(
            self.max_qps,
            int(self.current_qps * self.recovery_factor)
        )
        
        # 更新请求间隔
        self.request_interval = 1.0 / self.current_qps if self.current_qps > 0 else 0
        
        self.last_adjustment_time = now
        self.consecutive_successes = 0
        
        self.logger.info(
            f"Speeding up: workers {old_workers}→{self.current_workers}, "
            f"QPS {old_qps}→{self.current_qps}"
        )
    
    def _auto_recover(self):
        """自动恢复机制 - 距离上次限流一段时间后自动尝试恢复"""
        now = datetime.now()
        old_workers = self.current_workers
        old_qps = self.current_qps
        
        # 渐进式恢复
        self.recovery_attempts += 1
        if self.recovery_attempts <= 2:
            # 前两次恢复比较保守
            recovery_factor = 1.2
        else:
            # 之后可以更激进
            recovery_factor = 1.5
        
        # 恢复速度
        self.current_workers = min(
            self.max_workers,
            int(self.current_workers * recovery_factor)
        )
        self.current_qps = min(
            self.max_qps,
            int(self.current_qps * recovery_factor)
        )
        
        # 更新请求间隔
        self.request_interval = 1.0 / self.current_qps if self.current_qps > 0 else 0
        
        self.last_adjustment_time = now
        self.consecutive_successes = 0
        
        self.logger.info(
            f"Auto-recovering after {(now - self.last_rate_limit_time).seconds}s: "
            f"workers {old_workers}→{self.current_workers}, "
            f"QPS {old_qps}→{self.current_qps}"
        )
    
    def wait_if_needed(self):
        """根据QPS限制等待"""
        # Azure API不需要QPS限制
        if self.api_provider and 'azure' in self.api_provider.lower():
            return  # Azure跳过所有等待
        
        if self.request_interval > 0:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.request_interval:
                # 对于高QPS（>50），使用更短的等待
                actual_wait = min(0.02, self.request_interval - time_since_last)  # 最多等20ms
                if actual_wait > 0.001:  # 只有超过1ms才等待
                    time.sleep(actual_wait)
            self.last_request_time = time.time()
    
    def get_current_limits(self) -> Tuple[int, int]:
        """获取当前的限制值"""
        with self.lock:
            return self.current_workers, self.current_qps
    
    def get_stats_summary(self) -> Dict:
        """获取统计摘要"""
        with self.lock:
            return {
                'current_workers': self.current_workers,
                'current_qps': self.current_qps,
                'total_requests': self.stats.success_count + self.stats.rate_limit_count + self.stats.other_error_count,
                'success_count': self.stats.success_count,
                'rate_limit_count': self.stats.rate_limit_count,
                'other_error_count': self.stats.other_error_count,
                'success_ratio': f"{self.stats.success_ratio:.2%}",
                'rate_limit_ratio': f"{self.stats.rate_limit_ratio:.2%}",
                'consecutive_successes': self.consecutive_successes,
                'consecutive_rate_limits': self.consecutive_rate_limits
            }
    
    def should_retry(self, error_msg: str) -> bool:
        """判断是否应该重试"""
        if 'TPM/RPM限流' in error_msg or 'rate limit' in error_msg.lower():
            self.record_rate_limit(error_msg)
            # 限流错误应该等待后重试
            return True
        return False
    
    def get_retry_delay(self) -> float:
        """获取重试延迟（秒）"""
        with self.lock:
            # Azure API使用更短的延迟
            if self.api_provider and 'azure' in self.api_provider.lower():
                return 0.1  # Azure几乎不需要等待
            
            # 其他API的指数退避（更温和）
            base_delay = 0.2  # 基础延迟降到0.2秒
            delay = min(5.0, base_delay * (1.2 ** self.consecutive_rate_limits))  # 最大延迟降到5秒
            return delay


class SmartBatchExecutor:
    """
    智能批量执行器 - 与自适应限流器配合使用
    """
    
    def __init__(self, rate_limiter: AdaptiveRateLimiter):
        self.rate_limiter = rate_limiter
        self.logger = logging.getLogger(__name__)
    
    def execute_with_adaptive_rate(self, tasks: List, execute_fn, **kwargs):
        """
        使用自适应速率执行任务
        
        Args:
            tasks: 任务列表
            execute_fn: 执行函数，接收单个任务作为参数
            **kwargs: 传递给执行函数的额外参数
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import time
        
        completed = 0
        failed = 0
        total = len(tasks)
        
        while completed + failed < total:
            # 获取当前限制
            workers, qps = self.rate_limiter.get_current_limits()
            
            # 计算本批次要执行的任务数
            batch_size = min(workers, total - completed - failed)
            batch_tasks = tasks[completed + failed : completed + failed + batch_size]
            
            self.logger.info(
                f"Executing batch: {batch_size} tasks with {workers} workers, "
                f"QPS limit: {qps}, Progress: {completed + failed}/{total}"
            )
            
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = []
                for task in batch_tasks:
                    # QPS限制
                    self.rate_limiter.wait_if_needed()
                    future = executor.submit(self._execute_single_task, task, execute_fn, **kwargs)
                    futures.append((future, task))
                
                # 处理结果
                for future, task in futures:
                    try:
                        # 根据任务模型调整超时时间
                        task_timeout = 60  # 默认超时
                        if hasattr(task, 'model'):
                            if 'DeepSeek' in task.model or 'deepseek' in task.model.lower():
                                task_timeout = 180  # DeepSeek需要3分钟
                            elif 'Llama-3.3' in task.model or 'llama-3.3' in task.model.lower():
                                task_timeout = 120  # Llama-3.3需要2分钟
                            elif 'qwen' in task.model.lower() or 'llama-4-scout' in task.model.lower():
                                task_timeout = 90  # idealab API需要1.5分钟
                        elif hasattr(task, 'timeout'):
                            task_timeout = task.timeout
                        
                        result = future.result(timeout=task_timeout)
                        if result['success']:
                            self.rate_limiter.record_success()
                            completed += 1
                        else:
                            if self.rate_limiter.should_retry(result.get('error', '')):
                                # 需要重试的任务重新加入队列
                                tasks.append(task)
                                total += 1
                                time.sleep(self.rate_limiter.get_retry_delay())
                            else:
                                self.rate_limiter.record_error(result.get('error', ''))
                                failed += 1
                    except Exception as e:
                        self.logger.error(f"Task execution failed: {e}")
                        self.rate_limiter.record_error(str(e))
                        failed += 1
            
            # 打印当前统计
            stats = self.rate_limiter.get_stats_summary()
            self.logger.info(f"Current stats: {stats}")
            
            # 如果连续限流太多次，增加等待时间（更智能）
            if self.rate_limiter.consecutive_rate_limits > 10:  # 提高阈值
                # Azure API几乎不需要等待
                if self.rate_limiter.api_provider and 'azure' in self.rate_limiter.api_provider.lower():
                    wait_time = 0.1  # Azure只等100ms
                else:
                    wait_time = min(2.0, self.rate_limiter.get_retry_delay())  # 其他最多2秒
                if wait_time > 0:
                    self.logger.warning(f"Too many rate limits ({self.rate_limiter.consecutive_rate_limits}), waiting {wait_time:.1f}s...")
                    time.sleep(wait_time)
        
        return completed, failed
    
    def _execute_single_task(self, task, execute_fn, **kwargs):
        """执行单个任务"""
        try:
            result = execute_fn(task, **kwargs)
            return {'success': True, 'result': result}
        except Exception as e:
            error_msg = str(e)
            return {'success': False, 'error': error_msg}


# 使用示例
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # 创建自适应限流器
    limiter = AdaptiveRateLimiter(
        initial_workers=3,  # 保守的初始值
        initial_qps=5,
        min_workers=1,
        max_workers=10,
        min_qps=1,
        max_qps=20
    )
    
    # 模拟任务执行
    def mock_task(task_id):
        import random
        if random.random() < 0.1:  # 10%概率触发限流
            raise Exception("TPM/RPM限流")
        return f"Task {task_id} completed"
    
    # 创建执行器
    executor = SmartBatchExecutor(limiter)
    
    # 执行任务
    tasks = list(range(100))
    completed, failed = executor.execute_with_adaptive_rate(
        tasks,
        mock_task
    )
    
    print(f"Completed: {completed}, Failed: {failed}")
    print(f"Final stats: {limiter.get_stats_summary()}")