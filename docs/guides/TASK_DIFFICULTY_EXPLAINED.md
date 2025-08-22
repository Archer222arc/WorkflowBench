# 任务难度体系说明

## 两种独立的难度属性

### 1. 任务类型固有复杂度 (Task Type Complexity)
这是任务类型本身的固有难度，由 `complexity` 字段表示：

| 任务类型 | 固有复杂度 | 说明 |
|---------|-----------|------|
| `simple_task` | easy | 简单的单步或少步骤任务 |
| `basic_task` | easy | 基础任务，通常涉及3-4个工具 |
| `data_pipeline` | medium | 数据处理管道，需要协调多个数据处理步骤 |
| `api_integration` | medium | API集成任务，涉及网络请求和数据转换 |
| `multi_stage_pipeline` | hard | 多阶段管道，需要复杂的工作流编排 |

### 2. 任务描述难度 (Description Difficulty)
这是任务描述的语言复杂度，由 `difficulty_level` 字段表示，通过不同的任务库文件区分：

| 难度级别 | 文件名后缀 | 描述特点 | 示例 |
|---------|-----------|---------|------|
| `very_easy` | _very_easy.json | 简洁直接，使用基础词汇 | "Process data by validating, transforming, and filtering" |
| `easy` | _easy.json | 清晰明确，使用标准技术术语 | "Process data through three steps: validate with validator..." |
| `medium` | _medium.json | 较为抽象，使用专业术语 | "Transform input through sequential operations, enhancing value..." |
| `hard` | _hard.json | 抽象复杂，使用高级词汇 | "Elevate raw input through transformative operations..." |
| `very_hard` | _very_hard.json | 极度抽象，充满业务行话 | "Leverage synergies to catalyze metamorphosis..." |

## 测试覆盖矩阵

理想的测试应该覆盖两个维度的组合：

```
                    描述难度
                 ↓ very_easy  easy  medium  hard  very_hard
任务复杂度 →
easy             ✓          ✓     ✓       ✓     ✓
(simple/basic)
                 
medium           ✓          ✓     ✓       ✓     ✓  
(data/api)

hard             ✓          ✓     ✓       ✓     ✓
(multi_stage)
```

## 微量全面测试策略

`run_micro_comprehensive_test.py` 脚本设计覆盖关键组合：

1. **任务类型复杂度覆盖** - 测试所有三种复杂度级别（easy描述）
2. **中等描述难度** - 测试easy和medium复杂度任务
3. **困难描述+hard任务** - 测试最困难的组合
4. **极困难描述** - 测试模型理解抽象描述的能力
5. **缺陷工作流** - 测试错误处理能力

## 使用建议

- **快速验证**: 使用 easy 描述 + 各种任务复杂度
- **能力评估**: 测试 very_hard 描述 + 简单任务（考验理解能力）
- **压力测试**: 使用 hard 描述 + hard 复杂度任务
- **全面测试**: 系统地覆盖矩阵中的所有组合