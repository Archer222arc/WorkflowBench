# PILOT-Bench 快速参考指南 v3.0

## 🎯 最常用命令

### 运行测试
```bash
# 标准测试（JSON格式）
./run_systematic_test_final.sh

# Parquet格式测试（推荐）
export STORAGE_FORMAT=parquet
./run_systematic_test_final.sh --auto

# 指定模型测试
python smart_batch_runner.py --model gpt-4o-mini --prompt-types optimal --difficulty easy
```

### 查看进度
```bash
# 综合进度
python view_test_progress.py

# 特定模型
python view_test_progress.py --model DeepSeek-V3-0324

# 失败测试
python enhanced_failed_tests_manager.py status
```

### 数据管理
```bash
# JSON到Parquet转换
python json_to_parquet_converter.py

# 模型名称标准化
python normalize_model_names.py

# 查看数据库统计
python analyze_test_results.py
```

## 📊 模型速查表

### 开源模型
| 模型名称 | API端点 | 状态 | 备注 |
|---------|---------|------|------|
| DeepSeek-V3-0324 | Azure | ✅ | 支持max_completion_tokens |
| DeepSeek-R1-0528 | Azure | ✅ | 支持max_completion_tokens |
| qwen2.5-72b-instruct | IdealLab | ✅ | 最大规模 |
| qwen2.5-32b-instruct | IdealLab | ✅ | - |
| qwen2.5-14b-instruct | IdealLab | ✅ | - |
| qwen2.5-7b-instruct | IdealLab | ✅ | - |
| qwen2.5-3b-instruct | IdealLab | ✅ | 最小规模 |
| Llama-3.3-70B-Instruct | Azure | ✅ | 支持max_completion_tokens |

### 闭源模型
| 模型名称 | API端点 | 状态 | 备注 |
|---------|---------|------|------|
| gpt-4o-mini | Azure | ✅ | 稳定 |
| gpt-5-mini | Azure | ✅ | 需简化参数 |
| o3-0416-global | IdealLab | ✅ | - |
| gemini-2.5-flash-06-17 | IdealLab | ⚠️ | 可能返回空content |
| kimi-k2 | IdealLab | ✅ | 新增 |

## 🔧 测试参数组合

### 标准测试（5.1基准）
```bash
--prompt-types optimal
--difficulty easy
--task-types simple_task
--tool-success-rate 0.8
--num-instances 100
```

### 规模效应测试（5.2 Qwen）
```bash
# 对每个Qwen模型运行
--prompt-types optimal
--difficulty very_easy,easy,medium
--task-types simple_task
--num-instances 50
```

### 缺陷工作流测试（5.3）
```bash
--prompt-types flawed_incomplete,flawed_ambiguous,flawed_sequence_disorder
--difficulty easy
--task-types simple_task
--num-instances 30
```

### 工具可靠性测试（5.4）
```bash
--prompt-types optimal
--difficulty easy
--task-types simple_task
--tool-success-rate 0.9,0.8,0.7,0.6
--num-instances 25
```

### 提示敏感性测试（5.5）
```bash
--prompt-types optimal,baseline,cot
--difficulty easy
--task-types simple_task
--num-instances 30
```

## 🛠️ 环境变量

```bash
# 存储格式选择
export STORAGE_FORMAT=parquet  # 或 json

# API配置
export AZURE_OPENAI_API_KEY=xxx
export AZURE_OPENAI_ENDPOINT=xxx
export IDEALLAB_API_KEY=xxx

# 并发控制
export MAX_WORKERS=10
export QPS_LIMIT=5

# 调试模式
export DEBUG=true
export VERBOSE=true
```

## 📁 重要文件路径

### 数据文件
- JSON数据库: `pilot_bench_cumulative_results/master_database.json`
- Parquet主文件: `pilot_bench_cumulative_results/parquet_data/master_data.parquet`
- 增量文件: `pilot_bench_cumulative_results/parquet_data/incremental/`

### 日志文件
- 批量测试日志: `logs/batch_test_*.log`
- 调试日志: `logs/debug_*.log`
- 错误报告: `runtime_reports/runtime_error_report_*.json`

### 配置文件
- 模型配置: `model_config_manager.py`
- API路由: `model_api_router.py`
- 存储配置: `unified_storage_manager.py`

## 🚨 常见问题快速解决

### 1. 并发写入冲突
```bash
# 使用Parquet格式
export STORAGE_FORMAT=parquet
```

### 2. API超时
```python
# 在model_config_manager.py中调整
"timeout": 60  # 增加超时时间
```

### 3. 模型名称不一致
```bash
# 运行标准化
python normalize_model_names.py
```

### 4. 内存不足
```bash
# 减少并发数
--max-workers 5
```

### 5. 数据恢复
```bash
# 从备份恢复
cp pilot_bench_cumulative_results/master_database.backup \
   pilot_bench_cumulative_results/master_database.json
```

## 📊 进度监控

### 实时监控
```bash
# 终端1：运行测试
./run_systematic_test_final.sh --auto

# 终端2：监控进度
watch -n 5 'python view_test_progress.py | tail -20'

# 终端3：监控日志
tail -f logs/batch_test_*.log
```

### 生成报告
```bash
# 综合报告
python analyze_test_results.py > test_report.txt

# 5.3专项报告
python analyze_5_3_test_coverage.py

# 失败分析
python enhanced_failed_tests_manager.py report
```

## 🔄 维护操作

### 日常维护
```bash
# 自动维护
python auto_failure_maintenance_system.py maintain

# 清理日志
find logs/ -name "*.log" -mtime +7 -delete

# 备份数据
cp pilot_bench_cumulative_results/master_database.json \
   pilot_bench_cumulative_results/master_database.$(date +%Y%m%d).backup
```

### 项目整理
```bash
# 归档旧文件
./archive_and_cleanup.sh

# 组织项目结构
./organize_project.sh

# 更新文档
python update_documentation.py
```

## 💡 性能优化建议

1. **使用Parquet格式**: 并发性能提升50%+
2. **合理设置并发数**: IdealLab建议5-10，Azure建议10-20
3. **启用自适应QPS**: `--adaptive` 自动调整请求速率
4. **使用断点续传**: 测试中断后自动恢复
5. **定期清理日志**: 避免磁盘空间不足

## 🔗 快速链接

- [完整文档](./CLAUDE.md)
- [调试指南](./DEBUG_KNOWLEDGE_BASE_V2.md)
- [常见问题](./COMMON_ISSUES_V2.md)
- [Parquet指南](./PARQUET_GUIDE.md)
- [维护指南](./SYSTEM_MAINTENANCE_GUIDE.md)

---

*版本: 3.0.0 | 更新: 2025-08-17 | 快速参考指南*
