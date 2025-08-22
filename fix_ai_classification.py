#!/usr/bin/env python3
"""
修复AI错误分类未启用的问题
"""

import shutil
from pathlib import Path
from datetime import datetime

def fix_ai_classification():
    """修复AI分类器配置"""
    print("修复AI错误分类器...")
    
    # 1. 确保batch_test_runner默认启用AI分类
    file_path = Path("batch_test_runner.py")
    backup_path = file_path.parent / f"{file_path.stem}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_path.suffix}"
    shutil.copy2(file_path, backup_path)
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    modified = False
    
    # 查找并修改默认参数
    for i, line in enumerate(lines):
        # 确保默认启用AI分类
        if "use_ai_classification: bool = False" in line:
            lines[i] = line.replace("False", "True")
            modified = True
            print(f"  ✅ 修改第{i+1}行：默认启用AI分类")
        
        # 确保AI分类器总是初始化
        if "if use_ai_classification:" in line and i > 100 and i < 120:
            # 改为总是初始化（移除条件）
            indent = len(line) - len(line.lstrip())
            lines[i] = " " * indent + "# 总是初始化AI分类器\n"
            modified = True
            print(f"  ✅ 修改第{i+1}行：总是初始化AI分类器")
    
    if modified:
        with open(file_path, 'w') as f:
            f.writelines(lines)
        print("✅ batch_test_runner.py已修复")
    
    # 2. 添加调试日志
    print("\n添加调试日志...")
    
    # 在_ai_classify_with_txt_content方法开头添加日志
    for i, line in enumerate(lines):
        if "def _ai_classify_with_txt_content" in line:
            # 找到方法体开始
            j = i + 2
            while j < len(lines) and not lines[j].strip().startswith('if'):
                j += 1
            
            if j < len(lines):
                # 在条件检查前添加调试日志
                indent = len(lines[j]) - len(lines[j].lstrip())
                debug_lines = [
                    f'{" " * indent}# 调试：AI分类器状态\n',
                    f'{" " * indent}print(f"[AI_DEBUG] use_ai_classification={{self.use_ai_classification}}, ai_classifier={{self.ai_classifier is not None}}, txt_content_len={{len(txt_content) if txt_content else 0}}")\n',
                    f'{" " * indent}\n'
                ]
                lines = lines[:j] + debug_lines + lines[j:]
                modified = True
                print(f"  ✅ 在第{j}行添加调试日志")
            break
    
    if modified:
        with open(file_path, 'w') as f:
            f.writelines(lines)
    
    return modified

if __name__ == "__main__":
    fix_ai_classification()
