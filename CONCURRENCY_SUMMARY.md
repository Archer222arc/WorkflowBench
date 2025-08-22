# 🚀 并发优化策略总结

生成时间: 2025-08-19 19:50
作者: Claude Assistant

## 📊 并发层级概览

系统实现了多层级的并发优化，从API提供商级别到具体的任务分片级别：

```
Level 1: API提供商并发 (Azure vs IdealLab)
    ├── Level 2: 模型实例并发 (多个deployment)
    │   ├── Level 3: API Key并发 (IdealLab的3个keys)
    │   │   └── Level 4: Worker并发 (每个实例的max_workers)
    │   └── Level 4: Worker并发 (Azure的高并发)
    └── Level 2: 跨模型并发 (不同模型同时测试)
```

## 1️⃣ Azure开源模型并发策略

### 1.1 DeepSeek系列（6个实例）
```python
# DeepSeek-V3-0324
- DeepSeek-V3-0324    (主实例)
- DeepSeek-V3-0324-2  (并行实例)
- DeepSeek-V3-0324-3  (并行实例)

# DeepSeek-R1-0528
- DeepSeek-R1-0528    (主实例)
- DeepSeek-R1-0528-2  (并行实例)
- DeepSeek-R1-0528-3  (并行实例)
```

**并发配置**:
- 每个实例: max_workers=100, QPS=200
- 总并发能力: 3个实例 × 100 workers = **300并发**
- 策略: 任务分片到3个实例并行执行

### 1.2 Llama系列（3个实例）
```python
# Llama-3.3-70B-Instruct
- Llama-3.3-70B-Instruct    (主实例)
- Llama-3.3-70B-Instruct-2  (并行实例)
- Llama-3.3-70B-Instruct-3  (并行实例)
```

**并发配置**:
- 每个实例: max_workers=100, QPS=200
- 总并发能力: 3个实例 × 100 workers = **300并发**

## 2️⃣ IdealLab开源模型并发策略（qwen系列）

### 2.1 虚拟实例机制
```python
# 3个虚拟实例对应3个API keys
- qwen-key0  (API Key 0)
- qwen-key1  (API Key 1)
- qwen-key2  (API Key 2)
```

### 2.2 统一分片策略（最终简化版）

#### 所有场景统一处理
```
均匀分配策略:
- 所有任务均匀分配到3个keys
- 不管是什么场景（5.1/5.2/5.3/5.4/5.5）
- 每个key负责1/3的任务量
效果: 极致简化，3倍并发提升
```

具体应用：
- **5.1/5.2基准测试**：optimal任务 → 均匀分配
- **5.3缺陷测试**：7个flawed → 均匀分配
- **5.4工具可靠性**：不同rate → 均匀分配（rate层次串行）
- **5.5提示敏感性**：baseline/cot/optimal → 均匀分配

**并发配置**:
- 每个key: max_workers=3-5（自适应模式5，固定模式3）
- 总并发能力: 3个keys × 5 workers = **15并发**
- 特性: 不同模型间速率独立，可同时测试多个qwen模型

## 3️⃣ Azure闭源模型并发策略

### 3.1 支持的模型
- gpt-4o-mini
- gpt-5-mini

**并发配置**:
- 单deployment策略：虽然只有1个实例，但支持高并发
- max_workers=200（自适应模式）
- 多prompt并发：如果有N个prompt types，workers = 200 × N
- 例如：3个prompt types = 600个workers

## 4️⃣ IdealLab闭源模型并发策略

### 4.1 支持的模型
- o3-0416-global
- gemini-2.5-flash-06-17
- kimi-k2
- claude_sonnet4

**并发配置**:
- 单API Key限制：只能使用1个key
- max_workers=1（保守设置避免限流）
- QPS=5-10
- 策略：串行执行，稳定性优先

## 5️⃣ 多层级并发示例

### 完整的并发执行流程
```
ultra_parallel_runner.py
├── 检测模型类型
├── 创建任务分片
│   ├── Azure开源: 分3个实例
│   ├── IdealLab开源(qwen): 智能分配到3个keys
│   ├── Azure闭源: 单实例高并发
│   └── IdealLab闭源: 单实例保守并发
└── 并行执行所有分片
    ├── 分片1 → smart_batch_runner → batch_test_runner
    ├── 分片2 → smart_batch_runner → batch_test_runner
    └── 分片3 → smart_batch_runner → batch_test_runner
```

## 6️⃣ 并发性能对比

| 模型类型 | 实例/Keys | Workers/实例 | 总并发 | 优化效果 |
|---------|-----------|--------------|--------|----------|
| **Azure开源** | 3个实例 | 100 | 300 | 3倍提升 |
| **IdealLab开源(qwen)** | 3个keys | 5 | 15 | 3倍提升 |
| **Azure闭源** | 1个实例 | 200+ | 200-600 | 超高并发 |
| **IdealLab闭源** | 1个key | 1 | 1 | 稳定优先 |

## 7️⃣ 特殊优化技巧

### 7.1 错开启动策略
避免workflow生成冲突：
- 第1个分片：立即启动
- 第2个分片：延迟30秒
- 第3个分片：延迟20秒

### 7.2 Prompt并发倍增
对于多prompt场景：
```python
if prompt_count > 1:
    max_workers = base_workers * prompt_count
    # 例如: 3个prompts × 100 base = 300 workers
```

### 7.3 自适应速率控制
- adaptive模式：动态调整QPS，无上限
- fixed模式：固定QPS，保守策略

## 8️⃣ 环境变量控制

```bash
# 选择速率模式
export RATE_MODE=adaptive  # 或 fixed

# 选择存储格式
export STORAGE_FORMAT=parquet  # 或 json

# 调试特定进程
export DEBUG_LOG=true
export DEBUG_PROCESS_NUM=1
```

## 9️⃣ 命令行示例

### 基础测试（自动并发）
```bash
python ultra_parallel_runner.py \
  --model qwen2.5-72b-instruct \
  --prompt-types optimal \
  --num-instances 60 \
  --rate-mode adaptive
```

### 5.4场景（工具可靠性测试）
```bash
# 每个rate均匀使用3个keys（与5.1/5.2相同）
python ultra_parallel_runner.py \
  --model qwen2.5-72b-instruct \
  --prompt-types optimal \
  --tool-success-rate 0.9  # 均匀分配到3个keys
```

### 5.3场景（flawed测试）
```bash
# 自动分配到3个keys
python ultra_parallel_runner.py \
  --model qwen2.5-72b-instruct \
  --prompt-types flawed_sequence_disorder,flawed_tool_misuse,flawed_parameter_error
```

## 🎯 总结

系统实现了**4个层级**的并发优化：

1. **API提供商级**：Azure和IdealLab并行
2. **模型实例级**：多deployment/多key并行
3. **任务分片级**：智能分配策略
4. **Worker级**：每个实例的并发workers

**关键成果**：
- Azure开源模型：3倍提升（利用3个deployments）
- IdealLab开源模型(qwen)：3倍提升（利用3个API keys）
- Azure闭源模型：超高并发（单实例200+ workers）
- IdealLab闭源模型：稳定执行（单key限制）

**智能优化**：
- 5.1-5.5所有场景都有专门的优化策略
- 避免资源浪费和key拥堵
- 最大化利用可用资源

---
文档版本: 1.0.0
最后更新: 2025-08-19 19:50