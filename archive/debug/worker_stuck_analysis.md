# Worker卡死问题的完整分析

## Azure确实有100个worker，但为什么还是慢？

### 1. 超时机制失效（关键问题！）

```python
# batch_test_runner.py 第1530行
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(timeout)
```

**问题：signal.SIGALRM只能在主线程中使用！**
- ThreadPoolExecutor的worker线程中无法使用signal
- 超时机制完全失效
- 每个worker可能永远卡住

### 2. Worker卡死的连锁反应

```
初始状态：100个worker可用
↓
第1个任务：LLM搜索循环 → worker 1卡住（超时失效）
第2个任务：正常执行 → worker 2完成
第3个任务：LLM搜索循环 → worker 3卡住
...
第50个任务：LLM搜索循环 → worker 50卡住
↓
结果：50个worker永久卡死，只剩50个在工作
↓
随着时间推移，越来越多worker卡死
↓
最终：可能只剩几个worker在工作
```

### 3. 为什么worker会卡死？

#### 3.1 InteractiveExecutor没有超时
```python
# interactive_executor.py
def execute_interactive(self, initial_prompt, task_instance, workflow, prompt_type):
    for turn in range(self.max_turns):  # 10个turn
        response = self._get_llm_response(conversation, state)
        # 没有任何超时检查！
```

#### 3.2 LLM API调用的超时不够
```python
# 单个API调用60秒超时
response = self.llm_client.chat.completions.create(**params, timeout=60)
# 但10个turn = 10 × 60秒 = 600秒 = 10分钟
```

#### 3.3 无限搜索循环
```python
if search_queries:
    # 处理搜索
    continue  # 不计入失败，继续下一轮
```

### 4. 具体时间线分析

假设Azure配置：100个worker，100个任务（20 prompts × 5 instances）

**理想情况：**
- 100个worker同时启动
- 每个任务2-3分钟
- 总时间：2-3分钟（完全并行）

**实际情况：**
```
0分钟：100个worker开始，100个任务并行
5分钟：30个任务完成，70个还在运行
10分钟：20个worker卡在搜索循环（超时失效）
15分钟：又有20个worker卡住
30分钟：60个worker卡死，只剩40个在工作
1小时：80个worker卡死，只剩20个在工作
2小时：90个worker卡死，只剩10个在工作
...
8小时：几乎所有worker都卡死或在等待
```

### 5. 为什么数据也没保存？

**双重打击：**
1. **Worker卡死** → 任务永不完成
2. **Checkpoint机制** → 需要N个任务完成才保存
3. **结果** → 大量worker卡死，完成的任务不够触发checkpoint

### 6. 验证方法

```bash
# 监控进程状态
ps aux | grep python | grep smart_batch | wc -l
# 如果看到100+个python进程，说明worker确实启动了

# 查看线程状态
lsof -p <PID> | grep -c "ESTABLISHED"
# 看有多少活跃连接

# 查看CPU使用
top -p <PID>
# 如果CPU接近0%，说明在等待（卡死）
```

## 根本原因总结

### 三重故障导致灾难：

1. **超时机制失效**
   - signal.SIGALRM在线程中不工作
   - 单个任务可以无限运行

2. **LLM搜索循环**
   - 模型不理解任务
   - 陷入无限搜索
   - 每个worker被永久占用

3. **级联失效**
   - 越来越多worker卡死
   - 有效并发度急剧下降
   - 从100并发降到个位数

### 为什么看起来像"卡死8小时"？

- 不是真的卡死，而是：
  - 大部分worker被无效任务占用
  - 少数worker在慢慢执行
  - 进度极其缓慢
  - 数据因checkpoint机制无法保存

## 解决方案

### 立即修复：
1. **使用threading.Timer代替signal**
```python
import threading
timer = threading.Timer(timeout, timeout_callback)
timer.start()
try:
    result = execute_test()
finally:
    timer.cancel()
```

2. **在execute_interactive添加超时**
```python
def execute_interactive(self, ..., timeout=300):
    start_time = time.time()
    for turn in range(self.max_turns):
        if time.time() - start_time > timeout:
            break
```

3. **检测搜索循环**
```python
if consecutive_searches > 3:
    break  # 终止无效循环
```

### 长期优化：
1. 使用asyncio代替ThreadPoolExecutor
2. 实现真正的超时机制
3. 添加worker健康检查
4. 自动重启卡死的worker
