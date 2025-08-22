#!/usr/bin/env python3
"""
验证所有并行功能已正确集成到smart_batch_runner.py
"""
import subprocess
import sys

def run_test(description, cmd):
    """运行测试命令"""
    print(f"\n{'='*60}")
    print(f"测试: {description}")
    print(f"命令: {' '.join(cmd)}")
    print("="*60)
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # 检查关键输出
    checks = {
        "Azure高并发": "workers=50" in result.stdout or "workers=100" in result.stdout,
        "IdealLab API Key分配": "API Key 1" in result.stdout or "API Key 2" in result.stdout,
        "多prompt并行": "prompt types" in result.stdout and "并行" in result.stdout,
        "测试完成": "批测试完成" in result.stdout or "测试完成" in result.stdout
    }
    
    success = all(checks.values()) or result.returncode == 0
    
    if success:
        print("✅ 测试通过")
    else:
        print("❌ 测试失败")
        for check, passed in checks.items():
            if not passed:
                print(f"  ❌ {check}")
    
    return success

def main():
    print("\n" + "="*70)
    print("验证smart_batch_runner.py集成功能")
    print("="*70)
    
    tests = []
    
    # 测试1: Azure模型多prompt并行
    tests.append(("Azure模型多prompt并行", [
        "python", "smart_batch_runner.py",
        "--model", "gpt-4o-mini",
        "--prompt-types", "baseline,cot",
        "--task-types", "simple_task",
        "--num-instances", "1",
        "--prompt-parallel",
        "--no-save-logs",
        "--silent"
    ]))
    
    # 测试2: IdealLab模型多prompt并行
    tests.append(("IdealLab模型多prompt并行", [
        "python", "smart_batch_runner.py",
        "--model", "qwen2.5-3b-instruct",
        "--prompt-types", "baseline,cot,optimal",
        "--task-types", "simple_task",
        "--num-instances", "1",
        "--prompt-parallel",
        "--no-save-logs"
    ]))
    
    # 测试3: 使用all参数
    tests.append(("使用all参数测试", [
        "python", "smart_batch_runner.py",
        "--model", "qwen2.5-3b-instruct",
        "--prompt-types", "all",
        "--task-types", "simple_task",
        "--num-instances", "1",
        "--prompt-parallel",
        "--no-save-logs"
    ]))
    
    # 运行所有测试
    results = []
    for desc, cmd in tests:
        try:
            success = run_test(desc, cmd)
            results.append((desc, success))
        except Exception as e:
            print(f"❌ 异常: {e}")
            results.append((desc, False))
    
    # 总结
    print("\n" + "="*70)
    print("测试总结")
    print("="*70)
    
    for desc, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {desc}: {status}")
    
    success_count = sum(1 for _, s in results if s)
    total = len(results)
    
    print(f"\n总计: {success_count}/{total} 个测试通过")
    
    if success_count == total:
        print("\n🎉 所有功能已成功集成到smart_batch_runner.py！")
        return 0
    else:
        print("\n⚠️ 部分功能可能未正确集成")
        return 1

if __name__ == "__main__":
    sys.exit(main())