#!/usr/bin/env python3
"""
智能批测试运行器 - 增强版
保持原有接口，但内部使用BatchTestRunner以获得完整功能
支持缓存模式避免并发竞争条件
新增：自动失败维护和基于进度的增量重测
"""
import json
import os
import sys
import subprocess
import argparse
import tempfile
import shutil
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime
import time

sys.path.insert(0, str(Path(__file__).parent))
from batch_test_runner import BatchTestRunner, TestTask
# 支持存储格式选择
import os
storage_format = os.environ.get('STORAGE_FORMAT', 'json').lower()

# 可选支持ResultCollector
try:
    from result_collector import ResultCollector
    from result_collector_adapter import AdaptiveResultCollector
    RESULT_COLLECTOR_AVAILABLE = True
except ImportError:
    RESULT_COLLECTOR_AVAILABLE = False
if storage_format == 'parquet':
    try:
        from parquet_cumulative_manager import ParquetCumulativeManager as EnhancedCumulativeManager
        print(f"[INFO] 使用Parquet存储格式")
    except ImportError as e:
        print(f"[WARNING] Parquet导入失败: {e}")
        from enhanced_cumulative_manager import EnhancedCumulativeManager
        print(f"[INFO] 回退到JSON存储格式")
else:
    from enhanced_cumulative_manager import EnhancedCumulativeManager
    print(f"[INFO] 使用JSON存储格式")
# TestRecord总是从cumulative_test_manager导入
from cumulative_test_manager import TestRecord
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from collections import defaultdict
import threading
from api_client_manager import MODEL_PROVIDER_MAP
from database_utils import load_database, get_completed_count

# 全局manager实例缓存，避免重复创建导致缓存丢失
# 这是关键修复：Parquet格式需要累积缓存才能正确保存汇总数据
_global_manager_cache = {}
_manager_lock = threading.Lock()

def _get_or_create_manager(use_ai_classification=False, result_suffix=''):
    """获取或创建manager实例（单例模式）"""
    cache_key = f"{use_ai_classification}_{result_suffix}"
    
    with _manager_lock:
        if cache_key not in _global_manager_cache:
            # 创建新的manager实例
            _global_manager_cache[cache_key] = EnhancedCumulativeManager(
                use_ai_classification=use_ai_classification, 
                db_suffix=result_suffix
            )
            print(f"[DEBUG] 创建新的manager实例: key={cache_key}")
        
        return _global_manager_cache[cache_key]

def _flush_all_managers():
    """刷新所有manager的缓存到磁盘"""
    with _manager_lock:
        for cache_key, manager in _global_manager_cache.items():
            if hasattr(manager, '_flush_buffer'):
                manager._flush_buffer()
                print(f"[INFO] 刷新manager缓存: key={cache_key}")

# 注册退出时的清理函数
import atexit
atexit.register(_flush_all_managers)

def _save_results_to_database(results, model, difficulty, use_ai_classification=False, result_suffix=''):
    """保存测试结果到数据库"""
    if not results:
        return 0
    
    # 使用单例manager，避免重复创建导致缓存丢失
    # 这是关键修复：确保Parquet格式能累积缓存
    manager = _get_or_create_manager(use_ai_classification=use_ai_classification, result_suffix=result_suffix)
    success_commit = 0
    
    for result in results:
        if result and not result.get('_saved', False):
            record = TestRecord(
                model=model,
                task_type=result.get("task_type", "unknown"),
                prompt_type=result.get("prompt_type", "baseline"),
                difficulty=result.get("difficulty", difficulty)
            )
            # 设置其他字段
            for field in ['timestamp', 'success', 'success_level', 'execution_time', 'turns', 
                        'tool_calls', 'workflow_score', 'phase2_score', 'quality_score', 
                        'final_score', 'error_type', 'tool_success_rate', 'is_flawed', 
                        'flaw_type', 'format_error_count', 'api_issues', 'executed_tools', 
                        'required_tools', 'tool_coverage_rate', 'task_instance', 'execution_history']:
                if field in result:
                    setattr(record, field, result[field])
            
            try:
                manager.add_test_result_with_classification(record)
                result['_saved'] = True  # 标记已保存
                success_commit += 1
            except Exception as e:
                print(f"⚠️  提交失败: {e}")
    
    # 定期刷新缓冲区（每10个结果刷新一次，避免频繁IO）
    # 对于Parquet格式这很重要，因为需要累积一定数量才值得写入
    if success_commit > 0 and success_commit % 10 == 0:
        if hasattr(manager, '_flush_buffer'):
            manager._flush_buffer()
            print(f"[INFO] 刷新缓存到磁盘 (已累积{success_commit}个结果)")
    
    if success_commit > 0:
        print(f"✅ 已保存 {success_commit} 个测试结果到数据库")
        # 最后再刷新一次，确保所有数据都写入
        if hasattr(manager, '_flush_buffer'):
            manager._flush_buffer()
    
    return success_commit

# load_database函数已移动到database_utils.py

def get_incomplete_tests_for_model(model: str) -> Dict[str, List[Dict]]:
    """获取指定模型未完成的测试配置"""
    # 避免循环导入，在函数内部导入
    from auto_failure_maintenance_system import AutoFailureMaintenanceSystem
    maintenance_system = AutoFailureMaintenanceSystem(enable_auto_retry=False)
    incomplete_tests = maintenance_system.get_incomplete_tests([model])
    return incomplete_tests.get(model, [])

# get_completed_count函数已移动到database_utils.py

def run_batch_test_smart(model: str, prompt_types: str, difficulty: str, 
                         task_types: str, num_instances: int, deployment: str = None,
                         adaptive: bool = True, tool_success_rate: float = 0.8, 
                         batch_commit: bool = True, checkpoint_interval: int = 10, 
                         use_provider_parallel: bool = False, 
                         use_result_collector: bool = None, **kwargs):
    """
    智能运行批测试，自动计算需要补充的测试数量
    保持原有接口，但使用BatchTestRunner执行
    支持batch_commit批量提交避免并发竞争
    支持checkpoint_interval中间保存（每N个测试保存一次）
    支持多prompt types并行执行
    """
    # 解析prompt types - 支持多个prompt types
    if prompt_types == "all":
        prompt_list = ["baseline", "cot", "optimal"]
    elif prompt_types == "all_with_flawed":
        prompt_list = ["baseline", "cot", "optimal"] + [
            f"flawed_{ft}" for ft in [
                "sequence_disorder", "tool_misuse", "parameter_error",
                "missing_step", "redundant_operations", 
                "logical_inconsistency", "semantic_drift"
            ]
        ]
    elif "," in prompt_types:
        # 支持逗号分隔的多个prompt types
        prompt_list = [p.strip() for p in prompt_types.split(",")]
    else:
        # 单个prompt type
        prompt_list = [prompt_types]
    
    # 解析任务类型
    if task_types == "all":
        task_list = ["simple_task", "basic_task", "data_pipeline", 
                    "api_integration", "multi_stage_pipeline"]
    else:
        task_list = task_types.split(",")
    
    # 判断是否应该使用多prompt并行
    use_prompt_parallel = len(prompt_list) > 1 and kwargs.get('prompt_parallel', True)
    provider = MODEL_PROVIDER_MAP.get(model, 'idealab')
    silent = kwargs.get('silent', False)
    
    if not silent:
        print(f"\n{'='*60}")
        print(f"智能批测试: {model} ({provider})")
        print(f"Prompt types: {prompt_list}")
        print(f"难度: {difficulty}")
        print(f"目标: 每种配置 {num_instances} 个实例")
        if use_prompt_parallel:
            if provider in ['azure', 'user_azure']:
                print(f"策略: 所有{len(prompt_list)}个prompt types同时并行（高并发）")
            else:
                print(f"策略: {len(prompt_list)}个prompt types使用不同API keys并行")
        print(f"{'='*60}")
    
    # 如果使用多prompt并行，直接构建所有任务
    if use_prompt_parallel:
        return _run_multi_prompt_parallel(
            model=model,
            prompt_list=prompt_list,
            task_list=task_list,
            difficulty=difficulty,
            num_instances=num_instances,
            tool_success_rate=tool_success_rate,
            provider=provider,
            adaptive=adaptive,
            batch_commit=batch_commit,
            checkpoint_interval=checkpoint_interval,
            deployment=deployment,
            **kwargs
        )
    
    # 单prompt type的原有逻辑
    prompt_type = prompt_list[0]
    
    # 检查每种任务类型的完成情况
    total_needed = 0
    tasks_to_run = []
    
    # 判断是否是缺陷测试
    is_flawed = prompt_type.startswith("flawed_")
    flaw_type = prompt_type.replace("flawed_", "") if is_flawed else None
    
    for task_type in task_list:
        completed = get_completed_count(model, prompt_type, difficulty, task_type, tool_success_rate)
        needed = max(0, num_instances - completed)
        total_needed += needed
        
        status_symbol = "✓" if needed == 0 else "○"
        if not silent:
            print(f"{status_symbol} {task_type:20s}: {completed:3d}/{num_instances:3d} 已完成", end="")
            if needed > 0:
                print(f" (需要补充 {needed} 个)")
            else:
                print(" [跳过]")
        
        if needed > 0:
            # 记录需要运行的任务
            tasks_to_run.append({
                'task_type': task_type,
                'count': needed
            })
    
    if total_needed == 0:
        if not silent:
            print(f"\n✅ 所有测试已完成，跳过此配置")
        return True
    
    if not silent:
        print(f"\n⏳ 需要运行 {total_needed} 个新测试")
    
    # 构建所有测试任务
    all_tasks = []
    for task_info in tasks_to_run:
        task_type = task_info['task_type']
        count = task_info['count']
        
        if not silent:
            print(f"\n▶ 准备 {task_type} ({count} 个实例)...")
        
        for _ in range(count):
            task = TestTask(
                model=model,  # 保持原始大小写，normalize会在存储时处理
                deployment=deployment,  # API调用用的部署名
                task_type=task_type,
                prompt_type=prompt_type,  # 保持原始的prompt_type，不要简化
                difficulty=difficulty,
                is_flawed=is_flawed,
                flaw_type=flaw_type,
                tool_success_rate=tool_success_rate
            )
            all_tasks.append(task)
    
    # 运行批量测试
    if not silent:
        print(f"\n▶ 开始执行 {len(all_tasks)} 个测试...")
    
    # 智能checkpoint_interval处理
    if batch_commit:
        if checkpoint_interval is None:
            # 根据测试规模自动调整
            if num_instances <= 5:
                checkpoint_interval = max(1, num_instances)  # 小规模测试使用小阈值
            else:
                checkpoint_interval = min(10, num_instances // 2)  # 大规模测试使用适中阈值
        
        if not silent:
            print(f"📊 自适应checkpoint_interval: {checkpoint_interval}")
            if checkpoint_interval > 0:
                print(f"📦 批量提交模式：每{checkpoint_interval}个测试保存一次")
            else:
                print("📦 批量提交模式：测试完成后统一写入数据库")
    
    save_logs = kwargs.get('save_logs', True)
    workers = kwargs.get('max_workers', 10)
    qps = kwargs.get('qps', 20.0)
    use_ai_classification = kwargs.get('ai_classification', True)  # 获取AI分类参数
    
    # 如果使用基于提供商的并行策略
    if use_provider_parallel:
        if not silent:
            print("\n🚀 使用基于API提供商的并行策略（集成版）")
        
        # 按提供商分组任务
        provider_tasks = defaultdict(list)
        for task in all_tasks:
            provider = MODEL_PROVIDER_MAP.get(task.model, 'idealab')
            provider_tasks[provider].append(task)
        
        if not silent:
            print(f"\n📦 任务分布：")
            for provider, tasks in provider_tasks.items():
                print(f"  {provider}: {len(tasks)} 个任务")
        
        # 设置提供商级别的并发参数
        provider_configs = {
            'azure': {'max_workers': 100, 'initial_qps': 200.0},  # 提高到100 workers，支持20*5一次性完成
            'user_azure': {'max_workers': 50, 'initial_qps': 100.0},  # 也相应提高
            'idealab': {'max_workers': 24, 'initial_qps': 30.0}  # 3 keys × 8 并发
        }
        
        all_results = []
        
        # 并行运行不同提供商的任务
        with ProcessPoolExecutor(max_workers=len(provider_tasks)) as executor:
            futures = []
            
            for provider, tasks in provider_tasks.items():
                config = provider_configs.get(provider, {'max_workers': 10, 'initial_qps': 20.0})
                
                # 创建专门的runner
                future = executor.submit(
                    _run_provider_tasks,
                    tasks,
                    config['max_workers'],
                    config['initial_qps'],
                    adaptive,
                    save_logs,
                    silent,
                    not batch_commit,
                    kwargs.get('ai_classification', True),
                    checkpoint_interval if batch_commit else 0
                )
                futures.append((provider, future))
            
            # 收集结果
            for provider, future in futures:
                try:
                    provider_results = future.result()
                    all_results.extend(provider_results)
                    if not silent:
                        print(f"\n✅ {provider} 提供商任务完成：{len(provider_results)} 个结果")
                except Exception as e:
                    if not silent:
                        print(f"\n❌ {provider} 提供商任务失败：{e}")
        
        # 统计结果
        success_count = sum(1 for r in all_results if r and r.get('success', False))
        if not silent:
            print(f"\n✅ 所有任务完成")
            print(f"   成功: {success_count}/{len(all_results)}")
            print(f"   失败: {len(all_results) - success_count}/{len(all_results)}")
        
        # 保存结果
        if batch_commit and all_results:
            unsaved_results = [r for r in all_results if r and not r.get('_saved', False)]
            if unsaved_results:
                if not silent:
                    print(f"\n📤 保存{len(unsaved_results)}个测试结果...")
                _save_results_to_database(unsaved_results, model, difficulty, kwargs.get('ai_classification', True), kwargs.get('result_suffix', ''))
        
        return True
    
    # 根据模型和模式调整参数
    if any(x in model.lower() for x in ['qwen', 'llama-4-scout', 'o1']):
        # IdealLab API: 适度保守但不要太保守
        if adaptive:
            workers = min(workers, 5)  # 提高到5
            qps = None  # 移除QPS限制
        else:
            # 非adaptive模式也可以稍微激进一点
            workers = 2  # 优化：降为2，避免过载idealab API
            qps = None  # 移除QPS限制
        if not silent:
            print(f"⚠️  检测到idealab API，调整并发: workers={workers}, qps={qps}")
    elif any(x in model.lower() for x in ['deepseek', 'llama-3.3', 'gpt-4o-mini', 'gpt-5']):
        # Azure API: 非常激进，支持100并发一次性完成20*5测试
        if adaptive:
            workers = max(workers, 100)  # 直接从100开始，支持20*5一次性并行
            qps = None  # 移除QPS限制
        else:
            # 非adaptive模式使用固定值，与ultra_parallel_runner.py保持一致
            workers = 50   # 修正：Azure固定模式50 workers
            qps = None     # 移除QPS限制
        if not silent:
            print(f"🚀 检测到Azure API，使用超高并发: workers={workers}, qps={qps}")
    else:
        # 默认模型：也更激进一些
        if not adaptive:
            workers = min(workers, 20)  # 提高到20
            qps = min(qps, 30.0)  # 提高到30
    
    # 检查是否使用ResultCollector模式
    if use_result_collector is None:
        # 从环境变量决定
        use_collector = os.environ.get('USE_RESULT_COLLECTOR', 'false').lower() == 'true'
    else:
        use_collector = use_result_collector
    
        # 创建智能结果收集器
    result_collector = None
    if use_collector:
        try:
            # 尝试使用自适应收集器
            from result_collector_adapter import create_adaptive_collector
            
            # 智能配置（暂时不传入database_manager，稍后在runner创建后设置）
            collector_config = {
                'temp_dir': 'temp_results',
                'max_memory_results': max(5, checkpoint_interval or 5),  # 自适应阈值
                'max_time_seconds': 300,  # 5分钟超时
                'auto_save_interval': 60,  # 1分钟自动保存
                'adaptive_threshold': True
            }
            
            result_collector = create_adaptive_collector(**collector_config)
            
            if not silent:
                print("🧠 启用SmartResultCollector模式，智能数据管理")
        except ImportError:
            # 回退到原始ResultCollector
            try:
                result_collector = ResultCollector()
                if not silent:
                    print("🆕 启用ResultCollector模式，测试完成后统一写入")
            except:
                result_collector = None
                if not silent:
                    print("⚠️ ResultCollector不可用，使用传统模式")
        except Exception as e:
            print(f"⚠️ 智能收集器创建失败，使用传统模式: {e}")
            result_collector = None
    
    # 创建测试运行器
    runner = BatchTestRunner(
        debug=False,
        silent=silent,
        use_adaptive=adaptive,
        save_logs=save_logs,
        enable_database_updates=not use_collector,  # collector模式禁用实时写入
        is_subprocess=True,  # 标记为子进程
        use_ai_classification=use_ai_classification,  # 传递AI分类参数
        idealab_key_index=kwargs.get('idealab_key_index'),  # 传递API key索引
        checkpoint_interval=checkpoint_interval if batch_commit else 0  # 使用用户指定的间隔  # 中间保存间隔
    )
    
    # 如果使用智能收集器，设置database_manager
    if result_collector and hasattr(result_collector, 'set_database_manager'):
        database_manager = getattr(runner, 'manager', None)
        if database_manager:
            result_collector.set_database_manager(database_manager)
            if not silent:
                print("📊 已关联数据库管理器到智能收集器")
    
    try:
        if adaptive:
            results = runner.run_adaptive_concurrent_batch(
                all_tasks, 
                initial_workers=workers, 
                initial_qps=qps
            )
        else:
            results = runner.run_concurrent_batch(
                all_tasks, 
                workers=workers, 
                qps=qps
            )
        
        # 统计结果
        success_count = sum(1 for r in results if r and r.get('success', False))
        if not silent:
            print(f"\n✅ 批测试完成")
            print(f"   成功: {success_count}/{len(results)}")
            print(f"   失败: {len(results) - success_count}/{len(results)}")
        
        # ResultCollector模式：提交结果到收集器
        if result_collector:
            # 使用实际的results，而不是runner.pending_results
            # 因为在collector模式下，runner不会累积pending_results
            pending_results = results if results else getattr(runner, 'pending_results', [])
            if pending_results:
                if not silent:
                    print(f"📤 提交 {len(pending_results)} 个结果到ResultCollector...")
                
                # 添加进程信息
                process_info = {
                    'pid': os.getpid(),
                    'model': model,
                    'prompt_types': prompt_types,
                    'difficulty': difficulty,
                    'task_types': task_types,
                    'workers': workers,
                    'deployment': deployment
                }
                
                result_collector.add_batch_result(model, pending_results, process_info)
                # 只有当我们使用了runner.pending_results时才清空
                if hasattr(runner, 'pending_results'):
                    runner.pending_results = []  # 清空
            else:
                if not silent:
                    print("⚠️ 没有待提交的结果")
        
        # 传统模式：如果是批量提交模式，检查是否有未保存的结果
        elif batch_commit:
            # 获取runner中的pending_results（如果有）
            pending_results = getattr(runner, 'pending_results', [])
            if pending_results:
                if not silent:
                    print(f"\n📤 保存{len(pending_results)}个未提交的测试结果...")
                _save_results_to_database(pending_results, model, difficulty, kwargs.get('ai_classification', True), kwargs.get('result_suffix', ''))
                runner.pending_results = []  # 清空
            
            # 如果还有其他未处理的results
            if results:
                unsaved_results = [r for r in results if r and not r.get('_saved', False)]
                if unsaved_results:
                    if not silent:
                        print(f"\n📤 最终保存{len(unsaved_results)}个测试结果...")
                    _save_results_to_database(unsaved_results, model, difficulty, kwargs.get('ai_classification', True), kwargs.get('result_suffix', ''))
        
        # 强制刷新所有缓冲区，确保数据写入磁盘
        print("\n💾 最终刷新所有缓冲区...")
        _flush_all_managers()
        print("✅ 所有数据已安全写入磁盘")
        
        return True
        
    except Exception as e:
        if not silent:
            print(f"\n✗ 批测试失败: {e}")
            # 显示完整traceback以便调试
            import traceback
            print("完整错误信息:")
            traceback.print_exc()
        return False

def run_auto_maintenance_mode(models: Optional[List[str]] = None) -> bool:
    """
    自动维护模式：分析失败，生成重测计划并执行
    """
    print("🔧 进入自动维护模式...")
    
    # 避免循环导入
    from auto_failure_maintenance_system import AutoFailureMaintenanceSystem
    # 初始化维护系统
    maintenance_system = AutoFailureMaintenanceSystem(enable_auto_retry=True)
    
    # 执行自动维护
    maintenance_result = maintenance_system.auto_maintain_failures()
    
    # 获取未完成的测试
    incomplete_tests = maintenance_system.get_incomplete_tests(models)
    
    if not incomplete_tests:
        print("✅ 所有模型测试完整，无需补充")
        return True
    
    print(f"\n📋 发现 {len(incomplete_tests)} 个模型有未完成测试")
    
    # 生成并执行重测脚本
    total_executed = 0
    for model, configs in incomplete_tests.items():
        print(f"\n▶ 处理模型: {model}")
        
        for config in configs:
            if config["missing_count"] <= 0:
                continue
                
            print(f"  补充 {config['prompt_type']} / {config['task_type']}: {config['missing_count']} 个测试")
            
            # 执行单个配置的补充测试
            success = run_batch_test_smart(
                model=model,
                prompt_types=config["prompt_type"],
                difficulty=config["difficulty"],
                task_types=config["task_type"],
                num_instances=config["missing_count"],
                adaptive=True,
                tool_success_rate=0.8,
                batch_commit=True,
                checkpoint_interval=10,
                max_workers=5,
                save_logs=False,
                silent=True
            )
            
            if success:
                total_executed += config["missing_count"]
                print(f"    ✅ 完成 {config['missing_count']} 个测试")
            else:
                print(f"    ❌ 测试失败")
                # 记录失败
                maintenance_system.failed_manager.record_test_failure(
                    model=model,
                    group_name=f"{config['prompt_type']}_{config['task_type']}",
                    prompt_types=config["prompt_type"],
                    test_type="auto_retest",
                    failure_reason="Auto retest failed"
                )
    
    print(f"\n🎯 自动维护完成，执行了 {total_executed} 个测试")
    return True

def run_incremental_retest_mode(models: Optional[List[str]] = None, 
                               completion_threshold: float = 0.8) -> bool:
    """
    增量重测模式：基于现有进度，只测试缺失的部分
    """
    print(f"🔄 进入增量重测模式（完成率阈值: {completion_threshold:.1%}）...")
    
    # 避免循环导入
    from auto_failure_maintenance_system import AutoFailureMaintenanceSystem
    maintenance_system = AutoFailureMaintenanceSystem(enable_auto_retry=False)
    
    # 分析完成情况
    analysis = maintenance_system.analyze_test_completion(models)
    
    models_to_retest = []
    for model in analysis["models_analyzed"]:
        model_analysis = analysis["completion_summary"][model]
        if (model_analysis.get("status") == "analyzed" and 
            model_analysis.get("completion_rate", 0) < completion_threshold):
            models_to_retest.append(model)
    
    if not models_to_retest:
        print(f"✅ 所有模型完成率都超过 {completion_threshold:.1%}，无需重测")
        return True
    
    print(f"\n📋 需要重测的模型: {models_to_retest}")
    
    # 对每个需要重测的模型执行增量测试
    for model in models_to_retest:
        model_analysis = analysis["completion_summary"][model]
        print(f"\n▶ 重测模型: {model}")
        print(f"   当前完成率: {model_analysis.get('completion_rate', 0):.1%}")
        print(f"   失败率: {model_analysis.get('failure_rate', 0):.1%}")
        
        # 获取该模型的未完成测试
        incomplete_configs = get_incomplete_tests_for_model(model)
        
        for config in incomplete_configs:
            if config["missing_count"] <= 0:
                continue
                
            print(f"    补充: {config['prompt_type']} / {config['task_type']} ({config['missing_count']} 个)")
            
            success = run_batch_test_smart(
                model=model,
                prompt_types=config["prompt_type"],
                difficulty=config["difficulty"],
                task_types=config["task_type"],
                num_instances=config["missing_count"],
                adaptive=True,
                tool_success_rate=0.8,
                batch_commit=True,
                checkpoint_interval=5,
                max_workers=3,
                save_logs=False,
                silent=True
            )
            
            if success:
                print(f"      ✅ 完成")
            else:
                print(f"      ❌ 失败")
    
    print("\n🎯 增量重测完成")
    return True

def main():
    
    # 显示当前存储格式
    
    storage_format = os.environ.get('STORAGE_FORMAT', 'json').upper()
    
    print(f"[INFO] 使用{storage_format}存储格式")
    
    
    parser = argparse.ArgumentParser(description='智能批测试运行器 - 增强版')
    
    # 基本参数
    parser.add_argument('--model', help='模型名称（用于统计）')
    parser.add_argument('--deployment', help='部署实例名（用于API调用，如未指定则使用model）')
    parser.add_argument('--prompt-types', help='Prompt类型(逗号分隔或all)')
    parser.add_argument('--difficulty', default='easy', help='难度')
    parser.add_argument('--task-types', default='all', help='任务类型')
    parser.add_argument('--num-instances', type=int, default=20, help='每种任务的实例数')
    parser.add_argument('--tool-success-rate', type=float, help='工具成功率')
    
    # 运行参数
    parser.add_argument('--max-workers', type=int, default=20, help='最大并发数（Azure模型自动使用50+）')
    parser.add_argument('--adaptive', action='store_true', default=True, help='使用adaptive模式（默认开启）')
    parser.add_argument('--no-adaptive', dest='adaptive', action='store_false', help='禁用adaptive模式')
    parser.add_argument('--save-logs', action='store_true', default=True, help='保存详细日志（默认开启）')
    parser.add_argument('--no-save-logs', dest='save_logs', action='store_false', help='禁用日志保存')
    parser.add_argument('--silent', action='store_true', help='静默模式')
    parser.add_argument('--qps', type=float, default=20.0, help='QPS限制（非adaptive模式下使用）')
    parser.add_argument('--batch-commit', action='store_true', help='批量提交模式避免并发竞争')
    parser.add_argument('--checkpoint-interval', type=int, default=20, help='中间保存间隔(每N个测试保存一次，默认20)')
    parser.add_argument('--ai-classification', dest='ai_classification', action='store_true', default=True, help='启用AI错误分类(使用gpt-5-nano，默认启用)')
    parser.add_argument('--no-ai-classification', dest='ai_classification', action='store_false', help='禁用AI错误分类')
    parser.add_argument('--provider-parallel', action='store_true', help='使用基于API提供商的并行策略(跨提供商并行)')
    parser.add_argument('--prompt-parallel', action='store_true', help='并行运行多个prompt types(Azure直接并行,IdealLab使用不同keys)')
    parser.add_argument('--result-suffix', default='', help='结果文件后缀(用于区分闭源/开源模型)')
    
    # 新增：自动维护模式
    parser.add_argument('--auto-maintain', action='store_true', help='自动维护模式：自动检测失败并重测')
    parser.add_argument('--incremental-retest', action='store_true', help='增量重测模式：基于现有进度补充缺失测试')
    parser.add_argument('--completion-threshold', type=float, default=0.8, help='增量重测的完成率阈值(默认80%%)')
    
    # 新增：IdealLab API key索引
    parser.add_argument('--idealab-key-index', dest='idealab_key_index', type=int, default=None, help='指定使用的IdealLab API key索引(0-1)')
    parser.add_argument('--models', nargs='*', help='指定要处理的模型列表(用于自动维护模式)')
    
    args = parser.parse_args()
    
    # 检查是否进入特殊模式
    if args.auto_maintain:
        print("🔧 启动自动维护模式")
        success = run_auto_maintenance_mode(args.models)
        sys.exit(0 if success else 1)
    
    if args.incremental_retest:
        print("🔄 启动增量重测模式")
        success = run_incremental_retest_mode(args.models, args.completion_threshold)
        sys.exit(0 if success else 1)
    
    # 验证必需参数
    if not args.model or not args.prompt_types:
        print("❌ 常规模式需要指定 --model 和 --prompt-types 参数")
        print("💡 或使用以下特殊模式：")
        print("   --auto-maintain          自动维护模式")
        print("   --incremental-retest     增量重测模式")
        print("")
        print("📖 示例用法：")
        print("   # 常规测试")
        print("   python smart_batch_runner.py --model gpt-4o-mini --prompt-types baseline")
        print("   # 自动维护所有模型")
        print("   python smart_batch_runner.py --auto-maintain")
        print("   # 增量重测特定模型")
        print("   python smart_batch_runner.py --incremental-retest --models gpt-4o-mini claude-3-sonnet")
        sys.exit(1)
    
    # 常规测试模式
    success = run_batch_test_smart(
        model=args.model,
        deployment=args.deployment,  # 新增：传递部署实例名
        prompt_types=args.prompt_types,
        difficulty=args.difficulty,
        task_types=args.task_types,
        num_instances=args.num_instances,
        adaptive=args.adaptive,
        tool_success_rate=args.tool_success_rate if args.tool_success_rate else 0.8,
        batch_commit=args.batch_commit,
        checkpoint_interval=args.checkpoint_interval,
        use_provider_parallel=args.provider_parallel,
        max_workers=args.max_workers,
        save_logs=args.save_logs,
        silent=args.silent,
        qps=args.qps,
        ai_classification=args.ai_classification,
        prompt_parallel=args.prompt_parallel,  # 传递prompt_parallel参数
        result_suffix=args.result_suffix,  # 传递结果文件后缀
        idealab_key_index=args.idealab_key_index  # 传递API key索引
    )
    
    sys.exit(0 if success else 1)

def _run_multi_prompt_parallel(model: str, prompt_list: List[str], task_list: List[str],
                               difficulty: str, num_instances: int, tool_success_rate: float,
                               provider: str, adaptive: bool, batch_commit: bool,
                               checkpoint_interval: int, deployment: str = None, **kwargs):
    """
    并行运行多个prompt types
    Azure模型：所有prompt types同时并行
    IdealLab模型：每个prompt type使用不同的API key并行
    """
    # 构建所有测试任务
    all_tasks = []
    task_groups = {}  # 按prompt_type分组
    
    for prompt_type in prompt_list:
        task_groups[prompt_type] = []
        is_flawed = prompt_type.startswith("flawed_")
        flaw_type = prompt_type.replace("flawed_", "") if is_flawed else None
        
        for task_type in task_list:
            # 检查是否已完成
            completed = get_completed_count(model, prompt_type, difficulty, task_type, tool_success_rate)
            needed = max(0, num_instances - completed)
            
            if needed > 0:
                for _ in range(needed):
                    task = TestTask(
                        model=model,  # 保持原始大小写，normalize会在存储时处理
                        deployment=deployment,  # API调用用的部署名
                        task_type=task_type,
                        prompt_type=prompt_type,  # 保持原始的prompt_type，不要简化
                        difficulty=difficulty,
                        is_flawed=is_flawed,
                        flaw_type=flaw_type,
                        tool_success_rate=tool_success_rate
                    )
                    all_tasks.append(task)
                    task_groups[prompt_type].append(task)
    
    if not all_tasks:
        print(f"\n✅ 所有测试已完成，跳过此配置")
        return True
    
    print(f"\n总计: {len(all_tasks)} 个测试任务")
    for pt, tasks in task_groups.items():
        if tasks:
            print(f"  {pt}: {len(tasks)} 个任务")
    
    # 根据provider决定并行策略
    if provider in ['azure', 'user_azure']:
        # Azure：直接并行所有任务
        return _run_azure_parallel_tasks(all_tasks, model, difficulty, provider, 
                                        adaptive, batch_commit, checkpoint_interval, **kwargs)
    else:
        # IdealLab：按prompt type分组并行
        return _run_idealab_parallel_tasks(task_groups, model, difficulty,
                                          adaptive, batch_commit, checkpoint_interval, **kwargs)

def _run_azure_parallel_tasks(all_tasks: List, model: str, difficulty: str, provider: str,
                              adaptive: bool, batch_commit: bool, checkpoint_interval: int, **kwargs):
    """Azure模型的并行策略：所有prompt types同时运行"""
    # 设置Azure的激进并发参数 - 支持100并发一次性完成20*5测试
    if provider == 'azure':
        max_workers = max(kwargs.get('max_workers', 100), 100)  # 提高到100
        initial_qps = max(kwargs.get('qps', 200.0), 200.0)  # 提高到200
    else:  # user_azure
        max_workers = max(kwargs.get('max_workers', 50), 50)  # 也相应提高
        initial_qps = max(kwargs.get('qps', 100.0), 100.0)
    
    print(f"\n⚡ 使用高并发参数: workers={max_workers}, QPS={initial_qps}")
    
    # 运行批量测试
    runner = BatchTestRunner(
        debug=False,
        silent=kwargs.get('silent', False),
        use_adaptive=adaptive,
        save_logs=kwargs.get('save_logs', True),
        enable_database_updates=True,  # 总是启用数据库更新以防数据丢失
        is_subprocess=True,  # 标记为子进程
        use_ai_classification=kwargs.get('ai_classification', True),  # 传递AI分类参数
        checkpoint_interval=checkpoint_interval if batch_commit else 0  # 使用用户指定的间隔
    )
    
    if adaptive:
        results = runner.run_adaptive_concurrent_batch(
            all_tasks,
            initial_workers=max_workers,
            initial_qps=initial_qps
        )
    else:
        results = runner.run_concurrent_batch(
            all_tasks,
            workers=max_workers,
            qps=initial_qps
        )
    
    # 统计结果
    success_count = sum(1 for r in results if r and r.get('success', False))
    print(f"\n✅ 批测试完成")
    print(f"   成功: {success_count}/{len(results)}")
    print(f"   失败: {len(results) - success_count}/{len(results)}")
    
    # 保存结果（无论是否batch_commit）
    unsaved_results = [r for r in results if r and not r.get('_saved', False)]
    if unsaved_results:
        if not batch_commit:
            print(f"\n📤 自动保存{len(unsaved_results)}个测试结果...")
        else:
            print(f"\n📤 批量保存{len(unsaved_results)}个测试结果...")
            _save_results_to_database(unsaved_results, model, difficulty, 
                                    kwargs.get('ai_classification', True),
                                    kwargs.get('result_suffix', ''))
    
    return True

def _run_idealab_parallel_tasks(task_groups: Dict, model: str, difficulty: str,
                                adaptive: bool, batch_commit: bool, checkpoint_interval: int, **kwargs):
    """IdealLab模型的并行策略：每个prompt type使用不同的API key并行"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import time
    
    # API key分配说明
    print(f"\n📦 IdealLab并行策略：")
    for i, pt in enumerate(task_groups.keys()):
        if pt in ['baseline', 'cot', 'optimal']:
            print(f"  {pt} → API Key {i+1}")
        else:
            print(f"  {pt} → 轮询使用3个keys")
    
    print(f"\n⚡ 启动{len(task_groups)}个并行任务...")
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=len(task_groups)) as executor:
        futures = []
        
        for prompt_type, tasks in task_groups.items():
            if not tasks:
                continue
                
            # 为每个prompt type提交一个任务
            future = executor.submit(
                _run_single_prompt_tasks,
                tasks, model, prompt_type, difficulty,
                adaptive, batch_commit, **kwargs
            )
            futures.append((prompt_type, future))
        
        # 收集结果
        all_results = []
        prompt_results = {}
        
        for prompt_type, future in futures:
            try:
                results = future.result(timeout=600)  # 10分钟超时
                all_results.extend(results)
                success_count = sum(1 for r in results if r and r.get('success', False))
                prompt_results[prompt_type] = {
                    'success': True,
                    'count': len(results),
                    'success_count': success_count
                }
                print(f"✅ {prompt_type} 完成: {success_count}/{len(results)} 成功")
            except Exception as e:
                print(f"❌ {prompt_type} 失败: {e}")
                prompt_results[prompt_type] = {
                    'success': False,
                    'error': str(e)
                }
    
    elapsed = time.time() - start_time
    
    # 统计总结果
    total_success = sum(1 for r in all_results if r and r.get('success', False))
    print(f"\n✅ 所有prompt types测试完成")
    print(f"   总时间: {elapsed:.2f}秒")
    print(f"   总测试: {len(all_results)}")
    print(f"   成功: {total_success}")
    print(f"   失败: {len(all_results) - total_success}")
    
    # 保存结果（无论是否batch_commit）
    if all_results:
        unsaved_results = [r for r in all_results if r and not r.get('_saved', False)]
        if unsaved_results:
            if not batch_commit:
                print(f"\n📤 自动保存{len(unsaved_results)}个测试结果...")
            else:
                print(f"\n📤 批量保存{len(unsaved_results)}个测试结果...")
            _save_results_to_database(unsaved_results, model, difficulty,
                                    kwargs.get('ai_classification', True),
                                    kwargs.get('result_suffix', ''))
    
    return True

def _run_single_prompt_tasks(tasks: List, model: str, prompt_type: str, difficulty: str,
                            adaptive: bool, batch_commit: bool, **kwargs):
    """运行单个prompt type的所有任务"""
    # IdealLab使用保守参数
    max_workers = min(kwargs.get('max_workers', 5), 5)
    initial_qps = min(kwargs.get('qps', 10.0), 10.0)
    
    # 创建runner并运行
    runner = BatchTestRunner(
        debug=False,
        silent=True,  # 减少输出避免混乱
        use_adaptive=adaptive,
        save_logs=kwargs.get('save_logs', True),
        enable_database_updates=True,  # 总是启用数据库更新以防数据丢失
        is_subprocess=True,  # 标记为子进程
        use_ai_classification=kwargs.get('ai_classification', True),  # 传递AI分类参数
        checkpoint_interval=0  # 单个prompt type不需要checkpoint
    )
    
    if adaptive:
        results = runner.run_adaptive_concurrent_batch(
            tasks,
            initial_workers=max_workers,
            initial_qps=initial_qps
        )
    else:
        results = runner.run_concurrent_batch(
            tasks,
            workers=max_workers,
            qps=initial_qps
        )
    
    return results

def _run_provider_tasks(tasks, max_workers, initial_qps, adaptive, save_logs, silent, 
                        enable_database_updates, use_ai_classification, checkpoint_interval):
    """运行单个提供商的任务（用于进程池）"""
    runner = BatchTestRunner(
        debug=False,
        silent=silent,
        use_adaptive=adaptive,
        save_logs=save_logs,
        enable_database_updates=enable_database_updates,
        is_subprocess=True,  # 标记为子进程
        use_ai_classification=use_ai_classification,  # 传递AI分类参数
        checkpoint_interval=checkpoint_interval
    )
    
    if adaptive:
        return runner.run_adaptive_concurrent_batch(
            tasks,
            initial_workers=max_workers,
            initial_qps=initial_qps
        )
    else:
        return runner.run_concurrent_batch(
            tasks,
            workers=max_workers,
            qps=initial_qps
        )

if __name__ == "__main__":
    main()