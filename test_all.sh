#!/bin/bash
#
# 一键测试所有模型的所有prompt types
# 最简单的使用方式
#

# 默认配置
NUM_INSTANCES=${NUM_INSTANCES:-20}
MODELS=${MODELS:-"gpt-4o-mini qwen2.5-3b-instruct gpt-5-nano"}

echo "=========================================="
echo "一键测试脚本"
echo "测试所有模型的所有prompt types"
echo "=========================================="
echo ""
echo "配置:"
echo "  模型: $MODELS"
echo "  实例数: $NUM_INSTANCES"
echo "  Prompt类型: all (baseline, cot, optimal)"
echo "  任务类型: all"
echo ""

# 测试每个模型
for model in $MODELS; do
    echo "=========================================="
    echo "测试: $model"
    echo "=========================================="
    
    python smart_batch_runner.py \
        --model "$model" \
        --prompt-types all \
        --task-types all \
        --num-instances $NUM_INSTANCES \
        --prompt-parallel \
        --adaptive
    
    if [ $? -eq 0 ]; then
        echo "✅ $model 完成"
    else
        echo "❌ $model 失败"
    fi
    
    echo ""
done

echo "=========================================="
echo "测试完成"
echo "=========================================="

# 显示最终统计
python -c "
import json
from pathlib import Path

db_path = Path('pilot_bench_cumulative_results/master_database.json')
if db_path.exists():
    with open(db_path) as f:
        db = json.load(f)
    
    print('\n📊 测试统计:')
    print(f'总测试数: {db.get(\"summary\", {}).get(\"total_tests\", 0)}')
    
    if 'models' in db:
        print('\n各模型统计:')
        for model in sorted(db['models'].keys()):
            stats = db['models'][model].get('overall_stats', {})
            total = stats.get('total', 0)
            success = stats.get('success', 0)
            if total > 0:
                rate = (success / total * 100) if total > 0 else 0
                print(f'  {model}: {success}/{total} ({rate:.1f}%)')
"