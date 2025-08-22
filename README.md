# PILOT-Bench Scale-Up 测试系统 v3.0

## 📋 项目概述

PILOT-Bench Scale-Up 是一个用于评估大语言模型在工作流执行任务上的性能的综合测试系统。支持开源和闭源模型的批量测试、性能分析和结果管理。

**版本**: 3.0.0  
**状态**: 🟢 Active Development  
**更新**: 2025-08-17

## 🆕 v3.0 新特性

- **双存储格式支持**: JSON + Parquet，提升并发性能
- **模型名称标准化**: 自动统一并行实例命名
- **完整项目重构**: 标准化目录结构和文档体系
- **增强调试支持**: Debug知识库v2和故障排除指南
- **数据迁移工具**: JSON到Parquet无缝转换

## 🚀 快速开始

### 1. 选择存储格式

```bash
# 方式1：运行时选择
./run_systematic_test_final.sh  # 显示选择菜单

# 方式2：环境变量
export STORAGE_FORMAT=parquet  # 推荐：并发安全
export STORAGE_FORMAT=json     # 兼容模式
```

### 2. 运行系统测试

```bash
# 交互式菜单
./run_systematic_test_final.sh

# 直接运行（自动模式）
./run_systematic_test_final.sh --auto

# 全自动模式（无需确认）
./run_systematic_test_final.sh --full-auto
```

### 3. 查看测试进度

```bash
# 查看综合进度
python view_test_progress.py

# 查看失败测试
python enhanced_failed_tests_manager.py status

# 生成测试报告
python analyze_test_results.py
```

### 4. 运行维护系统

```bash
# 自动维护
python auto_failure_maintenance_system.py maintain

# 查看系统状态
python auto_failure_maintenance_system.py status

# 项目组织
./organize_project.sh
```

## 📊 支持的模型

### 开源模型（8个）
- DeepSeek-V3-0324 (Azure) ✅
- DeepSeek-R1-0528 (Azure) ✅
- Qwen2.5-72B-Instruct (IdealLab)
- Qwen2.5-32B-Instruct (IdealLab)
- Qwen2.5-14B-Instruct (IdealLab)
- Qwen2.5-7B-Instruct (IdealLab)
- Qwen2.5-3B-Instruct (IdealLab)
- Llama-3.3-70B-Instruct (Azure) ✅

### 闭源模型（5个）
- gpt-4o-mini (Azure) ✅
- gpt-5-mini (Azure) ✅
- o3-0416-global (IdealLab) ✅
- gemini-2.5-flash-06-17 (IdealLab) ⚠️
- kimi-k2 (IdealLab) ✅

## 📁 项目结构

```
scale_up/
├── src/                    # 源代码
│   ├── runners/           # 测试运行器
│   ├── managers/          # 数据管理器
│   └── analyzers/         # 结果分析器
├── scripts/               # 脚本集合
│   ├── test/             # 测试脚本
│   └── maintenance/      # 维护脚本
├── docs/                  # 文档
│   ├── guides/           # 使用指南
│   └── maintenance/      # 维护文档
├── pilot_bench_cumulative_results/  # 测试数据
│   ├── master_database.json        # JSON格式
│   └── parquet_data/               # Parquet格式
└── archive/               # 归档文件
```

## 🔧 核心功能

### 批量测试运行器
- `smart_batch_runner.py` - 智能批量测试
- `ultra_parallel_runner.py` - 超并行测试
- `batch_test_runner.py` - 基础批量测试

### 数据管理器
- `cumulative_test_manager.py` - JSON数据管理
- `parquet_cumulative_manager.py` - Parquet数据管理
- `unified_storage_manager.py` - 统一存储接口

### 分析工具
- `view_test_progress.py` - 进度查看
- `analyze_test_results.py` - 结果分析
- `analyze_5_3_test_coverage.py` - 覆盖率分析

## 📈 测试配置参数

### 提示类型 (prompt_types)
- `optimal` - 最优提示策略
- `baseline` - 基准提示
- `cot` - 思维链提示
- `flawed_*` - 缺陷工作流测试

### 难度级别 (difficulty)
- `very_easy` - 极简任务
- `easy` - 简单任务
- `medium` - 中等难度
- `hard` - 困难任务

### 任务类型 (task_types)
- `simple_task` - 简单任务
- `basic_task` - 基础任务
- `intermediate_task` - 中级任务
- `advanced_task` - 高级任务

### 工具成功率 (tool_success_rate)
- `0.9` - 90%成功率
- `0.8` - 80%成功率（默认）
- `0.7` - 70%成功率
- `0.6` - 60%成功率

## 🔍 常用命令示例

```bash
# 运行特定模型测试
python smart_batch_runner.py \
  --model gpt-4o-mini \
  --prompt-types optimal \
  --difficulty easy \
  --task-types simple_task \
  --num-instances 10

# 使用Parquet格式运行
STORAGE_FORMAT=parquet python smart_batch_runner.py \
  --model DeepSeek-V3-0324 \
  --prompt-types baseline \
  --difficulty medium

# 查看特定模型进度
python view_test_progress.py --model gpt-4o-mini

# JSON到Parquet数据迁移
python json_to_parquet_converter.py

# 模型名称标准化
python normalize_model_names.py
```

## 📚 文档索引

- [CLAUDE.md](./CLAUDE.md) - 项目主文档
- [DATA_SYNC_GUIDE.md](./DATA_SYNC_GUIDE.md) - 数据同步指南 ⭐ NEW
- [DOCUMENTATION_INDEX.md](./DOCUMENTATION_INDEX.md) - 完整文档索引
- [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - 快速参考
- [DEBUG_KNOWLEDGE_BASE_V2.md](./DEBUG_KNOWLEDGE_BASE_V2.md) - 调试指南
- [PARQUET_GUIDE.md](./PARQUET_GUIDE.md) - Parquet使用指南

## 🐛 故障排除

遇到问题时：
1. 查看 [COMMON_ISSUES_V2.md](./COMMON_ISSUES_V2.md)
2. 检查 `logs/` 目录下的日志
3. 运行诊断工具：`python diagnose_issues.py`

## 🤝 贡献指南

1. 遵守STRICT代码管理规范
2. 所有修改需更新相关文档
3. 提交前运行测试验证
4. 保持代码和文档同步

## 📄 许可证

本项目采用内部许可，仅供授权用户使用。

---

*最后更新: 2025-08-17 | 版本: 3.0.0 | 维护者: Claude Assistant*