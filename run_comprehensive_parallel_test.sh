#!/bin/bash
#
# 综合并行测试脚本
# 展示多种并行策略的组合使用
#

echo "=========================================="
echo "综合并行测试脚本"
echo "展示框架集成的所有并行能力"
echo "=========================================="

# 配置参数
NUM_INSTANCES=${NUM_INSTANCES:-10}
DIFFICULTY=${DIFFICULTY:-easy}
TASK_TYPES=${TASK_TYPES:-simple_task,basic_task}

echo ""
echo "测试配置:"
echo "  实例数: $NUM_INSTANCES"
echo "  难度: $DIFFICULTY"  
echo "  任务类型: $TASK_TYPES"
echo ""

# 1. Azure模型 - 多prompt并行
echo "=========================================="
echo "1. Azure模型多Prompt并行测试"
echo "=========================================="
echo "模型: gpt-4o-mini"
echo "策略: 所有prompt types同时并行（高并发）"
echo ""

python smart_batch_runner.py \
  --model gpt-4o-mini \
  --prompt-types baseline,cot,optimal \
  --task-types "$TASK_TYPES" \
  --num-instances $NUM_INSTANCES \
  --prompt-parallel \
  --adaptive \
  --no-save-logs &

AZURE_PID=$!
echo "Azure测试已启动 (PID: $AZURE_PID)"

# 2. IdealLab模型 - 多prompt并行（使用不同API keys）
echo ""
echo "=========================================="
echo "2. IdealLab模型多Prompt并行测试"
echo "=========================================="
echo "模型: qwen2.5-3b-instruct"
echo "策略: 每个prompt type使用不同API key并行"
echo "  baseline -> API Key 1"
echo "  cot -> API Key 2"
echo "  optimal -> API Key 3"
echo ""

python smart_batch_runner.py \
  --model qwen2.5-3b-instruct \
  --prompt-types baseline,cot,optimal \
  --task-types "$TASK_TYPES" \
  --num-instances $NUM_INSTANCES \
  --prompt-parallel \
  --adaptive \
  --no-save-logs &

IDEALAB_PID=$!
echo "IdealLab测试已启动 (PID: $IDEALAB_PID)"

# 3. User Azure模型测试
echo ""
echo "=========================================="
echo "3. User Azure模型测试"
echo "=========================================="
echo "模型: gpt-5-nano"
echo "策略: 中等并发参数"
echo ""

python smart_batch_runner.py \
  --model gpt-5-nano \
  --prompt-types baseline \
  --task-types "$TASK_TYPES" \
  --num-instances $NUM_INSTANCES \
  --adaptive \
  --no-save-logs &

USER_AZURE_PID=$!
echo "User Azure测试已启动 (PID: $USER_AZURE_PID)"

# 等待所有测试完成
echo ""
echo "=========================================="
echo "等待所有测试完成..."
echo "=========================================="

# 监控进度
while true; do
    if ! kill -0 $AZURE_PID 2>/dev/null && \
       ! kill -0 $IDEALAB_PID 2>/dev/null && \
       ! kill -0 $USER_AZURE_PID 2>/dev/null; then
        break
    fi
    
    echo -n "."
    sleep 5
done

echo ""
echo ""
echo "=========================================="
echo "✅ 所有测试完成！"
echo "=========================================="

# 显示统计
echo ""
echo "查看数据库统计:"
python -c "
import json
from pathlib import Path

db_path = Path('pilot_bench_cumulative_results/master_database.json')
if db_path.exists():
    with open(db_path) as f:
        db = json.load(f)
    
    print(f'总测试数: {db.get(\"summary\", {}).get(\"total_tests\", 0)}')
    
    # 显示每个模型的统计
    if 'models' in db:
        for model in ['gpt-4o-mini', 'qwen2.5-3b-instruct', 'gpt-5-nano']:
            if model in db['models']:
                total = db['models'][model].get('overall_stats', {}).get('total', 0)
                success = db['models'][model].get('overall_stats', {}).get('success', 0)
                print(f'{model}: {success}/{total} 成功')
"

echo ""
echo "=========================================="
echo "测试完成时间: $(date)"
echo "=========================================="