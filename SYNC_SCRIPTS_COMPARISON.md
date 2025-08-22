# 同步脚本对比分析

## 现有同步脚本列表

### 1. `json_to_parquet_converter.py`
- **创建时间**: 较早
- **主要功能**: 将master_database.json完整转换为Parquet格式
- **特点**:
  - 展平层次化的JSON数据为DataFrame格式
  - 保留所有维度信息（model, prompt_type, tool_success_rate, difficulty, task_type）
  - 包含所有统计字段（total, successful, partial, failed等）
  - 使用pyarrow库进行转换
- **数据范围**: 完整的层次化数据
- **用途**: 初始数据迁移

### 2. `migrate_json_to_parquet.py`
- **创建时间**: 中期
- **主要功能**: 正确迁移JSON汇总数据到Parquet格式
- **特点**:
  - 提取overall_stats作为汇总记录
  - 为每个层级创建汇总记录（包括overall级别）
  - 字段名使用`successful`而不是`success`
  - 包含备份功能
- **数据范围**: 汇总数据 + overall统计
- **用途**: 数据迁移和汇总

### 3. `restore_json_from_parquet.py`
- **创建时间**: 中期
- **主要功能**: 从Parquet文件恢复JSON数据库
- **特点**:
  - 反向操作：Parquet → JSON
  - 重建层次化结构
  - 使用defaultdict构建嵌套结构
  - 自动计算overall_stats
- **数据范围**: 从Parquet恢复完整JSON结构
- **用途**: 数据恢复和反向同步

### 4. `sync_json_to_parquet.py`
- **创建时间**: 最新（今天创建）
- **主要功能**: 从JSON同步数据到Parquet格式
- **特点**:
  - 提取所有task_type级别的汇总记录
  - 字段名使用`success`（正确的字段名）
  - 添加is_flawed和flaw_type字段
  - 生成JSON预览文件
  - 包含详细的统计报告
- **数据范围**: task_type级别的汇总数据
- **用途**: 日常数据同步

## 主要区别

| 脚本 | 方向 | 数据粒度 | 字段名 | 备份功能 | 统计报告 |
|-----|------|---------|--------|---------|---------|
| json_to_parquet_converter | JSON→Parquet | 完整层次 | successful | ❌ | ❌ |
| migrate_json_to_parquet | JSON→Parquet | 汇总+overall | successful | ✅ | ✅ |
| restore_json_from_parquet | Parquet→JSON | 完整恢复 | - | ✅ | ❌ |
| sync_json_to_parquet | JSON→Parquet | task级汇总 | success | ✅ | ✅ |

## 字段名问题

**重要发现**：存在字段名不一致问题
- JSON数据库实际使用: `success`
- 部分脚本错误使用: `successful`
- 正确的是: `success`

## 推荐使用

1. **日常同步**: 使用 `sync_json_to_parquet.py`（最新，字段名正确）
2. **数据恢复**: 使用 `restore_json_from_parquet.py`
3. **初始迁移**: 使用 `json_to_parquet_converter.py`（但需要修复字段名）

## 建议

1. 统一字段名为`success`（而不是`successful`）
2. 保留`sync_json_to_parquet.py`作为主要同步工具
3. 考虑归档或删除重复功能的脚本
4. 更新旧脚本中的字段名错误