#!/usr/bin/env python3
"""
强制产生错误以测试AI分类
"""

from batch_test_runner import BatchTestRunner

# 创建runner
runner = BatchTestRunner(debug=True, silent=False)

# 创建一个会产生错误的测试结果
test_result = {
    'success': False,
    'success_level': 'failure',
    'execution_time': 10.5,
    'turns': 20,  # 超过最大回合数
    'tool_calls': ['tool1', 'tool2', 'tool3'],
    'executed_tools': ['tool1'],  # 只成功执行了1个
    'required_tools': ['tool1', 'tool2', 'tool3'],
    'error_message': 'Maximum turns exceeded',
    'task_id': 'test_task',
    'prompt_type': 'baseline'
}

# 手动调用AI分类
if runner.ai_classifier:
    print("测试AI分类器...")
    
    # 创建模拟的txt文件内容
    txt_content = """
[TURN 1/20]
Calling tool: tool1
Result: SUCCESS

[TURN 2/20]
Calling tool: tool2
Result: FAILED

[TURN 3/20]
Calling tool: tool3
Result: FAILED

...

[TURN 20/20]
Maximum turns exceeded. Task terminated.
"""
    
    # 调用分类器
    error_type, category, confidence = runner.ai_classifier.classify_from_txt_content(
        txt_content=txt_content
    )
    
    print(f"\n分类结果:")
    print(f"  类别: {category}")
    print(f"  置信度: {confidence}")
    
    # 验证分类
    if category == 'max_turns_errors':
        print("  ✅ 正确分类为max_turns_errors")
    else:
        print(f"  ⚠️ 分类为{category}，预期是max_turns_errors")
        
    # 测试其他错误类型
    print("\n测试其他错误类型:")
    
    # 1. 超时错误
    timeout_txt = "[ERROR] Test timeout after 10 minutes"
    _, cat, conf = runner.ai_classifier.classify_from_txt_content(timeout_txt)
    print(f"  超时错误 -> {cat} (置信度: {conf})")
    
    # 2. 工具选择错误
    tool_error_txt = "[ERROR] Wrong tool selected: used data_processor instead of file_handler"
    _, cat, conf = runner.ai_classifier.classify_from_txt_content(tool_error_txt)
    print(f"  工具选择错误 -> {cat} (置信度: {conf})")
    
    # 3. 参数错误
    param_error_txt = "[ERROR] Invalid parameters: missing required field 'input_path'"
    _, cat, conf = runner.ai_classifier.classify_from_txt_content(param_error_txt)
    print(f"  参数错误 -> {cat} (置信度: {conf})")
    
else:
    print("❌ AI分类器未初始化")

print("\n测试完成!")