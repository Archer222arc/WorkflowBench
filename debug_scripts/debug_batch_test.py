#!/usr/bin/env python3
"""
调试批量测试问题
"""
import json
import time
from pathlib import Path
from batch_test_runner import BatchTestRunner
from cumulative_test_manager import CumulativeTestManager

def main():
    print("=" * 80)
    print("批量测试调试")
    print("=" * 80)
    
    # 1. 检查数据库状态
    db_path = Path("pilot_bench_cumulative_results/master_database.json")
    print(f"\n1. 检查数据库文件: {db_path}")
    if db_path.exists():
        with open(db_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            total_tests = data['summary']['total_tests']
            test_groups = len(data['test_groups'])
            print(f"   - 总测试数: {total_tests}")
            print(f"   - 测试组数: {test_groups}")
            print(f"   - 文件大小: {db_path.stat().st_size / 1024:.1f} KB")
    else:
        print("   - 数据库文件不存在")
    
    # 2. 运行小批量测试（5个）
    print("\n2. 运行小批量测试（5个测试）")
    runner = BatchTestRunner(
        max_workers=2,  # 降低并发数
        debug=True,
        silent=False
    )
    
    # 获取5个测试任务
    tasks = runner.get_smart_tasks(
        model='qwen2.5-3b-instruct',
        count=5,
        difficulty='very_easy',
        tool_success_rate=0.8
    )
    
    print(f"   获得 {len(tasks)} 个测试任务")
    
    # 运行测试
    start_time = time.time()
    print("\n3. 开始执行测试...")
    results = runner.run_tests_concurrent(tasks)
    execution_time = time.time() - start_time
    
    print(f"\n4. 测试执行完成")
    print(f"   - 执行时间: {execution_time:.2f}秒")
    print(f"   - 返回结果数: {len(results)}")
    
    # 统计结果
    success_count = sum(1 for r in results if r.get('success', False))
    print(f"   - 成功数: {success_count}")
    print(f"   - 失败数: {len(results) - success_count}")
    
    # 5. 再次检查数据库
    print(f"\n5. 重新检查数据库")
    if db_path.exists():
        with open(db_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            new_total_tests = data['summary']['total_tests']
            new_test_groups = len(data['test_groups'])
            print(f"   - 新的总测试数: {new_total_tests}")
            print(f"   - 新的测试组数: {new_test_groups}")
            print(f"   - 测试增量: {new_total_tests - total_tests}")
            print(f"   - 文件大小: {db_path.stat().st_size / 1024:.1f} KB")
    
    # 6. 显示测试组详情
    print(f"\n6. 测试组详情:")
    if db_path.exists():
        with open(db_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for group_key in list(data['test_groups'].keys())[:10]:  # 只显示前10个
                group = data['test_groups'][group_key]
                stats = group.get('statistics', {})
                print(f"   - {group_key}: total={stats.get('total', 0)}, "
                      f"success={stats.get('success', 0)}, "
                      f"avg_phase2_score={stats.get('avg_phase2_score', 0):.3f}")
    
    print("\n" + "=" * 80)
    print("调试完成")
    print("=" * 80)

if __name__ == "__main__":
    main()