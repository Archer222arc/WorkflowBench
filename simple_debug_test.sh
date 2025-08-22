#!/bin/bash

# 简单的调试测试脚本
# 直接运行测试并捕获所有输出

echo "========================================="
echo "简单调试测试 - 捕获完整输出"
echo "========================================="

# 设置环境变量
export PYTHONFAULTHANDLER=1
export PYTHONUNBUFFERED=1
export STORAGE_FORMAT=parquet
export PYTHONVERBOSE=1  # 显示导入信息

# 创建日志目录
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="logs/debug_simple_${TIMESTAMP}"
mkdir -p "$LOG_DIR"

echo "环境变量:"
echo "  STORAGE_FORMAT=$STORAGE_FORMAT"
echo "  PYTHONFAULTHANDLER=$PYTHONFAULTHANDLER"
echo "  PYTHONUNBUFFERED=$PYTHONUNBUFFERED"
echo ""

# 运行测试并捕获所有输出
echo "运行测试..."
python -u smart_batch_runner.py \
    --model gpt-4o-mini \
    --prompt-types baseline \
    --difficulty easy \
    --task-types simple_task \
    --num-instances 1 \
    --max-workers 1 \
    --tool-success-rate 0.8 \
    --batch-commit \
    --checkpoint-interval 1 \
    --no-save-logs \
    --no-adaptive \
    --qps 5 \
    2>&1 | tee "$LOG_DIR/complete_output.log"

# 检查退出码
EXITCODE=$?
echo ""
echo "退出码: $EXITCODE"

# 检查数据保存
echo ""
echo "检查数据保存..."
python -c "
import json
from pathlib import Path
import pandas as pd

# 检查JSON
json_path = Path('pilot_bench_cumulative_results/master_database.json')
if json_path.exists():
    with open(json_path, 'r') as f:
        db = json.load(f)
    print(f'JSON数据库: {db[\"summary\"][\"total_tests\"]} 个测试')
    
    # 检查gpt-4o-mini
    if 'gpt-4o-mini' in db['models']:
        model_data = db['models']['gpt-4o-mini']
        total = model_data['overall_stats'].get('total_tests', 0)
        print(f'gpt-4o-mini: {total} 个测试')

# 检查Parquet
parquet_path = Path('pilot_bench_parquet_data/test_results.parquet')
if parquet_path.exists():
    df = pd.read_parquet(parquet_path)
    gpt_df = df[df['model'] == 'gpt-4o-mini']
    print(f'Parquet中gpt-4o-mini: {len(gpt_df)} 条记录')
" | tee -a "$LOG_DIR/data_check.log"

echo ""
echo "日志保存在: $LOG_DIR"
echo ""
echo "关键信息过滤:"
grep -E "Parquet|JSON|保存|Save|Commit|Error|WARNING|成功|失败" "$LOG_DIR/complete_output.log" | head -20