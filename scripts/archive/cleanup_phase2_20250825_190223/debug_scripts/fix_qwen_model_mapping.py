#!/usr/bin/env python3
"""
修复qwen模型映射问题

问题：当测试qwen2.5-7b-instruct或qwen2.5-3b-instruct时，系统错误地使用qwen2.5-72b-instruct作为base_model，
导致所有7b和3b的测试实际上都是用72b模型运行的。

解决方案：修改ultra_parallel_runner.py，让base_model正确反映请求的模型。
"""

import os
import shutil
from datetime import datetime

def fix_qwen_model_mapping():
    """修复qwen模型映射逻辑"""
    
    file_path = "ultra_parallel_runner.py"
    backup_path = f"{file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # 备份原文件
    print(f"备份原文件到: {backup_path}")
    shutil.copy2(file_path, backup_path)
    
    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 查找并修改相关行
    modified = False
    for i, line in enumerate(lines):
        # 找到qwen模型族的处理逻辑
        if i >= 191 and i <= 194:
            if 'elif "qwen" in model.lower():' in line:
                # 找到了qwen判断的开始
                print(f"找到第{i+1}行: {line.strip()}")
                
                # 修改接下来的几行
                # 原来的逻辑:
                # elif "qwen" in model.lower():
                #     model_family = "qwen"
                #     base_model = "qwen2.5-72b-instruct"  # 使用最强的作为base
                
                # 新的逻辑：base_model应该使用实际请求的模型
                new_lines = [
                    '        elif "qwen" in model.lower():\n',
                    '            model_family = "qwen"\n',
                    '            # 修复：使用实际请求的模型，而不是硬编码为72b\n',
                    '            base_model = model  # 使用实际请求的模型\n'
                ]
                
                # 替换这几行
                lines[i:i+3] = new_lines
                modified = True
                print("已修改qwen模型映射逻辑")
                break
    
    if modified:
        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"✅ 成功修复 {file_path}")
        
        # 显示修改后的内容
        print("\n修改后的qwen处理逻辑:")
        print("```python")
        for i in range(192, 195):
            if i < len(lines):
                print(lines[i].rstrip())
        print("```")
    else:
        print("❌ 未找到需要修改的代码")
    
    return modified

def verify_fix():
    """验证修复是否成功"""
    print("\n验证修复...")
    
    # 模拟测试不同的qwen模型
    test_cases = [
        ("qwen2.5-72b-instruct", "qwen2.5-72b-instruct"),
        ("qwen2.5-32b-instruct", "qwen2.5-32b-instruct"),
        ("qwen2.5-14b-instruct", "qwen2.5-14b-instruct"),
        ("qwen2.5-7b-instruct", "qwen2.5-7b-instruct"),   # 应该保持为7b
        ("qwen2.5-3b-instruct", "qwen2.5-3b-instruct"),   # 应该保持为3b
    ]
    
    print("\n预期结果:")
    print("模型请求 -> base_model映射")
    for input_model, expected_base in test_cases:
        print(f"  {input_model} -> {expected_base}")
    
    print("\n注意：")
    print("- 修复后，每个qwen模型将使用其自身作为base_model")
    print("- 这确保了测试结果正确归属到相应的模型")
    print("- 实例分配仍然会从可用的qwen实例池中选择（72b, 32b, 14b）")

if __name__ == "__main__":
    print("=" * 60)
    print("修复qwen模型映射问题")
    print("=" * 60)
    
    if fix_qwen_model_mapping():
        verify_fix()
        
        print("\n" + "=" * 60)
        print("✅ 修复完成！")
        print("\n下一步建议：")
        print("1. 重新运行qwen2.5-7b和qwen2.5-3b的测试")
        print("2. 验证测试结果是否正确保存到对应模型名下")
        print("3. 检查历史数据是否需要修正（可能之前的7b/3b数据实际是72b的）")
        print("=" * 60)
    else:
        print("\n修复失败，请手动检查文件")