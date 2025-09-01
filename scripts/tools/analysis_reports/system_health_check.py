#!/usr/bin/env python3
"""系统健康检查脚本 - 深入检查潜在问题"""

import os
import sys
import json
import importlib
import traceback
from pathlib import Path
from datetime import datetime
import pandas as pd

def check_import_health():
    """检查关键模块是否能正确导入"""
    print("\n=== 模块导入健康检查 ===")
    modules_to_check = [
        'batch_test_runner',
        'smart_batch_runner',
        'ultra_parallel_runner',
        'enhanced_cumulative_manager',
        'cumulative_test_manager',
        'parquet_cumulative_manager',
        'file_lock_manager'
    ]
    
    results = {}
    for module_name in modules_to_check:
        try:
            module = importlib.import_module(module_name)
            results[module_name] = "✅ OK"
        except ImportError as e:
            results[module_name] = f"❌ 导入失败: {e}"
        except Exception as e:
            results[module_name] = f"⚠️ 其他错误: {e}"
    
    for module, status in results.items():
        print(f"  {module}: {status}")
    
    return all("✅" in status for status in results.values())

def check_critical_methods():
    """检查关键方法是否存在"""
    print("\n=== 关键方法检查 ===")
    
    checks = []
    
    # 检查BatchTestRunner
    try:
        from batch_test_runner import BatchTestRunner
        runner = BatchTestRunner(debug=False, silent=True)
        
        methods_to_check = [
            '_run_single_test_safe',
            'run_single_test',
            'run_batch_test',
            'get_smart_tasks'
        ]
        
        for method in methods_to_check:
            if hasattr(runner, method):
                print(f"  BatchTestRunner.{method}: ✅ 存在")
                checks.append(True)
            else:
                print(f"  BatchTestRunner.{method}: ❌ 不存在")
                checks.append(False)
                
    except Exception as e:
        print(f"  BatchTestRunner: ❌ 无法检查 - {e}")
        checks.append(False)
    
    # 检查Manager类
    try:
        from enhanced_cumulative_manager import EnhancedCumulativeManager
        manager = EnhancedCumulativeManager()
        
        methods_to_check = [
            'save_database',
            'add_test_result_with_classification',
            'get_runtime_summary'
        ]
        
        for method in methods_to_check:
            if hasattr(manager, method):
                print(f"  EnhancedCumulativeManager.{method}: ✅ 存在")
                checks.append(True)
            else:
                print(f"  EnhancedCumulativeManager.{method}: ❌ 不存在")
                checks.append(False)
                
    except Exception as e:
        print(f"  EnhancedCumulativeManager: ❌ 无法检查 - {e}")
        checks.append(False)
    
    return all(checks)

def check_data_consistency():
    """检查数据一致性"""
    print("\n=== 数据一致性检查 ===")
    
    # 检查JSON数据库
    json_path = Path('pilot_bench_cumulative_results/master_database.json')
    json_data = None
    if json_path.exists():
        with open(json_path, 'r') as f:
            json_data = json.load(f)
        
        json_tests = json_data.get('summary', {}).get('total_tests', 0)
        json_models = len(json_data.get('models', {}))
        print(f"  JSON数据库: {json_tests} 测试, {json_models} 模型")
    else:
        print(f"  JSON数据库: ❌ 文件不存在")
    
    # 检查Parquet数据
    parquet_path = Path('pilot_bench_parquet_data/test_results.parquet')
    parquet_data = None
    if parquet_path.exists():
        parquet_data = pd.read_parquet(parquet_path)
        parquet_tests = len(parquet_data)
        parquet_models = parquet_data['model'].nunique() if 'model' in parquet_data.columns else 0
        print(f"  Parquet数据: {parquet_tests} 记录, {parquet_models} 模型")
    else:
        print(f"  Parquet数据: ❌ 文件不存在")
    
    # 检查一致性
    if json_data and parquet_data is not None:
        if json_tests == parquet_tests:
            print(f"  数据一致性: ✅ 匹配 ({json_tests} = {parquet_tests})")
            return True
        else:
            print(f"  数据一致性: ⚠️ 不匹配 (JSON:{json_tests} ≠ Parquet:{parquet_tests})")
            return False
    
    return None

def check_potential_issues():
    """检查潜在问题"""
    print("\n=== 潜在问题检查 ===")
    
    issues = []
    
    # 检查是否有Python缓存文件
    cache_files = list(Path('__pycache__').glob('*.pyc')) if Path('__pycache__').exists() else []
    if cache_files:
        print(f"  ⚠️ 发现 {len(cache_files)} 个缓存文件，建议清理")
        issues.append("cache_files")
    else:
        print(f"  ✅ 没有Python缓存文件")
    
    # 检查日志文件大小
    log_dir = Path('logs')
    if log_dir.exists():
        log_files = list(log_dir.glob('*.log'))
        large_logs = [f for f in log_files if f.stat().st_size > 10 * 1024 * 1024]  # >10MB
        if large_logs:
            print(f"  ⚠️ 发现 {len(large_logs)} 个大日志文件 (>10MB)")
            issues.append("large_logs")
        else:
            print(f"  ✅ 日志文件大小正常")
    
    # 检查临时文件
    temp_files = list(Path('.').glob('*.tmp')) + list(Path('.').glob('*.backup*'))
    if temp_files:
        print(f"  ⚠️ 发现 {len(temp_files)} 个临时/备份文件")
        issues.append("temp_files")
    else:
        print(f"  ✅ 没有临时文件")
    
    # 检查进程
    import subprocess
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        python_processes = [line for line in result.stdout.split('\n') 
                          if 'python' in line and ('batch' in line or 'smart' in line or 'ultra' in line)]
        if python_processes:
            print(f"  ⚠️ 发现 {len(python_processes)} 个运行中的测试进程")
            issues.append("running_processes")
        else:
            print(f"  ✅ 没有运行中的测试进程")
    except:
        print(f"  ⚫ 无法检查进程状态")
    
    return issues

def check_return_statements():
    """检查关键方法是否有return语句"""
    print("\n=== Return语句检查 ===")
    
    critical_files = [
        ('batch_test_runner.py', ['_run_single_test_safe', 'run_single_test']),
        ('smart_batch_runner.py', ['run_batch', 'commit_to_database']),
        ('enhanced_cumulative_manager.py', ['save_database', 'add_test_result_with_classification'])
    ]
    
    issues = []
    for filename, methods in critical_files:
        file_path = Path(filename)
        if not file_path.exists():
            print(f"  {filename}: ❌ 文件不存在")
            continue
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        for method in methods:
            # 简单检查方法定义和return
            method_def = f"def {method}"
            if method_def in content:
                # 找到方法的大致位置
                method_start = content.index(method_def)
                # 检查接下来1000个字符内是否有return
                method_content = content[method_start:method_start+2000]
                
                # 统计return语句（排除注释中的）
                returns = []
                for line in method_content.split('\n'):
                    stripped = line.strip()
                    if stripped.startswith('return') and not stripped.startswith('#'):
                        returns.append(line)
                
                if returns:
                    print(f"  {filename}.{method}: ✅ 有{len(returns)}个return语句")
                else:
                    print(f"  {filename}.{method}: ⚠️ 没有找到return语句")
                    issues.append(f"{filename}.{method}")
            else:
                print(f"  {filename}.{method}: ❌ 方法不存在")
                issues.append(f"{filename}.{method}")
    
    return issues

def main():
    """运行完整的系统健康检查"""
    print("=" * 60)
    print("系统健康检查报告")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    all_good = True
    
    # 1. 模块导入检查
    if not check_import_health():
        all_good = False
    
    # 2. 关键方法检查
    if not check_critical_methods():
        all_good = False
    
    # 3. 数据一致性检查
    consistency = check_data_consistency()
    if consistency is False:
        all_good = False
    
    # 4. 潜在问题检查
    issues = check_potential_issues()
    if issues:
        all_good = False
    
    # 5. Return语句检查
    return_issues = check_return_statements()
    if return_issues:
        all_good = False
    
    # 总结
    print("\n" + "=" * 60)
    print("总体健康状态:")
    if all_good:
        print("🎉 系统健康，所有检查通过！")
    else:
        print("⚠️ 发现一些问题需要关注：")
        if issues:
            print(f"  - 潜在问题: {', '.join(issues)}")
        if return_issues:
            print(f"  - Return语句问题: {', '.join(return_issues)}")
    
    print("=" * 60)
    
    return 0 if all_good else 1

if __name__ == "__main__":
    sys.exit(main())