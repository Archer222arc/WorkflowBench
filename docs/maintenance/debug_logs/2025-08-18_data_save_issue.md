# 数据保存问题诊断报告

**诊断ID**: DIAG-20250818-002  
**日期**: 2025-08-18 17:35  
**影响组件**: smart_batch_runner.py, enhanced_cumulative_manager.py  
**严重程度**: 🔴 严重  
**状态**: 🔍 已诊断，需要深入调查

## 问题描述

运行测试后数据未能正确保存到master_database.json，虽然日志显示"Database saved successfully"，但实际数据未更新。

## 症状

1. **测试正常运行**
   - 日志显示测试执行成功
   - AI分类正常工作
   - 显示"✅ 已保存 1 个测试结果到数据库"

2. **数据未保存**
   - master_database.json的total_tests未增加
   - 虽创建了prompt_type键，但total_tests为0
   - test_groups未添加新记录

## 诊断过程

### 1. 简单测试验证
```bash
python simple_test_verify.py
# 结果：测试成功但数据未更新
```

### 2. 直接运行测试
```bash
python smart_batch_runner.py \
  --model gpt-4o-mini \
  --prompt-types flawed_vague_instruction \
  --difficulty easy \
  --task-types simple_task \
  --num-instances 1
```
结果：
- 测试执行成功
- 日志显示"Database saved successfully"
- 实际检查：total_tests仍为4993

### 3. 日志分析
```
[INFO] Flushing 1 records to database...
[INFO] Saving database...
[INFO] Database saved successfully in 0.03s
```
保存时间过短（0.03秒），可能只是创建了结构而未实际写入数据。

## 可能原因

1. **数据聚合逻辑问题**
   - 数据可能在聚合阶段丢失
   - 统计计数器未正确更新

2. **批处理模式问题**
   - batch-commit模式可能导致数据丢失
   - checkpoint机制可能有bug

3. **并发写入冲突**
   - 虽然使用了文件锁，但可能存在逻辑错误
   - 读取-修改-写入的过程可能被中断

4. **JSON/Parquet双格式问题**
   - 可能数据写入了Parquet但JSON未更新
   - 格式转换时数据丢失

## 验证测试

### 测试1：检查Parquet数据
```python
from pathlib import Path
parquet_file = Path("pilot_bench_parquet_data/test_results.parquet")
if parquet_file.exists():
    import pandas as pd
    df = pd.read_parquet(parquet_file)
    print(f"Parquet记录数: {len(df)}")
```

### 测试2：直接调用manager
```python
from enhanced_cumulative_manager import EnhancedCumulativeManager
from cumulative_test_manager import TestRecord

manager = EnhancedCumulativeManager()
record = TestRecord(
    model="test-model",
    task_type="simple_task",
    prompt_type="baseline",
    difficulty="easy",
    tool_success_rate=0.8,
    success=True
)
success = manager.add_test_result_with_classification(record)
print(f"添加结果: {success}")
```

## 临时解决方案

1. **禁用batch-commit模式**
   - 去掉`--batch-commit`参数
   - 每个测试立即保存

2. **使用JSON格式**
   - 设置`STORAGE_FORMAT=json`
   - 避免Parquet相关问题

3. **添加调试日志**
   - 在enhanced_cumulative_manager.py添加详细日志
   - 追踪数据流向

## 长期修复建议

1. **重构数据保存流程**
   - 简化保存逻辑
   - 添加数据验证步骤

2. **实现事务机制**
   - 确保数据完整性
   - 失败时自动回滚

3. **改进错误处理**
   - 捕获并报告所有异常
   - 添加数据恢复机制

## 相关文件

- smart_batch_runner.py - 行205-210（commit_to_database调用）
- enhanced_cumulative_manager.py - add_test_result_with_classification方法
- batch_test_runner.py - 数据写入逻辑

## 后续行动

1. 深入调试enhanced_cumulative_manager.py
2. 添加详细日志追踪数据流
3. 实现数据验证机制
4. 考虑回退到更简单的保存机制

---
**记录人**: Claude Assistant  
**审核状态**: 待处理