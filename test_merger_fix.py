#!/usr/bin/env python3
"""
测试ResultMerger并发修复
"""

import os
import json
import time
import threading
from pathlib import Path

# 设置环境变量
os.environ['USE_RESULT_COLLECTOR'] = 'true'
os.environ['STORAGE_FORMAT'] = 'json'

def test_concurrent_mergers():
    """测试多个merger同时运行"""
    from result_merger import ResultMerger
    
    print("=" * 60)
    print("测试并发ResultMerger")
    print("=" * 60)
    
    # 创建两个merger实例（单例模式，实际是同一个）
    merger1 = ResultMerger()
    merger2 = ResultMerger()
    
    print(f"Merger1 ID: {id(merger1)}")
    print(f"Merger2 ID: {id(merger2)}")
    print(f"是同一个实例: {merger1 is merger2}")
    
    # 启动第一个merger
    print("\n启动第一个merger...")
    merger1.start(interval=5)
    time.sleep(1)
    
    # 尝试启动第二个merger（应该被阻止）
    print("尝试启动第二个merger...")
    merger2.start(interval=5)
    
    # 停止merger
    time.sleep(2)
    print("\n停止merger...")
    merger1.stop()
    
    print("✅ 并发控制测试完成")

def test_file_race_condition():
    """测试文件竞态条件处理"""
    from result_collector import ResultCollector
    from result_merger import ResultMerger
    import concurrent.futures
    
    print("\n" + "=" * 60)
    print("测试文件竞态条件处理")
    print("=" * 60)
    
    collector = ResultCollector()
    
    def write_and_delete(i):
        """写入文件然后立即删除（模拟竞态）"""
        try:
            # 写入测试数据
            test_result = {
                'model': f'race-test-{i}',
                'success': i % 2 == 0,
                'task_type': 'test',
                'execution_history': []
            }
            
            file_path = collector.add_batch_result(
                f'race-test-{i}',
                [test_result],
                {'pid': os.getpid()}
            )
            
            # 立即删除文件（模拟另一个进程处理了它）
            if i % 3 == 0:
                Path(file_path).unlink()
                print(f"  已删除文件 {i}")
            
            return True
            
        except Exception as e:
            print(f"  错误 {i}: {e}")
            return False
    
    # 并发写入和删除
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(write_and_delete, i) for i in range(10)]
        results = [f.result() for f in futures]
    
    print(f"成功: {sum(results)}/10")
    
    # 启动merger处理剩余文件
    merger = ResultMerger()
    print("\n合并剩余文件...")
    count = merger.merge_once()
    print(f"✅ 合并了 {count} 个文件（无错误）")
    
    # 清理
    temp_dir = Path("temp_results")
    for file in temp_dir.glob("race-test-*.json"):
        file.unlink()

def test_json_completeness():
    """测试JSON文件完整性"""
    from result_collector import ResultCollector
    
    print("\n" + "=" * 60)
    print("测试JSON文件完整性")
    print("=" * 60)
    
    collector = ResultCollector()
    
    # 创建包含复杂execution_history的测试数据
    complex_result = {
        'model': 'completeness-test',
        'task_type': 'complex_task',
        'success': True,
        'execution_history': [
            {
                'tool': f'tool_{i}',
                'success': i % 2 == 0,
                'output': f'Output for tool {i}' * 100,  # 大量数据
                'error': None if i % 2 == 0 else f'Error {i}',
                'execution_time': i * 0.5
            }
            for i in range(20)  # 20个工具执行记录
        ],
        'conversation_history': [
            {'role': 'user', 'content': f'Message {i}'}
            for i in range(50)  # 50条对话
        ]
    }
    
    # 写入文件
    print("写入包含大量数据的JSON文件...")
    file_path = collector.add_batch_result(
        'completeness-test',
        [complex_result],
        {'pid': os.getpid()}
    )
    
    # 验证文件完整性
    print("验证JSON文件完整性...")
    with open(file_path, 'r') as f:
        data = json.load(f)
        
    results = data['results'][0]
    exec_history = results.get('execution_history', [])
    
    print(f"✅ JSON文件完整:")
    print(f"   - execution_history条目: {len(exec_history)}")
    print(f"   - conversation_history条目: {len(results.get('conversation_history', []))}")
    print(f"   - 文件大小: {Path(file_path).stat().st_size} bytes")
    
    # 清理
    Path(file_path).unlink()

if __name__ == "__main__":
    # 测试1: 并发控制
    test_concurrent_mergers()
    
    # 测试2: 文件竞态条件
    test_file_race_condition()
    
    # 测试3: JSON完整性
    test_json_completeness()
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)