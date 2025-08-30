# 📦 统一存储系统使用指南

## 🎯 概述

WorkflowBench 支持多种存储模式，满足不同场景需求：
- **性能优先**：Parquet格式
- **兼容性优先**：JSON格式  
- **并发优先**：ResultCollector模式
- **智能自适应**：SmartCollector模式
- **可靠性优先**：混合模式

## 📊 存储模式对比

| 模式 | 适用场景 | 优点 | 缺点 | 性能 |
|------|---------|------|------|------|
| **JSON直写** | 小规模测试 | 简单可靠、易读 | 并发写入冲突 | ⭐⭐ |
| **Parquet直写** | 大规模测试 | 高性能、压缩好 | 需要依赖库 | ⭐⭐⭐⭐ |
| **ResultCollector** | 高并发测试 | 无写入冲突 | 需要后台合并 | ⭐⭐⭐ |
| **SmartCollector** | 自适应场景 | 智能优化 | 复杂度高 | ⭐⭐⭐⭐ |
| **混合模式** | 关键任务 | 双重保障 | 资源占用多 | ⭐⭐⭐ |

## 🚀 快速使用

### 模式1: JSON直写（默认）
```bash
# 不需要设置，这是默认模式
./run_systematic_test_final.sh

# 或显式设置
export STORAGE_MODE=json_direct
./run_systematic_test_final.sh
```

### 模式2: Parquet直写
```bash
export STORAGE_MODE=parquet_direct
# 或使用旧的环境变量
export STORAGE_FORMAT=parquet
./run_systematic_test_final.sh
```

### 模式3: ResultCollector（解决并发冲突）
```bash
export STORAGE_MODE=result_collector
# 或使用旧的环境变量
export USE_RESULT_COLLECTOR=true
./run_systematic_test_final.sh
```

### 模式4: SmartCollector（智能自适应）
```bash
export STORAGE_MODE=smart_collector
# 设置规模
export COLLECTOR_SCALE=large  # small/medium/large
./run_systematic_test_final.sh
```

### 模式5: 混合模式（最可靠）
```bash
export STORAGE_MODE=hybrid
export STORAGE_FORMAT=json        # 主存储格式
export ENABLE_COLLECTOR=true      # 启用备份收集器
./run_systematic_test_final.sh
```

## ⚙️ 高级配置

### 通用配置选项
```bash
# 批量大小（影响内存使用）
export STORAGE_BATCH_SIZE=100

# 刷新间隔（秒）
export STORAGE_FLUSH_INTERVAL=60

# 临时文件目录
export STORAGE_TEMP_DIR=temp_results

# 启用压缩（Parquet模式）
export STORAGE_COMPRESSION=true

# 启用备份
export STORAGE_BACKUP=true

# 合并间隔（ResultCollector模式）
export MERGE_INTERVAL=10
```

### SmartCollector配置
```bash
# 规模预设
export COLLECTOR_SCALE=small   # 10个结果/30秒触发
export COLLECTOR_SCALE=medium  # 100个结果/60秒触发（默认）
export COLLECTOR_SCALE=large   # 1000个结果/300秒触发

# 自定义阈值
export MAX_MEMORY_RESULTS=500
export MAX_TIME_SECONDS=120
```

## 📝 存储模式详细说明

### 1. JSON直写模式
- **文件位置**: `pilot_bench_cumulative_results/master_database.json`
- **特点**: 
  - 实时写入，立即可见
  - 人类可读，易于调试
  - 支持文件锁防止损坏
- **适用**: 单进程或低并发场景

### 2. Parquet直写模式
- **文件位置**: `pilot_bench_cumulative_results/master_database.parquet`
- **特点**:
  - 列式存储，查询快
  - 自动压缩，节省空间
  - 支持并发读取
- **适用**: 大数据量分析场景

### 3. ResultCollector模式
- **临时文件**: `temp_results/*.json`
- **最终文件**: `pilot_bench_cumulative_results/master_database.json`
- **工作流程**:
  1. 各进程写入独立临时文件
  2. 后台ResultMerger定期合并
  3. 合并后删除临时文件
- **适用**: 高并发测试场景

### 4. SmartCollector模式
- **智能策略**:
  - 内存缓存优先
  - 达到阈值自动写盘
  - 进程结束强制刷新
- **自适应触发**:
  - 结果数量触发
  - 时间间隔触发
  - 内存压力触发
- **适用**: 不确定规模的测试

### 5. 混合模式
- **双重保障**:
  - 主存储：JSON或Parquet
  - 备份存储：ResultCollector
- **优势**:
  - 防止数据丢失
  - 支持故障恢复
- **适用**: 关键任务测试

## 🔍 故障排查

### 问题1: 并发写入冲突
**症状**: 数据被覆盖，只剩最后一个模型
**解决**: 使用ResultCollector模式
```bash
export STORAGE_MODE=result_collector
```

### 问题2: 内存占用过高
**症状**: 进程占用大量内存
**解决**: 减小批量大小
```bash
export STORAGE_BATCH_SIZE=10
export STORAGE_FLUSH_INTERVAL=30
```

### 问题3: 临时文件堆积
**症状**: temp_results/目录文件过多
**解决**: 检查ResultMerger是否运行
```bash
# 手动触发合并
python3 -c "from result_merger import force_merge; force_merge()"
```

### 问题4: Parquet写入失败
**症状**: "No module named 'pyarrow'"
**解决**: 安装依赖或切换到JSON
```bash
pip install pyarrow pandas
# 或
export STORAGE_MODE=json_direct
```

## 📊 性能基准

| 场景 | 推荐模式 | 配置建议 |
|------|---------|----------|
| 快速原型测试 | JSON直写 | 默认配置 |
| 生产环境测试 | Parquet直写 | `BATCH_SIZE=1000` |
| 并行100+进程 | ResultCollector | `MERGE_INTERVAL=5` |
| 长时间运行 | SmartCollector | `SCALE=large` |
| 关键数据收集 | 混合模式 | 启用所有备份 |

## 🛠️ 开发者指南

### 添加新的存储后端
```python
from unified_storage_system import BaseStorage

class CustomStorage(BaseStorage):
    def write_result(self, record) -> bool:
        # 实现写入逻辑
        pass
    
    def write_batch(self, records) -> int:
        # 实现批量写入
        pass
```

### 在代码中使用
```python
from unified_storage_system import UnifiedStorageSystem

# 创建存储
storage = UnifiedStorageSystem.create()

# 写入数据
storage.write_result(test_record)

# 批量写入
storage.write_batch(records)

# 关闭
storage.close()
```

## 📈 最佳实践

1. **开发阶段**: 使用JSON直写，便于调试
2. **测试阶段**: 使用ResultCollector，避免冲突
3. **生产阶段**: 使用Parquet，提高性能
4. **不确定时**: 使用SmartCollector，自动优化
5. **关键任务**: 使用混合模式，双重保障

---

更新时间: 2025-08-26
版本: 1.0.0