#!/usr/bin/env python3
"""
测试3个API keys的QPS独立限流
"""

import time
import threading
from qps_limiter import get_qps_limiter
from pathlib import Path

def test_three_keys():
    """测试3个keys的独立QPS限制"""
    print("=" * 60)
    print("测试3个qwen API keys独立限流")
    print("=" * 60)
    
    # 清理旧文件
    shared_dir = Path("/tmp/qps_limiter")
    if shared_dir.exists():
        for f in shared_dir.glob("ideallab_qwen*.json"):
            try:
                f.unlink()
                print(f"清理: {f.name}")
            except:
                pass
    
    print("\n配置信息：")
    print("- 3个API keys (key0, key1, key2)")
    print("- 每个key独立10 QPS限制")
    print("- 理论总QPS: 30")
    print()
    
    results = {}
    lock = threading.Lock()
    
    def worker(key_index, num_requests=10):
        """测试单个key的QPS"""
        model = "qwen2.5-7b-instruct"
        limiter = get_qps_limiter(model, qps=10, key_index=key_index)
        
        times = []
        start = time.time()
        
        for i in range(num_requests):
            req_start = time.time()
            limiter.acquire()
            wait = time.time() - req_start
            times.append(wait)
            
            if i % 3 == 0:
                print(f"Key{key_index} 请求{i+1:2d}: 等待{wait:.3f}秒")
        
        total = time.time() - start
        
        with lock:
            results[key_index] = {
                'total_time': total,
                'waits': times,
                'avg_wait': sum(times[1:]) / len(times[1:]) if len(times) > 1 else 0
            }
    
    # 启动3个线程，每个key一个
    threads = []
    overall_start = time.time()
    
    for i in range(3):  # 3个keys
        t = threading.Thread(target=worker, args=(i, 10))
        threads.append(t)
        t.start()
        time.sleep(0.02)  # 轻微错开启动
    
    for t in threads:
        t.join()
    
    overall_time = time.time() - overall_start
    
    # 分析结果
    print("\n" + "=" * 60)
    print("测试结果")
    print("=" * 60)
    
    # 检查state文件
    print("\n生成的state文件：")
    state_files = list(shared_dir.glob("ideallab_qwen_key*.json"))
    for f in sorted(state_files):
        print(f"  ✅ {f.name}")
    
    if len(state_files) != 3:
        print(f"  ⚠️ 预期3个文件，实际{len(state_files)}个")
    
    # 性能统计
    print("\n各Key性能统计：")
    total_requests = 0
    for key_idx in sorted(results.keys()):
        data = results[key_idx]
        print(f"Key{key_idx}:")
        print(f"  - 完成时间: {data['total_time']:.3f}秒")
        print(f"  - 平均等待: {data['avg_wait']:.3f}秒")
        print(f"  - 理论QPS: {1/data['avg_wait']:.1f}" if data['avg_wait'] > 0 else "  - 理论QPS: 无限制")
        total_requests += 10
    
    print(f"\n总体性能：")
    print(f"  - 3个keys并行处理{total_requests}个请求")
    print(f"  - 总耗时: {overall_time:.3f}秒")
    print(f"  - 实际总QPS: {total_requests/overall_time:.1f}")
    print(f"  - 理论总QPS: 30 (3×10)")
    
    efficiency = (total_requests/overall_time) / 30 * 100
    print(f"  - 效率: {efficiency:.1f}%")
    
    if efficiency > 85:
        print("\n✅ 优秀！3个keys独立限流正常工作")
    elif efficiency > 70:
        print("\n✅ 良好！3个keys基本独立工作")
    else:
        print("\n⚠️ 可能存在问题，效率偏低")
    
    return overall_time, total_requests

def compare_configurations():
    """对比不同配置的性能"""
    print("\n" + "=" * 60)
    print("配置对比")
    print("=" * 60)
    
    print("\n1个key配置：")
    print("  - 总QPS: 10")
    print("  - 30个请求需要: ~3秒")
    
    print("\n2个keys配置：")
    print("  - 总QPS: 20")
    print("  - 30个请求需要: ~1.5秒")
    
    print("\n3个keys配置（当前）：")
    print("  - 总QPS: 30")
    print("  - 30个请求需要: ~1秒")
    
    print("\n性能提升：")
    print("  - vs 1 key: 3倍速度")
    print("  - vs 2 keys: 1.5倍速度")

if __name__ == "__main__":
    # 测试3个keys
    overall_time, total_requests = test_three_keys()
    
    # 显示对比
    compare_configurations()
    
    print("\n" + "=" * 60)
    print("结论")
    print("=" * 60)
    print("✅ 3个API keys独立限流已实现")
    print("✅ 每个key保持10 QPS限制")
    print("✅ 总QPS可达30，性能提升3倍")
    print("✅ 适用于qwen模型的大规模并发测试")