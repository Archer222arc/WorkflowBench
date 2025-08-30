#!/usr/bin/env python3
"""
智能数据收集器配置文件
为不同的使用场景提供预设配置
"""

import os
from pathlib import Path

# 基础配置
BASE_CONFIG = {
    'temp_dir': 'temp_results',
    'adaptive_threshold': True,
    'auto_save_interval': 60,  # 1分钟
}

# 小规模测试配置（<10个测试）
SMALL_SCALE_CONFIG = {
    **BASE_CONFIG,
    'max_memory_results': 3,
    'max_time_seconds': 120,  # 2分钟
    'checkpoint_interval': 1,  # 每个测试都保存
}

# 中等规模测试配置（10-50个测试）
MEDIUM_SCALE_CONFIG = {
    **BASE_CONFIG,
    'max_memory_results': 10,
    'max_time_seconds': 300,  # 5分钟
    'checkpoint_interval': 5,
}

# 大规模测试配置（>50个测试）
LARGE_SCALE_CONFIG = {
    **BASE_CONFIG,
    'max_memory_results': 25,
    'max_time_seconds': 600,  # 10分钟
    'checkpoint_interval': 20,
}

# 超并发配置（多进程环境）
ULTRA_PARALLEL_CONFIG = {
    **BASE_CONFIG,
    'max_memory_results': 5,   # 更小的内存阈值
    'max_time_seconds': 180,   # 3分钟
    'auto_save_interval': 30,  # 30秒更频繁检查
    'checkpoint_interval': 3,
}

# 环境变量配置映射
ENV_CONFIG_MAP = {
    'small': SMALL_SCALE_CONFIG,
    'medium': MEDIUM_SCALE_CONFIG,
    'large': LARGE_SCALE_CONFIG,
    'ultra': ULTRA_PARALLEL_CONFIG,
}

def get_smart_collector_config(scale: str = None, num_tests: int = None) -> dict:
    """
    获取智能收集器配置
    
    Args:
        scale: 规模类型 ('small', 'medium', 'large', 'ultra')
        num_tests: 预期测试数量
    
    Returns:
        配置字典
    """
    # 从环境变量获取
    if scale is None:
        scale = os.environ.get('COLLECTOR_SCALE', '').lower()
    
    # 根据测试数量自动判断规模
    if scale == '' and num_tests:
        if num_tests <= 10:
            scale = 'small'
        elif num_tests <= 50:
            scale = 'medium'
        elif num_tests <= 200:
            scale = 'large'
        else:
            scale = 'ultra'
    
    # 获取配置
    config = ENV_CONFIG_MAP.get(scale, MEDIUM_SCALE_CONFIG)
    
    # 如果有具体的测试数量，进一步优化
    if num_tests:
        config = config.copy()
        config['max_memory_results'] = min(config['max_memory_results'], max(1, num_tests // 5))
        config['checkpoint_interval'] = min(config['checkpoint_interval'], max(1, num_tests // 3))
    
    return config

def get_current_config() -> dict:
    """获取当前环境的推荐配置"""
    # 检查环境变量
    scale = os.environ.get('COLLECTOR_SCALE', '').lower()
    num_tests = os.environ.get('NUM_TESTS')
    
    if num_tests:
        try:
            num_tests = int(num_tests)
        except:
            num_tests = None
    
    return get_smart_collector_config(scale, num_tests)

# 导出配置检查功能
def validate_config(config: dict) -> list:
    """验证配置的合理性"""
    issues = []
    
    if config.get('max_memory_results', 0) <= 0:
        issues.append("max_memory_results 必须大于0")
    
    if config.get('checkpoint_interval', 0) > config.get('max_memory_results', 0) * 2:
        issues.append("checkpoint_interval 过大，可能导致数据不保存")
    
    if config.get('max_time_seconds', 0) <= 0:
        issues.append("max_time_seconds 必须大于0")
    
    return issues

if __name__ == "__main__":
    # 显示当前推荐配置
    config = get_current_config()
    print("当前推荐配置:")
    for key, value in config.items():
        print(f"  {key}: {value}")
    
    # 验证配置
    issues = validate_config(config)
    if issues:
        print("\n配置问题:")
        for issue in issues:
            print(f"  ⚠️ {issue}")
    else:
        print("\n✅ 配置验证通过")
