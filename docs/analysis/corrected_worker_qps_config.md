# Ultra并发Worker和QPS配置修正总结

## ✅ **修正内容**

### **1. 统一非自适应模式Worker数配置**

| API类型 | 修正前 | 修正后 | 修正位置 |
|---------|--------|--------|----------|
| **Azure开源** | smart_batch_runner.py: 100 | **50** | smart_batch_runner.py:378 |
| **IdealLab开源** | ultra_parallel_runner.py: 3 | **2** | ultra_parallel_runner.py:337 |

### **2. 移除所有QPS上限限制**

所有API类型的QPS设置统一改为 `None`（无限制）:

#### **ultra_parallel_runner.py 修正**:
```python
# 修正前有各种QPS限制：
qps = 10, qps = 5, qps = 100, qps = 200, etc.

# 修正后全部移除：
qps = None  # 移除QPS限制
```

#### **smart_batch_runner.py 修正**:
```python  
# 修正前：
qps = 5.0, qps = 10.0, qps = 200.0

# 修正后：
qps = None  # 移除QPS限制
```

## 🎯 **修正后的完整配置表**

### **ultra_parallel_runner.py 配置**

| 模型类型 | 模式 | Workers | QPS | 备注 |
|---------|------|---------|-----|------|
| **Qwen (IdealLab开源)** | Fixed | 2 | None | ✅ 修正：3→2 |
| **Qwen (IdealLab开源)** | Adaptive | 1 | None | 保持不变 |
| **Azure开源** | Fixed | 50 | None | ✅ 已正确 |
| **Azure开源** | Adaptive | 100 | None | 保持不变 |
| **Azure闭源** | Fixed | 100 | None | ✅ 移除QPS限制 |
| **Azure闭源** | Adaptive | 200 | None | 保持不变 |
| **IdealLab闭源** | Fixed | 1 | None | ✅ 移除QPS限制 |
| **IdealLab闭源** | Adaptive | 1 | None | 保持不变 |

### **smart_batch_runner.py 配置**

| 模型类型 | 模式 | Workers | QPS | 备注 |
|---------|------|---------|-----|------|
| **IdealLab API** | Adaptive | 5 | None | ✅ 移除QPS限制 |
| **IdealLab API** | Fixed | 2 | None | ✅ 移除QPS限制 |
| **Azure API** | Adaptive | 100 | None | ✅ 移除QPS限制 |
| **Azure API** | Fixed | 50 | None | ✅ 修正：100→50 |

## 📊 **修正后的实际并发数**

### **非自适应模式（Fixed Mode）总并发**:

#### **Azure开源模型** (DeepSeek-V3, DeepSeek-R1, Llama-3.3):
```
50 workers/实例 × 3个实例 = 150 total concurrent workers
无QPS限制 = 无限制调用速度
```

#### **Qwen模型** (IdealLab开源):
```  
2 workers/key × 3个keys = 6 total concurrent workers
无QPS限制 = 无限制调用速度
```

#### **Azure闭源模型** (gpt-4o-mini, gpt-5-mini):
```
100 workers/实例 × 1个实例 = 100 total concurrent workers
无QPS限制 = 无限制调用速度
```

#### **IdealLab闭源模型** (o3, gemini, kimi):
```
1 worker/实例 × 1个实例 = 1 total concurrent worker  
无QPS限制 = 无限制调用速度
```

## 🎯 **配置一致性验证**

### ✅ **现在两个文件的配置完全一致**:

1. **Azure非自适应**: ultra_parallel_runner.py(50) = smart_batch_runner.py(50) 
2. **IdealLab非自适应**: ultra_parallel_runner.py(2) = smart_batch_runner.py(2)
3. **QPS限制**: 所有地方都统一设置为 `None`

### ✅ **符合您的要求**:
- Azure非自适应模式: **50 workers** ✓
- IdealLab非自适应模式: **2 workers** ✓  
- 无QPS上限限制: **qps = None** ✓

## 🚀 **性能影响预估**

### **相比修正前的变化**:

1. **Azure API并发降低**: 100→50 workers (降低50%)
   - **优势**: 更稳定，避免API过载
   - **影响**: 单实例并发略降，但3实例总计仍有150并发

2. **IdealLab API并发降低**: 3→2 workers (降低33%)
   - **优势**: 更好地避免IdealLab API限流
   - **影响**: 轻微降低，但3个key总计仍有6并发

3. **QPS无限制**: 所有限制移除
   - **优势**: 最大化API调用速度，无人为瓶颈
   - **影响**: 依赖API提供商的自然限制

### **预期结果**:
- 更稳定的测试执行
- 减少API超时和限流错误  
- 保持高效的总体并发能力
- 更一致的配置管理