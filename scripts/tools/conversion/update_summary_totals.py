#!/usr/bin/env python3
"""
更新数据库中的summary总计数
"""

import json
from pathlib import Path
from datetime import datetime

def calculate_totals(db):
    """计算实际的总测试数"""
    total_tests = 0
    total_success = 0
    total_partial = 0
    total_failure = 0
    models_tested = set()
    
    if 'models' in db:
        for model_name, model_data in db['models'].items():
            models_tested.add(model_name)
            
            if 'by_prompt_type' in model_data:
                for prompt_type, pt_data in model_data['by_prompt_type'].items():
                    if 'by_tool_success_rate' in pt_data:
                        for rate, rate_data in pt_data['by_tool_success_rate'].items():
                            if 'by_difficulty' in rate_data:
                                for diff, diff_data in rate_data['by_difficulty'].items():
                                    if 'by_task_type' in diff_data:
                                        for task, task_data in diff_data['by_task_type'].items():
                                            total = task_data.get('total', 0)
                                            successful = task_data.get('successful', 0)
                                            partial = task_data.get('partial', 0)
                                            failed = task_data.get('failed', 0)
                                            
                                            total_tests += total
                                            total_success += successful
                                            total_partial += partial
                                            total_failure += failed
    
    return {
        'total_tests': total_tests,
        'total_success': total_success,
        'total_partial': total_partial,
        'total_failure': total_failure,
        'models_tested': sorted(list(models_tested))
    }

def main():
    """主函数"""
    db_path = Path("pilot_bench_cumulative_results/master_database.json")
    
    if not db_path.exists():
        print("❌ 数据库不存在")
        return 1
    
    # 加载数据库
    with open(db_path, 'r') as f:
        db = json.load(f)
    
    print("当前summary:")
    print(f"  total_tests: {db['summary']['total_tests']}")
    print(f"  total_success: {db['summary']['total_success']}")
    print(f"  total_partial: {db['summary']['total_partial']}")
    print(f"  total_failure: {db['summary']['total_failure']}")
    print(f"  models_tested: {len(db['summary'].get('models_tested', []))}")
    
    # 计算实际总数
    actual_totals = calculate_totals(db)
    
    print("\n实际统计:")
    print(f"  total_tests: {actual_totals['total_tests']}")
    print(f"  total_success: {actual_totals['total_success']}")
    print(f"  total_partial: {actual_totals['total_partial']}")
    print(f"  total_failure: {actual_totals['total_failure']}")
    print(f"  models_tested: {len(actual_totals['models_tested'])}")
    
    # 更新summary
    db['summary']['total_tests'] = actual_totals['total_tests']
    db['summary']['total_success'] = actual_totals['total_success']
    db['summary']['total_partial'] = actual_totals['total_partial']
    db['summary']['total_failure'] = actual_totals['total_failure']
    db['summary']['models_tested'] = actual_totals['models_tested']
    db['summary']['last_test_time'] = datetime.now().isoformat()
    
    # 保存更新后的数据库
    with open(db_path, 'w') as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
    
    print("\n✅ Summary已更新")
    
    # 显示差异
    diff = actual_totals['total_tests'] - db['summary'].get('total_tests', 0)
    if diff != 0:
        print(f"📊 测试数变化: {'+' if diff > 0 else ''}{diff}")
    
    return 0

if __name__ == "__main__":
    exit(main())