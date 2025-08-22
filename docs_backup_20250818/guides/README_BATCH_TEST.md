# PILOT-Bench 批量测试系统

## 系统概述

`batch_test_runner.py` 是唯一的测试运行器，整合了所有测试功能，支持批量和并发测试模式。

## 快速入门

### 1. 执行测试

#### 普通批量测试
```bash
# 运行10个测试
python batch_test_runner.py --model gpt-4o-mini --count 10

# 智能选择最需要的测试
python batch_test_runner.py --model gpt-4o-mini --count 20 --smart

# 包含缺陷测试
python batch_test_runner.py --model qwen2.5-3b-instruct --count 10 --flawed
```

#### 并发测试（推荐，速度更快）
```bash
# 使用20个线程并发执行1000个测试
python batch_test_runner.py --model gpt-4o-mini --count 1000 --concurrent --workers 20 --qps 20 --smart

# 分难度并发测试
python batch_test_runner.py --model gpt-4o-mini --count 300 --difficulty very_easy --concurrent --workers 15
python batch_test_runner.py --model gpt-4o-mini --count 300 --difficulty easy --concurrent --workers 15
python batch_test_runner.py --model gpt-4o-mini --count 300 --difficulty medium --concurrent --workers 15
```

### 2. 查看进度
```bash
# 简单进度
python batch_test_runner.py --model gpt-4o-mini --progress

# 详细进度
python batch_test_runner.py --model gpt-4o-mini --progress --detailed
```

### 3. 模拟测试（快速验证）
```bash
# 运行50个模拟测试（不实际执行）
python batch_test_runner.py --model gpt-4o-mini --simulate 50
```

### 4. 生成实验报告
```bash
# 生成综合报告
python comprehensive_report_generator.py

# 生成特定表格
python comprehensive_report_generator.py --table 4.1.2
```

## 命令行参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--model` | 要测试的模型名称 | gpt-4o-mini |
| `--count` | 测试数量 | 10 |
| `--task-types` | 任务类型列表 | 所有类型 |
| `--prompt-types` | 提示类型列表 | 随机模式下使用全部10种 |
| `--flawed` | 包含缺陷测试（已废弃，自动20%概率） | False |
| `--smart` | 智能选择需要的测试（累积到100次） | False |
| `--progress` | 只显示进度 | False |
| `--detailed` | 显示详细进度 | False |
| `--simulate` | 运行模拟测试 | None |
| `--timeout` | 单个测试超时（秒） | 30 |
| `--debug` | 启用详细日志 | False |
| `--difficulty` | 任务难度级别 | easy |
| **并发参数** | | |
| `--concurrent` | 启用并发测试模式 | False |
| `--workers` | 最大并发线程数 | 20 |
| `--qps` | 每秒最大请求数 | 20 |
| `--silent` | 静默模式（最小化输出） | False |
| `--save-logs` | 保存详细交互日志 | False |

## 典型使用示例

### 策略1：智能累积测试（系统性覆盖）
```bash
# 使用 --smart 参数，系统性地累积测试
# 目标：50个组合，每个100次 = 5000次测试
python batch_test_runner.py --model gpt-4o-mini --count 1000 --smart --concurrent --workers 20

# 继续累积（会自动选择需要的组合）
python batch_test_runner.py --model gpt-4o-mini --count 1000 --smart --concurrent --workers 20

# 查看进度（看哪些组合还需要测试）
python batch_test_runner.py --model gpt-4o-mini --progress --detailed
```

### 策略2：随机测试（探索性测试）
```bash
# 不使用 --smart，随机组合10种提示类型和5种任务
# 灵活设置测试数量
python batch_test_runner.py --model gpt-4o-mini --count 500 --difficulty very_easy --concurrent --workers 20

# 或者测试多个难度
python batch_test_runner.py --model gpt-4o-mini --count 300 --difficulty very_easy --concurrent
python batch_test_runner.py --model gpt-4o-mini --count 300 --difficulty easy --concurrent
python batch_test_runner.py --model gpt-4o-mini --count 300 --difficulty medium --concurrent
```

### 批量测试多模型
```bash
#!/bin/bash
MODELS=("gpt-4o-mini" "qwen2.5-3b-instruct" "qwen2.5-7b-instruct")

for model in "${MODELS[@]}"; do
    echo "测试模型: $model"
    # 策略2：广度覆盖
    python batch_test_runner.py --model "$model" --count 1000 --difficulty very_easy --concurrent
done
```

### 完整测试工作流
```bash
# 1. 先用模拟测试验证
python batch_test_runner.py --model gpt-4o-mini --simulate 100

# 2. 运行少量真实测试
python batch_test_runner.py --model gpt-4o-mini --count 5

# 3. 选择测试策略
## 选项A：广度覆盖（推荐开始使用）
python batch_test_runner.py --model gpt-4o-mini --count 1000 --difficulty very_easy --concurrent

## 选项B：智能累积（用于深度分析）  
python batch_test_runner.py --model gpt-4o-mini --count 1000 --smart --concurrent

# 4. 查看进度
python batch_test_runner.py --model gpt-4o-mini --progress --detailed

# 5. 生成报告
python comprehensive_report_generator.py
```

## 测试覆盖目标

### 测试策略说明

#### 关于"10种提示类型"的理解
在实验设计中，"10种提示类型"实际指的是向模型展示工作流的10种不同方式：
- **3种正常提示**：展示正确的工作流（baseline, optimal, cot）
- **7种缺陷提示**：展示带有特定缺陷的工作流，测试模型的纠错和鲁棒性
  - 每种缺陷类型（sequence_disorder, tool_misuse等）代表一种"提示策略"
  - 通过在正确工作流中注入缺陷，测试模型是否能识别并处理错误

#### 两种测试模式对比

| 对比项 | 策略1: 智能累积 (--smart) | 策略2: 随机测试 (默认) |
|--------|---------------------------|------------------------|
| 核心理念 | 系统性覆盖所有组合 | 探索性随机测试 |
| 正常提示 | 3种 (baseline, optimal, cot) | 10种代码实现的提示类型 |
| 缺陷测试 | 7种缺陷作为独立测试组合 | 20%概率随机注入缺陷 |
| 组合方式 | 5任务×(3正常提示+7缺陷) = 50组合 | 任务×提示随机组合 |
| 目标 | 每组合100次，共5000次 | 灵活，按需设定 |

#### 策略1：智能累积测试（--smart）
目标是让每个测试组合达到100次，用于深度统计分析：
- 5种任务类型 × 3种提示类型 = 15个正常组合
- 5种任务类型 × 7种缺陷类型 = 35个缺陷组合  
- 每个组合目标100次测试
- **总计：5000个测试/模型**

说明：
- 缺陷测试会在正常生成的工作流中注入错误
- 7种缺陷类型：
  - `sequence_disorder`: 工作流步骤顺序错乱
  - `tool_misuse`: 使用错误的工具
  - `parameter_error`: 工具参数错误
  - `missing_step`: 缺少关键步骤
  - `redundant_operations`: 冗余操作
  - `logical_inconsistency`: 逻辑不一致
  - `semantic_drift`: 语义偏移
- 用于测试模型执行有缺陷工作流时的鲁棒性和容错能力
- 使用 `--smart` 参数会优先测试完成次数最少的组合

#### 策略2：随机测试（默认模式，不使用 --smart）
目标是探索性测试和快速评估：
- 10种提示类型（全部）：baseline, optimal, cot, structured, xml, json, few_shot, zero_shot, guided, adaptive
- 5种任务类型：simple_task, basic_task, data_pipeline, api_integration, multi_stage_pipeline
- 20%概率在工作流中注入缺陷
- **灵活的测试数量，根据需要设定**

说明：
- 每次测试随机选择任务类型和提示类型
- 有20%概率在生成的工作流中随机注入一种缺陷
- 适合探索不同提示类型的效果
- 不追求每个组合的均衡覆盖

### 任务库状态
系统拥有充足的任务量，支持5个难度级别：
- **very_easy**: 856个任务 ✅
- **easy**: 1,096个任务 ✅ (默认)
- **medium**: 1,136个任务 ✅
- **hard**: 1,096个任务 ✅
- **very_hard**: 856个任务 ✅
- **总任务数**: 5,040个任务

每个难度级别都包含完整的任务类型分布：
- basic_task, data_pipeline, multi_stage_pipeline
- simple_task, api_integration

### 任务类型分布（以very_easy为例）
- basic_task: 150个
- data_pipeline: 190个
- multi_stage_pipeline: 80个
- simple_task: 40个
- api_integration: 170个

## 核心组件

1. **batch_test_runner.py** - 批测试运行器
2. **cumulative_test_manager.py** - 累积结果管理
3. **comprehensive_report_generator.py** - 报告生成器

## 数据存储位置

- 累积结果：`pilot_bench_cumulative_results/master_database.json`
- 临时结果：`multi_model_test_results/`
- 生成报告：`comprehensive_report.md`

## 系统状态和兼容性

### ✅ 核心组件状态
- **Checkpoint**: `checkpoints/best_model.pt` ✅ (28.51 MB)
- **工具库**: `tool_registry_consolidated.json` ✅ (30个工具)
- **MCP缓存**: 正常工作 ✅

### 🔧 与其他测试脚本的关系

**注意**: 以下脚本已被 `batch_test_runner.py` 替代：
- `concurrent_test_runner.py` - 并发功能已集成
- `unified_test_runner.py` - 已废弃
- `comprehensive_test_manager_v2.py` - 功能已整合
- `start_comprehensive_test.py` - 已废弃

### 推荐测试流程

#### 阶段1：验证测试（小规模）
```bash
# 模拟测试验证
python batch_test_runner.py --model gpt-4o-mini --simulate 20

# 实际小规模测试
python batch_test_runner.py --model gpt-4o-mini --count 5 --smart
```

#### 阶段2：中等规模测试
```bash
# 智能批量测试
python batch_test_runner.py --model gpt-4o-mini --count 100 --smart --flawed
```

#### 阶段3：完整测试（标准配置）
```bash
# 按照标准配置运行完整测试（推荐使用并发模式）
python batch_test_runner.py --model gpt-4o-mini --count 3000 --concurrent --workers 20 --qps 20 --smart --flawed
```

## 预期输出

测试将生成：
1. **累积结果**: `pilot_bench_cumulative_results/master_database.json`
2. **综合报告**: `comprehensive_report.md` - 包含所有要求的表格：
   - 表4.1.2 任务类型分解性能表
   - 表4.3.1 缺陷工作流适应性表  
   - 表4.4.1 不同提示类型性能表
   - 表4.5.1 系统性错误分类表

## 故障排除

### 常见问题
1. **模型成功率低** - 正常现象，特别是对于较小的模型（如qwen2.5-3b-instruct）
2. **任务找不到** - 检查任务类型是否正确：`simple_task`, `basic_task`, `data_pipeline`, `api_integration`, `multi_stage_pipeline`
3. **系统卡住** - 使用 `--debug` 参数查看详细日志

### Debug模式
```bash
# 启用详细日志
python batch_test_runner.py --model gpt-4o-mini --count 5 --debug

# 查看日志文件
cat batch_test_debug.log
```

### 难度级别测试
```bash
# 可用的难度级别：very_easy, easy, medium, hard, very_hard

# 测试非常简单的任务
python batch_test_runner.py --model gpt-4o-mini --count 10 --difficulty very_easy

# 测试中等难度任务（智能选择）
python batch_test_runner.py --model gpt-4o-mini --count 20 --difficulty medium --smart

# 测试困难任务（带调试）
python batch_test_runner.py --model gpt-4o-mini --count 5 --difficulty hard --debug

# 标准配置：3000个测试的分布（使用并发模式加速）
python batch_test_runner.py --model gpt-4o-mini --count 1000 --difficulty very_easy --concurrent --workers 20 --smart
python batch_test_runner.py --model gpt-4o-mini --count 1000 --difficulty easy --concurrent --workers 20 --smart  
python batch_test_runner.py --model gpt-4o-mini --count 1000 --difficulty medium --concurrent --workers 20 --smart
```

---

**提示**: 使用 `--smart` 参数可以自动选择最需要的测试，避免重复测试已经完成的组合。

**状态**: ✅ 系统完全就绪，可以进行大规模测试！