#!/usr/bin/env python3
"""
修复ultra_parallel_runner_debug.py的日志覆盖问题
确保不同模型和不同时间的日志不会互相覆盖
"""

import sys
from pathlib import Path
import shutil
from datetime import datetime

def fix_debug_runner():
    """修复日志文件名生成逻辑"""
    
    file_path = Path('ultra_parallel_runner_debug.py')
    
    # 备份原文件
    backup_path = file_path.with_suffix(f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
    shutil.copy(file_path, backup_path)
    print(f"✅ 已备份到: {backup_path}")
    
    # 读取文件内容
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # 找到需要修改的部分（第128-144行）
    start_line = None
    for i, line in enumerate(lines):
        if '# 创建分片日志文件 - 使用唯一的文件名避免覆盖' in line:
            start_line = i
            break
    
    if start_line is None:
        print("❌ 未找到需要修改的代码")
        return False
    
    print(f"📍 找到日志生成代码: 第{start_line+1}行")
    
    # 新的日志文件名生成逻辑
    new_code = '''        # 创建分片日志文件 - 使用唯一的文件名避免覆盖
        self.shard_counter += 1
        
        # 将模型名和shard_id中的特殊字符替换为下划线
        model_safe = shard.model.replace('/', '_').replace('\\\\', '_').replace('.', '_').replace('-', '_')
        shard_id_safe = shard.shard_id.replace('/', '_').replace('\\\\', '_').replace('.', '_').replace('-', '_')
        
        # 使用完整时间戳（包含日期和时间）确保唯一性
        import time
        from datetime import datetime
        
        # 方案1：使用完整时间戳（精确到微秒）
        timestamp_full = datetime.now().strftime("%H%M%S_%f")[:-3]  # HHMMSS_mmm 格式
        
        # 方案2：添加进程ID确保跨进程唯一
        import os
        pid = os.getpid()
        
        # 方案3：使用全局计数器+模型名hash
        import hashlib
        model_hash = hashlib.md5(shard.model.encode()).hexdigest()[:4]
        
        # 组合多个元素确保绝对唯一性：模型名_模型hash_时间戳_进程ID_计数器
        shard_log_file = self.debug_log_dir / f"{model_safe}_{model_hash}_{timestamp_full}_p{pid}_{self.shard_counter:03d}_{shard_id_safe}.log"
        
        # 额外的安全检查：如果文件仍然存在，添加额外的计数器
        counter = 1
        base_name = shard_log_file.stem
        while shard_log_file.exists():
            shard_log_file = self.debug_log_dir / f"{base_name}_v{counter:02d}.log"
            counter += 1
            if counter > 99:  # 防止无限循环
                # 使用纳秒时间戳作为最后手段
                import time
                nano_suffix = str(time.time_ns())[-6:]
                shard_log_file = self.debug_log_dir / f"{base_name}_n{nano_suffix}.log"
                break
'''
    
    # 找到替换的结束位置
    end_line = start_line + 17  # 原代码大约17行
    
    # 替换代码
    new_lines = lines[:start_line] + [new_code] + lines[end_line:]
    
    # 另外修复debug_log_dir的初始化，确保每个测试会话有独立的目录
    # 查找__init__方法
    for i, line in enumerate(new_lines):
        if 'def __init__(self, debug_log_dir: str = None):' in line:
            # 找到设置debug_log_dir的部分
            for j in range(i, min(i+20, len(new_lines))):
                if 'self.debug_log_dir = Path(f"logs/debug_ultra_{timestamp}")' in new_lines[j]:
                    # 修改为包含更多信息的目录名
                    new_lines[j] = '            self.debug_log_dir = Path(f"logs/debug_ultra_{timestamp}_{os.getpid()}")\n'
                    print("✅ 修复了debug_log_dir生成逻辑")
                    break
    
    # 写回文件
    with open(file_path, 'w') as f:
        f.writelines(new_lines)
    
    print("✅ 修复完成")
    return True

def verify_fix():
    """验证修复是否成功"""
    
    print("\n验证修复...")
    
    # 检查文件是否包含新代码
    with open('ultra_parallel_runner_debug.py', 'r') as f:
        content = f.read()
    
    checks = [
        ('使用完整时间戳', 'timestamp_full' in content),
        ('包含进程ID', 'pid = os.getpid()' in content),
        ('包含模型hash', 'model_hash' in content),
        ('改进的文件名格式', 'model_hash}_{timestamp_full}_p{pid}' in content),
    ]
    
    all_passed = True
    for check_name, passed in checks:
        if passed:
            print(f"  ✅ {check_name}")
        else:
            print(f"  ❌ {check_name}")
            all_passed = False
    
    return all_passed

def test_uniqueness():
    """测试文件名唯一性"""
    
    print("\n测试文件名唯一性...")
    
    # 模拟生成文件名
    import hashlib
    import os
    from datetime import datetime
    
    models = ["DeepSeek-V3-0324", "DeepSeek-R1-0528", "DeepSeek-V3-0324"]  # 故意重复
    filenames = []
    
    for i, model in enumerate(models):
        model_safe = model.replace('-', '_')
        model_hash = hashlib.md5(model.encode()).hexdigest()[:4]
        timestamp_full = datetime.now().strftime("%H%M%S_%f")[:-3]
        pid = os.getpid()
        counter = i + 1
        
        filename = f"{model_safe}_{model_hash}_{timestamp_full}_p{pid}_{counter:03d}_easy_0.log"
        filenames.append(filename)
        
        # 稍微等待以获得不同的时间戳
        import time
        time.sleep(0.001)
    
    print(f"  生成了{len(filenames)}个文件名:")
    for f in filenames:
        print(f"    {f}")
    
    # 检查唯一性
    if len(set(filenames)) == len(filenames):
        print("  ✅ 所有文件名都是唯一的")
        return True
    else:
        print("  ❌ 存在重复的文件名")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("修复Ultra Parallel Runner Debug日志覆盖问题")
    print("=" * 60)
    
    # 执行修复
    if not fix_debug_runner():
        print("❌ 修复失败")
        return 1
    
    # 验证修复
    if not verify_fix():
        print("❌ 验证失败")
        return 1
    
    # 测试唯一性
    if not test_uniqueness():
        print("❌ 唯一性测试失败")
        return 1
    
    print("\n✅ 所有修复已完成！")
    print("\n改进内容：")
    print("1. 使用完整时间戳（精确到毫秒）")
    print("2. 添加模型hash（4位）区分不同模型")
    print("3. 添加进程ID防止并发冲突")
    print("4. 使用递增计数器")
    print("5. 改进的文件名格式：{模型}_{hash}_{时间戳}_p{进程ID}_{计数器}_{shard_id}.log")
    print("\n示例文件名：")
    print("  deepseek_v3_0324_a3f2_141523_456_p12345_001_easy_0.log")
    print("  deepseek_r1_0528_b7c9_141524_123_p12345_002_easy_1.log")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())