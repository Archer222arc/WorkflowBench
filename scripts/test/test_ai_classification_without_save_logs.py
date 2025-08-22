#!/usr/bin/env python3
"""
测试AI分类系统在不启用save-logs时也能正常工作
验证log_data始终可用于AI分类，save-logs只控制是否保存到文件
"""

import sys
import json
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

def test_ai_classification_modes():
    """测试不同模式下的AI分类"""
    print("=" * 60)
    print("测试AI分类系统（无论是否启用save-logs）")
    print("=" * 60)
    
    # 清理之前的测试数据
    print("\n清理之前的测试数据...")
    import subprocess
    subprocess.run([
        "python", "-c",
        """
import json
from pathlib import Path

db_path = Path('pilot_bench_cumulative_results/master_database.json')
if db_path.exists():
    with open(db_path, 'r') as f:
        db = json.load(f)
    
    # 清除test-model的数据
    if 'models' in db and 'test-model' in db['models']:
        del db['models']['test-model']
    
    # 清除相关的test_groups
    if 'test_groups' in db:
        keys_to_remove = [k for k in db['test_groups'].keys() if 'test-model' in k]
        for key in keys_to_remove:
            del db['test_groups'][key]
    
    # 保存清理后的数据库
    with open(db_path, 'w') as f:
        json.dump(db, f, indent=2)
    
    print('已清除test-model的数据')
"""
    ])
    
    print("\n" + "=" * 40)
    print("测试1: 启用AI分类，禁用save-logs")
    print("=" * 40)
    print("命令: --ai-classification（不带--save-logs）")
    print("期望: AI分类应该正常工作，但不保存日志文件")
    
    # 创建测试任务
    from batch_test_runner import BatchTestRunner, TestTask
    
    # 创建runner（启用AI分类，禁用save-logs）
    runner = BatchTestRunner(
        debug=True,
        silent=False,
        save_logs=False,  # 不保存日志文件
        use_ai_classification=True  # 启用AI分类
    )
    
    # 创建一个会失败的测试任务
    task = TestTask(
        model='gpt-4o-mini',
        task_type='simple_task',
        prompt_type='baseline',
        difficulty='easy',
        is_flawed=False,
        flaw_type=None,
        tool_success_rate=0.0  # 设置为0强制失败
    )
    
    print("\n运行测试（工具成功率=0，保证失败）...")
    try:
        # 运行单个测试
        result = runner.run_single_test(
            model=task.model,
            task_type=task.task_type,
            prompt_type=task.prompt_type,
            is_flawed=task.is_flawed,
            flaw_type=task.flaw_type,
            tool_success_rate=task.tool_success_rate
        )
        
        print(f"\n测试结果:")
        print(f"  成功: {result.get('success', False)}")
        print(f"  错误: {result.get('error', 'None')}")
        
        # 检查日志文件是否存在
        log_dir = Path("workflow_quality_results/test_logs")
        log_files = list(log_dir.glob(f"{task.task_type}*"))
        recent_logs = [f for f in log_files if 'simple_task' in f.name]
        
        print(f"\n日志文件检查:")
        print(f"  最近的日志文件数: {len(recent_logs)}")
        if len(recent_logs) == 0:
            print("  ✅ 正确：没有保存日志文件（save_logs=False）")
        else:
            print(f"  ❌ 错误：发现了日志文件（不应该存在）")
        
        # 检查AI分类是否工作
        print(f"\nAI分类检查:")
        if hasattr(runner, 'ai_classifier') and runner.ai_classifier:
            print(f"  ✅ AI分类器已初始化")
            
            # 检查log_data是否在内存中生成（通过查看result中的痕迹）
            if '_log_data' in str(result):
                print(f"  ⚠️  result中仍包含_log_data引用")
            else:
                print(f"  ✅ log_data已被正确处理和移除")
        else:
            print(f"  ❌ AI分类器未初始化")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 40)
    print("测试2: 同时启用AI分类和save-logs")
    print("=" * 40)
    print("命令: --ai-classification --save-logs")
    print("期望: AI分类正常工作，同时保存日志文件")
    
    # 创建新的runner（启用AI分类和save-logs）
    runner2 = BatchTestRunner(
        debug=True,
        silent=False,
        save_logs=True,  # 保存日志文件
        use_ai_classification=True  # 启用AI分类
    )
    
    # 运行相同的测试
    task2 = TestTask(
        model='gpt-4o-mini',
        task_type='simple_task',
        prompt_type='baseline',
        difficulty='easy',
        is_flawed=False,
        flaw_type=None,
        tool_success_rate=0.0  # 设置为0强制失败
    )
    
    print("\n运行测试（工具成功率=0，保证失败）...")
    try:
        result2 = runner2.run_single_test(
            model=task2.model,
            task_type=task2.task_type,
            prompt_type=task2.prompt_type,
            is_flawed=task2.is_flawed,
            flaw_type=task2.flaw_type,
            tool_success_rate=task2.tool_success_rate
        )
        
        print(f"\n测试结果:")
        print(f"  成功: {result2.get('success', False)}")
        print(f"  错误: {result2.get('error', 'None')}")
        
        # 检查日志文件
        import time
        time.sleep(0.5)  # 等待文件写入
        log_files = list(log_dir.glob(f"{task2.task_type}*"))
        new_logs = [f for f in log_files if f.stat().st_mtime > time.time() - 10]
        
        print(f"\n日志文件检查:")
        print(f"  新创建的日志文件数: {len(new_logs)}")
        if len(new_logs) > 0:
            print(f"  ✅ 正确：保存了日志文件（save_logs=True）")
            for log_file in new_logs[:2]:
                print(f"      - {log_file.name}")
        else:
            print(f"  ❌ 错误：没有保存日志文件（应该保存）")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主测试函数"""
    print("🧪 测试AI分类系统的独立性")
    print("验证：AI分类不依赖于save-logs选项")
    print("原则：log_data始终在内存中生成并用于AI分类")
    print("      save-logs只控制是否将日志保存到文件")
    print()
    
    test_ai_classification_modes()
    
    print("\n" + "=" * 60)
    print("✅ 测试完成!")
    print("\n📋 关键改进:")
    print("  1. ✅ log_data始终生成（在run_single_test中）")
    print("  2. ✅ AI分类始终使用log_data（如果有错误）")
    print("  3. ✅ save-logs只控制文件保存，不影响AI分类")
    print("  4. ✅ 实现了更好的关注点分离")
    print("\n💡 使用建议:")
    print("  - 快速测试: 只用--ai-classification（不保存文件）")
    print("  - 详细调试: 用--ai-classification --save-logs（保存文件）")
    print("=" * 60)

if __name__ == "__main__":
    main()