#!/usr/bin/env python3
"""
Multi-Model Provider-Parallel Test
===================================
测试多模型并行执行，利用提供商级别的速率限制
"""

import sys
import time
import argparse
from pathlib import Path
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent))

from batch_test_runner import TestTask
from provider_parallel_runner import ProviderParallelRunner
from api_client_manager import MODEL_PROVIDER_MAP


def run_multi_model_test(models: List[str], num_tests_per_model: int = 5,
                         task_types: List[str] = None, prompt_type: str = 'baseline',
                         difficulty: str = 'easy', tool_success_rate: float = 0.8):
    """
    运行多模型并行测试
    
    Args:
        models: 模型列表
        num_tests_per_model: 每个模型的测试数
        task_types: 任务类型列表
        prompt_type: 提示类型
        difficulty: 难度
        tool_success_rate: 工具成功率
    """
    if task_types is None:
        task_types = ['simple_task', 'basic_task']
    
    print("="*70)
    print("🚀 多模型提供商并行测试")
    print("="*70)
    
    # 按提供商分组模型
    provider_models = {}
    for model in models:
        provider = MODEL_PROVIDER_MAP.get(model, 'idealab')
        if provider not in provider_models:
            provider_models[provider] = []
        provider_models[provider].append(model)
    
    print("\n📊 模型分布:")
    for provider, pmodels in provider_models.items():
        print(f"  {provider}: {', '.join(pmodels)}")
    
    # 创建所有测试任务
    all_tasks = []
    for model in models:
        for task_type in task_types:
            for i in range(num_tests_per_model):
                task = TestTask(
                    model=model,
                    task_type=task_type,
                    prompt_type=prompt_type,
                    difficulty=difficulty,
                    tool_success_rate=tool_success_rate
                )
                all_tasks.append(task)
    
    total_tasks = len(all_tasks)
    print(f"\n📝 总任务数: {total_tasks}")
    print(f"   = {len(models)} 模型 × {len(task_types)} 任务类型 × {num_tests_per_model} 实例")
    
    # 估算时间
    print("\n⏱️ 时间估算:")
    # 串行时间（假设每个测试10秒）
    serial_time = total_tasks * 10
    print(f"  串行执行: ~{serial_time}秒 ({serial_time/60:.1f}分钟)")
    
    # 并行时间估算（基于提供商）
    if len(provider_models) > 1:
        # 跨提供商可以完全并行
        max_provider_tasks = max(
            len([t for t in all_tasks if MODEL_PROVIDER_MAP.get(t.model, 'idealab') == p])
            for p in provider_models.keys()
        )
        if 'idealab' in provider_models and len(provider_models['idealab']) > 1:
            # IdealLab内部需要限制并发
            idealab_tasks = len([t for t in all_tasks if MODEL_PROVIDER_MAP.get(t.model, 'idealab') == 'idealab'])
            idealab_time = idealab_tasks * 10 / 2  # 假设2个并发
            parallel_time = max(idealab_time, max_provider_tasks * 10 / 5)  # 其他提供商5个并发
        else:
            parallel_time = max_provider_tasks * 10 / 5  # 5个并发
    else:
        # 单提供商
        if 'idealab' in provider_models:
            parallel_time = total_tasks * 10 / 2  # IdealLab限制为2个并发
        else:
            parallel_time = total_tasks * 10 / 5  # 其他提供商5个并发
    
    print(f"  并行执行: ~{parallel_time}秒 ({parallel_time/60:.1f}分钟)")
    print(f"  预期加速: {serial_time/parallel_time:.1f}x")
    
    # 运行测试
    print("\n" + "="*70)
    print("🏃 开始执行...")
    print("="*70)
    
    start_time = time.time()
    
    # 使用提供商并行运行器
    runner = ProviderParallelRunner(
        debug=False,
        silent=False,
        save_logs=True,
        use_ai_classification=False
    )
    
    results, stats = runner.run_parallel_by_provider(all_tasks)
    
    actual_time = time.time() - start_time
    
    # 分析结果
    print("\n" + "="*70)
    print("📊 测试结果分析")
    print("="*70)
    
    print(f"\n⏱️ 实际执行时间: {actual_time:.1f}秒 ({actual_time/60:.1f}分钟)")
    print(f"📈 实际加速比: {serial_time/actual_time:.2f}x")
    
    # 按模型统计
    print("\n📊 按模型统计:")
    for model in models:
        model_results = [r for r in results if r and r.get('model') == model]
        success = sum(1 for r in model_results if r.get('success', False))
        total = len(model_results)
        if total > 0:
            print(f"  {model}: {success}/{total} 成功 ({success/total*100:.1f}%)")
    
    # 按任务类型统计
    print("\n📊 按任务类型统计:")
    for task_type in task_types:
        task_results = [r for r in results if r and r.get('task_type') == task_type]
        success = sum(1 for r in task_results if r.get('success', False))
        total = len(task_results)
        if total > 0:
            print(f"  {task_type}: {success}/{total} 成功 ({success/total*100:.1f}%)")
    
    return results, stats


def main():
    parser = argparse.ArgumentParser(description='多模型提供商并行测试')
    parser.add_argument('--models', type=str, default='gpt-4o-mini,qwen2.5-3b-instruct,DeepSeek-V3-671B',
                       help='要测试的模型列表（逗号分隔）')
    parser.add_argument('--num-tests', type=int, default=5,
                       help='每个模型的测试数量')
    parser.add_argument('--task-types', type=str, default='simple_task,basic_task',
                       help='任务类型列表（逗号分隔）')
    parser.add_argument('--prompt-type', type=str, default='baseline',
                       help='提示类型')
    parser.add_argument('--difficulty', type=str, default='easy',
                       help='难度级别')
    parser.add_argument('--tool-success-rate', type=float, default=0.8,
                       help='工具成功率')
    
    args = parser.parse_args()
    
    # 解析模型列表
    models = [m.strip() for m in args.models.split(',') if m.strip()]
    task_types = [t.strip() for t in args.task_types.split(',') if t.strip()]
    
    if not models:
        print("❌ 请指定至少一个模型")
        sys.exit(1)
    
    # 运行测试
    run_multi_model_test(
        models=models,
        num_tests_per_model=args.num_tests,
        task_types=task_types,
        prompt_type=args.prompt_type,
        difficulty=args.difficulty,
        tool_success_rate=args.tool_success_rate
    )


if __name__ == "__main__":
    main()