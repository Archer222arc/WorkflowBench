# 📚 文档索引 (Documentation Index)

> 最后更新: 2025-08-17  
> 文档总数: 30+  
> 状态: 🟢 Active

## 🗂️ 文档分类

### 🔧 维护文档 (`docs/maintenance/`)
- **[DEBUG_KNOWLEDGE_BASE_V2.md](./maintenance/DEBUG_KNOWLEDGE_BASE_V2.md)** 🆕
  - 调试知识库V2.0，包含Parquet调试、API问题、性能分析
  - 关键词: `调试`, `故障排除`, `性能`, `监控`

- **[COMMON_ISSUES_V2.md](./maintenance/COMMON_ISSUES_V2.md)** 🆕
  - 常见问题解决方案V2.0，按紧急程度分类
  - 关键词: `错误`, `解决方案`, `快速修复`

- **[SYSTEM_MAINTENANCE_GUIDE.md](./maintenance/SYSTEM_MAINTENANCE_GUIDE.md)** 🆕
  - 系统维护完整指南，包含日常维护、定期任务、故障恢复
  - 关键词: `维护`, `备份`, `恢复`, `监控`

- **[CODE_CONVENTIONS.md](./maintenance/CODE_CONVENTIONS.md)**
  - 代码规范和最佳实践
  - 关键词: `规范`, `最佳实践`, `代码风格`

### 📖 使用指南 (`docs/guides/`)
- **[PARQUET_GUIDE.md](./guides/PARQUET_GUIDE.md)** 🆕
  - Parquet存储模式完整指南
  - 关键词: `Parquet`, `数据存储`, `性能优化`, `并发`

- **[BATCH_TEST_USAGE.md](./guides/BATCH_TEST_USAGE.md)**
  - 批量测试使用指南
  - 关键词: `批量测试`, `并行`, `配置`

- **[PARALLEL_TESTING_GUIDE.md](./guides/PARALLEL_TESTING_GUIDE.md)**
  - 并行测试指南
  - 关键词: `并行`, `多进程`, `性能`

- **[FAILED_TESTS_GUIDE.md](./guides/FAILED_TESTS_GUIDE.md)**
  - 失败测试处理指南
  - 关键词: `失败处理`, `重试`, `恢复`

### 🌐 API文档 (`docs/api/`)
- **[API_REFERENCE.md](./api/API_REFERENCE.md)**
  - API参考文档
  - 关键词: `API`, `接口`, `参数`

- **[CLOSED_SOURCE_API_CONFIG.md](./api/CLOSED_SOURCE_API_CONFIG.md)**
  - 闭源模型API配置
  - 关键词: `配置`, `认证`, `端点`

- **[MODEL_ROUTING_GUIDE.md](./api/MODEL_ROUTING_GUIDE.md)**
  - 模型路由指南
  - 关键词: `路由`, `负载均衡`, `故障转移`

- **[API_TROUBLESHOOTING.md](./api/API_TROUBLESHOOTING.md)**
  - API故障排除
  - 关键词: `超时`, `限流`, `错误码`

### 🏗️ 架构文档 (`docs/architecture/`)
- **[SYSTEM_ARCHITECTURE.md](./architecture/SYSTEM_ARCHITECTURE.md)**
  - 系统架构总览
  - 关键词: `架构`, `组件`, `设计`

- **[DATABASE_STRUCTURE_V3.md](./architecture/DATABASE_STRUCTURE_V3.md)**
  - 数据库结构V3
  - 关键词: `数据结构`, `层次`, `JSON`, `Parquet`

- **[DATA_FLOW_STATUS.md](./architecture/DATA_FLOW_STATUS.md)**
  - 数据流状态
  - 关键词: `数据流`, `处理流程`, `状态管理`

### 📊 报告文档 (`docs/reports/`)
- **[系统化测试结果汇总.md](./reports/系统化测试结果汇总.md)**
  - 完整测试结果报告
  - 关键词: `测试结果`, `统计`, `分析`

- **[5.1_基准测试结果表.md](./reports/5.1_基准测试结果表.md)**
  - 基准测试数据
  - 关键词: `基准`, `性能`, `对比`

- **[5.2_Qwen规模效应测试表.md](./reports/5.2_Qwen规模效应测试表.md)**
  - Qwen系列规模效应分析
  - 关键词: `Qwen`, `规模`, `效应`

---

## 🔍 快速查找

### 按问题类型
| 问题类型 | 推荐文档 |
|---------|---------|
| **系统崩溃** | [SYSTEM_MAINTENANCE_GUIDE.md](./maintenance/SYSTEM_MAINTENANCE_GUIDE.md) → 故障恢复 |
| **数据丢失** | [COMMON_ISSUES_V2.md](./maintenance/COMMON_ISSUES_V2.md) → 紧急问题 |
| **API超时** | [API_TROUBLESHOOTING.md](./api/API_TROUBLESHOOTING.md) |
| **内存泄漏** | [DEBUG_KNOWLEDGE_BASE_V2.md](./maintenance/DEBUG_KNOWLEDGE_BASE_V2.md) → 性能调试 |
| **并发冲突** | [PARQUET_GUIDE.md](./guides/PARQUET_GUIDE.md) → 并发控制 |
| **测试失败** | [FAILED_TESTS_GUIDE.md](./guides/FAILED_TESTS_GUIDE.md) |

### 按任务类型
| 任务 | 推荐文档 |
|------|---------|
| **开始测试** | [BATCH_TEST_USAGE.md](./guides/BATCH_TEST_USAGE.md) |
| **配置模型** | [CLOSED_SOURCE_API_CONFIG.md](./api/CLOSED_SOURCE_API_CONFIG.md) |
| **数据迁移** | [PARQUET_GUIDE.md](./guides/PARQUET_GUIDE.md) → 数据迁移 |
| **日常维护** | [SYSTEM_MAINTENANCE_GUIDE.md](./maintenance/SYSTEM_MAINTENANCE_GUIDE.md) → 日常维护 |
| **性能优化** | [DEBUG_KNOWLEDGE_BASE_V2.md](./maintenance/DEBUG_KNOWLEDGE_BASE_V2.md) → 性能调试 |
| **生成报告** | [系统化测试结果汇总.md](./reports/系统化测试结果汇总.md) |

---

## 📝 文档更新记录

### 2025-08-17 更新
- 🆕 创建 `DEBUG_KNOWLEDGE_BASE_V2.md` - 包含Parquet调试
- 🆕 创建 `COMMON_ISSUES_V2.md` - 重新组织问题分类
- 🆕 创建 `SYSTEM_MAINTENANCE_GUIDE.md` - 完整维护指南
- 🆕 创建 `PARQUET_GUIDE.md` - Parquet使用完整指南
- 🆕 创建本索引文档

### 2025-08-16 更新
- 更新 `DATABASE_STRUCTURE_V3.md` - 添加Parquet支持
- 更新 `API_REFERENCE.md` - 添加新模型配置

---

## 🛠️ 快速命令

### 查看特定文档
```bash
# Markdown查看器
mdless docs/maintenance/DEBUG_KNOWLEDGE_BASE_V2.md

# 或使用cat
cat docs/guides/PARQUET_GUIDE.md

# 搜索关键词
grep -r "Parquet" docs/
```

### 生成PDF文档
```bash
# 安装pandoc
brew install pandoc

# 转换为PDF
pandoc docs/maintenance/SYSTEM_MAINTENANCE_GUIDE.md -o maintenance.pdf
```

### 文档统计
```bash
# 统计文档数量
find docs/ -name "*.md" | wc -l

# 统计总行数
find docs/ -name "*.md" -exec wc -l {} + | tail -1

# 查找最新更新
find docs/ -name "*.md" -mtime -7  # 7天内更新的文档
```

---

## 🔗 外部资源

### 官方文档
- [Python官方文档](https://docs.python.org/)
- [Pandas文档](https://pandas.pydata.org/docs/)
- [PyArrow文档](https://arrow.apache.org/docs/python/)

### 相关项目
- [OpenAI API文档](https://platform.openai.com/docs/)
- [Azure OpenAI文档](https://docs.microsoft.com/azure/cognitive-services/openai/)

---

**索引版本**: 1.0  
**创建时间**: 2025-08-17  
**维护者**: System Administrator  
**状态**: 🟢 Active | ✅ 完整