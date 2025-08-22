#!/usr/bin/env python3
"""验证闭源模型结果存储是否正常"""

import json
from pathlib import Path

def check_storage():
    """检查闭源模型存储配置"""
    
    print("=" * 60)
    print("🔍 闭源模型结果存储验证")
    print("=" * 60)
    
    # 1. 检查数据库文件
    print("\n1. 数据库文件检查：")
    db_dir = Path("pilot_bench_cumulative_results")
    
    # 开源模型数据库
    opensource_db = db_dir / "master_database.json"
    if opensource_db.exists():
        with open(opensource_db, 'r') as f:
            data = json.load(f)
            models = list(data.get('models', {}).keys())
            total_tests = sum(m.get('total_tests', 0) for m in data.get('models', {}).values())
            print(f"   ✅ 开源模型数据库: {opensource_db.name}")
            print(f"      - 模型数: {len(models)}")
            print(f"      - 总测试数: {total_tests}")
            if models:
                print(f"      - 模型列表: {', '.join(models[:5])}...")
    else:
        print(f"   ❌ 开源模型数据库不存在")
    
    # 闭源模型数据库
    closed_db = db_dir / "master_database_closed_source.json"
    if closed_db.exists():
        with open(closed_db, 'r') as f:
            data = json.load(f)
            models = list(data.get('models', {}).keys())
            total_tests = sum(m.get('total_tests', 0) for m in data.get('models', {}).values())
            print(f"   ✅ 闭源模型数据库: {closed_db.name}")
            print(f"      - 模型数: {len(models)}")
            print(f"      - 总测试数: {total_tests}")
            if models:
                print(f"      - 模型列表: {', '.join(models)}")
    else:
        print(f"   ⚠️ 闭源模型数据库不存在（正常，如果还没运行过闭源测试）")
    
    # 2. 检查进度文件
    print("\n2. 进度文件检查：")
    
    # 开源模型进度
    opensource_progress = Path("test_progress_opensource.txt")
    if opensource_progress.exists():
        print(f"   ✅ 开源模型进度文件: {opensource_progress.name}")
        with open(opensource_progress, 'r') as f:
            lines = f.readlines()
            for line in lines[:5]:
                print(f"      {line.strip()}")
    else:
        print(f"   ⚠️ 开源模型进度文件不存在")
    
    # 闭源模型进度
    closed_progress = Path("test_progress_closed_source.txt")
    if closed_progress.exists():
        print(f"   ✅ 闭源模型进度文件: {closed_progress.name}")
        with open(closed_progress, 'r') as f:
            lines = f.readlines()
            for line in lines[:5]:
                print(f"      {line.strip()}")
    else:
        print(f"   ⚠️ 闭源模型进度文件不存在")
    
    # 3. 检查失败测试配置
    print("\n3. 失败测试配置检查：")
    
    # 开源模型失败配置
    opensource_failed = Path("failed_tests_config_opensource.json")
    if opensource_failed.exists():
        with open(opensource_failed, 'r') as f:
            data = json.load(f)
            failed_count = data.get('active_session', {}).get('total_failed_tests', 0)
            print(f"   ✅ 开源模型失败配置: {opensource_failed.name}")
            print(f"      - 失败测试数: {failed_count}")
    else:
        print(f"   ⚠️ 开源模型失败配置不存在")
    
    # 闭源模型失败配置
    closed_failed = Path("failed_tests_config_closed_source.json")
    if closed_failed.exists():
        with open(closed_failed, 'r') as f:
            data = json.load(f)
            failed_count = data.get('active_session', {}).get('total_failed_tests', 0)
            print(f"   ✅ 闭源模型失败配置: {closed_failed.name}")
            print(f"      - 失败测试数: {failed_count}")
    else:
        print(f"   ⚠️ 闭源模型失败配置不存在")
    
    # 4. 测试存储功能
    print("\n4. 存储功能测试：")
    print("   测试 EnhancedCumulativeManager 的 db_suffix 参数...")
    
    try:
        from enhanced_cumulative_manager import EnhancedCumulativeManager
        
        # 测试开源模型存储（默认）
        manager_open = EnhancedCumulativeManager(db_suffix='')
        print(f"   ✅ 开源模型管理器数据库: {manager_open.db_file}")
        
        # 测试闭源模型存储
        manager_closed = EnhancedCumulativeManager(db_suffix='_closed_source')
        print(f"   ✅ 闭源模型管理器数据库: {manager_closed.db_file}")
        
        # 验证是否指向不同文件
        if manager_open.db_file != manager_closed.db_file:
            print(f"   ✅ 数据库正确分离")
        else:
            print(f"   ❌ 错误：两个管理器使用了相同的数据库文件！")
        
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
    
    print("\n" + "=" * 60)
    print("验证完成！")
    print("=" * 60)

if __name__ == "__main__":
    check_storage()