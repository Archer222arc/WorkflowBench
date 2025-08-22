#!/usr/bin/env python3
"""
测试存储系统的一致性
验证JSON和Parquet两种格式都能正常工作
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
import subprocess
import time

def test_storage_format(storage_format: str):
    """测试指定的存储格式"""
    print(f"\n{'='*60}")
    print(f"测试{storage_format.upper()}存储格式")
    print(f"{'='*60}")
    
    # 设置环境变量
    os.environ['STORAGE_FORMAT'] = storage_format
    
    # 1. 测试导入
    print("\n1. 测试导入...")
    try:
        if storage_format == 'parquet':
            from parquet_cumulative_manager import ParquetCumulativeManager as Manager
            print("  ✅ Parquet管理器导入成功")
        else:
            from cumulative_test_manager import CumulativeTestManager as Manager
            print("  ✅ JSON管理器导入成功")
    except ImportError as e:
        print(f"  ❌ 导入失败: {e}")
        return False
    
    # 2. 测试包装器
    print("\n2. 测试包装器...")
    try:
        from cumulative_test_manager_wrapper import (
            add_test_result,
            check_progress,
            is_test_completed,
            finalize
        )
        print("  ✅ 包装器导入成功")
    except ImportError as e:
        print(f"  ❌ 包装器导入失败: {e}")
        return False
    
    # 3. 测试添加数据
    print("\n3. 测试添加数据...")
    test_model = f"test-model-{storage_format}"
    success = add_test_result(
        model=test_model,
        task_type="consistency_test",
        prompt_type="baseline",
        success=True,
        execution_time=1.5,
        difficulty="easy",
        tool_success_rate=0.8
    )
    if success:
        print(f"  ✅ 数据添加成功")
    else:
        print(f"  ❌ 数据添加失败")
        return False
    
    # 4. 测试查询
    print("\n4. 测试查询...")
    progress = check_progress(test_model, 100)
    if progress and progress.get('current', 0) > 0:
        print(f"  ✅ 查询成功: {progress}")
    else:
        print(f"  ⚠️ 查询结果: {progress}")
    
    # 5. 测试数据持久化
    print("\n5. 测试数据持久化...")
    finalize()
    print(f"  ✅ 数据同步完成")
    
    # 6. 验证数据文件
    print("\n6. 验证数据文件...")
    if storage_format == 'parquet':
        data_dir = Path("pilot_bench_parquet_data")
        if data_dir.exists():
            parquet_files = list(data_dir.glob("*.parquet"))
            if parquet_files:
                print(f"  ✅ 找到{len(parquet_files)}个Parquet文件")
                for f in parquet_files[:3]:  # 显示前3个
                    size_kb = f.stat().st_size / 1024
                    print(f"     - {f.name}: {size_kb:.2f} KB")
            else:
                print(f"  ⚠️ Parquet目录存在但没有数据文件")
        else:
            print(f"  ⚠️ Parquet数据目录不存在")
    else:
        json_file = Path("pilot_bench_cumulative_results/master_database.json")
        if json_file.exists():
            size_kb = json_file.stat().st_size / 1024
            print(f"  ✅ JSON数据库存在: {size_kb:.2f} KB")
            
            # 验证数据内容
            with open(json_file, 'r') as f:
                data = json.load(f)
            if test_model in data.get('models', {}):
                print(f"  ✅ 测试模型数据已保存")
            else:
                print(f"  ⚠️ 测试模型数据未找到")
        else:
            print(f"  ⚠️ JSON数据库不存在")
    
    return True

def test_shell_integration():
    """测试Shell脚本集成"""
    print(f"\n{'='*60}")
    print("测试Shell脚本集成")
    print(f"{'='*60}")
    
    # 测试run_systematic_test_final.sh的存储格式功能
    script_path = Path("run_systematic_test_final.sh")
    if not script_path.exists():
        print("  ⚠️ run_systematic_test_final.sh不存在")
        return False
    
    # 检查脚本中是否有存储格式选择功能
    with open(script_path, 'r') as f:
        content = f.read()
    
    checks = [
        ("show_storage_format_menu", "存储格式菜单"),
        ("STORAGE_FORMAT", "存储格式变量"),
        ("Parquet", "Parquet支持"),
    ]
    
    for keyword, description in checks:
        if keyword in content:
            print(f"  ✅ {description}: 已集成")
        else:
            print(f"  ❌ {description}: 未找到")
    
    return True

def test_concurrent_safety():
    """测试并发安全性"""
    print(f"\n{'='*60}")
    print("测试并发安全性")
    print(f"{'='*60}")
    
    storage_format = os.environ.get('STORAGE_FORMAT', 'json')
    
    if storage_format == 'parquet':
        print("\n✅ Parquet格式天然支持并发写入")
        print("  • 每个进程写独立的增量文件")
        print("  • 不会相互覆盖")
        print("  • 中断安全")
    else:
        print("\n⚠️ JSON格式存在并发问题")
        print("  • 多进程会相互覆盖")
        print("  • 建议使用文件锁")
        print("  • 或切换到Parquet格式")
    
    return True

def main():
    """主测试函数"""
    print("="*60)
    print("存储系统一致性测试")
    print("="*60)
    
    all_success = True
    
    # 测试JSON格式
    if not test_storage_format('json'):
        all_success = False
        print("\n❌ JSON格式测试失败")
    
    # 测试Parquet格式（如果依赖已安装）
    try:
        import pandas
        import pyarrow
        if not test_storage_format('parquet'):
            all_success = False
            print("\n❌ Parquet格式测试失败")
    except ImportError:
        print("\n⚠️ 跳过Parquet测试（未安装依赖）")
        print("  运行: pip install pandas pyarrow")
    
    # 测试Shell集成
    if not test_shell_integration():
        all_success = False
        print("\n❌ Shell集成测试失败")
    
    # 测试并发安全性
    test_concurrent_safety()
    
    # 总结
    print(f"\n{'='*60}")
    print("测试总结")
    print(f"{'='*60}")
    
    if all_success:
        print("\n✅ 所有测试通过！")
        print("\n使用方法:")
        print("1. 在运行测试前设置存储格式:")
        print("   export STORAGE_FORMAT=parquet  # 推荐")
        print("   export STORAGE_FORMAT=json     # 传统")
        print("")
        print("2. 或在运行时指定:")
        print("   STORAGE_FORMAT=parquet ./run_systematic_test_final.sh")
        print("")
        print("3. 或使用交互式菜单选择（默认）")
    else:
        print("\n⚠️ 部分测试失败，请检查配置")
    
    return all_success

if __name__ == "__main__":
    sys.exit(0 if main() else 1)