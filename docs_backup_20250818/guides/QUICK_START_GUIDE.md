# WorkflowBench 快速开始指南

## 🚀 一键运行所有测试

```bash
# 完整测试（约需30-60分钟）
python integrated_batch_tester.py

# 快速测试（约需5-10分钟）
python integrated_batch_tester.py --quick
```

## 📊 测试类型说明

### 1. 性能测试
- 测试模型在标准任务上的表现
- 包含多种提示类型对比

### 2. 鲁棒性测试  
- 测试7种缺陷工作流处理能力
- 评估模型的容错能力

### 3. 可靠性测试
- 测试不同工具成功率下的表现
- 评估模型的适应能力

### 4. 提示敏感性测试
- 比较不同提示策略的效果
- 评估模型的稳定性

## 🎯 常用命令示例

### 测试特定模型
```bash
python integrated_batch_tester.py --models gpt-4o-mini
```

### 测试特定任务类型
```bash
python integrated_batch_tester.py --task-types simple_task data_pipeline
```

### 跳过某些测试
```bash
# 只运行性能和鲁棒性测试
python integrated_batch_tester.py --skip-reliability --skip-prompt-sensitivity
```

### 自定义测试规模
```bash
# 每种任务类型测试5个实例
python integrated_batch_tester.py --instances 5
```

## 📁 输出结构

```
integrated_test_results/
└── session_YYYYMMDD_HHMMSS/
    ├── integrated_report.md        # 主报告（先看这个！）
    ├── test_config.json            # 测试配置
    ├── performance_test/           # 性能测试结果
    │   └── comprehensive_report.md
    ├── robustness_test/            # 鲁棒性测试结果
    │   └── comprehensive_report.md
    └── reliability_test/           # 可靠性测试结果
        └── reliability_sensitivity_report.md
```

## 🔧 高级用法

### 使用原始测试脚本

如果需要更细粒度的控制：

```bash
# 只测试缺陷工作流
python test_flawed_robustness.py

# 只测试工具可靠性
python test_reliability_batch.py

# 使用统一入口的特定测试
python run_all_tests.py robustness --models gpt-4o-mini
```

### 自定义集成测试

```python
from integrated_batch_tester import IntegratedBatchTester, IntegratedTestConfig

# 创建自定义配置
config = IntegratedTestConfig(
    models=["gpt-4o-mini", "claude37_sonnet"],
    task_types=["simple_task", "data_pipeline"],
    instances_per_type=5,
    test_performance=True,
    test_robustness=True,
    test_reliability=False,  # 跳过可靠性测试
    robustness_severity='medium'  # 使用中等严重度
)

# 运行测试
tester = IntegratedBatchTester()
results_dir = tester.run_integrated_test(config)
```

## 📈 查看结果

1. **先看主报告**: `integrated_report.md`
   - 测试概览
   - 关键发现
   - 改进建议

2. **查看详细报告**：
   - 性能详情: `performance_test/comprehensive_report.md`
   - 缺陷处理详情: `robustness_test/comprehensive_report.md`
   - 可靠性曲线: `reliability_test/reliability_sensitivity_report.md`

3. **分析原始数据**：
   - JSON格式的完整测试结果
   - 可用于自定义分析和可视化

## ⚡ 性能优化建议

1. **减少测试规模**：
   ```bash
   python integrated_batch_tester.py --instances 1 --models gpt-4o-mini
   ```

2. **并行执行**：
   - 默认使用2个并行模型
   - 可通过修改配置增加并行度

3. **选择性测试**：
   - 使用 `--skip-*` 参数跳过不需要的测试
   - 使用 `--quick` 进行快速验证

## 🐛 故障排除

### 常见问题

1. **API配额限制**：
   - 减少 `--instances` 数量
   - 降低并行度

2. **内存不足**：
   - 使用 `--quick` 模式
   - 减少同时测试的模型数量

3. **测试失败**：
   - 查看详细日志: `*/model_name/*.log`
   - 检查API密钥配置

## 📚 更多文档

- 详细测试说明: `TEST_SUITE_README.md`
- 缺陷构造原理: `FLAW_CONSTRUCTION_DETAILS.md`
- 可靠性测试指南: `tool_reliability_testing_guide.md`

---

💡 **提示**: 首次使用建议运行 `--quick` 模式快速了解系统功能。