# Parquet存储格式设计文档

## 核心设计理念

### 🎯 设计决策：只存储汇总，不存储单个记录

**重要**：Parquet存储格式被设计为**只存储汇总数据，不存储单个测试记录**。这是一个深思熟虑的架构决策。

## 为什么这样设计？

### 1. 性能优化
- **减少I/O开销**：避免频繁写入单个记录
- **提高查询速度**：直接查询预聚合的汇总数据
- **减少存储空间**：汇总数据比原始记录小得多

### 2. 并发安全
- **避免写入冲突**：多个进程只更新汇总，不竞争写入原始数据
- **原子性操作**：汇总更新可以做成原子操作
- **无需文件锁**：减少锁竞争，提高并发性能

### 3. 适合大规模测试
- **内存友好**：不需要在内存中保持大量原始记录
- **增量聚合**：实时聚合，定期刷新
- **可扩展性**：适合处理百万级测试

## 实现细节

### 数据流程
```
测试执行 → TestRecord对象 → 实时聚合到内存缓存 → 定期刷新汇总到Parquet文件
```

### 关键代码位置

#### 1. ParquetDataManager.append_test_result()
```python
# parquet_data_manager.py:135-140
def append_test_result(self, test_data: Dict) -> bool:
    """
    兼容旧接口，但实际不存储单个测试记录
    """
    # 不做任何操作，因为我们只存储汇总
    return True
```
**注意**：这是故意的空操作，不是bug！

#### 2. ParquetCumulativeManager.add_test_result_with_classification()
```python
# parquet_cumulative_manager.py:265-408
def add_test_result_with_classification(self, record) -> bool:
    """
    从TestRecord对象提取数据
    但不保存单个记录，而是更新或创建汇总
    """
    # ... 更新内存中的汇总缓存 ...
    # 每10次更新后刷新到磁盘
    if summary['total'] % 10 == 0:
        self._flush_summary_to_disk(key)
```

#### 3. 汇总数据结构
每个汇总记录包含：
- **标识字段**：model, prompt_type, tool_success_rate, difficulty, task_type
- **统计字段**：total, success, partial_success, failed
- **率值字段**：success_rate, partial_rate, failure_rate
- **平均值字段**：avg_execution_time, avg_turns, avg_tool_calls
- **质量字段**：avg_workflow_score, avg_phase2_score, tool_coverage_rate
- **错误统计**：各种错误类型的计数和率值

### 查询处理

#### compute_statistics()的特殊处理
```python
# parquet_data_manager.py:207-266
def compute_statistics(self, df: pd.DataFrame) -> Dict:
    # 检查是否是汇总数据（包含total字段）
    is_summary_data = 'total' in df.columns
    
    if is_summary_data:
        # 累加各个汇总的总数，而不是统计行数
        total_tests = df['total'].sum()
        # 加权平均计算成功率
        success_rate = success_count / total_tests
```

#### get_progress_report()的实现
```python
# parquet_cumulative_manager.py:509-535
def get_progress_report(self, model: str) -> Dict:
    # 查询该模型的所有汇总数据
    df = self.manager.query_model_stats(model_name=model)
    # 计算总测试数（所有汇总记录的total字段之和）
    total_tests = df['total'].sum() if 'total' in df.columns else 0
```

## 与JSON格式的对比

| 特性 | JSON格式 | Parquet格式 |
|-----|---------|------------|
| 存储内容 | 完整测试记录 + 汇总 | 仅汇总数据 |
| 文件大小 | 大（包含所有原始数据） | 小（仅汇总） |
| 写入性能 | 慢（需要更新整个文件） | 快（增量追加） |
| 查询性能 | 慢（需要遍历所有记录） | 快（直接查询汇总） |
| 并发安全 | 需要文件锁 | 原生支持 |
| 适用场景 | 小规模测试，需要详细记录 | 大规模测试，关注统计结果 |

## 常见误解

### ❌ 错误理解
"Parquet格式没有保存测试数据" - 这是错误的！它保存了汇总数据。

### ✅ 正确理解
"Parquet格式保存预聚合的汇总数据，不保存单个测试记录" - 这是设计意图。

## 迁移和兼容性

### 从JSON迁移到Parquet
```python
# 使用migrate_from_json方法
manager = ParquetDataManager()
manager.migrate_from_json(Path("master_database.json"))
```

### 导出回JSON格式
```python
# 使用export_to_json方法
manager.export_to_json(Path("export.json"))
```

## 最佳实践

1. **批量刷新**：不要每次测试后都刷新，使用批量刷新提高性能
2. **定期consolidate**：虽然不需要合并增量文件，但定期清理有助于维护
3. **监控内存**：确保汇总缓存不会占用过多内存
4. **备份策略**：定期备份Parquet文件，使用create_backup()方法

## 故障排除

### 问题：进度报告显示0测试
**原因**：get_progress_report方法没有正确查询汇总数据
**解决**：确保方法查询Parquet文件并累加total字段

### 问题：统计数据不准确
**原因**：compute_statistics使用行数而不是累加total
**解决**：检测是否为汇总数据，使用相应的计算逻辑

### 问题：数据没有保存
**原因**：缓存没有刷新到磁盘
**解决**：调用_flush_buffer()或finalize()方法

## 版本历史

- **v2.4.5** (2025-08-18): 修复进度报告和统计计算
- **v2.2.0** (2025-08-16): 初始Parquet支持
- **v2.0.0** (2025-08-15): 系统重构

---

**文档创建**: 2025-08-18 00:45
**最后更新**: 2025-08-18 00:45
**维护者**: Claude Assistant