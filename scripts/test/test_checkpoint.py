#!/usr/bin/env python3
"""测试checkpoint功能"""

import sys
import signal
import time
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from smart_batch_runner import run_batch_test_smart

def signal_handler(sig, frame):
    print("\n⚠️  收到中断信号，正在保存checkpoint...")
    sys.exit(0)

# 注册中断处理
signal.signal(signal.SIGINT, signal_handler)

def test_checkpoint():
    """测试checkpoint功能"""
    print("=" * 60)
    print("测试Checkpoint功能")
    print("=" * 60)
    print("\n测试配置：")
    print("  - 模型: gpt-4o-mini")
    print("  - 任务类型: simple_task,basic_task (共40个测试)")
    print("  - Checkpoint间隔: 10个测试")
    print("  - 预期: 应该在第10、20、30个测试后保存")
    print("\n可以按Ctrl+C中断测试，检查是否保存了中间结果")
    print("=" * 60)
    
    # 运行测试
    success = run_batch_test_smart(
        model="gpt-4o-mini",
        prompt_types="baseline",
        difficulty="easy",
        task_types="simple_task,basic_task",  # 2种任务类型
        num_instances=20,  # 每种20个，共40个测试
        adaptive=True,
        tool_success_rate=0.8,
        batch_commit=True,  # 使用批量提交模式
        checkpoint_interval=10,  # 每10个测试保存一次
        max_workers=5,  # 用较少的并发便于观察
        save_logs=False,  # 不保存日志以加快速度
        silent=False
    )
    
    if success:
        print("\n✅ 测试完成！")
    else:
        print("\n❌ 测试失败")
    
    return success

if __name__ == "__main__":
    test_checkpoint()