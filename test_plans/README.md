# 自定义测试计划使用指南

## 概述
自定义测试系统允许您灵活配置测试计划，以评估不同模型在各种任务上的表现。

## 使用方法

### 1. 运行默认综合测试
```bash
python unified_test_runner.py custom --model qwen2.5-3b-instruct
```

### 2. 使用预定义测试计划
```bash
# 快速测试
python unified_test_runner.py custom --model qwen2.5-3b-instruct --plan-file test_plans/quick_test.json

# 全面综合测试
python unified_test_runner.py custom --model qwen2.5-3b-instruct --plan-file test_plans/full_comprehensive_test.json

# 模型能力测试
python unified_test_runner.py custom --model qwen2.5-3b-instruct --plan-file test_plans/model_capability_test.json
```

## 测试计划格式

每个测试计划是一个JSON数组，包含多个测试配置。每个配置支持以下字段：

```json
{
  "name": "测试名称",
  "task_types": ["任务类型列表"],
  "prompt_types": ["提示类型列表"],
  "difficulty": "难度级别",
  "instances_per_type": 每种类型的实例数,
  "test_flawed": 是否测试缺陷工作流,
  "description": "测试描述（可选）"
}
```

### 支持的参数值

**任务类型 (task_types)**:
- `simple_task` - 简单任务
- `basic_task` - 基础任务
- `data_pipeline` - 数据处理管道
- `api_integration` - API集成
- `multi_stage_pipeline` - 多阶段管道

**提示类型 (prompt_types)**:
- `baseline` - 基准提示
- `optimal` - 优化提示
- `cot` - 思维链提示
- `expert` - 专家提示
- `creative` - 创造性提示

**难度级别 (difficulty)**:
- `easy` - 简单
- `medium` - 中等
- `hard` - 困难
- `mixed` - 混合难度

## 预定义测试计划说明

### quick_test.json
- 最小化测试配置
- 用于快速验证系统功能
- 仅测试1个简单任务

### comprehensive_test.json
- 标准综合测试
- 覆盖所有任务类型
- 平衡的测试数量

### full_comprehensive_test.json
- 完整的综合测试
- 包含所有提示类型
- 测试缺陷工作流
- 适合深度评估

### model_capability_test.json
- 针对特定能力的测试
- 包括工具调用、推理、错误处理等
- 适合评估模型的特定能力

## 创建自定义测试计划

1. 创建新的JSON文件
2. 根据需要组合不同的测试配置
3. 保存到test_plans目录
4. 使用--plan-file参数运行

示例：创建一个专注于API测试的计划
```json
[
  {
    "name": "API基础测试",
    "task_types": ["api_integration"],
    "prompt_types": ["baseline"],
    "difficulty": "easy",
    "instances_per_type": 3
  },
  {
    "name": "API高级测试",
    "task_types": ["api_integration"],
    "prompt_types": ["optimal", "cot", "expert"],
    "difficulty": "hard",
    "instances_per_type": 2,
    "test_flawed": true
  }
]
```

## 测试结果

测试结果将保存在 `workflow_quality_results/` 目录下，包括：
- 详细的执行日志
- 性能指标
- 错误分析
- 可视化报告