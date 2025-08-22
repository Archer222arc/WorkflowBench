#!/usr/bin/env python3
"""
完整验证错误分类系统是否正常工作
运行一个会失败的测试，并检查AI分类结果
"""

import os
import subprocess
import json
import time
from pathlib import Path
import pandas as pd

# 设置使用Parquet格式
os.environ['STORAGE_FORMAT'] = 'parquet'

print("=" * 70)
print("错误分类系统完整验证")
print("=" * 70)

# 使用一个测试模型名称
test_model = "verify-ai-classification-model"

print(f"\n1. 清理测试模型 {test_model} 的旧数据...")

# 清理旧数据
from parquet_cumulative_manager import ParquetCumulativeManager
manager = ParquetCumulativeManager()

# 清理JSON数据
json_file = Path('pilot_bench_cumulative_results/master_database.json')
if json_file.exists():
    with open(json_file, 'r') as f:
        db = json.load(f)
    
    if 'models' in db and test_model in db['models']:
        del db['models'][test_model]
        print(f"  已清理JSON中的 {test_model}")
    
    # 清理test_groups
    if 'test_groups' in db:
        keys_to_remove = [k for k in db['test_groups'].keys() if test_model in k]
        for key in keys_to_remove:
            del db['test_groups'][key]
    
    with open(json_file, 'w') as f:
        json.dump(db, f, indent=2)

print("\n2. 运行测试（设置低成功率以产生错误）...")

# 构建命令
cmd = [
    "python", "smart_batch_runner.py",
    "--model", test_model,
    "--prompt-types", "baseline",
    "--difficulty", "easy",
    "--task-types", "simple_task",
    "--num-instances", "5",  # 运行5个测试
    "--max-workers", "2",
    "--tool-success-rate", "0.2",  # 设置很低的成功率，确保有失败
    "--ai-classification",  # 明确启用AI分类
    "--no-adaptive",
    "--qps", "5",
    "--no-save-logs"  # 不保存详细日志
]

print(f"  命令: {' '.join(cmd)}")
print("  正在运行测试...")

# 运行测试
start_time = time.time()
result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
elapsed = time.time() - start_time

print(f"  测试完成，耗时: {elapsed:.1f}秒")
print(f"  退出码: {result.returncode}")

# 检查输出中是否有AI分类信息
if "AI_CLASSIFIER" in result.stdout or "AI classification" in result.stdout:
    print("  ✅ 检测到AI分类器运行")
else:
    print("  ⚠️ 未检测到AI分类器运行信息")

# 等待数据写入
time.sleep(2)

print("\n3. 检查Parquet数据中的错误分类...")

# 读取Parquet数据
parquet_file = Path('pilot_bench_parquet_data/test_results.parquet')
if parquet_file.exists():
    df = pd.read_parquet(parquet_file)
    
    # 查找测试模型的数据
    test_df = df[df['model'] == test_model]
    
    if len(test_df) > 0:
        print(f"  ✅ 找到 {test_model} 的 {len(test_df)} 条记录")
        
        # 汇总所有错误统计
        total_errors = test_df['total_errors'].sum()
        other_errors = test_df['other_errors'].sum()
        
        error_types = {
            'tool_call_format_errors': '格式错误',
            'timeout_errors': '超时错误',
            'max_turns_errors': '轮次错误',
            'tool_selection_errors': '工具选择',
            'parameter_config_errors': '参数配置',
            'sequence_order_errors': '顺序错误',
            'dependency_errors': '依赖错误'
        }
        
        print(f"\n  总错误数: {int(total_errors)}")
        
        if total_errors > 0:
            print("  错误分类详情:")
            classified_count = 0
            
            for error_type, name in error_types.items():
                count = test_df[error_type].sum()
                if count > 0:
                    print(f"    {name}: {int(count)}")
                    classified_count += count
            
            if other_errors > 0:
                print(f"    其他错误: {int(other_errors)}")
            
            other_rate = other_errors / total_errors
            print(f"\n  other_error_rate: {other_rate:.1%}")
            
            if classified_count > 0:
                print("\n  ✅ AI分类系统工作正常！错误被正确分类")
                print(f"  ✅ {classified_count}/{int(total_errors)} 个错误被正确分类")
            else:
                print("\n  ❌ 所有错误都是other_errors，AI分类可能未启用")
        else:
            print("  ⚠️ 没有错误产生（所有测试都成功了）")
    else:
        print(f"  ❌ 未找到 {test_model} 的数据")
else:
    print("  ❌ Parquet文件不存在")

print("\n4. 检查JSON数据对比...")

json_file = Path('pilot_bench_cumulative_results/master_database.json')
if json_file.exists():
    with open(json_file, 'r') as f:
        db = json.load(f)
    
    if 'models' in db and test_model in db['models']:
        model_data = db['models'][test_model]
        print(f"  ✅ 找到JSON数据")
        
        # 查找baseline数据
        if 'by_prompt_type' in model_data and 'baseline' in model_data['by_prompt_type']:
            baseline = model_data['by_prompt_type']['baseline']
            
            # 遍历所有层级找到数据
            total_json_errors = 0
            other_json_errors = 0
            
            for rate_key in baseline.get('by_tool_success_rate', {}):
                rate_data = baseline['by_tool_success_rate'][rate_key]
                for diff_key in rate_data.get('by_difficulty', {}):
                    diff_data = rate_data['by_difficulty'][diff_key]
                    for task_key in diff_data.get('by_task_type', {}):
                        task_data = diff_data['by_task_type'][task_key]
                        
                        total_json_errors += task_data.get('total_errors', 0)
                        other_json_errors += task_data.get('other_errors', 0)
                        
                        if task_data.get('total_errors', 0) > 0:
                            print(f"\n  JSON数据 ({rate_key} -> {diff_key} -> {task_key}):")
                            print(f"    total_errors: {task_data.get('total_errors', 0)}")
                            
                            # 显示各种错误类型
                            for error_type in error_types.keys():
                                count = task_data.get(error_type, 0)
                                if count > 0:
                                    print(f"    {error_type}: {count}")
                            
                            if task_data.get('other_errors', 0) > 0:
                                print(f"    other_errors: {task_data.get('other_errors', 0)}")
            
            if total_json_errors > 0:
                json_other_rate = other_json_errors / total_json_errors
                print(f"\n  JSON other_error_rate: {json_other_rate:.1%}")
    else:
        print(f"  ❌ JSON中未找到 {test_model}")

print("\n" + "=" * 70)
print("验证完成！")
print("=" * 70)

# 总结
print("\n总结:")
print("1. 如果看到错误被分类为具体类型（非other_errors），说明系统工作正常")
print("2. 如果所有错误都是other_errors，可能需要检查AI分类是否正确启用")
print("3. 检查日志文件 logs/batch_test_*.log 可以看到更多细节")