#!/usr/bin/env python3
"""
迁移数据库到新格式 - 只保留统计，删除实例
"""

import json
from pathlib import Path
from datetime import datetime
from cumulative_data_structure import ModelStatistics

def migrate_database():
    """迁移数据库到v2.0格式"""
    
    db_path = Path("pilot_bench_cumulative_results/master_database.json")
    
    if not db_path.exists():
        print("数据库不存在")
        return
    
    # 读取现有数据库
    with open(db_path, 'r') as f:
        old_db = json.load(f)
    
    print(f"当前数据库版本: {old_db.get('version', '1.0')}")
    
    if old_db.get('version') == '2.0':
        print("数据库已经是v2.0版本")
        return
    
    # 创建备份
    backup_path = db_path.with_suffix('.backup_v1')
    with open(backup_path, 'w') as f:
        json.dump(old_db, f, indent=2, ensure_ascii=False)
    print(f"已创建备份: {backup_path}")
    
    # 创建新数据库结构
    new_db = {
        "version": "2.0",
        "created_at": old_db.get("created_at", datetime.now().isoformat()),
        "last_updated": datetime.now().isoformat(),
        "test_groups": {},  # 保留但不存储实例
        "models": {},  # 新的统计结构
        "summary": old_db.get("summary", {
            "total_tests": 0,
            "total_success": 0,
            "total_partial": 0,
            "total_failure": 0,
            "models_tested": [],
            "last_test_time": None
        })
    }
    
    # 迁移test_groups - 只保留统计，删除instances
    for key, group in old_db.get("test_groups", {}).items():
        new_group = {
            "model": group["model"],
            "task_type": group["task_type"],
            "prompt_type": group["prompt_type"],
            "difficulty": group["difficulty"],
            "is_flawed": group["is_flawed"],
            "flaw_type": group["flaw_type"],
            "statistics": group["statistics"],
            "instances": []  # 清空实例列表！
        }
        new_db["test_groups"][key] = new_group
    
    # 从test_groups构建新的models统计
    models_data = {}
    
    for key, group in new_db["test_groups"].items():
        model_name = group["model"]
        
        if model_name not in models_data:
            models_data[model_name] = {
                "model_name": model_name,
                "total_tests": 0,
                "total_success": 0,
                "total_partial": 0,
                "total_failure": 0,
                "by_task_type": {},
                "by_prompt_type": {},
                "by_flaw_type": {},
                "by_difficulty": {}
            }
        
        model = models_data[model_name]
        stats = group["statistics"]
        
        # 更新总计
        model["total_tests"] += stats["total"]
        model["total_success"] += stats["success"]
        model["total_partial"] += stats.get("partial_success", 0)
        model["total_failure"] += stats.get("failure", stats["total"] - stats["success"] - stats.get("partial_success", 0))
        
        # 按任务类型统计
        task_type = group["task_type"]
        if task_type not in model["by_task_type"]:
            model["by_task_type"][task_type] = {"total": 0, "success": 0}
        model["by_task_type"][task_type]["total"] += stats["total"]
        model["by_task_type"][task_type]["success"] += stats["success"]
        
        # 按提示类型统计（非缺陷测试）
        if not group["is_flawed"]:
            prompt_type = group["prompt_type"]
            if prompt_type not in model["by_prompt_type"]:
                model["by_prompt_type"][prompt_type] = {"total": 0, "success": 0}
            model["by_prompt_type"][prompt_type]["total"] += stats["total"]
            model["by_prompt_type"][prompt_type]["success"] += stats["success"]
        
        # 按缺陷类型统计
        if group["is_flawed"] and group["flaw_type"]:
            flaw_type = group["flaw_type"]
            if flaw_type not in model["by_flaw_type"]:
                model["by_flaw_type"][flaw_type] = {"total": 0, "success": 0}
            model["by_flaw_type"][flaw_type]["total"] += stats["total"]
            model["by_flaw_type"][flaw_type]["success"] += stats["success"]
        
        # 按难度统计
        difficulty = group["difficulty"]
        if difficulty not in model["by_difficulty"]:
            model["by_difficulty"][difficulty] = {"total": 0, "success": 0}
        model["by_difficulty"][difficulty]["total"] += stats["total"]
        model["by_difficulty"][difficulty]["success"] += stats["success"]
    
    # 添加计算的指标
    for model_name, model_data in models_data.items():
        # 计算成功率
        if model_data["total_tests"] > 0:
            model_data["success_rate"] = model_data["total_success"] / model_data["total_tests"] * 100
            model_data["weighted_success_score"] = (
                model_data["total_success"] * 1.0 + 
                model_data["total_partial"] * 0.5
            ) / model_data["total_tests"]
        else:
            model_data["success_rate"] = 0
            model_data["weighted_success_score"] = 0
        
        # 添加时间戳
        model_data["first_test_time"] = old_db.get("created_at")
        model_data["last_test_time"] = old_db.get("last_updated")
        
        # 为每个分类添加成功率
        for task_type, task_stats in model_data["by_task_type"].items():
            if task_stats["total"] > 0:
                task_stats["success_rate"] = task_stats["success"] / task_stats["total"] * 100
        
        for prompt_type, prompt_stats in model_data["by_prompt_type"].items():
            if prompt_stats["total"] > 0:
                prompt_stats["success_rate"] = prompt_stats["success"] / prompt_stats["total"] * 100
        
        for flaw_type, flaw_stats in model_data["by_flaw_type"].items():
            if flaw_stats["total"] > 0:
                flaw_stats["success_rate"] = flaw_stats["success"] / flaw_stats["total"] * 100
                flaw_stats["robustness_score"] = flaw_stats["success_rate"] / 100  # 0-1之间
    
    new_db["models"] = models_data
    
    # 保存新数据库
    with open(db_path, 'w') as f:
        json.dump(new_db, f, indent=2, ensure_ascii=False)
    
    # 显示迁移统计
    print("\n迁移完成！")
    print(f"数据库版本: 1.0 -> 2.0")
    print(f"模型数量: {len(models_data)}")
    
    total_instances_removed = 0
    for group in old_db.get("test_groups", {}).values():
        total_instances_removed += len(group.get("instances", []))
    
    print(f"删除的实例记录: {total_instances_removed}")
    
    # 显示文件大小变化
    old_size = backup_path.stat().st_size / 1024
    new_size = db_path.stat().st_size / 1024
    reduction = (old_size - new_size) / old_size * 100 if old_size > 0 else 0
    
    print(f"\n文件大小:")
    print(f"  原始: {old_size:.1f} KB")
    print(f"  现在: {new_size:.1f} KB")
    print(f"  减少: {reduction:.1f}%")
    
    # 显示统计摘要
    for model_name, model_data in models_data.items():
        print(f"\n模型 {model_name}:")
        print(f"  总测试: {model_data['total_tests']}")
        print(f"  成功率: {model_data['success_rate']:.1f}%")
        print(f"  加权分数: {model_data['weighted_success_score']:.3f}")

if __name__ == "__main__":
    migrate_database()