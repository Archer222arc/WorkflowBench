#!/usr/bin/env python3
"""
切换到Parquet数据存储
这个脚本会更新所有批测试脚本使用新的Parquet管理器
"""

import os
import sys
from pathlib import Path
import shutil
from datetime import datetime

def backup_file(file_path: Path):
    """备份文件"""
    if file_path.exists():
        backup_path = file_path.with_suffix(f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        shutil.copy2(file_path, backup_path)
        print(f"  备份: {backup_path.name}")
        return backup_path
    return None

def update_import_statements(file_path: Path):
    """更新Python文件的import语句"""
    if not file_path.exists():
        print(f"  ⚠️ 文件不存在: {file_path}")
        return False
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # 替换import语句
    replacements = [
        # 替换累积管理器导入
        ('from cumulative_test_manager import', 
         'from parquet_cumulative_manager import'),
        
        ('import cumulative_test_manager',
         'import parquet_cumulative_manager as cumulative_test_manager'),
        
        # 替换增强管理器导入
        ('from enhanced_cumulative_manager import',
         'from parquet_cumulative_manager import'),
         
        ('import enhanced_cumulative_manager',
         'import parquet_cumulative_manager as enhanced_cumulative_manager'),
         
        # 替换CumulativeTestManager类
        ('CumulativeTestManager()',
         'ParquetCumulativeManager()'),
         
        ('EnhancedCumulativeManager()',
         'ParquetCumulativeManager()'),
    ]
    
    for old, new in replacements:
        content = content.replace(old, new)
    
    if content != original_content:
        # 备份原文件
        backup_file(file_path)
        
        # 写入更新后的内容
        with open(file_path, 'w') as f:
            f.write(content)
        
        print(f"  ✅ 已更新: {file_path.name}")
        return True
    else:
        print(f"  ⏭️  无需更新: {file_path.name}")
        return False

def create_compatibility_layer():
    """创建兼容层，使旧代码无需修改即可使用"""
    compat_file = Path("cumulative_test_manager_compat.py")
    
    content = '''#!/usr/bin/env python3
"""
兼容层：将旧的cumulative_test_manager调用重定向到Parquet版本
"""

# 重定向到Parquet版本
from parquet_cumulative_manager import *

# 提供向后兼容的类名
CumulativeTestManager = ParquetCumulativeManager
EnhancedCumulativeManager = ParquetCumulativeManager

# 标记正在使用Parquet存储
STORAGE_BACKEND = "parquet"

print("[INFO] 使用Parquet存储后端")
'''
    
    with open(compat_file, 'w') as f:
        f.write(content)
    
    print(f"✅ 创建兼容层: {compat_file}")

def main():
    """主函数"""
    print("="*60)
    print("切换到Parquet数据存储")
    print("="*60)
    
    # 需要更新的批测试脚本
    scripts_to_update = [
        "batch_test_runner.py",
        "smart_batch_runner.py",
        "ultra_parallel_runner.py",
        "cumulative_test_manager.py",
        "enhanced_cumulative_manager.py",
    ]
    
    print("\n1. 检查并更新批测试脚本...")
    updated_count = 0
    for script_name in scripts_to_update:
        script_path = Path(script_name)
        if script_path.exists():
            if update_import_statements(script_path):
                updated_count += 1
    
    print(f"\n  更新了 {updated_count} 个文件")
    
    # 创建兼容层
    print("\n2. 创建兼容层...")
    create_compatibility_layer()
    
    # 设置环境变量
    print("\n3. 设置环境变量...")
    env_file = Path(".env")
    env_content = "USE_PARQUET_STORAGE=1\n"
    
    if env_file.exists():
        with open(env_file, 'r') as f:
            existing = f.read()
        if "USE_PARQUET_STORAGE" not in existing:
            with open(env_file, 'a') as f:
                f.write(f"\n{env_content}")
    else:
        with open(env_file, 'w') as f:
            f.write(env_content)
    
    print("  ✅ 环境变量已设置")
    
    # 检查数据迁移状态
    print("\n4. 检查数据迁移状态...")
    parquet_dir = Path("pilot_bench_parquet_data")
    if parquet_dir.exists() and any(parquet_dir.glob("*.parquet")):
        print("  ✅ Parquet数据已存在")
    else:
        print("  ⚠️ 需要运行数据迁移")
        print("  运行: python migrate_to_parquet.py")
    
    print("\n" + "="*60)
    print("✅ 切换完成！")
    print("\n下一步:")
    print("1. 如果还没有迁移数据，运行: python migrate_to_parquet.py")
    print("2. 测试新系统: python parquet_cumulative_manager.py")
    print("3. 开始使用: 所有批测试脚本现在将使用Parquet存储")
    
    print("\n回滚方法:")
    print("1. 恢复备份文件: *.backup_*")
    print("2. 删除.env中的USE_PARQUET_STORAGE=1")
    print("3. 删除cumulative_test_manager_compat.py")

if __name__ == "__main__":
    # 确认操作
    print("⚠️ 警告：此操作将修改批测试脚本以使用Parquet存储")
    print("建议先停止所有正在运行的测试进程")
    
    response = input("\n是否继续？(y/n): ").strip().lower()
    if response == 'y':
        main()
    else:
        print("已取消")