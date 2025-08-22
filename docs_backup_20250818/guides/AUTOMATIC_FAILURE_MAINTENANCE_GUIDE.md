# 自动失败维护系统指南

## 概述

本系统提供了一套完整的自动失败检测、记录、分析和重测功能，可以智能地管理测试进度并自动补充缺失的测试。

## 🆕 新增功能

### 1. 自动失败维护系统 (`auto_failure_maintenance_system.py`)

**核心功能：**
- 🔍 **智能失败检测**：自动分析测试完成情况，识别失败模式
- 📊 **进度分析**：基于现有数据库分析模型完成率和失败率
- 🔄 **自动重试**：根据配置自动执行重测
- 📋 **重测脚本生成**：生成基于现有进度的增量重测脚本
- 👁️ **监控模式**：持续监控测试状态，自动触发维护

### 2. 增强的智能批测试运行器 (`smart_batch_runner.py`)

**新增模式：**
- 🔧 **自动维护模式** (`--auto-maintain`)：自动检测失败并重测
- 🔄 **增量重测模式** (`--incremental-retest`)：基于现有进度补充缺失测试

### 3. 数据库工具模块 (`database_utils.py`)

**功能：**
- 🗄️ 统一的数据库访问接口
- 📈 模型完成情况分析
- 🔢 测试数量统计功能

## 📋 使用指南

### 基础状态检查

```bash
# 查看系统状态和配置
python auto_failure_maintenance_system.py status

# 查看未完成的测试
python auto_failure_maintenance_system.py incomplete
```

### 自动维护模式

```bash
# 自动检测所有模型的失败并执行重测
python smart_batch_runner.py --auto-maintain

# 针对特定模型进行自动维护
python smart_batch_runner.py --auto-maintain --models gpt-4o-mini claude-3-sonnet

# 执行自动维护（不实际运行测试，仅分析）
python auto_failure_maintenance_system.py maintain
```

### 增量重测模式

```bash
# 基于现有进度补充缺失测试（默认80%完成率阈值）
python smart_batch_runner.py --incremental-retest

# 指定完成率阈值和目标模型
python smart_batch_runner.py --incremental-retest --completion-threshold 0.9 --models gpt-4o-mini

# 生成重测脚本而不立即执行
python auto_failure_maintenance_system.py retest gpt-4o-mini
```

### 监控模式

```bash
# 启动自动监控（每小时检查一次）
python auto_failure_maintenance_system.py monitor
```

## ⚙️ 配置选项

### 自动维护配置 (`auto_maintenance_config.json`)

```json
{
  "retry_strategy": {
    "max_retries": 3,
    "retry_delay": 300,
    "backoff_multiplier": 1.5,
    "priority_models": ["gpt-4o", "claude-3-sonnet"],
    "skip_models": ["deprecated-model"],
    "retry_on_timeout": true,
    "retry_on_api_error": true,
    "retry_on_format_error": false
  },
  "auto_retest": {
    "enabled": true,
    "minimum_completion_rate": 0.8,
    "maximum_failure_rate": 0.3,
    "cooldown_hours": 2,
    "batch_size": 5
  }
}
```

### 智能批测试运行器新参数

| 参数 | 描述 | 示例 |
|------|------|------|
| `--auto-maintain` | 启动自动维护模式 | `--auto-maintain` |
| `--incremental-retest` | 启动增量重测模式 | `--incremental-retest` |
| `--completion-threshold` | 完成率阈值（0.0-1.0） | `--completion-threshold 0.85` |
| `--models` | 指定目标模型列表 | `--models gpt-4o-mini claude-3-sonnet` |

## 🔍 失败检测算法

### 失败模式识别

1. **高失败率模式**：失败率 > 30%
2. **低完成率模式**：完成率 < 80%
3. **组合模式**：同时满足多个条件

### 重试优先级

1. **高优先级模型**：在配置中指定的重要模型
2. **严重失败**：失败率 > 50% 的模型
3. **部分失败**：有失败但不严重的模型

## 📊 进度管理

### 增强的进度跟踪

- **细粒度进度**：按模型、提示类型、难度、任务类型分别跟踪
- **失败记录**：详细记录失败原因和时间
- **重试统计**：跟踪重试次数和成功率
- **完成率分析**：实时计算各维度完成情况

### 进度恢复

- **断点续传**：从上次中断的位置继续
- **增量补充**：只运行缺失的测试
- **智能跳过**：自动跳过已完成的配置

## 🚀 最佳实践

### 1. 日常维护

```bash
# 每日检查（推荐）
python auto_failure_maintenance_system.py status

# 发现问题时
python smart_batch_runner.py --auto-maintain
```

### 2. 大规模测试后

```bash
# 补充缺失的测试
python smart_batch_runner.py --incremental-retest --completion-threshold 0.95

# 生成详细的重测脚本
python auto_failure_maintenance_system.py retest
```

### 3. 特定模型问题

```bash
# 针对单个模型的完整维护
python smart_batch_runner.py --auto-maintain --models problematic-model

# 分析特定模型的未完成测试
python auto_failure_maintenance_system.py incomplete | grep problematic-model
```

## 📈 监控和报告

### 状态报告内容

- **配置信息**：当前系统配置和阈值
- **分析结果**：模型完成率和失败率统计
- **失败模式**：检测到的具体失败模式
- **重试建议**：系统生成的重试建议
- **未完成测试**：详细的缺失测试列表

### 自动生成文件

- **重测脚本**：`auto_retest_incomplete.sh`
- **监控报告**：`auto_maintenance_report_YYYYMMDD_HHMMSS.json`
- **配置文件**：`auto_maintenance_config.json`

## 🔧 故障排除

### 常见问题

1. **循环导入错误**
   - 解决方案：已通过 `database_utils.py` 模块化解决

2. **数据库锁定**
   - 解决方案：使用批量提交模式 `--batch-commit`

3. **内存不足**
   - 解决方案：降低 `--max-workers` 参数

4. **API限制**
   - 解决方案：调整 `--qps` 参数和重试延迟

### 调试模式

```bash
# 启用详细日志
python smart_batch_runner.py --auto-maintain --save-logs

# 静默模式减少输出
python smart_batch_runner.py --incremental-retest --silent
```

## 📝 集成示例

### 完整工作流示例

```bash
#!/bin/bash

echo "=== 每日自动维护工作流 ==="

# 1. 检查系统状态
echo "检查系统状态..."
python auto_failure_maintenance_system.py status

# 2. 执行自动维护
echo "执行自动维护..."
python smart_batch_runner.py --auto-maintain

# 3. 补充缺失测试
echo "补充缺失测试..."
python smart_batch_runner.py --incremental-retest --completion-threshold 0.9

# 4. 生成最终报告
echo "生成重测脚本..."
python auto_failure_maintenance_system.py retest

echo "=== 维护完成 ==="
```

## 🎯 性能优化

### 并行执行策略

- **多模型并行**：同时处理多个模型
- **批量提交**：减少数据库写入频率
- **自适应QPS**：根据API响应调整请求速率
- **检查点保存**：定期保存进度避免重复工作

### 资源管理

- **内存优化**：及时释放不用的数据
- **CPU平衡**：合理分配并发数
- **网络限制**：遵守API提供商限制

## 📚 相关文档

- [SYSTEM_ARCHITECTURE.md](./SYSTEM_ARCHITECTURE.md) - 系统架构文档
- [DEBUG_KNOWLEDGE_BASE.md](./DEBUG_KNOWLEDGE_BASE.md) - 调试知识库
- [BATCH_TEST_USAGE.md](./BATCH_TEST_USAGE.md) - 批测试使用指南

---

**维护状态**: ✅ 已实现并测试  
**最后更新**: 2025-08-15  
**版本**: v2.0