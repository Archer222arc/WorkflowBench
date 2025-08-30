#!/usr/bin/env python3
"""
将master_database.json完整转换为CSV格式，包含所有字段
"""

import json
import csv
from pathlib import Path
from datetime import datetime

print('🔄 开始完整转换JSON到CSV格式（包含所有字段）...')
print('=' * 80)

# 读取JSON数据
json_path = Path('pilot_bench_cumulative_results/master_database.json')
with open(json_path, 'r') as f:
    db = json.load(f)

print(f'✅ 读取JSON数据成功')
print(f'  - 模型数量: {len(db.get("models", {}))}')

# 创建输出目录
output_dir = Path('pilot_bench_csv_data')
output_dir.mkdir(exist_ok=True)

# 准备CSV数据
rows = []
models_data = db.get('models', {})

# 所有可能的字段（基于您选中的内容）
all_fields = [
    # 基本维度
    'model', 'prompt_type', 'tool_success_rate', 'difficulty', 'task_type',
    
    # 基本统计
    'total', 'success', 'partial', 'failed',
    'success_rate', 'partial_rate', 'failure_rate',
    'weighted_success_score', 'full_success_rate', 'partial_success_rate',
    
    # 执行指标
    'avg_execution_time', 'avg_turns', 'avg_tool_calls', 'tool_coverage_rate',
    
    # 质量分数
    'avg_workflow_score', 'avg_phase2_score', 'avg_quality_score', 'avg_final_score',
    
    # 错误统计
    'total_errors',
    'tool_call_format_errors', 'timeout_errors', 'dependency_errors',
    'parameter_config_errors', 'tool_selection_errors', 
    'sequence_order_errors', 'max_turns_errors', 'other_errors',
    
    # 错误率
    'tool_selection_error_rate', 'parameter_error_rate', 'sequence_error_rate',
    'dependency_error_rate', 'timeout_error_rate', 'format_error_rate',
    'max_turns_error_rate', 'other_error_rate',
    
    # 辅助相关
    'assisted_failure', 'assisted_success', 'total_assisted_turns',
    'tests_with_assistance', 'avg_assisted_turns', 
    'assisted_success_rate', 'assistance_rate',
    
    # 额外字段（可能存在）
    'full_success', 'partial_success',
    
    # 元数据
    'timestamp'
]

for model_name, model_data in models_data.items():
    by_prompt = model_data.get('by_prompt_type', {})
    
    for prompt_type, prompt_data in by_prompt.items():
        by_rate = prompt_data.get('by_tool_success_rate', {})
        
        for rate, rate_data in by_rate.items():
            by_diff = rate_data.get('by_difficulty', {})
            
            for difficulty, diff_data in by_diff.items():
                by_task = diff_data.get('by_task_type', {})
                
                for task_type, task_data in by_task.items():
                    # 创建行数据，包含所有字段
                    row = {
                        'model': model_name,
                        'prompt_type': prompt_type,
                        'tool_success_rate': float(rate),
                        'difficulty': difficulty,
                        'task_type': task_type,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # 添加所有任务数据字段
                    for field in all_fields:
                        if field not in ['model', 'prompt_type', 'tool_success_rate', 
                                        'difficulty', 'task_type', 'timestamp']:
                            row[field] = task_data.get(field, '')
                    
                    rows.append(row)

print(f'✅ 展平数据完成，共{len(rows)}条记录')

# 获取所有唯一字段名
if rows:
    all_fieldnames = []
    seen = set()
    
    # 保持顺序：先加维度字段，再加其他字段
    for field in ['model', 'prompt_type', 'tool_success_rate', 'difficulty', 'task_type']:
        if field not in seen:
            all_fieldnames.append(field)
            seen.add(field)
    
    # 添加其他字段
    for row in rows:
        for key in row.keys():
            if key not in seen:
                all_fieldnames.append(key)
                seen.add(key)
    
    print(f'✅ 检测到{len(all_fieldnames)}个字段')

    # 写入CSV文件
    output_file = output_dir / f'test_results_complete_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=all_fieldnames, restval='')
        writer.writeheader()
        writer.writerows(rows)
    
    print(f'✅ 成功保存到: {output_file}')
    print(f'  - 文件大小: {output_file.stat().st_size / 1024:.1f} KB')
    print(f'  - 记录数: {len(rows)}')
    print(f'  - 字段数: {len(all_fieldnames)}')
    
    # 保存一个字段列表文件
    fields_file = output_dir / 'field_descriptions.txt'
    with open(fields_file, 'w', encoding='utf-8') as f:
        f.write('CSV文件字段说明\n')
        f.write('=' * 60 + '\n\n')
        f.write('维度字段:\n')
        f.write('  - model: 模型名称\n')
        f.write('  - prompt_type: 提示类型\n')
        f.write('  - tool_success_rate: 工具成功率\n')
        f.write('  - difficulty: 难度等级\n')
        f.write('  - task_type: 任务类型\n\n')
        f.write('统计字段:\n')
        f.write('  - total/success/partial/failed: 总数/成功/部分/失败\n')
        f.write('  - *_rate: 各种比率\n')
        f.write('  - avg_*: 平均值指标\n')
        f.write('  - *_errors: 错误计数\n')
        f.write('  - *_error_rate: 错误率\n')
        f.write('  - assisted_*: 辅助相关指标\n')
        f.write('  - full_success/partial_success: 完全成功/部分成功数\n')
    
    print(f'✅ 字段说明已保存到: {fields_file}')
    
    # 显示摘要
    print('\n📊 数据摘要:')
    model_totals = {}
    for row in rows:
        model = row['model']
        if model not in model_totals:
            model_totals[model] = 0
        model_totals[model] += row.get('total', 0)
    
    for model, total in sorted(model_totals.items()):
        print(f'  {model}: {total}个测试')
    
    # 也保存为latest版本
    latest_file = output_dir / 'test_results_complete_latest.csv'
    with open(latest_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=all_fieldnames, restval='')
        writer.writeheader()
        writer.writerows(rows)
    print(f'\n✅ 同时保存为: {latest_file}')
    
else:
    print('⚠️ 没有数据可转换')
