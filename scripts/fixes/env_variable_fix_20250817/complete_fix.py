#!/usr/bin/env python3
"""
完整修复run_systematic_test_final.sh中所有环境变量传递问题
确保所有6个后台进程位置都正确导出环境变量
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

def fix_all_background_processes(content):
    """修复所有后台进程的环境变量传递"""
    
    # 找到所有后台进程模式: 独立的 ( 后跟 ) &
    # 这个模式匹配: 缩进 + ( + 换行 + 内容 + ) &
    pattern = r'(\n[\t ]+)\(\s*\n([\s\S]*?)\n[\t ]+\) &'
    
    fixes_count = 0
    positions = []
    
    # 找到所有匹配
    for match in re.finditer(pattern, content):
        indent = match.group(1).lstrip('\n')
        inner_content = match.group(2)
        
        # 检查是否已经有环境变量导出
        if "export STORAGE_FORMAT" not in inner_content:
            # 需要添加环境变量导出
            fixes_count += 1
            start_line = content[:match.start()].count('\n')
            positions.append(start_line)
    
    # 从后往前替换，避免位置偏移
    if fixes_count > 0:
        # 重新查找并替换
        def replace_func(match):
            indent = match.group(1).lstrip('\n')
            inner_content = match.group(2)
            
            # 检查是否已经有环境变量导出
            if "export STORAGE_FORMAT" not in inner_content:
                # 在第一行内容前添加环境变量导出
                lines = inner_content.split('\n')
                first_line = lines[0] if lines else ""
                
                env_exports = f'''{indent}    # 确保环境变量在子进程中可用
{indent}    export STORAGE_FORMAT="${{STORAGE_FORMAT}}"
{indent}    export MODEL_TYPE="${{MODEL_TYPE}}"
{indent}    export NUM_INSTANCES="${{NUM_INSTANCES}}"
{indent}    export RATE_MODE="${{RATE_MODE}}"
{indent}    '''
                
                # 重建内容
                new_inner = env_exports + '\n' + inner_content
                return f"{match.group(1)}(\n{new_inner}\n{indent}) &"
            else:
                return match.group(0)
        
        content = re.sub(pattern, replace_func, content)
    
    return content, fixes_count, positions

def fix_run_smart_test_function(content):
    """修复run_smart_test函数"""
    
    # 查找函数并在适当位置添加环境变量导出
    pattern = r'(run_smart_test\(\) \{[^\n]*\n[\s\S]*?local model="\$1"[^\n]*\n)'
    
    match = re.search(pattern, content)
    if match:
        func_part = match.group(1)
        
        # 检查是否已经有环境变量导出
        if "export STORAGE_FORMAT" not in content[match.start():match.end() + 500]:
            # 在local声明后添加
            env_exports = '''
    
    # 确保环境变量在函数内可用
    export STORAGE_FORMAT="${STORAGE_FORMAT}"
    export MODEL_TYPE="${MODEL_TYPE}"
    export NUM_INSTANCES="${NUM_INSTANCES}"
    export RATE_MODE="${RATE_MODE}"'''
            
            # 插入到函数开头的local声明后
            insert_pos = match.end()
            content = content[:insert_pos] + env_exports + content[insert_pos:]
            return content, True
    
    return content, False

def verify_fixes(filepath):
    """验证修复是否成功"""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # 统计后台进程
    bg_processes = len(re.findall(r'\n[\t ]+\(\s*\n', content))
    
    # 统计环境变量导出
    exports = len(re.findall(r'export STORAGE_FORMAT="\$\{STORAGE_FORMAT\}"', content))
    
    # 找到具体位置
    positions = []
    for match in re.finditer(r'export STORAGE_FORMAT="\$\{STORAGE_FORMAT\}"', content):
        line_num = content[:match.start()].count('\n') + 1
        positions.append(line_num)
    
    return bg_processes, exports, positions

def main():
    """主函数"""
    print("=" * 60)
    print("完整修复环境变量传递问题")
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
    
    # 1. 修复所有后台进程
    print("\n1. 修复后台进程环境变量传递:")
    content, bg_fixes, bg_positions = fix_all_background_processes(content)
    if bg_fixes > 0:
        print(f"  ✅ 修复了 {bg_fixes} 处后台进程")
        print(f"  位置（行号）: {bg_positions[:10]}")  # 只显示前10个
    else:
        print("  所有后台进程已包含环境变量导出")
    
    # 2. 修复run_smart_test函数
    print("\n2. 修复run_smart_test函数:")
    content, func_fixed = fix_run_smart_test_function(content)
    if func_fixed:
        print("  ✅ 已添加环境变量导出")
    else:
        print("  函数已包含环境变量导出")
    
    # 保存修复后的文件
    fixed_path = Path("run_systematic_test_final_fixed.sh")
    with open(fixed_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n✅ 修复后的文件已保存到: {fixed_path}")
    
    # 验证修复
    print("\n3. 验证修复结果:")
    bg_count, export_count, export_positions = verify_fixes(fixed_path)
    print(f"  - 文件中共有 {bg_count} 个后台进程")
    print(f"  - 共有 {export_count} 处环境变量导出")
    print(f"  - 导出位置（行号）: {export_positions[:10]}")  # 只显示前10个
    
    # 显示每个测试阶段的修复
    stages = {
        3237: "5.1 基准测试",
        3353: "5.2 Qwen very_easy测试",
        3385: "5.2 Qwen medium测试",
        3539: "5.3 缺陷工作流测试",
        3718: "5.4 工具可靠性测试",
        3925: "5.5 提示敏感性测试"
    }
    
    print("\n4. 各测试阶段修复情况:")
    for line, stage in stages.items():
        # 检查该位置附近是否有环境变量导出
        found = any(abs(pos - line) < 10 for pos in export_positions)
        status = "✅" if found else "❌"
        print(f"  {status} {stage} (行 ~{line})")
    
    print("\n" + "=" * 60)
    print("修复完成！")
    print("=" * 60)
    print("\n下一步操作:")
    print("1. 检查修复: diff -u run_systematic_test_final.sh run_systematic_test_final_fixed.sh | head -100")
    print("2. 应用修复: cp run_systematic_test_final_fixed.sh run_systematic_test_final.sh")
    print("3. 测试修复: ./test_full_fix.sh")
    print("\n重要提示:")
    print("- 确保STORAGE_FORMAT环境变量已设置")
    print("- 使用小实例数先测试一个模型")
    print("- 监控数据文件更新: ls -la pilot_bench_*_data/")

if __name__ == "__main__":
    main()