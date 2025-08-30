# 超并发模式(Ultra-Parallel Mode)详细分析

## 🔥 超并发模式概述

当启用超并发模式（`--ultra-parallel`）时，系统会最大化利用所有可用资源：

### 可用资源池
- **Azure DeepSeek-V3**：3个实例（DeepSeek-V3-0324, -2, -3）
- **Azure DeepSeek-R1**：3个实例（DeepSeek-R1-0528, -2, -3）  
- **Azure Llama-3.3**：3个实例（Llama-3.3-70B-Instruct, -2, -3）
- **IdealLab Qwen**：2个API keys（key0, key1）- 注意第3个key不可用
- **Azure闭源模型**：单实例高并发（gpt-4o-mini, gpt-5-mini）
- **IdealLab闭源模型**：单实例低并发（o3, gemini, kimi, claude）

### 并发参数（根据修改后的代码）
- **Azure开源模型**：每个实例100 workers，200 QPS
- **IdealLab Qwen**：每个key 1 worker，5 QPS（非常保守）
- **Azure闭源模型**：200 workers，400 QPS  
- **IdealLab闭源模型**：1 worker，5 QPS

---

## Phase 5.1 - 基准测试（超并发模式）

### 执行模式
- 每个模型仍然**串行执行**（一个模型完成后才开始下一个）
- 但每个模型内部使用超并发

### Azure模型（DeepSeek/Llama）
```
DeepSeek-V3-0324:
  → 创建3个分片
  → 分片1: DeepSeek-V3-0324 (100 workers)
  → 分片2: DeepSeek-V3-0324-2 (100 workers)  
  → 分片3: DeepSeek-V3-0324-3 (100 workers)
  总计：300个并发workers
```

### Qwen模型（修改后）
```
qwen2.5-72b-instruct:
  → 创建1个分片（API Key轮换策略）
  → 使用key0，1个worker
  总计：1个worker（极度保守）
  
qwen2.5-32b-instruct:
  → 创建1个分片
  → 使用key1，1个worker  
  总计：1个worker
```

### 问题：Qwen超并发模式实际没有并发
由于`max_workers=1`的限制，即使开启超并发，qwen模型仍然是单线程执行

---

## Phase 5.2 - Qwen规模效应（超并发模式）

### 执行模式
- 10个进程同时运行（5个模型 × 2个难度）
- 每个进程之间15秒延迟启动

### 实际并发情况（基于修改后的代码）
```
时间轴：
T+0s:  72b(very_easy) 启动 → key0, 1 worker
T+15s: 32b(very_easy) 启动 → key1, 1 worker
T+30s: 14b(very_easy) 启动 → key2, 1 worker
T+45s: 7b(very_easy) 启动 → key0, 1 worker（与72b共享）
T+60s: 3b(very_easy) 启动 → key1, 1 worker（与32b共享）
T+75s: 72b(medium) 启动 → key0, 1 worker
T+90s: 32b(medium) 启动 → key1, 1 worker
T+105s: 14b(medium) 启动 → key2, 1 worker
T+120s: 7b(medium) 启动 → key0, 1 worker
T+135s: 3b(medium) 启动 → key1, 1 worker
```

### Key负载分析
```
key0: 最多4个进程，但每个只有1 worker = 4 QPS
key1: 最多4个进程，但每个只有1 worker = 4 QPS
key2: 最多2个进程，但每个只有1 worker = 2 QPS
```

即使在超并发模式下，由于worker限制，实际QPS很低

---

## Phase 5.3 - 缺陷工作流（超并发模式）

### 执行模式
- 模型串行，但qwen模型的3个缺陷组会并发

### Azure模型
```
DeepSeek-V3-0324处理缺陷时：
  → 3个缺陷组串行执行（非qwen模型）
  → 每组使用3个实例并发
  → 总计300 workers处理每个缺陷组
```

### Qwen模型（问题！）
```
qwen2.5-72b处理缺陷时：
  → 3个缺陷组并发执行
  → 所有3个组都使用key0（根据轮换策略）
  → 每组1 worker
  总计：3个进程共享key0，3 QPS
```

问题：一个模型的3个缺陷组都用同一个key

---

## Phase 5.4 & 5.5 - 工具可靠性/提示敏感性（超并发模式）

### 执行模式
- 完全串行，无模型间并发
- 每个模型内部使用超并发

### Azure模型
- 每个测试使用3个实例，300 workers

### Qwen模型  
- 每个测试1个分片，1 worker（无实际并发）

---

## 🚨 超并发模式的关键问题

### 1. **Qwen模型没有真正的超并发**
```python
max_workers=1  # 强制限制为1，忽略用户设置
```
即使开启超并发模式，qwen仍然是单线程

### 2. **Phase 5.2的并发冲突**
- 10个进程同时运行
- key0和key1各被4个进程使用
- 虽然每个进程只有1 worker，但仍可能触发限流

### 3. **Phase 5.3的key共享问题**  
- 一个模型的3个缺陷组都用同一个key
- 导致瞬时QPS增加3倍

### 4. **Azure模型的资源浪费**
- 300 workers可能过度并发
- 可能导致API限流或系统资源耗尽

---

## 📊 建议优化

### 1. **放宽Qwen的worker限制**
```python
# 建议修改为
max_workers = 3  # 允许适度并发，但不要太高
```

### 2. **优化5.2的执行策略**
- 改为真正的串行执行
- 或限制同时运行的模型数量

### 3. **修复5.3的key分配**
- 让一个模型的不同缺陷组使用不同的key
- 或让缺陷组串行执行

### 4. **动态调整Azure并发**
- 根据实际响应时间动态调整workers
- 避免过度并发导致的问题