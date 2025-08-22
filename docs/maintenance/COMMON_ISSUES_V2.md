# 常见问题解决方案 V2.0

> 最后更新: 2025-08-17  
> 版本: 2.0  
> 状态: 🟢 Active

## 📋 快速导航

### 按错误类型
- [🔴 启动错误](#启动错误)
- [🟡 运行时错误](#运行时错误)  
- [🔵 API错误](#api错误)
- [🟢 数据错误](#数据错误)
- [⚫ 系统错误](#系统错误)

### 按紧急程度
- [🚨 紧急](#紧急问题)
- [⚠️ 重要](#重要问题)
- [ℹ️ 一般](#一般问题)

---

## 🚨 紧急问题

### 1. 数据完全丢失
**症状**: master_database.json被清空或损坏
```
JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

**解决方案**:
```bash
# 1. 检查备份
ls -la pilot_bench_cumulative_results/*.backup

# 2. 从最近的备份恢复
cp pilot_bench_cumulative_results/master_database.backup master_database.json

# 3. 如果有Parquet数据，从Parquet恢复
python -c "
from parquet_data_manager import ParquetDataManager
manager = ParquetDataManager()
manager.export_to_json(output_path='pilot_bench_cumulative_results/master_database.json')
"

# 4. 从增量文件重建（最后手段）
python recover_from_incremental.py
```

### 2. 所有API调用失败
**症状**: 所有模型都返回超时或连接错误

**诊断**:
```python
# 测试API连接
python test_deepseek_api.py

# 检查网络
ping api.openai.com
curl -I https://api.openai.com
```

**解决方案**:
```python
# 1. 检查API密钥
import os
print("API Keys configured:", [k for k in os.environ if 'API' in k])

# 2. 切换到备用端点
export IDEALAB_API_BASE=https://backup.endpoint.com/v1

# 3. 降低并发
export MAX_WORKERS=1
export QPS_LIMIT=1

# 4. 增加超时
# 在代码中修改timeout参数
timeout=120  # 增加到120秒
```

---

## ⚠️ 重要问题

### 3. Bash脚本语法错误
**症状**: macOS上运行时报错
```bash
${STORAGE_FORMAT^^}: bad substitution
```

**原因**: macOS的bash版本(3.2)不支持`^^`语法

**解决方案**:
```bash
# ❌ 错误（bash 4.0+）
UPPER=${VAR^^}

# ✅ 正确（兼容所有版本）
UPPER=$(echo "$VAR" | tr '[:lower:]' '[:upper:]')

# 或者升级bash
brew install bash
echo "/usr/local/bin/bash" | sudo tee -a /etc/shells
chsh -s /usr/local/bin/bash
```

### 4. Parquet文件未生成
**症状**: 启用Parquet模式但看不到.parquet文件

**诊断**:
```bash
# 检查环境变量
echo $STORAGE_FORMAT

# 检查增量目录
ls -la pilot_bench_parquet_data/incremental/

# 查看Python中的设置
python -c "import os; print('STORAGE_FORMAT:', os.environ.get('STORAGE_FORMAT', 'not set'))"
```

**解决方案**:
```bash
# 1. 正确设置环境变量
export STORAGE_FORMAT=parquet

# 2. 合并增量文件
python -c "
from parquet_data_manager import ParquetDataManager
m = ParquetDataManager()
m.consolidate_incremental_data()
"

# 3. 验证文件
ls -la pilot_bench_parquet_data/*.parquet
```

### 5. 并发写入冲突
**症状**: 多进程测试时数据不一致或丢失

**JSON模式的问题**:
```python
# ❌ 多进程同时写入JSON会冲突
with open('database.json', 'w') as f:
    json.dump(data, f)  # 可能被其他进程覆盖
```

**解决方案 - 使用Parquet**:
```bash
# 切换到Parquet模式（自动处理并发）
export STORAGE_FORMAT=parquet
```

**解决方案 - JSON加锁**:
```python
import fcntl
import json

def safe_json_update(filepath, update_func):
    with open(filepath, 'r+') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            data = json.load(f)
            update_func(data)
            f.seek(0)
            json.dump(data, f, indent=2)
            f.truncate()
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

---

## 🔵 API错误

### 6. Model not configured错误
**症状**: 
```
ValueError: Model DeepSeek-V3-0324 is not configured for user_azure
```

**原因**: 模型配置缺失或不正确

**解决方案**:
```json
// 在config/config.json的model_configs部分添加
"DeepSeek-V3-0324": {
    "provider": "user_azure",
    "azure_endpoint": "https://your-endpoint.services.ai.azure.com",
    "api_version": "2024-02-15-preview",
    "deployment_name": "DeepSeek-V3-0324",
    "max_tokens": 4096,
    "temperature": 0.1
}
```

### 7. Rate limit错误
**症状**: 
```
openai.RateLimitError: Rate limit exceeded
```

**解决方案**:
```python
# 1. 降低QPS
export QPS_LIMIT=5  # 降到5 QPS

# 2. 使用多个API密钥轮询
# 在config.json中配置多个key

# 3. 添加重试逻辑
from tenacity import retry, wait_exponential, stop_after_attempt

@retry(
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(5)
)
def call_api():
    # API调用
    pass

# 4. 使用不同的prompt_type分散负载
# baseline, cot, optimal使用不同的API key
```

### 8. 超时错误
**症状**:
```
TimeoutError: Request timed out after 30 seconds
```

**解决方案**:
```python
# 1. 增加超时时间
response = client.chat.completions.create(
    model=model,
    messages=messages,
    timeout=120  # 增加到120秒
)

# 2. 减小批量大小
--num-instances 5  # 减少并发请求

# 3. 使用流式响应
stream=True  # 启用流式响应避免超时
```

---

## 🟢 数据错误

### 9. 数据不一致
**症状**: 统计数字不匹配，总数不对

**诊断脚本**:
```python
def diagnose_data_consistency():
    import json
    
    with open('pilot_bench_cumulative_results/master_database.json') as f:
        data = json.load(f)
    
    # 计算实际总数
    actual_total = 0
    for model_data in data['models'].values():
        actual_total += model_data.get('total_tests', 0)
    
    # 比较汇总
    summary_total = data['summary'].get('total_tests', 0)
    
    print(f"实际总数: {actual_total}")
    print(f"汇总总数: {summary_total}")
    
    if actual_total != summary_total:
        print("❌ 数据不一致！")
        # 修复
        data['summary']['total_tests'] = actual_total
        with open('master_database.json', 'w') as f:
            json.dump(data, f, indent=2)
        print("✅ 已修复")

diagnose_data_consistency()
```

### 10. 重复数据
**症状**: 同一测试被记录多次

**检测**:
```python
import pandas as pd

# Parquet模式
df = pd.read_parquet('pilot_bench_parquet_data/test_results.parquet')
duplicates = df[df.duplicated(subset=['test_id'])]
print(f"发现 {len(duplicates)} 条重复记录")

# 去重
df_clean = df.drop_duplicates(subset=['test_id'], keep='last')
df_clean.to_parquet('test_results_clean.parquet')
```

---

## ⚫ 系统错误

### 11. 内存不足
**症状**: 
```
MemoryError: Unable to allocate array
```

**解决方案**:
```python
# 1. 分批处理
def process_in_batches(data, batch_size=1000):
    for i in range(0, len(data), batch_size):
        batch = data[i:i+batch_size]
        process_batch(batch)
        
        # 强制垃圾回收
        import gc
        gc.collect()

# 2. 使用生成器
def read_large_file(filepath):
    with open(filepath) as f:
        for line in f:
            yield json.loads(line)

# 3. 限制并发
MAX_WORKERS=5  # 减少并发数
```

### 12. 磁盘空间不足
**症状**: 
```
OSError: [Errno 28] No space left on device
```

**诊断**:
```bash
# 检查磁盘使用
df -h

# 查找大文件
du -sh * | sort -h | tail -20

# 清理日志
find logs/ -name "*.log" -mtime +7 -delete

# 清理旧的增量文件
find pilot_bench_parquet_data/incremental/ -name "*.parquet" -mtime +3 -delete
```

---

## ℹ️ 一般问题

### 13. 进度显示不准确
**症状**: 进度条卡住或显示错误

**解决方案**:
```python
# 使用tqdm的动态更新
from tqdm import tqdm

pbar = tqdm(total=total_tasks, dynamic_ncols=True)
pbar.set_description(f"处理中")
pbar.update(1)
pbar.refresh()  # 强制刷新显示
```

### 14. 日志文件过大
**症状**: logs/目录占用大量空间

**解决方案**:
```bash
# 1. 压缩旧日志
gzip logs/*.log

# 2. 设置日志轮转
# 在代码中使用RotatingFileHandler
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    'app.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)

# 3. 清理脚本
#!/bin/bash
find logs/ -name "*.log" -mtime +7 -exec gzip {} \;
find logs/ -name "*.gz" -mtime +30 -delete
```

### 15. 测试结果不可重现
**症状**: 相同配置的测试结果差异很大

**解决方案**:
```python
# 1. 设置随机种子
import random
import numpy as np

random.seed(42)
np.random.seed(42)

# 2. 固定模型参数
temperature=0.0  # 使用0温度确保确定性

# 3. 记录完整配置
test_config = {
    'model': model_name,
    'seed': 42,
    'temperature': 0.0,
    'timestamp': datetime.now().isoformat(),
    'environment': dict(os.environ)
}
```

---

## 🛠️ 快速修复工具箱

### 一键诊断脚本
```bash
#!/bin/bash
# diagnose.sh - 系统诊断脚本

echo "=== 系统诊断 ==="

# 检查环境变量
echo "环境变量:"
echo "  STORAGE_FORMAT: $STORAGE_FORMAT"
echo "  MAX_WORKERS: $MAX_WORKERS"

# 检查文件
echo "数据文件:"
ls -lh pilot_bench_cumulative_results/*.json 2>/dev/null || echo "  ❌ JSON文件不存在"
ls -lh pilot_bench_parquet_data/*.parquet 2>/dev/null || echo "  ❌ Parquet文件不存在"

# 检查进程
echo "运行中的进程:"
ps aux | grep python | grep -E "(batch|test)" || echo "  没有测试进程"

# 检查磁盘空间
echo "磁盘空间:"
df -h . | tail -1

# 检查最近错误
echo "最近的错误:"
grep ERROR logs/*.log 2>/dev/null | tail -5 || echo "  没有错误日志"
```

### 数据修复工具
```python
#!/usr/bin/env python3
# repair_data.py - 数据修复工具

def repair_json_database():
    """修复JSON数据库"""
    import json
    from pathlib import Path
    
    db_path = Path("pilot_bench_cumulative_results/master_database.json")
    
    try:
        with open(db_path) as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print("❌ JSON文件损坏，尝试从备份恢复...")
        # 查找最近的备份
        backups = sorted(Path(".").glob("*.backup"))
        if backups:
            import shutil
            shutil.copy(backups[-1], db_path)
            print(f"✅ 从 {backups[-1]} 恢复")
        else:
            print("❌ 没有可用备份")
            return False
    
    # 修复数据一致性
    # ... 修复逻辑 ...
    
    return True

if __name__ == "__main__":
    repair_json_database()
```

---

## 📚 相关文档

- [DEBUG_KNOWLEDGE_BASE_V2.md](./DEBUG_KNOWLEDGE_BASE_V2.md) - 详细调试指南
- [PARQUET_GUIDE.md](../guides/PARQUET_GUIDE.md) - Parquet使用指南
- [API_TROUBLESHOOTING.md](../api/API_TROUBLESHOOTING.md) - API问题详解

---

**文档版本**: 2.0  
**创建时间**: 2025-08-17  
**维护者**: System Administrator  
**状态**: 🟢 Active | ✅ 已更新