#!/usr/bin/env python3
"""
测试日志文件命名是否包含模型名
"""

from batch_test_runner import BatchTestRunner, TestTask
from pathlib import Path

def test_log_naming():
    """测试日志文件命名"""
    print("=" * 60)
    print("测试日志文件命名（模型名应该在文件名中）")
    print("=" * 60)
    
    # 创建测试runner，启用日志保存
    runner = BatchTestRunner(debug=True, silent=False, save_logs=True)
    print("✅ 创建BatchTestRunner (save_logs=True)")
    
    # 测试不同的模型
    test_models = [
        'gpt-4o-mini',
        'DeepSeek-V3-0324',
        'qwen2.5-72b-instruct'
    ]
    
    log_files = []
    
    for model in test_models:
        print(f"\n测试模型: {model}")
        
        # 创建测试任务
        task = TestTask(
            model=model,
            task_type='simple_task',
            prompt_type='baseline',
            difficulty='easy',
            tool_success_rate=0.8
        )
        
        # 运行测试
        result = runner.run_single_test(
            model=task.model,
            task_type=task.task_type,
            prompt_type=task.prompt_type,
            is_flawed=False,
            flaw_type=None,
            tool_success_rate=task.tool_success_rate
        )
        
        # 检查日志文件
        log_dir = Path("workflow_quality_results/test_logs")
        model_safe = model.replace('-', '_').replace('.', '_')
        
        # 查找包含模型名的日志文件
        matching_files = list(log_dir.glob(f"{model_safe}_*.txt"))
        
        if matching_files:
            latest_file = max(matching_files, key=lambda f: f.stat().st_mtime)
            print(f"  ✅ 找到日志文件: {latest_file.name}")
            log_files.append(latest_file.name)
            
            # 验证文件名格式
            if latest_file.name.startswith(model_safe):
                print(f"  ✅ 模型名在文件名开头")
            else:
                print(f"  ⚠️ 模型名不在文件名开头")
        else:
            print(f"  ❌ 未找到包含模型名 {model_safe} 的日志文件")
    
    # 显示所有创建的日志文件
    print("\n" + "=" * 60)
    print("创建的日志文件:")
    print("=" * 60)
    for filename in log_files:
        print(f"  - {filename}")
    
    # 测试flawed情况
    print("\n" + "=" * 60)
    print("测试flawed情况的命名:")
    print("=" * 60)
    
    task = TestTask(
        model='gpt-4o-mini',
        task_type='simple_task',
        prompt_type='baseline',
        difficulty='easy',
        tool_success_rate=0.8,
        is_flawed=True,
        flaw_type='sequence_disorder'
    )
    
    result = runner.run_single_test(
        model=task.model,
        task_type=task.task_type,
        prompt_type=task.prompt_type,
        is_flawed=task.is_flawed,
        flaw_type=task.flaw_type,
        tool_success_rate=task.tool_success_rate
    )
    
    # 查找flawed日志文件
    model_safe = task.model.replace('-', '_').replace('.', '_')
    flawed_files = list(log_dir.glob(f"{model_safe}_*flawed*.txt"))
    
    if flawed_files:
        latest_file = max(flawed_files, key=lambda f: f.stat().st_mtime)
        print(f"  ✅ 找到flawed日志文件: {latest_file.name}")
        
        # 验证格式
        expected_parts = [model_safe, task.task_type, 'flawed', task.flaw_type, task.prompt_type]
        missing_parts = []
        for part in expected_parts:
            if part not in latest_file.name:
                missing_parts.append(part)
        
        if not missing_parts:
            print(f"  ✅ 文件名包含所有必要部分")
        else:
            print(f"  ⚠️ 文件名缺少: {missing_parts}")
    
    print("\n" + "=" * 60)
    print("✅ 测试完成!")
    print("=" * 60)

if __name__ == "__main__":
    test_log_naming()