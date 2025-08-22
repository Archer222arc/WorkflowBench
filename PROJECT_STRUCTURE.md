# 项目结构说明

## 📁 目录结构

```
scale_up/
├── docs/                    # 文档目录
│   ├── api/                # API相关文档 (10个文件)
│   ├── guides/             # 使用指南 (18个文件)
│   ├── architecture/       # 架构文档 (9个文件)
│   ├── maintenance/        # 维护文档 (8个文件)
│   └── reports/           # 测试报告 (16个文件)
├── scripts/                # 脚本目录
│   ├── test/              # 测试脚本 (52个文件)
│   ├── utility/           # 工具脚本
│   └── maintenance/       # 维护脚本
├── config/                 # 配置文件
├── logs/                   # 日志文件 (621个，保留最近3天)
├── pilot_bench_cumulative_results/  # 测试结果数据库
├── workflow_quality_results/        # 工作流测试结果
└── archive/               # 归档文件
    ├── old_tests/         # 旧测试脚本
    └── old_docs/          # 旧文档
```

## 🔑 核心文件

### 主要执行脚本
- `run_systematic_test_final.sh` - 主测试脚本
- `smart_batch_runner.py` - 智能批量测试运行器
- `ultra_parallel_runner.py` - 超并行测试运行器
- `provider_parallel_runner.py` - 提供商并行运行器

### 核心模块
- `batch_test_runner.py` - 批量测试运行器
- `api_client_manager.py` - API客户端管理
- `smart_model_router.py` - 智能模型路由
- `enhanced_cumulative_manager.py` - 增强累积管理器
- `data_structure_v3.py` - 数据结构V3

### 配置文件
- `config/config.json` - 主配置文件
- `config/azure_models_config.json` - Azure模型配置

## 📊 数据文件

### 测试进度
- `test_progress_opensource.txt` - 开源模型进度
- `test_progress_closed_source.txt` - 闭源模型进度
- `completed_tests_opensource.txt` - 开源模型完成记录
- `completed_tests_closed_source.txt` - 闭源模型完成记录

### 数据库
- `pilot_bench_cumulative_results/master_database.json` - 开源模型数据库
- `pilot_bench_cumulative_results/master_database_closed_source.json` - 闭源模型数据库

## 📝 文档索引

### API文档
- `docs/api/` - API配置和使用文档

### 使用指南
- `docs/guides/` - 各种功能使用指南

### 架构文档
- `docs/architecture/` - 系统架构说明

### 维护文档
- `docs/maintenance/` - 维护和调试指南

## 🚀 快速开始

1. 运行系统测试：
   ```bash
   ./run_systematic_test_final.sh
   ```

2. 查看测试进度：
   ```bash
   python view_test_progress.py
   ```

3. 运行维护系统：
   ```bash
   python auto_failure_maintenance_system.py status
   ```

## 📊 整理统计

- **根目录保留文档**: 4个 (CLAUDE.md, README.md, QUICK_REFERENCE.md, PROJECT_STRUCTURE.md)
- **文档总数**: 65个MD文件，已分类整理到docs/子目录
- **日志清理**: 从1669个减少到621个（删除3天前的日志）
- **Python脚本**: 77个核心脚本保留在主目录
- **测试脚本**: 52个测试脚本整理到scripts/test/

更新时间：2025-08-15 16:18:00
