#!/usr/bin/env python3
"""
寻找IdealLab多API Key的最优配置
================================
"""

import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import sys
from openai import OpenAI
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))

IDEALAB_KEYS = [
    "956c41bd0f31beaf68b871d4987af4bb",  # Key 0
    "3d906058842b6cf4cee8aaa019f7e77b",  # Key 1  
    "88a9a9010f2864bfb53996279dc6c3b9"   # Key 2
]

IDEALAB_BASE = "https://idealab.alibaba-inc.com/api/openai/v1"

def test_request(model: str, api_key: str, request_id: int):
    """发送测试请求"""
    start = time.time()
    try:
        client = OpenAI(api_key=api_key, base_url=IDEALAB_BASE)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "1+1"}],
            max_tokens=5,
            temperature=0
        )
        return {
            'success': True,
            'time': time.time() - start,
            'model': model,
            'key_idx': IDEALAB_KEYS.index(api_key)
        }
    except Exception as e:
        return {
            'success': False,
            'time': time.time() - start,
            'model': model,
            'key_idx': IDEALAB_KEYS.index(api_key),
            'error': str(e)[:50]
        }

def test_configuration(models_per_key: dict, requests_per_model: int = 5):
    """
    测试特定的配置
    models_per_key: {key_idx: [models]}
    """
    print(f"\n测试配置:")
    for key_idx, models in models_per_key.items():
        print(f"  Key {key_idx}: {', '.join(models)}")
    
    total_requests = sum(len(models) * requests_per_model for models in models_per_key.values())
    print(f"  总请求数: {total_requests}")
    
    start = time.time()
    
    with ThreadPoolExecutor(max_workers=total_requests) as executor:
        futures = []
        for key_idx, models in models_per_key.items():
            api_key = IDEALAB_KEYS[key_idx]
            for model in models:
                for i in range(requests_per_model):
                    futures.append(
                        executor.submit(test_request, model, api_key, i)
                    )
        
        results = [f.result() for f in as_completed(futures)]
    
    elapsed = time.time() - start
    
    # 统计
    success_by_key = defaultdict(int)
    total_by_key = defaultdict(int)
    
    for r in results:
        total_by_key[r['key_idx']] += 1
        if r['success']:
            success_by_key[r['key_idx']] += 1
    
    total_success = sum(success_by_key.values())
    
    print(f"\n结果:")
    for key_idx in models_per_key.keys():
        success = success_by_key[key_idx]
        total = total_by_key[key_idx]
        print(f"  Key {key_idx}: {success}/{total} 成功 ({success/total*100:.0f}%)")
    
    print(f"\n总体:")
    print(f"  成功率: {total_success}/{total_requests} ({total_success/total_requests*100:.0f}%)")
    print(f"  耗时: {elapsed:.2f}s")
    print(f"  QPS: {total_requests/elapsed:.2f}")
    
    return total_success, total_requests, elapsed

def find_optimal_configuration():
    """找到最优配置"""
    print("="*70)
    print("IdealLab 多API Key 最优配置测试")
    print("="*70)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API Keys: {len(IDEALAB_KEYS)}个")
    
    models = [
        'qwen2.5-3b-instruct',
        'qwen2.5-7b-instruct', 
        'qwen2.5-14b-instruct',
        'qwen2.5-32b-instruct',
        'DeepSeek-V3-671B',
        'claude37_sonnet'
    ]
    
    print(f"测试模型: {', '.join(models)}")
    
    # 配置1: 所有模型用一个key
    print("\n\n【配置1】所有模型使用Key 0")
    print("-"*40)
    config1 = {0: models}
    success1, total1, time1 = test_configuration(config1, 3)
    
    time.sleep(3)
    
    # 配置2: 均匀分配
    print("\n\n【配置2】均匀分配模型到3个Keys")
    print("-"*40)
    config2 = {
        0: models[0:2],  # qwen2.5-3b, qwen2.5-7b
        1: models[2:4],  # qwen2.5-14b, qwen2.5-32b
        2: models[4:6]   # DeepSeek, claude
    }
    success2, total2, time2 = test_configuration(config2, 3)
    
    time.sleep(3)
    
    # 配置3: 轮询分配
    print("\n\n【配置3】轮询分配模型到3个Keys")
    print("-"*40)
    config3 = {0: [], 1: [], 2: []}
    for i, model in enumerate(models):
        config3[i % 3].append(model)
    success3, total3, time3 = test_configuration(config3, 3)
    
    # 分析
    print("\n" + "="*70)
    print("配置对比")
    print("="*70)
    
    configs = [
        ("单Key", success1, total1, time1),
        ("均匀分配", success2, total2, time2),
        ("轮询分配", success3, total3, time3)
    ]
    
    for name, success, total, elapsed in configs:
        print(f"\n{name}:")
        print(f"  成功率: {success}/{total} = {success/total*100:.0f}%")
        print(f"  耗时: {elapsed:.2f}s")
        print(f"  QPS: {total/elapsed:.2f}")
    
    # 找出最佳配置
    best_config = max(configs, key=lambda x: x[1]/x[3])  # 成功数/时间
    print(f"\n🏆 最佳配置: {best_config[0]}")
    print(f"   效率: {best_config[1]/best_config[3]:.2f} 成功/秒")
    
    # 建议
    print("\n" + "="*70)
    print("优化建议")
    print("="*70)
    
    print("\n基于测试结果，建议采用以下策略:")
    print("\n1. 【模型分组策略】")
    print("   将21个IdealLab模型分成3组，每组使用一个API Key:")
    print("   - Key 0: 7个Qwen模型")
    print("   - Key 1: 7个其他模型（Claude, Gemini等）")
    print("   - Key 2: 7个其他模型（DeepSeek, Kimi等）")
    
    print("\n2. 【并发控制】")
    print("   - 每个API Key控制在5-8个并发")
    print("   - 每个模型2-3个并发")
    print("   - 总并发: 3 keys × 8 = 24个并发")
    
    print("\n3. 【动态负载均衡】")
    print("   - 监控每个Key的成功率")
    print("   - 动态调整模型分配")
    print("   - 失败重试使用不同的Key")
    
    print("\n4. 【预期性能】")
    if success2/total2 > success1/total1 * 1.2:
        speedup = time1/time2
        print(f"   - 使用3个Keys可获得约{speedup:.1f}倍加速")
        print(f"   - 成功率从{success1/total1*100:.0f}%提升到{success2/total2*100:.0f}%")
    else:
        print(f"   - 多Key主要提升并发能力")
        print(f"   - 建议控制每个Key的并发数")

if __name__ == "__main__":
    find_optimal_configuration()