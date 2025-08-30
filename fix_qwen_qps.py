#!/usr/bin/env python3
"""
修复 Qwen QPS 控制，让每个 API key 独立限流
"""

def analyze_current_issue():
    """分析当前问题"""
    print("=" * 60)
    print("当前 Qwen QPS 控制问题分析")
    print("=" * 60)
    
    print("\n1. 当前实现的问题：")
    print("   - 所有 qwen 请求共享一个 state 文件")
    print("   - 文件：/tmp/qps_limiter/ideallab_qwen_qps_state.json")
    print("   - 结果：2个 API keys 总共只有 10 QPS")
    print("   - 期望：每个 key 10 QPS，总共 20 QPS")
    
    print("\n2. 实际效果：")
    print("   qwen-key0: 等待共享文件 → 10 QPS")
    print("   qwen-key1: 也等待同一个文件 → 被串行化")
    print("   总 QPS = 10（没有发挥多 key 优势）")
    
    print("\n3. 修复方案：")
    print("   方案A：每个 key 独立的 state 文件")
    print("   方案B：state 文件中记录每个 key 的时间戳")
    print("   方案C：完全移除跨进程同步（依赖进程内限流）")

def proposed_fix():
    """提出修复方案"""
    print("\n" + "=" * 60)
    print("推荐修复方案")
    print("=" * 60)
    
    fix_code = '''
# 修改 qps_limiter.py 的 get_qps_limiter 函数

def get_qps_limiter(model: str, qps: Optional[float] = None, key_index: Optional[int] = None) -> QPSLimiter:
    """获取QPS限制器实例
    
    Args:
        model: 模型名称
        qps: QPS限制
        key_index: API key 索引（用于多key并行）
    """
    global _limiters
    
    # 判断provider
    if any(x in model.lower() for x in ['deepseek', 'llama', 'gpt']):
        provider = "azure"
    elif "qwen" in model.lower():
        # 如果有key_index，创建独立的provider标识
        if key_index is not None:
            provider = f"ideallab_qwen_key{key_index}"
        else:
            provider = "ideallab_qwen"
    # ... 其他逻辑不变
    
    # 这样每个key会有独立的limiter实例和state文件
    key = f"{provider}_{qps}"
    if key not in _limiters:
        _limiters[key] = QPSLimiter(qps, provider)
    
    return _limiters[key]
'''
    print(fix_code)
    
    print("\n修复后的效果：")
    print("- qwen-key0 → /tmp/qps_limiter/ideallab_qwen_key0_qps_state.json")
    print("- qwen-key1 → /tmp/qps_limiter/ideallab_qwen_key1_qps_state.json")
    print("- 每个 key 独立限流 10 QPS")
    print("- 总计可达 20 QPS")

def test_qps_behavior():
    """测试 QPS 行为"""
    print("\n" + "=" * 60)
    print("QPS 测试方案")
    print("=" * 60)
    
    test_script = '''
import time
import threading
from qps_limiter import get_qps_limiter

def test_key(key_index, num_requests=10):
    """测试单个 key 的 QPS"""
    limiter = get_qps_limiter("qwen2.5-7b-instruct", key_index=key_index)
    
    times = []
    for i in range(num_requests):
        start = time.time()
        limiter.acquire()
        elapsed = time.time() - start
        times.append(elapsed)
        print(f"Key{key_index} Request{i}: waited {elapsed:.3f}s")
    
    avg_wait = sum(times[1:]) / len(times[1:]) if len(times) > 1 else 0
    print(f"Key{key_index} 平均等待: {avg_wait:.3f}s")
    return times

# 并行测试两个 keys
threads = []
for i in range(2):
    t = threading.Thread(target=test_key, args=(i, 10))
    threads.append(t)
    t.start()

for t in threads:
    t.join()
'''
    print("测试脚本：")
    print(test_script)

if __name__ == "__main__":
    analyze_current_issue()
    proposed_fix()
    test_qps_behavior()
    
    print("\n" + "=" * 60)
    print("总结")
    print("=" * 60)
    print("1. 当前 qwen 的 QPS 控制是有效的，但没有充分利用多 key")
    print("2. 所有 keys 共享同一个限流器，导致总 QPS = 10")
    print("3. 修复后每个 key 独立限流，总 QPS 可达 20")
    print("4. 这解释了为什么 qwen 测试比预期慢")