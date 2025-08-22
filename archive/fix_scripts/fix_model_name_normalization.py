#!/usr/bin/env python3
"""
修复cumulative_test_manager.py中的模型名称规范化问题
确保同一模型的不同实例被正确合并
"""

def generate_patch():
    """生成需要添加的代码补丁"""
    
    normalization_function = '''
def normalize_model_name(model_name: str) -> str:
    """
    规范化模型名称，将同一模型的不同实例映射到主名称
    例如：deepseek-v3-0324-2 -> DeepSeek-V3-0324
    """
    model_name_lower = model_name.lower()
    
    # DeepSeek V3 系列
    if 'deepseek-v3' in model_name_lower or 'deepseek_v3' in model_name_lower:
        return 'DeepSeek-V3-0324'
    
    # DeepSeek R1 系列
    if 'deepseek-r1' in model_name_lower or 'deepseek_r1' in model_name_lower:
        return 'DeepSeek-R1-0528'
    
    # Llama 3.3 系列
    if 'llama-3.3' in model_name_lower or 'llama_3.3' in model_name_lower:
        return 'Llama-3.3-70B-Instruct'
    
    # Qwen 系列 - 根据参数规模确定具体模型
    if 'qwen' in model_name_lower:
        if '72b' in model_name_lower:
            return 'qwen2.5-72b-instruct'
        elif '32b' in model_name_lower:
            return 'qwen2.5-32b-instruct'
        elif '14b' in model_name_lower:
            return 'qwen2.5-14b-instruct'
        elif '7b' in model_name_lower:
            return 'qwen2.5-7b-instruct'
        elif '3b' in model_name_lower:
            return 'qwen2.5-3b-instruct'
    
    # 其他模型保持原样
    return model_name
'''
    
    modification_in_add_test_result = '''
    # 在第179行后添加：
    model = normalize_model_name(record.model)  # 规范化模型名称
'''
    
    modification_in_update_test_result = '''
    # 同样需要在update_test_result方法中添加规范化
    model = normalize_model_name(record["model"])
'''
    
    print("需要添加的代码：")
    print("\n1. 在CumulativeTestManager类中添加normalize_model_name方法：")
    print(normalization_function)
    print("\n2. 在add_test_result方法中（第179行后）：")
    print(modification_in_add_test_result)
    print("\n3. 在update_test_result_with_dict方法中也需要类似修改")

if __name__ == "__main__":
    generate_patch()