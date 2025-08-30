#!/usr/bin/env python3
"""
修复Parquet错误统计问题：即使没有error_message，失败的测试也应该计入错误
"""

import os
from pathlib import Path

def fix_error_counting():
    """修复错误计数逻辑"""
    
    file_path = Path("parquet_cumulative_manager.py")
    if not file_path.exists():
        print(f"错误：找不到文件 {file_path}")
        return False
    
    # 备份原文件
    backup_path = file_path.with_suffix(f".py.backup_error_fix_{os.getpid()}")
    content = file_path.read_text()
    backup_path.write_text(content)
    print(f"✅ 已备份到: {backup_path}")
    
    # 需要替换的代码
    old_logic = """            # 错误统计（根据error_message或error_type更新）
            # 错误统计（支持多个字段名和error_message分析）
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
                    summary['other_errors'] += 1"""
    
    new_logic = """            # 错误统计（与enhanced一致：非full_success都算错误）
            # 判断success_level
            success_level = getattr(record, 'success_level', None)
            if success_level is None:
                # 如果没有success_level，根据success和partial_success判断
                if record.success:
                    if getattr(record, 'partial_success', False):
                        success_level = 'partial_success'
                    else:
                        success_level = 'full_success'
                else:
                    success_level = 'failure'
            
            # 只要不是full_success，就有错误
            if success_level != 'full_success':
                summary['total_errors'] += 1
                
                # 尝试分类错误
                error_type = None
                
                # 1. 首先检查是否是格式错误（工具调用为0）
                tool_calls = getattr(record, 'tool_calls', 0)
                executed_tools = getattr(record, 'executed_tools', [])
                
                # 处理tool_calls可能是int或list的情况
                if isinstance(tool_calls, list):
                    tool_calls_count = len(tool_calls)
                else:
                    tool_calls_count = tool_calls if tool_calls else 0
                
                if isinstance(executed_tools, list):
                    executed_tools_count = len(executed_tools)
                else:
                    executed_tools_count = executed_tools if executed_tools else 0
                
                # 如果没有任何工具调用，可能是格式错误
                if tool_calls_count == 0 and executed_tools_count == 0:
                    error_msg = getattr(record, 'error_message', '')
                    if error_msg:
                        error_lower = error_msg.lower()
                        format_indicators = [
                            'format errors detected', 'format recognition issue',
                            'tool call format', 'understand tool call format',
                            'invalid json', 'malformed', 'parse error'
                        ]
                        if any(indicator in error_lower for indicator in format_indicators):
                            error_type = 'format'
                    # 如果没有error_message但工具调用为0，也可能是格式问题
                    if not error_type and success_level == 'failure':
                        error_type = 'format'  # 默认认为是格式错误
                
                # 2. 尝试从字段获取错误类型
                if not error_type:
                    if hasattr(record, 'ai_error_category') and record.ai_error_category:
                        error_type = record.ai_error_category
                    elif hasattr(record, 'error_type') and record.error_type:
                        error_type = record.error_type
                    elif hasattr(record, 'error_classification') and record.error_classification:
                        error_type = record.error_classification
                    elif hasattr(record, 'error_message') and record.error_message:
                        # 分析error_message
                        error_type = self._classify_error_message(record.error_message)
                
                # 3. 根据错误类型更新统计
                if error_type:
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
                else:
                    # 如果无法分类，归为other_errors
                    summary['other_errors'] += 1"""
    
    # 应用修复
    if old_logic in content:
        modified_content = content.replace(old_logic, new_logic)
        file_path.write_text(modified_content)
        print("✅ 成功修复错误计数逻辑")
        print("   - 现在所有非full_success的测试都会计入错误")
        print("   - 智能检测格式错误（工具调用为0）")
        print("   - 无法分类的错误归为other_errors")
        return True
    else:
        print("⚠️  未找到要替换的代码，可能已经修复过了")
        return False

if __name__ == "__main__":
    if fix_error_counting():
        print("\n📝 下一步：")
        print("1. 运行测试验证修复：python test_error_counting_fix.py")
        print("2. 重新运行测试收集正确的错误统计")
    else:
        print("\n⚠️  修复失败，请手动检查代码")