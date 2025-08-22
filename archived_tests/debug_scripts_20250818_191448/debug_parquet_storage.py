#!/usr/bin/env python3
"""
调试Parquet存储不更新问题
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

def check_environment():
    """检查环境变量"""
    print("="*60)
    print("1. 检查环境变量")
    print("="*60)
    
    storage_format = os.environ.get('STORAGE_FORMAT', 'json')
    print(f"STORAGE_FORMAT: {storage_format}")
    
    # 检查Python内部是否正确识别
    print("\n测试环境变量传递:")
    result = subprocess.run([
        'python', '-c', 
        'import os; print(f"Python内部STORAGE_FORMAT: {os.environ.get(\\"STORAGE_FORMAT\\", \\"json\\")}")'
    ], capture_output=True, text=True)
    print(result.stdout.strip())
    
    # 使用env命令传递
    result = subprocess.run([
        'env', 'STORAGE_FORMAT=parquet', 'python', '-c',
        'import os; print(f"通过env传递后: {os.environ.get(\\"STORAGE_FORMAT\\", \\"json\\")}")'
    ], capture_output=True, text=True)
    print(result.stdout.strip())

def check_parquet_manager():
    """检查ParquetCumulativeManager是否工作"""
    print("\n" + "="*60)
    print("2. 测试ParquetCumulativeManager")
    print("="*60)
    
    # 设置环境变量
    os.environ['STORAGE_FORMAT'] = 'parquet'
    
    try:
        from parquet_cumulative_manager import ParquetCumulativeManager
        print("✅ 成功导入ParquetCumulativeManager")
        
        # 创建实例
        manager = ParquetCumulativeManager()
        print("✅ 成功创建ParquetCumulativeManager实例")
        
        # 测试添加数据
        from cumulative_test_manager import TestRecord
        
        record = TestRecord(
            model="parquet-test-model",
            task_type="simple_task",
            prompt_type="baseline",
            difficulty="easy",
            tool_reliability=0.8,
            success=True,
            execution_time=2.5,
            turns=5,
            tool_calls=3
        )
        
        print("\n添加测试记录...")
        success = manager.add_test_result_with_classification(record)
        print(f"add_test_result_with_classification返回: {success}")
        
        # 刷新缓冲区
        print("\n刷新缓冲区...")
        manager._flush_buffer()
        
        # 检查Parquet文件
        parquet_file = Path("pilot_bench_parquet_data/test_results.parquet")
        if parquet_file.exists():
            import pandas as pd
            df = pd.read_parquet(parquet_file)
            print(f"✅ Parquet文件存在，包含 {len(df)} 条记录")
            
            # 检查是否有新模型
            if 'model' in df.columns:
                models = df['model'].unique()
                if 'parquet-test-model' in models:
                    print("✅ parquet-test-model已保存到Parquet")
                else:
                    print("❌ parquet-test-model未找到")
                    print(f"现有模型: {list(models)[:5]}")
        else:
            print("❌ Parquet文件不存在")
            
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

def check_smart_batch_runner():
    """检查smart_batch_runner如何选择存储格式"""
    print("\n" + "="*60)
    print("3. 检查smart_batch_runner的存储选择")
    print("="*60)
    
    # 读取smart_batch_runner.py
    with open("smart_batch_runner.py", "r") as f:
        content = f.read()
    
    # 查找存储格式相关代码
    if "STORAGE_FORMAT" in content:
        print("✅ smart_batch_runner.py包含STORAGE_FORMAT相关代码")
        
        # 查找具体的判断逻辑
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'STORAGE_FORMAT' in line or 'parquet' in line.lower():
                print(f"Line {i+1}: {line.strip()}")
                if i < len(lines) - 1:
                    print(f"Line {i+2}: {lines[i+1].strip()}")
    else:
        print("❌ smart_batch_runner.py不包含STORAGE_FORMAT相关代码")

def test_with_parquet():
    """使用Parquet格式运行实际测试"""
    print("\n" + "="*60)
    print("4. 使用Parquet格式运行实际测试")
    print("="*60)
    
    # 检查Parquet文件状态
    parquet_file = Path("pilot_bench_parquet_data/test_results.parquet")
    before_size = 0
    before_time = None
    
    if parquet_file.exists():
        before_size = parquet_file.stat().st_size
        before_time = parquet_file.stat().st_mtime
        print(f"测试前 Parquet文件大小: {before_size} bytes")
        print(f"测试前 修改时间: {datetime.fromtimestamp(before_time)}")
    else:
        print("Parquet文件不存在")
    
    # 运行测试
    print("\n运行测试（STORAGE_FORMAT=parquet）...")
    result = subprocess.run([
        'env', 'STORAGE_FORMAT=parquet',
        'python', 'smart_batch_runner.py',
        '--model', 'gpt-4o-mini',
        '--prompt-types', 'optimal',  # 使用不同的prompt type
        '--difficulty', 'easy',
        '--task-types', 'simple_task',
        '--num-instances', '1',
        '--tool-success-rate', '0.8',
        '--max-workers', '1',
        '--no-adaptive',
        '--qps', '5',
        '--no-save-logs'
    ], capture_output=True, text=True, timeout=60)
    
    print(f"退出码: {result.returncode}")
    
    # 查找输出中的存储格式信息
    if "parquet" in result.stdout.lower() or "parquet" in result.stderr.lower():
        print("✅ 输出中提到了Parquet")
    else:
        print("⚠️ 输出中未提到Parquet")
    
    # 检查文件是否更新
    if parquet_file.exists():
        after_size = parquet_file.stat().st_size
        after_time = parquet_file.stat().st_mtime
        
        if after_time > before_time:
            print(f"✅ Parquet文件已更新！")
            print(f"   新大小: {after_size} bytes (增加 {after_size - before_size} bytes)")
            print(f"   新时间: {datetime.fromtimestamp(after_time)}")
        else:
            print("❌ Parquet文件未更新")
    else:
        print("❌ Parquet文件仍不存在")

def check_cumulative_manager_choice():
    """检查如何选择CumulativeManager"""
    print("\n" + "="*60)
    print("5. 检查Manager选择逻辑")
    print("="*60)
    
    # 查找manager选择逻辑
    files_to_check = [
        "smart_batch_runner.py",
        "batch_test_runner.py",
        "enhanced_cumulative_manager.py"
    ]
    
    for file in files_to_check:
        if Path(file).exists():
            with open(file, "r") as f:
                content = f.read()
            
            if "ParquetCumulativeManager" in content:
                print(f"✅ {file} 包含ParquetCumulativeManager")
                
                # 找出具体的导入和使用逻辑
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if 'ParquetCumulativeManager' in line:
                        print(f"  Line {i+1}: {line.strip()[:100]}")
            else:
                print(f"❌ {file} 不包含ParquetCumulativeManager")

def main():
    """主函数"""
    print("🔬 调试Parquet存储问题")
    print(f"时间: {datetime.now()}")
    print()
    
    check_environment()
    check_parquet_manager()
    check_smart_batch_runner()
    test_with_parquet()
    check_cumulative_manager_choice()
    
    print("\n" + "="*60)
    print("分析完成")
    print("="*60)
    
    print("\n📝 问题分析：")
    print("1. 如果STORAGE_FORMAT环境变量传递正确但Parquet不更新，")
    print("   可能是代码没有正确选择ParquetCumulativeManager")
    print("2. 需要检查enhanced_cumulative_manager.py是否正确处理parquet格式")
    print("3. 可能需要在smart_batch_runner.py中添加Parquet支持")

if __name__ == "__main__":
    main()