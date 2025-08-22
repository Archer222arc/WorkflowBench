# 测试统计可能的错误分析

## 1. 工具覆盖率 (Tool Coverage Rate)

### 当前计算
```python
total_available_tools = len(self.generator.tools) if hasattr(self.generator, 'tools') else 30
summary['comprehensive_metrics']['tool_coverage_rate'] = len(all_tools_used) / total_available_tools
```

### 潜在问题
- ❌ **全局统计而非按模型统计**：当前计算的是所有测试中使用的工具总数，而不是每个模型的工具覆盖率
- ❌ **重复计算**：如果同一个工具在多个测试中使用，只计算一次

### 建议修正
```python
# 应该按模型计算
for model in models:
    model_results = [r for r in results if r.model == model]
    model_tools_used = set()
    for result in model_results:
        model_tools_used.update(result.tool_calls)
    model_coverage = len(model_tools_used) / total_available_tools
```

## 2. 平均执行步数 (Average Execution Steps)

### 当前计算
```python
summary['comprehensive_metrics']['avg_execution_steps'] = summary['execution_metrics']['avg_tool_calls']
```

### 潜在问题
- ✅ 这个计算是正确的，但可能包含重试
- ⚠️ **是否应该计算去重后的步数？**

### 分析
- 如果工具A失败后重试成功，算1步还是2步？
- 当前：算2步（反映真实执行成本）
- 可选：算1步（反映逻辑步骤数）

## 3. 工具可靠性敏感性 (Tool Reliability Sensitivity)

### 当前计算
```python
current_tool_success_rate = summary['execution_metrics'].get('tool_success_rate', 0.85)
base_task_success_rate = summary.get('successful_tests', 0) / summary.get('total_tests', 1)
summary['tool_reliability_sensitivity']['success_rate_90'] = base_task_success_rate * (0.90 / current_tool_success_rate)
```

### 潜在问题
- ❌ **线性假设不合理**：工具成功率和任务成功率不是线性关系
- ❌ **没有实际测试**：应该通过修改InteractiveExecutor的成功率来实际测试
- ❌ **可能超过100%**：如果current_tool_success_rate < 0.90，计算结果会>1

### 建议修正
```python
# 使用更合理的非线性模型
def calculate_task_success_with_tool_reliability(base_success, tool_reliability):
    # 任务成功需要关键工具都成功
    # 假设平均需要3个关键工具
    estimated_task_success = base_success * (tool_reliability ** 3)
    return min(1.0, estimated_task_success)
```

## 4. 错误分类 (Error Classification)

### 当前计算
```python
if 'tool' in error_lower or 'not found' in error_lower:
    self.error_category = 'tool_selection'
elif 'param' in error_lower or 'argument' in error_lower:
    self.error_category = 'param_config'
```

### 潜在问题
- ❌ **过于简单的字符串匹配**：可能误分类
- ❌ **没有考虑多种错误类型**：一个错误可能包含多个关键词
- ❌ **忽略了execution_history中的详细错误信息**

### 建议改进
- 使用更精确的错误模式匹配
- 分析execution_history中的ToolExecutionResult.error字段
- 建立错误类型优先级

## 5. 成功级别统计 (Success Level Statistics)

### 当前逻辑
```python
success_levels = {'full_success': 0, 'partial_success': 0, 'failure': 0}
success_level = getattr(result, 'success_level', 'failure')
success_levels[success_level] += 1
```

### 潜在问题
- ⚠️ **success_level的定义可能不一致**
- ❓ **partial_success的判定标准是什么？**

### 需要验证
- full_success: 所有required_tools都成功执行？
- partial_success: 部分required_tools成功？
- failure: 任务完全失败？

## 6. 提示敏感性指数 (Prompt Sensitivity Index)

### 当前计算
```python
if len(prompt_type_scores) > 1:
    prompt_type_means = [np.mean(scores) for scores in prompt_type_scores.values()]
    summary['comprehensive_metrics']['prompt_sensitivity_index'] = np.std(prompt_type_means)
```

### 潜在问题
- ⚠️ **样本量可能不足**：如果某个prompt类型只有1-2个测试
- ❌ **没有按模型计算**：应该每个模型有自己的敏感性指数

## 7. 任务难度分类 (Task Difficulty Classification)

### 当前映射
```python
task_difficulty_map = {
    'simple_task': 'simple',
    'basic_task': 'simple',
    'data_pipeline': 'medium',
    'api_integration': 'medium',
    'multi_stage_pipeline': 'hard',
    'file_processing': 'hard'
}
```

### 潜在问题
- ❓ **file_processing在哪里定义？**
- ⚠️ **难度分类是否合理？**

## 8. Robustness指标统计

### 当前计算
```python
for flaw_type in flaw_types_order:
    flaw_results = [r for r in model_flawed_results if r.flaw_type == flaw_type]
    if flaw_results:
        success_rate = sum(1 for r in flaw_results if r.success) / len(flaw_results) * 100
```

### 潜在问题
- ✅ 按模型正确计算了
- ⚠️ **样本量问题**：每种缺陷类型可能只有很少的测试

## 9. 加权成功分数 (Weighted Success Score)

### 当前计算
```python
weighted_score = (success_levels['full_success'] * 1.0 + 
                 success_levels['partial_success'] * 0.5 + 
                 success_levels['failure'] * 0.0) / len(results)
```

### 潜在问题
- ✅ 计算逻辑正确
- ❓ **权重(1.0, 0.5, 0.0)是否合理？**

## 10. 序列正确率的边界情况

### 新计算中的潜在问题
```python
actual_seq = list(dict.fromkeys(result.tool_calls))  # 去重但保持顺序
```

### 需要考虑的情况
- 如果actual_seq为空怎么办？
- 如果optimal_seq为空怎么办？
- 如果两个序列完全不相交怎么办？

## 建议的修复优先级

1. **高优先级**
   - 工具覆盖率按模型计算
   - 工具可靠性敏感性使用非线性模型
   - 错误分类改进

2. **中优先级**
   - 提示敏感性按模型计算
   - 验证success_level的定义
   - 处理序列正确率的边界情况

3. **低优先级**
   - 确认任务难度分类
   - 调整加权成功分数的权重