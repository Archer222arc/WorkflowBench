# 新API端点模型状态报告

## ✅ 全部7个模型均可正常运行！

### 模型列表和配置

| 模型名称 | 状态 | API参数类型 | 备注 |
|---------|------|------------|------|
| **DeepSeek-R1-0528** | ✅ 正常 | max_completion_tokens | 最新推理模型 |
| **DeepSeek-V3-0324** | ✅ 正常 | max_completion_tokens | 替代所有V3版本 |
| **gpt-5-mini** | ✅ 正常 | 简化API（无限制） | 轻量版GPT-5 |
| **gpt-5-nano** | ✅ 正常 | 简化API（无限制） | 超轻量版GPT-5 |
| **gpt-oss-120b** | ✅ 正常 | max_completion_tokens | 开源GPT 120B |
| **grok-3** | ✅ 正常 | max_completion_tokens | Grok第三代 |
| **Llama-3.3-70B-Instruct** | ✅ 正常 | max_completion_tokens | Llama最新版 |

### 自动路由映射

系统会自动将旧版本模型路由到新版本：

- `deepseek-v3-671b` → `DeepSeek-V3-0324`
- `DeepSeek-V3-671B` → `DeepSeek-V3-0324`
- `deepseek-r1-671b` → `DeepSeek-R1-0528`
- `DeepSeek-R1-671B` → `DeepSeek-R1-0528`
- `llama-3.3-70b-instruct` → `Llama-3.3-70B-Instruct`

### API调用示例

#### GPT-5系列（使用简化API）
```python
response = client.chat.completions.create(
    model="gpt-5-mini",
    messages=[{"role": "user", "content": "Your prompt"}]
    # 不需要设置max_tokens或temperature
)
```

#### 其他模型（使用max_completion_tokens）
```python
response = client.chat.completions.create(
    model="DeepSeek-V3-0324",
    messages=[{"role": "user", "content": "Your prompt"}],
    max_completion_tokens=100,  # 注意：不是max_tokens
    temperature=0.7  # 最小值0.1，不能为0
)
```

### 批量测试命令

测试所有新模型：
```bash
python smart_batch_runner.py \
    --model DeepSeek-V3-0324 DeepSeek-R1-0528 gpt-5-mini gpt-5-nano gpt-oss-120b grok-3 Llama-3.3-70B-Instruct \
    --prompt-types baseline \
    --difficulty easy \
    --task-types simple_task \
    --num-instances 1
```

测试DeepSeek系列（包括自动路由）：
```bash
python smart_batch_runner.py \
    --model deepseek-v3-671b DeepSeek-V3-0324 DeepSeek-R1-0528 \
    --prompt-types baseline optimal \
    --difficulty easy medium \
    --task-types simple_task data_pipeline \
    --num-instances 5
```

### 性能特点

1. **DeepSeek系列**：强大的推理能力，适合复杂任务
2. **GPT-5系列**：
   - `gpt-5-mini`：平衡性能，适合一般任务
   - `gpt-5-nano`：响应快速，适合简单任务
3. **gpt-oss-120b**：开源大模型，性能稳定
4. **grok-3**：创新能力强，适合创造性任务
5. **Llama-3.3-70B**：指令遵循能力优秀

### 注意事项

1. **温度设置**：除GPT-5系列外，其他模型最小温度为0.1（不能设为0）
2. **参数名称**：大部分模型使用`max_completion_tokens`而非`max_tokens`
3. **GPT-5简化**：GPT-5系列使用最简单的API，不需要设置额外参数
4. **自动路由**：旧版本DeepSeek模型会自动使用新版本

---

**更新时间**: 2025-08-09  
**测试状态**: ✅ 全部7个模型测试通过  
**系统集成**: ✅ 已完全集成到批量测试框架