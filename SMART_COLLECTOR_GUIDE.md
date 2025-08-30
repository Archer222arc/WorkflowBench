# 智能数据收集器使用指南

## 概述

智能数据收集器已集成到现有的测试系统中，提供了更灵活、可靠的数据管理机制。

## 关键改进

### 1. 多重触发条件
不再依赖单一的数量阈值，支持：
- **数量触发**: 达到指定数量的结果
- **时间触发**: 超过指定时间间隔
- **智能触发**: 根据情况动态调整阈值
- **强制触发**: 进程退出时自动保存

### 2. 自适应配置
系统会根据实际测试规模自动调整参数：
- 小规模测试（<10个）：低阈值，快速保存
- 中等规模测试（10-50个）：平衡阈值
- 大规模测试（>50个）：高阈值，批量优化

### 3. 容错机制
- **进程退出保护**: 异常退出时自动保存未处理数据
- **多级回退**: 智能收集器 → 原始收集器 → 简单模式
- **数据恢复**: 从临时文件恢复丢失的数据

## 使用方法

### 基本使用（无需修改现有代码）
```bash
# 现有的测试命令将自动使用智能收集器
./run_systematic_test_final.sh --phase 5.1

# 或
python3 smart_batch_runner.py --model test_model --num-instances 10
```

### 环境变量配置
```bash
# 设置收集器规模
export COLLECTOR_SCALE=small    # 小规模测试
export COLLECTOR_SCALE=medium   # 中等规模测试  
export COLLECTOR_SCALE=large    # 大规模测试
export COLLECTOR_SCALE=ultra    # 超并发测试

# 设置预期测试数量（自动优化配置）
export NUM_TESTS=15

# 启用智能收集器
export USE_SMART_COLLECTOR=true
```

### 手动配置
如果需要精确控制，可以修改配置：

```python
# 在 smart_collector_config.py 中
CUSTOM_CONFIG = {
    'max_memory_results': 5,    # 5个结果触发保存
    'max_time_seconds': 180,    # 3分钟超时保存
    'auto_save_interval': 60,   # 1分钟自动检查
    'adaptive_threshold': True, # 启用自适应
    'checkpoint_interval': 3,   # 每3个测试保存
}
```

## 故障排除

### 1. 数据没有保存
检查以下几点：
- 确认 `temp_results` 目录存在
- 检查是否有权限写入文件
- 查看日志中的错误信息
- 运行 `python3 smart_collector_config.py` 检查配置

### 2. 性能问题
如果保存过于频繁：
- 增加 `max_memory_results`
- 增加 `max_time_seconds`
- 设置 `COLLECTOR_SCALE=large`

如果保存不够及时：
- 减少 `max_memory_results`
- 减少 `max_time_seconds`  
- 设置 `COLLECTOR_SCALE=small`

### 3. 恢复丢失的数据
```python
# 从临时文件恢复
from result_collector_adapter import create_adaptive_collector

collector = create_adaptive_collector()
recovered_data = collector.collect_all_results()
print(f"恢复了 {len(recovered_data)} 条记录")
```

### 4. 调试信息
增加详细日志：
```bash
export DEBUG_COLLECTOR=true
python3 smart_batch_runner.py --model test_model
```

## 配置参考

| 参数 | 小规模 | 中等规模 | 大规模 | 超并发 |
|------|--------|----------|--------|--------|
| max_memory_results | 3 | 10 | 25 | 5 |
| max_time_seconds | 120 | 300 | 600 | 180 |
| checkpoint_interval | 1 | 5 | 20 | 3 |
| auto_save_interval | 60 | 60 | 60 | 30 |

## 监控和统计

检查收集器状态：
```python
from result_collector_adapter import create_adaptive_collector

collector = create_adaptive_collector()
stats = collector.get_stats()
print(f"当前状态: {stats}")
```

## 注意事项

1. **向后兼容**: 现有代码无需修改即可使用新功能
2. **渐进升级**: 可以选择性启用新特性
3. **安全第一**: 所有修改都有备份，可以随时回滚
4. **监控重要**: 定期检查数据完整性和系统性能

## 获取帮助

如果遇到问题：
1. 检查备份目录中的原始文件
2. 查看 `data_collection_diagnosis_report.md`
3. 运行 `python3 fix_data_collection.py` 进行诊断
4. 查看系统日志获取详细错误信息
