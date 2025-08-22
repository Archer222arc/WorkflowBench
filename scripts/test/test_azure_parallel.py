#!/usr/bin/env python3
"""测试Azure模型的并行速率限制"""

import time
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import threading

import sys
sys.path.insert(0, str(Path(__file__).parent))

from api_client_manager import APIClientManager

class AzureParallelTester:
    def __init__(self):
        self.client_manager = APIClientManager()
        self.results = []
        self.lock = threading.Lock()
        
    def test_model(self, model: str, num_requests: int = 10):
        """测试单个模型"""
        results = []
        
        def make_request(i):
            start = time.time()
            try:
                client = self.client_manager.get_client(model)
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": f"Count to {i}"}],
                    max_tokens=20,
                    temperature=0
                )
                return {
                    'id': i,
                    'success': True,
                    'time': time.time() - start,
                    'model': model
                }
            except Exception as e:
                return {
                    'id': i,
                    'success': False,
                    'time': time.time() - start,
                    'model': model,
                    'error': str(e)[:100]
                }
        
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=num_requests) as executor:
            futures = [executor.submit(make_request, i) for i in range(num_requests)]
            for future in as_completed(futures):
                results.append(future.result())
        
        total_time = time.time() - start_time
        success_count = sum(1 for r in results if r['success'])
        
        return {
            'model': model,
            'total_time': total_time,
            'num_requests': num_requests,
            'success_count': success_count,
            'qps': num_requests / total_time if total_time > 0 else 0,
            'avg_response_time': sum(r['time'] for r in results) / len(results) if results else 0
        }
    
    def test_parallel_models(self, models, num_requests_per_model=10):
        """并行测试多个模型"""
        all_results = []
        model_stats = {}
        
        def test_single_model(model):
            return self.test_model(model, num_requests_per_model)
        
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=len(models)) as executor:
            future_to_model = {
                executor.submit(test_single_model, model): model 
                for model in models
            }
            
            for future in as_completed(future_to_model):
                model = future_to_model[future]
                result = future.result()
                model_stats[model] = result
        
        total_time = time.time() - start_time
        
        return {
            'total_time': total_time,
            'models': models,
            'model_stats': model_stats,
            'total_requests': sum(s['num_requests'] for s in model_stats.values()),
            'total_qps': sum(s['num_requests'] for s in model_stats.values()) / total_time if total_time > 0 else 0
        }

def main():
    print("="*70)
    print("Azure模型并行测试")
    print("="*70)
    
    tester = AzureParallelTester()
    
    # 检查可用的Azure模型
    azure_models = [
        'gpt-4o-mini',
        'gpt-4o',
        'Llama-3.3-70B-Instruct', 
        'DeepSeek-V3-0324',
        'DeepSeek-R1-0528'
    ]
    
    available_models = []
    print("\n检查模型可用性:")
    for model in azure_models:
        try:
            client = tester.client_manager.get_client(model)
            # 快速测试
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=5,
                temperature=0
            )
            available_models.append(model)
            print(f"  ✓ {model}")
        except Exception as e:
            print(f"  ✗ {model}: {str(e)[:50]}")
    
    if len(available_models) < 2:
        print("\n需要至少2个可用模型")
        return
    
    # 选择前3个可用模型进行测试
    test_models = available_models[:3]
    print(f"\n使用模型: {', '.join(test_models)}")
    
    # 测试1: 单个模型串行
    print("\n" + "="*50)
    print("测试1: 单模型性能基准")
    print("="*50)
    
    single_results = {}
    for model in test_models:
        print(f"\n测试 {model}...")
        result = tester.test_model(model, num_requests=5)
        single_results[model] = result
        print(f"  完成: {result['success_count']}/5 成功, "
              f"耗时 {result['total_time']:.2f}s, "
              f"QPS: {result['qps']:.2f}")
        time.sleep(1)  # 避免过快
    
    # 测试2: 多模型并行
    print("\n" + "="*50)
    print("测试2: 多模型并行")
    print("="*50)
    
    print(f"\n并行测试 {len(test_models)} 个模型...")
    parallel_result = tester.test_parallel_models(test_models, num_requests_per_model=5)
    
    print(f"\n并行测试完成:")
    print(f"  总耗时: {parallel_result['total_time']:.2f}s")
    print(f"  总请求: {parallel_result['total_requests']}")
    print(f"  总QPS: {parallel_result['total_qps']:.2f}")
    
    for model, stats in parallel_result['model_stats'].items():
        print(f"  {model}: {stats['success_count']}/{stats['num_requests']} 成功")
    
    # 分析
    print("\n" + "="*50)
    print("分析结果")
    print("="*50)
    
    # 计算串行总时间
    serial_time = sum(r['total_time'] for r in single_results.values())
    parallel_time = parallel_result['total_time']
    speedup = serial_time / parallel_time if parallel_time > 0 else 0
    
    print(f"\n时间对比:")
    print(f"  串行总时间: {serial_time:.2f}s")
    print(f"  并行时间: {parallel_time:.2f}s")
    print(f"  加速比: {speedup:.2f}x")
    print(f"  理论最大加速比: {len(test_models):.1f}x")
    print(f"  效率: {speedup/len(test_models)*100:.1f}%")
    
    # QPS对比
    serial_qps = sum(r['qps'] for r in single_results.values()) / len(single_results)
    parallel_qps = parallel_result['total_qps']
    
    print(f"\nQPS对比:")
    print(f"  平均单模型QPS: {serial_qps:.2f}")
    print(f"  并行总QPS: {parallel_qps:.2f}")
    print(f"  QPS提升: {parallel_qps/serial_qps:.2f}x")
    
    # 结论
    print("\n" + "="*50)
    print("结论")
    print("="*50)
    
    if speedup >= len(test_models) * 0.8:
        print("✅ 强烈确认: 速率限制是模型级别的!")
        print(f"   - 加速比接近理论最大值 ({speedup:.2f}x vs {len(test_models)}x)")
        print("   - 强烈建议使用多模型并行策略")
    elif speedup >= len(test_models) * 0.6:
        print("✅ 确认: 速率限制是模型级别的!")
        print(f"   - 加速比良好 ({speedup:.2f}x)")
        print("   - 建议使用多模型并行策略")
    elif speedup > 1.2:
        print("⚠️ 部分确认: 速率限制可能是模型级别的")
        print(f"   - 有一定加速效果 ({speedup:.2f}x)")
        print("   - 可能存在其他瓶颈")
    else:
        print("❌ 速率限制可能不是模型级别的")
        print(f"   - 加速效果不明显 ({speedup:.2f}x)")
    
    # 保存结果
    results = {
        'timestamp': datetime.now().isoformat(),
        'models': test_models,
        'single_results': single_results,
        'parallel_result': parallel_result,
        'analysis': {
            'serial_time': serial_time,
            'parallel_time': parallel_time,
            'speedup': speedup,
            'efficiency': speedup/len(test_models)*100
        }
    }
    
    output_file = Path('azure_parallel_test_results.json')
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n详细结果已保存到: {output_file}")

if __name__ == "__main__":
    main()