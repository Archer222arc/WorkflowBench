#!/usr/bin/env python3
"""
验证所有统计字段都被正确计算和保存
"""

from batch_test_runner import BatchTestRunner, TestTask
from pathlib import Path
import json

def test_all_statistics():
    print("测试所有统计字段...")
    
    # 创建测试运行器
    runner = BatchTestRunner(
        debug=True,
        save_logs=False,
        use_ai_classification=True  # 强制启用AI分类
    )
    
    # 创建测试任务
    task = TestTask(
        model='test-model',
        task_type='simple_task',
        prompt_type='baseline',
        difficulty='easy',
        tool_success_rate=0.8
    )
    
    # 运行单个测试
    result = runner.run_single_test(
        model=task.model,
        task_type=task.task_type,
        prompt_type=task.prompt_type,
        is_flawed=False,
        flaw_type=None,
        tool_success_rate=task.tool_success_rate
    )
    
    # 检查结果
    print("\n检查返回的结果：")
    print(f"  Success: {result.get('success')}")
    print(f"  Workflow Score: {result.get('workflow_score')}")
    print(f"  Phase2 Score: {result.get('phase2_score')}")
    print(f"  Quality Score: {result.get('quality_score')}")
    print(f"  Final Score: {result.get('final_score')}")
    print(f"  Tool Coverage: {result.get('tool_coverage_rate')}")
    
    # 检查是否所有分数都有值
    scores = ['workflow_score', 'phase2_score', 'quality_score', 'final_score']
    all_scores_present = all(result.get(score) is not None for score in scores)
    
    if all_scores_present:
        print("\n✅ 所有质量分数都已计算！")
    else:
        print("\n❌ 某些质量分数缺失")
        for score in scores:
            if result.get(score) is None:
                print(f"    缺失: {score}")
    
    return all_scores_present

if __name__ == "__main__":
    success = test_all_statistics()
    exit(0 if success else 1)
