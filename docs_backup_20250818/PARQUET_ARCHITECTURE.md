# Parquet存储架构说明

## 📊 数据存储策略

**核心原则**：Parquet只存储汇总统计数据，不存储单个测试记录

## 📁 文件结构

### 主文件：`pilot_bench_parquet_data/test_results.parquet`
存储所有汇总统计记录

#### 基本信息字段
- `model`: 模型名称
- `prompt_type`: 提示类型
- `tool_success_rate`: 工具成功率
- `difficulty`: 难度
- `task_type`: 任务类型

#### 核心统计字段
- `total`: 总测试数
- `success`: 成功数（向后兼容）
- `full_success`: 完全成功数
- `partial_success`: 部分成功数
- `success_rate`: 成功率
- `full_success_rate`: 完全成功率
- `partial_success_rate`: 部分成功率
- `failure_rate`: 失败率
- `weighted_success_score`: 加权成功分数

#### 执行指标字段
- `avg_execution_time`: 平均执行时间
- `avg_turns`: 平均轮数
- `avg_tool_calls`: 平均工具调用次数
- `tool_coverage_rate`: 工具覆盖率

#### 质量分数字段
- `avg_workflow_score`: 平均工作流分数
- `avg_phase2_score`: 平均第二阶段分数
- `avg_quality_score`: 平均质量分数
- `avg_final_score`: 平均最终分数

#### 错误统计字段
- `total_errors`: 总错误数
- `tool_call_format_errors`: 工具调用格式错误
- `timeout_errors`: 超时错误
- `dependency_errors`: 依赖错误
- `parameter_config_errors`: 参数配置错误
- `tool_selection_errors`: 工具选择错误
- `sequence_order_errors`: 序列顺序错误
- `max_turns_errors`: 最大轮数错误
- `other_errors`: 其他错误

#### 错误率字段
- `tool_selection_error_rate`: 工具选择错误率
- `parameter_error_rate`: 参数错误率
- `sequence_error_rate`: 序列错误率
- `dependency_error_rate`: 依赖错误率
- `timeout_error_rate`: 超时错误率
- `format_error_rate`: 格式错误率
- `max_turns_error_rate`: 最大轮数错误率
- `other_error_rate`: 其他错误率

#### 辅助统计字段
- `assisted_failure`: 辅助失败数
- `assisted_success`: 辅助成功数
- `total_assisted_turns`: 总辅助轮数
- `tests_with_assistance`: 有辅助的测试数
- `avg_assisted_turns`: 平均辅助轮数
- `assisted_success_rate`: 辅助成功率
- `assistance_rate`: 辅助率

#### 元数据字段
- `last_updated`: 最后更新时间
- `imported_from_json`: 是否从JSON导入
- `import_time`: 导入时间

## 🔄 数据流程

### 写入流程
1. **测试运行时**：
   - `add_test_result_with_classification()` 接收单个测试结果
   - 在内存中累积统计（不写入单个记录）
   - 更新对应组的汇总计数器

2. **定期刷新**：
   - 每10个测试或批次结束时
   - `_flush_buffer()` 被调用
   - 计算所有率和平均值
   - 将汇总记录写入主Parquet文件

3. **更新策略**：
   - 如果组已存在：更新现有汇总
   - 如果是新组：添加新汇总记录
   - 所有操作都是原子性的

### 查询流程
- 直接从主Parquet文件读取汇总数据
- 不需要实时计算，所有统计已预计算

## 🎯 最终架构

系统现在实现了纯汇总存储：
- **不存储单个测试记录**
- **只存储汇总统计**
- **内存累积，定期刷新**
- **与JSON保持完全一致的字段**

### 核心优势
1. **存储效率**：只存储汇总，大幅减少存储空间
2. **查询性能**：预计算的统计，查询速度快
3. **字段完整**：包含JSON中的所有48个字段
4. **兼容性好**：完全兼容现有的enhanced_cumulative_manager接口

---

**更新时间**: 2025-08-17
**状态**: ✅ 已完成
**作者**: Claude Assistant