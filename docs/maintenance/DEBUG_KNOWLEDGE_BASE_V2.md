# 调试知识库 V2.0 (Debug Knowledge Base)

> 最后更新: 2025-08-17  
> 版本: 2.0  
> 状态: 🟢 Active

## 📋 目录
1. [Parquet模式调试](#parquet模式调试)
2. [常见错误模式](#常见错误模式)
3. [API连接问题](#api连接问题)
4. [数据一致性检查](#数据一致性检查)
5. [性能调试](#性能调试)
6. [紧急修复流程](#紧急修复流程)

---

## 🆕 Parquet模式调试

### 问题1: Parquet文件未生成
**症状**: 启用Parquet模式但只看到JSON更新
```bash
# 诊断命令
ls -la pilot_bench_parquet_data/incremental/
```

**原因**: 
- 数据写入增量目录，而非主文件
- 环境变量未设置

**解决方案**:
```bash
# 1. 设置环境变量
export STORAGE_FORMAT=parquet

# 2. 检查增量文件
ls -la pilot_bench_parquet_data/incremental/*.parquet

# 3. 合并增量数据
python -c "from parquet_data_manager import ParquetDataManager; m=ParquetDataManager(); m.consolidate_incremental_data()"
```

### 问题2: 双重存储（JSON和Parquet同时更新）
**症状**: master_database.json仍在更新
```python
# 检查存储模式
import os
print(f"STORAGE_FORMAT: {os.environ.get('STORAGE_FORMAT', 'json')}")
```

**解决方案**:
```python
# 确保只使用一种存储
if os.environ.get('STORAGE_FORMAT') == 'parquet':
    from parquet_cumulative_manager import ParquetCumulativeManager as Manager
else:
    from cumulative_test_manager import CumulativeTestManager as Manager
```

---

## 🔴 常见错误模式

### 1. 5.3测试数据污染问题 [NEW]

**症状**: 运行5.3缺陷工作流测试后，数据库出现不相关的记录：
- 简化的"flawed"（应该是具体类型如"flawed_sequence_disorder"）  
- 不相关的"baseline"、"optimal"记录
- task_type为"unknown"的记录

**根本原因**: smart_batch_runner.py中有多处将prompt_type简化：
```python
# 错误代码（出现在两处）
prompt_type="flawed" if is_flawed else prompt_type
```

**解决方案**:
1. 修复所有简化点（第220行和第655行）：
```python
# 正确代码
prompt_type=prompt_type  # 保持原始值
```

2. 清理污染数据：
```python
# 清理Parquet
df = pd.read_parquet('pilot_bench_parquet_data/test_results.parquet')
bad_mask = (
    (df['model'] == 'DeepSeek-V3-0324') & 
    (df['prompt_type'] == 'flawed')  # 简化的flawed
)
df_clean = df[~bad_mask]
df_clean.to_parquet('pilot_bench_parquet_data/test_results.parquet')
```

3. 验证修复：
```bash
python smart_batch_runner.py --model gpt-4o-mini \
  --prompt-types flawed_sequence_disorder \
  --difficulty easy --task-types simple_task --num-instances 1
```

**相关文档**: [FIX-20250817-003](./debug_logs/2025-08-17_flawed_prompt_fix.md)

### 2. AttributeError系列

#### ExecutionState缺少属性
```python
# ❌ 错误
state.format_error_count  # AttributeError

# ✅ 修复
count = getattr(state, 'format_error_count', 0)

# ✅ 防御性编程
if hasattr(state, 'format_error_count'):
    count = state.format_error_count
else:
    count = 0
```

#### TestRecord字段缺失
```python
# ❌ 错误
record.execution_status  # AttributeError

# ✅ 修复：初始化时设置所有字段
def create_test_record(**kwargs):
    record = TestRecord()
    # 设置所有必需字段
    record.execution_status = kwargs.get('execution_status', 'unknown')
    record.format_error_count = kwargs.get('format_error_count', 0)
    record.execution_time = kwargs.get('execution_time', 0.0)
    return record
```

### 2. KeyError系列

#### 字典键不存在
```python
# ❌ 错误
value = data['missing_key']  # KeyError

# ✅ 修复1：使用get()
value = data.get('missing_key', default_value)

# ✅ 修复2：检查键存在
if 'missing_key' in data:
    value = data['missing_key']
else:
    value = default_value

# ✅ 修复3：使用try-except
try:
    value = data['missing_key']
except KeyError:
    value = default_value
```

### 3. ImportError系列

#### Parquet依赖缺失
```python
# ❌ 错误
import pyarrow  # ImportError: No module named 'pyarrow'

# ✅ 修复：条件导入
try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    PARQUET_AVAILABLE = True
except ImportError:
    PARQUET_AVAILABLE = False
    print("Warning: Parquet support not available. Install: pip install pyarrow")
```

### 4. 并发写入冲突

#### JSON文件并发写入
```python
# ❌ 错误：多进程同时写入
with open('data.json', 'w') as f:
    json.dump(data, f)

# ✅ 修复：使用文件锁
import fcntl

def safe_json_write(filepath, data):
    with open(filepath, 'r+') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            json.dump(data, f)
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

# ✅ 更好的方案：使用Parquet增量写入
# 每个进程写入独立的增量文件
```

---

## 🌐 API连接问题

### Azure OpenAI超时
**症状**: 
```
openai._base_client - INFO - Retrying request to /chat/completions
Batch execution timeout, cancelling remaining tasks
```

**诊断**:
```python
# 测试连接
python test_deepseek_api.py

# 检查配置
cat config/config.json | grep -A5 "DeepSeek"
```

**解决方案**:
```python
# 1. 增加超时时间
response = client.chat.completions.create(
    model=model,
    messages=messages,
    timeout=60  # 增加到60秒
)

# 2. 添加重试机制
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def call_api(client, model, messages):
    return client.chat.completions.create(
        model=model,
        messages=messages,
        timeout=30
    )
```

### 模型配置错误
**症状**: "Model XXX is not configured for user_azure"

**诊断**:
```bash
# 检查模型配置
python -c "
import json
with open('config/config.json') as f:
    config = json.load(f)
    print('Configured models:', list(config.get('model_configs', {}).keys())[:5])
"
```

**解决方案**:
1. 添加到config.json的model_configs部分
2. 确保provider字段正确设置
3. 检查API密钥是否配置

---

## 📊 数据一致性检查

### JSON数据验证
```python
# 验证master_database.json
def validate_json_database():
    import json
    from pathlib import Path
    
    db_path = Path("pilot_bench_cumulative_results/master_database.json")
    
    with open(db_path) as f:
        data = json.load(f)
    
    # 检查必需字段
    assert 'version' in data
    assert 'models' in data
    assert 'summary' in data
    
    # 验证数据一致性
    total_tests = 0
    for model_data in data['models'].values():
        total_tests += model_data.get('total_tests', 0)
    
    # 比较汇总
    summary_total = data['summary'].get('total_tests', 0)
    if total_tests != summary_total:
        print(f"⚠️ 数据不一致: 计算={total_tests}, 汇总={summary_total}")
    
    return data
```

### Parquet数据验证
```python
# 验证Parquet数据完整性
def validate_parquet_data():
    import pandas as pd
    from pathlib import Path
    
    parquet_file = Path("pilot_bench_parquet_data/test_results.parquet")
    
    if not parquet_file.exists():
        print("❌ Parquet文件不存在")
        return False
    
    df = pd.read_parquet(parquet_file)
    
    # 检查必需列
    required_cols = ['model', 'task_type', 'prompt_type', 'success']
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        print(f"❌ 缺少列: {missing}")
        return False
    
    # 检查数据类型
    if df['success'].dtype != bool:
        print(f"⚠️ success列类型错误: {df['success'].dtype}")
    
    # 检查空值
    nulls = df[required_cols].isnull().sum()
    if nulls.any():
        print(f"⚠️ 发现空值:\n{nulls[nulls > 0]}")
    
    print(f"✅ Parquet数据验证通过: {len(df)} 条记录")
    return True
```

---

## ⚡ 性能调试

### 内存泄漏检测
```python
import tracemalloc
import gc

# 开始跟踪
tracemalloc.start()

# ... 运行测试 ...

# 获取内存快照
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')

# 显示前10个内存消耗
for stat in top_stats[:10]:
    print(stat)

# 强制垃圾回收
gc.collect()
```

### 并发性能分析
```python
import time
import concurrent.futures

def profile_concurrent_execution(func, tasks, max_workers):
    start = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(func, task) for task in tasks]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    elapsed = time.time() - start
    throughput = len(tasks) / elapsed
    
    print(f"处理 {len(tasks)} 个任务")
    print(f"耗时: {elapsed:.2f}秒")
    print(f"吞吐量: {throughput:.1f} 任务/秒")
    print(f"平均延迟: {elapsed/len(tasks)*1000:.1f}ms")
    
    return results
```

### 瓶颈定位
```bash
# 使用cProfile分析
python -m cProfile -s cumulative smart_batch_runner.py --model gpt-4o-mini ...

# 生成火焰图
py-spy record -d 30 -f flamegraph.svg -- python smart_batch_runner.py ...

# 监控资源使用
htop  # CPU和内存
iotop  # 磁盘I/O
```

---

## 🚨 紧急修复流程

### 1. 数据损坏恢复
```bash
# 步骤1: 备份当前数据
cp pilot_bench_cumulative_results/master_database.json master_database.backup.$(date +%Y%m%d_%H%M%S).json

# 步骤2: 验证备份
python -c "import json; json.load(open('master_database.backup.*.json'))"

# 步骤3: 从备份恢复
cp master_database.backup.20250817_123456.json pilot_bench_cumulative_results/master_database.json

# 步骤4: 转换到Parquet（数据安全）
python json_to_parquet_converter.py
```

### 2. API故障切换
```python
# 自动故障转移
class APIFailover:
    def __init__(self):
        self.endpoints = [
            {"name": "primary", "url": "https://primary.api.com"},
            {"name": "backup", "url": "https://backup.api.com"},
            {"name": "fallback", "url": "https://fallback.api.com"}
        ]
        self.current = 0
    
    def get_client(self):
        for _ in range(len(self.endpoints)):
            endpoint = self.endpoints[self.current]
            try:
                client = create_client(endpoint['url'])
                # 测试连接
                test_connection(client)
                return client
            except Exception as e:
                print(f"❌ {endpoint['name']} 失败: {e}")
                self.current = (self.current + 1) % len(self.endpoints)
        
        raise Exception("所有端点都失败")
```

### 3. 进程清理
```bash
# 查找卡住的进程
ps aux | grep python | grep batch_test

# 终止所有测试进程
pkill -f "batch_test"

# 清理锁文件
rm -f /tmp/*.lock

# 清理临时文件
rm -rf pilot_bench_parquet_data/incremental/temp_*
```

---

## 📈 监控和告警

### 实时监控脚本
```python
#!/usr/bin/env python3
"""实时监控测试进度"""

import time
import pandas as pd
from pathlib import Path

def monitor_progress():
    while True:
        # 检查增量文件
        incremental_dir = Path("pilot_bench_parquet_data/incremental")
        files = list(incremental_dir.glob("*.parquet"))
        
        if files:
            total_records = 0
            for f in files:
                df = pd.read_parquet(f)
                total_records += len(df)
            
            print(f"\r增量文件: {len(files)}, 记录数: {total_records}", end="")
        
        time.sleep(5)

if __name__ == "__main__":
    monitor_progress()
```

### 健康检查
```python
def health_check():
    """系统健康检查"""
    checks = {
        "JSON数据库": check_json_database(),
        "Parquet数据": check_parquet_data(),
        "API连接": check_api_connection(),
        "磁盘空间": check_disk_space(),
        "内存使用": check_memory_usage()
    }
    
    for name, status in checks.items():
        emoji = "✅" if status else "❌"
        print(f"{emoji} {name}: {'正常' if status else '异常'}")
    
    return all(checks.values())
```

---

## 🔧 调试工具箱

### 快速诊断命令
```bash
# 查看最新错误
tail -n 100 logs/batch_test_*.log | grep ERROR

# 统计错误类型
grep "ERROR" logs/*.log | cut -d: -f4- | sort | uniq -c | sort -rn

# 查看进程状态
ps aux | grep python | grep -E "(batch|test|runner)"

# 检查端口占用
lsof -i :8080

# 查看系统资源
df -h  # 磁盘空间
free -h  # 内存
top -b -n 1  # CPU
```

### 调试环境变量
```bash
# 启用详细日志
export DEBUG=1
export LOG_LEVEL=DEBUG

# 使用Parquet模式
export STORAGE_FORMAT=parquet

# 禁用并发（调试用）
export MAX_WORKERS=1

# 启用性能分析
export PROFILE=1
```

---

## 📚 相关文档

- [COMMON_ISSUES.md](./COMMON_ISSUES.md) - 常见问题解决方案
- [PARQUET_GUIDE.md](../guides/PARQUET_GUIDE.md) - Parquet使用指南
- [API_TROUBLESHOOTING.md](../api/API_TROUBLESHOOTING.md) - API故障排除
- [PERFORMANCE_TUNING.md](./PERFORMANCE_TUNING.md) - 性能调优指南

---

**文档版本**: 2.0  
**创建时间**: 2025-08-17  
**维护者**: System Administrator  
**状态**: 🟢 Active | ✅ 已更新