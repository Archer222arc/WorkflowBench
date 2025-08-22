# 系统文档索引 - WorkflowBench Scale-Up

> 最后更新：2025-08-18 14:00  
> 文档总数：~60（优化后）  
> 组织状态：✅ 已清理和重组

## 📚 核心文档（必读）

### 主要文档
- **[CLAUDE.md](./CLAUDE.md)** ⭐ - 项目主文档，包含所有核心信息
- **[README.md](./README.md)** - 项目总体说明
- **[QUICK_REFERENCE.md](./QUICK_REFERENCE.md)** - 快速参考指南
- **[PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md)** - 项目结构说明

### 最新规范
- **[MODEL_NAMING_CONVENTION.md](./MODEL_NAMING_CONVENTION.md)** 🆕 - 模型命名规范（2025-08-18）
- **[STORAGE_SYSTEM_GUIDE.md](./STORAGE_SYSTEM_GUIDE.md)** 🆕 - 存储系统综合指南（合并7个文档）
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

### 6. 🐛 近期问题分析
- [5_3_TEST_SUCCESS_ANALYSIS.md](./5_3_TEST_SUCCESS_ANALYSIS.md) - 5.3测试成功分析
- [REAL_BOTTLENECK_ANALYSIS.md](./REAL_BOTTLENECK_ANALYSIS.md) - 真实瓶颈分析
- [PARQUET_CONCURRENCY_ANALYSIS.md](./PARQUET_CONCURRENCY_ANALYSIS.md) - Parquet并发分析
- [ULTRA_RUNNER_MODEL_MAPPING_ISSUES.md](./ULTRA_RUNNER_MODEL_MAPPING_ISSUES.md) - Ultra Runner问题

### 7. 📈 测试结果表格
- [5.1_基准测试结果表.md](./5.1_基准测试结果表.md)
- [5.2_Qwen规模效应测试表.md](./5.2_Qwen规模效应测试表.md)
- [5.3_缺陷工作流适应性测试表.md](./5.3_缺陷工作流适应性测试表.md)
- [5.4_工具可靠性敏感性测试表.md](./5.4_工具可靠性敏感性测试表.md)
- [5.5_提示类型敏感性测试表.md](./5.5_提示类型敏感性测试表.md)
- [4.2.1_Qwen系列规模效应汇总表.md](./4.2.1_Qwen系列规模效应汇总表.md)

### 8. 🗄️ 归档文档
位置：`archive/`
- `debug/` - 临时调试文档（20+个文件）
- `fixes/` - 已完成的修复报告（10+个文件）
- `old_docs/` - 旧版本文档（15+个文件）
- `temp/` - 临时文件

## 📊 文档清理成果

### 清理前后对比
| 指标 | 清理前 | 清理后 | 改进 |
|------|--------|--------|------|
| 文档总数 | 150+ | ~60 | -60% |
| 重复内容 | 30+ | 0 | -100% |
| 核心文档 | 分散 | 集中 | ✅ |
| 查找效率 | 低 | 高 | 3x |

### 主要改进
1. **合并存储文档**：7个文档 → 1个综合指南
2. **归档调试文档**：20+个临时文档移至archive/debug
3. **清理修复报告**：10+个已完成报告移至archive/fixes
4. **统一命名规范**：3个文档合并到MODEL_NAMING_CONVENTION.md

## 🏷️ 文档状态说明

### ✅ 活跃维护（经常更新）
- CLAUDE.md - 主文档
- debug_to_do.txt - 任务清单
- DEBUG_HISTORY.md - 调试记录
- CHANGELOG.md - 变更日志
- 测试结果表格（5.x系列）

### 📝 稳定文档（偶尔更新）
- 架构文档（docs/architecture/）
- API配置（docs/api/）
- 使用指南（docs/guides/）
- MODEL_NAMING_CONVENTION.md
- STORAGE_SYSTEM_GUIDE.md

### 🗑️ 已归档（不再更新）
- archive/debug/ - 历史调试文档
- archive/fixes/ - 已完成的修复
- archive/old_docs/ - 旧版本文档

## 🔄 文档维护计划

### 定期任务
- **每周**：更新测试结果表格
- **每月**：审查并归档过时文档
- **每季度**：重组文档结构

### 持续改进
1. 保持文档精简，避免重复
2. 及时归档临时文档
3. 定期更新索引
4. 维护清晰的分类结构

## 📞 文档问题反馈

如果发现文档问题：
1. 更新本索引文件
2. 在debug_to_do.txt中添加任务
3. 更新CLAUDE.md中的相关章节

---

**索引维护者**: Claude Assistant  
**创建时间**: 2025-08-18 13:10  
**最后更新**: 2025-08-18 14:00  
**状态**: ✅ 已完成重组和清理