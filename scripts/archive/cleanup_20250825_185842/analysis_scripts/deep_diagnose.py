#!/usr/bin/env python3
"""深度诊断为什么数据没有保存"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import time

def check_running_processes():
    """检查当前运行的Python进程"""
    print("=== 1. 检查运行中的Python进程 ===")
    
    result = subprocess.run(
        ['ps', 'aux'], 
        capture_output=True, 
        text=True
    )
    
    python_processes = []
    for line in result.stdout.split('\n'):
        if 'python' in line and ('smart_batch' in line or 'ultra_parallel' in line):
            parts = line.split()
            if len(parts) > 10:
                pid = parts[1]
                cpu = parts[2]
                mem = parts[3]
                start_time = parts[8]
                cmd = ' '.join(parts[10:])[:100]
                python_processes.append({
                    'pid': pid,
                    'cpu': cpu,
                    'mem': mem,
                    'start_time': start_time,
                    'cmd': cmd
                })
    
    print(f"找到 {len(python_processes)} 个相关Python进程")
    for p in python_processes[:5]:
        print(f"  PID {p['pid']}: CPU={p['cpu']}%, MEM={p['mem']}%, 启动于 {p['start_time']}")
        print(f"    命令: {p['cmd']}")
    
    return python_processes

def trace_process_activity(pid):
    """跟踪进程活动"""
    print(f"\n=== 2. 跟踪进程 {pid} 的活动 ===")
    
    # 使用lsof查看进程打开的文件
    try:
        result = subprocess.run(
            ['lsof', '-p', str(pid)], 
            capture_output=True, 
            text=True,
            timeout=5
        )
        
        files = []
        for line in result.stdout.split('\n'):
            if 'pilot_bench' in line or '.json' in line or '.parquet' in line:
                files.append(line)
        
        if files:
            print(f"进程 {pid} 打开的相关文件:")
            for f in files[:5]:
                print(f"  {f}")
        else:
            print(f"进程 {pid} 没有打开数据文件")
            
    except Exception as e:
        print(f"无法跟踪进程 {pid}: {e}")

def check_latest_logs():
    """检查最新的日志内容"""
    print("\n=== 3. 检查最新日志 ===")
    
    log_dir = Path('logs')
    if log_dir.exists():
        # 找到最新的batch_test日志
        batch_logs = list(log_dir.glob('batch_test_*.log'))
        if batch_logs:
            latest_log = max(batch_logs, key=lambda f: f.stat().st_mtime)
            print(f"最新日志: {latest_log.name}")
            
            # 读取日志内容
            with open(latest_log, 'r') as f:
                lines = f.readlines()
            
            # 查找关键信息
            save_attempts = 0
            errors = 0
            workflow_generating = 0
            
            for line in lines:
                if 'Saving' in line or 'save' in line.lower():
                    save_attempts += 1
                if 'ERROR' in line or 'error' in line.lower():
                    errors += 1
                if 'Generating' in line or 'workflow' in line.lower():
                    workflow_generating += 1
            
            print(f"  保存尝试: {save_attempts}")
            print(f"  错误数: {errors}")
            print(f"  工作流生成: {workflow_generating}")
            
            # 显示最后20行
            print("\n最后20行日志:")
            for line in lines[-20:]:
                print(f"  {line.strip()}")
            
            return latest_log
    
    return None

def test_data_save_directly():
    """直接测试数据保存功能"""
    print("\n=== 4. 直接测试数据保存 ===")
    
    storage_format = os.environ.get('STORAGE_FORMAT', 'json')
    print(f"当前STORAGE_FORMAT: {storage_format}")
    
    # 尝试直接调用保存功能
    test_code = """
import os
import sys
from pathlib import Path

# 设置环境变量
os.environ['STORAGE_FORMAT'] = '{}'

# 导入管理器
storage_format = os.environ.get('STORAGE_FORMAT', 'json').lower()
print(f"使用存储格式: {{storage_format}}")

if storage_format == 'parquet':
    from parquet_cumulative_manager import ParquetCumulativeManager as Manager
else:
    from enhanced_cumulative_manager import EnhancedCumulativeManager as Manager

# 创建管理器
manager = Manager()
print(f"Manager类型: {{type(manager).__name__}}")

# 创建测试记录
from cumulative_test_manager import TestRecord
import time

record = TestRecord(
    model='diagnose-test-model',
    task_type='simple_task',
    prompt_type='baseline',
    difficulty='easy'
)

# 设置记录属性
record.timestamp = time.time()
record.success = True
record.execution_time = 1.0
record.turns = 5
record.tool_calls = 3

# 尝试添加记录
print("尝试添加记录...")
success = manager.add_test_result_with_classification(record)
print(f"添加结果: {{success}}")

# 强制保存
if hasattr(manager, 'save_database'):
    print("调用save_database()...")
    manager.save_database()
    
if hasattr(manager, '_flush_buffer'):
    print("调用_flush_buffer()...")
    manager._flush_buffer()

print("保存操作完成")
""".format(storage_format)
    
    # 写入临时文件并执行
    with open('temp_save_test.py', 'w') as f:
        f.write(test_code)
    
    result = subprocess.run(
        [sys.executable, 'temp_save_test.py'],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    print("输出:")
    print(result.stdout)
    if result.stderr:
        print("错误:")
        print(result.stderr)
    
    # 清理
    Path('temp_save_test.py').unlink(missing_ok=True)
    
    return result.returncode == 0

def check_file_permissions():
    """检查文件权限"""
    print("\n=== 5. 检查文件权限 ===")
    
    paths_to_check = [
        'pilot_bench_cumulative_results',
        'pilot_bench_cumulative_results/master_database.json',
        'pilot_bench_parquet_data',
        'pilot_bench_parquet_data/test_results.parquet'
    ]
    
    for path_str in paths_to_check:
        path = Path(path_str)
        if path.exists():
            stat = path.stat()
            mode = oct(stat.st_mode)[-3:]
            print(f"  {path_str}: 权限={mode}, 可写={os.access(path, os.W_OK)}")
        else:
            print(f"  {path_str}: 不存在")
            # 尝试创建
            if path_str.endswith('.json') or path_str.endswith('.parquet'):
                parent = path.parent
                if not parent.exists():
                    print(f"    尝试创建父目录 {parent}...")
                    try:
                        parent.mkdir(parents=True, exist_ok=True)
                        print(f"    ✅ 父目录创建成功")
                    except Exception as e:
                        print(f"    ❌ 创建失败: {e}")

def check_python_imports():
    """检查Python导入是否正常"""
    print("\n=== 6. 检查Python模块导入 ===")
    
    modules_to_check = [
        'smart_batch_runner',
        'batch_test_runner',
        'enhanced_cumulative_manager',
        'parquet_cumulative_manager',
        'cumulative_test_manager'
    ]
    
    for module_name in modules_to_check:
        try:
            module = __import__(module_name)
            print(f"  ✅ {module_name}: 可导入")
            
            # 检查关键函数
            if module_name == 'smart_batch_runner':
                if hasattr(module, 'SmartBatchRunner'):
                    runner = module.SmartBatchRunner()
                    if hasattr(runner, 'commit_to_database'):
                        print(f"    ✅ commit_to_database方法存在")
                    else:
                        print(f"    ❌ commit_to_database方法不存在")
                        
        except ImportError as e:
            print(f"  ❌ {module_name}: 导入失败 - {e}")

def monitor_file_changes():
    """监控文件变化"""
    print("\n=== 7. 监控文件变化（10秒） ===")
    
    files_to_monitor = [
        'pilot_bench_cumulative_results/master_database.json',
        'pilot_bench_parquet_data/test_results.parquet'
    ]
    
    initial_state = {}
    for file_path in files_to_monitor:
        path = Path(file_path)
        if path.exists():
            initial_state[file_path] = {
                'size': path.stat().st_size,
                'mtime': path.stat().st_mtime
            }
    
    print("开始监控...")
    time.sleep(10)
    
    for file_path in files_to_monitor:
        path = Path(file_path)
        if path.exists():
            current_size = path.stat().st_size
            current_mtime = path.stat().st_mtime
            
            if file_path in initial_state:
                size_change = current_size - initial_state[file_path]['size']
                time_change = current_mtime - initial_state[file_path]['mtime']
                
                if size_change != 0 or time_change > 0:
                    print(f"  ✅ {file_path}: 有变化！大小变化={size_change}字节")
                else:
                    print(f"  ❌ {file_path}: 无变化")
            else:
                print(f"  🆕 {file_path}: 新创建")

def main():
    """主函数"""
    print("=" * 60)
    print("深度诊断：为什么数据没有保存")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. 检查进程
    processes = check_running_processes()
    
    # 2. 如果有进程，跟踪第一个
    if processes:
        trace_process_activity(processes[0]['pid'])
    
    # 3. 检查日志
    check_latest_logs()
    
    # 4. 测试保存功能
    save_ok = test_data_save_directly()
    
    # 5. 检查权限
    check_file_permissions()
    
    # 6. 检查导入
    check_python_imports()
    
    # 7. 监控文件变化
    monitor_file_changes()
    
    # 诊断结论
    print("\n" + "=" * 60)
    print("诊断结论:")
    
    if not processes:
        print("⚠️ 没有测试进程在运行")
    elif not save_ok:
        print("❌ 数据保存功能有问题")
    else:
        print("🤔 需要进一步调查:")
        print("  1. 检查是否卡在workflow生成阶段")
        print("  2. 检查是否有死锁或无限循环")
        print("  3. 检查内存使用是否正常")
        print("  4. 检查是否有异常被静默捕获")
    
    print("=" * 60)

if __name__ == "__main__":
    main()