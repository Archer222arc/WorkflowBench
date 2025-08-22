#!/usr/bin/env python3
"""
更新所有runner以支持存储格式选择
"""

import os
import re
from pathlib import Path
from datetime import datetime

def backup_file(file_path: Path) -> Path:
    """备份文件"""
    if file_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = file_path.with_suffix(f'.backup_{timestamp}')
        with open(file_path, 'r') as src:
            content = src.read()
        with open(backup_path, 'w') as dst:
            dst.write(content)
        print(f"  备份: {backup_path.name}")
        return backup_path
    return None

def update_runner_imports(file_path: Path) -> bool:
    """更新runner文件的导入语句"""
    
    if not file_path.exists():
        print(f"  ⚠️ 文件不存在: {file_path}")
        return False
    
    print(f"\n处理: {file_path.name}")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    modified = False
    
    # 检查是否已经修改过
    if 'storage_backend_manager' in content or 'STORAGE_FORMAT' in content:
        print("  ⏭️  已经支持存储格式选择")
        return False
    
    # 备份文件
    backup_file(file_path)
    
    # 1. 替换cumulative_test_manager导入
    replacements = []
    
    # 处理简单导入
    if 'from cumulative_test_manager import TestRecord' in content:
        replacements.append((
            'from cumulative_test_manager import TestRecord',
            '''# 支持存储格式选择
import os
storage_format = os.environ.get('STORAGE_FORMAT', 'json').lower()
if storage_format == 'parquet':
    try:
        from parquet_cumulative_manager import TestRecord
        print(f"[INFO] 使用Parquet存储格式")
    except ImportError:
        from cumulative_test_manager import TestRecord
        print(f"[INFO] Parquet不可用，使用JSON存储格式")
else:
    from cumulative_test_manager import TestRecord
    print(f"[INFO] 使用JSON存储格式")'''
        ))
    
    # 处理复杂导入（包含CumulativeTestManager）
    if 'from cumulative_test_manager import CumulativeTestManager' in content:
        replacements.append((
            re.compile(r'from cumulative_test_manager import ([^;\n]+)'),
            '''# 支持存储格式选择
import os
storage_format = os.environ.get('STORAGE_FORMAT', 'json').lower()
if storage_format == 'parquet':
    try:
        from parquet_cumulative_manager import (
            ParquetCumulativeManager as CumulativeTestManager,
            TestRecord,
            add_test_result,
            check_progress,
            is_test_completed,
            finalize
        )
        print(f"[INFO] 使用Parquet存储格式")
    except ImportError:
        from cumulative_test_manager import \\1
        print(f"[INFO] Parquet不可用，使用JSON存储格式")
else:
    from cumulative_test_manager import \\1
    print(f"[INFO] 使用JSON存储格式")'''
        ))
    
    # 处理enhanced_cumulative_manager导入
    if 'from enhanced_cumulative_manager import' in content:
        replacements.append((
            re.compile(r'from enhanced_cumulative_manager import ([^;\n]+)'),
            '''# 支持存储格式选择
import os
storage_format = os.environ.get('STORAGE_FORMAT', 'json').lower()
if storage_format == 'parquet':
    try:
        from parquet_cumulative_manager import \\1
        print(f"[INFO] 使用Parquet存储格式")
    except ImportError:
        from enhanced_cumulative_manager import \\1
        print(f"[INFO] Parquet不可用，使用JSON存储格式")
else:
    from enhanced_cumulative_manager import \\1
    print(f"[INFO] 使用JSON存储格式")'''
        ))
    
    # 应用替换
    for old, new in replacements:
        if isinstance(old, str):
            if old in content:
                content = content.replace(old, new)
                modified = True
        else:  # regex
            if old.search(content):
                content = old.sub(new, content)
                modified = True
    
    # 2. 在main函数开始处添加存储格式显示（如果有main函数）
    if modified and 'def main(' in content:
        # 查找main函数
        main_match = re.search(r'(def main\([^)]*\):[^\n]*\n)', content)
        if main_match:
            # 在main函数后添加存储格式显示
            insert_pos = main_match.end()
            # 获取缩进
            next_line_match = re.search(r'\n(\s+)', content[insert_pos:])
            indent = next_line_match.group(1) if next_line_match else '    '
            
            storage_info = f'''{indent}# 显示当前存储格式
{indent}storage_format = os.environ.get('STORAGE_FORMAT', 'json').upper()
{indent}print(f"[INFO] 使用{{storage_format}}存储格式")
{indent}
'''
            content = content[:insert_pos] + storage_info + content[insert_pos:]
    
    # 保存修改后的文件
    if modified:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"  ✅ 已更新支持存储格式选择")
        return True
    else:
        print(f"  ⏭️  无需更新")
        return False

def main():
    """主函数"""
    print("="*60)
    print("批量更新Runner脚本")
    print("添加存储格式选择支持")
    print("="*60)
    
    # 需要更新的文件
    runners_to_update = [
        "batch_test_runner.py",
        "smart_batch_runner.py",
        "ultra_parallel_runner.py",
        "provider_parallel_runner.py",
        "auto_failure_maintenance_system.py",
        "view_test_progress.py",
        "enhanced_cumulative_manager.py"
    ]
    
    updated_count = 0
    
    for runner_file in runners_to_update:
        file_path = Path(runner_file)
        if file_path.exists():
            if update_runner_imports(file_path):
                updated_count += 1
        else:
            print(f"\n跳过: {runner_file} (文件不存在)")
    
    print("\n" + "="*60)
    print(f"更新完成: {updated_count}/{len(runners_to_update)} 个文件")
    
    if updated_count > 0:
        print("\n使用方法:")
        print("1. 设置存储格式:")
        print("   export STORAGE_FORMAT=parquet  # 使用Parquet（推荐）")
        print("   export STORAGE_FORMAT=json     # 使用JSON（默认）")
        print("")
        print("2. 运行测试:")
        print("   python smart_batch_runner.py --model gpt-4o-mini")
        print("")
        print("3. 或在运行时指定:")
        print("   STORAGE_FORMAT=parquet python batch_test_runner.py")

if __name__ == "__main__":
    print("⚠️ 此脚本将更新所有runner以支持存储格式选择")
    print("建议先停止所有正在运行的测试")
    
    response = input("\n是否继续？(y/n): ").strip().lower()
    if response == 'y':
        main()
    else:
        print("已取消")