#!/usr/bin/env python3
"""
IdealLab API 压力测试 - 确定速率限制范围
=========================================
使用更高并发度测试IdealLab的速率限制是模型级别还是API key级别
"""

import time
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from api_client_manager import APIClientManager

def test_request(model: str, request_id: int):
    """发送测试请求"""
    manager = APIClientManager()
    start = time.time()
    try:
        client = manager.get_client(model)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": f"Say '{request_id}'"}],
            max_tokens=5,
            temperature=0
        )
        return {
            'model': model,
            'id': request_id,
            'success': True,
            'time': time.time() - start
        }
    except Exception as e:
        return {
            'model': model,
            'id': request_id,
            'success': False,
            'time': time.time() - start,
            'error': str(e)[:100]
        }

def stress_test_single_model(model: str, num_parallel: int = 20):
    """压力测试单个模型"""
    print(f"\n{'='*60}")
    print(f"压力测试单模型: {model}")
    print(f"并发请求数: {num_parallel}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=num_parallel) as executor:
        futures = [executor.submit(test_request, model, i) for i in range(num_parallel)]
        results = [f.result() for f in as_completed(futures)]
    
    total_time = time.time() - start_time
    success = sum(1 for r in results if r['success'])
    
    print(f"\n结果:")
    print(f"  成功: {success}/{num_parallel}")
    print(f"  总时间: {total_time:.2f}s")
    print(f"  QPS: {num_parallel/total_time:.2f}")
    
    # 显示失败的请求
    failed = [r for r in results if not r['success']]
    if failed:
        print(f"\n失败的请求 ({len(failed)}个):")
        for r in failed[:5]:  # 只显示前5个
            print(f"  ID {r['id']}: {r.get('error', 'Unknown')[:50]}")
    
    return results, total_time

def stress_test_multiple_models(models: list, requests_per_model: int = 10):
    """压力测试多个模型"""
    print(f"\n{'='*60}")
    print(f"压力测试多模型并行")
    print(f"模型: {', '.join(models)}")
    print(f"每个模型请求数: {requests_per_model}")
    print(f"总请求数: {len(models) * requests_per_model}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=len(models) * requests_per_model) as executor:
        futures = []
        for model in models:
            for i in range(requests_per_model):
                futures.append(executor.submit(test_request, model, i))
        
        results = [f.result() for f in as_completed(futures)]
    
    total_time = time.time() - start_time
    
    # 按模型分组统计
    model_stats = {}
    for model in models:
        model_results = [r for r in results if r['model'] == model]
        success = sum(1 for r in model_results if r['success'])
        model_stats[model] = {
            'success': success,
            'total': len(model_results),
            'rate': success / len(model_results) if model_results else 0
        }
    
    print(f"\n整体结果:")
    print(f"  总时间: {total_time:.2f}s")
    print(f"  总QPS: {len(results)/total_time:.2f}")
    
    print(f"\n各模型结果:")
    for model, stats in model_stats.items():
        print(f"  {model}: {stats['success']}/{stats['total']} ({stats['rate']*100:.0f}%)")
    
    return results, total_time

def compare_scenarios():
    """对比不同场景"""
    models = ['qwen2.5-3b-instruct', 'qwen2.5-7b-instruct', 'qwen2.5-14b-instruct']
    
    print("="*70)
    print("IdealLab API 速率限制压力测试")
    print("="*70)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 场景1: 单模型高并发
    print("\n\n场景1: 单模型高并发 (20个并发)")
    single_results, single_time = stress_test_single_model(models[0], 20)
    single_success = sum(1 for r in single_results if r['success'])
    
    time.sleep(5)  # 休息一下
    
    # 场景2: 3个模型，每个7个并发 (总共21个)
    print("\n\n场景2: 3个模型并行 (每个模型7个请求，总共21个)")
    multi_results, multi_time = stress_test_multiple_models(models, 7)
    multi_success = sum(1 for r in multi_results if r['success'])
    
    # 对比分析
    print("\n" + "="*70)
    print("对比分析")
    print("="*70)
    
    print(f"\n场景1 (单模型20并发):")
    print(f"  成功率: {single_success}/20 ({single_success/20*100:.0f}%)")
    print(f"  耗时: {single_time:.2f}s")
    print(f"  QPS: {20/single_time:.2f}")
    
    print(f"\n场景2 (3模型×7并发=21):")
    print(f"  成功率: {multi_success}/21 ({multi_success/21*100:.0f}%)")
    print(f"  耗时: {multi_time:.2f}s")
    print(f"  QPS: {21/multi_time:.2f}")
    
    print(f"\n加速比: {single_time/multi_time:.2f}x")
    
    # 结论
    print("\n" + "="*70)
    print("结论")
    print("="*70)
    
    if multi_time < single_time * 0.7:  # 如果多模型明显更快
        print("✅ IdealLab的速率限制很可能是【模型级别】")
        print("   不同模型可以独立并行，互不影响")
    elif multi_time > single_time * 1.3:  # 如果多模型明显更慢
        print("⚠️ IdealLab的速率限制很可能是【API key级别】")
        print("   所有模型共享同一速率限制")
    else:
        print("🤔 结果不明确，可能需要更多测试")
        print(f"   单模型时间: {single_time:.2f}s")
        print(f"   多模型时间: {multi_time:.2f}s")
    
    # 基于成功率的判断
    if single_success == 20 and multi_success == 21:
        print("\n额外观察: 两种场景都100%成功，说明并发限制较宽松")
    elif single_success > multi_success:
        print("\n额外观察: 单模型成功率更高，暗示可能存在总体速率限制")
    elif multi_success > single_success:
        print("\n额外观察: 多模型成功率更高，暗示模型间相对独立")

if __name__ == "__main__":
    compare_scenarios()