#!/usr/bin/env python3
"""
验证系统修复是否正常工作
包括：
1. 模型名称规范化
2. 文件锁机制
3. 数据库写入的正确性
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from cumulative_test_manager import CumulativeTestManager, TestRecord, normalize_model_name
from file_lock_manager import get_file_lock

def test_model_normalization():
    """测试模型名称规范化"""
    print("=== 测试模型名称规范化 ===")
    
    test_cases = [
        ('deepseek-v3-0324-2', 'DeepSeek-V3-0324'),
        ('deepseek-v3-0324-3', 'DeepSeek-V3-0324'),
        ('deepseek-r1-0528-2', 'DeepSeek-R1-0528'),
        ('llama-3.3-70b-instruct-3', 'Llama-3.3-70B-Instruct'),
        ('qwen2.5-72b-instruct', 'qwen2.5-72b-instruct'),
    ]
    
    all_pass = True
    for input_name, expected in test_cases:
        result = normalize_model_name(input_name)
        if result == expected:
            print(f"  ✅ {input_name} -> {result}")
        else:
            print(f"  ❌ {input_name} -> {result} (期望: {expected})")
            all_pass = False
    
    if all_pass:
        print("✅ 模型名称规范化测试通过\n")
    else:
        print("❌ 模型名称规范化测试失败\n")
    
    return all_pass

def test_file_lock():
    """测试文件锁机制"""
    print("=== 测试文件锁机制 ===")
    
    test_file = Path("test_lock_verify.json")
    
    # 清理旧文件
    if test_file.exists():
        test_file.unlink()
    
    lock_manager = get_file_lock(test_file)
    
    # 测试写入
    initial_data = {"test": "data", "counter": 0}
    success = lock_manager.write_json_safe(initial_data)
    
    if not success:
        print("  ❌ 文件锁写入失败")
        return False
    
    # 测试读取
    read_data = lock_manager.read_json_safe()
    if read_data != initial_data:
        print("  ❌ 文件锁读取数据不一致")
        return False
    
    # 测试更新
    def update_func(data):
        data["counter"] += 1
        data["updated_at"] = datetime.now().isoformat()
        return data
    
    success = lock_manager.update_json_safe(update_func)
    if not success:
        print("  ❌ 文件锁更新失败")
        return False
    
    # 验证更新结果
    final_data = lock_manager.read_json_safe()
    if final_data.get("counter") != 1:
        print("  ❌ 文件锁更新数据不正确")
        return False
    
    # 清理
    if test_file.exists():
        test_file.unlink()
    lock_file = test_file.with_suffix('.lock')
    if lock_file.exists():
        lock_file.unlink()
    
    print("  ✅ 文件锁机制工作正常")
    print("✅ 文件锁测试通过\n")
    return True

def test_cumulative_manager():
    """测试累积管理器的修复"""
    print("=== 测试累积管理器 ===")
    
    # 创建测试数据库
    test_db_path = Path("pilot_bench_cumulative_results/test_verification.json")
    
    # 备份原始数据库路径
    original_db = Path("pilot_bench_cumulative_results/master_database.json")
    
    # 临时使用测试数据库
    manager = CumulativeTestManager()
    manager.db_file = test_db_path
    
    # 清空测试数据库
    manager.database = manager._create_empty_database()
    
    # 测试添加不同实例的记录
    test_records = [
        TestRecord(
            model="deepseek-v3-0324-2",  # 应该被规范化为 DeepSeek-V3-0324
            task_type="simple_task",
            prompt_type="baseline",
            difficulty="easy",
            success=True,
            execution_time=5.0
        ),
        TestRecord(
            model="deepseek-v3-0324-3",  # 也应该被规范化为 DeepSeek-V3-0324
            task_type="simple_task",
            prompt_type="baseline",
            difficulty="easy",
            success=False,
            execution_time=3.0
        ),
        TestRecord(
            model="llama-3.3-70b-instruct-3",  # 应该被规范化为 Llama-3.3-70B-Instruct
            task_type="basic_task",
            prompt_type="cot",
            difficulty="medium",
            success=True,
            execution_time=7.0
        ),
    ]
    
    # 添加测试记录
    for record in test_records:
        success = manager.add_test_result(record)
        if not success:
            print(f"  ❌ 添加记录失败: {record.model}")
            return False
    
    # 验证数据库中的模型
    if "DeepSeek-V3-0324" not in manager.database["models"]:
        print("  ❌ DeepSeek-V3-0324 未找到（规范化失败）")
        return False
    
    if "Llama-3.3-70B-Instruct" not in manager.database["models"]:
        print("  ❌ Llama-3.3-70B-Instruct 未找到（规范化失败）")
        return False
    
    # 不应该有原始的实例名称
    if "deepseek-v3-0324-2" in manager.database["models"]:
        print("  ❌ 发现未规范化的模型名: deepseek-v3-0324-2")
        return False
    
    if "deepseek-v3-0324-3" in manager.database["models"]:
        print("  ❌ 发现未规范化的模型名: deepseek-v3-0324-3")
        return False
    
    print("  ✅ 模型名称正确规范化")
    print("  ✅ 数据正确合并到主模型")
    
    # 清理测试文件
    if test_db_path.exists():
        test_db_path.unlink()
    
    print("✅ 累积管理器测试通过\n")
    return True

def check_database_integrity():
    """检查主数据库的完整性"""
    print("=== 检查主数据库完整性 ===")
    
    db_path = Path("pilot_bench_cumulative_results/master_database.json")
    
    if not db_path.exists():
        print("  ⚠️  主数据库不存在")
        return True  # 不算失败
    
    with open(db_path, 'r') as f:
        db = json.load(f)
    
    print(f"  数据库版本: {db.get('version', '未知')}")
    print(f"  最后更新: {db.get('last_updated', '未知')}")
    print(f"  模型数量: {len(db.get('models', {}))}")
    
    # 检查是否还有未合并的实例
    models = db.get('models', {})
    instances_found = []
    
    for model_name in models.keys():
        if any(suffix in model_name.lower() for suffix in ['-2', '-3', '-4']):
            instances_found.append(model_name)
    
    if instances_found:
        print(f"  ⚠️  发现可能未合并的实例: {instances_found}")
        print("     建议运行 merge_model_instances.py 进行合并")
    else:
        print("  ✅ 没有发现未合并的模型实例")
    
    print("✅ 数据库完整性检查完成\n")
    return True

def main():
    """主测试函数"""
    print("=" * 60)
    print("系统修复验证")
    print("=" * 60)
    print()
    
    all_tests_pass = True
    
    # 1. 测试模型名称规范化
    if not test_model_normalization():
        all_tests_pass = False
    
    # 2. 测试文件锁机制
    if not test_file_lock():
        all_tests_pass = False
    
    # 3. 测试累积管理器
    if not test_cumulative_manager():
        all_tests_pass = False
    
    # 4. 检查数据库完整性
    if not check_database_integrity():
        all_tests_pass = False
    
    # 总结
    print("=" * 60)
    if all_tests_pass:
        print("✅ 所有系统修复验证通过!")
        print("\n系统已准备好进行并发测试，主要改进包括：")
        print("  1. 模型名称自动规范化，防止数据碎片化")
        print("  2. 文件锁机制，防止并发写入冲突")
        print("  3. 原子写入操作，确保数据一致性")
    else:
        print("❌ 部分测试失败，请检查修复")
    print("=" * 60)

if __name__ == "__main__":
    main()