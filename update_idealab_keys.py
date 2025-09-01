#!/usr/bin/env python3
"""
临时脚本：修改api_client_manager.py让所有IdealLab闭源模型使用key 0
"""

def update_api_client_manager():
    file_path = "/Users/ruicheng/Documents/GitHub/WorkflowBench/api_client_manager.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 找到_get_idealab_client方法中的key选择部分
    target_line = "api_key, actual_index = self._select_ideallab_key_with_index(prompt_type, key_index)"
    
    if target_line in content:
        replacement = '''        # 闭源模型强制使用key 0
        if any(keyword in model.lower() for keyword in ['claude', 'o3', 'gemini', 'kimi']):
            key_index = 0  # 强制使用key 0
        
        api_key, actual_index = self._select_ideallab_key_with_index(prompt_type, key_index)'''
        
        content = content.replace(target_line, replacement)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ 成功修改api_client_manager.py，闭源模型现在强制使用key 0")
        print("修改内容：在_get_ideallab_client方法中添加闭源模型检查")
    else:
        print("❌ 未找到目标行，请检查文件内容")
        print("查找的目标行：", target_line)

if __name__ == "__main__":
    update_api_client_manager()