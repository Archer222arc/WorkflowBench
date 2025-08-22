# 数据库结构 V3 文档

## 概述
V3版本使用纯字典格式，不再使用任何Python对象，确保数据的序列化和兼容性。

## 数据库根结构
```json
{
  "version": "3.0",
  "created_at": "ISO时间戳",
  "last_updated": "ISO时间戳",
  "test_groups": {},  // 保留用于兼容，但不再使用
  "models": {
    "模型名称": { /* ModelData结构 */ }
  },
  "summary": {
    "total_tests": 0,
    "total_success": 0,
    "total_partial": 0,
    "total_failure": 0,
    "models_tested": ["模型列表"],
    "last_test_time": "ISO时间戳或null"
  }
}
```

## ModelData 结构
每个模型的完整数据结构：
```json
{
  "model_name": "模型名称",
  "first_test_time": "ISO时间戳",
  "last_test_time": "ISO时间戳",
  "total_tests": 数字,  // 基于实际测试计算
  
  "overall_stats": {
    "total_success": 数字,
    "total_partial": 数字,
    "total_full": 数字,
    "total_failure": 数字,
    "success_rate": 小数,
    "weighted_success_score": 小数,
    "avg_execution_time": 小数,
    "avg_turns": 小数,
    "tool_coverage_rate": 小数
  },
  
  "by_prompt_type": {
    "prompt类型": { /* PromptTypeData结构 */ }
  }
}
```

## PromptTypeData 结构
按提示类型组织的数据：
```json
{
  "by_tool_success_rate": {
    "成功率值(如0.8)": { /* ToolSuccessRateData结构 */ }
  },
  "summary": { /* SummaryStats结构 */ }
}
```

## ToolSuccessRateData 结构
按工具成功率组织的数据：
```json
{
  "by_difficulty": {
    "难度级别": { /* DifficultyData结构 */ }
  }
}
```

## DifficultyData 结构
按难度组织的数据：
```json
{
  "by_task_type": {
    "任务类型": { /* TaskTypeStats结构 */ }
  }
}
```

## TaskTypeStats 结构
单个任务类型的完整统计：
```json
{
  // 基础统计
  "total": 数字,
  "success": 数字,
  "success_rate": 小数,
  "weighted_success_score": 小数,
  "full_success_rate": 小数,
  "partial_success_rate": 小数,
  "failure_rate": 小数,
  
  // 执行统计
  "avg_execution_time": 小数,
  "avg_turns": 小数,
  "avg_tool_calls": 小数,
  "tool_coverage_rate": 小数,
  
  // 质量分数
  "avg_workflow_score": 小数,
  "avg_phase2_score": 小数,
  "avg_quality_score": 小数,
  "avg_final_score": 小数,
  
  // 错误统计
  "total_errors": 数字,
  "tool_call_format_errors": 数字,
  "timeout_errors": 数字,
  "dependency_errors": 数字,
  "parameter_config_errors": 数字,
  "tool_selection_errors": 数字,
  "sequence_order_errors": 数字,
  "max_turns_errors": 数字,
  
  // 错误率
  "tool_selection_error_rate": 小数,
  "parameter_error_rate": 小数,
  "sequence_error_rate": 小数,
  "dependency_error_rate": 小数,
  "timeout_error_rate": 小数,
  "format_error_rate": 小数,
  "max_turns_error_rate": 小数,
  
  // 辅助统计
  "assisted_failure": 数字,
  "assisted_success": 数字,
  "total_assisted_turns": 数字,
  "tests_with_assistance": 数字,
  "avg_assisted_turns": 小数,
  "assisted_success_rate": 小数,
  "assistance_rate": 小数
}
```

## SummaryStats 结构
提示类型的汇总统计（与TaskTypeStats相同的字段）

## 层次结构总结
```
数据库
├── 版本信息
├── 时间戳
├── models
│   └── 模型名
│       ├── 基本信息
│       ├── overall_stats（总体统计）
│       └── by_prompt_type
│           └── 提示类型（baseline/optimal/cot/flawed）
│               ├── by_tool_success_rate
│               │   └── 成功率值（0.6/0.7/0.8/0.9等）
│               │       └── by_difficulty
│               │           └── 难度（easy/medium/hard）
│               │               └── by_task_type
│               │                   └── 任务类型
│               │                       └── 详细统计
│               └── summary（该提示类型的汇总）
└── summary（全局汇总）
```

## 重要说明
1. **所有数据都是字典格式**，不使用任何Python类对象
2. **tool_success_rate** 使用字符串键（如 "0.8"）存储，保留4位小数精度
3. **时间戳** 使用ISO格式字符串
4. **数值** 直接存储为数字，不需要额外封装
5. **不再使用** ModelStatistics、ModelStatisticsV2等类对象

## 迁移指南
从旧版本迁移：
- V1 (ModelStatistics对象) → 转换为字典
- V2 (ModelStatisticsV2对象) → 转换为字典
- 移除所有 `_deserialize_models` 和序列化逻辑
- 直接操作字典，使用 `.get()` 方法安全访问