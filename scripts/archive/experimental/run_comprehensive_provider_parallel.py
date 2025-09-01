#!/usr/bin/env python3
"""
Comprehensive Provider-Parallel Batch Testing
=============================================
利用提供商级别速率限制优化的综合批测试脚本
"""

import sys
import json
import time
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))

from batch_test_runner import TestTask
from provider_parallel_runner import ProviderParallelRunner
from api_client_manager import MODEL_PROVIDER_MAP, SUPPORTED_MODELS


def load_database(db_path="pilot_bench_cumulative_results/master_database.json"):
    """加载测试数据库"""
    if not Path(db_path).exists():
        return {}
    with open(db_path, 'r') as f:
        return json.load(f)


def analyze_missing_tests(models: List[str] = None, 
                         prompt_types: List[str] = None,
                         task_types: List[str] = None,
                         difficulties: List[str] = None,
                         target_instances: int = 20) -> Dict:
    """
    分析缺失的测试
    
    Returns:
        缺失测试的详细信息
    """
    if models is None:
        models = SUPPORTED_MODELS
    if prompt_types is None:
        prompt_types = ['baseline', 'cot', 'optimal', 'flawed']
    if task_types is None:
        task_types = ['simple_task', 'basic_task', 'data_pipeline', 
                     'api_integration', 'multi_stage_pipeline']
    if difficulties is None:
        difficulties = ['easy', 'medium', 'hard']
    
    db = load_database()
    missing_tests = defaultdict(lambda: defaultdict(list))
    total_missing = 0
    
    # 检查每个组合
    for model in models:
        if model not in SUPPORTED_MODELS:
            continue
            
        model_data = db.get('models', {}).get(model, {})
        
        for prompt_type in prompt_types:
            # 处理flawed类型
            if prompt_type == 'flawed':
                flaw_types = ['sequence_disorder', 'tool_misuse', 'parameter_error', 
                            'missing_step', 'redundant_operations', 
                            'logical_inconsistency', 'semantic_drift']
                for flaw_type in flaw_types:
                    full_prompt = f'flawed_{flaw_type}'
                    for difficulty in difficulties:
                        for task_type in task_types:
                            # 检查已完成数量
                            completed = 0
                            if 'by_prompt_type' in model_data:
                                prompt_data = model_data.get('by_prompt_type', {}).get('flawed', {})
                                if 'by_tool_success_rate' in prompt_data:
                                    for rate_data in prompt_data['by_tool_success_rate'].values():
                                        diff_data = rate_data.get('by_difficulty', {}).get(difficulty, {})
                                        task_data = diff_data.get('by_task_type', {}).get(task_type, {})
                                        if task_data.get('flaw_type') == flaw_type:
                                            completed += task_data.get('total', 0)
                            
                            needed = max(0, target_instances - completed)
                            if needed > 0:
                                missing_tests[model][full_prompt].append({
                                    'difficulty': difficulty,
                                    'task_type': task_type,
                                    'needed': needed,
                                    'completed': completed
                                })
                                total_missing += needed
            else:
                # 常规prompt类型
                for difficulty in difficulties:
                    for task_type in task_types:
                        # 检查已完成数量
                        completed = 0
                        if 'by_prompt_type' in model_data:
                            prompt_data = model_data.get('by_prompt_type', {}).get(prompt_type, {})
                            if 'by_tool_success_rate' in prompt_data:
                                for rate_data in prompt_data['by_tool_success_rate'].values():
                                    diff_data = rate_data.get('by_difficulty', {}).get(difficulty, {})
                                    task_data = diff_data.get('by_task_type', {}).get(task_type, {})
                                    completed += task_data.get('total', 0)
                        
                        needed = max(0, target_instances - completed)
                        if needed > 0:
                            missing_tests[model][prompt_type].append({
                                'difficulty': difficulty,
                                'task_type': task_type,
                                'needed': needed,
                                'completed': completed
                            })
                            total_missing += needed
    
    return {
        'missing_tests': dict(missing_tests),
        'total_missing': total_missing,
        'models_with_missing': len(missing_tests),
        'target_instances': target_instances
    }


def create_test_tasks_from_analysis(analysis: Dict, 
                                   max_tasks_per_model: int = None,
                                   priority_models: List[str] = None) -> List[TestTask]:
    """
    根据分析结果创建测试任务
    
    Args:
        analysis: 缺失测试分析结果
        max_tasks_per_model: 每个模型的最大任务数
        priority_models: 优先测试的模型列表
        
    Returns:
        测试任务列表
    """
    tasks = []
    missing_tests = analysis['missing_tests']
    
    # 如果指定了优先模型，先处理这些
    if priority_models:
        for model in priority_models:
            if model in missing_tests:
                model_tasks = _create_model_tasks(model, missing_tests[model], max_tasks_per_model)
                tasks.extend(model_tasks)
        
        # 然后处理其他模型
        for model in missing_tests:
            if model not in priority_models:
                model_tasks = _create_model_tasks(model, missing_tests[model], max_tasks_per_model)
                tasks.extend(model_tasks)
    else:
        # 按提供商分组，优化并行
        provider_groups = defaultdict(list)
        for model in missing_tests:
            provider = MODEL_PROVIDER_MAP.get(model, 'idealab')
            provider_groups[provider].append(model)
        
        # 交替从不同提供商选择模型，实现负载均衡
        while any(provider_groups.values()):
            for provider in ['azure', 'user_azure', 'idealab']:
                if provider_groups[provider]:
                    model = provider_groups[provider].pop(0)
                    model_tasks = _create_model_tasks(model, missing_tests[model], max_tasks_per_model)
                    tasks.extend(model_tasks)
    
    return tasks


def _create_model_tasks(model: str, prompt_configs: Dict, max_tasks: int = None) -> List[TestTask]:
    """为单个模型创建测试任务"""
    tasks = []
    task_count = 0
    
    for prompt_type, configs in prompt_configs.items():
        is_flawed = prompt_type.startswith('flawed_')
        flaw_type = prompt_type.replace('flawed_', '') if is_flawed else None
        
        for config in configs:
            needed = config['needed']
            if max_tasks and task_count + needed > max_tasks:
                needed = max_tasks - task_count
            
            for _ in range(needed):
                task = TestTask(
                    model=model,
                    task_type=config['task_type'],
                    prompt_type='flawed' if is_flawed else prompt_type,
                    difficulty=config['difficulty'],
                    is_flawed=is_flawed,
                    flaw_type=flaw_type,
                    tool_success_rate=0.8
                )
                tasks.append(task)
                task_count += 1
                
                if max_tasks and task_count >= max_tasks:
                    return tasks
    
    return tasks


def run_comprehensive_test(models: List[str] = None,
                          prompt_types: List[str] = None,
                          difficulties: List[str] = None,
                          task_types: List[str] = None,
                          target_instances: int = 20,
                          max_tasks: int = None,
                          dry_run: bool = False):
    """
    运行综合测试
    
    Args:
        models: 要测试的模型列表
        prompt_types: 提示类型列表
        difficulties: 难度列表
        task_types: 任务类型列表
        target_instances: 每个组合的目标实例数
        max_tasks: 最大任务数限制
        dry_run: 仅分析不执行
    """
    print("="*70)
    print("🎯 综合提供商并行批测试")
    print("="*70)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 分析缺失测试
    print("\n📊 分析缺失测试...")
    analysis = analyze_missing_tests(
        models=models,
        prompt_types=prompt_types,
        task_types=task_types,
        difficulties=difficulties,
        target_instances=target_instances
    )
    
    print(f"\n📈 分析结果:")
    print(f"  需要测试的模型数: {analysis['models_with_missing']}")
    print(f"  总缺失测试数: {analysis['total_missing']}")
    print(f"  目标实例数: {analysis['target_instances']}")
    
    if analysis['total_missing'] == 0:
        print("\n✅ 所有测试已完成！")
        return
    
    # 显示详细缺失信息
    print("\n📋 缺失测试详情:")
    for model, prompts in analysis['missing_tests'].items():
        provider = MODEL_PROVIDER_MAP.get(model, 'idealab')
        model_total = sum(
            sum(c['needed'] for c in configs)
            for configs in prompts.values()
        )
        print(f"\n  {model} ({provider}): {model_total} 个测试")
        for prompt_type, configs in prompts.items():
            prompt_total = sum(c['needed'] for c in configs)
            print(f"    {prompt_type}: {prompt_total} 个")
    
    if dry_run:
        print("\n🔍 试运行模式，不执行实际测试")
        return
    
    # 创建测试任务
    print("\n📝 创建测试任务...")
    tasks = create_test_tasks_from_analysis(analysis, max_tasks_per_model=max_tasks)
    
    if max_tasks and len(tasks) > max_tasks:
        tasks = tasks[:max_tasks]
        print(f"⚠️ 限制任务数到 {max_tasks}")
    
    print(f"✅ 创建了 {len(tasks)} 个测试任务")
    
    # 按提供商统计
    provider_counts = defaultdict(int)
    for task in tasks:
        provider = MODEL_PROVIDER_MAP.get(task.model, 'idealab')
        provider_counts[provider] += 1
    
    print("\n📊 任务分布（按提供商）:")
    for provider, count in provider_counts.items():
        print(f"  {provider}: {count} 个任务")
    
    # 估算时间
    print("\n⏱️ 时间估算:")
    serial_time = len(tasks) * 10  # 假设每个测试10秒
    print(f"  串行执行: ~{serial_time}秒 ({serial_time/60:.1f}分钟)")
    
    # 并行时间估算
    if len(provider_counts) > 1:
        # 最慢的提供商决定总时间
        idealab_tasks = provider_counts.get('idealab', 0)
        azure_tasks = provider_counts.get('azure', 0)
        user_azure_tasks = provider_counts.get('user_azure', 0)
        
        # 各提供商的预计时间
        idealab_time = idealab_tasks * 10 / 3  # IdealLab 3个并发
        azure_time = azure_tasks * 10 / 50  # Azure 50个并发
        user_azure_time = user_azure_tasks * 10 / 30  # User Azure 30个并发
        
        parallel_time = max(idealab_time, azure_time, user_azure_time)
    else:
        # 单提供商
        provider = list(provider_counts.keys())[0]
        if provider == 'idealab':
            parallel_time = len(tasks) * 10 / 3
        elif provider == 'azure':
            parallel_time = len(tasks) * 10 / 50
        else:
            parallel_time = len(tasks) * 10 / 30
    
    print(f"  并行执行: ~{parallel_time}秒 ({parallel_time/60:.1f}分钟)")
    print(f"  预期加速: {serial_time/parallel_time:.1f}x")
    
    # 确认执行
    print("\n" + "="*70)
    response = input("是否开始执行？(y/n): ")
    if response.lower() != 'y':
        print("取消执行")
        return
    
    # 执行测试
    print("\n🚀 开始执行测试...")
    start_time = time.time()
    
    runner = ProviderParallelRunner(
        debug=False,
        silent=False,
        save_logs=True,
        use_ai_classification=False
    )
    
    results, stats = runner.run_parallel_by_provider(tasks)
    
    actual_time = time.time() - start_time
    
    # 显示结果
    print("\n" + "="*70)
    print("📊 测试完成")
    print("="*70)
    
    print(f"\n⏱️ 实际执行时间: {actual_time:.1f}秒 ({actual_time/60:.1f}分钟)")
    print(f"📈 实际加速比: {serial_time/actual_time:.2f}x")
    
    # 保存结果到数据库
    print("\n💾 保存结果到数据库...")
    for model in set(t.model for t in tasks):
        model_results = [r for r in results if r and r.get('model') == model]
        if model_results:
            runner.save_results_to_database(model_results, model, 'mixed')
    
    print("\n✅ 批测试完成！")


def main():
    parser = argparse.ArgumentParser(description='综合提供商并行批测试')
    parser.add_argument('--models', type=str, help='模型列表（逗号分隔），默认所有支持的模型')
    parser.add_argument('--prompt-types', type=str, help='提示类型（逗号分隔），默认所有类型')
    parser.add_argument('--difficulties', type=str, default='easy', help='难度级别（逗号分隔）')
    parser.add_argument('--task-types', type=str, help='任务类型（逗号分隔），默认所有类型')
    parser.add_argument('--target-instances', type=int, default=20, help='每个组合的目标实例数')
    parser.add_argument('--max-tasks', type=int, help='最大任务数限制')
    parser.add_argument('--dry-run', action='store_true', help='仅分析不执行')
    
    args = parser.parse_args()
    
    # 解析参数
    models = [m.strip() for m in args.models.split(',')] if args.models else None
    prompt_types = [p.strip() for p in args.prompt_types.split(',')] if args.prompt_types else None
    difficulties = [d.strip() for d in args.difficulties.split(',')] if args.difficulties else ['easy']
    task_types = [t.strip() for t in args.task_types.split(',')] if args.task_types else None
    
    # 运行测试
    run_comprehensive_test(
        models=models,
        prompt_types=prompt_types,
        difficulties=difficulties,
        task_types=task_types,
        target_instances=args.target_instances,
        max_tasks=args.max_tasks,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()