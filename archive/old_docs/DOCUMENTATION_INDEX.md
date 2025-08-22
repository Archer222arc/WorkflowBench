# 文档索引目录

## 📚 核心文档

### 主要文档
- [CLAUDE.md](./CLAUDE.md) - Claude Assistant项目文档（核心）
- [README.md](./README.md) - 项目说明
- [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - 快速参考指南
- [PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md) - 项目结构说明

### 数据管理文档
- [PARQUET_GUIDE.md](./PARQUET_GUIDE.md) - Parquet使用指南
- [MODEL_NAME_NORMALIZATION_FIX.md](./MODEL_NAME_NORMALIZATION_FIX.md) - 模型名称标准化修复说明
- [CONCURRENT_WRITE_FIX_SUMMARY.md](./CONCURRENT_WRITE_FIX_SUMMARY.md) - 并发写入修复总结

## 🔧 维护文档

### Debug和故障排除
- [DEBUG_KNOWLEDGE_BASE_V2.md](./DEBUG_KNOWLEDGE_BASE_V2.md) - 调试知识库v2
- [DEBUG_KNOWLEDGE_BASE.md](./DEBUG_KNOWLEDGE_BASE.md) - 调试知识库v1
- [COMMON_ISSUES_V2.md](./COMMON_ISSUES_V2.md) - 常见问题解决方案v2
- [COMMON_ISSUES.md](./COMMON_ISSUES.md) - 常见问题解决方案v1

### 系统维护
- [SYSTEM_MAINTENANCE_GUIDE.md](./SYSTEM_MAINTENANCE_GUIDE.md) - 系统维护指南
- [AUTO_MAINTENANCE_PROGRESS.md](./AUTO_MAINTENANCE_PROGRESS.md) - 自动维护进度
- [MAINTENANCE_STATUS.md](./MAINTENANCE_STATUS.md) - 维护状态

## 📊 测试报告

### 5系列测试报告
- [5.1_基准测试结果表.md](./5.1_基准测试结果表.md) - 基准测试结果
- [5.2_Qwen规模效应测试表.md](./5.2_Qwen规模效应测试表.md) - Qwen规模效应测试
- [5.3_缺陷工作流适应性测试表.md](./5.3_缺陷工作流适应性测试表.md) - 缺陷工作流测试
- [5.4_工具可靠性敏感性测试表.md](./5.4_工具可靠性敏感性测试表.md) - 工具可靠性测试
- [5.5_提示类型敏感性测试表.md](./5.5_提示类型敏感性测试表.md) - 提示类型测试

### 规模效应分析
- [4.2.1_Qwen系列规模效应汇总表.md](./4.2.1_Qwen系列规模效应汇总表.md) - Qwen规模效应汇总

### 测试结果汇总
- [系统化测试结果汇总.md](./系统化测试结果汇总.md) - 整体测试结果
- [数据存储状况说明.md](./数据存储状况说明.md) - 数据存储说明

## 🛠️ 技术文档

### API和配置
- [CLOSED_SOURCE_API_CONFIG.md](./CLOSED_SOURCE_API_CONFIG.md) - 闭源API配置
- [BATCH_TEST_USAGE.md](./BATCH_TEST_USAGE.md) - 批量测试使用说明
- [PARALLEL_TESTING_GUIDE.md](./PARALLEL_TESTING_GUIDE.md) - 并行测试指南

### 系统架构
- [SYSTEM_ARCHITECTURE.md](./SYSTEM_ARCHITECTURE.md) - 系统架构
- [DATABASE_STRUCTURE_V3.md](./DATABASE_STRUCTURE_V3.md) - 数据库结构v3
- [DATA_FLOW_STATUS.md](./DATA_FLOW_STATUS.md) - 数据流状态

## 📂 归档文档

### 历史文档
- archive/docs/ - 历史版本文档
- archive/debug_scripts/ - 调试脚本归档
- archive/test_scripts/ - 测试脚本归档

## 🔍 快速导航

### 常用命令
```bash
# 查看项目状态
./run_systematic_test_final.sh

# 运行测试
python smart_batch_runner.py --model <model> --prompt-types <type> --difficulty <level>

# 查看进度
python view_test_progress.py

# 组织项目
./organize_project.sh
```

### 重要路径
- 测试结果: `pilot_bench_cumulative_results/`
- 日志文件: `logs/`
- 配置文件: `config/`
- 归档文件: `archive/`

## 更新记录

- 2025-08-17: 创建文档索引
- 2025-08-16: 整理项目结构，归档历史文件
- 2025-08-15: 添加Parquet支持，修复并发问题

---

*本索引由项目组织工具自动生成*
