# 存储格式使用指南

## 🎯 快速开始

### 1. 选择存储格式

运行测试时，系统会首先询问您选择哪种存储格式：

```bash
./run_systematic_test_final.sh
```

您会看到：
```
========================================
选择数据存储格式
========================================
请选择数据存储格式：

  1) 📄 JSON格式 (传统方式，兼容性好)
  2) 🚀 Parquet格式 (推荐：高性能，防数据丢失)

Parquet优势：
  • 增量写入，永不覆盖
  • 中断安全，数据不丢失
  • 并发写入不冲突
  • 查询速度快100倍
  • 文件大小减少80%

请选择 [1-2] (默认1):
```

### 2. 或通过环境变量设置

```bash
# 使用Parquet格式（推荐）
export STORAGE_FORMAT=parquet
./run_systematic_test_final.sh

# 使用JSON格式（传统）
export STORAGE_FORMAT=json
./run_systematic_test_final.sh

# 临时指定
STORAGE_FORMAT=parquet ./run_systematic_test_final.sh
```

## 📊 格式对比

| 特性 | JSON | Parquet |
|------|------|---------|
| **并发安全** | ❌ 会覆盖 | ✅ 增量写入 |
| **中断恢复** | ❌ 数据丢失 | ✅ 自动恢复 |
| **文件大小** | 大 | 小80% |
| **查询速度** | 慢 | 快100倍 |
| **兼容性** | ✅ 所有版本 | 需要pandas |
| **推荐场景** | 单进程测试 | 并发测试 |

## 🔄 数据迁移

### 从JSON迁移到Parquet

```bash
# 自动迁移所有历史数据
python migrate_to_parquet.py

# 或指定特定文件
python migrate_to_parquet.py pilot_bench_cumulative_results/master_database.json
```

### 从Parquet导出为JSON

```python
from parquet_data_manager import ParquetDataManager
manager = ParquetDataManager()
manager.export_to_json(Path("export.json"))
```

## 🛠️ 技术细节

### Parquet存储结构

```
pilot_bench_parquet_data/
├── test_results.parquet       # 主数据文件
├── model_stats.parquet        # 模型统计
└── incremental/               # 增量数据目录
    ├── increment_12345_*.parquet  # 进程12345的增量数据
    ├── increment_12346_*.parquet  # 进程12346的增量数据
    └── transaction_*.tmp          # 未完成的事务
```

### 工作原理

1. **增量写入**：每个进程写入独立的增量文件
2. **定期合并**：系统自动将增量数据合并到主文件
3. **事务恢复**：中断的写入保存在transaction文件中，下次启动时恢复

### JSON存储结构

```
pilot_bench_cumulative_results/
└── master_database.json       # 单一JSON文件（所有数据）
```

## ⚠️ 重要提示

### 并发测试场景

如果您运行多个并发测试进程，**强烈建议使用Parquet格式**：

```bash
# 设置为Parquet
export STORAGE_FORMAT=parquet

# 运行多个并发测试（安全）
./run_systematic_test_final.sh &
./run_systematic_test_final.sh &
./run_systematic_test_final.sh &
```

使用JSON格式时，多个进程会相互覆盖数据！

### 安装依赖

Parquet格式需要额外依赖：

```bash
pip install pandas pyarrow
```

## 🔍 监控和维护

### 查看Parquet数据统计

```python
from parquet_data_manager import ParquetDataManager
manager = ParquetDataManager()

# 查询数据
df = manager.query_model_stats()
print(f"总记录数: {len(df)}")
print(f"模型分布:\n{df['model'].value_counts()}")

# 计算统计
stats = manager.compute_statistics(df)
print(f"总成功率: {stats['success_rate']:.2%}")
```

### 合并增量数据

```python
# 手动触发合并（通常自动执行）
manager.consolidate_incremental_data()
```

### 恢复中断的事务

```python
from parquet_data_manager import SafeWriteManager
safe_manager = SafeWriteManager(manager)
recovered = safe_manager.recover_transactions()
print(f"恢复了{recovered}条记录")
```

## 📝 代码集成

### 在Python脚本中使用

```python
import os

# 设置存储格式
os.environ['STORAGE_FORMAT'] = 'parquet'  # 或 'json'

# 导入统一接口（自动选择正确的后端）
from storage_backend_manager import (
    add_test_result,
    check_progress,
    finalize
)

# 使用方法完全相同
add_test_result(
    model="gpt-4o-mini",
    task_type="simple_task",
    prompt_type="baseline",
    success=True,
    execution_time=2.5
)

# 检查进度
progress = check_progress("gpt-4o-mini", target_count=100)
print(f"完成率: {progress['completion_rate']:.1f}%")

# 同步数据
finalize()
```

### 在Shell脚本中使用

```bash
#!/bin/bash

# 设置存储格式
export STORAGE_FORMAT=parquet

# 运行Python脚本（会自动使用Parquet）
python batch_test_runner.py --model gpt-4o-mini

# 或直接在命令中指定
STORAGE_FORMAT=json python smart_batch_runner.py --model qwen2.5-72b
```

## 🚀 最佳实践

1. **生产环境**：使用Parquet
2. **开发测试**：JSON便于调试
3. **数据分析**：Parquet性能更好
4. **长期存储**：Parquet压缩率高

## 📞 故障排除

### 问题：Parquet依赖未安装
```bash
pip install pandas pyarrow
```

### 问题：数据迁移失败
```bash
# 检查权限
ls -la pilot_bench_cumulative_results/
ls -la pilot_bench_parquet_data/

# 手动创建目录
mkdir -p pilot_bench_parquet_data/incremental
```

### 问题：并发写入冲突（JSON）
立即切换到Parquet：
```bash
export STORAGE_FORMAT=parquet
```

---

**版本**: 1.0.0  
**更新时间**: 2025-08-16  
**作者**: Claude Assistant