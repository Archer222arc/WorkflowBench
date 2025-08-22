#!/usr/bin/env python3
"""诊断5.3测试数据未保存问题"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

def check_environment():
    """检查环境变量"""
    print("=== 环境变量检查 ===")
    storage_format = os.environ.get('STORAGE_FORMAT', 'json')
    print(f"STORAGE_FORMAT: {storage_format}")
    
    # 检查Python路径
    print(f"Python路径: {sys.executable}")
    print(f"当前工作目录: {os.getcwd()}")
    
    return storage_format

def check_processes():
    """检查运行中的进程"""
    print("\n=== 运行中的进程 ===")
    
    result = subprocess.run(
        ['ps', 'aux'], 
        capture_output=True, 
        text=True
    )
    
    processes = []
    for line in result.stdout.split('\n'):
        if 'smart_batch_runner' in line and 'flawed' in line:
            # 提取进程信息
            parts = line.split()
            if len(parts) > 10:
                pid = parts[1]
                start_time = parts[8]
                cmd = ' '.join(parts[10:])
                processes.append({
                    'pid': pid,
                    'start_time': start_time,
                    'cmd': cmd[:100]  # 截断命令
                })
    
    print(f"找到 {len(processes)} 个5.3测试进程")
    for p in processes[:5]:  # 只显示前5个
        print(f"  PID {p['pid']}: 启动于 {p['start_time']}")
    
    return processes

def check_data_files():
    """检查数据文件状态"""
    print("\n=== 数据文件状态 ===")
    
    # JSON文件
    json_path = Path('pilot_bench_cumulative_results/master_database.json')
    if json_path.exists():
        stat = json_path.stat()
        mod_time = datetime.fromtimestamp(stat.st_mtime)
        age = datetime.now() - mod_time
        print(f"JSON数据库:")
        print(f"  最后修改: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  年龄: {age}")
        print(f"  大小: {stat.st_size / 1024:.1f} KB")
        
        # 检查内容
        with open(json_path, 'r') as f:
            data = json.load(f)
            total_tests = data.get('summary', {}).get('total_tests', 0)
            models = list(data.get('models', {}).keys())
            print(f"  总测试数: {total_tests}")
            print(f"  模型数: {len(models)}")
            
            # 检查是否有flawed数据
            flawed_count = 0
            for model_name, model_data in data.get('models', {}).items():
                if 'by_prompt_type' in model_data:
                    for prompt_type in model_data['by_prompt_type']:
                        if 'flawed' in prompt_type:
                            flawed_count += 1
            print(f"  Flawed prompt类型数: {flawed_count}")
    
    # Parquet文件
    parquet_path = Path('pilot_bench_parquet_data/test_results.parquet')
    if parquet_path.exists():
        stat = parquet_path.stat()
        mod_time = datetime.fromtimestamp(stat.st_mtime)
        age = datetime.now() - mod_time
        print(f"\nParquet数据:")
        print(f"  最后修改: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  年龄: {age}")
        print(f"  大小: {stat.st_size / 1024:.1f} KB")
        
        # 检查内容
        df = pd.read_parquet(parquet_path)
        print(f"  总记录数: {len(df)}")
        if 'prompt_type' in df.columns:
            flawed_types = df[df['prompt_type'].str.contains('flawed', na=False)]['prompt_type'].unique()
            print(f"  Flawed类型: {list(flawed_types)}")

def check_incremental_files():
    """检查增量文件"""
    print("\n=== 增量文件检查 ===")
    
    incremental_dirs = [
        'pilot_bench_parquet_data/incremental',
        'pilot_bench_cumulative_results/parquet_data/incremental'
    ]
    
    for dir_path in incremental_dirs:
        path = Path(dir_path)
        if path.exists():
            files = list(path.glob('*.parquet'))
            print(f"{dir_path}:")
            print(f"  文件数: {len(files)}")
            if files:
                for f in files[:3]:  # 只显示前3个
                    stat = f.stat()
                    print(f"    {f.name}: {stat.st_size / 1024:.1f} KB")
        else:
            print(f"{dir_path}: 不存在")

def check_logs():
    """检查最新日志"""
    print("\n=== 最新日志检查 ===")
    
    log_dir = Path('logs')
    if log_dir.exists():
        # 找到最新的日志文件
        log_files = list(log_dir.glob('batch_test_*.log'))
        if log_files:
            latest_log = max(log_files, key=lambda f: f.stat().st_mtime)
            print(f"最新日志: {latest_log.name}")
            
            # 读取最后50行
            with open(latest_log, 'r') as f:
                lines = f.readlines()
                
            # 统计关键信息
            error_count = sum(1 for line in lines if 'ERROR' in line)
            success_count = sum(1 for line in lines if '成功' in line or 'success' in line.lower())
            failed_count = sum(1 for line in lines if '失败' in line or 'failed' in line.lower())
            
            print(f"  错误数: {error_count}")
            print(f"  成功数: {success_count}")
            print(f"  失败数: {failed_count}")
            
            # 显示最后几行
            print("\n最后10行日志:")
            for line in lines[-10:]:
                print(f"  {line.strip()}")

def test_import_and_save():
    """测试导入和保存功能"""
    print("\n=== 测试导入和保存 ===")
    
    storage_format = os.environ.get('STORAGE_FORMAT', 'json')
    
    try:
        if storage_format == 'parquet':
            print("尝试导入ParquetCumulativeManager...")
            from parquet_cumulative_manager import ParquetCumulativeManager
            manager = ParquetCumulativeManager()
            print("✅ 成功导入ParquetCumulativeManager")
            
            # 检查关键方法
            methods = ['add_test_result_with_classification', '_flush_buffer', 'save_database']
            for method in methods:
                if hasattr(manager, method):
                    print(f"  ✅ {method} 存在")
                else:
                    print(f"  ❌ {method} 不存在")
                    
        else:
            print("尝试导入EnhancedCumulativeManager...")
            from enhanced_cumulative_manager import EnhancedCumulativeManager
            manager = EnhancedCumulativeManager()
            print("✅ 成功导入EnhancedCumulativeManager")
            
        # 测试添加数据
        from cumulative_test_manager import TestRecord
        test_record = TestRecord(
            model='test-model',
            task_type='simple_task',
            prompt_type='flawed_sequence_disorder',
            difficulty='easy',
            tool_success_rate=0.8,
            success=True,
            execution_time=5.0,
            turns=10,
            tool_calls=5
        )
        
        print("\n尝试添加测试记录...")
        result = manager.add_test_result_with_classification(test_record)
        print(f"添加结果: {result}")
        
        if storage_format == 'parquet' and hasattr(manager, '_flush_buffer'):
            print("刷新缓冲区...")
            manager._flush_buffer()
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

def check_python_modules():
    """检查Python模块状态"""
    print("\n=== Python模块检查 ===")
    
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
            print(f"✅ {module_name}: 可导入")
            
            # 检查关键属性
            if module_name == 'smart_batch_runner':
                if hasattr(module, 'SmartBatchRunner'):
                    print(f"  ✅ SmartBatchRunner类存在")
                    
        except ImportError as e:
            print(f"❌ {module_name}: 导入失败 - {e}")

def main():
    """主函数"""
    print("=" * 60)
    print("5.3测试数据未保存问题诊断")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 执行各项检查
    storage_format = check_environment()
    check_processes()
    check_data_files()
    check_incremental_files()
    check_logs()
    check_python_modules()
    test_import_and_save()
    
    # 诊断结论
    print("\n" + "=" * 60)
    print("诊断结论:")
    
    # 检查数据是否更新
    json_path = Path('pilot_bench_cumulative_results/master_database.json')
    if json_path.exists():
        age = datetime.now() - datetime.fromtimestamp(json_path.stat().st_mtime)
        if age > timedelta(hours=1):
            print("⚠️ 数据文件超过1小时未更新")
            print("可能原因:")
            print("  1. 数据保存功能被禁用或失败")
            print("  2. 进程仍在生成workflow阶段")
            print("  3. 环境变量未正确传递到Python脚本")
            print("  4. 文件锁导致写入阻塞")
        else:
            print("✅ 数据文件最近有更新")
    
    print("=" * 60)

if __name__ == "__main__":
    main()