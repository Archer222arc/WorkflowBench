# 开源模型配置说明

## 批量测试脚本中的开源模型

### 实际测试的独立模型（去重后）
在`run_systematic_test_final.sh`中，虽然列出了11个模型名称，但实际会测试以下独立模型：

1. **DeepSeek-V3-0324** ✅ - 您的Azure端点（替代所有V3版本）
2. **DeepSeek-R1-0528** ✅ - 您的Azure端点（最新推理模型）
3. **Qwen2.5-72B-Instruct** - idealab API
4. **Qwen2.5-32B-Instruct** - idealab API
5. **Qwen2.5-14B-Instruct** - idealab API
6. **Qwen2.5-7B-Instruct** - idealab API
7. **Qwen2.5-3B-Instruct** - idealab API
8. **Llama-3.3-70B-Instruct** ✅ - 您的Azure端点
9. **Llama-4-Scout-17B** - idealab API

### 自动路由关系
以下模型名称会自动路由到新版本，不会重复测试：
- `deepseek-v3-671b` → `DeepSeek-V3-0324`
- `llama-3.3-70b-instruct` → `Llama-3.3-70B-Instruct`

### 测试命令示例

#### 测试所有开源模型（包括新增的）
```bash
./run_systematic_test_final.sh
# 选择选项1（继续）或2（重新开始）
```

#### 单独测试新增模型
```bash
# 测试DeepSeek最新版本
python smart_batch_runner.py \
    --model DeepSeek-V3-0324 DeepSeek-R1-0528 \
    --prompt-types baseline optimal \
    --difficulty easy medium \
    --task-types simple_task data_pipeline \
    --num-instances 5

# 测试Llama最新版本
python smart_batch_runner.py \
    --model Llama-3.3-70B-Instruct \
    --prompt-types baseline optimal cot \
    --difficulty easy medium hard \
    --task-types all \
    --num-instances 10
```

### 注意事项

1. **去重机制**：系统会自动识别重复模型，避免重复测试
2. **路由优化**：旧版本自动使用新版本，确保使用最优端点
3. **API分配**：
   - 您的Azure端点：DeepSeek系列、Llama-3.3
   - idealab API：Qwen系列、Llama-4-Scout

### 性能优势

使用您的Azure端点的模型（标记✅）具有以下优势：
- 更新的模型版本
- 更稳定的连接
- 可能更好的性价比
- 更快的响应速度

---

**更新时间**: 2025-08-09
**脚本位置**: `run_systematic_test_final.sh`