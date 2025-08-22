#!/usr/bin/env python3
"""
修复parquet_cumulative_manager的错误分类问题
通过支持多个字段名和添加error_message分析能力
"""

import sys
from pathlib import Path
import shutil
from datetime import datetime

def fix_parquet_manager():
    """修复parquet_cumulative_manager.py的错误分类逻辑"""
    
    file_path = Path('parquet_cumulative_manager.py')
    
    # 备份原文件
    backup_path = file_path.with_suffix(f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
    shutil.copy(file_path, backup_path)
    print(f"✅ 已备份到: {backup_path}")
    
    # 读取文件内容
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # 找到需要修改的部分（第367-386行）
    # 错误统计（根据error_message或error_type更新）
    start_line = None
    for i, line in enumerate(lines):
        if 'if hasattr(record, \'error_type\') and record.error_type:' in line:
            start_line = i
            break
    
    if start_line is None:
        print("❌ 未找到需要修改的代码")
        return False
    
    # 找到这个if块的结束位置
    end_line = start_line + 1
    indent_level = len(lines[start_line]) - len(lines[start_line].lstrip())
    for i in range(start_line + 1, len(lines)):
        current_indent = len(lines[i]) - len(lines[i].lstrip())
        if lines[i].strip() and current_indent <= indent_level:
            end_line = i
            break
    
    print(f"📍 找到错误分类代码: 第{start_line+1}行到第{end_line}行")
    
    # 新的错误分类代码
    new_code = '''            # 错误统计（支持多个字段名和error_message分析）
            error_type = None
            
            # 尝试多个可能的字段名
            if hasattr(record, 'ai_error_category') and record.ai_error_category:
                error_type = record.ai_error_category
            elif hasattr(record, 'error_type') and record.error_type:
                error_type = record.error_type
            elif hasattr(record, 'error_classification') and record.error_classification:
                error_type = record.error_classification
            elif record.error_message:
                # 如果都没有，分析error_message（简化版分类逻辑）
                error_type = self._classify_error_message(record.error_message)
            
            if error_type:
                summary['total_errors'] += 1
                error_type = str(error_type).lower()
                if 'timeout' in error_type:
                    summary['timeout_errors'] += 1
                elif 'dependency' in error_type:
                    summary['dependency_errors'] += 1
                elif 'parameter' in error_type:
                    summary['parameter_config_errors'] += 1
                elif 'tool_selection' in error_type:
                    summary['tool_selection_errors'] += 1
                elif 'sequence' in error_type:
                    summary['sequence_order_errors'] += 1
                elif 'max_turns' in error_type:
                    summary['max_turns_errors'] += 1
                elif 'format' in error_type:
                    summary['tool_call_format_errors'] += 1
                else:
                    summary['other_errors'] += 1
'''
    
    # 替换代码
    new_lines = lines[:start_line] + [new_code] + lines[end_line:]
    
    # 添加_classify_error_message方法（如果不存在）
    # 在类的最后添加这个方法
    classify_method = '''
    def _classify_error_message(self, error_message: str) -> str:
        """根据错误消息内容分类错误类型（简化版）"""
        if not error_message:
            return 'unknown'
        
        error_lower = error_message.lower()
        
        # 超时错误
        if any(keyword in error_lower for keyword in ['timeout', 'timed out', 'time limit']):
            return 'timeout_errors'
        
        # 格式错误
        if any(keyword in error_lower for keyword in ['format', 'parse', 'invalid json', 'malformed']):
            return 'tool_call_format_errors'
        
        # 最大轮数错误
        if any(keyword in error_lower for keyword in ['max turns', 'maximum turns', 'turn limit']):
            return 'max_turns_errors'
        
        # 工具选择错误
        if any(keyword in error_lower for keyword in ['tool not found', 'unknown tool', 'invalid tool']):
            return 'tool_selection_errors'
        
        # 参数错误
        if any(keyword in error_lower for keyword in ['parameter', 'argument', 'missing required']):
            return 'parameter_config_errors'
        
        # 顺序错误
        if any(keyword in error_lower for keyword in ['sequence', 'order', 'step']):
            return 'sequence_order_errors'
        
        # 依赖错误
        if any(keyword in error_lower for keyword in ['dependency', 'depend', 'prerequisite']):
            return 'dependency_errors'
        
        return 'other_errors'
'''
    
    # 找到类的结束位置，在最后一个方法后添加
    class_end = None
    for i in range(len(new_lines) - 1, -1, -1):
        if new_lines[i].strip().startswith('def ') and not new_lines[i].strip().startswith('def _classify_error_message'):
            # 找到这个方法的结束
            for j in range(i + 1, len(new_lines)):
                if new_lines[j].strip() and not new_lines[j].startswith(' ') and not new_lines[j].startswith('\t'):
                    class_end = j
                    break
            if class_end is None:
                class_end = len(new_lines) - 1
            break
    
    # 检查是否已经有_classify_error_message方法
    has_classify_method = any('def _classify_error_message' in line for line in new_lines)
    
    if not has_classify_method and class_end:
        new_lines = new_lines[:class_end] + [classify_method + '\n'] + new_lines[class_end:]
        print("✅ 添加了_classify_error_message方法")
    
    # 写回文件
    with open(file_path, 'w') as f:
        f.writelines(new_lines)
    
    print("✅ 修复完成")
    return True

def verify_fix():
    """验证修复是否成功"""
    
    print("\n验证修复...")
    
    # 检查文件是否包含新代码
    with open('parquet_cumulative_manager.py', 'r') as f:
        content = f.read()
    
    checks = [
        ('支持ai_error_category', 'ai_error_category' in content),
        ('支持error_classification', 'error_classification' in content),
        ('包含_classify_error_message方法', '_classify_error_message' in content),
        ('分析error_message', 'record.error_message' in content and '_classify_error_message(record.error_message)' in content)
    ]
    
    all_passed = True
    for check_name, passed in checks:
        if passed:
            print(f"  ✅ {check_name}")
        else:
            print(f"  ❌ {check_name}")
            all_passed = False
    
    return all_passed

def main():
    """主函数"""
    print("=" * 60)
    print("修复Parquet错误分类字段映射问题")
    print("=" * 60)
    
    # 执行修复
    if not fix_parquet_manager():
        print("❌ 修复失败")
        return 1
    
    # 验证修复
    if not verify_fix():
        print("❌ 验证失败")
        return 1
    
    print("\n✅ 所有修复已完成！")
    print("\n下一步：")
    print("1. 运行小规模测试验证错误分类是否正确记录")
    print("2. 从JSON恢复历史数据的错误分类字段")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())