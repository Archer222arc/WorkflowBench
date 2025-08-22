#!/usr/bin/env python3
"""测试速率限制是否在模型级别"""

import time
import asyncio
import json
from datetime import datetime
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from pathlib import Path

# 添加项目路径
import sys
sys.path.insert(0, str(Path(__file__).parent))

from api_client_manager import APIClientManager

class RateLimitTester:
    def __init__(self):
        self.client_manager = APIClientManager()
        self.results = []
        self.lock = threading.Lock()
        
    def make_request(self, model: str, request_id: int) -> Dict:
        """发送单个请求并记录结果"""
        start_time = time.time()
        
        try:
            # 简单的测试请求
            client = self.client_manager.get_client(model)
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Say 'test' and nothing else."}],
                max_tokens=10,
                temperature=0
            )
            
            end_time = time.time()
            
            result = {
                'model': model,
                'request_id': request_id,
                'start_time': start_time,
                'end_time': end_time,
                'duration': end_time - start_time,
                'success': True,
                'error': None
            }
            
        except Exception as e:
            end_time = time.time()
            result = {
                'model': model,
                'request_id': request_id,
                'start_time': start_time,
                'end_time': end_time,
                'duration': end_time - start_time,
                'success': False,
                'error': str(e)
            }
        
        with self.lock:
            self.results.append(result)
        
        return result
    
    def test_single_model_concurrent(self, model: str, num_requests: int = 10) -> Dict:
        """测试单个模型的并发请求"""
        print(f"\n{'='*60}")
        print(f"测试单模型并发: {model}")
        print(f"{'='*60}")
        print(f"发送 {num_requests} 个并发请求...")
        
        self.results = []
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_requests) as executor:
            futures = []
            for i in range(num_requests):
                future = executor.submit(self.make_request, model, i)
                futures.append(future)
            
            # 等待所有请求完成
            for future in as_completed(futures):
                result = future.result()
                if result['success']:
                    print(f"  ✓ 请求 {result['request_id']} 成功 ({result['duration']:.2f}s)")
                else:
                    print(f"  ✗ 请求 {result['request_id']} 失败: {result['error'][:50]}")
        
        total_time = time.time() - start_time
        
        # 分析结果
        success_count = sum(1 for r in self.results if r['success'])
        avg_duration = sum(r['duration'] for r in self.results) / len(self.results)
        
        return {
            'model': model,
            'total_requests': num_requests,
            'success_count': success_count,
            'failure_count': num_requests - success_count,
            'total_time': total_time,
            'avg_duration': avg_duration,
            'requests_per_second': num_requests / total_time,
            'results': self.results
        }
    
    def test_multi_model_parallel(self, models: List[str], requests_per_model: int = 5) -> Dict:
        """测试多个模型并行请求"""
        print(f"\n{'='*60}")
        print(f"测试多模型并行")
        print(f"{'='*60}")
        print(f"模型: {', '.join(models)}")
        print(f"每个模型发送 {requests_per_model} 个请求...")
        
        self.results = []
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=len(models) * requests_per_model) as executor:
            futures = []
            
            # 为每个模型创建请求
            for model in models:
                for i in range(requests_per_model):
                    future = executor.submit(self.make_request, model, i)
                    futures.append((model, future))
            
            # 收集结果
            model_results = {model: {'success': 0, 'failure': 0} for model in models}
            
            for model, future in futures:
                result = future.result()
                if result['success']:
                    model_results[model]['success'] += 1
                    print(f"  ✓ [{model}] 请求 {result['request_id']} 成功")
                else:
                    model_results[model]['failure'] += 1
                    print(f"  ✗ [{model}] 请求 {result['request_id']} 失败")
        
        total_time = time.time() - start_time
        total_requests = len(models) * requests_per_model
        
        return {
            'models': models,
            'requests_per_model': requests_per_model,
            'total_requests': total_requests,
            'total_time': total_time,
            'requests_per_second': total_requests / total_time,
            'model_results': model_results,
            'results': self.results
        }
    
    def analyze_results(self, single_model_results: List[Dict], multi_model_result: Dict):
        """分析测试结果"""
        print(f"\n{'='*60}")
        print("结果分析")
        print(f"{'='*60}")
        
        # 单模型测试总结
        print("\n单模型并发测试结果:")
        print("-" * 40)
        for result in single_model_results:
            print(f"{result['model']}:")
            print(f"  成功率: {result['success_count']}/{result['total_requests']} "
                  f"({result['success_count']/result['total_requests']*100:.1f}%)")
            print(f"  总耗时: {result['total_time']:.2f}s")
            print(f"  QPS: {result['requests_per_second']:.2f}")
            print(f"  平均响应时间: {result['avg_duration']:.2f}s")
        
        # 多模型测试总结
        print("\n多模型并行测试结果:")
        print("-" * 40)
        print(f"总请求数: {multi_model_result['total_requests']}")
        print(f"总耗时: {multi_model_result['total_time']:.2f}s")
        print(f"总QPS: {multi_model_result['requests_per_second']:.2f}")
        
        print("\n各模型表现:")
        for model, stats in multi_model_result['model_results'].items():
            total = stats['success'] + stats['failure']
            success_rate = stats['success'] / total * 100 if total > 0 else 0
            print(f"  {model}: {stats['success']}/{total} ({success_rate:.1f}%)")
        
        # 性能对比
        print(f"\n{'='*60}")
        print("性能对比分析")
        print(f"{'='*60}")
        
        # 计算单模型串行的预期时间
        single_serial_time = sum(r['total_time'] for r in single_model_results)
        multi_parallel_time = multi_model_result['total_time']
        speedup = single_serial_time / multi_parallel_time if multi_parallel_time > 0 else 0
        
        print(f"单模型串行总时间（理论）: {single_serial_time:.2f}s")
        print(f"多模型并行实际时间: {multi_parallel_time:.2f}s")
        print(f"加速比: {speedup:.2f}x")
        
        if speedup > 1.5:
            print("\n✅ 结论: 速率限制很可能是模型级别的!")
            print("   - 多模型并行显著快于串行")
            print("   - 建议在批量测试时并行运行多个模型")
        elif speedup > 1.1:
            print("\n⚠️ 结论: 速率限制可能是模型级别的，但效果有限")
            print("   - 多模型并行略快于串行")
            print("   - 可能存在其他瓶颈（如网络、API endpoint等）")
        else:
            print("\n❌ 结论: 速率限制可能是全局的或存在其他限制")
            print("   - 多模型并行没有明显优势")
            print("   - 建议使用串行方式避免冲突")
        
        return {
            'single_serial_time': single_serial_time,
            'multi_parallel_time': multi_parallel_time,
            'speedup': speedup
        }

def main():
    """主测试函数"""
    print("="*60)
    print("速率限制范围测试")
    print("="*60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tester = RateLimitTester()
    
    # 选择要测试的模型
    test_models = [
        'gpt-4o-mini',      # Azure模型
        'qwen2.5-3b-instruct',  # 开源模型1
        'qwen2.5-7b-instruct'   # 开源模型2
    ]
    
    # 确保模型可用
    available_models = []
    for model in test_models:
        try:
            client = tester.client_manager.get_client(model)
            if client:
                available_models.append(model)
                print(f"✓ {model} 可用")
        except:
            print(f"✗ {model} 不可用")
    
    if len(available_models) < 2:
        print("\n错误: 需要至少2个可用模型进行测试")
        return
    
    # 使用前两个可用模型
    test_models = available_models[:2]
    
    print(f"\n将使用以下模型进行测试: {', '.join(test_models)}")
    
    # 1. 测试单个模型的并发限制
    print("\n" + "="*60)
    print("步骤1: 测试单模型并发")
    print("="*60)
    
    single_model_results = []
    for model in test_models:
        result = tester.test_single_model_concurrent(model, num_requests=5)
        single_model_results.append(result)
        time.sleep(2)  # 避免请求过快
    
    # 2. 测试多个模型并行
    print("\n" + "="*60)
    print("步骤2: 测试多模型并行")
    print("="*60)
    
    time.sleep(3)  # 给API一些恢复时间
    multi_model_result = tester.test_multi_model_parallel(test_models, requests_per_model=5)
    
    # 3. 分析结果
    analysis = tester.analyze_results(single_model_results, multi_model_result)
    
    # 保存结果
    results = {
        'test_time': datetime.now().isoformat(),
        'models': test_models,
        'single_model_results': single_model_results,
        'multi_model_result': multi_model_result,
        'analysis': analysis
    }
    
    output_file = Path('rate_limit_test_results.json')
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n详细结果已保存到: {output_file}")
    
    return results

if __name__ == "__main__":
    results = main()