#!/usr/bin/env python3
"""
修复任务类型不匹配问题
将所有错误的 file_processing 替换为 basic_task
"""

import os
import re
from pathlib import Path
from datetime import datetime

# 需要修复的文件列表
FILES_TO_FIX = [
    "mdp_workflow_generator.py",
    "workflow_quality_test_flawed.py",
    "multi_model_batch_tester_v2.py",
    "extended_execution_result.py",
    "workflow_reasoning_generator.py",
    "unified_training_manager_dqn.py",
    "tool_and_task_generator.py"
]

# 已经修复的文件
ALREADY_FIXED = [
    "unified_training_manager.py"
]

def backup_file(filepath):
    """备份文件"""
    backup_path = f"{filepath}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    with open(filepath, 'r') as f:
        content = f.read()
    with open(backup_path, 'w') as f:
        f.write(content)
    print(f"  备份创建: {backup_path}")
    return backup_path

def fix_file_simple_replacement(filepath):
    """简单替换修复策略"""
    with open(filepath, 'r') as f:
        content = f.read()
    
    original = content
    changes = 0
    
    # 策略1: 直接替换file_processing为basic_task
    replacements = [
        ('file_processing', 'basic_task'),
        ('File processing', 'Basic task'),
        ('FILE_PROCESSING', 'BASIC_TASK'),
    ]
    
    for old, new in replacements:
        count = content.count(old)
        if count > 0:
            content = content.replace(old, new)
            changes += count
            print(f"    替换 '{old}' -> '{new}': {count} 处")
    
    # 特殊处理：某些函数名需要保留
    # 恢复函数名（如果有的话）
    function_preserves = [
        ('_create_basic_task_template', '_create_file_processing_template'),  # 如果函数名也被改了，改回来
    ]
    
    for new_name, old_name in function_preserves:
        if new_name in content and old_name not in content:
            # 如果我们错误地改了函数名，这里可以恢复
            pass  # 目前不需要
    
    if changes > 0:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"  ✅ 修复完成: {changes} 处更改")
    else:
        print(f"  ⚠️ 未发现需要修复的内容")
    
    return changes

def main():
    print("=" * 60)
    print("修复任务类型不匹配问题")
    print("=" * 60)
    
    print("\n📋 任务类型映射:")
    print("  错误: file_processing (不存在于任务库)")
    print("  正确: basic_task (1200个任务)")
    print()
    
    base_dir = Path(__file__).parent
    total_fixes = 0
    
    print("📁 开始修复文件:")
    for filename in FILES_TO_FIX:
        filepath = base_dir / filename
        
        if not filepath.exists():
            print(f"\n❌ 文件不存在: {filename}")
            continue
        
        print(f"\n处理: {filename}")
        
        # 备份原文件
        backup_file(filepath)
        
        # 修复文件
        fixes = fix_file_simple_replacement(filepath)
        total_fixes += fixes
    
    print("\n" + "=" * 60)
    print(f"✅ 修复完成！")
    print(f"  总共修复: {total_fixes} 处")
    print(f"  已处理文件: {len(FILES_TO_FIX)} 个")
    
    # 验证修复
    print("\n🔍 验证修复结果:")
    remaining = 0
    for filename in FILES_TO_FIX:
        filepath = base_dir / filename
        if filepath.exists():
            with open(filepath, 'r') as f:
                content = f.read()
                count = content.count('file_processing')
                if count > 0:
                    print(f"  ⚠️ {filename}: 仍有 {count} 处 'file_processing'")
                    remaining += count
                else:
                    print(f"  ✅ {filename}: 已完全修复")
    
    if remaining == 0:
        print("\n🎉 所有文件已成功修复！")
    else:
        print(f"\n⚠️ 仍有 {remaining} 处需要手动检查")
    
    # 提醒更新测试
    print("\n📌 后续步骤:")
    print("  1. 运行测试验证修复")
    print("  2. 检查是否有其他引用file_processing的地方")
    print("  3. 更新文档和配置文件")
    print("  4. 重新运行批量测试确认basic_task被正确测试")

if __name__ == "__main__":
    main()