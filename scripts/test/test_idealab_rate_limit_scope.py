#!/usr/bin/env python3
"""
测试IdealLab API的速率限制范围
================================
测试多个Qwen模型，判断速率限制是模型级别还是API key级别
"""

import time
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from collections import defaultdict
import sys

sys.path.insert(0, str(Path(__file__).parent))

from api_client_manager import APIClientManager

class IdealLabRateLimitTester:
    def __init__(self):
        self.client_manager = APIClientManager()
        
        # IdealLab的Qwen模型
        self.qwen_models = [
            'qwen2.5-3b-instruct',
            'qwen2.5-7b-instruct',
            'qwen2.5-14b-instruct',
            'qwen2.5-32b-instruct'
        ]
        
        # 测试结果收集
        self.results = defaultdict(list)
        
    def test_single_request(self, model: str, request_id: int, delay: float = 0):
        """发送单个测试请求"""
        if delay > 0:
            time.sleep(delay)
            
        start_time = time.time()
        try:
            client = self.client_manager.get_client(model)
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": f"Test {request_id}: Return 'ok'"}],
                max_tokens=10,
                temperature=0
            )
            
            elapsed = time.time() - start_time
            return {
                'model': model,
                'request_id': request_id,
                'success': True,
                'time': elapsed,
                'timestamp': time.time()
            }
        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = str(e)
            is_rate_limit = 'rate' in error_msg.lower() or '429' in error_msg
            
            return {
                'model': model,
                'request_id': request_id,
                'success': False,
                'time': elapsed,
                'timestamp': time.time(),
                'error': error_msg[:100],
                'is_rate_limit': is_rate_limit
            }
    
    def test_same_model_parallel(self, model: str, num_parallel: int = 5):
        """测试同一模型的并行请求"""
        print(f"\n{'='*60}")
        print(f"测试1: 同一模型({model})的{num_parallel}个并行请求")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_parallel) as executor:
            futures = []
            for i in range(num_parallel):
                future = executor.submit(self.test_single_request, model, i)
                futures.append(future)
            
            results = []
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                status = "✓" if result['success'] else "✗"
                print(f"  {status} 请求{result['request_id']}: {result['time']:.2f}s", end="")
                if not result['success'] and result.get('is_rate_limit'):
                    print(" [速率限制]", end="")
                print()
        
        total_time = time.time() - start_time
        success_count = sum(1 for r in results if r['success'])
        
        print(f"\n结果:")
        print(f"  总时间: {total_time:.2f}s")
        print(f"  成功: {success_count}/{num_parallel}")
        print(f"  平均响应: {sum(r['time'] for r in results)/len(results):.2f}s")
        
        # 分析并发性
        if total_time < (sum(r['time'] for r in results) * 0.8):
            print(f"  ✅ 检测到并行执行")
        else:
            print(f"  ⚠️ 可能是串行执行")
        
        return results
    
    def test_different_models_parallel(self, num_requests_per_model: int = 3):
        """测试不同Qwen模型的并行请求"""
        print(f"\n{'='*60}")
        print(f"测试2: 不同Qwen模型并行 (每个模型{num_requests_per_model}个请求)")
        print(f"模型: {', '.join(self.qwen_models)}")
        print(f"{'='*60}")
        
        start_time = time.time()
        all_results = []
        
        with ThreadPoolExecutor(max_workers=len(self.qwen_models) * num_requests_per_model) as executor:
            futures = []
            
            # 为每个模型提交多个请求
            for model in self.qwen_models:
                for i in range(num_requests_per_model):
                    future = executor.submit(self.test_single_request, model, i)
                    futures.append((future, model))
            
            # 收集结果
            model_results = defaultdict(list)
            for future, model in futures:
                result = future.result()
                all_results.append(result)
                model_results[model].append(result)
        
        total_time = time.time() - start_time
        
        # 分析每个模型的结果
        print("\n各模型结果:")
        for model in self.qwen_models:
            results = model_results[model]
            success = sum(1 for r in results if r['success'])
            avg_time = sum(r['time'] for r in results) / len(results)
            print(f"  {model}: {success}/{len(results)} 成功, 平均{avg_time:.2f}s")
        
        # 分析整体并发性
        total_requests = len(self.qwen_models) * num_requests_per_model
        total_success = sum(1 for r in all_results if r['success'])
        
        print(f"\n整体结果:")
        print(f"  总请求: {total_requests}")
        print(f"  总成功: {total_success}")
        print(f"  总时间: {total_time:.2f}s")
        print(f"  QPS: {total_requests/total_time:.2f}")
        
        # 判断是否共享速率限制
        if total_time > (num_requests_per_model * 2):  # 如果时间明显长于预期
            print(f"\n⚠️ 不同Qwen模型可能共享速率限制")
        else:
            print(f"\n✅ 不同Qwen模型可能有独立速率限制")
        
        return all_results
    
    def test_burst_then_continuous(self, model: str, burst_size: int = 10, continuous_size: int = 10):
        """测试突发请求后的持续请求"""
        print(f"\n{'='*60}")
        print(f"测试3: 突发请求后持续请求 ({model})")
        print(f"突发: {burst_size}个, 持续: {continuous_size}个")
        print(f"{'='*60}")
        
        # 阶段1: 突发请求
        print("\n阶段1: 突发请求")
        burst_start = time.time()
        
        with ThreadPoolExecutor(max_workers=burst_size) as executor:
            futures = [executor.submit(self.test_single_request, model, i) for i in range(burst_size)]
            burst_results = [f.result() for f in as_completed(futures)]
        
        burst_time = time.time() - burst_start
        burst_success = sum(1 for r in burst_results if r['success'])
        print(f"  完成: {burst_success}/{burst_size} 成功, 耗时{burst_time:.2f}s")
        
        # 等待一下
        print("\n等待2秒...")
        time.sleep(2)
        
        # 阶段2: 持续请求（串行）
        print("\n阶段2: 持续请求（串行）")
        continuous_results = []
        continuous_start = time.time()
        
        for i in range(continuous_size):
            result = self.test_single_request(model, burst_size + i)
            status = "✓" if result['success'] else "✗"
            print(f"  {status} 请求{i}: {result['time']:.2f}s")
            continuous_results.append(result)
            
            # 如果失败了，等待一下
            if not result['success'] and result.get('is_rate_limit'):
                print("    检测到速率限制，等待1秒...")
                time.sleep(1)
        
        continuous_time = time.time() - continuous_start
        continuous_success = sum(1 for r in continuous_results if r['success'])
        
        print(f"\n持续阶段结果:")
        print(f"  成功: {continuous_success}/{continuous_size}")
        print(f"  耗时: {continuous_time:.2f}s")
        print(f"  平均: {continuous_time/continuous_size:.2f}s/请求")
        
        return burst_results, continuous_results
    
    def test_cross_model_interleaved(self):
        """交错测试不同模型"""
        print(f"\n{'='*60}")
        print(f"测试4: 交错请求不同Qwen模型")
        print(f"{'='*60}")
        
        # 创建交错的请求序列
        requests = []
        for i in range(3):  # 每个模型3个请求
            for model in self.qwen_models:
                requests.append((model, i))
        
        print(f"请求序列: {len(requests)}个请求，交错4个模型")
        
        results = []
        start_time = time.time()
        
        # 串行发送，观察响应时间
        for model, req_id in requests:
            result = self.test_single_request(model, req_id)
            status = "✓" if result['success'] else "✗"
            print(f"  {status} {model:20s} 请求{req_id}: {result['time']:.2f}s")
            results.append(result)
            
            # 极短延迟，避免本地限制
            time.sleep(0.1)
        
        total_time = time.time() - start_time
        
        # 分析结果
        model_stats = defaultdict(lambda: {'success': 0, 'total': 0, 'times': []})
        for r in results:
            model = r['model']
            model_stats[model]['total'] += 1
            model_stats[model]['times'].append(r['time'])
            if r['success']:
                model_stats[model]['success'] += 1
        
        print(f"\n统计:")
        print(f"  总时间: {total_time:.2f}s")
        print(f"  总请求: {len(results)}")
        print(f"  QPS: {len(results)/total_time:.2f}")
        
        print(f"\n各模型统计:")
        for model, stats in model_stats.items():
            avg_time = sum(stats['times']) / len(stats['times'])
            print(f"  {model}: {stats['success']}/{stats['total']} 成功, 平均{avg_time:.2f}s")
        
        # 判断
        avg_response_time = sum(r['time'] for r in results) / len(results)
        if avg_response_time > 1.0:  # 如果平均响应时间很长
            print(f"\n⚠️ 响应时间较长，可能存在共享速率限制")
        else:
            print(f"\n✅ 响应时间正常")
        
        return results
    
    def run_comprehensive_test(self):
        """运行全面测试"""
        print("="*70)
        print("IdealLab API 速率限制范围测试")
        print("="*70)
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"测试模型: {', '.join(self.qwen_models)}")
        
        # 检查模型可用性
        print("\n检查模型可用性...")
        available_models = []
        for model in self.qwen_models:
            try:
                result = self.test_single_request(model, -1)
                if result['success']:
                    available_models.append(model)
                    print(f"  ✓ {model}")
                else:
                    print(f"  ✗ {model}: {result.get('error', 'Unknown error')[:50]}")
            except Exception as e:
                print(f"  ✗ {model}: {str(e)[:50]}")
        
        if len(available_models) < 2:
            print("\n❌ 可用模型不足，无法进行对比测试")
            return
        
        print(f"\n可用模型: {len(available_models)}/{len(self.qwen_models)}")
        
        # 使用可用模型进行测试
        self.qwen_models = available_models
        
        # 测试1: 同模型并行
        if available_models:
            self.test_same_model_parallel(available_models[0], 5)
        
        # 测试2: 不同模型并行
        if len(available_models) >= 2:
            time.sleep(3)  # 休息一下
            self.test_different_models_parallel(3)
        
        # 测试3: 突发测试
        if available_models:
            time.sleep(3)
            self.test_burst_then_continuous(available_models[0], 5, 5)
        
        # 测试4: 交错测试
        if len(available_models) >= 2:
            time.sleep(3)
            self.test_cross_model_interleaved()
        
        # 最终结论
        print("\n" + "="*70)
        print("测试结论")
        print("="*70)
        print("\n基于测试结果：")
        print("1. 如果不同Qwen模型的并行测试明显比单模型慢 → API key级别限制")
        print("2. 如果不同Qwen模型可以独立并行 → 模型级别限制")
        print("3. 如果交错请求导致所有模型变慢 → API key级别限制")
        print("\n请根据上述测试结果判断IdealLab的速率限制范围。")


def main():
    tester = IdealLabRateLimitTester()
    tester.run_comprehensive_test()


if __name__ == "__main__":
    main()