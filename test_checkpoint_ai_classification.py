#!/usr/bin/env python3
"""
测试checkpoint save是否正确传递ai_error_category字段
"""

import os
os.environ['STORAGE_FORMAT'] = 'parquet'

from batch_test_runner import BatchTestRunner
from cumulative_test_manager import TestRecord

print("=" * 70)
print("测试checkpoint save的AI分类传递")
print("=" * 70)

# 创建runner
runner = BatchTestRunner(
    debug=True,
    checkpoint_interval=1,  # 每个测试后立即保存
    enable_database_updates=False  # 使用checkpoint save
)

# 模拟一个失败的测试结果
result = {
    'model': 'test-checkpoint',
    'task_type': 'api_integration',
    'prompt_type': 'optimal',
    'difficulty': 'easy',
    'success': False,
    'success_level': 'failure',
    'execution_time': 600.0,
    'turns': 1,
    'tool_calls': 0,
    'error': 'Test timeout after 10 minutes',
    'ai_error_category': 'timeout_errors',  # AI分类结果
    'ai_error_reason': 'The test timed out',
    'ai_confidence': 0.85
}

print("\n测试结果包含AI分类:")
print(f"  ai_error_category: {result.get('ai_error_category')}")
print(f"  ai_error_reason: {result.get('ai_error_reason')}")
print(f"  ai_confidence: {result.get('ai_confidence')}")

# 调用checkpoint save
print("\n调用_checkpoint_save...")
runner._lazy_init()
runner._checkpoint_save([result], task_model='test-checkpoint', force=True)

print("\n✅ 测试完成")
print("如果修复成功，Parquet数据中应该包含timeout_errors而不是other_errors")