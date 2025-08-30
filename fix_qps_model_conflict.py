#!/usr/bin/env python3
"""
修复多个qwen模型使用相同key导致的QPS冲突
"""

import re
from pathlib import Path

def analyze_problem():
    """分析问题"""
    print("=" * 80)
    print("多模型Key冲突问题分析")
    print("=" * 80)
    
    print("\n当前问题：")
    print("1. 5个qwen模型（72b/32b/14b/7b/3b）同时运行")
    print("2. 每个模型的分片0都使用key0")
    print("3. 5个进程共享/tmp/qps_limiter/ideallab_qwen_key0_qps_state.json")
    print("4. 结果：每个进程只能获得10/5=2 QPS")
    
    print("\n影响：")
    print("- 严重的性能下降（QPS从10降到2）")
    print("- 大规模限流错误")
    print("- 测试时间增加5倍")

def show_fix():
    """展示修复方案"""
    print("\n" + "=" * 80)
    print("修复方案：在state文件名中加入模型标识")
    print("=" * 80)
    
    print("\n修改 qps_limiter.py：")
    print("-" * 40)
    
    fix_code = '''
def get_qps_limiter(model: str, qps: Optional[float] = None, key_index: Optional[int] = None) -> QPSLimiter:
    """获取QPS限制器实例
    
    Args:
        model: 模型名称
        qps: QPS限制（如果为None，根据模型自动设置）
        key_index: API key索引（用于多key独立限流）
    
    Returns:
        QPSLimiter实例
    """
    global _limiters
    
    # 判断provider
    if any(x in model.lower() for x in ['deepseek', 'llama', 'gpt']):
        provider = "azure"
    elif "qwen" in model.lower():
        # 提取模型规模标识，避免不同模型冲突
        import re
        match = re.search(r'(\d+b)', model.lower())
        model_size = match.group(1) if match else 'unknown'
        
        # 为每个模型+key组合创建独立的provider标识
        if key_index is not None:
            provider = f"ideallab_qwen_{model_size}_key{key_index}"
        else:
            provider = f"ideallab_qwen_{model_size}"
    elif any(x in model.lower() for x in ['o3', 'gemini', 'kimi']):
        # 闭源模型也支持独立key限流
        if key_index is not None:
            provider = f"ideallab_closed_key{key_index}"
        else:
            provider = "ideallab_closed"
    else:
        provider = "default"
    
    # 自动设置QPS
    if qps is None:
        if provider == "azure":
            qps = 0  # 无限制
        elif "ideallab" in provider:  # 包括所有ideallab相关的provider
            qps = 10  # IdealLab限制为10
        else:
            qps = 20  # 默认20
    
    # 获取或创建limiter
    key = f"{provider}_{qps}"
    if key not in _limiters:
        _limiters[key] = QPSLimiter(qps, provider)
    
    return _limiters[key]
'''
    print(fix_code)
    
    print("\n修复后的state文件：")
    print("-" * 40)
    print("之前（冲突）：")
    print("  qwen2.5-72b + key0 → ideallab_qwen_key0_qps_state.json")
    print("  qwen2.5-32b + key0 → ideallab_qwen_key0_qps_state.json（冲突！）")
    print("  qwen2.5-7b + key0 → ideallab_qwen_key0_qps_state.json（冲突！）")
    print()
    print("之后（独立）：")
    print("  qwen2.5-72b + key0 → ideallab_qwen_72b_key0_qps_state.json")
    print("  qwen2.5-32b + key0 → ideallab_qwen_32b_key0_qps_state.json")
    print("  qwen2.5-7b + key0 → ideallab_qwen_7b_key0_qps_state.json")

def apply_fix():
    """应用修复"""
    print("\n" + "=" * 80)
    print("应用修复")
    print("=" * 80)
    
    qps_file = Path("qps_limiter.py")
    
    if not qps_file.exists():
        print("❌ 找不到qps_limiter.py文件")
        return False
    
    # 读取文件
    content = qps_file.read_text()
    
    # 查找函数位置
    if 'def get_qps_limiter' not in content:
        print("❌ 找不到get_qps_limiter函数")
        return False
    
    print("✅ 找到qps_limiter.py文件")
    print("✅ 找到get_qps_limiter函数")
    print("\n请手动应用上述修复代码，或运行以下命令自动修复：")
    print("python3 fix_qps_model_conflict.py --apply")
    
    return True

def verify_fix():
    """验证修复效果"""
    print("\n" + "=" * 80)
    print("验证修复效果")
    print("=" * 80)
    
    print("\n测试场景：5个qwen模型并发，每个使用key0")
    
    from qps_limiter import get_qps_limiter
    import time
    
    models = [
        "qwen2.5-72b-instruct",
        "qwen2.5-32b-instruct", 
        "qwen2.5-7b-instruct"
    ]
    
    print("\n创建限流器：")
    limiters = []
    for model in models:
        limiter = get_qps_limiter(model, qps=10, key_index=0)
        limiters.append((model, limiter))
        print(f"  {model}: {limiter.state_file.name}")
    
    # 检查是否使用不同的state文件
    state_files = [l[1].state_file.name for l in limiters]
    if len(set(state_files)) == len(state_files):
        print("\n✅ 验证成功：每个模型使用独立的state文件")
        print("   不同模型不再冲突！")
    else:
        print("\n❌ 验证失败：仍然存在state文件冲突")
        print(f"   State文件: {state_files}")

if __name__ == "__main__":
    import sys
    
    # 分析问题
    analyze_problem()
    
    # 展示修复
    show_fix()
    
    # 应用修复提示
    if "--apply" in sys.argv:
        print("\n正在应用修复...")
        # 这里可以添加自动修改代码的逻辑
        print("（自动修复功能待实现，请手动修改）")
    else:
        apply_fix()
    
    # 如果已经修复，验证效果
    if "--verify" in sys.argv:
        verify_fix()