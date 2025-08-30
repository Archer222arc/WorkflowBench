#!/usr/bin/env python3
"""
修复统计字段计算，确保所有测试都能计算完整的统计数据
"""

import shutil
from pathlib import Path
from datetime import datetime

def fix_batch_test_runner():
    """修改batch_test_runner.py确保分数总是被计算"""
    print("=" * 60)
    print("修复batch_test_runner.py - 确保分数总是被计算")
    print("=" * 60)
    
    file_path = Path("batch_test_runner.py")
    
    # 备份
    backup_path = file_path.parent / f"{file_path.stem}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_path.suffix}"
    shutil.copy2(file_path, backup_path)
    print(f"✅ 已备份到: {backup_path.name}")
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    modified = False
    
    # 查找并修改条件性分数计算（第818行附近）
    for i in range(len(lines)):
        # 找到条件检查
        if "if hasattr(self.quality_tester, 'stable_scorer') and self.quality_tester.stable_scorer:" in lines[i]:
            print(f"找到条件性分数计算: 第{i+1}行")
            
            # 找到对应的else分支
            j = i + 1
            indent_level = len(lines[i]) - len(lines[i].lstrip())
            else_line = -1
            
            while j < len(lines):
                current_indent = len(lines[j]) - len(lines[j].lstrip())
                if current_indent <= indent_level and lines[j].strip().startswith('else:'):
                    else_line = j
                    break
                j += 1
            
            if else_line > 0:
                # 在else分支中添加备用计算
                print(f"  修改else分支（第{else_line+1}行）添加备用计算")
                
                # 找到else后的内容
                k = else_line + 1
                if k < len(lines) and "print(f\"[DEBUG] stable_scorer not available" in lines[k]:
                    # 在debug print后添加备用计算
                    new_lines = []
                    indent = " " * (indent_level + 4)
                    
                    new_lines.append(f"{indent}# 备用分数计算（当stable_scorer不可用时）\n")
                    new_lines.append(f"{indent}# 基于工具执行计算workflow_score\n")
                    new_lines.append(f"{indent}if required_tools:\n")
                    new_lines.append(f"{indent}    workflow_score = tool_coverage_rate  # 使用工具覆盖率作为workflow分数\n")
                    new_lines.append(f"{indent}else:\n")
                    new_lines.append(f"{indent}    workflow_score = 1.0 if success else 0.3  # 没有工具要求时基于成功与否\n")
                    new_lines.append(f"{indent}\n")
                    new_lines.append(f"{indent}# 基于执行效率计算phase2_score\n")
                    new_lines.append(f"{indent}max_turns = 30\n")
                    new_lines.append(f"{indent}actual_turns = result.get('turns', 0)\n")
                    new_lines.append(f"{indent}if actual_turns > 0:\n")
                    new_lines.append(f"{indent}    phase2_score = max(0, 1 - (actual_turns / max_turns))\n")
                    new_lines.append(f"{indent}else:\n")
                    new_lines.append(f"{indent}    phase2_score = 0.0\n")
                    new_lines.append(f"{indent}\n")
                    new_lines.append(f"{indent}# 基于成功级别计算quality_score\n")
                    new_lines.append(f"{indent}if execution_status == 'full_success':\n")
                    new_lines.append(f"{indent}    quality_score = 1.0\n")
                    new_lines.append(f"{indent}elif execution_status == 'partial_success':\n")
                    new_lines.append(f"{indent}    quality_score = 0.6\n")
                    new_lines.append(f"{indent}else:\n")
                    new_lines.append(f"{indent}    quality_score = 0.2  # 失败也给基础分\n")
                    new_lines.append(f"{indent}\n")
                    
                    # 插入新行
                    lines = lines[:k+1] + new_lines + lines[k+1:]
                    modified = True
                    print("  ✅ 添加了备用分数计算逻辑")
                    break
    
    if modified:
        with open(file_path, 'w') as f:
            f.writelines(lines)
        print("✅ batch_test_runner.py修复完成")
    else:
        print("⚠️ 未找到需要修改的位置")
    
    return modified

def fix_enhanced_cumulative_manager():
    """确保enhanced_cumulative_manager正确初始化AI分类器"""
    print("\n" + "=" * 60)
    print("修复enhanced_cumulative_manager.py - 确保AI分类器初始化")
    print("=" * 60)
    
    file_path = Path("enhanced_cumulative_manager.py")
    
    # 备份
    backup_path = file_path.parent / f"{file_path.stem}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_path.suffix}"
    shutil.copy2(file_path, backup_path)
    print(f"✅ 已备份到: {backup_path.name}")
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    modified = False
    
    # 查找__init__方法
    for i in range(len(lines)):
        if "def __init__(self" in lines[i]:
            print(f"找到__init__方法: 第{i+1}行")
            
            # 查找是否有AI分类器初始化
            j = i + 1
            has_ai_init = False
            init_end = -1
            
            while j < len(lines):
                # 检查是否到了下一个方法
                if lines[j].strip() and not lines[j].startswith(' ') and not lines[j].startswith('\t'):
                    init_end = j
                    break
                if "def " in lines[j] and not lines[j].strip().startswith('#'):
                    init_end = j
                    break
                    
                if "self.ai_classifier" in lines[j]:
                    has_ai_init = True
                    print(f"  已有AI分类器初始化: 第{j+1}行")
                    break
                j += 1
            
            if not has_ai_init and init_end > 0:
                # 在__init__末尾添加AI分类器初始化
                print("  未找到AI分类器初始化，添加中...")
                
                # 找到合适的插入位置（在最后一个self.赋值之后）
                insert_pos = i + 1
                for k in range(i+1, init_end):
                    if lines[k].strip().startswith('self.'):
                        insert_pos = k + 1
                
                # 准备插入的代码
                indent = "        "  # 2级缩进
                new_lines = [
                    f"\n{indent}# 初始化AI错误分类器（确保总是可用）\n",
                    f"{indent}try:\n",
                    f"{indent}    from enhanced_ai_classifier import EnhancedAIErrorClassifier\n",
                    f"{indent}    self.ai_classifier = EnhancedAIErrorClassifier(\n",
                    f"{indent}        enable_gpt_classification=use_ai_classification,\n",
                    f"{indent}        fallback_on_failure=True\n",
                    f"{indent}    )\n",
                    f"{indent}    print('[INFO] AI错误分类器已初始化')\n",
                    f"{indent}except Exception as e:\n",
                    f"{indent}    print(f'[WARNING] 无法初始化AI分类器: {{e}}')\n",
                    f"{indent}    self.ai_classifier = None\n"
                ]
                
                # 插入代码
                lines = lines[:insert_pos] + new_lines + lines[insert_pos:]
                modified = True
                print("  ✅ 添加了AI分类器初始化代码")
            
            break
    
    if modified:
        with open(file_path, 'w') as f:
            f.writelines(lines)
        print("✅ enhanced_cumulative_manager.py修复完成")
    else:
        print("⚠️ AI分类器可能已经正确初始化")
    
    return modified

def verify_fixes():
    """验证修复是否成功"""
    print("\n" + "=" * 60)
    print("验证修复")
    print("=" * 60)
    
    # 检查batch_test_runner.py
    with open("batch_test_runner.py", 'r') as f:
        content = f.read()
    
    if "# 备用分数计算（当stable_scorer不可用时）" in content:
        print("✅ batch_test_runner.py: 备用分数计算已添加")
    else:
        print("❌ batch_test_runner.py: 备用分数计算未找到")
    
    # 检查enhanced_cumulative_manager.py
    with open("enhanced_cumulative_manager.py", 'r') as f:
        content = f.read()
    
    if "EnhancedAIErrorClassifier" in content and "self.ai_classifier = EnhancedAIErrorClassifier" in content:
        print("✅ enhanced_cumulative_manager.py: AI分类器初始化已添加")
    else:
        print("❌ enhanced_cumulative_manager.py: AI分类器初始化未找到")

def main():
    """主函数"""
    print("=" * 60)
    print("修复统计字段计算")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. 修复batch_test_runner.py
    runner_fixed = fix_batch_test_runner()
    
    # 2. 修复enhanced_cumulative_manager.py
    manager_fixed = fix_enhanced_cumulative_manager()
    
    # 3. 验证修复
    verify_fixes()
    
    # 4. 总结
    print("\n" + "=" * 60)
    print("总结")
    print("=" * 60)
    
    if runner_fixed or manager_fixed:
        print("✅ 修复已应用")
        print("\n下一步：")
        print("1. 运行测试: python test_all_statistics.py")
        print("2. 检查分数是否不再全是0")
        print("3. 运行实际测试验证统计字段")
    else:
        print("⚠️ 未进行任何修改")
        print("代码可能已经正确，或需要手动检查")

if __name__ == "__main__":
    main()