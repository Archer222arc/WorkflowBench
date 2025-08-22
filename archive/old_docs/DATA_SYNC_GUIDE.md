# JSON-Parquet数据同步指南

## 概述
`sync_json_parquet.py`是一个强大的双向数据同步工具，用于管理PILOT-Bench的JSON和Parquet数据格式之间的转换和同步。

## 功能特性
- ✅ 双向数据同步（JSON ↔ Parquet）
- ✅ 自动数据备份
- ✅ 无效数据清理
- ✅ 数据验证和统计
- ✅ flawed记录类型验证

## 使用方法

### 基本命令
```bash
# 查看数据统计
python sync_json_parquet.py stats

# 清理并同步（推荐）
python sync_json_parquet.py clean --primary parquet

# 普通同步
python sync_json_parquet.py sync --primary parquet

# Parquet转JSON
python sync_json_parquet.py p2j

# JSON转Parquet
python sync_json_parquet.py j2p
```

### 参数说明
- `action`: 操作类型
  - `sync`: 双向同步
  - `clean`: 清理无效数据并同步
  - `stats`: 显示统计信息
  - `p2j`: Parquet转JSON
  - `j2p`: JSON转Parquet
- `--primary`: 主数据源（parquet或json），默认parquet
- `--no-clean`: 不清理无效数据

## 数据清理规则

### 无效flawed记录
工具会自动识别并清理以下无效记录：
- prompt_type只是"flawed"而没有具体类型的记录
- 这些通常是测试配置错误导致的

### 有效的flawed类型
5.3测试中的有效flawed类型：
1. `flawed_sequence_disorder` - 顺序错误
2. `flawed_tool_misuse` - 工具误用
3. `flawed_parameter_error` - 参数错误
4. `flawed_missing_step` - 缺少步骤
5. `flawed_redundant_operations` - 冗余操作
6. `flawed_logical_inconsistency` - 逻辑不一致
7. `flawed_semantic_drift` - 语义偏移

## 备份机制
- 每次同步操作前自动备份原文件
- 备份位置：`pilot_bench_cumulative_results/backups/`
- 备份命名：`{filename}_{timestamp}.{ext}`

## 使用示例

### 场景1：清理5.3测试产生的无效数据
```bash
# 1. 先查看当前状态
python sync_json_parquet.py stats

# 2. 清理并同步
python sync_json_parquet.py clean --primary parquet

# 3. 验证结果
python sync_json_parquet.py stats
```

### 场景2：从JSON恢复Parquet
```bash
# 如果Parquet损坏，从JSON重建
python sync_json_parquet.py j2p
```

### 场景3：导出Parquet到JSON格式
```bash
# 导出给其他工具使用
python sync_json_parquet.py p2j
```

## 注意事项
1. **备份重要数据**：虽然工具会自动备份，建议重要操作前手动备份
2. **选择正确的主数据源**：通常Parquet更新更频繁，应作为主数据源
3. **定期清理**：建议定期运行clean命令保持数据质量

## 故障排除

### 问题：同步后数据不一致
**解决**：使用`clean`命令而不是`sync`，强制清理无效数据

### 问题：备份目录过大
**解决**：定期清理旧备份文件，保留最近7天的备份即可

### 问题：无法读取Parquet文件
**解决**：确保安装了pandas和pyarrow：
```bash
pip install pandas pyarrow
```

## 相关文档
- [数据存储结构说明](../architecture/DATABASE_STRUCTURE_V3.md)
- [Parquet存储系统](../architecture/PARQUET_STORAGE.md)
- [测试数据管理](./TEST_DATA_MANAGEMENT.md)