# 为什么调用一次LLM API要5分钟？

## 1. 看实际的重试代码

```python
# interactive_executor.py 第1178-1216行
max_retries = 5  # 重试5次
for attempt in range(max_retries):
    try:
        # 调用API，设置60秒超时
        response = self.llm_client.chat.completions.create(
            model=api_model_name,
            messages=conversation,
            timeout=60  # 60秒超时
        )
        break  # 成功就跳出
        
    except Exception as e:
        if attempt < max_retries - 1:  # 还有重试机会
            # 计算等待时间（指数退避）
            base_wait = random.uniform(0.5, 1.5)
            wait_time = base_wait * (1.5 ** attempt)
            wait_time = min(wait_time, 10)  # 最多等10秒
            
            print(f"[RETRY] 失败，等待 {wait_time:.1f}秒 后重试...")
            time.sleep(wait_time)
            continue
```

## 2. 时间分解（最坏情况）

### 如果每次都超时：
```
尝试1: 等待API响应60秒（超时） + 休眠1秒    = 61秒
尝试2: 等待API响应60秒（超时） + 休眠1.5秒  = 61.5秒
尝试3: 等待API响应60秒（超时） + 休眠2.25秒 = 62.25秒
尝试4: 等待API响应60秒（超时） + 休眠3.4秒  = 63.4秒
尝试5: 等待API响应60秒（超时） + 不休眠     = 60秒

总计: 61 + 61.5 + 62.25 + 63.4 + 60 = 308.15秒 ≈ 5分钟
```

## 3. 为什么会超时？

### 3.1 网络原因
```
你的请求 → 网络延迟 → Azure/IdealLab服务器 → 网络延迟 → 响应
         ↑                              ↑
      可能10秒                      可能20秒
```

### 3.2 API服务器原因
- **Azure**: 
  - 冷启动（第一次调用需要唤醒实例）
  - 负载高（排队等待）
  - 地理位置远（跨国访问）

- **IdealLab**:
  - 限流（QPS限制）
  - 服务器负载高
  - 模型加载慢

### 3.3 模型本身原因
- **大模型生成慢**:
  - DeepSeek-V3: 671B参数，生成一个token可能需要100ms
  - 生成500个token = 50秒
  - 加上其他开销 → 接近60秒

## 4. 实际案例

### 案例1：网络不稳定
```
[LLM_CALL] Using model: DeepSeek-V3-0324
[LLM_ERROR] Attempt 1/5: Connection timeout
[RETRY] Connection issue, waiting 1.0s before retry...
[LLM_ERROR] Attempt 2/5: Connection timeout  
[RETRY] Connection issue, waiting 1.5s before retry...
[LLM_ERROR] Attempt 3/5: Connection timeout
[RETRY] Connection issue, waiting 2.3s before retry...
[LLM_ERROR] Attempt 4/5: Response timeout (60s)
[RETRY] Connection issue, waiting 3.4s before retry...
[LLM_ERROR] Attempt 5/5: Response timeout (60s)
# 总时间：5分钟+
```

### 案例2：API限流
```
[LLM_CALL] Using model: qwen2.5-7b-instruct
[LLM_ERROR] Attempt 1/5: 429 Too Many Requests (限流)
[RETRY] Rate limited, waiting 1.0s before retry...
[LLM_ERROR] Attempt 2/5: 429 Too Many Requests
[RETRY] Rate limited, waiting 1.5s before retry...
# ... 继续重试 ...
# 总时间：取决于限流解除时间
```

### 案例3：模型响应慢
```
[LLM_CALL] Using model: Llama-3.3-70B-Instruct
# 等待58秒...
[LLM_RESPONSE] 收到响应（接近超时）
# 没有重试，但单次就要1分钟
```

## 5. 为什么不能设置更短的超时？

### 合理的响应时间：
- **小模型（7B）**: 5-10秒
- **中模型（30B）**: 10-20秒  
- **大模型（70B+）**: 20-40秒
- **超大模型（100B+）**: 30-60秒

### 如果超时设置太短（如10秒）：
- 大模型永远超时
- 不断重试反而更慢
- 浪费API调用次数

## 6. 累积效应

### 单个任务的时间：
```
10个turn × 每turn可能重试 = 最坏情况
10 × 5分钟 = 50分钟

即使平均只重试2次：
10 × 2分钟 = 20分钟
```

### 100个任务：
```
最坏：100 × 50分钟 = 5000分钟 ≈ 83小时
平均：100 × 20分钟 = 2000分钟 ≈ 33小时
最好：100 × 5分钟 = 500分钟 ≈ 8小时
```

## 7. 真实的问题

### 不是单次调用5分钟的问题，而是：
1. **没有任务级超时**：单个任务可以跑50分钟
2. **没有智能重试**：盲目重试5次，即使明显会失败
3. **没有熔断机制**：某个API持续失败应该跳过
4. **没有负载均衡**：所有请求打到同一个endpoint

## 解决方案

### 短期：
```python
# 1. 减少重试次数
max_retries = 2  # 不要5次

# 2. 减少单次超时
timeout = 30  # 不要60秒

# 3. 任务级超时
if time.time() - task_start > 300:  # 5分钟
    return {"error": "task timeout"}
```

### 长期：
1. **使用异步调用**：不阻塞等待
2. **智能路由**：失败的API切换到备用
3. **预热缓存**：常用响应缓存
4. **批量请求**：减少调用次数
