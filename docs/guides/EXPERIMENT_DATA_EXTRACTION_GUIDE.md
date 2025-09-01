# 实验数据提取使用指南

## 📖 概述

`extract_experiment_results.py` 是WorkflowBench项目的核心数据处理脚本，用于从`master_database.json`中提取和计算实验表格数据。

**重要性**: ★★★★★ (核心脚本)  
**创建时间**: 2025-08-30  
**作者**: Claude Assistant

## 🎯 核心功能

### 1. 自动timeout失败排除
- **逻辑**: `timeout_failures = min(timeout_errors, failed)`
- **计算**: `effective_total = original_total - timeout_failures`
- **目的**: 确保测试结果反映模型真实能力，而非网络/系统问题

### 2. 标准化数据结构理解
- **正确理解**: `success = full_success + partial_success`
- **失败计算**: `success + failed = total`
- **完全成功**: `full_success = success - partial`

### 3. 多实验支持
- **5.1基准测试**: optimal prompt, easy难度, 0.8工具成功率
- **5.2规模效应**: Qwen系列, very_easy/medium难度对比
- **5.3缺陷工作流**: 7种缺陷类型适应性测试

## 🚀 使用方法

### 基本命令
```bash
# 提取所有实验数据概览
python extract_experiment_results.py

# 提取特定实验数据
python extract_experiment_results.py 5.1     # 基准测试
python extract_experiment_results.py 5.2     # 规模效应
python extract_experiment_results.py 5.3     # 缺陷工作流

# 生成标准markdown表格文件
python extract_experiment_results.py generate
```

### 输出示例
```
📊 提取5.1基准测试结果 (排除timeout失败)
============================================================
✅ DeepSeek-V3-0324: 100.0% 成功率 (174 有效测试, 排除 0 timeout)
✅ Llama-3.3-70B-Instruct: 98.3% 成功率 (179 有效测试, 排除 1 timeout)
✅ DeepSeek-R1-0528: 63.9% 成功率 (147 有效测试, 排除 51 timeout)
...
```

## 📊 数据提取规则

### 5.1 基准测试提取
- **配置**: optimal prompt, easy难度, 0.8工具成功率
- **模型**: 8个开源模型 (DeepSeek, Llama, Qwen系列)
- **输出**: 总体成功率、完全成功率、部分成功率、失败率

### 5.2 Qwen规模效应提取  
- **配置**: optimal prompt, very_easy/medium难度, 0.8工具成功率
- **模型**: 5个Qwen系列模型 (3B-72B)
- **输出**: 任务特定成功率、整体成功率、每参数效率得分

### 5.3 缺陷工作流适应性提取
- **配置**: 7种flawed prompt类型, easy难度, 0.8工具成功率
- **模型**: 8个开源模型
- **输出**: 各缺陷类型纠正率、平均适应性得分

## 🔍 Timeout处理详解

### 处理逻辑
1. **识别timeout失败**: 从总失败中识别因超时导致的失败
2. **计算有效测试数**: 排除timeout失败后的测试总数
3. **重新计算成功率**: 基于有效测试数计算准确的成功率

### 重要意义
- **提升数据质量**: 排除系统性问题，关注模型能力
- **公平比较**: 不同模型在相同有效条件下的表现对比
- **科学严谨**: 实验结果更准确反映模型真实性能

## 🛠️ 技术细节

### 类结构
```python
class WorkflowBenchDataExtractor:
    def __init__(db_path)                          # 初始化数据库连接
    def _calculate_timeout_excluded_stats()        # 核心计算方法
    def extract_5_1_baseline_results()             # 提取5.1数据
    def extract_5_2_qwen_scale_results()           # 提取5.2数据  
    def extract_5_3_flawed_workflow_results()      # 提取5.3数据
    def generate_markdown_tables()                 # 生成表格文件
```

### 数据库路径
- **默认**: `pilot_bench_cumulative_results/master_database.json`
- **层次**: models → by_prompt_type → by_tool_success_rate → by_difficulty → by_task_type

## 📈 影响分析

### Timeout排除的影响
- **5.1测试**: 排除52个timeout，DeepSeek-R1-0528从47.5%提升到63.9%
- **5.2测试**: 排除13个timeout，Qwen模型微幅提升
- **5.3测试**: 排除6个timeout，DeepSeek系列适应性得分微幅提升

### 数据质量提升
- **总计排除**: 71个timeout失败测试
- **准确性**: 更真实反映模型能力而非系统问题
- **可比性**: 不同模型在相同条件下的公平比较

## 🎯 使用建议

1. **论文写作**: 使用 `generate` 命令生成标准化表格
2. **数据分析**: 使用特定命令 (5.1/5.2/5.3) 进行深入分析
3. **质量检查**: 定期运行确保数据一致性
4. **备份数据**: 重要修改前先备份master_database.json

## 🔧 维护说明

- **更新频率**: 每次master_database.json更新后运行
- **版本控制**: 脚本变更需更新CLAUDE.md维护记录
- **测试要求**: 重要修改后必须测试所有功能
- **文档同步**: 功能变更需同步更新本指南

---
**创建时间**: 2025-08-30  
**最后更新**: 2025-08-30  
**维护者**: Claude Assistant  
**状态**: ✅ 已验证 | 📊 已集成到项目文档系统