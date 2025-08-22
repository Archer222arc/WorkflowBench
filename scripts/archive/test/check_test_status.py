#!/usr/bin/env python3
"""检查测试状态和数据存储情况"""

import os
import json
import subprocess
from pathlib import Path
from datetime import datetime

def check_running_processes():
    """检查运行中的测试进程"""
    print("\n🔍 运行中的测试进程:")
    result = subprocess.run(
        "ps aux | grep -E '(smart_batch_runner|ultra_parallel|batch_test)' | grep -v grep",
        shell=True, capture_output=True, text=True
    )
    
    processes = result.stdout.strip().split('\n')
    if processes and processes[0]:
        print(f"  找到 {len(processes)} 个进程")
        for proc in processes[:5]:  # 只显示前5个
            parts = proc.split()
            if len(parts) > 10:
                cmd = ' '.join(parts[10:13])  # 命令的前几个参数
                print(f"    PID {parts[1]}: {cmd}...")
    else:
        print("  没有找到运行中的测试进程")

def check_storage_format():
    """检查存储格式配置"""
    print("\n💾 存储格式配置:")
    
    # 检查环境变量
    storage_format = os.environ.get('STORAGE_FORMAT', 'json')
    print(f"  环境变量 STORAGE_FORMAT: {storage_format}")
    
    # 检查Parquet目录
    parquet_dir = Path('pilot_bench_cumulative_results/parquet_data')
    if parquet_dir.exists():
        parquet_files = list(parquet_dir.glob('**/*.parquet'))
        print(f"  ✅ Parquet目录存在")
        print(f"  Parquet文件数: {len(parquet_files)}")
        
        # 检查最新文件
        if parquet_files:
            latest = max(parquet_files, key=lambda p: p.stat().st_mtime)
            mtime = datetime.fromtimestamp(latest.stat().st_mtime)
            print(f"  最新文件: {latest.name}")
            print(f"  更新时间: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print(f"  ❌ Parquet目录不存在")
    
    # 检查JSON数据库
    json_db = Path('pilot_bench_cumulative_results/master_database.json')
    if json_db.exists():
        mtime = datetime.fromtimestamp(json_db.stat().st_mtime)
        print(f"  ✅ JSON数据库存在")
        print(f"  更新时间: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 统计测试数
        with open(json_db, 'r') as f:
            db = json.load(f)
        
        total_tests = 0
        for model_data in db.get('models', {}).values():
            if 'by_prompt_type' in model_data:
                for prompt_data in model_data['by_prompt_type'].values():
                    if 'by_tool_success_rate' in prompt_data:
                        for rate_data in prompt_data['by_tool_success_rate'].values():
                            if 'by_difficulty' in rate_data:
                                for diff_data in rate_data['by_difficulty'].values():
                                    if 'by_task_type' in diff_data:
                                        for task_data in diff_data['by_task_type'].values():
                                            total_tests += task_data.get('total', 0)
        
        print(f"  总测试数: {total_tests}")

def check_logs():
    """检查最新日志"""
    print("\n📝 最新日志:")
    
    log_dir = Path('logs')
    if log_dir.exists():
        # 找最新的batch_test日志
        batch_logs = list(log_dir.glob('batch_test_*.log'))
        if batch_logs:
            latest = max(batch_logs, key=lambda p: p.stat().st_mtime)
            mtime = datetime.fromtimestamp(latest.stat().st_mtime)
            print(f"  最新日志: {latest.name}")
            print(f"  更新时间: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 显示最后几行
            with open(latest, 'r') as f:
                lines = f.readlines()
                last_lines = lines[-5:] if len(lines) > 5 else lines
                print("  最后几行:")
                for line in last_lines:
                    print(f"    {line.strip()}")

def suggest_actions():
    """建议操作"""
    print("\n💡 建议操作:")
    
    storage_format = os.environ.get('STORAGE_FORMAT', 'json')
    
    if storage_format != 'parquet':
        print("  1. 你选择了Parquet但环境变量未设置")
        print("     解决方法: 在运行测试的终端中执行:")
        print("     export STORAGE_FORMAT=parquet")
    
    parquet_dir = Path('pilot_bench_cumulative_results/parquet_data')
    if not parquet_dir.exists() and storage_format == 'parquet':
        print("  2. Parquet目录不存在")
        print("     解决方法: 创建目录")
        print("     mkdir -p pilot_bench_cumulative_results/parquet_data/incremental")
    
    print("\n  3. 查看实时进度:")
    print("     tail -f logs/batch_test_*.log | grep -E '(成功|失败|完成|checkpoint)'")
    
    print("\n  4. 如果测试卡住，可以:")
    print("     - 查看具体进程: ps aux | grep smart_batch_runner")
    print("     - 终止测试: pkill -f smart_batch_runner")
    print("     - 重新开始（会从checkpoint恢复）")

if __name__ == "__main__":
    print("=" * 50)
    print("PILOT-Bench 测试状态检查")
    print("=" * 50)
    
    check_running_processes()
    check_storage_format()
    check_logs()
    suggest_actions()
    
    print("\n" + "=" * 50)
