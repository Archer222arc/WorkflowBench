#!/usr/bin/env python3
"""
深入分析数据保存流程
追踪从测试执行到数据保存的完整路径
"""

import sys
import os
import json
import traceback
from pathlib import Path
from datetime import datetime

def trace_data_flow():
    """追踪数据流"""
    print("="*60)
    print("🔍 追踪数据流")
    print("="*60)
    
    # 1. 检查当前数据库状态
    print("\n1. 当前数据库状态")
    db_path = Path("pilot_bench_cumulative_results/master_database.json")
    with open(db_path) as f:
        db = json.load(f)
    
    print(f"   Version: {db.get('version')}")
    print(f"   Total tests: {db['summary']['total_tests']}")
    print(f"   Models count: {len(db.get('models', {}))}")
    
    # 检查models结构
    for model_name in list(db.get('models', {}).keys())[:3]:
        model_data = db['models'][model_name]
        print(f"\n   {model_name}:")
        print(f"     Type: {type(model_data)}")
        if isinstance(model_data, dict):
            print(f"     Keys: {list(model_data.keys())[:5]}")
            print(f"     total_tests: {model_data.get('total_tests', 'N/A')}")
            if 'overall_stats' in model_data:
                print(f"     overall_stats keys: {list(model_data['overall_stats'].keys())[:3]}")

def test_add_test_result():
    """测试add_test_result方法"""
    print("\n" + "="*60)
    print("2. 测试add_test_result方法")
    print("="*60)
    
    from cumulative_test_manager import CumulativeTestManager, TestRecord
    
    manager = CumulativeTestManager()
    
    # 创建测试记录
    record = TestRecord(
        model="debug-test-model",
        task_type="simple_task",
        prompt_type="baseline",
        difficulty="easy",
        success=True,
        execution_time=2.5,
        turns=5
    )
    
    print(f"\n添加测试记录: {record.model}")
    
    # 调用add_test_result
    try:
        result = manager.add_test_result(record)
        print(f"✅ add_test_result返回: {result}")
        
        # 检查内存中的数据
        if "debug-test-model" in manager.database["models"]:
            model_data = manager.database["models"]["debug-test-model"]
            print(f"\n内存中的模型数据:")
            print(f"  Type: {type(model_data)}")
            print(f"  total_tests: {model_data.get('total_tests', 'N/A')}")
            
            # 检查test_groups
            key = record.get_key()
            if key in manager.database.get("test_groups", {}):
                group = manager.database["test_groups"][key]
                print(f"\ntest_group统计:")
                print(f"  total: {group['statistics']['total']}")
                print(f"  success: {group['statistics']['success']}")
        else:
            print("❌ 模型未添加到内存数据库")
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        traceback.print_exc()
    
    # 检查磁盘上的数据
    print("\n检查磁盘数据...")
    db_path = Path("pilot_bench_cumulative_results/master_database.json")
    with open(db_path) as f:
        db_after = json.load(f)
    
    if "debug-test-model" in db_after["models"]:
        print("✅ 模型已保存到磁盘")
        model_data = db_after["models"]["debug-test-model"]
        print(f"  total_tests: {model_data.get('total_tests', 'N/A')}")
    else:
        print("❌ 模型未保存到磁盘")

def test_enhanced_manager():
    """测试EnhancedCumulativeManager"""
    print("\n" + "="*60)
    print("3. 测试EnhancedCumulativeManager")
    print("="*60)
    
    try:
        from enhanced_cumulative_manager import EnhancedCumulativeManager
        from cumulative_test_manager import TestRecord
        
        print("\n创建EnhancedCumulativeManager...")
        manager = EnhancedCumulativeManager()
        
        # 创建测试记录
        record = TestRecord(
            model="enhanced-test-model",
            task_type="simple_task",
            prompt_type="baseline",
            difficulty="easy",
            success=True,
            execution_time=2.5,
            turns=5,
            tool_calls=3
        )
        record.tool_reliability = 0.8  # 设置正确的属性
        
        print(f"添加测试记录: {record.model}")
        
        # 添加记录
        result = manager.add_test_result_with_classification(record)
        print(f"add_test_result_with_classification返回: {result}")
        
        # 检查update_buffer
        print(f"\nBuffer大小: {len(manager.update_buffer)}")
        
        # 手动刷新
        if manager.update_buffer:
            print("手动刷新buffer...")
            manager._flush_buffer()
        
        # 检查内存数据
        if "enhanced-test-model" in manager.database["models"]:
            print("✅ 模型在内存数据库中")
        else:
            print("❌ 模型不在内存数据库中")
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        traceback.print_exc()

def analyze_smart_batch_runner():
    """分析smart_batch_runner的调用链"""
    print("\n" + "="*60)
    print("4. 分析smart_batch_runner调用链")
    print("="*60)
    
    print("\n调用链分析:")
    print("1. smart_batch_runner.py")
    print("   └─> commit_to_database()")
    print("       └─> enhanced_manager.add_test_result_with_classification()")
    print("           ├─> 添加到update_buffer")
    print("           └─> 如果buffer满，调用_flush_buffer()")
    print("               ├─> 调用parent的add_test_result()")
    print("               ├─> _update_error_metrics()")
    print("               ├─> _recalculate_total_tests()")
    print("               └─> save_database()")
    
    # 检查smart_batch_runner中的commit_to_database
    print("\n检查commit_to_database函数...")
    try:
        with open("smart_batch_runner.py", "r") as f:
            content = f.read()
            
        # 查找commit_to_database函数
        if "def commit_to_database" in content:
            print("✅ 找到commit_to_database函数")
            
            # 检查是否调用了_flush_buffer
            if "_flush_buffer()" in content:
                print("✅ 调用了_flush_buffer()")
            else:
                print("⚠️ 未找到_flush_buffer()调用")
                
            # 检查是否有finalize调用
            if ".finalize()" in content:
                print("✅ 调用了finalize()")
            else:
                print("⚠️ 未找到finalize()调用")
                
    except Exception as e:
        print(f"❌ 无法分析: {e}")

def check_buffer_settings():
    """检查buffer设置"""
    print("\n" + "="*60)
    print("5. 检查Buffer设置")
    print("="*60)
    
    from enhanced_cumulative_manager import EnhancedCumulativeManager
    
    manager = EnhancedCumulativeManager()
    
    print(f"Buffer大小设置: {manager.buffer_size}")
    print(f"Flush间隔: {manager.flush_interval}秒")
    
    # 测试buffer是否会自动刷新
    print("\n测试Buffer刷新...")
    from cumulative_test_manager import TestRecord
    
    for i in range(manager.buffer_size + 1):
        record = TestRecord(
            model=f"buffer-test-{i}",
            task_type="simple_task",
            prompt_type="baseline",
            difficulty="easy",
            success=True
        )
        record.tool_reliability = 0.8
        
        print(f"  添加记录 {i+1}/{manager.buffer_size + 1}")
        manager.add_test_result_with_classification(record)
        
        if i == manager.buffer_size - 1:
            print(f"  Buffer应该满了 (大小={len(manager.update_buffer)})")
            if len(manager.update_buffer) == 0:
                print("  ✅ Buffer已自动刷新")
            else:
                print(f"  ❌ Buffer未刷新，仍有{len(manager.update_buffer)}条记录")

def test_direct_save():
    """直接测试数据保存"""
    print("\n" + "="*60)
    print("6. 直接测试数据保存")
    print("="*60)
    
    # 创建简单的测试数据
    test_data = {
        "version": "3.0",
        "test_key": "test_value_" + datetime.now().strftime("%H%M%S"),
        "models": {},
        "summary": {
            "total_tests": 9999  # 特殊值用于验证
        }
    }
    
    # 保存到临时文件
    temp_file = Path("pilot_bench_cumulative_results/test_direct_save.json")
    print(f"\n保存测试数据到: {temp_file}")
    
    with open(temp_file, "w") as f:
        json.dump(test_data, f, indent=2)
    
    # 验证保存
    with open(temp_file) as f:
        loaded = json.load(f)
    
    if loaded["test_key"] == test_data["test_key"]:
        print("✅ 直接保存成功")
    else:
        print("❌ 直接保存失败")
    
    # 清理
    temp_file.unlink()

def main():
    """主函数"""
    print("🔬 深入分析数据保存问题")
    print(f"时间: {datetime.now()}")
    print(f"Python版本: {sys.version}")
    print(f"工作目录: {os.getcwd()}")
    
    # 运行各项测试
    trace_data_flow()
    test_add_test_result()
    test_enhanced_manager()
    analyze_smart_batch_runner()
    check_buffer_settings()
    test_direct_save()
    
    print("\n" + "="*60)
    print("分析完成")
    print("="*60)

if __name__ == "__main__":
    main()