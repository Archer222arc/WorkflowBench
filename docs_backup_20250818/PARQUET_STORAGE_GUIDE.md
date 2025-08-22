# Parquet存储系统使用指南

## 📁 存储结构

Parquet存储系统采用**增量写入 + 定期合并**的策略：

```
pilot_bench_parquet_data/
├── test_results.parquet         # 主数据文件（合并后的完整数据）
├── test_results.parquet.backup  # 主文件备份
├── model_stats.parquet          # 模型统计数据
├── metadata.json                # 元数据
└── incremental/                 # 增量数据目录
    ├── increment_12345_20250816_203211.parquet  # 进程1的增量文件
    ├── increment_67890_20250816_203541.parquet  # 进程2的增量文件
    └── ...                      # 每个进程独立写入
```

## 🔄 数据流程

### 1. 写入流程（实时）
- 每个测试进程写入自己的增量文件：`increment_{进程ID}_{时间戳}.parquet`
- 避免并发写入冲突
- 数据立即持久化

### 2. 合并流程（定期）
- 增量文件会定期合并到主文件 `test_results.parquet`
- 合并时会去重（基于test_id）
- 合并后清理增量文件

## 📊 数据访问方式

### 方式1：手动合并（推荐）
```bash
# 运行合并脚本
python consolidate_parquet.py

# 输出示例：
# ✅ 合并完成！
#    最终记录数: 4998
#    最新记录时间: 2025-08-16T20:38:56
```

### 方式2：查询时自动合并
```python
from parquet_cumulative_manager import ParquetCumulativeManager

manager = ParquetCumulativeManager()
# query_model_stats会自动调用consolidate_incremental_data()
stats = manager.query_model_stats(model_name="gpt-4o-mini")
```

### 方式3：程序结束时合并
```python
# 在测试完成后调用
manager.finalize()  # 会触发consolidate_incremental_data()
```

## 🚀 使用场景

### 运行测试
```bash
# 1. 设置Parquet格式
./run_systematic_test_final.sh
# 选择 2 (Parquet格式)

# 2. 测试运行时，数据写入增量文件
# pilot_bench_parquet_data/incremental/increment_*.parquet

# 3. 定期合并到主文件
python consolidate_parquet.py
```

### 查询数据
```python
import pandas as pd

# 直接读取主文件（注意：可能不包含最新的增量数据）
df = pd.read_parquet("pilot_bench_parquet_data/test_results.parquet")
print(f"总记录数: {len(df)}")

# 或使用manager（会自动合并增量数据）
from parquet_cumulative_manager import ParquetCumulativeManager
manager = ParquetCumulativeManager()
stats = manager.get_model_statistics()
```

## ⚠️ 注意事项

1. **增量文件不会自动合并**
   - 需要手动运行 `consolidate_parquet.py`
   - 或在查询时自动触发合并

2. **主文件可能不是最新的**
   - 查看 `incremental/` 目录是否有未合并的文件
   - 运行合并脚本以获取完整数据

3. **备份策略**
   - 合并时会自动创建 `.backup` 文件
   - 保留上一次的主文件版本

## 📈 优势

- ✅ **高并发写入**：每个进程独立写入，无锁竞争
- ✅ **数据安全**：增量写入，不会丢失数据
- ✅ **查询效率**：列式存储，压缩率高
- ✅ **灵活合并**：可选择合适时机合并数据

## 🛠️ 维护建议

1. **定期合并**：建议每天或每周运行一次合并脚本
2. **监控增量文件**：如果增量文件过多（>100个），应及时合并
3. **备份管理**：定期清理旧的备份文件

## 📝 与JSON格式对比

| 特性 | Parquet | JSON |
|-----|---------|------|
| 文件大小 | 小（压缩） | 大 |
| 查询速度 | 快 | 慢 |
| 并发写入 | 优秀（增量） | 差（锁竞争） |
| 人类可读 | 否 | 是 |
| 适用场景 | 大规模测试 | 小规模调试 |

---

**最后更新**: 2025-08-16
**版本**: 1.0