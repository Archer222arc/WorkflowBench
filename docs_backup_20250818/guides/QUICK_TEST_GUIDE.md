# PILOT-Bench 快速测试指南

## 🚀 最快开始

### 1. 模拟测试（无需等待）
```bash
# 运行50个模拟测试
python batch_test_runner.py --model qwen2.5-3b-instruct --simulate 50

# 查看进度
python batch_test_runner.py --model qwen2.5-3b-instruct --progress

# 查看详细进度
python batch_test_runner.py --model qwen2.5-3b-instruct --progress --detailed
```

### 2. 实际测试
```bash
# 微量测试
python batch_test_runner.py --model gpt-4o-mini --count 5

# 智能测试（自动选择需要的）
python batch_test_runner.py --model gpt-4o-mini --count 20 --smart

# 包含缺陷测试
python batch_test_runner.py --model gpt-4o-mini --count 10 --flawed
```

## 📊 生成报告

```bash
# 生成综合报告
python comprehensive_report_generator.py

# 生成特定表格
python comprehensive_report_generator.py --table 4.1.2
```

## 🔧 核心文件说明

| 文件名 | 功能 | 使用场景 |
|--------|------|----------|
| `batch_test_runner.py` | 唯一测试运行器 | 所有测试功能 |
| `cumulative_test_manager.py` | 累积管理 | API核心 |
| `comprehensive_report_generator.py` | 报告生成 | 生成实验表格 |

## 💡 使用建议

1. **先用模拟测试验证流程**
   ```bash
   python batch_test_runner.py --simulate 50
   ```

2. **再运行少量真实测试**
   ```bash
   python batch_test_runner.py --count 3
   ```

3. **最后批量测试**
   ```bash
   python batch_test_runner.py --count 100 --smart
   ```

## 📈 测试目标

每个组合（模型+任务+提示）目标100次测试：
- 5种任务类型
- 3种提示类型（baseline, optimal, cot）
- 7种缺陷类型
- 总计：15个正常组合 + 35个缺陷组合 = 50个组合
- 每个组合100次 = 5000个测试/模型

## ⚡ 常用命令

```bash
# 快速添加100个模拟测试
python batch_test_runner.py --model gpt-4o-mini --simulate 100

# 批量测试多个模型
for model in gpt-4o-mini qwen2.5-3b-instruct claude37_sonnet; do
    python batch_test_runner.py --model $model --count 20 --smart --flawed
done

# 查看所有模型进度
for model in gpt-4o-mini qwen2.5-3b-instruct; do
    echo "=== $model ==="
    python batch_test_runner.py --model $model --progress --detailed
done
```

---
**提示**: 使用 `--smart` 参数可以自动选择最需要的测试，避免重复测试已经完成的组合。