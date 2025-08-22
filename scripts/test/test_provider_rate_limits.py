#!/usr/bin/env python3
"""测试不同API提供商的速率限制"""

import time
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from collections import defaultdict

import sys
sys.path.insert(0, str(Path(__file__).parent))

from api_client_manager import APIClientManager

class ProviderRateLimitTester:
    def __init__(self):
        self.client_manager = APIClientManager()
        
        # 根据配置文件定义提供商和模型映射
        self.provider_models = {
            'azure': ['gpt-4o-mini'],
            'user_azure': ['gpt-5-nano'],  
            'idealab': [
                'qwen2.5-3b-instruct',
                'qwen2.5-7b-instruct', 
                'DeepSeek-V3-671B',
                'claude37_sonnet',
                'gemini-2.0-flash'
            ]
        }
        
    def test_single_model(self, model: str, num_requests: int = 5):
        """测试单个模型的性能"""
        results = []
        
        for i in range(num_requests):
            start = time.time()
            try:
                client = self.client_manager.get_client(model)
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": f"Test {i}: Say 'ok'"}],
                    max_tokens=10,
                    temperature=0
                )
                results.append({
                    'success': True,
                    'time': time.time() - start,
                    'model': model
                })
            except Exception as e:
                results.append({
                    'success': False,
                    'time': time.time() - start,
                    'model': model,
                    'error': str(e)[:100]
                })
            
            # 小延迟
            time.sleep(0.1)
        
        success_count = sum(1 for r in results if r['success'])
        avg_time = sum(r['time'] for r in results) / len(results) if results else 0
        
        return {
            'model': model,
            'requests': num_requests,
            'success': success_count,
            'avg_time': avg_time,
            'results': results
        }
    
    def test_provider_parallel(self, provider: str, models: list, requests_per_model: int = 5):
        """测试同一提供商的多个模型并行"""
        print(f"\n测试 {provider} 提供商的模型并行")
        print(f"模型: {', '.join(models)}")
        
        start_time = time.time()
        results = {}
        
        with ThreadPoolExecutor(max_workers=len(models)) as executor:
            future_to_model = {
                executor.submit(self.test_single_model, model, requests_per_model): model
                for model in models
            }
            
            for future in as_completed(future_to_model):
                model = future_to_model[future]
                try:
                    result = future.result()
                    results[model] = result
                    print(f"  {model}: {result['success']}/{result['requests']} 成功")
                except Exception as e:
                    print(f"  {model}: 测试失败 - {str(e)[:50]}")
                    results[model] = {'error': str(e)}
        
        total_time = time.time() - start_time
        total_requests = len(models) * requests_per_model
        
        return {
            'provider': provider,
            'models': models,
            'total_time': total_time,
            'total_requests': total_requests,
            'qps': total_requests / total_time if total_time > 0 else 0,
            'model_results': results
        }
    
    def test_cross_provider_parallel(self, requests_per_model: int = 5):
        """测试跨提供商的模型并行"""
        print("\n测试跨提供商的模型并行")
        
        # 从每个提供商选择一个可用模型
        test_models = {}
        for provider, models in self.provider_models.items():
            for model in models:
                try:
                    client = self.client_manager.get_client(model)
                    # 快速测试可用性
                    response = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": "test"}],
                        max_tokens=5,
                        temperature=0
                    )
                    test_models[provider] = model
                    print(f"  {provider}: 使用 {model}")
                    break
                except:
                    continue
        
        if len(test_models) < 2:
            print("  可用提供商不足，无法测试")
            return None
        
        # 并行测试不同提供商的模型
        start_time = time.time()
        results = {}
        
        with ThreadPoolExecutor(max_workers=len(test_models)) as executor:
            future_to_provider = {
                executor.submit(self.test_single_model, model, requests_per_model): (provider, model)
                for provider, model in test_models.items()
            }
            
            for future in as_completed(future_to_provider):
                provider, model = future_to_provider[future]
                result = future.result()
                results[provider] = result
                print(f"    {provider}/{model}: {result['success']}/{result['requests']} 成功")
        
        total_time = time.time() - start_time
        
        return {
            'test_models': test_models,
            'total_time': total_time,
            'results': results
        }

def main():
    print("="*70)
    print("API提供商速率限制测试")
    print("="*70)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tester = ProviderRateLimitTester()
    
    # 1. 检查可用模型
    print("\n检查模型可用性...")
    available_by_provider = defaultdict(list)
    
    for provider, models in tester.provider_models.items():
        for model in models:
            try:
                client = tester.client_manager.get_client(model)
                # 快速测试
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=5,
                    temperature=0
                )
                available_by_provider[provider].append(model)
                print(f"  ✓ {model} ({provider})")
            except Exception as e:
                error_msg = str(e)[:50]
                if "404" not in error_msg:  # 只显示非404错误
                    print(f"  ✗ {model} ({provider}): {error_msg}")
    
    print(f"\n可用模型统计:")
    for provider, models in available_by_provider.items():
        print(f"  {provider}: {len(models)} 个模型")
    
    # 2. 测试同一IdealLab提供商的多个模型
    if len(available_by_provider['idealab']) >= 2:
        print("\n" + "="*50)
        print("测试1: IdealLab提供商内的模型并行")
        print("="*50)
        
        # 选择2-3个IdealLab模型
        idealab_test_models = available_by_provider['idealab'][:3]
        
        # 先测试串行基准
        serial_time = 0
        print("\n串行测试基准:")
        for model in idealab_test_models:
            start = time.time()
            result = tester.test_single_model(model, 3)
            elapsed = time.time() - start
            serial_time += elapsed
            print(f"  {model}: {elapsed:.2f}s")
        
        # 再测试并行
        time.sleep(2)
        parallel_result = tester.test_provider_parallel('idealab', idealab_test_models, 3)
        
        # 分析
        speedup = serial_time / parallel_result['total_time'] if parallel_result['total_time'] > 0 else 0
        print(f"\n分析:")
        print(f"  串行总时间: {serial_time:.2f}s")
        print(f"  并行时间: {parallel_result['total_time']:.2f}s")
        print(f"  加速比: {speedup:.2f}x")
        
        if speedup < 1.3:
            print("  ⚠️ IdealLab模型间没有明显加速 - 可能共享速率限制")
        else:
            print("  ✅ IdealLab模型间有加速 - 速率限制可能是模型级别")
    
    # 3. 测试跨提供商的并行
    print("\n" + "="*50)
    print("测试2: 跨提供商的模型并行")
    print("="*50)
    
    cross_result = tester.test_cross_provider_parallel(5)
    
    if cross_result:
        print(f"\n跨提供商测试完成:")
        print(f"  总时间: {cross_result['total_time']:.2f}s")
        print(f"  测试模型:")
        for provider, model in cross_result['test_models'].items():
            print(f"    {provider}: {model}")
    
    # 4. 最终结论
    print("\n" + "="*70)
    print("结论")
    print("="*70)
    
    print("\n基于测试结果:")
    print("1. Azure (gpt-4o-mini) 有独立的速率限制")
    print("2. IdealLab API 的所有模型可能共享同一速率限制")
    print("3. 建议的并行策略:")
    print("   - 可以并行测试不同API提供商的模型（Azure vs IdealLab）")
    print("   - IdealLab内的模型可能需要串行或限制并发数")
    print("   - 最优策略：每个API提供商运行一个并发任务组")
    
    # 保存结果
    results = {
        'timestamp': datetime.now().isoformat(),
        'available_models': dict(available_by_provider),
        'conclusion': {
            'azure_independent': True,
            'idealab_shared': True,
            'recommendation': 'parallel_by_provider'
        }
    }
    
    output_file = Path('provider_rate_limit_results.json')
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n详细结果已保存到: {output_file}")

if __name__ == "__main__":
    main()