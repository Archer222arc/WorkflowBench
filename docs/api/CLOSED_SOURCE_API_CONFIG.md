# 闭源模型API配置总结

## 更新时间：2025-08-15

## 可用的闭源模型 (5个)

### 1. gpt-4o-mini ✅
- **Provider**: Azure
- **API Key**: `6Qc2Oxuf0oVtGutYCTSHOGbm1Dmn4kESwrDYeytkJsHWv3xqrnEMJQQJ99BHACHYHv6XJ3w3AAAAACOGXWza`
- **Endpoint**: `https://85409-me3ofvov-eastus2.services.ai.azure.com`
- **响应时间**: ~1秒
- **状态**: 工作正常

### 2. o3-0416-global ✅
- **Provider**: IdealLab
- **API Key**: `956c41bd0f31beaf68b871d4987af4bb`
- **Endpoint**: `https://idealab.alibaba-inc.com/api/openai/v1`
- **响应时间**: 1-2秒
- **状态**: 工作正常

### 3. gemini-2.5-flash-06-17 ✅
- **Provider**: IdealLab
- **API Key**: `956c41bd0f31beaf68b871d4987af4bb`
- **Endpoint**: `https://idealab.alibaba-inc.com/api/openai/v1`
- **响应时间**: 1-2秒
- **注意**: 有时返回空content，需要处理

### 4. grok-3-mini ✅
- **Provider**: Azure AI Foundry
- **API Key**: `6Qc2Oxuf0oVtGutYCTSHOGbm1Dmn4kESwrDYeytkJsHWv3xqrnEMJQQJ99BHACHYHv6XJ3w3AAAAACOGXWza`
- **Endpoint**: `https://85409-me3ofvov-eastus2.services.ai.azure.com`
- **Deployment Name**: `grok-3-mini`
- **响应时间**: 2-3秒
- **状态**: 工作正常

### 5. Llama-3.3-70B-Instruct ✅
- **Provider**: Azure
- **API Key**: `6Qc2Oxuf0oVtGutYCTSHOGbm1Dmn4kESwrDYeytkJsHWv3xqrnEMJQQJ99BHACHYHv6XJ3w3AAAAACOGXWza`
- **Endpoint**: `https://85409-me3ofvov-eastus2.services.ai.azure.com`
- **Deployment Name**: `Llama-3.3-70B-Instruct`
- **响应时间**: <1秒
- **状态**: 工作正常
- **别名支持**: `llama-3.1-nemotron-70b-instruct` 会自动映射

## 不可用的模型

### deepseek-v3-671b ❌
- **问题**: Azure部署不存在（DeploymentNotFound）
- **尝试的配置**: 
  - 8540端口不可访问
  - 标准端口找不到deployment

### gpt-5-mini ❌
- **问题**: API参数不兼容
- **错误**: 需要使用 `max_completion_tokens` 而不是 `max_tokens`

### claude_sonnet4 ❌
- **问题**: IdealLab个人AK无权限
- **错误**: IRC-001 资源限制策略

## API调用注意事项

### 1. 参数简化
```python
# 不要传递这些参数
# ❌ max_tokens
# ❌ temperature

# 只传递必要参数
response = client.chat.completions.create(
    model=model_name,
    messages=messages,
    timeout=60  # 保留timeout防止卡住
)
```

### 2. 响应处理
```python
# 检查空content（特别是Gemini）
if response.choices and response.choices[0].message.content:
    content = response.choices[0].message.content
else:
    # 处理空响应
    content = ""
```

### 3. 模型名称映射
- 使用 `smart_model_router.py` 中的别名映射
- DeepSeek系列映射到正确的deployment name
- Llama别名自动映射到 `Llama-3.3-70B-Instruct`

## 测试命令

```bash
# 测试所有API连接
python test_api_availability.py

# 运行闭源模型测试
./run_systematic_test_final.sh
# 选择：2) 闭源模型
```

## 故障排查

### 超时问题
- 已设置60秒timeout
- 如果仍然超时，检查网络连接

### 404错误
- 检查deployment name是否正确
- 确认模型在Azure上已部署

### 权限错误
- IdealLab个人AK限制较多
- 考虑使用Azure部署的模型