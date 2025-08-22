#!/usr/bin/env python3
"""
查看累积测试进度
显示详细的测试统计信息
"""

import json
from pathlib import Path
from datetime import datetime
import argparse

def view_progress(target_per_group: int = 100, model_filter: str = None):
    """查看测试进度"""
    results_db = Path("cumulative_test_results/results_database.json")
    
    if not results_db.exists():
        print("暂无测试数据")
        return
    
    with open(results_db, 'r') as f:
        db = json.load(f)
    
    print("="*80)
    print("PILOT-Bench 累积测试进度报告")
    print("="*80)
    print(f"数据库创建时间: {db.get('created_at', 'N/A')}")
    print(f"总测试数: {db.get('total_tests', 0)}")
    print(f"测试模型数: {len(db.get('models', {}))}")
    print(f"测试会话数: {len(db.get('test_sessions', []))}")
    
    # 显示每个模型的详细进度
    models = db.get('models', {})
    
    for model_name, model_data in models.items():
        if model_filter and model_filter not in model_name:
            continue
            
        print(f"\n{'='*80}")
        print(f"模型: {model_name}")
        print(f"{'='*80}")
        print(f"首次测试: {model_data.get('first_tested', 'N/A')}")
        print(f"最后测试: {model_data.get('last_tested', 'N/A')}")
        print(f"总测试数: {model_data.get('total_tests', 0)}")
        
        # 分析结果分布
        results = model_data.get('results', {})
        
        # 按类型分组
        normal_tests = {}
        flawed_tests = {}
        
        for key, tests in results.items():
            if 'flawed' in key:
                flawed_tests[key] = tests
            else:
                normal_tests[key] = tests
        
        # 显示正常测试进度
        if normal_tests:
            print(f"\n正常测试进度 (目标: {target_per_group}/组):")
            print("-" * 70)
            print(f"{'组合':<40} {'完成':<10} {'进度':<15} {'状态'}")
            print("-" * 70)
            
            for key in sorted(normal_tests.keys()):
                tests = normal_tests[key]
                count = len(tests)
                percent = (count / target_per_group * 100) if target_per_group > 0 else 0
                status = "✅ 完成" if count >= target_per_group else f"🔄 进行中"
                
                print(f"{key:<40} {count:>3}/{target_per_group:<3} {percent:>6.1f}% {status}")
            
            # 统计总体进度
            total_normal = sum(len(tests) for tests in normal_tests.values())
            total_groups = len(normal_tests)
            total_target = total_groups * target_per_group
            overall_percent = (total_normal / total_target * 100) if total_target > 0 else 0
            
            print("-" * 70)
            print(f"{'总计':<40} {total_normal:>3}/{total_target:<3} {overall_percent:>6.1f}%")
        
        # 显示缺陷测试进度
        if flawed_tests:
            print(f"\n缺陷测试进度 (目标: {target_per_group}/组):")
            print("-" * 70)
            print(f"{'组合':<40} {'完成':<10} {'进度':<15} {'状态'}")
            print("-" * 70)
            
            for key in sorted(flawed_tests.keys()):
                tests = flawed_tests[key]
                count = len(tests)
                percent = (count / target_per_group * 100) if target_per_group > 0 else 0
                status = "✅ 完成" if count >= target_per_group else f"🔄 进行中"
                
                print(f"{key:<40} {count:>3}/{target_per_group:<3} {percent:>6.1f}% {status}")
        
        # 显示成功率统计
        if results:
            print(f"\n成功率统计:")
            print("-" * 50)
            
            total_success = 0
            total_count = 0
            
            for key, tests in results.items():
                if tests:
                    success_count = sum(1 for t in tests if t.get('success', False))
                    test_count = len(tests)
                    success_rate = (success_count / test_count * 100) if test_count > 0 else 0
                    
                    total_success += success_count
                    total_count += test_count
                    
                    print(f"{key:<40} {success_rate:>5.1f}% ({success_count}/{test_count})")
            
            if total_count > 0:
                overall_success = (total_success / total_count * 100)
                print("-" * 50)
                print(f"{'总体成功率':<40} {overall_success:>5.1f}% ({total_success}/{total_count})")
    
    # 显示最近的测试会话
    sessions = db.get('test_sessions', [])
    if sessions:
        print(f"\n\n最近10个测试会话:")
        print("-" * 80)
        for session in sessions[-10:]:
            timestamp = session['timestamp']
            model = session['model']
            num_tests = session['num_tests']
            session_id = session.get('session_id', 'N/A')
            print(f"{timestamp} | {model:<30} | {num_tests:>3} 个测试 | {session_id}")

def main():
    parser = argparse.ArgumentParser(description='查看累积测试进度')
    parser.add_argument('--target', type=int, default=100,
                       help='每组目标测试数 (默认: 100)')
    parser.add_argument('--model', type=str, default=None,
                       help='筛选特定模型')
    
    args = parser.parse_args()
    
    view_progress(args.target, args.model)

if __name__ == "__main__":
    main()