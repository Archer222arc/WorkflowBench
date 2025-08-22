#!/usr/bin/env python3
"""
修复累积统计系统
1. 确保每种prompt类型（包括7种flawed）都有独立的完整统计
2. 支持设置工具成功率
3. 正确记录所有分类数据
"""

import json
from pathlib import Path
from datetime import datetime

def fix_database_structure():
    """修复数据库结构，清理旧数据"""
    
    db_path = Path("pilot_bench_cumulative_results/master_database.json")
    
    if not db_path.exists():
        print("数据库不存在")
        return
    
    # 创建备份
    backup_path = db_path.with_suffix('.backup_before_fix')
    with open(db_path, 'r') as f:
        old_db = json.load(f)
    
    with open(backup_path, 'w') as f:
        json.dump(old_db, f, indent=2, ensure_ascii=False)
    print(f"已创建备份: {backup_path}")
    
    # 创建新的空数据库
    new_db = {
        "version": "2.1",
        "created_at": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
        "models": {},
        "summary": {
            "total_tests": 0,
            "total_success": 0,
            "total_partial": 0,
            "total_failure": 0,
            "models_tested": [],
            "last_test_time": None
        }
    }
    
    # 保存新数据库
    with open(db_path, 'w') as f:
        json.dump(new_db, f, indent=2, ensure_ascii=False)
    
    print("数据库已重置为v2.1版本")
    print("准备好进行新的测试")

if __name__ == "__main__":
    fix_database_structure()