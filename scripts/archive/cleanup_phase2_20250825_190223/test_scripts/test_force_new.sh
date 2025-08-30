#!/bin/bash

# 强制运行新测试（使用不同的tool_success_rate以避免跳过）

echo "======================================"
echo "强制新测试 - 捕获详细输出"
echo "======================================"
echo ""

# 设置环境变量
export PYTHONFAULTHANDLER=1
export PYTHONUNBUFFERED=1
export STORAGE_FORMAT=json

# 使用唯一的tool_success_rate值以避免"已完成"
UNIQUE_RATE="0.$(date +%N | cut -c1-4)"
echo "使用唯一的tool_success_rate: $UNIQUE_RATE"
echo ""

# 创建日志目录
LOG_DIR="logs/debug_force_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"

echo "日志目录: $LOG_DIR"
echo ""

# 测试完整输出（不带--silent和--no-save-logs）
echo "运行完整输出模式..."
echo ""

python smart_batch_runner.py \
    --model gpt-4o-mini \
    --prompt-types baseline \
    --difficulty easy \
    --task-types simple_task \
    --num-instances 1 \
    --max-workers 1 \
    --tool-success-rate "$UNIQUE_RATE" \
    --batch-commit \
    --checkpoint-interval 1 \
    --ai-classification \
    2>&1 | tee "$LOG_DIR/full_output.log"

echo ""
echo "======================================"
echo "测试完成"
echo "======================================"
echo ""
echo "输出行数: $(wc -l < "$LOG_DIR/full_output.log")"
echo ""
echo "前20行:"
head -20 "$LOG_DIR/full_output.log"
echo ""
echo "后20行:"
tail -20 "$LOG_DIR/full_output.log"