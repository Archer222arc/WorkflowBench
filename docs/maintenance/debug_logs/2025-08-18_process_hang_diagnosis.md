# 进程卡死诊断报告

**诊断ID**: DIAG-20250818-001  
**日期**: 2025-08-18 17:15  
**影响组件**: ultra_parallel_runner.py, smart_batch_runner.py  
**严重程度**: 🔴 严重  
**状态**: 🔍 诊断完成，待修复

## 问题描述

运行5.3缺陷工作流测试时，使用超高并行模式后进程长时间卡住无响应。

### 症状
- 25个Python进程持续运行
- 无任何输出或进度更新
- 进程不结束也不报错
- 数据库无更新记录

## 诊断过程

### 1. 进程状态检查
```bash
ps aux | grep -E "(smart_batch|ultra_parallel)" | wc -l
# 结果：25个进程
```

#### 进程详情
- 3个`ultra_parallel_runner`主控进程
- 9个`smart_batch_runner`执行进程
- 多个重复的qwen2.5模型实例

### 2. CPU使用率分析
```
PID 86512: deepseek-v3-0324 - CPU 0.4% (几乎空闲)
PID 88172: qwen2.5-72b - CPU 4.7% (低活动)
PID 88350: qwen2.5-72b - CPU 20.5% (偶尔活动)
```

### 3. 内存使用分析
- 多个进程占用700MB+内存
- smart_batch_runner进程内存持续占用但无输出

### 4. 数据写入检查

#### Parquet增量目录
```bash
ls -la pilot_bench_parquet_data/incremental/
# 结果：目录为空
```

#### 主数据文件
```bash
ls -la pilot_bench_parquet_data/*.parquet
# 最后更新：test_results.parquet - 12:19（5小时前）
```

## 根本原因分析

### 1. **Workflow生成瓶颈**
- 多个进程同时生成workflow
- 每个workflow实例占用~250MB内存
- 25个进程 × 250MB = 6.25GB内存压力

### 2. **并发启动冲突**
- 3个模型同时启动超高并行模式
- 每个模型又分3个分片
- 总计9个并发执行进程争抢资源

### 3. **Silent模式掩盖错误**
- `--silent`参数阻止了错误输出
- API调用失败无法看到
- 超时或异常被静默处理

### 4. **Parquet写入失败**
- 增量目录完全为空
- 可能是并发写入锁冲突
- 或checkpoint机制失效

## 诊断结论

### 核心问题
1. ❌ **资源竞争严重**：过多进程同时启动导致资源耗尽
2. ❌ **无超时控制**：进程可以无限等待
3. ❌ **无错误反馈**：silent模式下问题被隐藏
4. ❌ **数据未保存**：5小时运行无任何数据产出

### 影响范围
- 所有使用超高并行模式的测试
- 5.3缺陷工作流测试完全阻塞
- 系统资源被长时间占用

## 修复建议

### 紧急措施
```bash
# 1. 终止所有卡死进程
pkill -f "ultra_parallel"
pkill -f "smart_batch"

# 2. 清理残留
rm -f pilot_bench_parquet_data/incremental/*.tmp
```

### 短期修复
1. **降低并发度**
   - 每次只启动1个模型
   - 减少workers数到10-20
   - 增加分片启动延迟到60秒

2. **添加超时控制**
   - 为每个测试添加总超时时间
   - API调用超时设置为30秒
   - Workflow生成超时设置为5分钟

3. **改进日志输出**
   - 移除--silent参数
   - 添加进度打印
   - 定期输出心跳信息

### 长期优化
1. **资源管理器**
   - 实现进程池管理
   - 动态调整并发数
   - 内存压力监控

2. **健康检查机制**
   - 定期检查进程活性
   - 自动重启卡死进程
   - 数据保存验证

## 相关文档
- [debug_to_do.txt](../../../debug_to_do.txt) - 当前任务列表
- [DEBUG_HISTORY.md](../DEBUG_HISTORY.md) - 调试历史记录
- [超高并行模式设计文档](../../../ultra_parallel_runner.py)

## 后续行动
1. 实施紧急措施终止进程
2. 修改启动策略避免资源竞争
3. 添加超时和健康检查机制
4. 重新测试并验证修复效果

---
**记录人**: Claude Assistant  
**审核状态**: 待处理