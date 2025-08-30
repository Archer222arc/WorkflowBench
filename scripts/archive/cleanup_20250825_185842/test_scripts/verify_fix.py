#!/usr/bin/env python3
"""
验证数据保存修复
"""

import os
import json
from pathlib import Path
from datetime import datetime

def test_data_save():
    """测试数据保存功能"""
    print("="*60)
    print("验证数据保存修复")
    print("="*60)
    
    # 记录测试前状态
    db_path = Path("pilot_bench_cumulative_results/master_database.json")
    with open(db_path) as f:
        db_before = json.load(f)
    before_total = db_before['summary'].get('total_tests', 0)
    print(f"测试前: total_tests = {before_total}")
    
    # 导入修复后的manager
    from cumulative_test_manager import CumulativeTestManager, TestRecord
    
    manager = CumulativeTestManager()
    
    # 创建测试记录（使用正确的参数名）
    record = TestRecord(
        model="test-fix-verify",
        task_type="simple_task",
        prompt_type="baseline",
        difficulty="easy",
        tool_reliability=0.8,  # 使用正确的参数名
        success=True,
        execution_time=2.5,
        turns=5,
        tool_calls=3
    )
    
    print(f"\n添加测试记录: {record.model}")
    
    # 添加记录
    try:
        success = manager.add_test_result_with_classification(record)
        print(f"add_test_result_with_classification返回: {success}")
    except AttributeError as e:
        print(f"❌ AttributeError: {e}")
        # 如果方法不存在，使用基础方法
        success = manager.add_test_result(record)
        print(f"add_test_result返回: {success}")
    
    # 手动保存
    manager.save_database()
    print("调用save_database()完成")
    
    # 检查结果
    with open(db_path) as f:
        db_after = json.load(f)
    after_total = db_after['summary'].get('total_tests', 0)
    print(f"\n测试后: total_tests = {after_total}")
    
    if after_total > before_total:
        print(f"✅ 数据已保存! 新增 {after_total - before_total} 个测试")
        return True
    else:
        print("❌ 数据未保存!")
        
        # 检查模型是否在数据库中
        if 'test-fix-verify' in db_after.get('models', {}):
            print("  但test-fix-verify已添加到models中")
            model_data = db_after['models']['test-fix-verify']
            print(f"  model_data类型: {type(model_data)}")
            if isinstance(model_data, dict):
                print(f"  total_tests: {model_data.get('total_tests', 0)}")
        
        return False

def test_flawed_prompt():
    """测试flawed prompt保存"""
    print("\n" + "="*60)
    print("测试flawed prompt数据保存")
    print("="*60)
    
    # 记录前状态
    db_path = Path("pilot_bench_cumulative_results/master_database.json")
    with open(db_path) as f:
        db_before = json.load(f)
    
    # 运行测试
    import subprocess
    result = subprocess.run([
        'python', 'smart_batch_runner.py',
        '--model', 'gpt-4o-mini',
        '--prompt-types', 'flawed_redundant_steps',
        '--difficulty', 'easy',
        '--task-types', 'simple_task',
        '--num-instances', '1',
        '--tool-success-rate', '0.8',
        '--max-workers', '5',
        '--no-adaptive',
        '--qps', '5',
        '--batch-commit',
        '--checkpoint-interval', '1',
        '--no-save-logs',
        '--silent'
    ], capture_output=True, text=True, timeout=60)
    
    if result.returncode == 0:
        print("✅ 测试运行成功")
    else:
        print(f"❌ 测试运行失败 (退出码: {result.returncode})")
        if result.stderr:
            print(f"错误: {result.stderr[-500:]}")
    
    # 检查结果
    with open(db_path) as f:
        db_after = json.load(f)
    
    after_total = db_after['summary'].get('total_tests', 0)
    before_total = db_before['summary'].get('total_tests', 0)
    
    if after_total > before_total:
        print(f"✅ 数据已保存! 新增 {after_total - before_total} 个测试")
        
        # 检查flawed数据
        if 'gpt-4o-mini' in db_after['models']:
            model_data = db_after['models']['gpt-4o-mini']
            if 'by_prompt_type' in model_data:
                flawed_types = [k for k in model_data['by_prompt_type'].keys() if 'flawed' in k]
                if flawed_types:
                    print(f"\nflawed prompt类型:")
                    for ft in flawed_types:
                        data = model_data['by_prompt_type'][ft]
                        total = data.get('total_tests', 0)
                        if total > 0:
                            print(f"  ✅ {ft}: {total} tests")
                        else:
                            print(f"  ⚠️ {ft}: 0 tests (键存在但无数据)")
        return True
    else:
        print("❌ 数据未更新!")
        return False

def main():
    """主函数"""
    print("🔧 验证数据保存修复")
    print(f"时间: {datetime.now()}")
    print(f"STORAGE_FORMAT: {os.environ.get('STORAGE_FORMAT', 'json')}")
    
    # 测试1：基础功能
    test1_success = test_data_save()
    
    # 测试2：flawed prompt
    test2_success = test_flawed_prompt()
    
    print("\n" + "="*60)
    print("验证结果汇总")
    print("="*60)
    print(f"基础保存测试: {'✅ 通过' if test1_success else '❌ 失败'}")
    print(f"Flawed测试: {'✅ 通过' if test2_success else '❌ 失败'}")
    
    if test1_success and test2_success:
        print("\n🎉 所有测试通过！数据保存功能已修复。")
    else:
        print("\n⚠️ 部分测试失败，需要进一步调查。")

if __name__ == "__main__":
    main()