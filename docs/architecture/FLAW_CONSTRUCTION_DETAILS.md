# 缺陷工作流构造详细说明

## 概述

系统使用 `FlawedWorkflowGenerator` 类来生成7种不同类型的缺陷工作流。这些缺陷是在最优工作流（optimal workflow）的基础上，通过特定的规则和算法注入的。

## 缺陷类型及构造方法

### 1. 顺序错误 (Sequence Disorder)

**实现方法**: `introduce_order_flaw(workflow, method='dependency', severity)`

**构造逻辑**:
- **swap方法**: 交换工具执行顺序
  - light: 交换1对相邻工具
  - medium: 交换2-3对工具
  - severe: 完全打乱工具顺序
- **dependency方法**: 破坏依赖关系
  - 将有依赖的工具移到其依赖项之前
  - 例如：如果工具B依赖工具A的输出，将B移到A之前

```python
# 示例：原序列 [A, B, C, D]，B依赖A
# 缺陷序列：[B, A, C, D] （B被移到A前面）
```

### 2. 工具误用 (Tool Misuse)

**实现方法**: `introduce_tool_misuse(workflow, method='similar', severity)`

**构造逻辑**:
- 使用语义相似但功能不同的工具替换
- 利用RAG（Retrieval Augmented Generation）找相似工具
- severity决定替换工具的数量：
  - light: 替换1个工具
  - medium: 替换2-3个工具
  - severe: 替换50%以上的工具

**特点**:
- 使用embedding相似度找替代工具
- 确保替换的工具在语义上相似但功能不同
- 例如：将`data_transformer`替换为`data_validator`

### 3. 参数错误 (Parameter Error)

**实现方法**: `introduce_parameter_flaw(workflow, method='wrong', severity)`

**构造逻辑**:
- 在workflow中添加参数错误标记
- 错误类型包括：
  - missing_required: 缺少必需参数
  - wrong_type: 参数类型错误
  - wrong_value: 参数值错误

**注意**: 参数错误主要在prompt生成时体现，不改变工具序列

### 4. 缺失步骤 (Missing Step)

**实现方法**: `introduce_missing_steps(workflow, method='critical', severity)`

**构造逻辑**:
- **middle方法**: 删除中间步骤
  - light: 删除1个中间步骤
  - medium: 删除2个步骤
  - severe: 只保留首尾步骤
- **critical方法**: 删除关键步骤
  - 优先删除验证、检查类工具
- **validation方法**: 删除所有验证相关步骤

### 5. 冗余操作 (Redundant Operations)

**实现方法**: `introduce_redundancy(workflow, method='duplicate', severity)`

**构造逻辑**:
- **duplicate方法**: 重复某些步骤
  - light: 重复1个步骤
  - medium: 重复2个步骤
  - severe: 多个步骤重复多次
- **unnecessary方法**: 添加不必要的工具
  - 插入与任务无关的工具调用

### 6. 逻辑不连续 (Logical Inconsistency)

**实现方法**: `introduce_logic_break(workflow, method='format', severity)`

**构造逻辑**:
- **format方法**: 标记输出格式不匹配
  - 工具A输出JSON，工具B期望CSV
- **unrelated方法**: 插入逻辑上不相关的步骤
  - 在数据处理流程中插入邮件发送步骤

### 7. 语义漂移 (Semantic Drift)

**实现方法**: `introduce_semantic_drift(workflow, severity)`

**构造逻辑**:
- 工具选择逐渐偏离原始意图
- 从某个点开始，每个工具基于前一个工具选择
- 造成累积偏差效应：
  - light: 最后2步开始漂移
  - medium: 中间开始漂移
  - severe: 早期（第2步）就开始漂移

**示例**:
```
原始: [data_reader, data_transformer, data_validator, data_writer]
漂移: [data_reader, data_parser, document_analyzer, file_analyzer]
```

## 特殊功能

### 1. Required Tools Filter

系统支持只对特定工具（required_tools）注入缺陷：
```python
flawed_generator.set_required_tools_filter(['tool_A', 'tool_B'])
```

这确保缺陷只影响任务关键的工具，而不影响辅助工具。

### 2. Smart Actions 更新

每次修改optimal_sequence后，系统会自动更新smart_actions以保持一致性：
```python
def _update_smart_actions(self, workflow: Dict) -> None:
    # 根据新的optimal_sequence重新排序smart_actions
```

### 3. RAG 增强

对于语义相关的缺陷（tool_misuse, semantic_drift），系统使用embedding相似度：
```python
def _find_semantically_similar_tools(self, tool_name: str) -> List[Tuple[str, float]]:
    # 使用embedding_manager查找语义相似的工具
```

## 缺陷注入流程

1. **获取原始工作流**: 从MDPWorkflowGenerator生成的optimal workflow
2. **选择缺陷类型**: 根据测试需求选择7种缺陷之一
3. **应用缺陷规则**: 根据severity级别修改工作流
4. **更新元数据**: 添加缺陷类型、严重程度等标记
5. **同步更新**: 更新smart_actions等相关数据结构

## 使用方式

### 方式1：通过inject_specific_flaw（推荐）
```python
flawed_workflow = generator.inject_specific_flaw(
    workflow=optimal_workflow,
    flaw_type='sequence_disorder',  # 7种类型之一
    severity='severe'
)
```

### 方式2：直接调用具体方法
```python
flawed_workflow = generator.introduce_order_flaw(
    workflow=optimal_workflow,
    method='dependency',
    severity='medium'
)
```

## 缺陷严重程度

- **light**: 轻微缺陷，模型可能能够恢复
- **medium**: 中等缺陷，需要一定的纠错能力
- **severe**: 严重缺陷，测试模型的极限能力

## 评估标准

缺陷工作流的质量通过以下方式评估：
1. 任务是否仍能完成（鲁棒性）
2. 模型是否能识别并纠正缺陷
3. 执行效率的下降程度
4. 错误恢复的策略

这些缺陷类型覆盖了实际应用中可能出现的各种工作流问题，用于全面评估模型的鲁棒性。