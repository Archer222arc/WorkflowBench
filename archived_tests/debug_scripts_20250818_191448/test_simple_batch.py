#!/usr/bin/env python3
"""简单测试batch_test_runner的AttributeError问题"""

import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from batch_test_runner import BatchTestRunner, TestTask

def mock_test_function(task):
    """模拟测试函数，不实际执行测试"""
    return {
        'success': True,
        'error': None,
        'execution_time': 1.0,
        'success_level': 'success',
        'tool_calls': [],
        'turns': 1,
        'workflow_score': 1.0,
        'phase2_score': 1.0,
        'quality_score': 1.0,
        'final_score': 1.0,
        'task_type': task.task_type,
        'prompt_type': task.prompt_type,
        'difficulty': task.difficulty,
        'is_flawed': task.is_flawed,
        'flaw_type': task.flaw_type,
        'tool_success_rate': task.tool_success_rate
    }

def test_attribute_error():
    """测试AttributeError问题"""
    
    # 创建测试任务
    task = TestTask(
        model='gpt-4o-mini',
        task_type='simple_task',
        prompt_type='flawed_sequence_disorder',
        difficulty='easy',
        is_flawed=True,
        flaw_type='sequence_disorder',
        tool_success_rate=0.8,
        timeout=60
    )
    
    # 创建BatchTestRunner实例
    runner = BatchTestRunner(debug=False, silent=True)
    
    # 替换实际的测试方法为mock
    original_run_single_test = runner.run_single_test
    runner.run_single_test = lambda **kwargs: mock_test_function(task)
    
    print("测试1: 检查_run_single_test_safe方法是否存在")
    if hasattr(runner, '_run_single_test_safe'):
        print("✅ _run_single_test_safe 存在")
    else:
        print("❌ _run_single_test_safe 不存在")
        return False
    
    print("\n测试2: 在主线程中调用")
    try:
        result = runner._run_single_test_safe(task)
        print(f"✅ 主线程调用成功: {result.get('success')}")
    except AttributeError as e:
        print(f"❌ AttributeError: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False
    
    print("\n测试3: 在线程池中调用")
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(runner._run_single_test_safe, task)
            result = future.result(timeout=5)
            print(f"✅ 线程池调用成功: {result.get('success')}")
    except AttributeError as e:
        print(f"❌ AttributeError在线程池中: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误在线程池中: {e}")
        return False
    
    print("\n测试4: 检查是否在子线程中")
    def thread_test():
        is_main = threading.current_thread() == threading.main_thread()
        print(f"  当前线程: {threading.current_thread().name}")
        print(f"  是主线程: {is_main}")
        
        # 调用方法
        try:
            result = runner._run_single_test_safe(task)
            print(f"  ✅ 子线程调用成功: {result.get('success')}")
            return True
        except Exception as e:
            print(f"  ❌ 子线程调用失败: {e}")
            return False
    
    thread = threading.Thread(target=thread_test, name="TestThread")
    thread.start()
    thread.join(timeout=5)
    
    # 恢复原始方法
    runner.run_single_test = original_run_single_test
    
    print("\n✅ 所有测试通过！没有AttributeError")
    return True

if __name__ == "__main__":
    # 清理缓存
    import os
    os.system("rm -rf __pycache__/batch_test_runner.cpython*.pyc 2>/dev/null")
    
    print("=" * 60)
    print("测试batch_test_runner的AttributeError问题")
    print("=" * 60)
    
    success = test_attribute_error()
    
    if not success:
        print("\n⚠️ 发现问题需要修复")
        sys.exit(1)
    else:
        print("\n🎉 测试成功，没有AttributeError问题")
        sys.exit(0)