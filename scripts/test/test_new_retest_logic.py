#!/usr/bin/env python3
"""
测试新的重测逻辑：基于完全失败+平均执行时间达到上限
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from auto_failure_maintenance_system import AutoFailureMaintenanceSystem

def test_new_retest_logic():
    """测试新的重测逻辑"""
    print("🧪 测试新的重测逻辑：基于完全失败+平均执行时间达到上限")
    print("=" * 60)
    
    # 创建维护系统
    system = AutoFailureMaintenanceSystem(enable_auto_retry=False)
    
    # 显示配置
    print(f"📋 当前配置:")
    print(f"  - 完全失败阈值: {system.auto_retest_config.complete_failure_threshold}")
    print(f"  - 最大执行时间: {system.auto_retest_config.max_execution_time}秒")
    print()
    
    # 分析测试完成情况
    print("🔍 分析测试完成情况...")
    analysis = system.analyze_test_completion()
    
    print(f"分析了 {len(analysis['models_analyzed'])} 个模型")
    print(f"发现失败模式: {len(analysis['failure_patterns'])} 个")
    print()
    
    # 显示详细分析结果
    retry_models = []
    for model in analysis['models_analyzed']:
        summary = analysis['completion_summary'][model]
        if summary['status'] == 'analyzed':
            completion_rate = summary['completion_rate']
            avg_exec_time = summary.get('avg_execution_time', 0)
            complete_failure = summary.get('needs_retry_complete_failure', False)
            high_exec_time = summary.get('needs_retry_high_execution_time', False)
            
            print(f"📊 模型: {model}")
            print(f"   - 完成率: {completion_rate:.1%}")
            print(f"   - 平均执行时间: {avg_exec_time:.1f}秒")
            
            reasons = []
            if complete_failure:
                failure_configs = summary.get('complete_failure_configs', [])
                reasons.append(f"完全失败配置: {len(failure_configs)}个")
                print(f"   - ⚠️  完全失败配置: {len(failure_configs)}个")
                for config in failure_configs[:3]:  # 显示前3个
                    print(f"     • {config['config']} ({config['total_tests']}个测试)")
            
            if high_exec_time:
                reasons.append(f"执行时间过长: {avg_exec_time:.1f}秒")
                print(f"   - ⚠️  执行时间过长: {avg_exec_time:.1f}秒 (阈值: {system.auto_retest_config.max_execution_time}秒)")
            
            needs_retry = summary.get('needs_retry', False)
            if needs_retry:
                retry_models.append(model)
                print(f"   - 🔄 需要重测: 是 ({', '.join(reasons)})")
            else:
                print(f"   - ✅ 状态: 正常")
            
            print()
    
    # 总结
    print("=" * 60)
    print(f"📈 重测建议总结:")
    if retry_models:
        print(f"🔄 需要重测的模型 ({len(retry_models)}个):")
        for model in retry_models:
            print(f"   - {model}")
    else:
        print("✅ 所有模型都在正常范围内，无需重测")
    
    print()
    print("💡 重测逻辑说明:")
    print("  1. 完全失败: 某配置的成功率为0%")
    print("  2. 执行时间过长: 平均执行时间超过设定阈值")
    print("  3. 满足任一条件即建议重测")

if __name__ == "__main__":
    test_new_retest_logic()