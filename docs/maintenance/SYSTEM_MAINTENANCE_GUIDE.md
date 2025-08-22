# 系统维护完整指南

> 版本: 1.0  
> 创建时间: 2025-08-17  
> 状态: 🟢 Active

## 📋 目录
1. [日常维护](#日常维护)
2. [定期任务](#定期任务)
3. [性能优化](#性能优化)
4. [数据管理](#数据管理)
5. [故障恢复](#故障恢复)
6. [系统监控](#系统监控)
7. [维护脚本](#维护脚本)

---

## 📅 日常维护

### 每日检查清单
```bash
#!/bin/bash
# daily_check.sh - 每日系统检查

echo "=== 每日系统检查 $(date) ==="

# 1. 检查系统状态
echo "[1/5] 系统状态..."
ps aux | grep python | grep -c batch_test && echo "✅ 测试进程运行中" || echo "⚠️ 无测试进程"

# 2. 检查数据完整性
echo "[2/5] 数据完整性..."
python -c "
import json
try:
    with open('pilot_bench_cumulative_results/master_database.json') as f:
        data = json.load(f)
    print(f'✅ JSON数据正常: {len(data.get(\"models\", {}))} 个模型')
except:
    print('❌ JSON数据异常')
"

# 3. 检查磁盘空间
echo "[3/5] 磁盘空间..."
USAGE=$(df -h . | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $USAGE -lt 80 ]; then
    echo "✅ 磁盘使用率: ${USAGE}%"
else
    echo "⚠️ 磁盘使用率过高: ${USAGE}%"
fi

# 4. 检查日志错误
echo "[4/5] 错误日志..."
ERROR_COUNT=$(grep -c ERROR logs/*.log 2>/dev/null || echo 0)
echo "错误数量: $ERROR_COUNT"

# 5. 检查API连接
echo "[5/5] API连接..."
python -c "
import requests
try:
    r = requests.get('https://api.openai.com', timeout=5)
    print('✅ API可访问')
except:
    print('❌ API不可访问')
"

echo "=== 检查完成 ==="
```

### 实时监控面板
```python
#!/usr/bin/env python3
# monitor.py - 实时监控面板

import time
import os
from datetime import datetime
from pathlib import Path
import pandas as pd

def clear_screen():
    os.system('clear' if os.name == 'posix' else 'cls')

def get_system_stats():
    """获取系统统计"""
    stats = {}
    
    # 进程数
    import subprocess
    result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
    stats['processes'] = len([l for l in result.stdout.split('\n') if 'python' in l and 'batch' in l])
    
    # 数据统计
    try:
        if Path('pilot_bench_parquet_data/test_results.parquet').exists():
            df = pd.read_parquet('pilot_bench_parquet_data/test_results.parquet')
            stats['total_tests'] = len(df)
            stats['success_rate'] = f"{df['success'].mean():.1%}"
        else:
            stats['total_tests'] = 0
            stats['success_rate'] = "N/A"
    except:
        stats['total_tests'] = 0
        stats['success_rate'] = "N/A"
    
    # 增量文件
    inc_dir = Path('pilot_bench_parquet_data/incremental')
    if inc_dir.exists():
        stats['incremental_files'] = len(list(inc_dir.glob('*.parquet')))
    else:
        stats['incremental_files'] = 0
    
    return stats

def display_dashboard():
    """显示监控面板"""
    while True:
        clear_screen()
        stats = get_system_stats()
        
        print("="*60)
        print(f"📊 PILOT-Bench 系统监控面板")
        print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        print(f"\n📈 数据统计:")
        print(f"  总测试数: {stats['total_tests']}")
        print(f"  成功率: {stats['success_rate']}")
        print(f"  增量文件: {stats['incremental_files']}")
        
        print(f"\n⚙️ 系统状态:")
        print(f"  运行进程: {stats['processes']}")
        
        print("\n按 Ctrl+C 退出")
        
        time.sleep(5)  # 5秒刷新一次

if __name__ == "__main__":
    try:
        display_dashboard()
    except KeyboardInterrupt:
        print("\n监控已停止")
```

---

## ⏰ 定期任务

### Crontab配置
```bash
# 编辑crontab: crontab -e

# 每小时合并Parquet增量数据
0 * * * * cd /path/to/project && python -c "from parquet_data_manager import ParquetDataManager; m=ParquetDataManager(); m.consolidate_incremental_data()" >> logs/cron.log 2>&1

# 每天凌晨2点备份数据
0 2 * * * cd /path/to/project && ./backup_data.sh >> logs/backup.log 2>&1

# 每天凌晨3点清理旧日志
0 3 * * * cd /path/to/project && find logs/ -name "*.log" -mtime +7 -delete

# 每周一凌晨4点生成报告
0 4 * * 1 cd /path/to/project && python generate_weekly_report.py >> logs/report.log 2>&1

# 每天早上9点发送健康检查邮件
0 9 * * * cd /path/to/project && ./health_check.sh | mail -s "System Health Report" admin@example.com
```

### 自动备份脚本
```bash
#!/bin/bash
# backup_data.sh - 自动备份脚本

BACKUP_DIR="backups/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

echo "开始备份 $(date)"

# 1. 备份JSON数据
if [ -f "pilot_bench_cumulative_results/master_database.json" ]; then
    cp pilot_bench_cumulative_results/master_database.json "$BACKUP_DIR/"
    echo "✅ JSON数据已备份"
fi

# 2. 备份Parquet数据
if [ -d "pilot_bench_parquet_data" ]; then
    tar -czf "$BACKUP_DIR/parquet_data.tar.gz" pilot_bench_parquet_data/
    echo "✅ Parquet数据已备份"
fi

# 3. 备份配置文件
cp -r config/ "$BACKUP_DIR/"
echo "✅ 配置文件已备份"

# 4. 清理旧备份（保留30天）
find backups/ -type d -mtime +30 -exec rm -rf {} \; 2>/dev/null

echo "备份完成 $(date)"
```

---

## ⚡ 性能优化

### 内存优化
```python
# memory_optimizer.py - 内存优化工具

import gc
import psutil
import os

def get_memory_usage():
    """获取当前内存使用"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  # MB

def optimize_memory():
    """优化内存使用"""
    before = get_memory_usage()
    
    # 1. 强制垃圾回收
    gc.collect()
    
    # 2. 清理缓存
    import functools
    functools.lru_cache().cache_clear()
    
    # 3. 释放未使用的内存
    import ctypes
    libc = ctypes.CDLL("libc.so.6")
    libc.malloc_trim(0)
    
    after = get_memory_usage()
    
    print(f"内存优化: {before:.1f}MB -> {after:.1f}MB (释放 {before-after:.1f}MB)")
    
    return before - after

# 定期优化
import schedule
schedule.every(30).minutes.do(optimize_memory)
```

### 并发优化
```python
# concurrency_optimizer.py - 并发优化

import os
import multiprocessing

def get_optimal_workers():
    """计算最优工作进程数"""
    cpu_count = multiprocessing.cpu_count()
    
    # 根据不同场景优化
    if os.environ.get('STORAGE_FORMAT') == 'parquet':
        # Parquet模式可以更高并发
        return min(cpu_count * 2, 50)
    else:
        # JSON模式需要限制并发避免冲突
        return min(cpu_count, 10)

def optimize_batch_size(total_tasks, workers):
    """优化批量大小"""
    if total_tasks < 100:
        return max(1, total_tasks // workers)
    elif total_tasks < 1000:
        return 10
    else:
        return 20

# 应用优化
workers = get_optimal_workers()
batch_size = optimize_batch_size(1000, workers)
print(f"优化配置: {workers} workers, batch_size={batch_size}")
```

---

## 💾 数据管理

### 数据清理
```python
#!/usr/bin/env python3
# data_cleanup.py - 数据清理工具

from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

def cleanup_old_incremental(days=7):
    """清理旧的增量文件"""
    inc_dir = Path('pilot_bench_parquet_data/incremental')
    if not inc_dir.exists():
        return
    
    cutoff = datetime.now() - timedelta(days=days)
    removed = 0
    
    for file in inc_dir.glob('*.parquet'):
        if datetime.fromtimestamp(file.stat().st_mtime) < cutoff:
            file.unlink()
            removed += 1
    
    print(f"清理了 {removed} 个旧增量文件")

def deduplicate_data():
    """去重数据"""
    parquet_file = Path('pilot_bench_parquet_data/test_results.parquet')
    if not parquet_file.exists():
        return
    
    df = pd.read_parquet(parquet_file)
    before = len(df)
    
    # 基于test_id去重
    df = df.drop_duplicates(subset=['test_id'], keep='last')
    
    after = len(df)
    
    if before > after:
        df.to_parquet(parquet_file, index=False)
        print(f"去重: {before} -> {after} (删除 {before-after} 条)")
    else:
        print("没有重复数据")

def compress_logs():
    """压缩日志文件"""
    import gzip
    import shutil
    
    log_dir = Path('logs')
    compressed = 0
    
    for log_file in log_dir.glob('*.log'):
        # 只压缩超过1天的日志
        if datetime.fromtimestamp(log_file.stat().st_mtime) < datetime.now() - timedelta(days=1):
            with open(log_file, 'rb') as f_in:
                with gzip.open(f"{log_file}.gz", 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            log_file.unlink()
            compressed += 1
    
    print(f"压缩了 {compressed} 个日志文件")

if __name__ == "__main__":
    print("开始数据清理...")
    cleanup_old_incremental()
    deduplicate_data()
    compress_logs()
    print("清理完成")
```

### 数据迁移
```python
#!/usr/bin/env python3
# data_migration.py - 数据迁移工具

def migrate_json_to_parquet():
    """JSON到Parquet迁移"""
    import json
    import pandas as pd
    from pathlib import Path
    
    json_path = Path("pilot_bench_cumulative_results/master_database.json")
    parquet_path = Path("pilot_bench_parquet_data/test_results.parquet")
    
    if not json_path.exists():
        print("JSON文件不存在")
        return False
    
    # 运行转换脚本
    import subprocess
    result = subprocess.run(['python', 'json_to_parquet_converter.py'], 
                          capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ 迁移成功")
        return True
    else:
        print(f"❌ 迁移失败: {result.stderr}")
        return False

def export_for_analysis():
    """导出数据用于分析"""
    import pandas as pd
    
    # 读取Parquet数据
    df = pd.read_parquet('pilot_bench_parquet_data/test_results.parquet')
    
    # 导出不同格式
    df.to_csv('export/test_results.csv', index=False)
    df.to_excel('export/test_results.xlsx', index=False)
    df.to_json('export/test_results.json', orient='records', indent=2)
    
    print(f"导出 {len(df)} 条记录到 export/ 目录")
```

---

## 🚨 故障恢复

### 紧急恢复流程
```bash
#!/bin/bash
# emergency_recovery.sh - 紧急恢复脚本

echo "=== 紧急恢复流程 ==="

# 1. 停止所有进程
echo "[1/5] 停止所有测试进程..."
pkill -f "batch_test"
pkill -f "smart_batch"
pkill -f "ultra_parallel"
sleep 2

# 2. 备份当前数据
echo "[2/5] 备份当前数据..."
EMERGENCY_BACKUP="emergency_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p $EMERGENCY_BACKUP
cp -r pilot_bench_cumulative_results/ $EMERGENCY_BACKUP/ 2>/dev/null
cp -r pilot_bench_parquet_data/ $EMERGENCY_BACKUP/ 2>/dev/null

# 3. 检查备份
echo "[3/5] 查找可用备份..."
LATEST_BACKUP=$(ls -t backups/*/master_database.json 2>/dev/null | head -1)
if [ -n "$LATEST_BACKUP" ]; then
    echo "找到备份: $LATEST_BACKUP"
    cp $LATEST_BACKUP pilot_bench_cumulative_results/master_database.json
    echo "✅ 已恢复JSON数据"
else
    echo "⚠️ 没有找到备份"
fi

# 4. 验证数据
echo "[4/5] 验证数据..."
python -c "
import json
try:
    with open('pilot_bench_cumulative_results/master_database.json') as f:
        data = json.load(f)
    print('✅ 数据验证通过')
except Exception as e:
    print(f'❌ 数据验证失败: {e}')
"

# 5. 重建索引
echo "[5/5] 重建Parquet索引..."
python -c "
from parquet_data_manager import ParquetDataManager
m = ParquetDataManager()
m.consolidate_incremental_data()
print('✅ 索引重建完成')
"

echo "=== 恢复完成 ==="
```

### 数据修复工具
```python
#!/usr/bin/env python3
# repair_tool.py - 数据修复工具

import json
from pathlib import Path
from datetime import datetime

class DataRepairTool:
    def __init__(self):
        self.db_path = Path("pilot_bench_cumulative_results/master_database.json")
        self.backup_dir = Path("backups")
    
    def diagnose(self):
        """诊断数据问题"""
        issues = []
        
        try:
            with open(self.db_path) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            issues.append(f"JSON解析错误: {e}")
            return issues
        except FileNotFoundError:
            issues.append("数据文件不存在")
            return issues
        
        # 检查必需字段
        required = ['version', 'models', 'summary']
        for field in required:
            if field not in data:
                issues.append(f"缺少必需字段: {field}")
        
        # 检查数据一致性
        if 'models' in data and 'summary' in data:
            actual_total = sum(m.get('total_tests', 0) for m in data['models'].values())
            summary_total = data['summary'].get('total_tests', 0)
            if actual_total != summary_total:
                issues.append(f"数据不一致: 实际={actual_total}, 汇总={summary_total}")
        
        return issues
    
    def repair(self):
        """修复数据"""
        issues = self.diagnose()
        
        if not issues:
            print("✅ 数据正常，无需修复")
            return True
        
        print(f"发现 {len(issues)} 个问题:")
        for issue in issues:
            print(f"  - {issue}")
        
        # 尝试自动修复
        try:
            with open(self.db_path) as f:
                data = json.load(f)
            
            # 修复缺失字段
            if 'version' not in data:
                data['version'] = '3.0'
            if 'models' not in data:
                data['models'] = {}
            if 'summary' not in data:
                data['summary'] = {}
            
            # 修复数据一致性
            actual_total = sum(m.get('total_tests', 0) for m in data['models'].values())
            data['summary']['total_tests'] = actual_total
            data['last_updated'] = datetime.now().isoformat()
            
            # 保存修复后的数据
            with open(self.db_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            print("✅ 数据修复完成")
            return True
            
        except Exception as e:
            print(f"❌ 修复失败: {e}")
            return False

if __name__ == "__main__":
    tool = DataRepairTool()
    tool.repair()
```

---

## 📊 系统监控

### Prometheus配置
```yaml
# prometheus.yml - Prometheus监控配置

global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'pilot_bench'
    static_configs:
      - targets: ['localhost:8000']
    
  - job_name: 'node_exporter'
    static_configs:
      - targets: ['localhost:9100']
```

### 监控指标导出
```python
#!/usr/bin/env python3
# metrics_exporter.py - 导出Prometheus指标

from prometheus_client import start_http_server, Gauge, Counter
import time
from pathlib import Path
import pandas as pd

# 定义指标
total_tests = Gauge('pilot_bench_total_tests', 'Total number of tests')
success_rate = Gauge('pilot_bench_success_rate', 'Overall success rate')
incremental_files = Gauge('pilot_bench_incremental_files', 'Number of incremental files')
api_errors = Counter('pilot_bench_api_errors', 'Total API errors')

def update_metrics():
    """更新指标"""
    # 更新测试总数
    try:
        df = pd.read_parquet('pilot_bench_parquet_data/test_results.parquet')
        total_tests.set(len(df))
        success_rate.set(df['success'].mean())
    except:
        pass
    
    # 更新增量文件数
    inc_dir = Path('pilot_bench_parquet_data/incremental')
    if inc_dir.exists():
        incremental_files.set(len(list(inc_dir.glob('*.parquet'))))

if __name__ == '__main__':
    # 启动HTTP服务器
    start_http_server(8000)
    
    # 定期更新指标
    while True:
        update_metrics()
        time.sleep(30)
```

---

## 🔧 维护脚本

### 一键维护脚本
```bash
#!/bin/bash
# maintenance.sh - 一键维护脚本

function show_menu() {
    echo "================================"
    echo "    系统维护菜单"
    echo "================================"
    echo "1. 日常检查"
    echo "2. 数据备份"
    echo "3. 数据清理"
    echo "4. 性能优化"
    echo "5. 故障恢复"
    echo "6. 生成报告"
    echo "7. 查看监控"
    echo "0. 退出"
    echo "================================"
}

function daily_check() {
    ./daily_check.sh
}

function backup_data() {
    ./backup_data.sh
}

function cleanup_data() {
    python data_cleanup.py
}

function optimize_performance() {
    python memory_optimizer.py
    echo "性能优化完成"
}

function emergency_recovery() {
    ./emergency_recovery.sh
}

function generate_report() {
    python generate_report.py
}

function show_monitoring() {
    python monitor.py
}

# 主循环
while true; do
    show_menu
    read -p "请选择操作 [0-7]: " choice
    
    case $choice in
        1) daily_check ;;
        2) backup_data ;;
        3) cleanup_data ;;
        4) optimize_performance ;;
        5) emergency_recovery ;;
        6) generate_report ;;
        7) show_monitoring ;;
        0) echo "退出维护系统"; exit 0 ;;
        *) echo "无效选择" ;;
    esac
    
    echo ""
    read -p "按回车继续..."
done
```

---

## 📚 相关文档

### 内部文档
- [DEBUG_KNOWLEDGE_BASE_V2.md](./DEBUG_KNOWLEDGE_BASE_V2.md) - 调试知识库
- [COMMON_ISSUES_V2.md](./COMMON_ISSUES_V2.md) - 常见问题
- [PARQUET_GUIDE.md](../guides/PARQUET_GUIDE.md) - Parquet指南

### 外部工具
- [Prometheus](https://prometheus.io/) - 监控系统
- [Grafana](https://grafana.com/) - 可视化面板
- [Sentry](https://sentry.io/) - 错误追踪

---

**文档版本**: 1.0  
**创建时间**: 2025-08-17  
**维护者**: System Administrator  
**状态**: 🟢 Active | ✅ 完整