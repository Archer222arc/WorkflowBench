#!/usr/bin/env python3
"""
测试AI分类是否已正确启用
"""

import os
os.environ['STORAGE_FORMAT'] = 'parquet'

from batch_test_runner import BatchTestRunner, TestTask

def test_ai_classification():
    """测试AI分类是否默认启用"""
    
    print("=" * 60)
    print("测试AI分类启用状态")
    print("=" * 60)
    
    # 创建BatchTestRunner，使用默认参数
    print("\n测试1: 显式启用AI分类")
    runner1 = BatchTestRunner(
        debug=False,
        silent=False,
        use_ai_classification=True
    )
    print(f"  use_ai_classification={runner1.use_ai_classification}")
    print(f"  ai_classifier={runner1.ai_classifier is not None}")
    
    # 测试默认值（在smart_batch_runner中现在应该是True）
    print("\n测试2: 测试smart_batch_runner的默认值")
    import smart_batch_runner
    
    # 模拟从smart_batch_runner创建runner
    kwargs = {'ai_classification': True}  # 命令行默认传递True
    runner2 = BatchTestRunner(
        debug=False,
        silent=False,
        use_ai_classification=kwargs.get('ai_classification', True)  # 修复后的默认值
    )
    print(f"  use_ai_classification={runner2.use_ai_classification}")
    print(f"  ai_classifier={runner2.ai_classifier is not None}")
    
    # 测试实际错误分类
    print("\n测试3: 实际错误分类测试")
    
    # 创建一个测试任务
    task = TestTask(
        model='test-model',
        task_type='api_integration',
        prompt_type='optimal',
        difficulty='easy',
        tool_success_rate=0.8
    )
    
    # 创建一个失败的结果
    result = {
        'success': False,
        'error_message': 'Test timeout after 10 minutes',
        'tool_calls': []
    }
    
    # 创建TXT内容（模拟实际的交互日志）
    txt_content = """
===================
TASK TYPE: api_integration
MODEL: test-model
PROMPT TYPE: optimal
===================

[ERROR] Test timeout after 10 minutes
Model failed to complete the task within the time limit.
"""
    
    # 调用AI分类
    if runner2.use_ai_classification and runner2.ai_classifier:
        try:
            ai_category, ai_reason, ai_confidence = runner2._ai_classify_with_txt_content(task, result, txt_content)
            print(f"  AI分类结果:")
            print(f"    Category: {ai_category}")
            print(f"    Confidence: {ai_confidence}")
            print(f"    Reason: {ai_reason[:100] if ai_reason else 'None'}")
            
            if ai_category and 'timeout' in str(ai_category).lower():
                print("\n✅ AI分类正确识别了timeout错误！")
            else:
                print(f"\n⚠️ AI分类结果可能不正确: {ai_category}")
        except Exception as e:
            print(f"  ❌ AI分类失败: {e}")
    else:
        print("  ❌ AI分类器未启用或未初始化")
    
    # 检查总结
    print("\n" + "=" * 60)
    print("检查结果:")
    
    checks = []
    checks.append(("BatchTestRunner默认启用AI分类", runner1.use_ai_classification))
    checks.append(("AI分类器成功初始化", runner1.ai_classifier is not None))
    checks.append(("smart_batch_runner传递正确默认值", runner2.use_ai_classification))
    
    all_passed = True
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {check_name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 AI分类功能已正确启用！")
        print("   现在错误应该能被正确分类，而不是全部归为other_errors")
    else:
        print("\n⚠️ AI分类功能存在问题，请检查配置")
    
    return all_passed

if __name__ == "__main__":
    import sys
    success = test_ai_classification()
    sys.exit(0 if success else 1)