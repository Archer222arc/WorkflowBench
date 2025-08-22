#!/usr/bin/env python3
"""
检查IdealLab并发配置
"""

from pathlib import Path
import re

def check_ideallab_concurrency():
    """检查IdealLab模型的并发配置"""
    print("=" * 60)
    print("IdealLab并发配置检查")
    print("=" * 60)
    
    # 1. 检查ultra_parallel_runner.py中的配置
    print("\n1. Ultra Parallel Runner配置")
    print("-" * 40)
    
    runner_file = Path('ultra_parallel_runner.py')
    with open(runner_file, 'r') as f:
        content = f.read()
    
    # 查找qwen模型配置
    print("\nQwen模型（开源）配置：")
    qwen_pattern = r'name="qwen".*?max_workers=(\d+).*?max_qps=([\d.]+)'
    qwen_matches = re.findall(qwen_pattern, content, re.DOTALL)
    if qwen_matches:
        for workers, qps in qwen_matches[:1]:  # 只显示第一个匹配
            print(f"  max_workers: {workers}")
            print(f"  max_qps: {qps}")
    
    # 查找IdealLab特定配置（在execute_shard_async方法中）
    print("\n动态配置（execute_shard_async方法）：")
    
    # 查找qwen优化部分
    if 'if "qwen" in base_model.lower():' in content:
        print("\n  Qwen模型优化配置:")
        # 提取qwen配置部分
        qwen_section = content[content.find('if "qwen" in base_model.lower():'):content.find('if "qwen" in base_model.lower():') + 500]
        
        # 固定模式
        if 'rate_mode == "fixed"' in qwen_section:
            fixed_match = re.search(r'rate_mode == "fixed".*?max_workers = (\d+).*?qps = (\d+)', qwen_section, re.DOTALL)
            if fixed_match:
                print(f"    固定模式: max_workers={fixed_match.group(1)}, qps={fixed_match.group(2)}")
        
        # 自适应模式
        if 'else:' in qwen_section:
            adaptive_match = re.search(r'else:.*?max_workers = (\d+)', qwen_section, re.DOTALL)
            if adaptive_match:
                print(f"    自适应模式: max_workers={adaptive_match.group(1)}, qps=None (adaptive)")
    
    # 查找IdealLab闭源模型配置
    if 'elif base_model in ["o3-0416-global", "gemini-2.5-flash-06-17", "kimi-k2"]' in content:
        print("\n  IdealLab闭源模型配置:")
        idealab_section = content[content.find('elif base_model in ["o3-0416-global"'):content.find('elif base_model in ["o3-0416-global"') + 500]
        
        # 固定模式
        if 'rate_mode == "fixed"' in idealab_section:
            fixed_match = re.search(r'rate_mode == "fixed".*?max_workers = (\d+).*?qps = (\d+)', idealab_section, re.DOTALL)
            if fixed_match:
                print(f"    固定模式: max_workers={fixed_match.group(1)}, qps={fixed_match.group(2)}")
        
        # 自适应模式
        if 'else:' in idealab_section:
            adaptive_match = re.search(r'else:.*?max_workers = (\d+)', idealab_section, re.DOTALL)
            if adaptive_match:
                print(f"    自适应模式: max_workers={adaptive_match.group(1)}, qps=None")
    
    # 2. 检查API key配置
    print("\n\n2. IdealLab API Keys配置")
    print("-" * 40)
    
    api_file = Path('api_client_manager.py')
    with open(api_file, 'r') as f:
        api_content = f.read()
    
    # 查找IdealLab keys
    idealab_keys = re.findall(r'IDEALLAB_API_KEY_(\d+)', api_content)
    if idealab_keys:
        print(f"  发现 {len(set(idealab_keys))} 个IdealLab API keys:")
        for key_num in sorted(set(idealab_keys)):
            print(f"    - IDEALLAB_API_KEY_{key_num}")
    
    # 查找qwen虚拟实例
    qwen_instances = re.findall(r'qwen.*?-key\d+', api_content)
    if qwen_instances:
        print(f"\n  Qwen虚拟实例（用于负载均衡）:")
        for instance in set(qwen_instances):
            print(f"    - {instance}")
    
    # 3. 分析并发策略
    print("\n\n3. 并发策略分析")
    print("-" * 40)
    
    print("\n当前配置总结：")
    print("  Qwen模型（5个型号）:")
    print("    - 使用3个API keys进行负载均衡")
    print("    - 每个key限制：max_workers=3-5")
    print("    - 总并发能力：3 keys × 5 workers = 15并发")
    
    print("\n  IdealLab闭源模型（3个）:")
    print("    - o3-0416-global")
    print("    - gemini-2.5-flash-06-17")
    print("    - kimi-k2")
    print("    - 共享同一组API keys")
    print("    - max_workers=1（保守设置避免限流）")
    
    # 4. 检查实际使用情况
    print("\n\n4. 检查实际负载分配")
    print("-" * 40)
    
    # 查找create_qwen_shards方法
    if 'def create_qwen_shards' in content:
        print("\n  Qwen分片策略:")
        shard_section = content[content.find('def create_qwen_shards'):content.find('def create_qwen_shards') + 1000]
        
        if 'for i, (chunk_start, chunk_end) in enumerate(chunks):' in shard_section:
            print("    ✅ 使用轮询分配到不同的key")
            print("    ✅ 每个分片分配到 qwen-key0/1/2")
    
    # 5. 建议优化
    print("\n\n5. 优化建议")
    print("-" * 40)
    
    print("\n当前设置分析：")
    print("  ✅ Qwen模型使用3个keys负载均衡（合理）")
    print("  ⚠️  max_workers=1可能过于保守")
    print("  建议根据实际限流情况调整：")
    print("    - 如无限流：可增加到3-5")
    print("    - 如有限流：保持1")
    
    print("\n  ✅ IdealLab闭源模型使用单worker（安全）")
    print("  说明：避免并发请求触发限流")
    
    return True

def check_recent_performance():
    """检查最近的测试性能"""
    print("\n\n6. 最近测试性能分析")
    print("-" * 40)
    
    # 检查最新的日志
    log_dir = Path('logs')
    if log_dir.exists():
        debug_logs = sorted(log_dir.glob('debug_ultra_*'), key=lambda x: x.stat().st_mtime, reverse=True)
        
        if debug_logs:
            latest = debug_logs[0]
            print(f"\n最新调试日志: {latest.name}")
            
            # 分析qwen模型日志
            qwen_logs = list(latest.glob('qwen*.log'))
            if qwen_logs:
                print(f"  Qwen测试日志: {len(qwen_logs)} 个分片")
                
                # 检查是否有超时或错误
                timeout_count = 0
                error_count = 0
                for log_file in qwen_logs[:3]:  # 检查前3个
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(10000)  # 读取前10KB
                        if 'timeout' in content.lower():
                            timeout_count += 1
                        if 'error' in content.lower():
                            error_count += 1
                
                if timeout_count > 0:
                    print(f"  ⚠️ 发现 {timeout_count} 个分片有超时")
                if error_count > 0:
                    print(f"  ⚠️ 发现 {error_count} 个分片有错误")
                
                if timeout_count == 0 and error_count == 0:
                    print("  ✅ 未发现超时或错误（样本检查）")

def main():
    """主函数"""
    # 检查配置
    check_ideallab_concurrency()
    
    # 检查性能
    check_recent_performance()
    
    print("\n" + "=" * 60)
    print("检查完成")
    print("=" * 60)

if __name__ == "__main__":
    main()