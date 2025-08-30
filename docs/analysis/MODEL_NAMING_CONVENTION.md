# 模型命名规范文档

## 背景与目的

在超并行测试系统中，我们使用多个Azure部署来提高并发能力。同一个模型可能有多个部署实例（如 DeepSeek-V3-0324, DeepSeek-V3-0324-2, DeepSeek-V3-0324-3），这些都是同一个模型的不同部署，用于并行处理。

本文档定义了统一的命名规范，确保：
1. API调用使用正确的部署名
2. 数据统计正确聚合到基础模型
3. 各组件之间名称传递的一致性

## 核心概念

### 基础模型名 (Base Model Name)
- **定义**: 模型的标准名称，不包含部署后缀
- **用途**: 数据统计、结果聚合、报告生成
- **示例**: `DeepSeek-V3-0324`, `Llama-3.3-70B-Instruct`

### 部署实例名 (Deployment Instance Name)
- **定义**: 具体的Azure部署名称，可能包含后缀
- **用途**: API调用、路由选择
- **示例**: `DeepSeek-V3-0324-2`, `DeepSeek-V3-0324-3`

### API模型名 (API Model Name)
- **定义**: 调用API时使用的实际名称
- **用途**: 发送给Azure/IdealLab API的模型参数
- **示例**: 必须与Azure deployment name完全一致

### 统计模型名 (Statistical Model Name)
- **定义**: 用于数据统计的规范化名称
- **用途**: 数据库存储、报告生成
- **示例**: 始终使用基础模型名

## 命名规则

### 1. 格式规范

#### Azure开源模型
```
格式: {ModelFamily}-{Version}-{Date}[-{InstanceNumber}]
示例: DeepSeek-V3-0324-2
     └─ModelFamily─┘└Ver┘└Date┘└─Instance─┘
```

#### IdealLab模型
```
格式: {model-name}-{version}-{variant}
示例: qwen2.5-72b-instruct
```

#### 闭源模型
```
格式: {provider}-{model}-{version}
示例: gpt-4o-mini, o3-0416-global
```

### 2. 大小写规则

| 模型类型 | 大小写规则 | 示例 |
|---------|-----------|------|
| DeepSeek系列 | 大驼峰-大写-数字 | `DeepSeek-V3-0324` |
| Llama系列 | 首字母大写 | `Llama-3.3-70B-Instruct` |
| Qwen系列 | 全小写 | `qwen2.5-72b-instruct` |
| GPT系列 | 小写带连字符 | `gpt-4o-mini` |

### 3. 并行实例命名

```python
# 正确的命名格式
deepseek_instances = [
    "DeepSeek-V3-0324",      # 主部署
    "DeepSeek-V3-0324-2",    # 并行部署2（保持大小写一致）
    "DeepSeek-V3-0324-3"     # 并行部署3（保持大小写一致）
]

# 错误的命名格式
wrong_instances = [
    "DeepSeek-V3-0324",      # 主部署
    "deepseek-v3-0324-2",    # ❌ 小写不一致
    "deepseek-v3-0324-3"     # ❌ 小写不一致
]
```

## 组件间传递规则

### 传递链路图
```
用户输入
    ↓
run_systematic_test_final.sh (基础模型名)
    ↓
ultra_parallel_runner.py
    ├─ 创建分片时：model=基础模型名
    └─ 内部记录：instance_name=部署实例名
    ↓
smart_batch_runner.py
    ├─ --model参数：基础模型名（用于统计）
    └─ API调用时：转换为部署实例名
    ↓
api_client_manager.py (使用部署实例名)
    ↓
Azure/IdealLab API
```

### 各组件职责

#### 1. run_systematic_test_final.sh
- **输入**: 基础模型名
- **输出**: 基础模型名
- **示例**: `--model "DeepSeek-V3-0324"`

#### 2. ultra_parallel_runner.py
- **输入**: 基础模型名
- **分片创建**:
  ```python
  TaskShard(
      model=base_model,           # 基础模型名（用于统计）
      instance_name=instance.name  # 部署实例名（用于路由）
  )
  ```
- **传递给smart_batch_runner**:
  ```bash
  --model {base_model}  # 不是instance_name
  ```

#### 3. smart_batch_runner.py
- **接收**: 基础模型名
- **内部处理**: 
  - 数据统计用基础模型名
  - API调用可能需要转换为部署实例名

#### 4. parquet_cumulative_manager.py
- **normalize_model_name**:
  ```python
  # 数据统计场景：去除后缀
  "DeepSeek-V3-0324-2" → "DeepSeek-V3-0324"
  
  # API调用场景：不应使用此函数
  ```

#### 5. smart_model_router.py
- **路由逻辑**:
  ```python
  # 需要支持带后缀的部署名
  "DeepSeek-V3-0324-2" → ("user_azure", "DeepSeek-V3-0324-2")
  ```

## 实现要求

### 必须修复的问题

1. **ultra_parallel_runner.py 第253行**
   ```python
   # 错误
   model=instance.name
   
   # 正确
   model=base_model
   ```

2. **实例名大小写统一**
   ```python
   # 所有并行实例必须保持一致的大小写
   "DeepSeek-V3-0324-2"  # 不是 "deepseek-v3-0324-2"
   ```

3. **API名称与统计名称分离**
   ```python
   class TestResult:
       api_model_name: str      # 用于API调用
       stat_model_name: str     # 用于数据统计
   ```

## 测试验证

### 1. 验证API调用
```python
# 测试带后缀的部署名是否能正确调用
client.create_chat_completion("DeepSeek-V3-0324-2", messages)
```

### 2. 验证数据聚合
```python
# 确认不同部署的结果都归类到基础模型
assert normalize_model_name("DeepSeek-V3-0324-2") == "DeepSeek-V3-0324"
```

### 3. 验证传递链
```bash
# 运行完整流程，检查每个环节的名称传递
./run_systematic_test_final.sh --model "DeepSeek-V3-0324" --debug
```

## 常见错误与解决

### 错误1: 数据分散
**症状**: 同一模型的不同部署被当作独立模型
**原因**: ultra_parallel_runner传递了instance_name而不是base_model
**解决**: 修改TaskShard的model字段使用base_model

### 错误2: API调用失败
**症状**: "Model not found" 或 404错误
**原因**: 部署名大小写不正确
**解决**: 统一所有实例的大小写格式

### 错误3: 统计不准确
**症状**: 模型结果没有正确聚合
**原因**: normalize_model_name在不该使用的地方被调用
**解决**: 区分API场景和统计场景

## 版本历史

- **v1.0** (2025-08-18): 初始版本，定义基本规范
- **v1.1** (待定): 添加配置文件支持

## 相关文档

- [CLAUDE.md](./CLAUDE.md) - 项目主文档
- [debug_to_do.txt](./debug_to_do.txt) - 当前待修复问题列表
- [ULTRA_RUNNER_MODEL_MAPPING_ISSUES.md](./ULTRA_RUNNER_MODEL_MAPPING_ISSUES.md) - 具体问题分析

---

**文档维护者**: Claude Assistant
**最后更新**: 2025-08-18
**状态**: 🔴 待实施