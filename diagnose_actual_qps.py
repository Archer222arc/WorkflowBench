#!/usr/bin/env python3
"""
诊断实际的QPS情况和限流问题
"""

import time
import json
from pathlib import Path
from datetime import datetime
import threading

def analyze_qps_timing():
    """分析QPS时序问题"""
    print("=" * 80)
    print("QPS时序分析")
    print("=" * 80)
    
    print("\n1. 理论QPS设置：")
    print("  - IdealLab限制：10 QPS")
    print("  - 3个API keys")
    print("  - 理论总QPS：30")
    
    print("\n2. 实际场景分析：")
    print("  如果5个qwen模型同时运行：")
    print("  - 5个模型 × 3个keys = 15个并发进程")
    print("  - 每个key被5个进程使用")
    
    print("\n3. 关键问题识别：")
    print("  ⚠️ 即使修复了模型冲突，每个key仍然被多个进程使用")
    print("  例如：")
    print("    - qwen2.5-72b 使用 key0")
    print("    - qwen2.5-32b 使用 key1") 
    print("    - qwen2.5-14b 使用 key2")
    print("    - qwen2.5-7b 使用 key0（又是key0！）")
    print("    - qwen2.5-3b 使用 key1（又是key1！）")

def check_actual_state_files():
    """检查实际的state文件"""
    print("\n" + "=" * 80)
    print("检查当前State文件")
    print("=" * 80)
    
    state_dir = Path("/tmp/qps_limiter")
    if not state_dir.exists():
        print("State目录不存在")
        return []
    
    state_files = list(state_dir.glob("*.json"))
    
    if not state_files:
        print("没有找到state文件")
        return []
    
    print(f"\n找到 {len(state_files)} 个state文件：")
    
    active_files = []
    for f in sorted(state_files):
        try:
            with open(f, 'r') as fp:
                data = json.load(fp)
                timestamp = data.get('last_request_time', 0)
                pid = data.get('pid', 'unknown')
                age = time.time() - timestamp if timestamp > 0 else float('inf')
                
                if age < 60:  # 最近60秒内活跃
                    active_files.append(f.name)
                    print(f"\n✅ {f.name}:")
                    print(f"    最后请求: {age:.1f}秒前")
                    print(f"    进程ID: {pid}")
                else:
                    print(f"\n⚪ {f.name}: （{age:.0f}秒前，已过期）")
        except Exception as e:
            print(f"\n❌ {f.name}: 读取失败 - {e}")
    
    return active_files

def analyze_key_distribution():
    """分析key分配情况"""
    print("\n" + "=" * 80)
    print("API Key使用分析")
    print("=" * 80)
    
    print("\n当前3个API keys的理想分配：")
    print("  Key0: 10 QPS")
    print("  Key1: 10 QPS")
    print("  Key2: 10 QPS")
    print("  总计: 30 QPS")
    
    print("\n实际情况（5个模型并发）：")
    models = ["qwen2.5-72b", "qwen2.5-32b", "qwen2.5-14b", "qwen2.5-7b", "qwen2.5-3b"]
    
    key_usage = {0: [], 1: [], 2: []}
    
    # 模拟ultra_parallel_runner的分配逻辑
    for i, model in enumerate(models):
        # 每个模型创建3个分片，分别使用key0/1/2
        for key_idx in range(3):
            key_usage[key_idx].append(f"{model}-shard{key_idx}")
    
    print("\n每个Key的负载：")
    for key_idx, users in key_usage.items():
        print(f"\n  Key{key_idx} ({len(users)}个用户):")
        for user in users[:3]:  # 只显示前3个
            print(f"    - {user}")
        if len(users) > 3:
            print(f"    ... 还有{len(users)-3}个")

def propose_solutions():
    """提出解决方案"""
    print("\n" + "=" * 80)
    print("解决方案建议")
    print("=" * 80)
    
    print("\n方案1：降低QPS设置")
    print("  将每个key的QPS从10降到5")
    print("  修改 qps_limiter.py:")
    print("    elif 'ideallab' in provider:")
    print("        qps = 5  # 从10降到5")
    
    print("\n方案2：限制并发模型数")
    print("  同时只运行2-3个qwen模型")
    print("  或者串行执行不同模型")
    
    print("\n方案3：增加启动延迟")
    print("  每个模型启动间隔30秒")
    print("  避免瞬时请求峰值")
    
    print("\n方案4：实现全局QPS协调器")
    print("  所有qwen请求共享一个总QPS池")
    print("  动态分配QPS配额")

def simulate_real_qps():
    """模拟真实的QPS情况"""
    print("\n" + "=" * 80)
    print("模拟真实QPS情况")
    print("=" * 80)
    
    from qps_limiter import get_qps_limiter
    
    print("\n模拟3个模型同时使用同一个key：")
    
    def simulate_model(model_name, key_index, num_requests=5):
        """模拟一个模型的请求"""
        limiter = get_qps_limiter(model_name, qps=10, key_index=key_index)
        
        for i in range(num_requests):
            start = time.time()
            limiter.acquire()
            wait = time.time() - start
            
            if i == 0:
                print(f"{model_name}: 第1个请求等待 {wait:.3f}秒")
    
    # 模拟3个模型都使用key0
    models = [
        "qwen2.5-72b-instruct",
        "qwen2.5-7b-instruct",
        "qwen2.5-3b-instruct"
    ]
    
    threads = []
    start_time = time.time()
    
    for model in models:
        t = threading.Thread(target=simulate_model, args=(model, 0, 3))
        threads.append(t)
        t.start()
        time.sleep(0.01)  # 轻微错开
    
    for t in threads:
        t.join()
    
    total_time = time.time() - start_time
    total_requests = 3 * 3  # 3个模型，每个3个请求
    
    print(f"\n结果：")
    print(f"  总请求数: {total_requests}")
    print(f"  总耗时: {total_time:.2f}秒")
    print(f"  实际QPS: {total_requests/total_time:.1f}")
    print(f"  理论QPS: 10（单key限制）")
    
    if total_requests/total_time > 11:
        print("\n⚠️ 问题：QPS超过单key限制！")
        print("   可能原因：不同模型的state文件是独立的")
        print("   但API服务器看到的是同一个key的请求！")
    else:
        print("\n✅ QPS控制正常")

if __name__ == "__main__":
    # 分析时序
    analyze_qps_timing()
    
    # 检查state文件
    active_files = check_actual_state_files()
    
    # 分析key分配
    analyze_key_distribution()
    
    # 模拟QPS
    print("\n是否模拟QPS测试？(输入y确认，其他跳过): ", end="")
    try:
        if input().strip().lower() == 'y':
            simulate_real_qps()
    except:
        print("跳过模拟")
    
    # 提出解决方案
    propose_solutions()
    
    print("\n" + "=" * 80)
    print("关键发现")
    print("=" * 80)
    print("\n问题根源：")
    print("1. 虽然不同模型使用独立的state文件")
    print("2. 但API服务器端看到的是同一个API key的请求")
    print("3. 服务器端的限流是基于API key，不是基于state文件")
    print("\n结论：")
    print("✅ 客户端QPS控制正常工作")
    print("❌ 但服务器端仍然会限流，因为：")
    print("   - 3个API keys被15个进程使用")
    print("   - 每个key实际承载5个进程的请求")
    print("   - 服务器看到每个key的QPS = 5个进程 × 各自QPS")
    print("\n建议：")
    print("1. 降低QPS设置到2-3")
    print("2. 或减少并发模型数量")
    print("3. 或实现更智能的全局QPS协调")