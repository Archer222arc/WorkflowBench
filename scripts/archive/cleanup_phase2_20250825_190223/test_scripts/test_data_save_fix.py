#!/usr/bin/env python3
"""
测试数据保存修复是否有效
"""

from enhanced_cumulative_manager import EnhancedCumulativeManager
from cumulative_test_manager import TestRecord
import json
from pathlib import Path

def test_data_save():
    """测试数据保存逻辑"""
    
    print("测试数据保存修复...")
    print("=" * 60)
    
    # 创建管理器
    manager = EnhancedCumulativeManager()
    
    # 创建测试记录
    test_cases = [
        # 成功的案例
        {"success": True, "expected_counts": {"success": 1, "partial": 0, "failed": 0}},
        # 失败的案例
        {"success": False, "expected_counts": {"success": 0, "partial": 0, "failed": 1}},
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试案例 {i}: success={test_case['success']}")
        
        # 创建测试记录
        record = TestRecord(
            model="test-model",
            task_type="simple_task",
            prompt_type="baseline",
            difficulty="easy"
        )
        record.tool_success_rate = 0.8
        record.success = test_case["success"]
        record.execution_time = 5.0
        record.turns = 10
        record.tool_calls = 3
        
        # 添加记录
        manager.add_test_result_with_classification(record)
        
        # 获取统计数据
        json_path = Path('pilot_bench_cumulative_results/master_database.json')
        with open(json_path, 'r') as f:
            db = json.load(f)
        
        # 检查数据
        if 'test-model' in db['models']:
            model_data = db['models']['test-model']
            task_data = model_data['by_prompt_type']['baseline']['by_tool_success_rate']['0.8']['by_difficulty']['easy']['by_task_type']['simple_task']
            
            print(f"  total: {task_data['total']}")
            print(f"  success: {task_data.get('success', 0)}")
            print(f"  partial: {task_data.get('partial', 0)}")
            print(f"  failed: {task_data.get('failed', 0)}")
            
            # 验证
            actual_sum = task_data.get('success', 0) + task_data.get('partial', 0) + task_data.get('failed', 0)
            if actual_sum == task_data['total']:
                print(f"  ✅ 数据一致: total({task_data['total']}) = success + partial + failed({actual_sum})")
            else:
                print(f"  ❌ 数据不一致: total({task_data['total']}) != success + partial + failed({actual_sum})")
            
            # 检查率的计算
            print(f"  success_rate: {task_data.get('success_rate', 0):.2f}")
            print(f"  partial_rate: {task_data.get('partial_rate', 0):.2f}")
            print(f"  failure_rate: {task_data.get('failure_rate', 0):.2f}")
            
            rate_sum = task_data.get('success_rate', 0) + task_data.get('partial_rate', 0) + task_data.get('failure_rate', 0)
            if abs(rate_sum - 1.0) < 0.01:  # 允许小的浮点误差
                print(f"  ✅ 率的总和正确: {rate_sum:.2f} ≈ 1.0")
            else:
                print(f"  ❌ 率的总和错误: {rate_sum:.2f} != 1.0")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    
    # 清理测试数据
    if 'test-model' in db['models']:
        del db['models']['test-model']
        with open(json_path, 'w') as f:
            json.dump(db, f, indent=2)
        print("已清理测试数据")

if __name__ == "__main__":
    test_data_save()