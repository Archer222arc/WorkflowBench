#!/usr/bin/env python3
"""高级并行测试 - 测试同一模型的多个并发连接"""

import time
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import random

import sys
sys.path.insert(0, str(Path(__file__).parent))

from api_client_manager import APIClientManager

class AdvancedParallelTester:
    def __init__(self):
        self.client_manager = APIClientManager()
        
    def test_single_connection(self, model: str, connection_id: int, num_requests: int = 5):
        """测试单个连接（模拟一个独立的测试进程）"""
        results = []
        
        for i in range(num_requests):
            start = time.time()
            try:
                client = self.client_manager.get_client(model)
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": f"Connection {connection_id}, Request {i}: Say 'ok'"}],
                    max_tokens=10,
                    temperature=0
                )
                results.append({
                    'connection_id': connection_id,
                    'request_id': i,
                    'success': True,
                    'time': time.time() - start
                })
            except Exception as e:
                results.append({
                    'connection_id': connection_id,
                    'request_id': i,
                    'success': False,
                    'time': time.time() - start,
                    'error': str(e)[:50]
                })
            
            # 小延迟避免突发
            time.sleep(0.1)
        
        return results
    
    def test_parallel_connections(self, model: str, num_connections: int = 3, requests_per_connection: int = 5):
        """测试多个并发连接到同一个模型"""
        print(f"\n测试 {num_connections} 个并发连接到 {model}")
        print(f"每个连接发送 {requests_per_connection} 个请求")
        
        all_results = []
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_connections) as executor:
            futures = []
            for conn_id in range(num_connections):
                future = executor.submit(
                    self.test_single_connection, 
                    model, 
                    conn_id, 
                    requests_per_connection
                )
                futures.append(future)
            
            for future in as_completed(futures):
                results = future.result()
                all_results.extend(results)
                success_count = sum(1 for r in results if r['success'])
                conn_id = results[0]['connection_id'] if results else -1
                print(f"  连接 {conn_id} 完成: {success_count}/{len(results)} 成功")
        
        total_time = time.time() - start_time
        total_requests = num_connections * requests_per_connection
        success_count = sum(1 for r in all_results if r['success'])
        
        return {
            'model': model,
            'num_connections': num_connections,
            'requests_per_connection': requests_per_connection,
            'total_requests': total_requests,
            'success_count': success_count,
            'total_time': total_time,
            'qps': total_requests / total_time if total_time > 0 else 0,
            'results': all_results
        }

def main():
    print("="*70)
    print("高级并行测试 - 同模型多连接")
    print("="*70)
    
    tester = AdvancedParallelTester()
    
    # 使用gpt-4o-mini进行测试
    test_model = 'gpt-4o-mini'
    
    print(f"\n测试模型: {test_model}")
    
    # 测试1: 单连接基准
    print("\n" + "="*50)
    print("测试1: 单连接基准")
    print("="*50)
    
    single_start = time.time()
    single_results = tester.test_single_connection(test_model, 0, num_requests=10)
    single_time = time.time() - single_start
    single_success = sum(1 for r in single_results if r['success'])
    
    print(f"单连接完成: {single_success}/10 成功")
    print(f"耗时: {single_time:.2f}s")
    print(f"QPS: {10/single_time:.2f}")
    
    # 测试2: 多连接并发（模拟多个模型）
    print("\n" + "="*50)
    print("测试2: 多连接并发")
    print("="*50)
    
    parallel_configs = [
        (2, 5),  # 2个连接，每个5请求
        (3, 5),  # 3个连接，每个5请求
        (5, 3),  # 5个连接，每个3请求
    ]
    
    results = []
    for num_conn, req_per_conn in parallel_configs:
        print(f"\n配置: {num_conn} 连接 × {req_per_conn} 请求")
        result = tester.test_parallel_connections(test_model, num_conn, req_per_conn)
        results.append(result)
        
        print(f"总结:")
        print(f"  总请求: {result['total_requests']}")
        print(f"  成功: {result['success_count']}")
        print(f"  耗时: {result['total_time']:.2f}s")
        print(f"  QPS: {result['qps']:.2f}")
        
        # 计算加速比
        expected_serial_time = single_time * num_conn * req_per_conn / 10
        speedup = expected_serial_time / result['total_time'] if result['total_time'] > 0 else 0
        print(f"  加速比: {speedup:.2f}x (相对于串行)")
        
        time.sleep(2)  # 避免过快
    
    # 最终分析
    print("\n" + "="*70)
    print("分析结论")
    print("="*70)
    
    print("\nQPS对比:")
    print(f"  单连接QPS: {10/single_time:.2f}")
    for i, result in enumerate(results):
        config = parallel_configs[i]
        print(f"  {config[0]}连接并发QPS: {result['qps']:.2f} "
              f"(提升 {result['qps']/(10/single_time):.2f}x)")
    
    # 判断是否支持并发
    avg_qps_improvement = sum(r['qps']/(10/single_time) for r in results) / len(results)
    
    print(f"\n平均QPS提升: {avg_qps_improvement:.2f}x")
    
    if avg_qps_improvement > 1.5:
        print("\n✅ 结论: Azure API支持同模型的多连接并发!")
        print("   这意味着:")
        print("   1. 可以通过多个并发连接提高单个模型的测试吞吐量")
        print("   2. 不同模型之间的并发更是没有问题")
        print("   3. 建议使用多线程/多进程并行测试策略")
    elif avg_qps_improvement > 1.2:
        print("\n⚠️ 结论: Azure API部分支持并发")
        print("   可能存在一些限制，但仍有优化空间")
    else:
        print("\n❌ 结论: Azure API可能有严格的并发限制")
        print("   建议使用串行方式或控制并发数")
    
    # 保存结果
    output = {
        'timestamp': datetime.now().isoformat(),
        'model': test_model,
        'single_connection': {
            'time': single_time,
            'qps': 10/single_time,
            'success': single_success
        },
        'parallel_tests': results,
        'conclusion': {
            'avg_qps_improvement': avg_qps_improvement,
            'supports_parallel': avg_qps_improvement > 1.5
        }
    }
    
    output_file = Path('model_parallel_advanced_results.json')
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n详细结果已保存到: {output_file}")

if __name__ == "__main__":
    main()