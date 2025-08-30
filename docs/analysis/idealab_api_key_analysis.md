# IdealLab API Key 轮换机制分析报告

生成时间: 2025-08-19 18:15
调查者: Claude Assistant

## 🔍 调查背景

用户反馈："运行开源模型qwen使用idealab测试时，没有使用备用的api key"

## ✅ 调查结果：API Key轮换机制正常工作

### 1. API Key池配置
系统配置了3个IdealLab API keys：
- Key 0: 956c41bd...f4bb
- Key 1: 3d906058...e77b  
- Key 2: 88a9a901...c3b9

### 2. Key分配策略
```python
_prompt_key_strategy = {
    'baseline': 0,  # 固定使用Key 0
    'cot': 1,       # 固定使用Key 1
    'optimal': 2,   # 固定使用Key 2
    'flawed': -1    # 轮询使用所有keys
}
```

### 3. 测试验证结果
运行`test_idealab_key_rotation.py`测试显示：
- ✅ baseline → Key 0 (正确)
- ✅ cot → Key 1 (正确)
- ✅ optimal → Key 2 (正确)
- ✅ flawed类型轮询使用3个keys (正确)

### 4. 调用链路分析
```
ultra_parallel_runner.py
    ↓ (传递prompt_types)
smart_batch_runner.py
    ↓ (创建TestTask，每个包含prompt_type)
batch_test_runner.py
    ↓ (传递prompt_type到InteractiveExecutor)
interactive_executor.py
    ↓ (调用get_client_for_model(model, prompt_type))
api_client_manager.py
    ↓ (_select_idealab_key(prompt_type))
返回对应的API key
```

## ⚠️ 发现的问题

### 问题1：并发受限
**现状**: max_workers=1导致串行执行
- 当前为了避免单个API key并发问题，设置了max_workers=1
- 这导致即使有3个API keys，也无法并行执行

**影响**: 
- 测试速度慢
- 没有充分利用3个API keys的并发能力

### 问题2：未实现真正的Key池并发
**期望行为**:
- 3个API keys应该能同时处理3个并发请求
- 当一个key繁忙时，自动使用下一个可用的key

**实际行为**:
- 每个prompt_type固定映射到一个key
- 没有根据key的繁忙状态动态分配

## 💡 优化建议

### 方案1：智能并发管理（推荐）
```python
# 在ultra_parallel_runner.py中
if instance.model_family == "qwen":
    # 根据prompt_type数量动态设置workers
    prompt_types = shard.prompt_types.split(",")
    unique_keys = set()
    for pt in prompt_types:
        if pt == 'baseline': unique_keys.add(0)
        elif pt == 'cot': unique_keys.add(1)
        elif pt == 'optimal': unique_keys.add(2)
        else: unique_keys.add(-1)  # flawed类型
    
    # 最多使用的key数量
    max_workers = min(3, len(unique_keys))
```

### 方案2：动态Key池管理
实现一个KeyPool类，维护每个key的状态：
- 空闲/繁忙状态
- 当前并发数
- 请求队列

### 方案3：分批并发
将不同prompt_type的测试分成3批：
- 批次1: baseline测试 (使用Key 0)
- 批次2: cot测试 (使用Key 1)
- 批次3: optimal测试 (使用Key 2)
每批内部可以并发执行

## 📊 结论

1. **API key轮换机制本身工作正常** - 不同的prompt_type确实使用了不同的API key
2. **并发策略需要优化** - 当前的max_workers=1限制了并发能力
3. **建议实施智能并发管理** - 充分利用3个API keys的并发潜力

## 🚀 下一步行动

1. [ ] 实现智能并发管理方案
2. [ ] 测试并发执行的稳定性
3. [ ] 监控API key使用率和错误率
4. [ ] 根据实际运行情况调整并发参数

---
*注：本报告基于代码分析和实际测试验证*