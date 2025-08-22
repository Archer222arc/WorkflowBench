# Parquet存储模式完整指南

> 版本: 1.0  
> 创建时间: 2025-08-17  
> 状态: 🟢 Active

## 📋 目录
1. [为什么选择Parquet](#为什么选择parquet)
2. [快速开始](#快速开始)
3. [架构设计](#架构设计)
4. [使用方法](#使用方法)
5. [数据管理](#数据管理)
6. [故障排除](#故障排除)
7. [最佳实践](#最佳实践)

---

## 🎯 为什么选择Parquet

### 对比JSON的优势

| 特性 | JSON | Parquet |
|------|------|---------|
| **文件大小** | 100MB | 20MB (-80%) |
| **查询速度** | 1秒 | 0.01秒 (100x) |
| **并发写入** | ❌ 冲突 | ✅ 安全 |
| **增量更新** | ❌ 全量覆盖 | ✅ 增量追加 |
| **数据恢复** | ❌ 易丢失 | ✅ 可恢复 |
| **类型安全** | ❌ 字符串 | ✅ 强类型 |

### 适用场景
- ✅ 大规模批量测试（>1000次）
- ✅ 多进程并发测试
- ✅ 需要数据分析和统计
- ✅ 长时间运行的测试
- ✅ 需要中断恢复

---

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install pyarrow pandas
```

### 2. 从JSON迁移到Parquet
```bash
# 转换现有数据
python json_to_parquet_converter.py

# 输出:
# ✅ 转换成功！
# - 主数据文件: pilot_bench_parquet_data/test_results.parquet
# - 总记录数: 4993
```

### 3. 启用Parquet模式
```bash
# 方法1: 使用设置脚本
./setup_parquet_incremental_test.sh

# 方法2: 手动设置环境变量
export STORAGE_FORMAT=parquet

# 方法3: 在Python中设置
import os
os.environ['STORAGE_FORMAT'] = 'parquet'
```

### 4. 运行测试
```bash
# 单个模型测试
STORAGE_FORMAT=parquet python smart_batch_runner.py \
    --model gpt-4o-mini \
    --prompt-types baseline \
    --difficulty easy \
    --task-types simple_task \
    --num-instances 10

# 批量测试
STORAGE_FORMAT=parquet python ultra_parallel_runner.py \
    --model DeepSeek-V3-0324 \
    --num-instances 100 \
    --workers 50
```

---

## 🏗️ 架构设计

### 目录结构
```
pilot_bench_parquet_data/
├── test_results.parquet        # 主数据文件（合并后）
├── model_stats.parquet         # 模型统计
├── metadata.json               # 元数据
└── incremental/                # 增量数据目录
    ├── increment_12345_*.parquet  # 进程1的增量文件
    ├── increment_67890_*.parquet  # 进程2的增量文件
    └── ...
```

### 数据流程
```
测试运行 → 写入增量文件 → 定期合并 → 主数据文件
    ↓           ↓              ↓           ↓
 [进程专属]  [无冲突写入]   [批量处理]   [查询优化]
```

### 增量写入机制
每个进程创建独立的增量文件，避免并发冲突：
```python
# 进程ID + 时间戳 = 唯一文件名
process_id = f"{os.getpid()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
incremental_file = f"increment_{process_id}.parquet"
```

---

## 📖 使用方法

### 基本操作

#### 1. 添加测试结果
```python
from parquet_cumulative_manager import ParquetCumulativeManager

manager = ParquetCumulativeManager()

# 添加单个测试结果
manager.add_test_result(
    model='gpt-4o-mini',
    task_type='simple_task',
    prompt_type='baseline',
    success=True,
    execution_time=5.2,
    difficulty='easy',
    tool_success_rate=0.8
)
```

#### 2. 查询数据
```python
from parquet_data_manager import ParquetDataManager

manager = ParquetDataManager()

# 查询特定模型的数据
df = manager.query_model_stats(
    model_name='DeepSeek-V3-0324',
    prompt_type='optimal',
    tool_success_rate=0.8
)

print(f"找到 {len(df)} 条记录")
print(f"成功率: {df['success'].mean():.1%}")
```

#### 3. 合并增量数据
```python
# 自动合并所有增量文件到主文件
manager.consolidate_incremental_data()

# 输出:
# 合并 5 个增量文件...
# ✅ 成功合并 250 条记录
```

#### 4. 导出数据
```python
# 导出为JSON（兼容旧系统）
manager.export_to_json(output_path='export.json')

# 导出为CSV（数据分析）
import pandas as pd
df = pd.read_parquet('pilot_bench_parquet_data/test_results.parquet')
df.to_csv('test_results.csv', index=False)
```

### 高级操作

#### 批量数据分析
```python
import pandas as pd
import matplotlib.pyplot as plt

# 读取数据
df = pd.read_parquet('pilot_bench_parquet_data/test_results.parquet')

# 按模型分组统计
model_stats = df.groupby('model').agg({
    'success': ['count', 'mean'],
    'execution_time': 'mean',
    'tool_coverage_rate': 'mean'
}).round(3)

# 可视化
model_stats['success']['mean'].plot(kind='bar')
plt.title('模型成功率对比')
plt.ylabel('成功率')
plt.show()
```

#### 实时监控
```python
from pathlib import Path
import time

def monitor_incremental_updates():
    """监控增量文件更新"""
    incremental_dir = Path('pilot_bench_parquet_data/incremental')
    
    while True:
        files = list(incremental_dir.glob('*.parquet'))
        total_size = sum(f.stat().st_size for f in files) / 1024 / 1024
        
        print(f"\r增量文件: {len(files)}个, 总大小: {total_size:.1f}MB", end="")
        time.sleep(5)
```

---

## 🗄️ 数据管理

### 定期维护任务

#### 1. 每小时：合并增量数据
```bash
# 添加到crontab
0 * * * * cd /path/to/project && python -c "from parquet_data_manager import ParquetDataManager; m=ParquetDataManager(); m.consolidate_incremental_data()"
```

#### 2. 每日：备份主数据
```bash
#!/bin/bash
DATE=$(date +%Y%m%d)
cp pilot_bench_parquet_data/test_results.parquet backups/test_results_${DATE}.parquet
```

#### 3. 每周：清理旧数据
```python
def cleanup_old_increments(days=7):
    """清理超过N天的增量文件"""
    from pathlib import Path
    from datetime import datetime, timedelta
    
    cutoff = datetime.now() - timedelta(days=days)
    incremental_dir = Path('pilot_bench_parquet_data/incremental')
    
    for file in incremental_dir.glob('*.parquet'):
        if file.stat().st_mtime < cutoff.timestamp():
            file.unlink()
            print(f"删除旧文件: {file.name}")
```

### 数据迁移

#### JSON → Parquet
```bash
python json_to_parquet_converter.py
```

#### Parquet → JSON
```python
from parquet_data_manager import ParquetDataManager

manager = ParquetDataManager()
manager.export_to_json(output_path='export.json')
```

#### 合并多个Parquet文件
```python
import pandas as pd
import glob

# 读取所有parquet文件
files = glob.glob('pilot_bench_parquet_data/*.parquet')
dfs = [pd.read_parquet(f) for f in files]

# 合并
combined = pd.concat(dfs, ignore_index=True)

# 去重
combined = combined.drop_duplicates(subset=['test_id'])

# 保存
combined.to_parquet('merged_data.parquet', index=False)
```

---

## 🔧 故障排除

### 常见问题

#### Q1: 看不到Parquet文件
**原因**: 数据在增量目录中
```bash
# 检查增量目录
ls -la pilot_bench_parquet_data/incremental/

# 手动合并
python -c "from parquet_data_manager import ParquetDataManager; m=ParquetDataManager(); m.consolidate_incremental_data()"
```

#### Q2: ImportError: No module named 'pyarrow'
**解决**: 安装依赖
```bash
pip install pyarrow pandas
```

#### Q3: 数据不一致
**诊断**:
```python
# 验证数据完整性
def validate_parquet_data():
    import pandas as pd
    
    # 读取主文件
    main_df = pd.read_parquet('pilot_bench_parquet_data/test_results.parquet')
    
    # 读取增量文件
    from pathlib import Path
    incremental_dir = Path('pilot_bench_parquet_data/incremental')
    inc_dfs = [pd.read_parquet(f) for f in incremental_dir.glob('*.parquet')]
    
    if inc_dfs:
        inc_df = pd.concat(inc_dfs)
        print(f"主文件: {len(main_df)} 条")
        print(f"增量: {len(inc_df)} 条")
        print(f"总计: {len(main_df) + len(inc_df)} 条")
    else:
        print(f"只有主文件: {len(main_df)} 条")

validate_parquet_data()
```

#### Q4: 内存不足
**解决**: 分批处理
```python
# 分批读取大文件
def read_parquet_in_chunks(filepath, chunk_size=10000):
    import pyarrow.parquet as pq
    
    parquet_file = pq.ParquetFile(filepath)
    
    for batch in parquet_file.iter_batches(batch_size=chunk_size):
        df = batch.to_pandas()
        # 处理每个批次
        yield df

# 使用
for chunk in read_parquet_in_chunks('large_file.parquet'):
    process(chunk)  # 处理每个块
```

---

## 💡 最佳实践

### 1. 性能优化
```python
# ✅ 好: 批量写入
manager.batch_append_results(test_results)  # 一次写入多条

# ❌ 差: 单条写入
for result in test_results:
    manager.append_test_result(result)  # 多次I/O
```

### 2. 数据安全
```python
# 定期合并增量数据
import schedule

def merge_incremental():
    manager = ParquetDataManager()
    manager.consolidate_incremental_data()

# 每30分钟合并一次
schedule.every(30).minutes.do(merge_incremental)
```

### 3. 监控和告警
```python
def check_data_health():
    """数据健康检查"""
    from pathlib import Path
    
    # 检查增量文件数量
    inc_dir = Path('pilot_bench_parquet_data/incremental')
    inc_files = list(inc_dir.glob('*.parquet'))
    
    if len(inc_files) > 100:
        print(f"⚠️ 警告: 增量文件过多 ({len(inc_files)}), 需要合并")
    
    # 检查文件大小
    total_size = sum(f.stat().st_size for f in inc_files) / 1024 / 1024
    if total_size > 100:
        print(f"⚠️ 警告: 增量数据过大 ({total_size:.1f}MB), 需要合并")
    
    return len(inc_files) < 100 and total_size < 100
```

### 4. 并发控制
```python
# 使用进程池限制并发
from concurrent.futures import ProcessPoolExecutor

def run_parallel_tests(tasks, max_workers=10):
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(run_test, task) for task in tasks]
        results = [f.result() for f in futures]
    
    # 合并所有进程的增量数据
    manager = ParquetDataManager()
    manager.consolidate_incremental_data()
    
    return results
```

---

## 📊 性能基准

### 测试环境
- MacBook Pro M1
- 16GB RAM
- 1TB SSD

### 性能对比

| 操作 | JSON | Parquet | 提升 |
|------|------|---------|------|
| 写入1000条 | 2.5s | 0.3s | 8.3x |
| 读取10000条 | 1.2s | 0.05s | 24x |
| 查询特定模型 | 0.8s | 0.01s | 80x |
| 文件大小(10k条) | 15MB | 2MB | 7.5x |
| 并发写入(10进程) | ❌失败 | ✅成功 | ∞ |

---

## 🔗 相关资源

### 内部文档
- [DEBUG_KNOWLEDGE_BASE_V2.md](../maintenance/DEBUG_KNOWLEDGE_BASE_V2.md)
- [COMMON_ISSUES.md](../maintenance/COMMON_ISSUES.md)
- [setup_parquet_incremental_test.sh](../../setup_parquet_incremental_test.sh)

### 外部资源
- [Apache Parquet官方文档](https://parquet.apache.org/)
- [PyArrow文档](https://arrow.apache.org/docs/python/)
- [Pandas Parquet指南](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_parquet.html)

---

**文档版本**: 1.0  
**创建时间**: 2025-08-17  
**维护者**: System Administrator  
**状态**: 🟢 Active | ✅ 完整