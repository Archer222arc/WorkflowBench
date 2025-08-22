# 智能模型路由系统使用指南

## 系统概述

智能模型路由系统已成功集成到批量测试框架中。系统会自动选择最优的API端点，优先使用您提供的Azure端点上的最新模型。

## 核心特性

### 1. 自动模型替换
当您在测试中使用旧版本模型名称时，系统会自动路由到新版本：

| 原始模型名称 | 自动路由到 | 端点 |
|------------|-----------|------|
| deepseek-v3-671b | DeepSeek-V3-0324 | 您的Azure |
| DeepSeek-V3-671B | DeepSeek-V3-0324 | 您的Azure |
| deepseek-r1-671b | DeepSeek-R1-0528 | 您的Azure |
| DeepSeek-R1-671B | DeepSeek-R1-0528 | 您的Azure |

### 2. 新增可用模型
您的Azure端点上的7个强大模型：

- **DeepSeek-R1-0528** - 最新推理模型
- **DeepSeek-V3-0324** - 最新V3版本（替代所有V3变体）
- **gpt-5-mini** - GPT-5轻量版
- **gpt-5-nano** - GPT-5超轻量版
- **gpt-oss-120b** - 开源GPT 120B
- **grok-3** - Grok第三代
- **Llama-3.3-70B-Instruct** - Llama 3.3指令版

### 3. 智能端点选择优先级

1. **您的Azure端点**（优先）- 最新最强的模型
2. **标准Azure** - gpt-4o-mini等
3. **idealab API** - Qwen系列、其他模型

## 使用方法

### 基础测试命令
```bash
# 测试新模型
python smart_batch_runner.py --model gpt-5-mini --prompt-types baseline --difficulty easy --task-types simple_task --num-instances 1

# 使用旧名称（会自动路由到新版本）
python smart_batch_runner.py --model deepseek-v3-671b --prompt-types baseline --difficulty easy --task-types simple_task --num-instances 1
```

### 批量测试多个模型
```bash
python smart_batch_runner.py \
    --model gpt-5-mini DeepSeek-V3-0324 grok-3 \
    --prompt-types baseline optimal \
    --difficulty easy medium \
    --task-types simple_task data_pipeline \
    --num-instances 10 \
    --max-workers 3
```

## 模型别名支持

系统支持多种模型名称格式：

```python
# 这些名称都会路由到相同的模型
"deepseek-v3", "DeepSeek-V3", "deepseek-v3-0324" -> DeepSeek-V3-0324
"deepseek-r1", "DeepSeek-R1", "deepseek-r1-0528" -> DeepSeek-R1-0528
"gpt5-mini", "GPT-5-mini" -> gpt-5-mini
"llama-3.3", "llama-3.3-70b" -> Llama-3.3-70B-Instruct
```

## 验证路由

运行以下命令查看模型路由报告：

```bash
python verify_routing.py
```

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
    
    # 查看 DeepSeek-V3-0324 的结果（包含所有V3变体的测试）
    model = 'DeepSeek-V3-0324'
    if model in db.get('models', {}):
        model_data = db['models'][model]
        print(f'{model} 测试结果:')
        print(f'  总测试数: {model_data.get(\"total_tests\", 0)}')
        print(f'  成功率: {model_data.get(\"overall_stats\", {}).get(\"success_rate\", 0):.2%}')
"
```

## 注意事项

1. **自动替换**: DeepSeek V3的所有变体都会自动使用V3-0324
2. **成本优化**: 系统优先使用您的Azure端点，可能有更好的性价比
3. **向后兼容**: 所有现有脚本无需修改即可使用新模型

## 故障排除

如果遇到问题：

1. 验证路由是否正确：`python verify_routing.py`
2. 检查API密钥是否有效
3. 查看日志文件：`logs/batch_test_*.log`

---

**更新时间**: 2025-08-09
**状态**: ✅ 系统已完全集成并验证