#!/usr/bin/env python3
"""
将master_database.json转换为CSV格式（不需要pandas）
"""

import json
import csv
from pathlib import Path
from datetime import datetime

print('🔄 开始转换JSON到CSV格式...')
print('=' * 60)

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

for model_name, model_data in models_data.items():
    by_prompt = model_data.get('by_prompt_type', {})
    
    for prompt_type, prompt_data in by_prompt.items():
        by_rate = prompt_data.get('by_tool_success_rate', {})
        
        for rate, rate_data in by_rate.items():
            by_diff = rate_data.get('by_difficulty', {})
            
            for difficulty, diff_data in by_diff.items():
                by_task = diff_data.get('by_task_type', {})
                
                for task_type, task_data in by_task.items():
                    # 创建行数据
                    row = {
                        'model': model_name,
                        'prompt_type': prompt_type,
                        'tool_success_rate': float(rate),
                        'difficulty': difficulty,
                        'task_type': task_type,
                        'total': task_data.get('total', 0),
                        'success': task_data.get('success', 0),
                        'partial': task_data.get('partial', 0),
                        'failed': task_data.get('failed', 0),
                        'success_rate': task_data.get('success_rate', 0),
                        'avg_execution_time': task_data.get('avg_execution_time', 0),
                        'avg_tool_calls': task_data.get('avg_tool_calls', 0),
                        'tool_coverage_rate': task_data.get('tool_coverage_rate', 0),
                        'timestamp': datetime.now().isoformat()
                    }
                    rows.append(row)

print(f'✅ 展平数据完成，共{len(rows)}条记录')

# 写入CSV文件
if rows:
    output_file = output_dir / f'test_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    
    print(f'✅ 成功保存到: {output_file}')
    print(f'  - 文件大小: {output_file.stat().st_size / 1024:.1f} KB')
    
    # 显示摘要
    print('\n📊 数据摘要:')
    model_totals = {}
    for row in rows:
        model = row['model']
        if model not in model_totals:
            model_totals[model] = 0
        model_totals[model] += row['total']
    
    for model, total in sorted(model_totals.items()):
        print(f'  {model}: {total}个测试')
else:
    print('⚠️ 没有数据可转换')
