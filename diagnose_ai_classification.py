#!/usr/bin/env python3
"""
诊断AI错误分类器未正常工作的问题
"""

import json
from pathlib import Path
from datetime import datetime

def analyze_ai_classification_issue():
    """分析为什么AI错误分类没有启用"""
    print("=" * 60)
    print("诊断AI错误分类器问题")
    print("=" * 60)
    
    # 1. 检查5.1的统计结果
    print("\n1. 检查5.1统计结果（从Parquet数据）")
    parquet_json = Path('pilot_bench_parquet_data/test_results.parquet.as.json')
    if parquet_json.exists():
        with open(parquet_json, 'r') as f:
            lines = f.readlines()[:20]  # 读取前20行样本
        
        # 分析错误统计字段
        print("\n分析错误分类字段状态：")
        error_fields = [
            'max_turns_errors',
            'tool_selection_errors', 
            'parameter_config_errors',
            'sequence_order_errors',
            'tool_call_format_errors',
            'timeout_errors',
            'dependency_errors',
            'other_errors'
        ]
        
        for line in lines[:5]:  # 分析前5条记录
            try:
                data = json.loads(line)
                print(f"\n模型: {data.get('model')}, 任务: {data.get('task_type')}")
                print("  错误统计:")
                all_zero = True
                for field in error_fields:
                    value = data.get(field, 0)
                    if value > 0:
                        all_zero = False
                        print(f"    ✅ {field}: {value}")
                    else:
                        print(f"    ❌ {field}: {value}")
                
                if all_zero:
                    print("  ⚠️ 所有错误分类字段都是0！AI分类器可能未工作")
                    
                # 检查失败率
                failure_rate = data.get('failure_rate', 0)
                if failure_rate > 0:
                    print(f"  失败率: {failure_rate:.1%} - 但没有错误分类!")
                    
            except json.JSONDecodeError:
                continue
    
    # 2. 检查batch_test_runner的配置
    print("\n\n2. 检查batch_test_runner.py配置")
    runner_file = Path('batch_test_runner.py')
    with open(runner_file, 'r') as f:
        content = f.read()
    
    # 检查关键配置点
    checks = {
        'use_ai_classification默认值': 'use_ai_classification: bool = True' in content,
        'TxtBasedAIClassifier导入': 'from txt_based_ai_classifier import TxtBasedAIClassifier' in content,
        'AI分类器初始化': 'self.ai_classifier = TxtBasedAIClassifier' in content,
        '分类结果使用': 'ai_error_category' in content,
        'EnhancedCumulativeManager传递参数': 'use_ai_classification=self.use_ai_classification' in content
    }
    
    for check, result in checks.items():
        status = "✅" if result else "❌"
        print(f"  {status} {check}")
    
    # 3. 检查txt_based_ai_classifier.py
    print("\n3. 检查txt_based_ai_classifier.py")
    classifier_file = Path('txt_based_ai_classifier.py')
    if classifier_file.exists():
        with open(classifier_file, 'r') as f:
            content = f.read()
        
        checks = {
            'gpt-5-nano模型配置': 'gpt-5-nano' in content,
            'API client初始化': 'get_client_for_model' in content,
            '快速规则检查': '_quick_rule_check_from_txt' in content,
            'AI分类实现': '_ai_classify_from_txt' in content,
            'Fallback分类': '_fallback_classify_from_txt' in content
        }
        
        for check, result in checks.items():
            status = "✅" if result else "❌"
            print(f"  {status} {check}")
    else:
        print("  ❌ txt_based_ai_classifier.py文件不存在!")
    
    # 4. 检查API配置
    print("\n4. 检查API配置")
    api_file = Path('api_client_manager.py')
    with open(api_file, 'r') as f:
        content = f.read()
    
    if 'gpt-5-nano' in content:
        print("  ✅ gpt-5-nano在支持的模型列表中")
        
        # 检查特殊处理
        if 'elif model_name == "gpt-5-nano"' in content:
            print("  ✅ gpt-5-nano有特殊endpoint配置")
        
        if 'client.is_gpt5_nano = True' in content:
            print("  ✅ gpt-5-nano标记已设置")
    else:
        print("  ❌ gpt-5-nano未在API配置中!")
    
    # 5. 分析可能的问题
    print("\n\n5. 问题诊断")
    print("-" * 40)
    
    problems = []
    
    # 问题1：AI分类器未被调用
    print("\n可能问题1：AI分类器未被正确调用")
    print("  原因：")
    print("  - use_ai_classification参数可能被设为False")
    print("  - ai_classifier对象可能为None")
    print("  - txt_content可能为空")
    
    # 问题2：分类结果未被保存
    print("\n可能问题2：分类结果未被正确保存")
    print("  原因：")
    print("  - AI分类结果未传递到record对象")
    print("  - EnhancedCumulativeManager未正确处理分类结果")
    print("  - 错误类型映射不正确")
    
    # 问题3：API调用失败
    print("\n可能问题3：gpt-5-nano API调用失败")
    print("  原因：")
    print("  - API key或endpoint配置错误")
    print("  - 网络问题或超时")
    print("  - Fallback分类器返回None")
    
    return problems

def create_fix_script():
    """创建修复脚本"""
    print("\n" + "=" * 60)
    print("创建修复脚本")
    print("=" * 60)
    
    fix_script = '''#!/usr/bin/env python3
"""
修复AI错误分类未启用的问题
"""

import shutil
from pathlib import Path
from datetime import datetime

def fix_ai_classification():
    """修复AI分类器配置"""
    print("修复AI错误分类器...")
    
    # 1. 确保batch_test_runner默认启用AI分类
    file_path = Path("batch_test_runner.py")
    backup_path = file_path.parent / f"{file_path.stem}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_path.suffix}"
    shutil.copy2(file_path, backup_path)
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    modified = False
    
    # 查找并修改默认参数
    for i, line in enumerate(lines):
        # 确保默认启用AI分类
        if "use_ai_classification: bool = False" in line:
            lines[i] = line.replace("False", "True")
            modified = True
            print(f"  ✅ 修改第{i+1}行：默认启用AI分类")
        
        # 确保AI分类器总是初始化
        if "if use_ai_classification:" in line and i > 100 and i < 120:
            # 改为总是初始化（移除条件）
            indent = len(line) - len(line.lstrip())
            lines[i] = " " * indent + "# 总是初始化AI分类器\\n"
            modified = True
            print(f"  ✅ 修改第{i+1}行：总是初始化AI分类器")
    
    if modified:
        with open(file_path, 'w') as f:
            f.writelines(lines)
        print("✅ batch_test_runner.py已修复")
    
    # 2. 添加调试日志
    print("\\n添加调试日志...")
    
    # 在_ai_classify_with_txt_content方法开头添加日志
    for i, line in enumerate(lines):
        if "def _ai_classify_with_txt_content" in line:
            # 找到方法体开始
            j = i + 2
            while j < len(lines) and not lines[j].strip().startswith('if'):
                j += 1
            
            if j < len(lines):
                # 在条件检查前添加调试日志
                indent = len(lines[j]) - len(lines[j].lstrip())
                debug_lines = [
                    f'{" " * indent}# 调试：AI分类器状态\\n',
                    f'{" " * indent}print(f"[AI_DEBUG] use_ai_classification={{self.use_ai_classification}}, ai_classifier={{self.ai_classifier is not None}}, txt_content_len={{len(txt_content) if txt_content else 0}}")\\n',
                    f'{" " * indent}\\n'
                ]
                lines = lines[:j] + debug_lines + lines[j:]
                modified = True
                print(f"  ✅ 在第{j}行添加调试日志")
            break
    
    if modified:
        with open(file_path, 'w') as f:
            f.writelines(lines)
    
    return modified

if __name__ == "__main__":
    fix_ai_classification()
'''
    
    fix_file = Path('fix_ai_classification.py')
    with open(fix_file, 'w') as f:
        f.write(fix_script)
    
    print(f"✅ 创建修复脚本: {fix_file}")
    return fix_file

def main():
    """主函数"""
    print("=" * 60)
    print("AI错误分类器诊断")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 诊断问题
    problems = analyze_ai_classification_issue()
    
    # 创建修复脚本
    fix_script = create_fix_script()
    
    # 总结
    print("\n" + "=" * 60)
    print("诊断总结")
    print("=" * 60)
    
    print("\n主要发现：")
    print("1. 5.1统计结果显示所有错误分类字段都是0")
    print("2. 说明AI分类器未被正确调用或结果未保存")
    print("3. 需要确保:")
    print("   - use_ai_classification默认为True")
    print("   - AI分类器总是初始化")
    print("   - 分类结果正确传递到数据库")
    
    print(f"\n下一步：")
    print(f"1. 运行修复脚本: python {fix_script}")
    print("2. 添加更多调试日志")
    print("3. 运行小测试验证AI分类")
    print("4. 检查gpt-5-nano API是否正常")

if __name__ == "__main__":
    main()