# 文档清理计划

## 需要合并的重复文档

### 1. 存储系统文档（7个可合并为2-3个）
重复文档：
- PARQUET_STORAGE_GUIDE.md
- PARQUET_ARCHITECTURE.md  
- STORAGE_FORMAT_GUIDE.md
- STORAGE_VALIDATION_REPORT.md
- DATA_SYNC_GUIDE.md
- docs/guides/PARQUET_GUIDE.md
- docs/guides/DATA_SYNC_GUIDE.md

**建议**：合并为一个综合的 `STORAGE_SYSTEM_GUIDE.md`

### 2. 调试知识库（4个版本）
重复文档：
- docs/maintenance/DEBUG_KNOWLEDGE_BASE.md
- docs/maintenance/DEBUG_KNOWLEDGE_BASE_V2.md
- docs/maintenance/DEBUG_HISTORY.md
- docs/maintenance/debug_logs/

**建议**：保留V2版本，其他归档

### 3. 常见问题文档（2个版本）
重复文档：
- docs/maintenance/COMMON_ISSUES.md
- docs/maintenance/COMMON_ISSUES_V2.md

**建议**：保留V2版本，V1归档

### 4. 模型标准化文档（3个相似）
重复文档：
- MODEL_NAME_NORMALIZATION_FIX.md
- MODEL_NORMALIZATION_SUMMARY.md
- normalize_model_names.py（代码）

**建议**：合并到 MODEL_NAMING_CONVENTION.md

### 5. 并发写入修复文档（2个）
重复文档：
- CONCURRENT_WRITE_FIX_SUMMARY.md
- docs/maintenance/debug_logs/2025-08-16_concurrent_write_fix.md

**建议**：归档到debug_logs

## 需要归档的过时文档

### 临时调试文档（移到archive/debug/）
- RUN_SYSTEMATIC_TEST_ISSUE.md
- STUCK_PROCESS_ANALYSIS.md
- root_cause_analysis.md
- root_cause_deep_analysis.md
- real_root_cause_analysis.md
- worker_stuck_analysis.md
- timeout_error_classification.md
- timeout_explanation.md
- why_api_call_takes_5min.md
- why_search_takes_30min.md
- llm_search_loop_explanation.md
- api_retry_and_signal_explanation.md

### 已完成的修复报告（移到archive/fixes/）
- FIX_COMPLETE_REPORT.md
- checkpoint_fix_summary.md
- data_sync_validation_report.md
- critical_issues_status.md

### 旧版本文档（移到archive/old_docs/）
- DOCUMENTATION_INDEX.md（被新索引替代）
- ARCHIVE_REPORT.md（2025-08-16之前的）
- WINDOWS_COMPATIBILITY.md（如果不再支持）
- WSL_SETUP_GUIDE.md（如果不再需要）

## 需要更新的文档

### 高优先级更新
1. **README.md** - 添加新的模型命名规范链接
2. **CLAUDE.md** - 确保包含最新的所有重要信息
3. **QUICK_REFERENCE.md** - 更新命令和配置

### 中优先级更新
1. **PROJECT_STRUCTURE.md** - 反映最新的目录结构
2. **docs/api/API_REFERENCE.md** - 添加并行实例说明
3. **docs/guides/BATCH_TEST_USAGE.md** - 更新参数说明

## 建议的新文档结构

```
scale_up/
├── 📚 核心文档/
│   ├── README.md
│   ├── CLAUDE.md（主文档）
│   ├── QUICK_REFERENCE.md
│   └── PROJECT_STRUCTURE.md
│
├── 📖 docs/
│   ├── architecture/（系统架构）
│   ├── api/（API配置）
│   ├── guides/（使用指南）
│   ├── maintenance/（维护文档）
│   ├── reports/（测试报告）
│   └── storage/（存储系统）🆕
│
├── 📊 test_results/（测试结果表格）
│   ├── 5.1_基准测试.md
│   ├── 5.2_规模效应.md
│   ├── 5.3_缺陷适应性.md
│   ├── 5.4_工具可靠性.md
│   └── 5.5_提示敏感性.md
│
├── 🗄️ archive/（归档文档）
│   ├── debug/（调试文档）
│   ├── fixes/（修复报告）
│   ├── old_docs/（旧版文档）
│   └── temp/（临时文档）
│
└── 📝 active/（活跃文档）
    ├── debug_to_do.txt
    ├── CHANGELOG.md
    └── MODEL_NAMING_CONVENTION.md
```

## 执行步骤

### 第一阶段：备份（立即）
1. 创建 `docs_backup_20250818/` 目录
2. 复制所有现有文档

### 第二阶段：归档（今天）
1. 移动过时文档到 `archive/`
2. 移动临时文档到 `archive/temp/`
3. 移动修复报告到 `archive/fixes/`

### 第三阶段：合并（本周）
1. 合并存储系统文档
2. 合并调试知识库
3. 合并模型标准化文档

### 第四阶段：重组（下周）
1. 创建新的目录结构
2. 移动文档到正确位置
3. 更新所有内部链接

### 第五阶段：维护（持续）
1. 建立文档审查机制
2. 定期清理过时内容
3. 保持索引更新

## 预期结果

- **文档数量**：从150+减少到50-60个核心文档
- **重复内容**：消除90%的重复
- **查找效率**：提升3倍
- **维护成本**：降低50%

## 风险控制

1. **所有操作前先备份**
2. **保留原始文件至少30天**
3. **逐步执行，不要一次性删除**
4. **更新后测试所有链接**

---

**计划制定**: 2025-08-18  
**执行负责**: Claude Assistant  
**审核**: 用户确认后执行