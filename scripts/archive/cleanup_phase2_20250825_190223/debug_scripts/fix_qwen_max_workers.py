#!/usr/bin/env python3
"""
修改Qwen模型的max_workers为1
根据用户要求："可以把qwen的max worker也设成1"
"""

import shutil
from pathlib import Path
from datetime import datetime

def fix_qwen_max_workers():
    """修改ultra_parallel_runner.py中的qwen max_workers设置"""
    
    file_path = Path("ultra_parallel_runner.py")
    
    # 备份文件
    backup_path = file_path.parent / f"{file_path.stem}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_path.suffix}"
    shutil.copy2(file_path, backup_path)
    print(f"✅ 备份文件到: {backup_path}")
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    modified = False
    changes = []
    
    for i, line in enumerate(lines):
        # 修改固定模式的max_workers
        if 'max_workers = 3  # 固定模式：3个workers避免频繁切换' in line:
            lines[i] = line.replace('3', '1')
            changes.append(f"  第{i+1}行: 固定模式 max_workers 3 → 1")
            modified = True
        
        # 修改自适应模式的max_workers  
        elif 'max_workers = 5  # 自适应模式：每个key可以用5个workers' in line:
            lines[i] = line.replace('5', '1')
            changes.append(f"  第{i+1}行: 自适应模式 max_workers 5 → 1")
            modified = True
    
    if modified:
        with open(file_path, 'w') as f:
            f.writelines(lines)
        
        print("\n✅ 已修改ultra_parallel_runner.py:")
        for change in changes:
            print(change)
        
        print("\n说明:")
        print("  - Qwen模型固定模式：max_workers 3 → 1")
        print("  - Qwen模型自适应模式：max_workers 5 → 1")
        print("  - 这将降低并发度，但可能提高稳定性")
        print("  - 总并发从 3×5=15 降低到 3×1=3")
    else:
        print("⚠️ 未找到需要修改的配置行")
    
    return modified

def verify_changes():
    """验证修改是否正确"""
    file_path = Path("ultra_parallel_runner.py")
    
    print("\n验证修改结果:")
    print("-" * 40)
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # 查找qwen配置部分
    start = content.find('if "qwen" in base_model.lower():')
    if start != -1:
        end = start + 500
        qwen_section = content[start:end]
        
        # 检查固定模式
        if 'max_workers = 1  # 固定模式' in qwen_section:
            print("✅ 固定模式已改为 max_workers=1")
        else:
            print("❌ 固定模式未正确修改")
        
        # 检查自适应模式
        if 'max_workers = 1  # 自适应模式' in qwen_section:
            print("✅ 自适应模式已改为 max_workers=1")
        else:
            print("❌ 自适应模式未正确修改")

def main():
    print("=" * 60)
    print("修改Qwen模型max_workers配置")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 执行修改
    if fix_qwen_max_workers():
        # 验证修改
        verify_changes()
        
        print("\n" + "=" * 60)
        print("修改完成")
        print("=" * 60)
        print("\n下一步:")
        print("1. 重新运行测试以使用新配置")
        print("2. 观察并发度是否降低到预期水平")
        print("3. 检查是否减少超时和错误")
    else:
        print("\n修改失败，请检查文件内容")

if __name__ == "__main__":
    main()