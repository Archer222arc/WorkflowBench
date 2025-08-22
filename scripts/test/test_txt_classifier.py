#\!/usr/bin/env python3
"""测试TXT-based AI分类器的完整流程"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from batch_test_runner import BatchTestRunner, TestTask

print("=" * 60)
print("测试TXT-based AI分类器")
print("=" * 60)

# 创建runner（启用AI分类，禁用save_logs）
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
    print(f"  错误: {result.get('error', 'None')[:100]}")
    
    # 检查临时日志文件是否已被删除
    log_dir = Path("workflow_quality_results/test_logs")
    if log_dir.exists():
        recent_logs = list(log_dir.glob("simple_task*"))
        print(f"\n日志文件检查:")
        print(f"  找到的日志文件数: {len(recent_logs)}")
        if len(recent_logs) == 0:
            print("  ✅ 正确：临时日志文件已被删除（save_logs=False）")
        else:
            print(f"  ⚠️  发现了日志文件（可能是之前的测试留下的）")
            # 显示最近的文件
            import time
            current_time = time.time()
            for log_file in recent_logs[-3:]:
                age = current_time - log_file.stat().st_mtime
                if age < 10:  # 10秒内的文件
                    print(f"      - {log_file.name} (刚创建)")
                    
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("✅ 测试完成\!")
print("\n关键改进:")
print("  1. AI分类器现在读取人类可读的TXT文件")
print("  2. 临时TXT文件在AI分类后自动删除")
print("  3. save-logs只控制是否永久保存文件")
print("=" * 60)
