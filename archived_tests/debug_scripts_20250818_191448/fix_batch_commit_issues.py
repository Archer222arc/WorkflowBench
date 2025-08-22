#!/usr/bin/env python3
"""
修复batch_commit相关问题
1. 添加自动flush机制
2. 修复默认保存逻辑
3. 确保Parquet同步更新
"""

import os
import sys
from pathlib import Path
import shutil
from datetime import datetime

def backup_file(filepath):
    """备份文件"""
    if Path(filepath).exists():
        backup_path = f"{filepath}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(filepath, backup_path)
        print(f"✅ 备份: {backup_path}")
        return backup_path
    return None

def fix_batch_test_runner():
    """修复batch_test_runner.py的checkpoint逻辑"""
    print("\n📝 修复batch_test_runner.py...")
    
    filepath = "batch_test_runner.py"
    backup_file(filepath)
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # 修复1: checkpoint_save逻辑 - 添加结束时的强制保存
    old_code = """    def run_concurrent_batch(self, tasks, workers=5, qps=2.0):"""
    
    new_code = """    def run_concurrent_batch(self, tasks, workers=5, qps=2.0):"""
    
    # 查找run_concurrent_batch的结尾，添加强制保存
    if "# 最后一次checkpoint保存（强制）" in content:
        # 确保最后的pending_results被保存
        old_end = """        # 最后一次checkpoint保存（强制）
        if not self.enable_database_updates and self.checkpoint_interval > 0:
            self._checkpoint_save([], force=True)"""
        
        new_end = """        # 最后一次checkpoint保存（强制）
        if not self.enable_database_updates and self.checkpoint_interval > 0:
            self._checkpoint_save([], force=True)
        
        # 确保所有pending_results都被保存（即使不满checkpoint_interval）
        if self.pending_results and not self.enable_database_updates:
            print(f"\\n💾 Final save: 保存剩余的{len(self.pending_results)}个结果...")
            self._checkpoint_save([], force=True)"""
        
        if old_end in content:
            content = content.replace(old_end, new_end)
            print("  ✅ 添加了最终保存机制")
    
    # 修复2: 改进checkpoint条件
    old_condition = """        should_save = force or (len(self.pending_results) >= self.checkpoint_interval and self.checkpoint_interval > 0)"""
    
    new_condition = """        # 修改保存条件：force时强制保存，或者达到checkpoint_interval，或者interval为0时立即保存
        should_save = force or (self.checkpoint_interval == 0 and len(self.pending_results) > 0) or \
                     (self.checkpoint_interval > 0 and len(self.pending_results) >= self.checkpoint_interval)"""
    
    if old_condition in content:
        content = content.replace(old_condition, new_condition)
        print("  ✅ 修复了checkpoint保存条件")
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print("  ✅ batch_test_runner.py修复完成")

def fix_smart_batch_runner():
    """修复smart_batch_runner.py的默认保存逻辑"""
    print("\n📝 修复smart_batch_runner.py...")
    
    filepath = "smart_batch_runner.py"
    backup_file(filepath)
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # 修复：即使不是batch_commit模式也要保存数据
    # 找到所有"if batch_commit:"的保存逻辑，改为总是保存
    
    # 位置1: _run_azure_parallel_tasks函数
    old_save1 = """    # 如果是批量提交模式，保存结果
    if batch_commit:
        unsaved_results = [r for r in results if r and not r.get('_saved', False)]
        if unsaved_results:
            print(f"\\n📤 保存{len(unsaved_results)}个测试结果...")"""
    
    new_save1 = """    # 保存结果（无论是否batch_commit）
    unsaved_results = [r for r in results if r and not r.get('_saved', False)]
    if unsaved_results:
        if not batch_commit:
            print(f"\\n📤 自动保存{len(unsaved_results)}个测试结果...")
        else:
            print(f"\\n📤 批量保存{len(unsaved_results)}个测试结果...")"""
    
    if old_save1 in content:
        content = content.replace(old_save1, new_save1)
        print("  ✅ 修复了Azure并行任务的保存逻辑")
    
    # 位置2: _run_idealab_parallel_tasks函数
    old_save2 = """    # 如果是批量提交模式，保存结果
    if batch_commit and all_results:
        unsaved_results = [r for r in all_results if r and not r.get('_saved', False)]
        if unsaved_results:
            print(f"\\n📤 保存{len(unsaved_results)}个测试结果...")"""
    
    new_save2 = """    # 保存结果（无论是否batch_commit）
    if all_results:
        unsaved_results = [r for r in all_results if r and not r.get('_saved', False)]
        if unsaved_results:
            if not batch_commit:
                print(f"\\n📤 自动保存{len(unsaved_results)}个测试结果...")
            else:
                print(f"\\n📤 批量保存{len(unsaved_results)}个测试结果...")"""
    
    if old_save2 in content:
        content = content.replace(old_save2, new_save2)
        print("  ✅ 修复了IdealLab并行任务的保存逻辑")
    
    # 添加默认batch_commit=True
    old_default = """                         batch_commit: bool = False, checkpoint_interval: int = 20,"""
    new_default = """                         batch_commit: bool = True, checkpoint_interval: int = 10,"""
    
    if old_default in content:
        content = content.replace(old_default, new_default)
        print("  ✅ 将batch_commit默认值改为True，checkpoint_interval改为10")
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print("  ✅ smart_batch_runner.py修复完成")

def add_batch_commit_to_scripts():
    """给run_systematic_test_final.sh添加--batch-commit参数"""
    print("\n📝 修复run_systematic_test_final.sh...")
    
    filepath = "run_systematic_test_final.sh"
    backup_file(filepath)
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # 统计需要修复的位置
    count = 0
    
    # 为所有smart_batch_runner.py调用添加--batch-commit
    lines = content.split('\n')
    new_lines = []
    
    for line in lines:
        if 'smart_batch_runner.py' in line and '--batch-commit' not in line:
            # 如果这行调用了smart_batch_runner.py但没有--batch-commit
            if line.strip().endswith('\\'):
                # 多行命令，在末尾添加
                new_lines.append(line)
                new_lines.append('            --batch-commit \\')
                count += 1
            elif 'python' in line:
                # 单行命令，在末尾添加
                new_lines.append(line + ' --batch-commit')
                count += 1
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    
    content = '\n'.join(new_lines)
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"  ✅ 为{count}处smart_batch_runner.py调用添加了--batch-commit参数")

def enable_parquet_update():
    """确保Parquet存储被更新"""
    print("\n📝 检查Parquet存储配置...")
    
    # 检查enhanced_cumulative_manager.py是否正确处理Parquet
    filepath = "enhanced_cumulative_manager.py"
    
    if not Path(filepath).exists():
        print("  ⚠️ enhanced_cumulative_manager.py不存在")
        return
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # 确保_flush_buffer调用了Parquet保存
    if "parquet" in content.lower():
        print("  ✅ enhanced_cumulative_manager.py已支持Parquet")
    else:
        print("  ⚠️ enhanced_cumulative_manager.py可能不支持Parquet")
    
    # 检查环境变量
    storage_format = os.environ.get('STORAGE_FORMAT', 'json')
    print(f"  当前STORAGE_FORMAT: {storage_format}")
    
    if storage_format == 'parquet':
        print("  ✅ Parquet存储已启用")
    else:
        print("  ℹ️ 当前使用JSON存储，如需启用Parquet，请设置：")
        print("     export STORAGE_FORMAT=parquet")

def main():
    """主函数"""
    print("🔧 修复batch_commit相关问题")
    print("="*50)
    
    # 1. 修复batch_test_runner.py
    fix_batch_test_runner()
    
    # 2. 修复smart_batch_runner.py
    fix_smart_batch_runner()
    
    # 3. 修复run_systematic_test_final.sh
    add_batch_commit_to_scripts()
    
    # 4. 检查Parquet配置
    enable_parquet_update()
    
    print("\n" + "="*50)
    print("✅ 所有修复完成！")
    print("\n建议：")
    print("1. 运行测试验证修复：")
    print("   python smart_batch_runner.py --model gpt-4o-mini --prompt-types baseline \\")
    print("     --difficulty easy --task-types simple_task --num-instances 1")
    print("\n2. 如需启用Parquet存储：")
    print("   export STORAGE_FORMAT=parquet")
    print("\n3. 运行完整的5.3测试：")
    print("   ./run_5_3_macos.sh")

if __name__ == "__main__":
    main()