# 新模型使用指南

## 已配置的新模型

感谢您提供的API密钥和endpoint，以下模型已成功配置并可以使用：

1. **DeepSeek-R1-0528** - DeepSeek最新推理模型
2. **DeepSeek-V3-0324** - DeepSeek V3版本
3. **gpt-5-mini** - GPT-5轻量版
4. **gpt-5-nano** - GPT-5超轻量版
5. **gpt-oss-120b** - 开源GPT 120B参数模型
6. **grok-3** - Grok第三代模型
7. **Llama-3.3-70B-Instruct** - Llama 3.3指令调优版

## API配置信息

- **Endpoint**: https://85409-me3ofvov-eastus2.services.ai.azure.com
- **API版本**: 2024-02-15-preview
- **认证方式**: Azure OpenAI API兼容

## 快速测试

### 单个模型测试
```bash
# 测试 gpt-5-mini
python smart_batch_runner.py \
    --model gpt-5-mini \
    --prompt-types baseline \
    --difficulty easy \
    --task-types simple_task \
    --num-instances 1 \
    --tool-success-rate 0.8
```

### 批量测试所有新模型
```bash
# 创建测试脚本
cat > test_all_new_models.sh << 'EOF'
#!/bin/bash

MODELS=(
    "DeepSeek-R1-0528"
    "DeepSeek-V3-0324"
    "gpt-5-mini"
    "gpt-5-nano"
    "gpt-oss-120b"
    "grok-3"
    "Llama-3.3-70B-Instruct"
)

for model in "${MODELS[@]}"; do
    echo "Testing $model..."
    python smart_batch_runner.py \
        --model "$model" \
        --prompt-types baseline \
        --difficulty easy \
        --task-types simple_task \
        --num-instances 1 \
        --tool-success-rate 0.8 \
        --no-save-logs
    echo "---"
done
EOF

chmod +x test_all_new_models.sh
./test_all_new_models.sh
```

## 高级用法

### 完整测试套件
```bash
python smart_batch_runner.py \
    --model gpt-5-mini \
    --prompt-types baseline optimal cot flawed \
    --difficulty easy medium hard \
    --task-types simple_task data_pipeline api_integration multi_stage_pipeline \
    --num-instances 10 \
    --tool-success-rate 0.8 \
    --max-workers 5 \
    --adaptive
```

### 对比测试
```bash
# 对比 GPT-5 系列
python smart_batch_runner.py \
    --model gpt-5-mini gpt-5-nano \
    --prompt-types baseline \
    --difficulty easy \
    --task-types simple_task \
    --num-instances 5 \
    --tool-success-rate 0.8
```

## 性能建议

1. **DeepSeek模型**：推理能力强，适合复杂推理任务
2. **GPT-5系列**：
   - `gpt-5-mini`：平衡性能和成本
   - `gpt-5-nano`：快速响应，适合简单任务
3. **gpt-oss-120b**：开源大模型，性能稳定
4. **grok-3**：创新能力强，适合创造性任务
5. **Llama-3.3-70B**：指令遵循能力强

## 注意事项

1. 这些模型使用您提供的专用Azure endpoint
2. 请注意API调用限制和成本
3. 建议先用少量测试验证模型性能
4. 测试结果会自动保存到 `pilot_bench_cumulative_results/master_database.json`

## 查看测试结果

```python
# 查看特定模型的测试结果
python -c "
import json
from pathlib import Path

db_path = Path('pilot_bench_cumulative_results/master_database.json')
if db_path.exists():
    with open(db_path, 'r') as f:
        db = json.load(f)
    
    model = 'gpt-5-mini'  # 替换为你要查看的模型
    if model in db.get('models', {}):
        model_data = db['models'][model]
        overall = model_data.get('overall_stats', {})
        print(f'{model} 测试结果:')
        print(f'  总测试数: {model_data.get(\"total_tests\", 0)}')
        print(f'  成功率: {overall.get(\"success_rate\", 0):.2%}')
        print(f'  工具覆盖率: {overall.get(\"tool_coverage_rate\", 0):.2%}')
        print(f'  平均执行时间: {overall.get(\"avg_execution_time\", 0):.2f}秒')
"
```

## 故障排除

如果遇到问题：

1. **认证错误**：检查API密钥是否正确
2. **模型不存在**：确认模型名称拼写正确
3. **超时错误**：某些模型可能响应较慢，可以增加超时时间
4. **配置问题**：检查 `api_client_manager.py` 中的配置

---

**更新时间**: 2025-08-09
**配置状态**: ✅ 已成功配置所有7个新模型