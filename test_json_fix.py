#!/usr/bin/env python3
"""
测试JSON序列化修复
"""

import os
import json
import sys
from pathlib import Path

# 设置环境变量使用ResultCollector模式
os.environ['USE_RESULT_COLLECTOR'] = 'true'
os.environ['STORAGE_FORMAT'] = 'json'

def test_result_collector():
    """测试ResultCollector的JSON写入"""
    from result_collector import ResultCollector
    
    collector = ResultCollector()
    
    # 创建一个包含复杂数据的测试结果
    test_result = {
        'model': 'test-model',
        'task_type': 'basic_task',
        'success': True,
        'execution_history': [
            {
                'tool': 'test_tool_1',
                'success': True,
                'output': 'Test output 1',
                'error': None,
                'execution_time': 1.23
            },
            {
                'tool': 'test_tool_2',
                'success': False,
                'output': None,
                'error': 'Test error',
                'execution_time': 0.45
            }
        ],
        'conversation_history': [
            {'role': 'user', 'content': 'Test message'},
            {'role': 'assistant', 'content': 'Test response'}
        ]
    }
    
    # 添加结果到collector
    print("📝 测试写入ResultCollector...")
    try:
        result_file = collector.add_batch_result(
            'test-model',
            [test_result],
            {'pid': os.getpid()}
        )
        print(f"✅ 成功写入文件: {result_file}")
        
        # 验证文件可以被正确读取
        with open(result_file, 'r') as f:
            data = json.load(f)
            print(f"✅ 文件可以正确解析")
            print(f"   - 模型: {data['model']}")
            print(f"   - 结果数: {data['result_count']}")
            
            # 检查execution_history是否完整
            if data['results'][0].get('execution_history'):
                print(f"   - execution_history条目: {len(data['results'][0]['execution_history'])}")
            
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_merger():
    """测试ResultMerger处理文件"""
    from result_merger import ResultMerger
    from result_collector import ResultCollector
    
    merger = ResultMerger()
    
    print("\n📝 测试ResultMerger合并...")
    try:
        # 先创建几个测试文件
        collector = ResultCollector()
        for i in range(3):
            test_result = {
                'model': f'test-model-{i}',
                'success': i % 2 == 0,
                'execution_history': [
                    {'tool': f'tool_{j}', 'success': True}
                    for j in range(2)
                ]
            }
            collector.add_batch_result(
                f'test-model-{i}',
                [test_result],
                {'pid': os.getpid()}
            )
        
        # 执行合并
        count = merger.merge_once()
        print(f"✅ 成功合并 {count} 个文件")
        
        # 检查数据库
        db_path = Path('pilot_bench_cumulative_results/master_database.json')
        if db_path.exists():
            with open(db_path, 'r') as f:
                db = json.load(f)
                print(f"✅ 数据库包含 {len(db.get('models', {}))} 个模型")
        
        return True
        
    except Exception as e:
        print(f"❌ 合并测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("测试JSON序列化修复")
    print("=" * 60)
    
    # 测试1: ResultCollector
    success1 = test_result_collector()
    
    # 测试2: ResultMerger
    success2 = test_merger()
    
    print("\n" + "=" * 60)
    if success1 and success2:
        print("✅ 所有测试通过！JSON序列化问题已修复")
    else:
        print("❌ 部分测试失败，请检查日志")
    print("=" * 60)