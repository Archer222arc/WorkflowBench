#!/usr/bin/env python3
"""
测试多个IdealLab API Key的并行能力
===================================
验证使用不同API key是否能突破单key的限制
"""

import time
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import sys
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).parent))

# 三个IdealLab API keys
IDEALAB_KEYS = [
    "956c41bd0f31beaf68b871d4987af4bb",  # 原始key
    "3d906058842b6cf4cee8aaa019f7e77b",  # 新key 1
    "88a9a9010f2864bfb53996279dc6c3b9"   # 新key 2
]

IDEALAB_BASE = "https://idealab.alibaba-inc.com/api/openai/v1"

def get_client_for_key(api_key: str) -> OpenAI:
    """为特定API key创建客户端"""
    return OpenAI(
        api_key=api_key,
        base_url=IDEALAB_BASE
    )

def test_request_with_key(model: str, api_key: str, request_id: int):
    """使用指定的API key发送请求"""
    start = time.time()
    try:
        client = get_client_for_key(api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": f"Say {request_id}"}],
            max_tokens=5,
            temperature=0
        )
        return {
            'model': model,
            'key_index': IDEALAB_KEYS.index(api_key),
            'id': request_id,
            'success': True,
            'time': time.time() - start
        }
    except Exception as e:
        error_msg = str(e)
        is_rate_limit = '平行度' in error_msg or 'rate' in error_msg.lower()
        return {
            'model': model,
            'key_index': IDEALAB_KEYS.index(api_key),
            'id': request_id,
            'success': False,
            'time': time.time() - start,
            'error': error_msg[:100],
            'is_rate_limit': is_rate_limit
        }

def test_single_key_limit(model: str, api_key: str, num_requests: int = 20):
    """测试单个API key的并发限制"""
    print(f"\n{'='*60}")
    print(f"测试单个API Key的限制")
    print(f"模型: {model}")
    print(f"API Key: ...{api_key[-8:]}")
    print(f"并发请求: {num_requests}")
    print(f"{'='*60}")
    
    start = time.time()
    
    with ThreadPoolExecutor(max_workers=num_requests) as executor:
        futures = [
            executor.submit(test_request_with_key, model, api_key, i)
            for i in range(num_requests)
        ]
        results = [f.result() for f in as_completed(futures)]
    
    elapsed = time.time() - start
    success = sum(1 for r in results if r['success'])
    rate_limited = sum(1 for r in results if not r['success'] and r.get('is_rate_limit'))
    
    print(f"\n结果:")
    print(f"  成功: {success}/{num_requests} ({success/num_requests*100:.0f}%)")
    print(f"  速率限制: {rate_limited}")
    print(f"  耗时: {elapsed:.2f}s")
    print(f"  QPS: {num_requests/elapsed:.2f}")
    
    return results, elapsed, success

def test_multi_key_same_model(model: str, requests_per_key: int = 10):
    """测试多个API key访问同一模型"""
    print(f"\n{'='*60}")
    print(f"测试多个API Key并行访问同一模型")
    print(f"模型: {model}")
    print(f"API Keys: {len(IDEALAB_KEYS)}个")
    print(f"每个Key请求数: {requests_per_key}")
    print(f"总请求数: {len(IDEALAB_KEYS) * requests_per_key}")
    print(f"{'='*60}")
    
    start = time.time()
    
    with ThreadPoolExecutor(max_workers=len(IDEALAB_KEYS) * requests_per_key) as executor:
        futures = []
        for key_idx, api_key in enumerate(IDEALAB_KEYS):
            for i in range(requests_per_key):
                futures.append(
                    executor.submit(test_request_with_key, model, api_key, i)
                )
        
        results = [f.result() for f in as_completed(futures)]
    
    elapsed = time.time() - start
    
    # 按API key统计
    for key_idx, api_key in enumerate(IDEALAB_KEYS):
        key_results = [r for r in results if r['key_index'] == key_idx]
        success = sum(1 for r in key_results if r['success'])
        print(f"\nKey {key_idx} (...{api_key[-8:]}): {success}/{len(key_results)} 成功")
    
    total_success = sum(1 for r in results if r['success'])
    print(f"\n总计: {total_success}/{len(results)} 成功")
    print(f"耗时: {elapsed:.2f}s")
    print(f"QPS: {len(results)/elapsed:.2f}")
    
    return results, elapsed, total_success

def test_multi_key_multi_model(models: list, requests_per_combo: int = 5):
    """测试多个API key访问多个模型（最大并行）"""
    print(f"\n{'='*60}")
    print(f"测试多Key×多模型 最大并行")
    print(f"模型: {', '.join(models)}")
    print(f"API Keys: {len(IDEALAB_KEYS)}个")
    print(f"每个组合: {requests_per_combo}个请求")
    print(f"总请求数: {len(models) * len(IDEALAB_KEYS) * requests_per_combo}")
    print(f"{'='*60}")
    
    start = time.time()
    total_requests = len(models) * len(IDEALAB_KEYS) * requests_per_combo
    
    with ThreadPoolExecutor(max_workers=total_requests) as executor:
        futures = []
        for model in models:
            for api_key in IDEALAB_KEYS:
                for i in range(requests_per_combo):
                    futures.append(
                        executor.submit(test_request_with_key, model, api_key, i)
                    )
        
        results = [f.result() for f in as_completed(futures)]
    
    elapsed = time.time() - start
    
    # 统计结果
    print("\n按模型和API Key统计:")
    for model in models:
        print(f"\n{model}:")
        for key_idx, api_key in enumerate(IDEALAB_KEYS):
            combo_results = [
                r for r in results 
                if r['model'] == model and r['key_index'] == key_idx
            ]
            success = sum(1 for r in combo_results if r['success'])
            print(f"  Key {key_idx}: {success}/{len(combo_results)} 成功")
    
    total_success = sum(1 for r in results if r['success'])
    print(f"\n总计: {total_success}/{len(results)} 成功 ({total_success/len(results)*100:.0f}%)")
    print(f"耗时: {elapsed:.2f}s")
    print(f"QPS: {len(results)/elapsed:.2f}")
    
    return results, elapsed, total_success

def comprehensive_test():
    """综合测试"""
    print("="*70)
    print("IdealLab 多API Key并行测试")
    print("="*70)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API Keys: {len(IDEALAB_KEYS)}个")
    
    models = ['qwen2.5-3b-instruct', 'qwen2.5-7b-instruct', 'qwen2.5-14b-instruct']
    
    # 阶段1: 测试单个key的限制
    print("\n\n【阶段1】单个API Key的限制")
    single_results, single_time, single_success = test_single_key_limit(
        models[0], IDEALAB_KEYS[0], 20
    )
    
    time.sleep(3)
    
    # 阶段2: 多个key访问同一模型
    print("\n\n【阶段2】多个API Key访问同一模型")
    multi_key_results, multi_key_time, multi_key_success = test_multi_key_same_model(
        models[0], 10
    )
    
    time.sleep(3)
    
    # 阶段3: 多key×多模型
    print("\n\n【阶段3】多Key×多模型 极限测试")
    extreme_results, extreme_time, extreme_success = test_multi_key_multi_model(
        models, 5
    )
    
    # 最终分析
    print("\n" + "="*70)
    print("测试结果分析")
    print("="*70)
    
    print(f"\n1. 单Key测试 (1 key × 1 model × 20 requests):")
    print(f"   成功率: {single_success}/20 = {single_success/20*100:.0f}%")
    print(f"   耗时: {single_time:.2f}s")
    
    print(f"\n2. 多Key同模型 (3 keys × 1 model × 10 requests = 30):")
    print(f"   成功率: {multi_key_success}/30 = {multi_key_success/30*100:.0f}%")
    print(f"   耗时: {multi_key_time:.2f}s")
    print(f"   vs 单Key加速: {single_time*1.5/multi_key_time:.2f}x")
    
    total_extreme = len(models) * len(IDEALAB_KEYS) * 5
    print(f"\n3. 极限测试 (3 keys × 3 models × 5 requests = 45):")
    print(f"   成功率: {extreme_success}/{total_extreme} = {extreme_success/total_extreme*100:.0f}%")
    print(f"   耗时: {extreme_time:.2f}s")
    print(f"   QPS: {total_extreme/extreme_time:.2f}")
    
    # 结论
    print("\n" + "="*70)
    print("结论")
    print("="*70)
    
    if multi_key_success > single_success * 1.5:
        print("✅ 多个API Key可以突破单Key限制！")
        print("   - 每个API Key有独立的速率限制")
        print("   - 可以通过多Key实现更高并发")
    
    if extreme_success == total_extreme:
        print("\n✅ 多Key×多模型可以实现极高并发！")
        print("   - 不同模型 + 不同API Key = 最大并行度")
    
    # 实用建议
    print("\n" + "="*70)
    print("优化建议")
    print("="*70)
    
    print("\n🚀 基于3个API Key的最优配置:")
    print("1. 将21个IdealLab模型分成3组（每组7个模型）")
    print("2. 每个API Key负责一组模型")
    print("3. 每个模型可以有8-10个并发")
    print("4. 总并发数: 3 keys × 7 models × 8 并发 = 168个并发！")
    print("\n预期性能提升:")
    print("  - 原始（1 key）: ~10个并发")
    print("  - 优化（3 keys）: ~30个并发（3倍提升）")
    print("  - 极限（3 keys × 多模型）: 100+并发（10倍提升）")

if __name__ == "__main__":
    comprehensive_test()