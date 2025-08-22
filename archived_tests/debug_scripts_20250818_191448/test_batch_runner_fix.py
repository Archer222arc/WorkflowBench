#!/usr/bin/env python3
"""测试batch_test_runner的修复"""

import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from batch_test_runner import BatchTestRunner, TestTask

def test_single_task():
    """测试单个任务执行"""
    print("=" * 60)
    print("测试1: 单个任务执行")
    print("=" * 60)
    
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
    
    runner = BatchTestRunner(debug=False, silent=True)
    
    # 检查方法是否存在
    if not hasattr(runner, '_run_single_test_safe'):
        print("❌ _run_single_test_safe 方法不存在")
        return False
    
    print("✅ _run_single_test_safe 方法存在")
    
    # 测试在主线程中调用
    print("\n在主线程中测试...")
    try:
        result = runner._run_single_test_safe(task)
        if result:
            print(f"✅ 主线程测试成功: success={result.get('success', False)}")
        else:
            print("❌ 主线程测试返回None")
    except Exception as e:
        print(f"❌ 主线程测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_thread_pool():
    """测试线程池执行"""
    print("\n" + "=" * 60)
    print("测试2: 线程池执行")
    print("=" * 60)
    
    tasks = []
    for i in range(3):
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
        tasks.append(task)
    
    runner = BatchTestRunner(debug=False, silent=True)
    
    print(f"创建了 {len(tasks)} 个测试任务")
    
    # 使用线程池执行
    results = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        print("提交任务到线程池...")
        
        future_to_task = {}
        for task in tasks:
            # 这里是关键：检查是否能正确调用
            try:
                future = executor.submit(runner._run_single_test_safe, task)
                future_to_task[future] = task
            except AttributeError as e:
                print(f"❌ AttributeError提交任务时: {e}")
                return False
            except Exception as e:
                print(f"❌ 其他错误提交任务时: {e}")
                return False
        
        print(f"✅ 成功提交 {len(future_to_task)} 个任务")
        
        # 收集结果
        completed = 0
        failed = 0
        for future in as_completed(future_to_task):
            task = future_to_task[future]
            try:
                result = future.result(timeout=10)
                if result:
                    completed += 1
                    print(f"  任务完成: success={result.get('success', False)}")
                else:
                    failed += 1
                    print(f"  任务返回None")
            except AttributeError as e:
                print(f"❌ AttributeError获取结果时: {e}")
                failed += 1
            except Exception as e:
                print(f"❌ 其他错误获取结果时: {e}")
                failed += 1
    
    print(f"\n线程池测试结果: 完成={completed}, 失败={failed}")
    return failed == 0

def test_in_thread():
    """测试在子线程中执行"""
    print("\n" + "=" * 60)
    print("测试3: 子线程执行")
    print("=" * 60)
    
    result_holder = [None]
    error_holder = [None]
    
    def thread_func():
        try:
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
            
            runner = BatchTestRunner(debug=False, silent=True)
            
            # 在子线程中调用
            print(f"当前线程: {threading.current_thread().name}")
            print(f"是主线程: {threading.current_thread() == threading.main_thread()}")
            
            result = runner._run_single_test_safe(task)
            result_holder[0] = result
        except Exception as e:
            error_holder[0] = e
            import traceback
            traceback.print_exc()
    
    # 创建并启动线程
    thread = threading.Thread(target=thread_func, name="TestThread")
    thread.start()
    thread.join(timeout=10)
    
    if thread.is_alive():
        print("❌ 线程超时")
        return False
    
    if error_holder[0]:
        print(f"❌ 子线程执行失败: {error_holder[0]}")
        return False
    
    if result_holder[0]:
        print(f"✅ 子线程执行成功: success={result_holder[0].get('success', False)}")
        return True
    else:
        print("❌ 子线程返回None")
        return False

def main():
    """运行所有测试"""
    print("🔍 开始测试batch_test_runner修复")
    print("=" * 60)
    
    # 清理缓存
    import os
    os.system("rm -rf __pycache__/*.pyc 2>/dev/null")
    
    tests = [
        ("单任务测试", test_single_task),
        ("线程池测试", test_thread_pool),
        ("子线程测试", test_in_thread)
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n❌ {name} 异常: {e}")
            results[name] = False
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 所有测试通过！batch_test_runner已正确修复")
    else:
        print("\n⚠️ 部分测试失败，需要进一步调试")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)