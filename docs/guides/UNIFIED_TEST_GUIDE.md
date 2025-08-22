# 统一测试指南

> 更新时间：2025-08-04
> 
> **重要**: 所有测试功能已集成到 `unified_test_runner.py` 一个脚本中

## 🚀 快速开始

### 最常用的命令

```bash
# 1. 微量全面测试（5分钟快速验证）
python unified_test_runner.py micro --model qwen2.5-3b-instruct

# 2. 批量测试（大规模测试）
python unified_test_runner.py batch --model qwen2.5-3b-instruct --repeat 100

# 3. 查看进度
python unified_test_runner.py view --model qwen2.5-3b-instruct
```

## 📋 完整功能列表

### 1. 微量全面测试 (`micro`)
最少的样本覆盖所有主要功能点，适合快速验证。

```bash
python unified_test_runner.py micro --model <模型名>
```

**特点**：
- 覆盖所有任务复杂度（easy/medium/hard）
- 测试多种描述难度（easy到very_hard）
- 包含缺陷工作流测试
- 5-10分钟完成

### 2. 快速测试 (`quick`)
灵活的小批量测试，验证特定配置。

```bash
python unified_test_runner.py quick \
    --model <模型名> \
    --task-types simple_task data_pipeline \
    --prompt-types baseline optimal \
    --difficulty medium \
    --instances 3
```

**参数**：
- `--task-types`: 任务类型列表
- `--prompt-types`: 提示类型列表
- `--difficulty`: 描述难度级别
- `--instances`: 每个任务类型的实例数
- `--test-flawed`: 包含缺陷测试
- `--no-merge`: 不合并到累积数据库

### 3. 批量累积测试 (`batch`)
大规模测试，支持断点续传和并行执行。

```bash
# 新开始测试
python unified_test_runner.py batch \
    --model <模型名> \
    --repeat 100 \
    --parallel 8

# 继续之前的测试
python unified_test_runner.py batch \
    --model <模型名> \
    --continue
```

**参数**：
- `--repeat`: 每组目标测试数（默认100）
- `--instances`: 每批运行的实例数（默认10）
- `--parallel`: 并行测试数（默认4）
- `--continue`: 继续之前的测试
- `--difficulty`: 任务描述难度级别
- `--test-flawed`: 包含缺陷测试

### 4. 查看进度 (`view`)
查看累积测试的详细进度和统计。

```bash
# 查看所有模型
python unified_test_runner.py view

# 查看特定模型
python unified_test_runner.py view --model qwen2.5-3b-instruct

# 自定义目标值
python unified_test_runner.py view --target 50
```

### 5. 综合测试 (`comprehensive`)
综合测试管理，运行完整的测试套件。

```bash
python unified_test_runner.py comprehensive \
    --model <模型名> \
    --repeat 100 \
    --parallel 4
```

## 🎯 测试策略建议

### 开源模型测试计划

```bash
# 1. 首先运行微量测试验证
python unified_test_runner.py micro --model qwen2.5-3b-instruct

# 2. 如果通过，开始批量测试
python unified_test_runner.py batch --model qwen2.5-3b-instruct --repeat 100

# 3. 随时查看进度
python unified_test_runner.py view --model qwen2.5-3b-instruct

# 4. 如果中断，继续测试
python unified_test_runner.py batch --model qwen2.5-3b-instruct --continue
```

### 不同难度测试

```bash
# 测试very_easy描述
python unified_test_runner.py batch --model qwen2.5-3b-instruct --difficulty very_easy --repeat 50

# 测试medium描述
python unified_test_runner.py batch --model qwen2.5-3b-instruct --difficulty medium --repeat 50

# 测试hard描述
python unified_test_runner.py batch --model qwen2.5-3b-instruct --difficulty hard --repeat 50
```

## 📊 任务类型和难度说明

### 任务类型复杂度
- `simple_task` - easy复杂度
- `basic_task` - easy复杂度
- `data_pipeline` - medium复杂度
- `api_integration` - medium复杂度
- `multi_stage_pipeline` - hard复杂度

### 描述难度级别
- `very_easy` - 非常简单直接的描述
- `easy` - 清晰明确的标准描述（默认）
- `medium` - 较为抽象的专业描述
- `hard` - 复杂抽象的高级描述
- `very_hard` - 极度抽象的业务行话

## 💾 数据存储

所有测试结果累积保存在：
- `cumulative_test_results/results_database.json` - 主数据库
- `cumulative_test_results/temp/` - 临时文件（自动清理）

## 🛠 故障排除

1. **查看帮助**
   ```bash
   python unified_test_runner.py --help
   python unified_test_runner.py batch --help
   ```

2. **检查配置**
   - 确保 `config/config.json` 中有正确的API密钥
   - 确保 `checkpoints/best_model.pt` 存在

3. **进程挂起**
   - 脚本已使用子进程隔离，应该不会挂起
   - 如仍有问题，检查 `temp/` 目录下的日志

## 📝 迁移说明

以下脚本已被集成，请使用对应的命令：

| 原脚本 | 新命令 |
|--------|--------|
| `run_micro_comprehensive_test.py` | `python unified_test_runner.py micro` |
| `run_real_test.py` | `python unified_test_runner.py quick` |
| `run_batch_test.py` | `python unified_test_runner.py batch` |
| `test_model_100x_cumulative.py` | `python unified_test_runner.py batch` |
| `view_test_progress.py` | `python unified_test_runner.py view` |
| `comprehensive_test_manager_v2.py` | `python unified_test_runner.py comprehensive` |

原脚本已备份到 `integrated_scripts_backup_20250804/` 目录。