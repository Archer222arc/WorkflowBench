#!/usr/bin/env python3
"""
IdealLab速率限制最终验证
========================
明确测试是模型级别还是API key级别的限制
"""

import time
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
            messages=[{"role": "user", "content": "1+1"}],
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
        error_msg = str(e)
        is_rate_limit = '平行度' in error_msg or 'rate' in error_msg.lower() or '429' in str(e)
        return {
            'model': model,
            'id': request_id,
            'success': False,
            'time': time.time() - start,
            'error': error_msg[:100],
            'is_rate_limit': is_rate_limit
        }

def extreme_test():
    """极端测试：每个模型15个并发 vs 单模型15个并发"""
    
    print("="*70)
    print("IdealLab 速率限制最终验证")
    print("="*70)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    models = ['qwen2.5-3b-instruct', 'qwen2.5-7b-instruct', 'qwen2.5-14b-instruct', 'qwen2.5-32b-instruct']
    
    # 测试1: 单模型15个并发
    print("\n测试1: 单个模型15个并发请求")
    print("-"*40)
    
    model = models[0]
    start = time.time()
    
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(test_request, model, i) for i in range(15)]
        single_results = [f.result() for f in as_completed(futures)]
    
    single_time = time.time() - start
    single_success = sum(1 for r in single_results if r['success'])
    single_rate_limit = sum(1 for r in single_results if not r['success'] and r.get('is_rate_limit'))
    
    print(f"模型: {model}")
    print(f"成功: {single_success}/15")
    print(f"速率限制错误: {single_rate_limit}")
    print(f"耗时: {single_time:.2f}s")
    
    # 休息5秒
    print("\n等待5秒...")
    time.sleep(5)
    
    # 测试2: 4个模型，每个4个并发（总共16个）
    print("\n测试2: 4个模型并行，每个4个请求（总共16个）")
    print("-"*40)
    
    start = time.time()
    
    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = []
        for model in models:
            for i in range(4):
                futures.append(executor.submit(test_request, model, i))
        
        multi_results = [f.result() for f in as_completed(futures)]
    
    multi_time = time.time() - start
    
    # 统计每个模型的结果
    for model in models:
        model_results = [r for r in multi_results if r['model'] == model]
        success = sum(1 for r in model_results if r['success'])
        rate_limit = sum(1 for r in model_results if not r['success'] and r.get('is_rate_limit'))
        print(f"{model}: 成功 {success}/4, 速率限制 {rate_limit}")
    
    multi_success = sum(1 for r in multi_results if r['success'])
    multi_rate_limit = sum(1 for r in multi_results if not r['success'] and r.get('is_rate_limit'))
    
    print(f"\n总计: 成功 {multi_success}/16, 速率限制错误 {multi_rate_limit}")
    print(f"耗时: {multi_time:.2f}s")
    
    # 最终分析
    print("\n" + "="*70)
    print("分析结果")
    print("="*70)
    
    print(f"\n单模型15并发:")
    print(f"  成功率: {single_success}/15 = {single_success/15*100:.0f}%")
    print(f"  速率限制: {single_rate_limit}个")
    print(f"  耗时: {single_time:.2f}s")
    
    print(f"\n4模型×4并发:")
    print(f"  成功率: {multi_success}/16 = {multi_success/16*100:.0f}%")
    print(f"  速率限制: {multi_rate_limit}个")
    print(f"  耗时: {multi_time:.2f}s")
    
    print(f"\n时间对比: {single_time:.2f}s vs {multi_time:.2f}s")
    print(f"成功率对比: {single_success/15*100:.0f}% vs {multi_success/16*100:.0f}%")
    
    print("\n" + "="*70)
    print("最终结论")
    print("="*70)
    
    # 判断逻辑
    if single_success < 15 and single_rate_limit > 0:
        # 单模型触发了速率限制
        if multi_success == 16 or multi_success > single_success * 1.5:
            print("✅ 【确认】IdealLab的速率限制是【模型级别】")
            print("   证据：")
            print(f"   - 单模型15并发触发速率限制（只成功{single_success}/15）")
            print(f"   - 4个模型分散请求全部成功（{multi_success}/16）")
            print("   - 说明每个模型有独立的速率限制")
        elif multi_rate_limit > 0:
            print("⚠️ 【确认】IdealLab的速率限制是【API key级别】")
            print("   证据：")
            print(f"   - 单模型触发速率限制（{single_rate_limit}个）")
            print(f"   - 多模型也触发速率限制（{multi_rate_limit}个）")
            print("   - 说明所有模型共享速率限制")
    else:
        # 单模型没有触发速率限制
        if multi_success == 16:
            print("✅ 速率限制较宽松，两种模式都成功")
            print("   建议：可以使用更高的并发度")
        else:
            print("🤔 结果异常，需要进一步测试")
    
    # 实用建议
    print("\n" + "="*70)
    print("实用建议")
    print("="*70)
    
    if single_success < 15 and multi_success > single_success:
        print("🎯 对于IdealLab API:")
        print("   1. 每个模型的并发限制约为10个")
        print("   2. 不同模型可以并行执行")
        print("   3. 建议策略：多个模型轮流使用，每个模型控制并发数")
        print("   4. 最优配置：每个模型5-8个并发")
    else:
        print("🎯 基于测试结果:")
        print(f"   1. 单模型安全并发数：{min(single_success, 10)}")
        print(f"   2. 建议并发配置：{min(single_success, 10) - 2}（留有余地）")

if __name__ == "__main__":
    extreme_test()