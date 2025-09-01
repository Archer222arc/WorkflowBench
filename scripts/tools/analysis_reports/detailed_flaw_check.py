#!/usr/bin/env python3
"""详细检查每个缺陷方法的实际实现"""

import re
from pathlib import Path

def analyze_flaw_implementations():
    """分析flawed_workflow_generator.py中每个方法的实际实现"""
    
    file_path = Path('flawed_workflow_generator.py')
    with open(file_path, 'r') as f:
        content = f.read()
    
    # 定义要检查的方法和它们在映射中使用的参数
    methods_to_check = {
        'introduce_order_flaw': {
            'mapping_param': 'dependency',
            'pattern': r'def introduce_order_flaw.*?(?=\n    def|\nclass|\Z)',
        },
        'introduce_tool_misuse': {
            'mapping_param': 'similar',
            'pattern': r'def introduce_tool_misuse.*?(?=\n    def|\nclass|\Z)',
        },
        'introduce_missing_steps': {
            'mapping_param': 'critical',
            'pattern': r'def introduce_missing_steps.*?(?=\n    def|\nclass|\Z)',
        },
        'introduce_redundancy': {
            'mapping_param': 'duplicate',
            'pattern': r'def introduce_redundancy.*?(?=\n    def|\nclass|\Z)',
        },
        'introduce_logic_break': {
            'mapping_param': 'format',
            'pattern': r'def introduce_logic_break.*?(?=\n    def|\nclass|\Z)',
        }
    }
    
    print("="*70)
    print("详细的方法实现分析")
    print("="*70)
    
    issues = []
    
    for method_name, config in methods_to_check.items():
        print(f"\n### {method_name}")
        print(f"映射使用的参数: '{config['mapping_param']}'")
        
        # 提取方法代码
        match = re.search(config['pattern'], content, re.DOTALL)
        if not match:
            print(f"  ❌ 无法找到方法实现")
            continue
            
        method_code = match.group(0)
        
        # 查找所有的 if/elif method == 语句
        if_patterns = re.findall(r'(if|elif)\s+method\s*==\s*[\'"](\w+)[\'"]', method_code)
        
        if if_patterns:
            print(f"  实现的分支:")
            supported_methods = []
            for condition, method_value in if_patterns:
                print(f"    - {condition} method == '{method_value}'")
                supported_methods.append(method_value)
            
            # 检查映射参数是否被支持
            if config['mapping_param'] in supported_methods:
                print(f"  ✅ '{config['mapping_param']}' 被正确实现")
            else:
                print(f"  ❌ '{config['mapping_param']}' 没有对应的实现分支！")
                issues.append((method_name, config['mapping_param']))
                
            # 检查是否有else分支
            if 'else:' in method_code and 'else:' not in [s for s in method_code.split('\n') if 'severity' in s]:
                # 排除处理severity的else分支
                else_lines = [line for line in method_code.split('\n') if 'else:' in line and 'severity' not in line]
                if else_lines:
                    print(f"  ℹ️  有else分支作为默认处理")
        else:
            print(f"  ⚠️  没有找到method参数的条件分支")
            
    return issues

def check_specific_implementations():
    """检查特定的可能有问题的实现"""
    
    print("\n" + "="*70)
    print("特定问题检查")
    print("="*70)
    
    # 这里检查一些已知可能有问题的情况
    file_path = Path('flawed_workflow_generator.py')
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # 查找每个方法的实现细节
    findings = []
    
    # 1. 检查introduce_missing_steps是否处理'critical'
    print("\n1. 检查 introduce_missing_steps 对 'critical' 的处理:")
    for i, line in enumerate(lines):
        if 'def introduce_missing_steps' in line:
            # 查看接下来的50行
            method_lines = lines[i:i+50]
            has_critical = any("'critical'" in l or '"critical"' in l for l in method_lines)
            if has_critical:
                print("  ✅ 找到 'critical' 相关代码")
            else:
                print("  ⚠️  没有找到 'critical' 的直接处理")
                # 检查是否有其他处理逻辑
                if any('elif' in l for l in method_lines):
                    print("     但有其他条件分支，可能有间接处理")
                findings.append("introduce_missing_steps可能没有处理'critical'")
            break
    
    # 2. 检查其他潜在问题
    print("\n2. 检查缺省值处理:")
    for method in ['introduce_order_flaw', 'introduce_tool_misuse', 'introduce_logic_break']:
        print(f"  {method}:")
        for i, line in enumerate(lines):
            if f'def {method}' in line:
                method_lines = lines[i:i+80]
                # 检查是否有未处理的情况
                has_else = any('else:' in l and 'severity' not in l for l in method_lines)
                if has_else:
                    print(f"    ✅ 有else分支处理未匹配的情况")
                else:
                    # 检查是否所有路径都有返回值
                    print(f"    ⚠️  可能没有处理所有情况")
                break
    
    return findings

if __name__ == "__main__":
    # 运行分析
    issues = analyze_flaw_implementations()
    findings = check_specific_implementations()
    
    # 总结
    print("\n" + "="*70)
    print("分析总结")
    print("="*70)
    
    if not issues and not findings:
        print("\n✅ 所有方法实现看起来都正确！")
    else:
        print("\n⚠️  发现以下潜在问题:")
        
        if issues:
            print("\n缺失的实现分支:")
            for method, param in issues:
                print(f"  - {method} 缺少对 '{param}' 的处理")
        
        if findings:
            print("\n其他发现:")
            for finding in findings:
                print(f"  - {finding}")
        
        print("\n建议:")
        print("  1. 检查这些方法是否有默认处理逻辑")
        print("  2. 确认是否所有映射参数都有对应的实现")
        print("  3. 考虑添加缺失的分支或修改映射")