#!/usr/bin/env python3
"""
测试共享调试日志目录的脚本
验证多个模型的日志都保存在同一个目录中
"""

import subprocess
import time
from pathlib import Path
from datetime import datetime
import tempfile
import os

def test_shared_debug_directory():
    """测试使用共享的调试日志目录"""
    
    print("=" * 60)
    print("测试共享调试日志目录")
    print("=" * 60)
    
    # 创建一个共享的调试目录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    shared_debug_dir = f"logs/debug_ultra_test_{timestamp}"
    
    print(f"\n📁 使用共享调试目录: {shared_debug_dir}")
    
    # 测试的模型列表
    models = [
        'DeepSeek-V3-0324',
        'DeepSeek-R1-0528',
        'qwen2.5-72b-instruct'
    ]
    
    processes = []
    
    # 依次启动每个模型的测试，都使用同一个调试目录
    for model in models:
        print(f"\n启动 {model} 测试...")
        
        cmd = [
            'python', 'ultra_parallel_runner_debug.py',
            '--model', model,
            '--num-instances', '1',
            '--max-workers', '2',
            '--tool-success-rate', '0.8',
            '--prompt-types', 'baseline',
            '--difficulty', 'easy',
            '--task-types', 'simple_task',
            '--debug-log-dir', shared_debug_dir  # 使用共享目录
        ]
        
        # 启动进程
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        processes.append((model, proc))
        
        # 稍微等待让进程开始创建日志
        time.sleep(2)
    
    # 让所有进程运行一会儿
    print("\n让测试运行5秒...")
    time.sleep(5)
    
    # 终止所有进程
    print("\n终止所有测试进程...")
    for model, proc in processes:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        print(f"  {model} 已终止")
    
    # 检查共享目录中的日志文件
    print(f"\n检查共享目录: {shared_debug_dir}")
    
    debug_dir = Path(shared_debug_dir)
    if not debug_dir.exists():
        print("❌ 调试目录不存在！")
        return False
    
    log_files = sorted(debug_dir.glob('*.log'))
    
    print(f"\n找到 {len(log_files)} 个日志文件:")
    
    # 分析每个模型的日志
    model_logs = {}
    for log_file in log_files:
        print(f"  📄 {log_file.name}")
        
        # 从文件名中提取模型信息
        name_parts = log_file.stem.lower()
        for model in models:
            model_key = model.lower().replace('-', '_').replace('.', '_')
            if model_key in name_parts:
                if model not in model_logs:
                    model_logs[model] = []
                model_logs[model].append(log_file.name)
                break
    
    # 统计结果
    print("\n📊 统计结果:")
    all_models_found = True
    
    for model in models:
        if model in model_logs:
            count = len(model_logs[model])
            print(f"  ✅ {model}: {count} 个日志文件")
            for log_name in model_logs[model]:
                print(f"      - {log_name}")
        else:
            print(f"  ❌ {model}: 没有找到日志文件")
            all_models_found = False
    
    # 验证文件名唯一性
    print("\n验证文件名唯一性...")
    if len(log_files) == len(set(f.name for f in log_files)):
        print("  ✅ 所有文件名都是唯一的")
    else:
        print("  ❌ 存在重复的文件名")
    
    # 最终结果
    print("\n" + "=" * 60)
    if all_models_found and len(log_files) >= len(models):
        print("✅ 测试成功！")
        print("   - 所有模型的日志都保存在同一个目录中")
        print(f"   - 共享目录: {shared_debug_dir}")
        print(f"   - 包含 {len(log_files)} 个日志文件")
        return True
    else:
        print("❌ 测试失败！")
        if not all_models_found:
            print("   - 某些模型的日志缺失")
        if len(log_files) < len(models):
            print(f"   - 日志文件数量不足 ({len(log_files)} < {len(models)})")
        return False

def test_bash_script_integration():
    """测试与bash脚本的集成"""
    
    print("\n" + "=" * 60)
    print("测试bash脚本集成")
    print("=" * 60)
    
    # 创建一个简单的测试脚本
    test_script = """#!/bin/bash
    
# 模拟run_systematic_test_final.sh的行为
GLOBAL_DEBUG_LOG_DIR=""
DEBUG_LOG=true

# 函数：运行单个模型
run_model() {
    local model=$1
    
    # 如果全局调试目录未设置，创建一个新的
    if [ -z "$GLOBAL_DEBUG_LOG_DIR" ]; then
        GLOBAL_DEBUG_LOG_DIR="logs/debug_ultra_test_$(date +%Y%m%d_%H%M%S)"
        echo "创建全局调试目录: $GLOBAL_DEBUG_LOG_DIR"
    fi
    
    echo "运行模型: $model"
    echo "使用调试目录: $GLOBAL_DEBUG_LOG_DIR"
    
    # 运行测试（短时间）
    timeout 3 python ultra_parallel_runner_debug.py \
        --model "$model" \
        --num-instances 1 \
        --max-workers 2 \
        --tool-success-rate 0.8 \
        --prompt-types baseline \
        --difficulty easy \
        --task-types simple_task \
        --debug-log-dir "$GLOBAL_DEBUG_LOG_DIR" \
        > /dev/null 2>&1
}

# 测试多个模型
run_model "DeepSeek-V3-0324"
run_model "DeepSeek-R1-0528"

echo "测试完成，检查目录: $GLOBAL_DEBUG_LOG_DIR"
ls -la "$GLOBAL_DEBUG_LOG_DIR" 2>/dev/null | head -5
"""
    
    # 写入临时脚本文件
    script_path = Path("test_integration.sh")
    script_path.write_text(test_script)
    script_path.chmod(0o755)
    
    print("\n运行集成测试脚本...")
    
    try:
        # 运行脚本
        result = subprocess.run(
            ["bash", str(script_path)],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print("\n脚本输出:")
        print(result.stdout)
        
        if result.stderr:
            print("\n错误输出:")
            print(result.stderr)
        
        # 检查是否创建了共享目录
        if "创建全局调试目录" in result.stdout:
            print("\n✅ bash脚本正确创建了全局调试目录")
        else:
            print("\n❌ bash脚本未创建全局调试目录")
        
    finally:
        # 清理临时脚本
        script_path.unlink(missing_ok=True)

if __name__ == "__main__":
    # 运行测试
    success = test_shared_debug_directory()
    
    # 如果第一个测试成功，运行集成测试
    if success:
        test_bash_script_integration()
    
    print("\n" + "=" * 60)
    print("所有测试完成")
    print("=" * 60)