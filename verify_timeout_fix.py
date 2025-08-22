#!/usr/bin/env python3
"""
验证timeout_errors修复效果
"""

import os
os.environ['STORAGE_FORMAT'] = 'json'  # 使用JSON格式以便查看详细数据

from cumulative_test_manager import TestRecord
from enhanced_cumulative_manager import EnhancedCumulativeManager

print("=" * 70)
print("验证timeout_errors分类修复")
print("=" * 70)

# 创建管理器
manager = EnhancedCumulativeManager()

# 创建一个模拟DeepSeek V3超时的测试记录
record = TestRecord(
    model='timeout-fix-test',
    task_type='api_integration',
    prompt_type='optimal',
    difficulty='easy'
)

# 设置测试结果 - 模拟超时失败的情况
record.tool_success_rate = 0.8
record.success = False
record.partial_success = False
record.execution_time = 120.0  # 超时
record.turns = 1
record.tool_calls = 0  # 没有工具调用（因为超时了）
record.success_level = 'failure'
record.execution_status = 'failure'
record.error_message = "Test timeout after 10 minutes"

# 动态添加AI分类字段（模拟batch_test_runner的行为）
# 这是关键 - AI正确分类为timeout_errors
setattr(record, 'ai_error_category', 'timeout_errors')
setattr(record, 'ai_error_reason', 'The test timed out after 10 minutes')
setattr(record, 'ai_confidence', 0.95)

print(f"\n测试记录:")
print(f"  模型: {record.model}")
print(f"  任务类型: {record.task_type}")
print(f"  成功级别: {record.success_level}")
print(f"  工具调用数: {record.tool_calls}")
print(f"  错误消息: {record.error_message}")
print(f"  AI分类: {getattr(record, 'ai_error_category', 'N/A')}")

# 添加到manager
success = manager.add_test_result_with_classification(record)
print(f"\n添加记录: {'成功' if success else '失败'}")

# 保存数据库
manager.save_database()
print("数据已保存")

# 检查JSON数据
import json
from pathlib import Path

db_file = Path('pilot_bench_cumulative_results/master_database.json')
if db_file.exists():
    with open(db_file, 'r') as f:
        db = json.load(f)
    
    if 'timeout-fix-test' in db.get('models', {}):
        model_data = db['models']['timeout-fix-test']
        print("\n✅ 找到测试模型数据")
        
        # Navigate the hierarchy
        try:
            optimal = model_data['by_prompt_type']['optimal']
            rate_08 = optimal['by_tool_success_rate']['0.8']
            easy = rate_08['by_difficulty']['easy']
            api_int = easy['by_task_type']['api_integration']
            
            print(f"\n错误分类结果:")
            print(f"  total_errors: {api_int.get('total_errors', 0)}")
            print(f"  timeout_errors: {api_int.get('timeout_errors', 0)}")
            print(f"  tool_call_format_errors: {api_int.get('tool_call_format_errors', 0)}")
            print(f"  other_errors: {api_int.get('other_errors', 0)}")
            
            if api_int.get('timeout_errors', 0) > 0:
                print("\n✅ 成功: timeout_errors被正确分类!")
            elif api_int.get('tool_call_format_errors', 0) > 0:
                print("\n❌ 问题: timeout_errors被错误分类为tool_call_format_errors")
                print("   原因: 没有工具调用时默认分类为format错误")
            elif api_int.get('other_errors', 0) > 0:
                print("\n❌ 问题: timeout_errors被错误分类为other_errors")
        except KeyError as e:
            print(f"\n❌ 数据结构错误: {e}")
    else:
        print("\n❌ 未找到测试模型")

print("\n" + "=" * 70)
print("测试完成")