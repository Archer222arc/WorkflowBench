#!/usr/bin/env python3
"""
简单测试验证脚本 - 验证数据保存功能
"""

import os
import sys
import json
import subprocess
import time
from pathlib import Path
from datetime import datetime

def run_simple_test():
    """运行一个简单的测试验证数据保存"""
    
    print("="*60)
    print("🧪 简单测试 - 验证数据保存")
    print(f"时间: {datetime.now()}")
    print("="*60)
    
    # 记录测试前的状态
    db_path = Path("pilot_bench_cumulative_results/master_database.json")
    
    before_total = 0
    if db_path.exists():
        with open(db_path) as f:
            db_before = json.load(f)
        before_total = db_before['summary'].get('total_tests', 0)
        print(f"\n📊 测试前: 总测试数 = {before_total}")
    
    # 设置环境变量
    env = os.environ.copy()
    env['STORAGE_FORMAT'] = 'json'
    env['PYTHONUNBUFFERED'] = '1'
    
    # 构建测试命令 - 最小化参数
    cmd = [
        'python', '-u',
        'smart_batch_runner.py',
        '--model', 'gpt-4o-mini',
        '--prompt-types', 'baseline',
        '--difficulty', 'easy', 
        '--task-types', 'simple_task',
        '--num-instances', '1',
        '--tool-success-rate', '0.8',
        '--max-workers', '5',
        '--no-adaptive',
        '--qps', '5',
        '--batch-commit',
        '--checkpoint-interval', '1',
        '--no-save-logs',
        '--silent'
    ]
    
    print(f"\n🚀 执行命令:")
    print(f"   {' '.join(cmd)}")
    
    # 运行测试
    print("\n⏳ 运行中...")
    start_time = time.time()
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        timeout=300
    )
    
    duration = time.time() - start_time
    
    # 显示结果
    if result.returncode == 0:
        print(f"✅ 测试成功 (耗时: {duration:.1f}秒)")
    else:
        print(f"❌ 测试失败 (退出码: {result.returncode})")
        if result.stderr:
            print("错误信息:")
            print(result.stderr[-500:])  # 最后500字符
    
    # 检查测试后的状态
    time.sleep(2)  # 等待数据写入
    
    after_total = 0
    if db_path.exists():
        with open(db_path) as f:
            db_after = json.load(f)
        after_total = db_after['summary'].get('total_tests', 0)
        print(f"\n📊 测试后: 总测试数 = {after_total}")
        
        if after_total > before_total:
            print(f"✅ 数据已保存! 新增 {after_total - before_total} 个测试")
            
            # 显示最新的测试组
            if 'test_groups' in db_after:
                recent = sorted(db_after['test_groups'].items(),
                              key=lambda x: x[1].get('timestamp', ''),
                              reverse=True)[:1]
                if recent:
                    gid, data = recent[0]
                    print(f"   最新测试: {data['model']} - {data['total_tests']} tests @ {data['timestamp'][:19]}")
        else:
            print("⚠️ 数据未更新!")
    
    return after_total > before_total

if __name__ == "__main__":
    success = run_simple_test()
    sys.exit(0 if success else 1)