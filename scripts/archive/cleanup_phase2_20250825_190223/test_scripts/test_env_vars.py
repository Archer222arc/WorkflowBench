#!/usr/bin/env python3
"""
测试环境变量传递和ResultCollector启用情况
"""
import os
import sys

def test_environment_vars():
    """测试环境变量"""
    print("🔍 环境变量检测:")
    print(f"  USE_RESULT_COLLECTOR: {os.environ.get('USE_RESULT_COLLECTOR', 'NOT SET')}")
    print(f"  STORAGE_FORMAT: {os.environ.get('STORAGE_FORMAT', 'NOT SET')}")
    
    # 测试ResultCollector导入
    try:
        from result_collector import ResultCollector, ResultAggregator
        print("✅ ResultCollector模块导入成功")
        
        # 测试环境变量检测
        use_collector = os.environ.get('USE_RESULT_COLLECTOR', 'false').lower() == 'true'
        print(f"✅ 环境变量检测结果: {use_collector}")
        
        if use_collector:
            collector = ResultCollector()
            print(f"✅ ResultCollector初始化成功，目录: {collector.temp_dir}")
        else:
            print("ℹ️  ResultCollector未启用（环境变量为false或未设置）")
            
    except ImportError as e:
        print(f"❌ ResultCollector导入失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    test_environment_vars()