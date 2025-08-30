#!/usr/bin/env python3
"""
更新所有批测试脚本以支持存储后端管理器
"""

import os
from pathlib import Path
import re
from datetime import datetime

def backup_file(file_path: Path) -> Path:
    """备份文件"""
    if file_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = file_path.with_suffix(f'.backup_{timestamp}')
        with open(file_path, 'r') as src, open(backup_path, 'w') as dst:
            dst.write(src.read())
        print(f"  已备份: {backup_path.name}")
        return backup_path
    return None

def update_imports_for_storage_backend(file_path: Path) -> bool:
    """更新Python文件使用存储后端管理器"""
    
    if not file_path.exists():
        print(f"  ⚠️ 文件不存在: {file_path}")
        return False
    
    print(f"\n处理文件: {file_path.name}")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    modified = False
    
    # 1. 检查是否已经使用storage_backend_manager
    if 'storage_backend_manager' in content:
        print(f"  ⏭️  已使用存储后端管理器")
        return False
    
    # 2. 替换cumulative_test_manager导入
    if 'from cumulative_test_manager import' in content or 'import cumulative_test_manager' in content:
        # 备份原文件
        backup_file(file_path)
        
        # 查找所有的cumulative_test_manager导入
        patterns = [
            (r'from cumulative_test_manager import (\w+(?:, \w+)*)',
             r'from storage_backend_manager import \1'),
            (r'import cumulative_test_manager',
             r'import storage_backend_manager'),
            (r'cumulative_test_manager\.(\w+)',
             r'storage_backend_manager.\1'),
        ]
        
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content)
        
        # 特殊处理CumulativeTestManager类
        if 'CumulativeTestManager' in content:
            # 添加兼容性导入
            import_section = """# 使用统一的存储后端管理器
from storage_backend_manager import (
    add_test_result,
    check_progress,
    is_test_completed,
    finalize,
    get_model_stats,
    get_storage_backend
)

# 兼容性别名
class CumulativeTestManager:
    def __init__(self):
        self.backend = get_storage_backend()
    
    def add_test_result(self, **kwargs):
        return add_test_result(**kwargs)
    
    def check_progress(self, model, target_count=100):
        return check_progress(model, target_count)
    
    def is_test_completed(self, **kwargs):
        return is_test_completed(**kwargs)
    
    def finalize(self):
        return finalize()

"""
            # 替换原有的import部分
            content = re.sub(
                r'from cumulative_test_manager import.*?\n(?:.*?\n)*?(?=\n(?:from|import|\w|class|def|#))',
                import_section,
                content,
                count=1,
                flags=re.MULTILINE
            )
        
        modified = True
    
    # 3. 替换enhanced_cumulative_manager导入
    if 'from enhanced_cumulative_manager import' in content or 'import enhanced_cumulative_manager' in content:
        if not modified:
            backup_file(file_path)
        
        patterns = [
            (r'from enhanced_cumulative_manager import (\w+(?:, \w+)*)',
             r'from storage_backend_manager import \1'),
            (r'import enhanced_cumulative_manager',
             r'import storage_backend_manager'),
            (r'enhanced_cumulative_manager\.(\w+)',
             r'storage_backend_manager.\1'),
        ]
        
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content)
        
        modified = True
    
    # 4. 添加存储格式检测（如果使用了测试管理功能）
    if modified and 'def main(' in content:
        # 在main函数开始处添加存储格式显示
        storage_check = """
    # 显示当前存储格式
    storage_format = os.environ.get('STORAGE_FORMAT', 'json').upper()
    print(f"[INFO] 使用{storage_format}存储格式")
    
"""
        content = re.sub(
            r'(def main\([^)]*\):[^\n]*\n)(.*?)(?=\n    \w)',
            r'\1' + storage_check + r'\2',
            content,
            count=1,
            flags=re.MULTILINE | re.DOTALL
        )
    
    # 保存修改后的文件
    if modified:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"  ✅ 已更新为使用存储后端管理器")
        return True
    else:
        print(f"  ⏭️  无需更新")
        return False

def main():
    """主函数"""
    print("="*60)
    print("批测试脚本更新工具")
    print("更新为使用统一的存储后端管理器")
    print("="*60)
    
    # 需要更新的文件列表
    files_to_update = [
        "batch_test_runner.py",
        "smart_batch_runner.py",
        "ultra_parallel_runner.py",
        "enhanced_cumulative_manager.py",
        "auto_failure_maintenance_system.py",
        "view_test_progress.py",
    ]
    
    updated_count = 0
    
    for file_name in files_to_update:
        file_path = Path(file_name)
        if file_path.exists():
            if update_imports_for_storage_backend(file_path):
                updated_count += 1
        else:
            print(f"\n跳过不存在的文件: {file_name}")
    
    print("\n" + "="*60)
    print(f"更新完成: {updated_count}/{len(files_to_update)} 个文件")
    
    if updated_count > 0:
        print("\n下一步:")
        print("1. 设置存储格式环境变量:")
        print("   export STORAGE_FORMAT=parquet  # 使用Parquet")
        print("   export STORAGE_FORMAT=json     # 使用JSON（默认）")
        print("")
        print("2. 运行测试:")
        print("   ./run_systematic_test_final.sh")
        print("")
        print("3. 或者在运行时指定:")
        print("   STORAGE_FORMAT=parquet ./run_systematic_test_final.sh")

if __name__ == "__main__":
    print("⚠️ 此脚本将修改批测试脚本以使用统一的存储后端管理器")
    print("建议先停止所有正在运行的测试")
    
    response = input("\n是否继续？(y/n): ").strip().lower()
    if response == 'y':
        main()
    else:
        print("已取消")