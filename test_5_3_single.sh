#!/bin/bash

# ============================================
# 5.3 缺陷工作流测试 - 单模型测试脚本
# ============================================

echo "============================================"
echo "5.3 缺陷工作流测试 - 单模型 (DeepSeek-V3-0324)"
echo "============================================"
echo ""

# 设置存储格式
export STORAGE_FORMAT="${STORAGE_FORMAT:-parquet}"
echo "存储格式: $STORAGE_FORMAT"

# 测试一个缺陷类型的一个小实例
echo "测试: flawed_sequence_disorder, 2个实例"
python smart_batch_runner.py \
    --model "DeepSeek-V3-0324" \
    --prompt-types "flawed_sequence_disorder" \
    --difficulty "easy" \
    --task-types "simple_task" \
    --num-instances 2 \
    --tool-success-rate 0.8 \
    --max-workers 5 \
    --batch-commit \
    --checkpoint-interval 1 \
    --no-adaptive \
    --qps 5 \
    --no-save-logs 2>&1 | tail -30

echo ""
echo "检查数据更新..."
python monitor_parquet_updates.py | grep -E "(今天的记录|最后修改|DeepSeek)"

echo ""
echo "检查缺陷测试数据..."
python -c "
import json
from pathlib import Path

db_path = Path('pilot_bench_cumulative_results/master_database.json')
with open(db_path, 'r') as f:
    db = json.load(f)

model = 'DeepSeek-V3-0324'
if model in db['models']:
    model_data = db['models'][model]
    if 'by_prompt_type' in model_data and 'flawed_sequence_disorder' in model_data['by_prompt_type']:
        flaw_data = model_data['by_prompt_type']['flawed_sequence_disorder']
        print(f'DeepSeek-V3-0324 flawed_sequence_disorder 数据:')
        if 'by_tool_success_rate' in flaw_data and '0.8' in flaw_data['by_tool_success_rate']:
            rate_data = flaw_data['by_tool_success_rate']['0.8']
            if 'by_difficulty' in rate_data and 'easy' in rate_data['by_difficulty']:
                diff_data = rate_data['by_difficulty']['easy']
                if 'by_task_type' in diff_data and 'simple_task' in diff_data['by_task_type']:
                    task_data = diff_data['by_task_type']['simple_task']
                    print(f'  total: {task_data.get(\"total\", 0)}')
                    print(f'  successful: {task_data.get(\"successful\", 0)}')
                    print(f'  partial: {task_data.get(\"partial\", 0)}')
                    print(f'  failed: {task_data.get(\"failed\", 0)}')
                    print(f'  success_rate: {task_data.get(\"success_rate\", 0):.1%}')
                    print(f'  partial_rate: {task_data.get(\"partial_rate\", 0):.1%}')
                    print(f'  weighted_success_score: {task_data.get(\"weighted_success_score\", 0):.3f}')
"