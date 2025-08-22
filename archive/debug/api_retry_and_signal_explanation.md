# API重试时间和Signal机制详解

## 1. API重试为什么可能需要3分钟？

### 看看实际的重试代码：
```python
# interactive_executor.py 第1178-1216行
max_retries = 5  # 重试5次
for attempt in range(max_retries):
    try:
        response = self.llm_client.chat.completions.create(**params, timeout=60)
        break  # 成功则跳出
    except Exception as e:
        if attempt < max_retries - 1:
            # 指数退避
            base_wait = random.uniform(0.5, 1.5)
            wait_time = base_wait * (1.5 ** attempt)
            wait_time = min(wait_time, 10)
            time.sleep(wait_time)
```

### 时间计算：
```
第1次尝试：60秒（超时） + 等待0.5-1.5秒
第2次尝试：60秒（超时） + 等待0.75-2.25秒  
第3次尝试：60秒（超时） + 等待1.125-3.375秒
第4次尝试：60秒（超时） + 等待1.69-5.06秒
第5次尝试：60秒（超时） + 无需等待

总计：
- API调用：5 × 60秒 = 300秒
- 等待时间：约10-15秒
- 总时间：约315秒 ≈ 5分钟！
```

**但这只是一个API调用！如果一个turn需要多次调用，时间更长。**

## 2. signal.SIGALRM只能在主线程用是什么意思？

### 2.1 什么是signal.SIGALRM？

signal.SIGALRM是Unix/Linux系统的一个信号机制，用于设置定时器：

```python
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("超时了！")

# 设置信号处理器
signal.signal(signal.SIGALRM, timeout_handler)
# 设置5秒后发送SIGALRM信号
signal.alarm(5)

# 执行某个可能很慢的操作
slow_operation()  # 如果超过5秒，会触发TimeoutError
```

### 2.2 为什么只能在主线程用？

**Python的限制：**
```python
# 主线程中 - 工作正常
def main():
    signal.signal(signal.SIGALRM, handler)  # ✅ 可以设置
    signal.alarm(5)  # ✅ 会触发
    
# Worker线程中 - 不工作
def worker_thread():
    signal.signal(signal.SIGALRM, handler)  # ❌ 报错！
    # ValueError: signal only works in main thread
```

### 2.3 实际代码中的问题

```python
# batch_test_runner.py 使用ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=100) as executor:
    for task in tasks:
        future = executor.submit(self._run_single_test_safe, task)
        
# _run_single_test_safe 在worker线程中执行
def _run_single_test_safe(self, task):
    # 这段代码在worker线程中运行！
    signal.signal(signal.SIGALRM, timeout_handler)  # ❌ 这里会失败！
    signal.alarm(timeout)  # ❌ 即使不报错，也不会触发！
```

### 2.4 具体表现

```python
# 期望的行为：
任务运行 → 60秒后 → SIGALRM信号 → 触发超时 → 任务终止

# 实际的行为：
任务运行 → 60秒后 → （没有信号） → 继续运行 → 永远不超时
```

## 3. 为什么这很致命？

### 场景演示：

```
主线程：创建100个worker
Worker 1：执行任务A
  → signal.alarm(60) # 设置了但不会触发
  → LLM API调用（可能5分钟）
  → 再调用9次（可能50分钟）
  → 永远不会超时终止

Worker 2：执行任务B
  → 同样的问题
  
...

Worker 100：执行任务Z
  → 同样的问题
```

**结果：**
- 所有worker都可能被慢任务占用
- 没有任何超时保护
- 看起来像"卡死"

## 4. 正确的解决方案

### 方案1：使用threading.Timer（线程安全）
```python
import threading

def timeout_callback():
    # 标记超时，但不能直接终止线程
    task.timed_out = True

timer = threading.Timer(60, timeout_callback)
timer.start()
try:
    result = run_task()
finally:
    timer.cancel()
```

### 方案2：使用concurrent.futures的timeout
```python
future = executor.submit(task)
try:
    result = future.result(timeout=60)  # 这个timeout是有效的
except TimeoutError:
    future.cancel()  # 尝试取消（但可能取消不了）
```

### 方案3：在任务内部检查时间
```python
def execute_interactive(self, timeout=300):
    start_time = time.time()
    for turn in range(10):
        if time.time() - start_time > timeout:
            return {"error": "timeout"}
        # 执行任务...
```

## 5. 总结

### API重试3分钟的原因：
- 每次尝试60秒超时
- 重试5次 = 5 × 60秒 = 300秒
- 加上等待时间 ≈ 5分钟
- 这只是一个API调用，10个turn可能50分钟

### signal.SIGALRM失效的原因：
- Python限制：信号只能在主线程设置和接收
- ThreadPoolExecutor的任务在worker线程执行
- 结果：超时机制完全失效
- 任务可以无限运行，worker被永久占用

### 致命组合：
1. 任务可能需要50分钟（API重试）
2. 没有超时保护（signal失效）
3. Worker被占用，无法处理新任务
4. 100个worker逐渐都被占用
5. 系统看起来"卡死"8小时
