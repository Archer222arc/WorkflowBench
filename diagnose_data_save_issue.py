#!/usr/bin/env python3
"""
诊断数据保存问题
"""

import sys
import os
import json
import traceback
from pathlib import Path
from datetime import datetime

def test_direct_manager():
    """直接测试manager的数据保存"""
    print("="*60)
    print("测试1: 直接调用CumulativeTestManager")
    print("="*60)
    
    try:
        # 导入manager
        from cumulative_test_manager import CumulativeTestManager, TestRecord
        
        # 创建manager实例
        manager = CumulativeTestManager()
        
        # 获取初始状态
        db_path = Path("pilot_bench_cumulative_results/master_database.json")
        with open(db_path) as f:
            db_before = json.load(f)
        before_total = db_before['summary'].get('total_tests', 0)
        print(f"测试前: total_tests = {before_total}")
        
        # 创建测试记录
        record = TestRecord(
            model="test-model-direct",
            task_type="simple_task",
            prompt_type="baseline",
            difficulty="easy",
            tool_success_rate=0.8,
            success=True,
            execution_time=2.5,
            turns=5,
            tool_calls=3
        )
        
        print(f"\n添加测试记录: {record.model}")
        
        # 添加记录
        success = manager.add_test_result_with_classification(record)
        print(f"add_test_result_with_classification返回: {success}")
        
        # 手动刷新
        manager.finalize()
        print("调用finalize()完成")
        
        # 检查结果
        with open(db_path) as f:
            db_after = json.load(f)
        after_total = db_after['summary'].get('total_tests', 0)
        print(f"\n测试后: total_tests = {after_total}")
        
        if after_total > before_total:
            print(f"✅ 数据已保存! 新增 {after_total - before_total} 个测试")
        else:
            print("❌ 数据未保存!")
            
            # 检查test-model-direct是否在数据库中
            if 'test-model-direct' in db_after.get('models', {}):
                print("  但test-model-direct已添加到models中")
                model_data = db_after['models']['test-model-direct']
                print(f"  total_tests: {model_data.get('total_tests', 0)}")
                
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        traceback.print_exc()

def test_v2_models_issue():
    """测试v2_models的问题"""
    print("\n" + "="*60)
    print("测试2: 检查v2_models问题")
    print("="*60)
    
    try:
        from cumulative_test_manager import CumulativeTestManager, TestRecord
        
        manager = CumulativeTestManager()
        
        # 创建测试记录
        record = TestRecord(
            model="test-v2-issue",
            task_type="simple_task", 
            prompt_type="baseline",
            difficulty="easy",
            tool_success_rate=0.8,
            success=True
        )
        
        print(f"模型名: {record.model}")
        print(f"v2_models类型: {type(manager.v2_models)}")
        
        # 检查v2_models中的对象
        if record.model not in manager.v2_models:
            manager.v2_models[record.model] = {}
            print(f"创建v2_models['{record.model}'] = {{}}")
        
        model_obj = manager.v2_models[record.model]
        print(f"v2_models['{record.model}']类型: {type(model_obj)}")
        print(f"是否有update_from_test方法: {hasattr(model_obj, 'update_from_test')}")
        
        if not hasattr(model_obj, 'update_from_test'):
            print("\n❌ 问题找到！")
            print("v2_models[model]是字典，但代码尝试调用.update_from_test()方法")
            print("这就是为什么测试运行了但数据没有保存的原因")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        traceback.print_exc()

def test_enhanced_manager():
    """测试EnhancedCumulativeManager"""
    print("\n" + "="*60)
    print("测试3: EnhancedCumulativeManager")
    print("="*60)
    
    try:
        from enhanced_cumulative_manager import EnhancedCumulativeManager
        from cumulative_test_manager import TestRecord
        
        manager = EnhancedCumulativeManager()
        
        # 获取初始状态
        db_path = Path("pilot_bench_cumulative_results/master_database.json")
        with open(db_path) as f:
            db_before = json.load(f)
        before_total = db_before['summary'].get('total_tests', 0)
        print(f"测试前: total_tests = {before_total}")
        
        # 创建测试记录
        record = TestRecord(
            model="test-enhanced",
            task_type="simple_task",
            prompt_type="baseline",
            difficulty="easy",
            tool_success_rate=0.8,
            success=True,
            execution_time=2.5,
            turns=5,
            tool_calls=3
        )
        
        print(f"\n添加测试记录: {record.model}")
        
        # 添加记录
        success = manager.add_test_result_with_classification(record)
        print(f"add_test_result_with_classification返回: {success}")
        
        # 手动刷新
        if hasattr(manager, '_flush_buffer'):
            manager._flush_buffer()
            print("调用_flush_buffer()完成")
        
        # 检查结果
        with open(db_path) as f:
            db_after = json.load(f)
        after_total = db_after['summary'].get('total_tests', 0)
        print(f"\n测试后: total_tests = {after_total}")
        
        if after_total > before_total:
            print(f"✅ 数据已保存! 新增 {after_total - before_total} 个测试")
        else:
            print("❌ 数据未保存!")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        traceback.print_exc()

def main():
    """主函数"""
    print("📊 诊断数据保存问题")
    print(f"时间: {datetime.now()}")
    print(f"STORAGE_FORMAT: {os.environ.get('STORAGE_FORMAT', 'json')}")
    
    # 运行测试
    test_direct_manager()
    test_v2_models_issue()
    test_enhanced_manager()
    
    print("\n" + "="*60)
    print("诊断完成")
    print("="*60)

if __name__ == "__main__":
    main()