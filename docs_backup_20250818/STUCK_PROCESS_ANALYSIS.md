# 5.3测试进程卡死40小时问题分析

## 问题描述
- 运行`run_systematic_test_final.sh`的5.3部分
- 进程运行40小时不终止
- 没有任何数据写入JSON/Parquet

## 根本原因分析

### 1. **Checkpoint机制问题** 🔴
- **问题**: `batch_test_runner.py`的`_checkpoint_save`每次创建新manager实例
- **影响**: 缓存永远无法累积到触发保存的阈值
- **已修复**: 2025-08-18改为使用`self.manager`

### 2. **Batch-commit模式问题** 🔴
```bash
--batch-commit --checkpoint-interval 20
```
- **问题**: 批量提交模式下，数据只在以下情况保存：
  1. 每20个测试完成时（checkpoint）
  2. 所有测试完成时（final save）
  3. 进程正常退出时
- **影响**: 如果进程卡死，数据永远不会保存

### 3. **缺少超时机制** 🔴
原始代码中的问题：
- 单个测试没有超时限制
- API调用可能无限等待
- 整个批次没有总超时

### 4. **并发死锁问题** 🔴
ultra_parallel模式下：
- 多个进程同时运行
- 每个进程有独立的manager实例
- 文件锁竞争可能导致死锁

### 5. **内存耗尽问题** 🟡
- 150个workers同时初始化MDPWorkflowGenerator
- 每个实例占用大量内存
- 系统资源耗尽导致进程僵死

## 为什么进程不终止？

### 主要原因：
1. **API调用卡死**: IdealLab API可能无响应，没有超时机制
2. **死锁**: 多进程竞争文件锁或其他资源
3. **内存swap**: 内存不足导致系统进入swap，极度缓慢
4. **异常未捕获**: 某些异常导致进程进入僵死状态

### 证据：
```bash
# 之前的日志显示
- 网络连接：CLOSED
- 进程状态：仍在运行
- CPU使用：很低或0
- 内存使用：可能很高
```

## 为什么数据不保存？

### 主要原因：
1. **Batch-commit不触发**: 
   - 测试未完成20个，checkpoint不触发
   - 进程未正常退出，final save不执行

2. **Manager实例问题**:
   - 每次checkpoint创建新实例（已修复）
   - 多进程各自有独立manager
   - Parquet需要100条记录才auto-flush

3. **异常中断**:
   - 进程被强制kill
   - 系统OOM killer
   - 未捕获的异常

## 解决方案

### 已实施的修复：
1. ✅ 修复`_checkpoint_save`使用现有manager
2. ✅ 添加测试超时机制
3. ✅ 减少并发数量

### 建议的额外修复：

#### 1. 添加定时强制保存
```python
# 每5分钟强制flush一次
import threading
def periodic_flush():
    while not stop_flag:
        time.sleep(300)  # 5分钟
        manager._flush_buffer()
        
flush_thread = threading.Thread(target=periodic_flush)
flush_thread.start()
```

#### 2. 使用更小的checkpoint间隔
```bash
--checkpoint-interval 5  # 每5个测试保存一次
```

#### 3. 添加进程监控
```bash
# 在脚本中添加超时监控
timeout 7200 python smart_batch_runner.py ...  # 2小时超时
```

#### 4. 使用更保守的并发设置
```bash
--max-workers 20  # 而不是150
--num-instances 5  # 而不是20
```

#### 5. 启用实时保存
```bash
# 不使用batch-commit，直接实时保存
# 移除 --batch-commit 参数
```

## 推荐的测试命令

### 安全的5.3测试命令：
```bash
# 单模型测试，实时保存
python smart_batch_runner.py \
    --model "DeepSeek-V3-0324" \
    --prompt-types "flawed_sequence_disorder" \
    --difficulty "easy" \
    --task-types "all" \
    --num-instances 5 \
    --tool-success-rate 0.8 \
    --max-workers 20 \
    --no-batch-commit \  # 实时保存
    --checkpoint-interval 5 \
    --no-adaptive \
    --qps 10

# 或使用超时包装
timeout 3600 ./test_5_3_flawed.sh  # 1小时超时
```

## 监控建议

运行测试时监控：
```bash
# 监控进程
watch -n 10 'ps aux | grep smart_batch_runner'

# 监控数据更新
watch -n 60 'python monitor_parquet_updates.py'

# 监控内存
watch -n 5 'free -h'
```

## 总结

**核心问题**：
1. Batch-commit模式 + checkpoint机制bug = 数据不保存
2. 无超时机制 + API卡死 = 进程永不终止
3. 过高并发 + 内存耗尽 = 系统僵死

**解决方案**：
1. 使用实时保存（移除--batch-commit）
2. 添加超时机制
3. 降低并发数量
4. 定期监控和强制保存