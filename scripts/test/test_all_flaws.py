#!/usr/bin/env python3
"""综合测试所有缺陷类型的功能"""

import sys
import json
import time
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent))

from batch_test_runner import BatchTestRunner, TestTask

def test_single_flaw(runner: BatchTestRunner, flaw_type: str) -> Dict:
    """测试单个缺陷类型"""
    
    task = TestTask(
        model='gpt-4o-mini',
        task_type='simple_task',
        prompt_type='flawed',
        difficulty='easy',
        is_flawed=True,
        flaw_type=flaw_type,
        tool_success_rate=0.8,
        timeout=30
    )
    
    start_time = time.time()
    
    try:
        result = runner.run_single_test(
            model=task.model,
            task_type=task.task_type,
            prompt_type=task.prompt_type,
            is_flawed=task.is_flawed,
            flaw_type=task.flaw_type,
            timeout=task.timeout,
            tool_success_rate=task.tool_success_rate,
            difficulty=task.difficulty
        )
        
        elapsed = time.time() - start_time
        
        return {
            'flaw_type': flaw_type,
            'success': result.get('success', False),
            'error': result.get('error'),
            'execution_time': elapsed,
            'turns': result.get('turns', 0),
            'timeout': elapsed >= task.timeout
        }
        
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            'flaw_type': flaw_type,
            'success': False,
            'error': str(e),
            'execution_time': elapsed,
            'turns': 0,
            'timeout': False,
            'exception': True
        }

def main():
    """主测试函数"""
    
    print("="*70)
    print("缺陷类型综合测试")
    print("="*70)
    print("\n测试配置:")
    print("  - 模型: gpt-4o-mini")
    print("  - 任务类型: simple_task")
    print("  - 难度: easy")
    print("  - 超时: 30秒")
    print("  - 工具成功率: 0.8")
    
    # 所有缺陷类型
    flaw_types = [
        'sequence_disorder',
        'tool_misuse',
        'parameter_error',
        'missing_step',
        'redundant_operations',
        'logical_inconsistency',
        'semantic_drift'
    ]
    
    # 创建测试运行器
    print("\n初始化测试运行器...")
    runner = BatchTestRunner(debug=False, silent=True)
    
    # 测试每个缺陷类型
    results = []
    print("\n开始测试:")
    print("-" * 50)
    
    for i, flaw_type in enumerate(flaw_types, 1):
        print(f"\n[{i}/{len(flaw_types)}] 测试 {flaw_type}...")
        result = test_single_flaw(runner, flaw_type)
        
        # 显示结果
        status = "✅ 成功" if result['success'] else "❌ 失败"
        time_str = f"{result['execution_time']:.2f}s"
        
        if result.get('timeout'):
            status += " (超时)"
        elif result.get('exception'):
            status += " (异常)"
        
        print(f"    {status} - 耗时: {time_str}, 轮数: {result['turns']}")
        
        if result.get('error') and not result['success']:
            print(f"    错误: {result['error'][:100]}...")
        
        results.append(result)
    
    # 总结
    print("\n" + "="*70)
    print("测试总结")
    print("="*70)
    
    success_count = sum(1 for r in results if r['success'])
    timeout_count = sum(1 for r in results if r.get('timeout'))
    exception_count = sum(1 for r in results if r.get('exception'))
    
    print(f"\n总体结果: {success_count}/{len(results)} 成功")
    
    if timeout_count > 0:
        print(f"  - 超时: {timeout_count} 个")
    if exception_count > 0:
        print(f"  - 异常: {exception_count} 个")
    
    # 详细统计
    print("\n详细统计:")
    print("-" * 50)
    print(f"{'缺陷类型':<25} {'结果':<10} {'耗时':<10} {'轮数':<10}")
    print("-" * 50)
    
    for result in results:
        status = "成功" if result['success'] else "失败"
        if result.get('timeout'):
            status += "(超时)"
        elif result.get('exception'):
            status += "(异常)"
        
        print(f"{result['flaw_type']:<25} {status:<10} "
              f"{result['execution_time']:<10.2f} {result['turns']:<10}")
    
    # 平均执行时间
    avg_time = sum(r['execution_time'] for r in results) / len(results)
    print(f"\n平均执行时间: {avg_time:.2f}秒")
    
    # 保存结果
    output_file = Path('flaw_test_results.json')
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'summary': {
                'total': len(results),
                'success': success_count,
                'timeout': timeout_count,
                'exception': exception_count,
                'avg_execution_time': avg_time
            },
            'results': results
        }, f, indent=2)
    
    print(f"\n详细结果已保存到: {output_file}")
    
    # 最终判断
    print("\n" + "="*70)
    if success_count == len(results):
        print("✅ 所有缺陷类型测试通过！")
    elif success_count >= len(results) * 0.8:
        print("⚠️  大部分测试通过，但仍有一些问题需要关注")
    else:
        print("❌ 多个缺陷类型测试失败，需要进一步调查")
    print("="*70)

if __name__ == "__main__":
    main()