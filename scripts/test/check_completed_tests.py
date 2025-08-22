#!/usr/bin/env python3
"""
检查已完成的测试，支持细粒度的续测
"""
import json
import os
import sys
from typing import Set, Dict, List

def load_database(db_path="pilot_bench_cumulative_results/master_database.json"):
    """加载测试数据库"""
    if not os.path.exists(db_path):
        return {}
    
    with open(db_path, 'r') as f:
        return json.load(f)

def get_completed_tests(model: str, prompt_type: str, difficulty: str, task_type: str = None) -> Dict:
    """
    获取已完成的测试信息
    返回：{task_type: instance_count}
    """
    db = load_database()
    completed = {}
    
    # 遍历测试组
    test_groups = db.get("test_groups", {})
    
    for group_key, group_data in test_groups.items():
        # 解析group key: model_promptType_difficulty
        parts = group_key.split('_')
        if len(parts) < 3:
            continue
            
        group_model = '_'.join(parts[:-2])  # 处理模型名中的下划线
        group_prompt = parts[-2]
        group_diff = parts[-1]
        
        # 检查是否匹配
        if (group_model == model and 
            group_prompt == prompt_type and 
            group_diff == difficulty):
            
            # 统计每种任务类型的完成数
            for test_record in group_data.get("test_records", []):
                test_task_type = test_record.get("task_type", "unknown")
                
                if task_type is None or task_type == test_task_type:
                    if test_task_type not in completed:
                        completed[test_task_type] = 0
                    completed[test_task_type] += 1
    
    return completed

def check_test_completion(model: str, prompt_type: str, difficulty: str, 
                         task_types: List[str], target_instances: int) -> Dict:
    """
    检查测试完成情况
    返回：{
        "completed": bool,
        "details": {task_type: {"done": n, "remaining": m}},
        "total_done": n,
        "total_remaining": m
    }
    """
    completed_tests = get_completed_tests(model, prompt_type, difficulty)
    
    details = {}
    total_done = 0
    total_remaining = 0
    
    for task_type in task_types:
        done = completed_tests.get(task_type, 0)
        remaining = max(0, target_instances - done)
        
        details[task_type] = {
            "done": done,
            "remaining": remaining,
            "target": target_instances
        }
        
        total_done += done
        total_remaining += remaining
    
    return {
        "completed": total_remaining == 0,
        "details": details,
        "total_done": total_done,
        "total_remaining": total_remaining,
        "total_target": len(task_types) * target_instances
    }

def main():
    """主函数，可以作为命令行工具使用"""
    if len(sys.argv) < 4:
        print("Usage: python check_completed_tests.py <model> <prompt_type> <difficulty> [num_instances]")
        print("Example: python check_completed_tests.py gpt-4o optimal easy 20")
        sys.exit(1)
    
    model = sys.argv[1]
    prompt_type = sys.argv[2]
    difficulty = sys.argv[3]
    target_instances = int(sys.argv[4]) if len(sys.argv) > 4 else 20
    
    # 默认的5种任务类型
    task_types = ["simple_task", "basic_task", "data_pipeline", "api_integration", "multi_stage_pipeline"]
    
    result = check_test_completion(model, prompt_type, difficulty, task_types, target_instances)
    
    print(f"\n测试完成情况检查")
    print(f"模型: {model}")
    print(f"Prompt类型: {prompt_type}")
    print(f"难度: {difficulty}")
    print(f"目标实例数: {target_instances}/任务类型")
    print("-" * 50)
    
    for task_type, info in result["details"].items():
        status = "✓" if info["remaining"] == 0 else "○"
        print(f"{status} {task_type:20s}: {info['done']:3d}/{info['target']:3d} 完成")
    
    print("-" * 50)
    print(f"总计: {result['total_done']}/{result['total_target']} 完成")
    
    if result["completed"]:
        print(f"\n✅ 该配置的测试已全部完成！")
    else:
        print(f"\n⏳ 还需要完成 {result['total_remaining']} 个测试")
    
    # 返回退出码：0表示已完成，1表示未完成
    sys.exit(0 if result["completed"] else 1)

if __name__ == "__main__":
    main()