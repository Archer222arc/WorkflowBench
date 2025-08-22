#!/usr/bin/env python3
"""
修复数据统计字段不一致的问题
主要问题：
1. partial和failed字段未正确初始化和更新
2. 成功率计算基于错误的数据
"""

import json
from pathlib import Path
from datetime import datetime
import shutil

def fix_enhanced_cumulative_manager():
    """修复enhanced_cumulative_manager.py中的字段初始化问题"""
    
    print("修复enhanced_cumulative_manager.py...")
    file_path = Path("enhanced_cumulative_manager.py")
    
    # 备份原文件
    backup_path = file_path.parent / f"{file_path.stem}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_path.suffix}"
    shutil.copy2(file_path, backup_path)
    print(f"  已备份到: {backup_path.name}")
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # 查找初始化字典的位置（大约在584-625行）
    modified = False
    for i in range(len(lines)):
        # 在"success": 0,之后添加partial和failed
        if '"success": 0,' in lines[i] and '"partial":' not in lines[i+1]:
            # 找到缩进级别
            indent = len(lines[i]) - len(lines[i].lstrip())
            # 插入partial和failed字段
            lines.insert(i+1, ' ' * indent + '"partial": 0,\n')
            lines.insert(i+2, ' ' * indent + '"failed": 0,\n')
            modified = True
            print(f"  在第{i+1}行添加了partial和failed字段初始化")
            break
    
    # 查找更新统计的位置（大约在627-635行）
    for i in range(len(lines)):
        if 'task_data["total"] += 1' in lines[i]:
            # 找到后面更新success的地方
            j = i + 1
            while j < len(lines) and j < i + 20:
                if 'task_data["success"] += 1' in lines[j]:
                    # 检查是否需要添加partial和failed的更新逻辑
                    indent = len(lines[j]) - len(lines[j].lstrip())
                    
                    # 查找else分支
                    k = j + 1
                    while k < len(lines) and k < j + 10:
                        if 'else:' in lines[k] and lines[k].strip() == 'else:':
                            # 在else后面添加failed更新
                            lines.insert(k+1, ' ' * (indent) + 'task_data["failed"] += 1\n')
                            print(f"  在第{k+2}行添加了failed字段更新")
                            modified = True
                            break
                        k += 1
                    
                    # 如果没有else分支，需要添加
                    if not modified:
                        # 寻找if block的结束位置
                        k = j + 1
                        while k < len(lines):
                            # 检查缩进是否回到if的级别
                            current_indent = len(lines[k]) - len(lines[k].lstrip())
                            if current_indent <= indent - 4 and lines[k].strip():
                                # 在这里插入else分支
                                lines.insert(k, ' ' * (indent - 4) + 'else:\n')
                                lines.insert(k+1, ' ' * indent + 'task_data["failed"] += 1\n')
                                print(f"  在第{k+1}行添加了else分支和failed更新")
                                modified = True
                                break
                            k += 1
                    break
                j += 1
            break
    
    if modified:
        with open(file_path, 'w') as f:
            f.writelines(lines)
        print("  ✅ 修复完成")
    else:
        print("  ⚠️ 未找到需要修复的位置")
    
    return modified

def verify_fix():
    """验证修复是否成功"""
    print("\n验证修复...")
    
    with open("enhanced_cumulative_manager.py", 'r') as f:
        content = f.read()
    
    checks = [
        ('"partial": 0,', "partial字段初始化"),
        ('"failed": 0,', "failed字段初始化"),
        ('task_data["failed"] += 1', "failed字段更新")
    ]
    
    all_good = True
    for check_str, desc in checks:
        if check_str in content:
            print(f"  ✅ {desc}: 已找到")
        else:
            print(f"  ❌ {desc}: 未找到")
            all_good = False
    
    return all_good

if __name__ == "__main__":
    print("=" * 60)
    print("修复数据统计字段不一致问题")
    print("=" * 60)
    
    # 修复代码
    if fix_enhanced_cumulative_manager():
        # 验证修复
        if verify_fix():
            print("\n✅ 所有修复已成功应用！")
            print("\n下一步：")
            print("1. 重新运行测试以生成正确的统计数据")
            print("2. 或运行数据修复脚本来修正现有数据")
        else:
            print("\n⚠️ 修复可能不完整，请手动检查")
    else:
        print("\n未执行任何修复")