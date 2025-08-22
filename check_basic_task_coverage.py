#!/usr/bin/env python3
"""
检查所有模型的basic_task测试覆盖情况
验证是否真的缺失basic_task测试
"""

import json
from pathlib import Path
from collections import defaultdict
import pandas as pd

def check_json_database():
    """检查JSON数据库中的basic_task覆盖"""
    
    db_path = Path("pilot_bench_cumulative_results/master_database.json")
    if not db_path.exists():
        print("❌ JSON数据库不存在")
        return None
    
    with open(db_path, 'r', encoding='utf-8') as f:
        db = json.load(f)
    
    print("=" * 60)
    print("JSON数据库 - basic_task覆盖分析")
    print("=" * 60)
    
    # 定义所有任务类型
    all_task_types = [
        "simple_task",
        "basic_task",  # 之前被错误地称为file_processing
        "multi_step_task", 
        "complex_branching",
        "multi_stage_pipeline"
    ]
    
    task_coverage = defaultdict(lambda: defaultdict(int))
    missing_basic_task_models = []
    
    # 遍历所有模型
    for model_name, model_data in db.get('models', {}).items():
        print(f"\n📊 {model_name}:")
        
        model_has_basic_task = False
        
        # 遍历所有prompt_type
        if 'by_prompt_type' in model_data:
            for prompt_type, prompt_data in model_data['by_prompt_type'].items():
                # 遍历tool_success_rate层级
                if 'by_tool_success_rate' in prompt_data:
                    for rate, rate_data in prompt_data['by_tool_success_rate'].items():
                        # 遍历difficulty层级
                        if 'by_difficulty' in rate_data:
                            for difficulty, diff_data in rate_data['by_difficulty'].items():
                                # 遍历task_type层级
                                if 'by_task_type' in diff_data:
                                    task_types = diff_data['by_task_type'].keys()
                                    for task_type in task_types:
                                        task_data = diff_data['by_task_type'][task_type]
                                        total = task_data.get('total', 0)
                                        if total > 0:
                                            task_coverage[model_name][task_type] += total
                                            if task_type == "basic_task":
                                                model_has_basic_task = True
        
        # 显示该模型的任务类型覆盖
        if task_coverage[model_name]:
            print("  任务类型覆盖:")
            for task_type in all_task_types:
                count = task_coverage[model_name].get(task_type, 0)
                if count > 0:
                    print(f"    ✅ {task_type}: {count} 个测试")
                else:
                    print(f"    ❌ {task_type}: 0 个测试（缺失）")
            
            # 检查是否有basic_task
            if not model_has_basic_task:
                missing_basic_task_models.append(model_name)
                print(f"  ⚠️ 警告：缺少basic_task测试！")
        else:
            print("  无测试数据")
    
    return missing_basic_task_models, task_coverage

def check_parquet_database():
    """检查Parquet数据库中的basic_task覆盖"""
    
    parquet_path = Path("pilot_bench_parquet_data/test_results.parquet")
    if not parquet_path.exists():
        print("\n❌ Parquet数据库不存在")
        return None
    
    print("\n" + "=" * 60)
    print("Parquet数据库 - basic_task覆盖分析")
    print("=" * 60)
    
    try:
        df = pd.read_parquet(parquet_path)
        
        # 检查是否有task_type列
        if 'task_type' not in df.columns:
            print("⚠️ Parquet中没有task_type列")
            return None
        
        # 按模型和任务类型分组
        task_summary = df.groupby(['model', 'task_type']).size().unstack(fill_value=0)
        
        print("\n任务类型分布：")
        print(task_summary)
        
        # 找出缺少basic_task的模型
        if 'basic_task' not in task_summary.columns:
            print("\n❌ 所有模型都缺少basic_task！")
            return list(task_summary.index)
        else:
            missing_models = task_summary[task_summary['basic_task'] == 0].index.tolist()
            if missing_models:
                print(f"\n⚠️ 缺少basic_task的模型: {missing_models}")
            else:
                print("\n✅ 所有模型都有basic_task测试")
            return missing_models
            
    except Exception as e:
        print(f"❌ 分析Parquet失败: {e}")
        return None

def check_test_logs():
    """检查测试日志中是否有file_processing相关的警告"""
    
    print("\n" + "=" * 60)
    print("测试日志分析")
    print("=" * 60)
    
    log_dir = Path("logs")
    if not log_dir.exists():
        print("❌ 日志目录不存在")
        return
    
    # 查找包含file_processing警告的日志
    warning_count = 0
    for log_file in log_dir.glob("batch_test_*.log"):
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                if "No tasks found for type 'file_processing'" in content:
                    warning_count += 1
                    print(f"  ⚠️ {log_file.name}: 发现file_processing警告")
                    # 只显示前3个
                    if warning_count >= 3:
                        break
        except:
            pass
    
    if warning_count > 0:
        print(f"\n发现 {warning_count}+ 个日志包含file_processing警告")
        print("这证实了file_processing vs basic_task的混淆问题")

def main():
    """主函数"""
    
    print("=" * 60)
    print("Basic Task 覆盖检查工具")
    print("=" * 60)
    
    # 检查JSON数据库
    missing_json, task_coverage = check_json_database()
    
    # 检查Parquet数据库
    missing_parquet = check_parquet_database()
    
    # 检查日志
    check_test_logs()
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 分析总结")
    print("=" * 60)
    
    if missing_json:
        print(f"\n❌ JSON数据库中缺少basic_task的模型数: {len(missing_json)}")
        print("缺失的模型:")
        for model in missing_json[:10]:  # 只显示前10个
            print(f"  - {model}")
        if len(missing_json) > 10:
            print(f"  ... 以及其他 {len(missing_json)-10} 个模型")
    else:
        print("\n✅ JSON数据库中所有模型都有basic_task测试")
    
    # 计算总体覆盖率
    if task_coverage:
        total_basic_task = sum(cov.get('basic_task', 0) for cov in task_coverage.values())
        total_all_tasks = sum(sum(cov.values()) for cov in task_coverage.values())
        
        print(f"\n📈 总体统计:")
        print(f"  - basic_task测试总数: {total_basic_task}")
        print(f"  - 所有测试总数: {total_all_tasks}")
        if total_all_tasks > 0:
            print(f"  - basic_task占比: {total_basic_task/total_all_tasks*100:.1f}%")
            
            # 预期basic_task应该占20%（5种任务类型之一）
            expected_percentage = 20
            actual_percentage = total_basic_task/total_all_tasks*100
            
            if actual_percentage < expected_percentage * 0.5:  # 如果实际占比小于预期的一半
                print(f"\n⚠️ basic_task严重不足！预期约{expected_percentage}%，实际只有{actual_percentage:.1f}%")
                print("建议：需要为所有模型补充basic_task测试")
            elif actual_percentage < expected_percentage * 0.9:
                print(f"\n⚠️ basic_task略有不足。预期约{expected_percentage}%，实际{actual_percentage:.1f}%")
            else:
                print(f"\n✅ basic_task覆盖正常")

if __name__ == "__main__":
    main()