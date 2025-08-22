# 数据同步指南 (Data Sync Guide)

**版本**: 1.0.0  
**创建时间**: 2025-08-17  
**最后更新**: 2025-08-17 07:00

## 📋 概述

本指南详细说明了如何在JSON和Parquet格式之间同步测试数据，确保数据的完整性和一致性。

## 🔄 数据同步流程

### 1. JSON → Parquet 同步（推荐）

使用完整同步脚本：
```bash
python scripts/data_sync/sync_complete_json_to_parquet.py
```

此脚本会：
- ✅ 自动备份现有Parquet文件
- ✅ 提取JSON中的所有41个必需字段
- ✅ 自动过滤无效数据（llama-4-scout-17b, unknown, 单独的flawed）
- ✅ 生成详细的验证报告

### 2. 数据字段结构

#### 必需的41个字段分类：

**基本统计字段 (12个)**：
- total, successful, partial, failed
- success, full_success, partial_success
- success_rate, partial_rate, failure_rate
- weighted_success_score, full_success_rate

**执行指标 (4个)**：
- avg_execution_time
- avg_turns
- avg_tool_calls
- tool_coverage_rate

**质量分数 (4个)**：
- avg_workflow_score
- avg_phase2_score
- avg_quality_score
- avg_final_score

**错误统计 (9个)**：
- total_errors
- tool_call_format_errors
- timeout_errors
- dependency_errors
- parameter_config_errors
- tool_selection_errors
- sequence_order_errors
- max_turns_errors
- other_errors

**错误率 (8个)**：
- tool_selection_error_rate
- parameter_error_rate
- sequence_error_rate
- dependency_error_rate
- timeout_error_rate
- format_error_rate
- max_turns_error_rate
- other_error_rate

**辅助统计 (7个)**：
- assisted_failure
- assisted_success
- total_assisted_turns
- tests_with_assistance
- avg_assisted_turns
- assisted_success_rate
- assistance_rate

### 3. 数据清理规则

#### 必须删除的数据：
| 类型 | 描述 | 原因 |
|------|------|------|
| llama-4-scout-17b | 模型名称 | 已停用的测试模型 |
| task_type=unknown | 任务类型 | 无效的任务分类 |
| prompt_type=flawed | 提示类型 | 没有具体缺陷类型的无效记录 |

#### 必须保留的数据：
| 类型 | 示例 | 说明 |
|------|------|------|
| 具体flawed类型 | flawed_sequence_disorder | 有具体缺陷类型的测试 |
| 质量分数 | avg_workflow_score > 0 | 包含实际测试结果的记录 |
| 错误统计 | total_errors > 0 | 包含错误分析的记录 |

## 🔍 验证和检查

### 运行验证脚本
```python
import pandas as pd

# 读取Parquet文件
df = pd.read_parquet('pilot_bench_parquet_data/test_results.parquet')

# 检查数据完整性
print(f"记录数: {len(df)}")
print(f"字段数: {len(df.columns)}")
print(f"模型数: {len(df['model'].unique())}")

# 检查关键字段非零率
key_fields = ['total_errors', 'avg_workflow_score', 'assisted_success']
for field in key_fields:
    non_zero = len(df[df[field] != 0])
    percentage = (non_zero / len(df)) * 100
    print(f"{field}: {percentage:.1f}% 有值")
```

### 期望的验证结果
- ✅ 222条记录（9个模型）
- ✅ 51个字段（包括5个标识字段）
- ✅ total_errors: >95% 有值
- ✅ tool_selection_errors: >60% 有值
- ✅ avg_workflow_score: >45% 有值

## ⚠️ 常见问题

### 问题1：字段全为0
**原因**：使用了错误的同步脚本或JSON数据不完整  
**解决**：
1. 恢复包含完整字段的JSON备份
2. 使用`sync_complete_json_to_parquet.py`脚本

### 问题2：包含无效数据
**原因**：没有进行数据清理  
**解决**：同步脚本会自动过滤，或手动运行：
```python
df = pd.read_parquet('pilot_bench_parquet_data/test_results.parquet')
df_clean = df[df['model'] != 'llama-4-scout-17b']
df_clean = df_clean[df_clean['task_type'] != 'unknown']
df_clean = df_clean[df_clean['prompt_type'] != 'flawed']
df_clean.to_parquet('pilot_bench_parquet_data/test_results.parquet')
```

### 问题3：JSON备份丢失
**原因**：没有定期备份  
**解决**：检查`pilot_bench_cumulative_results/backups/`目录

## 📊 数据同步最佳实践

1. **定期备份**：在每次同步前自动创建备份
2. **验证字段**：确保JSON包含所有41个必需字段
3. **数据清理**：自动过滤无效数据
4. **质量检查**：同步后验证关键字段的非零率
5. **文档记录**：在CLAUDE.md中记录每次重要的数据同步

## 🔗 相关文档

- [CLAUDE.md](./CLAUDE.md) - 项目主文档
- [PARQUET_STORAGE_GUIDE.md](./PARQUET_STORAGE_GUIDE.md) - Parquet存储指南
- [README.md](./README.md) - 项目说明

## 📝 更新日志

### 2025-08-17 v1.0.0
- 创建初始版本
- 添加完整的字段说明
- 添加数据清理规则
- 添加常见问题解决方案