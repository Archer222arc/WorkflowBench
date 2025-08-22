# 如何进行测试

> **重要更新**: 所有测试功能已集成到 `unified_test_runner.py` 
> 
> 详细使用指南请参考 [UNIFIED_TEST_GUIDE.md](./UNIFIED_TEST_GUIDE.md)

## 快速开始（使用统一测试脚本）

### 1. 微量全面测试（推荐首选）
```bash
# 一键运行微量全面测试，覆盖所有主要功能
python unified_test_runner.py micro --model qwen2.5-3b-instruct
```

### 2. 快速测试（验证系统工作）
```bash
# 运行快速测试
python unified_test_runner.py quick --model qwen2.5-3b-instruct --instances 2

# 测试不同难度级别
python unified_test_runner.py quick --model qwen2.5-3b-instruct --difficulty medium --instances 1
```

### 3. 批量累积测试
```bash
# 运行批量测试（目标100个/组）
python unified_test_runner.py batch \
    --model qwen2.5-3b-instruct \
    --repeat 100 \
    --parallel 8

# 继续之前的测试
python unified_test_runner.py batch \
    --model qwen2.5-3b-instruct \
    --continue
```

### 4. 查看测试进度
```bash
# 查看所有模型的进度
python unified_test_runner.py view

# 查看特定模型的进度
python unified_test_runner.py view --model qwen2.5-3b-instruct

# 设置不同的目标值查看进度
python unified_test_runner.py view --target 50
```

## 参数说明

### run_real_test.py 参数

| 参数 | 说明 | 默认值 | 示例 |
|-----|------|-------|------|
| `--model` | 模型名称 | qwen2.5-3b-instruct | `--model gpt-4o-mini` |
| `--task-types` | 任务类型列表 | simple_task/data_pipeline/api_integration | `--task-types simple_task` |
| `--prompt-types` | 提示类型列表 | baseline/optimal/cot | `--prompt-types baseline optimal` |
| `--instances` | 每个任务类型的实例数 | 2 | `--instances 5` |
| `--difficulty` | 任务难度级别 | easy | `--difficulty medium` |
| `--test-flawed` | 包含缺陷测试 | False | `--test-flawed` |
| `--merge` | 合并到累积数据库 | False | `--merge` |

#### 难度级别选项
- `very_easy` - 非常简单
- `easy` - 简单（默认）
- `medium` - 中等
- `hard` - 困难
- `very_hard` - 非常困难

### test_model_100x_cumulative.py 参数

| 参数 | 说明 | 默认值 | 示例 |
|-----|------|-------|------|
| `--model` | 模型名称 | 无（必需） | `qwen2.5-3b-instruct` |
| `--repeat` | 每组目标测试数 | 100 | `--repeat 50` |
| `--instances` | 每批运行的实例数 | 自动计算 | `--instances 10` |
| `--task-types` | 任务类型列表 | 全部5种 | `--task-types simple_task data_pipeline` |
| `--prompt-types` | 提示类型列表 | baseline/optimal/cot | `--prompt-types baseline optimal` |
| `--no-save-logs` | 不保存详细日志 | False | `--no-save-logs` |
| `--no-flawed` | 不进行缺陷测试 | False | `--no-flawed` |
| `--continue` | 继续之前的测试 | False | `--continue` |
| `--parallel` | 并行测试数 | 4 | `--parallel 8` |
| `--difficulty` | 任务难度级别 | easy | `--difficulty medium` |

## 测试策略

### 开源模型测试计划
```bash
# 1. Qwen 系列（阿里开源）
python test_model_100x_cumulative.py --model qwen2.5-3b-instruct --repeat 100
python test_model_100x_cumulative.py --model qwen2.5-7b-instruct --repeat 100
python test_model_100x_cumulative.py --model qwen2.5-14b-instruct --repeat 100

# 2. DeepSeek 系列（深度求索开源）
python test_model_100x_cumulative.py --model DeepSeek-V3-671B --repeat 100
python test_model_100x_cumulative.py --model DeepSeek-R1-671B --repeat 100
```

### 分阶段测试
```bash
# 阶段1：快速验证（每组10个）
python test_model_100x_cumulative.py --model qwen2.5-3b-instruct --repeat 10 --instances 2

# 阶段2：标准测试（每组50个）
python test_model_100x_cumulative.py --model qwen2.5-3b-instruct --repeat 50 --instances 10

# 阶段3：完整测试（每组100个）
python test_model_100x_cumulative.py --model qwen2.5-3b-instruct --repeat 100 --instances 20
```

## 测试数量解释

- `--repeat 100` 表示每个组合（如 simple_task_baseline）的目标是累积到 100 个测试
- `--instances 10` 表示每次批量运行 10 个任务实例
- 测试会自动分配到不同的任务类型和提示类型组合

例如，如果有：
- 3 种任务类型：simple_task, data_pipeline, api_integration
- 3 种提示类型：baseline, optimal, cot
- 总共 9 种组合

运行 `--instances 10` 会为每种组合生成测试，总共约 90 个测试。

## 注意事项

1. **API 配置**：确保 `config/config.json` 中配置了正确的 API 密钥
2. **累积存储**：所有结果都会累积保存在 `cumulative_test_results/` 目录
3. **断点续传**：可以随时中断测试，之后使用 `--continue` 继续
4. **真实测试**：脚本会运行真实的工作流执行，不是模拟数据
5. **资源消耗**：大规模测试会消耗 API 配额，请合理规划

## 故障排除

如果遇到进程挂起：
1. 检查是否有 faiss 相关的导入错误
2. 确保使用的是修复后的版本
3. 查看 `cumulative_test_results/temp/` 目录下的日志

如果测试失败：
1. 检查 API 配置是否正确
2. 查看错误日志了解具体原因
3. 确保所需的模型文件存在（如 checkpoints/best_model.pt）

---
更新时间：2025-08-04