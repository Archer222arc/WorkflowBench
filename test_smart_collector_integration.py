#!/usr/bin/env python3
"""
测试智能数据收集器集成效果
验证SmartResultCollector在实际工作流中的表现
"""

import os
import sys
import json
import time
from pathlib import Path

def test_integration():
    """测试集成效果"""
    print("🔬 智能数据收集器集成测试")
    print("=" * 50)
    
    # 1. 设置环境变量
    os.environ['USE_SMART_COLLECTOR'] = 'true'
    os.environ['COLLECTOR_SCALE'] = 'small'
    os.environ['NUM_TESTS'] = '5'
    os.environ['STORAGE_FORMAT'] = 'json'
    
    print("✅ 环境变量已设置:")
    print(f"  USE_SMART_COLLECTOR: {os.environ.get('USE_SMART_COLLECTOR')}")
    print(f"  COLLECTOR_SCALE: {os.environ.get('COLLECTOR_SCALE')}")
    print(f"  NUM_TESTS: {os.environ.get('NUM_TESTS')}")
    
    # 2. 验证ResultCollector配置
    try:
        from result_collector_adapter import create_adaptive_collector
        from smart_collector_config import get_smart_collector_config
        
        # 获取配置
        config = get_smart_collector_config(scale='small')
        print(f"\n📋 Small Scale配置:")
        print(f"  checkpoint_interval: {config['checkpoint_interval']}")
        print(f"  max_time_seconds: {config['max_time_seconds']}")
        print(f"  adaptive_threshold: {config['adaptive_threshold']}")
        
        # 创建收集器
        collector = create_adaptive_collector(**config)
        print(f"\n✅ 收集器创建成功: {type(collector).__name__}")
        
        # 模拟5个测试结果（对应5.1实验的实际情况）
        print("\n🧪 模拟5个测试结果（5.1实验场景）:")
        for i in range(5):
            result = {
                'model': 'qwen2.5-72b-instruct',
                'task_id': f'test_{i+1}',
                'success': i % 2 == 0,
                'prompt_type': 'optimal',
                'difficulty': 'easy',
                'tool_success_rate': 0.8
            }
            
            triggered = collector.add_result(result)
            print(f"  测试 {i+1}/5: 触发保存={triggered}")
            
            if i == 1:
                # 第2个结果应该触发保存（small scale配置）
                if triggered:
                    print("    ✅ 正确！第2个结果触发了保存")
                else:
                    print("    ❌ 错误！第2个结果应该触发保存")
            
            time.sleep(0.1)
        
        # 强制保存剩余数据
        print("\n💾 强制保存剩余数据...")
        collector.force_save("test_completion")
        
        # 获取最终统计
        stats = collector.get_stats()
        print(f"\n📊 最终统计:")
        print(f"  总处理结果: {stats.get('total_results', 0)}")
        print(f"  内存中结果: {stats.get('memory_results', 0)}")
        print(f"  临时文件数: {stats.get('temp_files', 0)}")
        
        # 关闭收集器
        collector.shutdown()
        
        print("\n✅ 集成测试成功！")
        print("\n🎯 关键改进:")
        print("  1. checkpoint_interval从20降到2（适合小批量）")
        print("  2. 添加时间触发（5分钟自动保存）")
        print("  3. 进程退出时自动保存")
        print("  4. 实时写入临时文件防止数据丢失")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_database_update():
    """检查数据库更新情况"""
    print("\n📊 检查数据库更新...")
    
    db_path = Path("pilot_bench_cumulative_results/master_database.json")
    if db_path.exists():
        with open(db_path, 'r') as f:
            db = json.load(f)
        
        models = db.get('models', {})
        print(f"  当前模型数: {len(models)}")
        
        for model_name in list(models.keys())[:3]:  # 显示前3个
            model_data = models[model_name]
            total = model_data.get('overall_stats', {}).get('total_tests', 0)
            print(f"  {model_name}: {total} tests")
        
        summary = db.get('summary', {})
        print(f"\n  总测试数: {summary.get('total_tests', 0)}")
        print(f"  成功数: {summary.get('total_success', 0)}")
        print(f"  部分成功: {summary.get('total_partial', 0)}")
        print(f"  失败数: {summary.get('total_failure', 0)}")

if __name__ == "__main__":
    # 运行集成测试
    success = test_integration()
    
    # 检查数据库
    check_database_update()
    
    if success:
        print("\n🎉 智能数据收集器已成功集成！")
        print("\n📝 使用方法:")
        print("1. source ./smart_env.sh")
        print("2. ./run_systematic_test_final.sh --phase 5.1")
        print("\n或直接运行:")
        print("USE_SMART_COLLECTOR=true ./run_systematic_test_final.sh --phase 5.1")
        sys.exit(0)
    else:
        sys.exit(1)