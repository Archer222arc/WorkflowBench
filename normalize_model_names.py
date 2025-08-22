#!/usr/bin/env python3
"""
模型名称归一化工具
将并行实例（如deepseek-v3-0324-2）归并到主模型名（如DeepSeek-V3-0324）
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import shutil
from typing import Dict, List, Tuple

# 模型名称映射规则
MODEL_NORMALIZATION_RULES = {
    # DeepSeek系列
    'deepseek-v3-0324-2': 'DeepSeek-V3-0324',
    'deepseek-v3-0324-3': 'DeepSeek-V3-0324',
    'deepseek-r1-0528-2': 'DeepSeek-R1-0528',
    'deepseek-r1-0528-3': 'DeepSeek-R1-0528',
    
    # Llama系列
    'llama-3.3-70b-instruct-2': 'Llama-3.3-70B-Instruct',
    'llama-3.3-70b-instruct-3': 'Llama-3.3-70B-Instruct',
    
    # Qwen系列 - 这些是不同的模型，不应合并
    # 'qwen2.5-32b-instruct': 'qwen2.5-32b-instruct',  # 保持原样
    # 'qwen2.5-3b-instruct': 'qwen2.5-3b-instruct',    # 保持原样
}

def normalize_model_name(model_name: str) -> str:
    """
    标准化模型名称
    将并行实例名称转换为主模型名称
    """
    # 检查是否在映射规则中
    if model_name in MODEL_NORMALIZATION_RULES:
        return MODEL_NORMALIZATION_RULES[model_name]
    
    # 通用规则：去除 -2, -3 等后缀（仅对已知的并行模型）
    if any(base in model_name.lower() for base in ['deepseek', 'llama', 'grok']):
        # 移除 -数字 后缀
        import re
        cleaned = re.sub(r'-\d+$', '', model_name)
        
        # 标准化大小写
        if 'deepseek-v3' in cleaned.lower():
            return 'DeepSeek-V3-0324'
        elif 'deepseek-r1' in cleaned.lower():
            return 'DeepSeek-R1-0528'
        elif 'llama-3.3' in cleaned.lower():
            return 'Llama-3.3-70B-Instruct'
    
    return model_name

def fix_parquet_data():
    """修复Parquet数据中的模型名称"""
    parquet_file = Path('pilot_bench_parquet_data/test_results.parquet')
    
    if not parquet_file.exists():
        print("❌ Parquet文件不存在")
        return False
    
    # 备份原文件
    backup_file = parquet_file.with_suffix('.parquet.backup')
    shutil.copy(parquet_file, backup_file)
    print(f"✅ 已备份到 {backup_file}")
    
    # 读取数据
    df = pd.read_parquet(parquet_file)
    original_count = len(df)
    
    # 统计需要修改的记录
    models_to_fix = df['model'].apply(lambda x: x in MODEL_NORMALIZATION_RULES)
    fix_count = models_to_fix.sum()
    
    print(f"\n📊 Parquet数据统计:")
    print(f"  总记录数: {original_count}")
    print(f"  需要修复: {fix_count}")
    
    if fix_count > 0:
        # 显示修改详情
        print("\n📝 修改详情:")
        for old_name in MODEL_NORMALIZATION_RULES.keys():
            count = (df['model'] == old_name).sum()
            if count > 0:
                new_name = MODEL_NORMALIZATION_RULES[old_name]
                print(f"  {old_name} -> {new_name}: {count} 条")
        
        # 应用归一化
        df['model'] = df['model'].apply(normalize_model_name)
        
        # 重新生成test_id（如果需要）
        # 注意：保留原始test_id可能更好，用于追踪
        
        # 保存修复后的数据
        df.to_parquet(parquet_file, index=False)
        print(f"\n✅ Parquet数据已修复")
        
        # 显示合并后的统计
        print("\n📈 合并后统计:")
        for model in df['model'].unique():
            if model in ['DeepSeek-V3-0324', 'DeepSeek-R1-0528', 'Llama-3.3-70B-Instruct']:
                count = (df['model'] == model).sum()
                print(f"  {model}: {count} 条")
    else:
        print("✅ Parquet数据无需修复")
    
    return True

def fix_json_data():
    """修复JSON数据中的模型名称"""
    json_file = Path('pilot_bench_cumulative_results/master_database.json')
    
    if not json_file.exists():
        print("❌ JSON文件不存在")
        return False
    
    # 备份原文件
    backup_file = json_file.with_suffix('.json.backup')
    shutil.copy(json_file, backup_file)
    print(f"✅ 已备份到 {backup_file}")
    
    # 读取数据
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    models_data = data.get('models', {})
    
    # 统计需要合并的模型
    models_to_merge = [m for m in models_data.keys() if m in MODEL_NORMALIZATION_RULES]
    
    print(f"\n📊 JSON数据统计:")
    print(f"  总模型数: {len(models_data)}")
    print(f"  需要合并: {len(models_to_merge)}")
    
    if models_to_merge:
        print("\n📝 合并详情:")
        
        for old_name in models_to_merge:
            new_name = MODEL_NORMALIZATION_RULES[old_name]
            old_data = models_data[old_name]
            
            print(f"\n  {old_name} -> {new_name}")
            print(f"    测试数: {old_data.get('total_tests', 0)}")
            
            # 如果目标模型已存在，需要合并数据
            if new_name in models_data:
                print(f"    ⚠️ 目标模型已存在，合并数据...")
                merge_model_data(models_data[new_name], old_data)
            else:
                # 直接改名
                models_data[new_name] = old_data
                models_data[new_name]['model_name'] = new_name
            
            # 删除旧模型
            del models_data[old_name]
        
        # 更新汇总统计
        update_summary_stats(data)
        
        # 保存修复后的数据
        data['last_updated'] = datetime.now().isoformat()
        with open(json_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"\n✅ JSON数据已修复")
        
        # 显示合并后的统计
        print("\n📈 合并后统计:")
        for model in ['DeepSeek-V3-0324', 'DeepSeek-R1-0528', 'Llama-3.3-70B-Instruct']:
            if model in models_data:
                tests = models_data[model].get('total_tests', 0)
                print(f"  {model}: {tests} 个测试")
    else:
        print("✅ JSON数据无需修复")
    
    return True

def merge_model_data(target_data: Dict, source_data: Dict):
    """
    合并两个模型的数据
    """
    # 更新总测试数
    target_data['total_tests'] = target_data.get('total_tests', 0) + source_data.get('total_tests', 0)
    
    # 合并overall_stats
    if 'overall_stats' in source_data:
        if 'overall_stats' not in target_data:
            target_data['overall_stats'] = source_data['overall_stats']
        else:
            # 需要重新计算统计数据
            merge_stats(target_data['overall_stats'], source_data['overall_stats'])
    
    # 合并by_prompt_type层次结构
    if 'by_prompt_type' in source_data:
        if 'by_prompt_type' not in target_data:
            target_data['by_prompt_type'] = source_data['by_prompt_type']
        else:
            merge_hierarchical_data(target_data['by_prompt_type'], source_data['by_prompt_type'])
    
    # 更新时间戳
    target_data['last_test_time'] = datetime.now().isoformat()

def merge_stats(target_stats: Dict, source_stats: Dict):
    """合并统计数据"""
    # 累加计数类字段
    for field in ['total_tests', 'successful', 'partial', 'failed']:
        if field in source_stats:
            target_stats[field] = target_stats.get(field, 0) + source_stats[field]
    
    # 重新计算比率
    total = target_stats.get('total_tests', 0)
    if total > 0:
        target_stats['success_rate'] = target_stats.get('successful', 0) / total
        target_stats['partial_rate'] = target_stats.get('partial', 0) / total
        target_stats['failure_rate'] = target_stats.get('failed', 0) / total

def merge_hierarchical_data(target: Dict, source: Dict):
    """递归合并层次化数据"""
    for key, value in source.items():
        if key not in target:
            target[key] = value
        elif isinstance(value, dict) and isinstance(target[key], dict):
            # 递归合并字典
            merge_hierarchical_data(target[key], value)
        elif isinstance(value, (int, float)) and key in ['total', 'successful', 'partial', 'failed']:
            # 累加数值
            target[key] = target.get(key, 0) + value
        # 其他情况保持target的值

def update_summary_stats(data: Dict):
    """更新汇总统计"""
    models_data = data.get('models', {})
    
    total_tests = 0
    total_success = 0
    total_partial = 0
    total_failure = 0
    
    for model_data in models_data.values():
        total_tests += model_data.get('total_tests', 0)
        stats = model_data.get('overall_stats', {})
        total_success += stats.get('successful', 0)
        total_partial += stats.get('partial', 0)
        total_failure += stats.get('failed', 0)
    
    data['summary'] = {
        'total_tests': total_tests,
        'total_success': total_success,
        'total_partial': total_partial,
        'total_failure': total_failure,
        'models_tested': list(models_data.keys()),
        'last_test_time': datetime.now().isoformat()
    }

def verify_normalization():
    """验证归一化结果"""
    print("\n" + "="*60)
    print("🔍 验证归一化结果")
    print("="*60)
    
    # 验证Parquet
    if Path('pilot_bench_parquet_data/test_results.parquet').exists():
        df = pd.read_parquet('pilot_bench_parquet_data/test_results.parquet')
        problematic = [m for m in df['model'].unique() if '-2' in m or '-3' in m]
        if problematic:
            print(f"⚠️ Parquet中仍有并行实例: {problematic}")
        else:
            print("✅ Parquet数据已完全归一化")
    
    # 验证JSON
    if Path('pilot_bench_cumulative_results/master_database.json').exists():
        with open('pilot_bench_cumulative_results/master_database.json') as f:
            data = json.load(f)
        
        problematic = [m for m in data.get('models', {}).keys() if '-2' in m or '-3' in m]
        if problematic:
            print(f"⚠️ JSON中仍有并行实例: {problematic}")
        else:
            print("✅ JSON数据已完全归一化")

def main():
    """主函数"""
    print("="*60)
    print("🔧 模型名称归一化工具")
    print("="*60)
    print("\n此工具将：")
    print("1. 将并行实例（如deepseek-v3-0324-2）合并到主模型")
    print("2. 备份原始数据")
    print("3. 更新Parquet和JSON数据")
    print("")
    
    # 确认执行
    response = input("确认执行归一化？(y/n): ")
    if response.lower() != 'y':
        print("已取消")
        return
    
    print("\n开始处理...")
    
    # 修复Parquet数据
    print("\n" + "="*40)
    print("1️⃣ 修复Parquet数据")
    print("="*40)
    fix_parquet_data()
    
    # 修复JSON数据
    print("\n" + "="*40)
    print("2️⃣ 修复JSON数据")
    print("="*40)
    fix_json_data()
    
    # 验证结果
    verify_normalization()
    
    print("\n" + "="*60)
    print("✅ 归一化完成！")
    print("="*60)
    print("\n备份文件：")
    print("  - pilot_bench_parquet_data/test_results.parquet.backup")
    print("  - pilot_bench_cumulative_results/master_database.json.backup")

if __name__ == "__main__":
    main()