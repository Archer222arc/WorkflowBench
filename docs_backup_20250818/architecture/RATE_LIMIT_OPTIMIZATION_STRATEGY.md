# 批量测试速率限制优化策略

## 核心发现

速率限制是**API提供商级别**的，不是模型级别的！

### API提供商分布

| 提供商 | 模型数量 | 模型列表 |
|--------|----------|----------|
| **azure** | 1 | gpt-4o-mini |
| **user_azure** | 1 | gpt-5-nano |
| **idealab** | 21+ | 所有Qwen系列、DeepSeek系列、Claude系列、Gemini系列等 |

## 优化策略

### 1. 并行策略（推荐）

```python
# 伪代码示例
def run_parallel_tests():
    # 创建3个并行任务组（每个API提供商一个）
    with ThreadPoolExecutor(max_workers=3) as provider_executor:
        futures = []
        
        # Azure组
        azure_future = provider_executor.submit(
            test_models, ['gpt-4o-mini'], max_parallel=5
        )
        
        # User Azure组  
        user_azure_future = provider_executor.submit(
            test_models, ['gpt-5-nano'], max_parallel=5
        )
        
        # IdealLab组（注意：这些模型共享速率限制）
        idealab_future = provider_executor.submit(
            test_models_sequential,  # 串行或限制并发
            ['qwen2.5-3b', 'qwen2.5-7b', 'DeepSeek-V3']
        )
```

### 2. 具体优化建议

#### A. 跨提供商并行（最大化吞吐量）
- ✅ 可以同时测试：gpt-4o-mini + gpt-5-nano + 一个IdealLab模型
- 预期加速：3x

#### B. 单提供商内的处理
- **Azure/User Azure**：可以使用5-10个并发连接
- **IdealLab**：建议串行或限制为2-3个并发（因为有20+个模型共享限制）

#### C. 批量测试优化流程

```
1. 将所有模型按提供商分组
2. 为每个提供商创建独立的任务队列
3. 并行执行不同提供商的队列
4. IdealLab队列内部使用较低的并发度
```

### 3. 测试时间估算

假设每个测试需要10秒：

**优化前（串行）**：
- 23个模型 × 100个测试 × 10秒 = 23,000秒 ≈ 6.4小时

**优化后（智能并行）**：
- Azure: 100个测试 ÷ 5并发 × 10秒 = 200秒
- User Azure: 100个测试 ÷ 5并发 × 10秒 = 200秒  
- IdealLab: 21模型 × 100测试 ÷ 2并发 × 10秒 = 10,500秒 ≈ 2.9小时
- **总时间：约2.9小时（节省54%时间）**

### 4. 实现建议

#### 修改 smart_batch_runner.py

```python
class SmartBatchRunner:
    def __init__(self):
        # 定义提供商配置
        self.provider_config = {
            'azure': {
                'models': ['gpt-4o-mini'],
                'max_parallel': 5,
                'qps_limit': 10
            },
            'user_azure': {
                'models': ['gpt-5-nano'],
                'max_parallel': 5,
                'qps_limit': 10
            },
            'idealab': {
                'models': [...],  # 所有IdealLab模型
                'max_parallel': 2,  # 限制并发
                'qps_limit': 5
            }
        }
    
    def run_batch_optimized(self, models, tests):
        # 按提供商分组
        provider_groups = self.group_by_provider(models)
        
        # 并行运行不同提供商
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for provider, model_list in provider_groups.items():
                config = self.provider_config[provider]
                future = executor.submit(
                    self.run_provider_tests,
                    model_list,
                    tests,
                    config['max_parallel']
                )
                futures.append(future)
```

### 5. 监控和调优

建议添加以下监控：

1. **实时QPS监控**：记录每个提供商的实际QPS
2. **错误率监控**：如果某个提供商错误率上升，动态降低并发
3. **自适应并发**：根据成功率自动调整并发数

### 6. 紧急情况处理

如果IdealLab速率限制更严格：
- 将IdealLab模型分批，每批5个模型
- 批次之间休息30秒
- 使用更激进的重试策略

## 总结

1. **速率限制是API提供商级别的**，不是模型级别
2. **最优策略**：按提供商分组，跨提供商并行，提供商内控制并发
3. **预期效果**：可以将6.4小时的测试缩短到2.9小时
4. **关键点**：IdealLab的20+个模型共享速率限制，需要特别处理

---

**生成时间**: 2025-08-13 18:10
**测试环境**: Azure OpenAI + IdealLab API