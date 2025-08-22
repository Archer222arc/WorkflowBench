# 智能进度管理功能

## 📋 概述

`run_systematic_test_final.sh` 现在支持智能进度管理，可以通过命令行参数灵活控制测试流程。

## 🚀 新增命令行参数

### 基础参数

| 参数 | 说明 | 使用场景 |
|-----|------|---------|
| `--ignore-progress` | 忽略进度文件，从头开始测试 | 重新测试但保留已有数据 |
| `--fresh` | 完全重新开始，清理所有数据 | 全新的测试环境 |
| `--incremental` | 增量测试模式 | 只测试未完成的配置 |
| `--auto` | 自动模式运行 | 无人值守测试（阶段间暂停） |
| `--debug` | 调试模式运行 | 详细调试（每个模型后暂停） |
| `--full-auto` | 全自动模式 | 完全无人值守（11,400个测试） |
| `--help` | 显示帮助信息 | 查看所有选项 |

## 💡 使用场景

### 1. 增量测试（最常用）
```bash
# 忽略进度文件，只测试数据库中未完成的配置
./run_systematic_test_final.sh --incremental

# 效果：
# - 临时忽略 test_progress.txt
# - 检查 master_database.json 中已完成的测试
# - 只运行未完成的配置
# - 测试后恢复进度文件
```

### 2. 强制重新测试
```bash
# 忽略进度，从头测试，但保留已有数据
./run_systematic_test_final.sh --ignore-progress --auto

# 效果：
# - 临时忽略进度文件
# - 从步骤5.1开始
# - 已有数据会被覆盖更新
# - 测试后恢复进度文件
```

### 3. 完全重新开始
```bash
# 清理所有数据，全新开始
./run_systematic_test_final.sh --fresh --full-auto

# 效果：
# - 备份并清理所有数据
# - 创建新的数据库
# - 连续运行所有11,400个测试
```

### 4. 调试特定问题
```bash
# 调试模式，忽略进度
./run_systematic_test_final.sh --ignore-progress --debug

# 效果：
# - 从头开始但保留数据
# - 每个模型后暂停
# - 可以详细观察每个步骤
```

## 🔧 高级功能

### 进度文件管理

1. **临时忽略**
   - 进度文件被重命名为 `.ignored` 后缀
   - 测试完成后自动恢复
   - 不会丢失原有进度信息

2. **智能检测**
   - 自动检测数据库中已完成的配置
   - 跳过已成功的测试
   - 只运行失败或未测试的配置

3. **三层保护**
   - **宏观层**：步骤级别（5.1-5.5）
   - **中观层**：配置级别（模型+参数组合）
   - **微观层**：任务级别（每20个测试保存）

### 组合使用

```bash
# 示例1：周末无人值守测试
./run_systematic_test_final.sh --incremental --full-auto

# 示例2：快速验证修复
./run_systematic_test_final.sh --ignore-progress --auto

# 示例3：生产环境部署
./run_systematic_test_final.sh --fresh --full-auto
```

## 📊 进度状态管理

### 文件结构
```
test_progress.txt          # 当前进度（步骤、模型索引、子步骤）
completed_tests.txt         # 已完成的配置列表
master_database.json        # 完整的测试结果数据库
```

### 智能恢复机制
1. 正常中断：从上次位置继续
2. 忽略进度：临时跳过，测试后恢复
3. 增量模式：基于数据库智能判断
4. 完全重置：备份后清理所有状态

## 🎯 最佳实践

### 日常测试流程
```bash
# 1. 首次运行
./run_systematic_test_final.sh --auto

# 2. 中断后继续
./run_systematic_test_final.sh  # 交互式选择继续

# 3. 发现问题后重测
./run_systematic_test_final.sh --incremental

# 4. 验证修复
./run_systematic_test_final.sh --ignore-progress --debug
```

### CI/CD集成
```bash
# GitLab CI示例
test:
  script:
    - ./run_systematic_test_final.sh --incremental --full-auto
  timeout: 48h
  retry:
    max: 2
    when:
      - runner_system_failure
      - unknown_failure
```

## 🔍 监控和调试

### 查看当前进度
```bash
# 查看进度文件
cat test_progress.txt

# 查看已完成配置
wc -l completed_tests.txt

# 查看数据库统计
python -c "
import json
with open('pilot_bench_cumulative_results/master_database.json') as f:
    db = json.load(f)
    print(f'总测试: {db['summary']['total_tests']}')
    print(f'成功率: {db['summary']['total_success']/db['summary']['total_tests']*100:.1f}%')
"
```

### 实时监控
```bash
# 监控测试进程
watch -n 5 'ps aux | grep smart_batch_runner | wc -l'

# 监控日志
tail -f logs/batch_test_*.log

# 监控数据库更新
watch -n 10 'ls -lh pilot_bench_cumulative_results/master_database.json'
```

## ✨ 特色功能

1. **无缝切换** - 可以随时在不同模式间切换
2. **数据保护** - 自动备份重要数据
3. **断点续传** - 支持任意位置中断和恢复
4. **并行优化** - 自动启用所有并行优化
5. **智能跳过** - 基于数据库智能判断已完成测试

## 📝 注意事项

- 使用 `--fresh` 会备份但清理所有数据
- `--incremental` 依赖数据库的完整性
- `--full-auto` 需要约44小时完成（优化后）
- 进度文件被忽略时会自动创建 `.ignored` 备份

---

**更新时间**: 2025-08-14
**版本**: v1.0
**状态**: ✅ 生产就绪