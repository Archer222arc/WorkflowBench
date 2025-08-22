# 系统文档索引 - WorkflowBench Scale-Up

> 最后更新：2025-08-18 13:10  
> 文档总数：150+  
> 组织状态：需要清理和重组

## 📚 核心文档（必读）

### 主要文档
- **[CLAUDE.md](./CLAUDE.md)** ⭐ - 项目主文档，包含所有核心信息
- **[README.md](./README.md)** - 项目总体说明
- **[QUICK_REFERENCE.md](./QUICK_REFERENCE.md)** - 快速参考指南
- **[PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md)** - 项目结构说明

### 最新规范
- **[MODEL_NAMING_CONVENTION.md](./MODEL_NAMING_CONVENTION.md)** 🆕 - 模型命名规范（2025-08-18）
- **[debug_to_do.txt](./debug_to_do.txt)** - 当前待修复问题清单

## 📁 文档分类索引

### 1. 🏗️ 系统架构文档
位置：`docs/architecture/`
- [SYSTEM_ARCHITECTURE.md](docs/architecture/SYSTEM_ARCHITECTURE.md) - 系统架构概述
- [DATABASE_STRUCTURE_V3.md](docs/architecture/DATABASE_STRUCTURE_V3.md) - 数据库结构v3
- [DATA_FLOW_STATUS.md](docs/architecture/DATA_FLOW_STATUS.md) - 数据流状态
- [RATE_LIMIT_OPTIMIZATION_STRATEGY.md](docs/architecture/RATE_LIMIT_OPTIMIZATION_STRATEGY.md) - 速率限制优化策略

### 2. 🔌 API配置文档
位置：`docs/api/`
- [API_REFERENCE.md](docs/api/API_REFERENCE.md) - API参考手册
- [CLOSED_SOURCE_API_CONFIG.md](docs/api/CLOSED_SOURCE_API_CONFIG.md) - 闭源API配置
- [OPENSOURCE_MODELS_CONFIG.md](docs/api/OPENSOURCE_MODELS_CONFIG.md) - 开源模型配置
- [MODEL_ROUTING_GUIDE.md](docs/api/MODEL_ROUTING_GUIDE.md) - 模型路由指南
- [完整API可用性测试报告.md](docs/api/完整API可用性测试报告.md) - API测试报告

### 3. 📖 使用指南
位置：`docs/guides/`
- [BATCH_TEST_USAGE.md](docs/guides/BATCH_TEST_USAGE.md) - 批量测试使用说明
- [PARALLEL_TESTING_GUIDE.md](docs/guides/PARALLEL_TESTING_GUIDE.md) - 并行测试指南
- [FAILED_TESTS_GUIDE.md](docs/guides/FAILED_TESTS_GUIDE.md) - 失败测试处理
- [DATA_SYNC_GUIDE.md](docs/guides/DATA_SYNC_GUIDE.md) - 数据同步指南
- [PARQUET_GUIDE.md](docs/guides/PARQUET_GUIDE.md) - Parquet存储指南

### 4. 🔧 维护文档
位置：`docs/maintenance/`
- [SYSTEM_MAINTENANCE_GUIDE.md](docs/maintenance/SYSTEM_MAINTENANCE_GUIDE.md) - 系统维护指南
- [DEBUG_KNOWLEDGE_BASE_V2.md](docs/maintenance/DEBUG_KNOWLEDGE_BASE_V2.md) - 调试知识库v2
- [DEBUG_HISTORY.md](docs/maintenance/DEBUG_HISTORY.md) - 调试历史记录
- [COMMON_ISSUES_V2.md](docs/maintenance/COMMON_ISSUES_V2.md) - 常见问题v2
- [CODE_MANAGEMENT.md](docs/maintenance/CODE_MANAGEMENT.md) - 代码管理规范

### 5. 📊 测试报告
位置：`docs/reports/`
- [TEST_RESULTS_SUMMARY.md](docs/reports/TEST_RESULTS_SUMMARY.md) - 测试结果总结
- [FINAL_TEST_STATUS.md](docs/reports/FINAL_TEST_STATUS.md) - 最终测试状态
- [实验结果统计表格.md](docs/reports/实验结果统计表格.md) - 实验统计表

### 6. 💾 存储系统文档
根目录存储相关：
- [PARQUET_STORAGE_GUIDE.md](./PARQUET_STORAGE_GUIDE.md) - Parquet存储指南
- [PARQUET_ARCHITECTURE.md](./PARQUET_ARCHITECTURE.md) - Parquet架构
- [STORAGE_FORMAT_GUIDE.md](./STORAGE_FORMAT_GUIDE.md) - 存储格式指南
- [STORAGE_VALIDATION_REPORT.md](./STORAGE_VALIDATION_REPORT.md) - 存储验证报告

### 7. 🐛 问题分析文档
近期问题分析：
- [5_3_TEST_SUCCESS_ANALYSIS.md](./5_3_TEST_SUCCESS_ANALYSIS.md) - 5.3测试成功分析
- [REAL_BOTTLENECK_ANALYSIS.md](./REAL_BOTTLENECK_ANALYSIS.md) - 真实瓶颈分析
- [STUCK_PROCESS_ANALYSIS.md](./STUCK_PROCESS_ANALYSIS.md) - 进程卡死分析
- [PARQUET_CONCURRENCY_ANALYSIS.md](./PARQUET_CONCURRENCY_ANALYSIS.md) - Parquet并发分析
- [ULTRA_RUNNER_MODEL_MAPPING_ISSUES.md](./ULTRA_RUNNER_MODEL_MAPPING_ISSUES.md) - Ultra Runner问题

### 8. 📈 测试结果表格
根目录测试表格：
- [5.1_基准测试结果表.md](./5.1_基准测试结果表.md)
- [5.2_Qwen规模效应测试表.md](./5.2_Qwen规模效应测试表.md)
- [5.3_缺陷工作流适应性测试表.md](./5.3_缺陷工作流适应性测试表.md)
- [5.4_工具可靠性敏感性测试表.md](./5.4_工具可靠性敏感性测试表.md)
- [5.5_提示类型敏感性测试表.md](./5.5_提示类型敏感性测试表.md)

## 🗂️ 文档状态分类

### ✅ 活跃维护（经常更新）
- CLAUDE.md - 主文档
- debug_to_do.txt - 任务清单
- DEBUG_HISTORY.md - 调试记录
- CHANGELOG.md - 变更日志

### 📝 稳定文档（偶尔更新）
- 架构文档（docs/architecture/）
- API配置（docs/api/）
- 使用指南（docs/guides/）

### ⚠️ 需要整理的文档
- 多个存储相关文档（可能有重复）
- 多个分析报告（部分过时）
- 临时调试文档

### 🗑️ 建议删除/归档
- 重复的问题分析文档
- 过时的测试报告
- 临时调试文件

## 📊 文档统计

| 类别 | 数量 | 位置 |
|------|------|------|
| 核心文档 | 4 | 根目录 |
| 架构文档 | 8 | docs/architecture/ |
| API文档 | 10 | docs/api/ |
| 使用指南 | 18 | docs/guides/ |
| 维护文档 | 15 | docs/maintenance/ |
| 测试报告 | 13 | docs/reports/ |
| 问题分析 | 20+ | 根目录（需整理） |
| 测试表格 | 6 | 根目录 |
| 其他 | 50+ | 分散各处 |

## 🔄 文档维护建议

### 立即需要的行动
1. **清理重复文档** - 合并相似内容
2. **更新过时内容** - 标记或删除过时信息
3. **统一存储文档** - 将所有存储相关文档放到一个目录
4. **归档临时文件** - 移动到archive目录

### 长期改进
1. **建立文档模板** - 统一格式
2. **添加版本控制** - 文档版本号
3. **创建自动索引** - 自动生成文档列表
4. **定期审查机制** - 每月检查文档状态

## 🏷️ 文档标签说明

- ⭐ **必读** - 核心文档，所有开发者必须了解
- 🆕 **新增** - 最近添加的文档
- 📝 **更新** - 最近有重要更新
- ⚠️ **注意** - 包含重要警告或注意事项
- 🗑️ **废弃** - 计划删除或归档
- 🔧 **维护** - 需要定期更新

## 📞 文档问题反馈

如果发现文档问题：
1. 更新本索引文件
2. 在debug_to_do.txt中添加任务
3. 更新CLAUDE.md中的相关章节

---

**索引维护者**: Claude Assistant  
**创建时间**: 2025-08-18 13:10  
**状态**: 🔴 需要大规模整理