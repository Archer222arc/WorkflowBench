# WorkflowBench 集成测试报告

生成时间: 2025-08-03T15:18:13.541005

## 测试概览

- **测试模型**: gpt-4o-mini, claude37_sonnet
- **任务类型**: simple_task, data_pipeline
- **每类型实例数**: 1
- **运行的测试类型**: 性能测试, 鲁棒性测试, 可靠性测试

## 测试结果摘要

### 4.1 性能测试

- 总测试数: 6
- 整体成功率: 83.3%
- 测试的提示类型: baseline, optimal
- 详细报告: `test_results/performance_test/comprehensive_report.md`

### 4.3.1 鲁棒性测试

- 总测试数: 14
- 测试的缺陷类型: 3种

| 缺陷类型 | 测试数 | 成功数 | 成功率 |
|---------|--------|--------|--------|
| sequence_disorder | 4 | 3 | 75.0% |
| tool_misuse | 5 | 2 | 40.0% |
| parameter_error | 5 | 4 | 80.0% |

- 详细报告: `test_results/robustness_test/comprehensive_report.md`

### 4.3.2 可靠性测试

- 总测试数: 8
- 测试的成功率级别: 90.0%, 60.0%

| 工具成功率 | 测试数 | 任务成功数 | 任务成功率 |
|-----------|--------|------------|------------|
| 90.0% | 4 | 3 | 75.0% |
| 60.0% | 4 | 1 | 25.0% |

- 详细报告: `test_results/reliability_test/reliability_sensitivity_report.md`

## 关键发现

- ✅ 基础性能良好，整体成功率达83.3%
- ⚠️ 对tool_misuse类型缺陷的处理能力较弱（成功率40.0%）
- ⚠️ 对工具可靠性高度敏感（下降50.0%）

## 改进建议

1. **提升工具选择准确性**: 改进语义匹配和工具功能理解
2. **提高错误恢复能力**: 增强在工具失败时的重试和替代策略
