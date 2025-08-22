#!/usr/bin/env python3
"""
修复数据无法保存的问题
根本原因：
1. batch_commit模式下enable_database_updates被设置为False
2. 数据只在checkpoint时保存，如果进程被杀死就会丢失
"""

import sys
from pathlib import Path
import shutil
from datetime import datetime

def backup_file(filepath):
    """备份文件"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{filepath}.backup_{timestamp}"
    shutil.copy2(filepath, backup_path)
    print(f"✅ 备份已创建: {backup_path}")
    return backup_path

def fix_smart_batch_runner():
    """修复smart_batch_runner.py"""
    print("\n修复smart_batch_runner.py...")
    
    filepath = Path("smart_batch_runner.py")
    if not filepath.exists():
        print("❌ 文件不存在: smart_batch_runner.py")
        return False
    
    backup_file(filepath)
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # 修复1：即使batch_commit也要启用数据库更新
    old_line = "enable_database_updates=not batch_commit,"
    new_line = "enable_database_updates=True,  # 总是启用数据库更新以防数据丢失"
    
    if old_line in content:
        content = content.replace(old_line, new_line)
        print("  ✅ 修复enable_database_updates设置")
    else:
        print("  ⚠️ 未找到enable_database_updates设置")
    
    # 修复2：降低checkpoint间隔，更频繁地保存
    old_checkpoint = "checkpoint_interval=checkpoint_interval if batch_commit else 0"
    new_checkpoint = "checkpoint_interval=5 if batch_commit else 0  # 降低间隔以防数据丢失"
    
    if old_checkpoint in content:
        content = content.replace(old_checkpoint, new_checkpoint)
        print("  ✅ 修复checkpoint_interval设置")
    
    # 保存修复后的文件
    with open(filepath, 'w') as f:
        f.write(content)
    
    print("  ✅ smart_batch_runner.py修复完成")
    return True

def fix_batch_test_runner():
    """修复batch_test_runner.py"""
    print("\n修复batch_test_runner.py...")
    
    filepath = Path("batch_test_runner.py")
    if not filepath.exists():
        print("❌ 文件不存在: batch_test_runner.py")
        return False
    
    backup_file(filepath)
    
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    # 修复：即使enable_database_updates=False也要保存数据
    # 在行1006-1015附近
    modified = False
    for i in range(len(lines)):
        if "# ❌ 修复：即使disable_database_updates，也要保存数据！" in lines[i]:
            # 已经有修复了，但我们需要确保它真的在执行
            print("  ✅ 已有修复代码")
            modified = True
            break
    
    if not modified:
        # 添加强制保存逻辑
        for i in range(len(lines)):
            if "if self.enable_database_updates:" in lines[i] and i > 990 and i < 1010:
                # 修改为总是保存
                lines[i] = "        if True:  # 强制总是保存数据，避免丢失\n"
                print("  ✅ 修复数据保存逻辑")
                modified = True
                break
    
    if modified:
        with open(filepath, 'w') as f:
            f.writelines(lines)
        print("  ✅ batch_test_runner.py修复完成")
    else:
        print("  ⚠️ 未找到需要修复的代码")
    
    return True

def add_periodic_flush():
    """添加定期刷新功能到manager"""
    print("\n添加定期刷新功能...")
    
    # 创建一个wrapper脚本，定期刷新数据
    wrapper_content = '''#!/usr/bin/env python3
"""
数据保存包装器 - 确保数据定期保存
"""
import os
import sys
import time
import threading
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# 导入manager
storage_format = os.environ.get('STORAGE_FORMAT', 'json').lower()
if storage_format == 'parquet':
    try:
        from parquet_cumulative_manager import ParquetCumulativeManager as Manager
        print("[INFO] 使用Parquet存储格式")
    except ImportError:
        from enhanced_cumulative_manager import EnhancedCumulativeManager as Manager
        print("[INFO] 使用JSON存储格式")
else:
    from enhanced_cumulative_manager import EnhancedCumulativeManager as Manager
    print("[INFO] 使用JSON存储格式")

def periodic_flush(manager, interval=30):
    """定期刷新数据"""
    while True:
        time.sleep(interval)
        try:
            if hasattr(manager, '_flush_buffer'):
                manager._flush_buffer()
                print(f"[FLUSH] 数据已刷新到磁盘")
            if hasattr(manager, 'save_database'):
                manager.save_database()
                print(f"[SAVE] 数据库已保存")
        except Exception as e:
            print(f"[ERROR] 刷新失败: {e}")

# 创建全局manager实例
global_manager = Manager()

# 启动定期刷新线程
flush_thread = threading.Thread(target=periodic_flush, args=(global_manager, 30))
flush_thread.daemon = True
flush_thread.start()

print("[INFO] 定期刷新线程已启动（每30秒刷新）")
'''
    
    with open('data_save_wrapper.py', 'w') as f:
        f.write(wrapper_content)
    
    print("  ✅ 创建data_save_wrapper.py")
    return True

def main():
    """主函数"""
    print("=" * 60)
    print("修复数据保存问题")
    print("=" * 60)
    
    # 1. 修复smart_batch_runner.py
    fix_smart_batch_runner()
    
    # 2. 修复batch_test_runner.py
    fix_batch_test_runner()
    
    # 3. 添加定期刷新
    add_periodic_flush()
    
    print("\n" + "=" * 60)
    print("修复完成！")
    print("=" * 60)
    print("\n建议：")
    print("1. 不要使用--batch-commit参数，让数据实时保存")
    print("2. 或者使用更小的checkpoint-interval（如5）")
    print("3. 运行测试时监控数据文件更新：")
    print("   watch -n 10 'ls -la pilot_bench_parquet_data/test_results.parquet'")
    print("\n测试命令（不使用batch-commit）：")
    print("export STORAGE_FORMAT=parquet")
    print("python3 smart_batch_runner.py \\")
    print("  --model DeepSeek-V3-0324 \\")
    print("  --prompt-types baseline \\")
    print("  --difficulty easy \\")
    print("  --task-types simple_task \\")
    print("  --num-instances 2 \\")
    print("  --tool-success-rate 0.8 \\")
    print("  --max-workers 5 \\")
    print("  --save-logs")

if __name__ == "__main__":
    main()