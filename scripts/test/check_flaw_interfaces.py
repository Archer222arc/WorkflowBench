#!/usr/bin/env python3
"""检查所有缺陷类型的接口匹配情况"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from flawed_workflow_generator import FlawedWorkflowGenerator

def check_flaw_interface(gen, flaw_type, expected_method, expected_severity='severe'):
    """检查单个缺陷类型的接口"""
    print(f"\n检查 {flaw_type}:")
    print(f"  预期参数: method='{expected_method}', severity='{expected_severity}'")
    
    # 创建测试工作流
    test_workflow = {
        'optimal_sequence': ['tool1', 'tool2', 'tool3'],
        'smart_actions': []
    }
    
    try:
        # 尝试注入缺陷
        result = gen.inject_specific_flaw(test_workflow, flaw_type, expected_severity)
        
        # 检查结果
        if result and result != test_workflow:
            print(f"  ✅ 成功 - 工作流已被修改")
            if 'flaw_type' in result:
                print(f"     flaw_type: {result['flaw_type']}")
            if 'parameter_flaws' in result:
                print(f"     parameter_flaws: {len(result['parameter_flaws'])} 个")
            return True
        else:
            print(f"  ❌ 失败 - 工作流未被修改")
            return False
            
    except Exception as e:
        print(f"  ❌ 异常: {str(e)}")
        return False

def analyze_method_implementations():
    """分析每个方法的实现，检查它们支持哪些参数值"""
    
    methods_info = {
        'introduce_order_flaw': {
            'supported_methods': ['swap', 'dependency', 'reverse'],
            'mapping_uses': 'dependency'
        },
        'introduce_tool_misuse': {
            'supported_methods': ['similar', 'wrong'],
            'mapping_uses': 'similar'
        },
        'introduce_parameter_flaw': {
            'supported_methods': ['missing', 'wrong_type', 'wrong'],  # 现在包含'wrong'
            'mapping_uses': 'wrong'
        },
        'introduce_missing_steps': {
            'supported_methods': ['middle', 'critical', 'random'],
            'mapping_uses': 'critical'
        },
        'introduce_redundancy': {
            'supported_methods': ['duplicate', 'repeat'],
            'mapping_uses': 'duplicate'
        },
        'introduce_logic_break': {
            'supported_methods': ['format', 'dependency'],
            'mapping_uses': 'format'
        },
        'introduce_semantic_drift': {
            'supported_methods': None,  # 不使用method参数
            'mapping_uses': None
        }
    }
    
    print("\n" + "="*60)
    print("方法实现分析")
    print("="*60)
    
    issues = []
    for method_name, info in methods_info.items():
        print(f"\n{method_name}:")
        print(f"  映射使用: {info['mapping_uses']}")
        print(f"  支持的值: {info['supported_methods']}")
        
        if info['mapping_uses'] and info['supported_methods']:
            if info['mapping_uses'] not in info['supported_methods']:
                print(f"  ⚠️  潜在问题: 映射使用的 '{info['mapping_uses']}' 可能不被支持")
                issues.append(method_name)
            else:
                print(f"  ✅ 接口匹配")
    
    return issues

def test_all_flaws():
    """测试所有缺陷类型"""
    
    # 创建生成器
    gen = FlawedWorkflowGenerator(
        tool_registry={},
        embedding_manager=None,
        tool_capabilities={}
    )
    
    # 缺陷映射（从代码中提取）
    flaw_mappings = {
        'sequence_disorder': ('introduce_order_flaw', 'dependency'),
        'tool_misuse': ('introduce_tool_misuse', 'similar'),
        'parameter_error': ('introduce_parameter_flaw', 'wrong'),
        'missing_step': ('introduce_missing_steps', 'critical'),
        'redundant_operations': ('introduce_redundancy', 'duplicate'),
        'logical_inconsistency': ('introduce_logic_break', 'format'),
        'semantic_drift': ('introduce_semantic_drift', None)
    }
    
    print("\n" + "="*60)
    print("缺陷注入测试")
    print("="*60)
    
    results = {}
    for flaw_type, (method_name, method_param) in flaw_mappings.items():
        success = check_flaw_interface(gen, flaw_type, method_param)
        results[flaw_type] = success
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    
    print(f"\n成功: {success_count}/{total_count}")
    
    if success_count < total_count:
        print("\n失败的缺陷类型:")
        for flaw_type, success in results.items():
            if not success:
                print(f"  - {flaw_type}")
    
    return results

def check_method_branches():
    """检查每个方法的条件分支，确认它们处理了哪些参数值"""
    
    import ast
    import inspect
    from flawed_workflow_generator import FlawedWorkflowGenerator
    
    print("\n" + "="*60)
    print("条件分支检查")
    print("="*60)
    
    methods_to_check = [
        'introduce_order_flaw',
        'introduce_tool_misuse', 
        'introduce_missing_steps',
        'introduce_redundancy',
        'introduce_logic_break'
    ]
    
    for method_name in methods_to_check:
        method = getattr(FlawedWorkflowGenerator, method_name)
        source = inspect.getsource(method)
        
        # 简单的字符串搜索来找到 if/elif 语句中的 method 比较
        print(f"\n{method_name} 中的 method 参数检查:")
        
        lines = source.split('\n')
        for line in lines:
            if 'if method ==' in line or 'elif method ==' in line:
                # 提取比较的值
                print(f"  {line.strip()}")

if __name__ == "__main__":
    # 1. 分析方法实现
    issues = analyze_method_implementations()
    
    # 2. 测试所有缺陷
    results = test_all_flaws()
    
    # 3. 检查条件分支
    check_method_branches()
    
    # 最终结论
    print("\n" + "="*60)
    print("最终结论")
    print("="*60)
    
    if not issues and all(results.values()):
        print("\n✅ 所有缺陷类型接口都正常工作！")
    else:
        print("\n⚠️  发现以下问题:")
        if issues:
            print(f"  - 潜在接口不匹配: {', '.join(issues)}")
        failed_flaws = [k for k, v in results.items() if not v]
        if failed_flaws:
            print(f"  - 测试失败的缺陷: {', '.join(failed_flaws)}")