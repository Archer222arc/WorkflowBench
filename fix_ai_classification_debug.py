#!/usr/bin/env python3
"""
修复AI错误分类未正常工作的问题
添加详细的调试日志
"""

import shutil
from pathlib import Path
from datetime import datetime

def add_ai_classification_debug():
    """在batch_test_runner.py中添加AI分类调试日志"""
    
    file_path = Path("batch_test_runner.py")
    
    # 备份文件
    backup_path = file_path.parent / f"{file_path.stem}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_path.suffix}"
    shutil.copy2(file_path, backup_path)
    print(f"✅ 备份文件到: {backup_path}")
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    modified = False
    changes = []
    
    for i, line in enumerate(lines):
        # 1. 在AI分类器初始化后添加调试日志
        if 'self.ai_classifier = TxtBasedAIClassifier(model_name="gpt-5-nano")' in line:
            # 在下一行添加调试
            if i + 1 < len(lines):
                indent = len(line) - len(line.lstrip())
                debug_line = f'{" " * indent}print(f"[AI_DEBUG] AI分类器初始化成功: {{self.ai_classifier}}")\n'
                lines.insert(i + 1, debug_line)
                changes.append(f"  第{i+2}行: 添加AI分类器初始化调试")
                modified = True
        
        # 2. 在_ai_classify_with_txt_content开头添加调试
        elif 'def _ai_classify_with_txt_content' in line and i + 4 < len(lines):
            # 在条件检查前添加调试
            for j in range(i+1, min(i+10, len(lines))):
                if 'if not (self.use_ai_classification' in lines[j]:
                    indent = len(lines[j]) - len(lines[j].lstrip())
                    debug_lines = [
                        f'{" " * indent}# AI分类调试信息\n',
                        f'{" " * indent}print(f"[AI_DEBUG] _ai_classify_with_txt_content called:")\n',
                        f'{" " * indent}print(f"  - use_ai_classification={{self.use_ai_classification}}")\n',
                        f'{" " * indent}print(f"  - ai_classifier={{self.ai_classifier is not None}}")\n',
                        f'{" " * indent}print(f"  - txt_content_len={{len(txt_content) if txt_content else 0}}")\n',
                        f'{" " * indent}print(f"  - task_model={{task.model}}")\n',
                        f'{" " * indent}\n'
                    ]
                    # 插入调试代码
                    lines = lines[:j] + debug_lines + lines[j:]
                    changes.append(f"  第{j}行: 添加AI分类方法调试")
                    modified = True
                    break
        
        # 3. 在AI分类被调用的地方添加调试
        elif 'ai_error_category, ai_error_reason, ai_confidence = self._ai_classify_with_txt_content' in line:
            # 在调用前添加调试
            indent = len(line) - len(line.lstrip())
            debug_line = f'{" " * indent}print(f"[AI_DEBUG] 准备调用AI分类，测试失败={{not result.get(\'success\', False)}}")\n'
            lines.insert(i, debug_line)
            changes.append(f"  第{i+1}行: 添加AI分类调用前调试")
            
            # 在调用后添加结果调试
            result_debug = f'{" " * indent}print(f"[AI_DEBUG] AI分类结果: category={{ai_error_category}}, reason={{ai_error_reason[:50] if ai_error_reason else None}}, confidence={{ai_confidence}}")\n'
            lines.insert(i + 2, result_debug)
            changes.append(f"  第{i+3}行: 添加AI分类结果调试")
            modified = True
            break
        
        # 4. 在测试执行结果处添加调试
        elif "if not result.get('success', False):" in line and 'txt_content = self._generate_txt_log_content' in lines[i+1] if i+1 < len(lines) else False:
            indent = len(line) - len(line.lstrip())
            debug_line = f'{" " * indent}print(f"[AI_DEBUG] 测试失败，将生成txt_content进行AI分类")\n'
            lines.insert(i + 1, debug_line)
            changes.append(f"  第{i+2}行: 添加失败测试调试")
            modified = True
    
    if modified:
        with open(file_path, 'w') as f:
            f.writelines(lines)
        
        print("\n✅ 已修改batch_test_runner.py:")
        for change in changes:
            print(change)
    else:
        print("⚠️ 未找到需要修改的代码位置")
    
    return modified

def add_txt_classifier_debug():
    """在txt_based_ai_classifier.py中添加调试日志"""
    
    file_path = Path("txt_based_ai_classifier.py")
    if not file_path.exists():
        print(f"⚠️ {file_path} 不存在")
        return False
    
    # 备份文件
    backup_path = file_path.parent / f"{file_path.stem}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_path.suffix}"
    shutil.copy2(file_path, backup_path)
    print(f"✅ 备份文件到: {backup_path}")
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    modified = False
    changes = []
    
    for i, line in enumerate(lines):
        # 在classify_from_txt_content方法开头添加调试
        if 'def classify_from_txt_content' in line and 'self' in line:
            # 找到方法体开始
            for j in range(i+1, min(i+10, len(lines))):
                if lines[j].strip() and not lines[j].strip().startswith('"""'):
                    indent = len(lines[j]) - len(lines[j].lstrip())
                    debug_lines = [
                        f'{" " * indent}print(f"[AI_CLASSIFIER_DEBUG] classify_from_txt_content called")\n',
                        f'{" " * indent}print(f"  - txt_content length: {{len(txt_content) if txt_content else 0}}")\n',
                        f'{" " * indent}print(f"  - client available: {{self.client is not None}}")\n',
                        f'{" " * indent}\n'
                    ]
                    lines = lines[:j] + debug_lines + lines[j:]
                    changes.append(f"  第{j}行: 添加classify_from_txt_content调试")
                    modified = True
                    break
            break
    
    if modified:
        with open(file_path, 'w') as f:
            f.writelines(lines)
        
        print(f"\n✅ 已修改{file_path}:")
        for change in changes:
            print(change)
    
    return modified

def verify_ai_configuration():
    """验证AI分类配置是否正确"""
    print("\n验证AI分类配置:")
    print("-" * 40)
    
    # 检查batch_test_runner中的默认值
    with open("batch_test_runner.py", 'r') as f:
        content = f.read()
    
    if 'use_ai_classification: bool = True' in content:
        print("✅ batch_test_runner默认启用AI分类")
    else:
        print("❌ batch_test_runner默认未启用AI分类")
    
    if 'from txt_based_ai_classifier import TxtBasedAIClassifier' in content:
        print("✅ 正确导入TxtBasedAIClassifier")
    else:
        print("❌ 未导入TxtBasedAIClassifier")
    
    # 检查smart_batch_runner的默认值
    with open("smart_batch_runner.py", 'r') as f:
        content = f.read()
    
    if "'--ai-classification', dest='ai_classification', action='store_true', default=True" in content:
        print("✅ smart_batch_runner默认启用AI分类")
    else:
        print("❌ smart_batch_runner默认未启用AI分类")
    
    # 检查ultra_parallel_runner是否传递参数
    with open("ultra_parallel_runner.py", 'r') as f:
        content = f.read()
    
    if '"--ai-classification"' in content:
        print("✅ ultra_parallel_runner传递AI分类参数")
    else:
        print("❌ ultra_parallel_runner未传递AI分类参数")

def main():
    print("=" * 60)
    print("修复AI错误分类问题 - 添加调试日志")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. 添加batch_test_runner调试
    print("\n1. 修改batch_test_runner.py")
    add_ai_classification_debug()
    
    # 2. 添加txt_based_ai_classifier调试
    print("\n2. 修改txt_based_ai_classifier.py")
    add_txt_classifier_debug()
    
    # 3. 验证配置
    print("\n3. 验证配置")
    verify_ai_configuration()
    
    print("\n" + "=" * 60)
    print("修复完成")
    print("=" * 60)
    
    print("\n下一步:")
    print("1. 运行小规模测试查看调试信息")
    print("2. 确认AI分类器是否被正确初始化和调用")
    print("3. 检查txt_content是否正确生成")
    print("4. 验证gpt-5-nano API是否正常响应")

if __name__ == "__main__":
    main()