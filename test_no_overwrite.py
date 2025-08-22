#!/usr/bin/env python3
"""
测试debug日志不会被覆盖
模拟run_systematic_test_final.sh的行为
"""

import subprocess
import time
from pathlib import Path
from datetime import datetime
import os

def run_model_test(model: str, debug_dir: str):
    """运行单个模型测试，使用指定的debug目录"""
    
    print(f"\n启动 {model} 测试...")
    print(f"  使用debug目录: {debug_dir}")
    
    cmd = [
        'python', 'ultra_parallel_runner_debug.py',
        '--model', model,
        '--num-instances', '1',
        '--max-workers', '2',
        '--tool-success-rate', '0.8',
        '--prompt-types', 'baseline',
        '--difficulty', 'easy',
        '--task-types', 'simple_task',
        '--debug-log-dir', debug_dir
    ]
    
    # 运行短时间
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(3)
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    
    print(f"  {model} 测试已终止")

def main():
    print("=" * 60)
    print("测试Debug日志不被覆盖")
    print("=" * 60)
    
    # 创建一个共享的debug目录（模拟bash脚本的行为）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    shared_debug_dir = f"logs/debug_ultra_test_no_overwrite_{timestamp}"
    
    print(f"\n📁 创建共享debug目录: {shared_debug_dir}")
    Path(shared_debug_dir).mkdir(parents=True, exist_ok=True)
    
    # 测试的模型列表
    models = [
        'DeepSeek-V3-0324',
        'DeepSeek-R1-0528', 
        'qwen2.5-72b-instruct',
        'DeepSeek-V3-0324',  # 故意重复，测试同一模型的多次运行
    ]
    
    # 依次运行每个模型（模拟bash脚本的行为）
    for i, model in enumerate(models):
        print(f"\n--- 第 {i+1} 次测试 ---")
        run_model_test(model, shared_debug_dir)
        
        # 检查当前目录中的文件
        debug_dir = Path(shared_debug_dir)
        log_files = sorted(debug_dir.glob('*.log'))
        print(f"\n  当前日志文件数: {len(log_files)}")
        for f in log_files[-3:]:  # 只显示最新的3个
            print(f"    - {f.name}")
        
        time.sleep(1)  # 稍微等待
    
    # 最终检查
    print("\n" + "=" * 60)
    print("最终检查结果")
    print("=" * 60)
    
    debug_dir = Path(shared_debug_dir)
    log_files = sorted(debug_dir.glob('*.log'))
    
    print(f"\n总共创建了 {len(log_files)} 个日志文件:")
    
    # 分析每个模型的日志
    model_counts = {}
    for log_file in log_files:
        print(f"  📄 {log_file.name}")
        
        # 提取模型信息
        for model in set(models):
            model_key = model.lower().replace('-', '_').replace('.', '_')
            if model_key in log_file.name.lower():
                model_counts[model] = model_counts.get(model, 0) + 1
                break
    
    # 统计
    print("\n📊 统计结果:")
    for model in set(models):
        count = model_counts.get(model, 0)
        expected = models.count(model)
        if count >= expected:
            print(f"  ✅ {model}: {count} 个日志文件 (期望至少 {expected})")
        else:
            print(f"  ❌ {model}: {count} 个日志文件 (期望至少 {expected})")
    
    # 验证是否有覆盖
    if len(log_files) >= len(models):
        print("\n✅ 测试成功！没有日志被覆盖")
        print(f"   - 运行了 {len(models)} 个测试")
        print(f"   - 创建了 {len(log_files)} 个日志文件")
        print(f"   - 所有日志都保存在: {shared_debug_dir}")
    else:
        print(f"\n❌ 测试失败！可能有日志被覆盖")
        print(f"   - 运行了 {len(models)} 个测试")
        print(f"   - 只有 {len(log_files)} 个日志文件")
    
    # 检查文件名中的计数器
    print("\n检查文件名计数器:")
    counters = []
    for log_file in log_files:
        # 提取计数器（格式：_XXX_）
        parts = log_file.stem.split('_')
        for i, part in enumerate(parts):
            if part.isdigit() and len(part) == 3:
                counters.append(int(part))
                print(f"  文件 {log_file.name}")
                print(f"    计数器: {part}")
                break
    
    # 验证计数器是否递增
    if counters == sorted(counters):
        print("\n✅ 计数器正确递增，没有重复")
    else:
        print("\n❌ 计数器有问题，可能有覆盖")
        print(f"   计数器序列: {counters}")

if __name__ == "__main__":
    main()