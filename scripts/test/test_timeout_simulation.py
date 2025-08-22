#!/usr/bin/env python3
"""模拟测试超时情况以验证超时错误分类"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from enhanced_cumulative_manager import EnhancedCumulativeManager
from data_structure_v3 import DataStructureV3

class MockTestRecord:
    """模拟测试记录"""
    def __init__(self, model='test-model', success=False, error='Test timeout after 180 seconds'):
        from datetime import datetime
        self.model = model
        self.task_type = 'simple_task'
        self.prompt_type = 'baseline'
        self.difficulty = 'easy'
        self.is_flawed = False
        self.flaw_type = None
        self.tool_success_rate = 0.8
        self.success = success
        self.error = error
        self.success_level = 'failure' if not success else 'full_success'
        self.execution_time = 180
        self.turns = 0
        self.tool_calls = []
        self.executed_tools = []
        self.required_tools = ['tool1', 'tool2']
        self.workflow_score = 0.0
        self.phase2_score = 0.0
        self.quality_score = 0.0
        self.final_score = 0.0
        self.execution_history = []
        self.partial_success = 0
        self.timestamp = datetime.now().isoformat()

def test_timeout_classification():
    """测试超时错误是否被正确分类和统计"""
    
    print("🔍 超时错误分类和统计测试")
    print("=" * 50)
    
    # 创建临时数据库
    temp_db_path = Path('temp_test_database.json')
    if temp_db_path.exists():
        temp_db_path.unlink()
    
    # 创建管理器
    manager = EnhancedCumulativeManager(use_ai_classification=False)  # 使用规则分类便于测试
    # 设置临时数据库路径
    manager.database_path = temp_db_path
    
    # 测试不同类型的错误
    test_cases = [
        # 超时错误
        MockTestRecord(success=False, error='Test timeout after 180 seconds'),
        MockTestRecord(success=False, error='Agent timeout occurred'),
        MockTestRecord(success=False, error='execution timeout'),
        
        # 格式错误
        MockTestRecord(success=False, error='format errors detected'),
        MockTestRecord(success=False, error='tool call format issue'),
        
        # 其他错误
        MockTestRecord(success=False, error='unknown error occurred'),
    ]
    
    # 添加测试记录
    for i, record in enumerate(test_cases):
        print(f"添加测试 {i+1}: '{record.error}'")
        manager.add_test_result(record)
    
    # 保存并检查结果
    manager.save_database()
    
    # 读取数据库检查分类结果
    with open(temp_db_path, 'r') as f:
        import json
        db = json.load(f)
    
    print(f"\n📊 分类结果:")
    
    model_data = db['models']['test-model']
    task_data = model_data['by_prompt_type']['baseline']['by_tool_success_rate']['0.8']['by_difficulty']['easy']['by_task_type']['simple_task']
    
    timeout_errors = task_data.get('timeout_errors', 0)
    format_errors = task_data.get('tool_call_format_errors', 0)
    other_errors = task_data.get('other_errors', 0)
    total_errors = task_data.get('total_errors', 0)
    
    print(f"  超时错误: {timeout_errors}")
    print(f"  格式错误: {format_errors}")
    print(f"  其他错误: {other_errors}")
    print(f"  总错误数: {total_errors}")
    
    # 验证结果
    expected_timeout = 3  # 前三个是超时错误
    expected_format = 2   # 第4-5个是格式错误
    expected_other = 1    # 最后一个是其他错误
    
    print(f"\n✅ 验证结果:")
    print(f"  超时错误: {'✅' if timeout_errors == expected_timeout else '❌'} (期望:{expected_timeout}, 实际:{timeout_errors})")
    print(f"  格式错误: {'✅' if format_errors == expected_format else '❌'} (期望:{expected_format}, 实际:{format_errors})")
    print(f"  其他错误: {'✅' if other_errors == expected_other else '❌'} (期望:{expected_other}, 实际:{other_errors})")
    print(f"  总计一致: {'✅' if total_errors == len(test_cases) else '❌'} (期望:{len(test_cases)}, 实际:{total_errors})")
    
    # 检查错误率
    if total_errors > 0:
        timeout_rate = task_data.get('timeout_error_rate', 0)
        format_rate = task_data.get('format_error_rate', 0)
        other_rate = task_data.get('other_error_rate', 0)
        
        expected_timeout_rate = timeout_errors / total_errors
        expected_format_rate = format_errors / total_errors
        expected_other_rate = other_errors / total_errors
        
        print(f"\n📊 错误率验证:")
        print(f"  超时错误率: {timeout_rate:.2%} (期望: {expected_timeout_rate:.2%})")
        print(f"  格式错误率: {format_rate:.2%} (期望: {expected_format_rate:.2%})")
        print(f"  其他错误率: {other_rate:.2%} (期望: {expected_other_rate:.2%})")
        
        rate_sum = timeout_rate + format_rate + other_rate
        print(f"  错误率总和: {rate_sum:.2%} {'✅' if abs(rate_sum - 1.0) < 0.001 else '❌'}")
    
    # 清理临时文件
    if temp_db_path.exists():
        temp_db_path.unlink()
    
    print(f"\n💡 结论:")
    if timeout_errors == expected_timeout:
        print("✅ 超时错误分类系统工作正常")
        print("✅ 如果数据库中显示 timeout_errors=0，说明测试过程中确实没有发生超时")
    else:
        print("❌ 超时错误分类系统存在问题")

if __name__ == "__main__":
    test_timeout_classification()