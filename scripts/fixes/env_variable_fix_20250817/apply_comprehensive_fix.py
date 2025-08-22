#!/usr/bin/env python3
"""
全面修复run_systematic_test_final.sh中的环境变量传递问题
根据用户要求："不光是5.3,每个部分都要仔细检查分析修改一遍"
"""

import re
import shutil
from datetime import datetime
from pathlib import Path

def backup_file(filepath):
    """备份原文件"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{filepath}.backup_{timestamp}"
    shutil.copy2(filepath, backup_path)
    print(f"✅ 备份已创建: {backup_path}")
    return backup_path

def fix_background_processes(content):
    """修复所有后台进程的环境变量传递问题"""
    
    fixes_applied = []
    
    # 定义需要修复的模式和对应的测试阶段
    patterns = [
        # 5.1 基准测试 - 修复所有后台运行的模型测试
        {
            'stage': '5.1 基准测试',
            'pattern': r'(\s+)\(\s*\n(\s+echo -e.*?(?:开始基准测试|baseline测试).*?\n)',
            'insert_after_open_paren': True
        },
        
        # 5.2 Qwen规模效应测试 - very_easy测试
        {
            'stage': '5.2 Qwen very_easy测试',
            'pattern': r'(\s+)\(\s*\n(\s+echo.*?very_easy.*?\n)',
            'insert_after_open_paren': True
        },
        
        # 5.2 Qwen规模效应测试 - medium测试
        {
            'stage': '5.2 Qwen medium测试',
            'pattern': r'(\s+)\(\s*\n(\s+echo.*?medium.*?\n)',
            'insert_after_open_paren': True
        },
        
        # 5.3 缺陷工作流测试
        {
            'stage': '5.3 缺陷工作流测试',
            'pattern': r'(\s+)\(\s*\n(\s+echo -e.*?开始缺陷工作流测试.*?\n)',
            'insert_after_open_paren': True
        },
        
        # 5.4 工具可靠性测试
        {
            'stage': '5.4 工具可靠性测试',
            'pattern': r'(\s+)\(\s*\n(\s+echo -e.*?开始工具可靠性测试.*?\n)',
            'insert_after_open_paren': True
        },
        
        # 5.5 提示敏感性测试
        {
            'stage': '5.5 提示敏感性测试',
            'pattern': r'(\s+)\(\s*\n(\s+echo -e.*?开始提示敏感性测试.*?\n)',
            'insert_after_open_paren': True
        }
    ]
    
    for pattern_info in patterns:
        pattern = pattern_info['pattern']
        stage = pattern_info['stage']
        
        # 查找所有匹配项
        matches = list(re.finditer(pattern, content, re.MULTILINE))
        
        if matches:
            print(f"  找到 {len(matches)} 处 {stage} 需要修复")
            
            # 从后往前替换，避免偏移问题
            for match in reversed(matches):
                indent = match.group(1)
                echo_line = match.group(2)
                
                # 检查是否已经有环境变量导出
                check_start = match.end()
                check_end = min(check_start + 500, len(content))
                check_text = content[check_start:check_end]
                
                if "export STORAGE_FORMAT" not in check_text:
                    # 构建环境变量导出代码
                    env_exports = f'''{indent}    # 确保环境变量在子进程中可用
{indent}    export STORAGE_FORMAT="${{STORAGE_FORMAT}}"
{indent}    export MODEL_TYPE="${{MODEL_TYPE}}"
{indent}    export NUM_INSTANCES="${{NUM_INSTANCES}}"
{indent}    export RATE_MODE="${{RATE_MODE}}"
{indent}    
'''
                    # 插入到(后面
                    insert_pos = match.end()
                    content = content[:insert_pos] + env_exports + echo_line + content[insert_pos + len(echo_line):]
                    fixes_applied.append(f"{stage} (行 ~{content[:match.start()].count(chr(10))})")
    
    return content, fixes_applied

def fix_run_smart_test_function(content):
    """修复run_smart_test函数本身"""
    
    # 查找run_smart_test函数定义
    func_pattern = r'(run_smart_test\(\) \{[^\n]*\n)([\s\S]*?)(    local model="\$1")'
    match = re.search(func_pattern, content)
    
    if match:
        func_start = match.group(1)
        between = match.group(2)
        local_line = match.group(3)
        
        # 检查是否已经有环境变量导出
        if "export STORAGE_FORMAT" not in between:
            # 在local声明后添加环境变量导出
            env_exports = '''
    
    # 确保环境变量在函数内可用
    export STORAGE_FORMAT="${STORAGE_FORMAT}"
    export MODEL_TYPE="${MODEL_TYPE}"
    export NUM_INSTANCES="${NUM_INSTANCES}"
    export RATE_MODE="${RATE_MODE}"'''
            
            # 重建函数开头
            new_content = content[:match.start()] + func_start + between + local_line + env_exports + content[match.end():]
            
            print("  ✅ 修复run_smart_test函数")
            return new_content, True
    
    return content, False

def main():
    """主函数"""
    print("=" * 60)
    print("全面修复环境变量传递问题")
    print("=" * 60)
    
    # 文件路径
    script_path = Path("run_systematic_test_final.sh")
    
    if not script_path.exists():
        print(f"❌ 文件不存在: {script_path}")
        return
    
    # 备份原文件
    backup_path = backup_file(script_path)
    
    # 读取文件内容
    with open(script_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("\n开始修复...")
    
    # 1. 修复后台进程
    print("\n1. 修复后台进程环境变量传递:")
    content, bg_fixes = fix_background_processes(content)
    if bg_fixes:
        for fix in bg_fixes:
            print(f"  - {fix}")
    else:
        print("  未找到需要修复的后台进程")
    
    # 2. 修复run_smart_test函数
    print("\n2. 修复run_smart_test函数:")
    content, func_fixed = fix_run_smart_test_function(content)
    if not func_fixed:
        print("  函数已经包含环境变量导出或未找到函数")
    
    # 保存修复后的文件
    fixed_path = Path("run_systematic_test_final_fixed.sh")
    with open(fixed_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n✅ 修复后的文件已保存到: {fixed_path}")
    
    # 统计修复数量
    export_count = content.count("确保环境变量在子进程中可用") + content.count("确保环境变量在函数内可用")
    print(f"\n📊 统计:")
    print(f"  - 共添加 {export_count} 处环境变量导出")
    print(f"  - 修复 {len(bg_fixes)} 处后台进程")
    print(f"  - 修复 {'1' if func_fixed else '0'} 个函数")
    
    print("\n" + "=" * 60)
    print("修复完成！")
    print("=" * 60)
    print("\n下一步操作:")
    print("1. 检查修复: diff run_systematic_test_final.sh run_systematic_test_final_fixed.sh | head -50")
    print("2. 应用修复: mv run_systematic_test_final_fixed.sh run_systematic_test_final.sh")
    print("3. 测试修复: ./test_full_fix.sh")
    print("\n建议:")
    print("- 先用少量实例测试验证修复效果")
    print("- 监控数据文件更新情况")
    print("- 查看日志确认环境变量传递正确")

if __name__ == "__main__":
    main()