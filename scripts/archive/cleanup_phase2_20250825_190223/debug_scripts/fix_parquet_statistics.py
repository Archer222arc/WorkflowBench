#!/usr/bin/env python3
"""
修复Parquet统计计算，使其与enhanced_cumulative_manager保持一致
"""

import os
import sys
from pathlib import Path

def main():
    """修改parquet_cumulative_manager.py使用与enhanced相同的统计方法"""
    
    file_path = Path("parquet_cumulative_manager.py")
    if not file_path.exists():
        print(f"错误：找不到文件 {file_path}")
        return 1
    
    # 备份原文件
    backup_path = file_path.with_suffix(f".py.backup_{os.getpid()}")
    content = file_path.read_text()
    backup_path.write_text(content)
    print(f"✅ 已备份到: {backup_path}")
    
    # 需要修改的关键部分
    fixes = []
    
    # 1. 修复成功统计逻辑（添加partial统计）
    old_success_logic = """            # 更新成功计数
            if record.success:
                summary['success'] += 1
                summary['full_success'] += 1
            elif getattr(record, 'partial_success', False):
                summary['partial_success'] += 1"""
    
    new_success_logic = """            # 更新成功计数（与enhanced一致）
            if record.success:
                summary['success'] += 1
                # 检查是否是完全成功还是部分成功
                success_level = getattr(record, 'success_level', 'full_success')
                if success_level == "full_success":
                    summary['full_success'] += 1
                elif success_level == "partial_success":
                    summary['partial_success'] += 1
                    summary['partial'] = summary.get('partial', 0) + 1
            elif getattr(record, 'partial_success', False):
                summary['partial_success'] += 1
                summary['partial'] = summary.get('partial', 0) + 1
            else:
                # 失败的情况
                summary['failed'] = summary.get('failed', 0) + 1"""
    
    fixes.append((old_success_logic, new_success_logic))
    
    # 2. 添加增量平均计算（用于执行统计）
    old_avg_calc = """                # 平均值
                summary['avg_execution_time'] = summary['_total_execution_time'] / total
                summary['avg_turns'] = summary['_total_turns'] / total
                summary['avg_tool_calls'] = summary['_total_tool_calls'] / total
                summary['tool_coverage_rate'] = summary['_total_tool_coverage'] / total"""
    
    new_avg_calc = """                # 使用增量平均更新执行统计（与enhanced一致）
                n = total
                prev_avg_time = summary.get('avg_execution_time', 0)
                prev_avg_turns = summary.get('avg_turns', 0)
                prev_avg_calls = summary.get('avg_tool_calls', 0)
                prev_avg_coverage = summary.get('tool_coverage_rate', 0)
                
                # 增量更新（避免累积误差）
                summary['avg_execution_time'] = prev_avg_time + (summary['_total_execution_time'] / n - prev_avg_time) / n
                summary['avg_turns'] = prev_avg_turns + (summary['_total_turns'] / n - prev_avg_turns) / n
                summary['avg_tool_calls'] = prev_avg_calls + (summary['_total_tool_calls'] / n - prev_avg_calls) / n
                summary['tool_coverage_rate'] = prev_avg_coverage + (summary['_total_tool_coverage'] / n - prev_avg_coverage) / n"""
    
    fixes.append((old_avg_calc, new_avg_calc))
    
    # 3. 修复错误率计算（基于总错误数而不是总测试数）
    old_error_rates = """                # 错误率
                if summary['total_errors'] > 0:
                    summary['tool_selection_error_rate'] = summary['tool_selection_errors'] / summary['total_errors']
                    summary['parameter_error_rate'] = summary['parameter_config_errors'] / summary['total_errors']
                    summary['sequence_error_rate'] = summary['sequence_order_errors'] / summary['total_errors']
                    summary['dependency_error_rate'] = summary['dependency_errors'] / summary['total_errors']
                    summary['timeout_error_rate'] = summary['timeout_errors'] / summary['total_errors']
                    summary['format_error_rate'] = summary['tool_call_format_errors'] / summary['total_errors']
                    summary['max_turns_error_rate'] = summary['max_turns_errors'] / summary['total_errors']
                    summary['other_error_rate'] = summary['other_errors'] / summary['total_errors']"""
    
    new_error_rates = """                # 错误率（基于总错误数，与enhanced一致）
                total_errors = summary.get('total_errors', 0)
                if total_errors > 0:
                    summary['tool_selection_error_rate'] = summary.get('tool_selection_errors', 0) / total_errors
                    summary['parameter_error_rate'] = summary.get('parameter_config_errors', 0) / total_errors
                    summary['sequence_error_rate'] = summary.get('sequence_order_errors', 0) / total_errors
                    summary['dependency_error_rate'] = summary.get('dependency_errors', 0) / total_errors
                    summary['timeout_error_rate'] = summary.get('timeout_errors', 0) / total_errors
                    summary['format_error_rate'] = summary.get('tool_call_format_errors', 0) / total_errors
                    summary['max_turns_error_rate'] = summary.get('max_turns_errors', 0) / total_errors
                    summary['other_error_rate'] = summary.get('other_errors', 0) / total_errors
                else:
                    # 没有错误时，所有错误率都为0
                    summary['tool_selection_error_rate'] = 0.0
                    summary['parameter_error_rate'] = 0.0
                    summary['sequence_error_rate'] = 0.0
                    summary['dependency_error_rate'] = 0.0
                    summary['timeout_error_rate'] = 0.0
                    summary['format_error_rate'] = 0.0
                    summary['max_turns_error_rate'] = 0.0
                    summary['other_error_rate'] = 0.0"""
    
    fixes.append((old_error_rates, new_error_rates))
    
    # 4. 添加辅助统计处理
    old_assisted = """            # 辅助统计
            if hasattr(record, 'assisted') and record.assisted:
                summary['tests_with_assistance'] += 1
                if record.success:
                    summary['assisted_success'] += 1
                else:
                    summary['assisted_failure'] += 1
                if hasattr(record, 'assisted_turns'):
                    summary['total_assisted_turns'] += record.assisted_turns"""
    
    new_assisted = """            # 辅助统计（与enhanced一致）
            format_error_count = getattr(record, 'format_error_count', 0)
            if format_error_count > 0:
                summary['tests_with_assistance'] += 1
                summary['total_assisted_turns'] += format_error_count
                if record.success:
                    summary['assisted_success'] += 1
                else:
                    summary['assisted_failure'] += 1
            elif hasattr(record, 'assisted') and record.assisted:
                summary['tests_with_assistance'] += 1
                if record.success:
                    summary['assisted_success'] += 1
                else:
                    summary['assisted_failure'] += 1
                if hasattr(record, 'assisted_turns'):
                    summary['total_assisted_turns'] += record.assisted_turns"""
    
    fixes.append((old_assisted, new_assisted))
    
    # 5. 添加辅助统计率计算
    find_after_error_rates = "summary['other_error_rate'] = 0.0"
    add_assisted_rates = """summary['other_error_rate'] = 0.0
                
                # 辅助统计率（与enhanced一致）
                tests_with_assist = summary.get('tests_with_assistance', 0)
                if tests_with_assist > 0:
                    summary['assisted_success_rate'] = summary.get('assisted_success', 0) / tests_with_assist
                    summary['avg_assisted_turns'] = summary.get('total_assisted_turns', 0) / tests_with_assist
                else:
                    summary['assisted_success_rate'] = 0.0
                    summary['avg_assisted_turns'] = 0.0
                summary['assistance_rate'] = tests_with_assist / total"""
    
    # 应用修复
    modified_content = content
    success_count = 0
    
    for old, new in fixes:
        if old in modified_content:
            modified_content = modified_content.replace(old, new)
            success_count += 1
            print(f"✅ 应用修复 {success_count}: {new.split('（')[1].split('）')[0] if '（' in new else '统计逻辑修复'}")
        else:
            print(f"⚠️  未找到要替换的代码块 {success_count + 1}")
    
    # 特殊处理辅助统计率（在正确位置插入）
    if find_after_error_rates in modified_content:
        modified_content = modified_content.replace(find_after_error_rates, add_assisted_rates)
        success_count += 1
        print(f"✅ 应用修复 {success_count}: 添加辅助统计率计算")
    
    # 6. 添加智能错误分类支持（如果工具调用为0）
    add_format_error_detection = """
    def _classify_error_message(self, error_message: str) -> str:
        \"\"\"
        分析错误消息进行分类（与enhanced一致）
        \"\"\"
        if not error_message:
            return 'unknown'
        
        error_lower = error_message.lower()
        
        # Format errors
        if any(x in error_lower for x in ['format errors detected', 'format recognition issue', 
                                          'tool call format', 'understand tool call format',
                                          'invalid json', 'malformed', 'parse error']):
            return 'format'
        
        # Max turns without tool calls (also format)
        if ('no tool calls' in error_lower and 'turns' in error_lower) or \
           ('max turns reached' in error_lower and 'no tool calls' in error_lower):
            return 'format'
        
        # Pure max turns
        if 'max turns reached' in error_lower:
            return 'max_turns'
        
        # Agent-level timeout
        if ('test timeout after' in error_lower) or \
           ('timeout after' in error_lower and ('seconds' in error_lower or 'minutes' in error_lower)):
            return 'timeout'
        
        # Tool selection
        if ('tool' in error_lower and ('select' in error_lower or 'choice' in error_lower)) or \
           'tool calls failed' in error_lower:
            return 'tool_selection'
        
        # Parameter errors
        if any(x in error_lower for x in ['parameter', 'argument', 'invalid_input', 
                                          'permission_denied', 'validation failed']):
            return 'parameter'
        
        # Sequence errors
        if any(x in error_lower for x in ['sequence', 'order', 'required tools not completed']):
            return 'sequence'
        
        # Dependency errors
        if any(x in error_lower for x in ['dependency', 'prerequisite', 'missing requirement']):
            return 'dependency'
        
        return 'other'
"""
    
    # 找到合适的位置插入分类方法（在类定义内）
    if "_classify_error_message" not in modified_content:
        # 在add_test_result_with_classification方法之前插入
        insert_pos = modified_content.find("    def add_test_result_with_classification")
        if insert_pos > 0:
            modified_content = modified_content[:insert_pos] + add_format_error_detection + "\n" + modified_content[insert_pos:]
            success_count += 1
            print(f"✅ 应用修复 {success_count}: 添加错误消息分类方法")
    
    # 保存修改后的文件
    file_path.write_text(modified_content)
    print(f"\n✅ 成功应用 {success_count} 个修复到 {file_path}")
    print(f"📝 备份文件: {backup_path}")
    
    # 验证修改
    print("\n验证修改...")
    with open(file_path, 'r') as f:
        new_content = f.read()
        
    checks = [
        ("增量平均计算", "增量更新" in new_content),
        ("错误率基于总错误", "total_errors > 0" in new_content and "/ total_errors" in new_content),
        ("辅助统计率", "assisted_success_rate" in new_content),
        ("格式错误检测", "format_error_count" in new_content),
        ("错误消息分类", "_classify_error_message" in new_content),
        ("完整成功级别处理", "success_level" in new_content)
    ]
    
    all_good = True
    for check_name, check_result in checks:
        if check_result:
            print(f"  ✅ {check_name}")
        else:
            print(f"  ❌ {check_name}")
            all_good = False
    
    if all_good:
        print("\n🎉 所有修复成功应用！Parquet统计现在与JSON完全一致")
    else:
        print("\n⚠️  部分修复可能未成功，请检查")
    
    return 0 if all_good else 1

if __name__ == "__main__":
    sys.exit(main())