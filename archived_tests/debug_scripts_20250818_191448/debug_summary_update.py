#!/usr/bin/env python3
"""
深入调试统计汇总更新问题
追踪为什么total_tests不更新
"""

import json
import traceback
from pathlib import Path
from datetime import datetime

def analyze_database_structure():
    """分析数据库结构"""
    print("="*60)
    print("1. 分析数据库结构")
    print("="*60)
    
    db_path = Path("pilot_bench_cumulative_results/master_database.json")
    with open(db_path) as f:
        db = json.load(f)
    
    print(f"Database version: {db.get('version')}")
    print(f"Summary total_tests: {db['summary']['total_tests']}")
    
    # 计算实际的测试总数
    actual_total = 0
    model_details = {}
    
    for model_name, model_data in db.get('models', {}).items():
        model_total = 0
        
        # 检查顶层的total_tests
        if 'total_tests' in model_data:
            print(f"\n{model_name} 顶层 total_tests: {model_data['total_tests']}")
        
        # 遍历层次结构计算实际测试数
        if 'by_prompt_type' in model_data:
            for pt_name, pt_data in model_data['by_prompt_type'].items():
                if 'by_tool_success_rate' in pt_data:
                    for rate, rate_data in pt_data['by_tool_success_rate'].items():
                        if 'by_difficulty' in rate_data:
                            for diff, diff_data in rate_data['by_difficulty'].items():
                                if 'by_task_type' in diff_data:
                                    for task, task_data in diff_data['by_task_type'].items():
                                        total = task_data.get('total', 0)
                                        if total > 0:
                                            model_total += total
                                            actual_total += total
                                            print(f"  {pt_name}/{rate}/{diff}/{task}: {total} tests")
        
        if model_total > 0:
            model_details[model_name] = model_total
    
    print(f"\n实际测试总数（从层次结构计算）: {actual_total}")
    print(f"Summary中的total_tests: {db['summary']['total_tests']}")
    print(f"差异: {actual_total - db['summary']['total_tests']}")
    
    return db, actual_total

def test_update_global_summary():
    """测试_update_global_summary_v2函数"""
    print("\n" + "="*60)
    print("2. 测试_update_global_summary_v2函数")
    print("="*60)
    
    from cumulative_test_manager import CumulativeTestManager
    
    manager = CumulativeTestManager()
    
    # 获取当前数据库状态
    print(f"调用前 total_tests: {manager.database['summary']['total_tests']}")
    
    # 调用更新函数
    try:
        manager._update_global_summary_v2()
        print(f"调用后 total_tests: {manager.database['summary']['total_tests']}")
        
        # 保存并重新加载
        manager.save_database()
        
        # 重新读取验证
        db_path = Path("pilot_bench_cumulative_results/master_database.json")
        with open(db_path) as f:
            db_after = json.load(f)
        
        print(f"保存后 total_tests: {db_after['summary']['total_tests']}")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        traceback.print_exc()

def check_update_logic():
    """检查更新逻辑的具体实现"""
    print("\n" + "="*60)
    print("3. 检查_update_global_summary_v2的实现")
    print("="*60)
    
    # 读取cumulative_test_manager.py的源码
    with open("cumulative_test_manager.py", "r") as f:
        content = f.read()
    
    # 查找_update_global_summary_v2函数
    import re
    pattern = r'def _update_global_summary_v2\(self\):.*?(?=\n    def |\nclass |\Z)'
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        func_code = match.group()
        print("找到_update_global_summary_v2函数")
        
        # 分析关键逻辑
        if "if False:" in func_code:
            print("❌ 发现 'if False:' 条件！统计永远不会更新")
        
        if "total_tests = 0" in func_code:
            print("⚠️ 发现 total_tests 初始化为0")
        
        # 检查是否正确累加
        if "total_tests +=" in func_code:
            print("✅ 发现 total_tests 累加逻辑")
        else:
            print("❌ 未发现 total_tests 累加逻辑")
        
        # 显示关键代码片段
        print("\n关键代码片段：")
        lines = func_code.split('\n')
        for i, line in enumerate(lines):
            if 'total_tests' in line or 'if False' in line:
                start = max(0, i-2)
                end = min(len(lines), i+3)
                for j in range(start, end):
                    if j == i:
                        print(f">>> {lines[j]}")
                    else:
                        print(f"    {lines[j]}")
                print()

def test_enhanced_manager():
    """测试EnhancedCumulativeManager"""
    print("\n" + "="*60)
    print("4. 测试EnhancedCumulativeManager")
    print("="*60)
    
    from enhanced_cumulative_manager import EnhancedCumulativeManager
    
    manager = EnhancedCumulativeManager()
    
    print(f"调用前 total_tests: {manager.database['summary']['total_tests']}")
    
    # 尝试手动调用重新计算
    try:
        manager._recalculate_total_tests()
        print(f"_recalculate_total_tests后: {manager.database['summary']['total_tests']}")
    except Exception as e:
        print(f"_recalculate_total_tests错误: {e}")
    
    # 尝试刷新缓冲区
    try:
        if hasattr(manager, '_flush_buffer'):
            manager._flush_buffer()
            print(f"_flush_buffer后: {manager.database['summary']['total_tests']}")
    except Exception as e:
        print(f"_flush_buffer错误: {e}")

def trace_save_flow():
    """追踪完整的保存流程"""
    print("\n" + "="*60)
    print("5. 追踪完整的保存流程")
    print("="*60)
    
    from enhanced_cumulative_manager import EnhancedCumulativeManager
    from cumulative_test_manager import TestRecord
    
    # 创建manager
    manager = EnhancedCumulativeManager()
    
    # 记录初始状态
    db_path = Path("pilot_bench_cumulative_results/master_database.json")
    with open(db_path) as f:
        db_before = json.load(f)
    before_total = db_before['summary']['total_tests']
    
    print(f"初始 total_tests: {before_total}")
    
    # 创建测试记录
    record = TestRecord(
        model="debug-trace-model",
        task_type="simple_task",
        prompt_type="baseline",
        difficulty="easy",
        tool_reliability=0.8,
        success=True,
        execution_time=2.5,
        turns=5,
        tool_calls=3
    )
    
    # 添加记录
    print("\n添加测试记录...")
    result = manager.add_test_result_with_classification(record)
    print(f"add_test_result_with_classification返回: {result}")
    
    # 检查内存中的状态
    print(f"内存中 total_tests: {manager.database['summary']['total_tests']}")
    
    # 手动刷新
    print("\n手动刷新缓冲区...")
    if hasattr(manager, '_flush_buffer'):
        manager._flush_buffer()
    
    print(f"刷新后 total_tests: {manager.database['summary']['total_tests']}")
    
    # 手动保存
    print("\n手动保存数据库...")
    manager.save_database()
    
    # 重新读取
    with open(db_path) as f:
        db_after = json.load(f)
    after_total = db_after['summary']['total_tests']
    
    print(f"保存后 total_tests: {after_total}")
    
    if after_total > before_total:
        print(f"✅ total_tests增加了 {after_total - before_total}")
    else:
        print("❌ total_tests没有增加")
        
        # 检查模型数据
        if 'debug-trace-model' in db_after['models']:
            model = db_after['models']['debug-trace-model']
            print(f"但debug-trace-model存在，total_tests: {model.get('total_tests', 0)}")

def check_calculation_logic():
    """检查统计计算的具体逻辑"""
    print("\n" + "="*60)
    print("6. 分析统计计算逻辑")
    print("="*60)
    
    # 手动实现正确的统计逻辑
    db_path = Path("pilot_bench_cumulative_results/master_database.json")
    with open(db_path) as f:
        db = json.load(f)
    
    # 方法1: 从test_groups计算
    test_groups_total = 0
    for group_data in db.get('test_groups', {}).values():
        test_groups_total += group_data.get('total_tests', 0)
    
    print(f"从test_groups计算的总数: {test_groups_total}")
    
    # 方法2: 从models的顶层total_tests计算
    models_top_total = 0
    for model_data in db.get('models', {}).values():
        models_top_total += model_data.get('total_tests', 0)
    
    print(f"从models顶层total_tests计算的总数: {models_top_total}")
    
    # 方法3: 从层次结构计算
    hierarchy_total = 0
    for model_data in db.get('models', {}).values():
        if 'by_prompt_type' in model_data:
            for pt_data in model_data['by_prompt_type'].values():
                if 'by_tool_success_rate' in pt_data:
                    for rate_data in pt_data['by_tool_success_rate'].values():
                        if 'by_difficulty' in rate_data:
                            for diff_data in rate_data['by_difficulty'].values():
                                if 'by_task_type' in diff_data:
                                    for task_data in diff_data['by_task_type'].values():
                                        hierarchy_total += task_data.get('total', 0)
    
    print(f"从层次结构计算的总数: {hierarchy_total}")
    
    print(f"\nsummary中的total_tests: {db['summary']['total_tests']}")
    
    # 建议正确的值
    correct_total = max(test_groups_total, models_top_total, hierarchy_total)
    print(f"\n建议的正确值: {correct_total}")
    
    if correct_total != db['summary']['total_tests']:
        print(f"需要修正: {db['summary']['total_tests']} -> {correct_total}")

def main():
    """主函数"""
    print("🔬 深入调试统计汇总更新问题")
    print(f"时间: {datetime.now()}")
    print()
    
    # 执行各项分析
    db, actual_total = analyze_database_structure()
    test_update_global_summary()
    check_update_logic()
    test_enhanced_manager()
    trace_save_flow()
    check_calculation_logic()
    
    print("\n" + "="*60)
    print("分析完成")
    print("="*60)
    
    # 提供修复建议
    print("\n📝 修复建议：")
    print("1. 检查_update_global_summary_v2是否有'if False:'等跳过逻辑")
    print("2. 确保统计时包含所有模型数据")
    print("3. 验证save_database()是否正确调用了统计更新")
    print(f"4. 手动修正total_tests为: {actual_total}")

if __name__ == "__main__":
    main()