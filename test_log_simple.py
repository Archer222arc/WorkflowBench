#!/usr/bin/env python3
"""
简化的日志测试
"""

from batch_test_runner import BatchTestRunner, TestTask
from pathlib import Path

def test_simple():
    print("=" * 60)
    print("简化日志测试")
    print("=" * 60)
    
    # 创建runner
    runner = BatchTestRunner(debug=True, silent=False, save_logs=True)
    
    # 运行单个测试
    print(f"\n运行单个测试...")
    result = runner.run_single_test(
        model='gpt-4o-mini',
        task_type='simple_task',
        prompt_type='baseline',
        difficulty='easy',
        tool_success_rate=0.8
    )
    results = [result] if result else []
    
    print(f"\n测试完成，返回 {len(results)} 个结果")
    
    # 检查日志文件
    log_dir = Path("workflow_quality_results/test_logs")
    if log_dir.exists():
        txt_files = list(log_dir.glob("*.txt"))
        json_files = list(log_dir.glob("*.json"))
        
        print(f"\n日志目录中的文件:")
        print(f"  TXT文件: {len(txt_files)}")
        print(f"  JSON文件: {len(json_files)}")
        
        if txt_files:
            # 显示最新的文件
            latest = max(txt_files, key=lambda f: f.stat().st_mtime)
            print(f"\n最新的TXT日志: {latest.name}")
            
            # 检查文件名格式
            if "gpt_4o_mini" in latest.name:
                print("  ✅ 文件名包含模型名")
                if latest.name.startswith("gpt_4o_mini"):
                    print("  ✅ 模型名在文件名开头")
            else:
                print("  ❌ 文件名不包含模型名")
    else:
        print(f"\n日志目录不存在: {log_dir}")

if __name__ == "__main__":
    test_simple()