#!/usr/bin/env python3
"""
清理和归档调试文件
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

def main():
    """主函数"""
    
    # 创建归档目录
    archive_dir = Path("archived_tests")
    archive_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    debug_archive = archive_dir / f"debug_scripts_{timestamp}"
    debug_archive.mkdir(exist_ok=True)
    
    # 定义要归档的调试文件
    debug_files = [
        # 调试脚本
        "debug_parquet_storage.py",
        "debug_summary_update.py", 
        "debug_test_with_monitoring.py",
        "deep_analysis.py",
        
        # 修复脚本
        "fix_batch_commit_issues.py",
        "fix_concurrent_initialization.py",
        "fix_data_save_bug.py",
        "fix_data_save_issue.py",
        
        # 测试脚本
        "test_batch_runner_fix.py",
        "test_parallel_deployment.py",
        "test_parquet_fix.py",
        "test_simple_batch.py",
        "test_small_batch.py",
        "test_workflow_generation.py",
        "simple_test_verify.py",
        
        # 验证脚本
        "validate_5_phases.py",
        "quick_save_test.py",
        
        # 验证报告
        "validation_report_*.json",
    ]
    
    # 要保留的工具脚本（有长期价值）
    keep_tools = [
        "update_summary_totals.py",  # 有用的工具，保留
    ]
    
    # 要删除的临时文件
    temp_patterns = [
        "*.backup_*",
        "test_*.log",
        "debug_*.log",
        "temp_*.py",
        "fix_*.py.bak",
    ]
    
    print("=" * 60)
    print("清理调试文件")
    print("=" * 60)
    
    # 1. 归档调试脚本
    print("\n📁 归档调试脚本...")
    archived_count = 0
    for pattern in debug_files:
        for file in Path(".").glob(pattern):
            if file.exists() and file.name not in keep_tools:
                target = debug_archive / file.name
                shutil.move(str(file), str(target))
                print(f"  ✅ 归档: {file.name}")
                archived_count += 1
    
    print(f"\n归档了 {archived_count} 个文件到 {debug_archive}")
    
    # 2. 删除临时文件
    print("\n🗑️ 删除临时文件...")
    deleted_count = 0
    for pattern in temp_patterns:
        for file in Path(".").glob(pattern):
            if file.exists():
                file.unlink()
                print(f"  ✅ 删除: {file.name}")
                deleted_count += 1
    
    print(f"\n删除了 {deleted_count} 个临时文件")
    
    # 3. 整理测试结果备份
    print("\n📦 整理测试结果备份...")
    backup_dir = Path("pilot_bench_cumulative_results")
    if backup_dir.exists():
        backup_files = list(backup_dir.glob("*.backup_*.json"))
        if backup_files:
            backups_archive = archive_dir / f"db_backups_{timestamp}"
            backups_archive.mkdir(exist_ok=True)
            
            for backup in backup_files:
                target = backups_archive / backup.name
                shutil.move(str(backup), str(target))
                print(f"  ✅ 归档备份: {backup.name}")
            
            print(f"\n归档了 {len(backup_files)} 个数据库备份")
    
    # 4. 创建清理报告
    report_path = archive_dir / f"cleanup_report_{timestamp}.txt"
    with open(report_path, 'w') as f:
        f.write(f"清理报告\n")
        f.write(f"时间: {datetime.now()}\n")
        f.write(f"归档脚本: {archived_count}\n")
        f.write(f"删除临时文件: {deleted_count}\n")
        f.write(f"归档目录: {debug_archive}\n")
    
    print("\n" + "=" * 60)
    print("清理完成！")
    print("=" * 60)
    
    print(f"\n📊 总结:")
    print(f"  归档脚本: {archived_count}")
    print(f"  删除临时文件: {deleted_count}")
    print(f"  保留工具: {len(keep_tools)}")
    print(f"\n报告已保存到: {report_path}")
    
    # 5. 显示保留的重要文件
    print("\n📌 保留的重要文件:")
    for tool in keep_tools:
        if Path(tool).exists():
            print(f"  ✅ {tool}")
    
    important_files = [
        "smart_batch_runner.py",
        "batch_test_runner.py",
        "enhanced_cumulative_manager.py",
        "run_systematic_test_final.sh",
        "FIX_SUMMARY_REPORT.md",
        "debug_to_do.txt",
    ]
    
    for file in important_files:
        if Path(file).exists():
            print(f"  ✅ {file}")
    
    return 0

if __name__ == "__main__":
    exit(main())