#!/bin/bash

# 直接测试捕获smart_batch_runner的输出

echo "======================================"
echo "直接捕获smart_batch_runner输出测试"
echo "======================================"
echo ""

# 设置环境变量
export PYTHONFAULTHANDLER=1
export PYTHONUNBUFFERED=1
export STORAGE_FORMAT=json

# 创建日志目录
LOG_DIR="logs/debug_direct_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"

echo "日志目录: $LOG_DIR"
echo ""

# 测试1: 不带--silent和--no-save-logs
echo "测试1: 完整输出模式"
echo "运行命令:"
echo "python smart_batch_runner.py --model gpt-4o-mini --prompt-types baseline --difficulty easy --task-types simple_task --num-instances 1 --max-workers 1 --tool-success-rate 0.8 --batch-commit --checkpoint-interval 1 --ai-classification"
echo ""

python smart_batch_runner.py \
    --model gpt-4o-mini \
    --prompt-types baseline \
    --difficulty easy \
    --task-types simple_task \
    --num-instances 1 \
    --max-workers 1 \
    --tool-success-rate 0.8 \
    --batch-commit \
    --checkpoint-interval 1 \
    --ai-classification \
    2>&1 | tee "$LOG_DIR/test1_full_output.log"

echo ""
echo "输出保存到: $LOG_DIR/test1_full_output.log"
echo "行数: $(wc -l < "$LOG_DIR/test1_full_output.log")"

echo ""
echo "----------------------------------------"
echo ""

# 测试2: 带--no-save-logs但不带--silent
echo "测试2: no-save-logs模式"
echo "运行命令:"
echo "python smart_batch_runner.py --model gpt-4o-mini --prompt-types baseline --difficulty easy --task-types simple_task --num-instances 1 --max-workers 1 --tool-success-rate 0.8 --batch-commit --checkpoint-interval 1 --ai-classification --no-save-logs"
echo ""

python smart_batch_runner.py \
    --model gpt-4o-mini \
    --prompt-types baseline \
    --difficulty easy \
    --task-types simple_task \
    --num-instances 1 \
    --max-workers 1 \
    --tool-success-rate 0.8 \
    --batch-commit \
    --checkpoint-interval 1 \
    --ai-classification \
    --no-save-logs \
    2>&1 | tee "$LOG_DIR/test2_no_save_logs.log"

echo ""
echo "输出保存到: $LOG_DIR/test2_no_save_logs.log"
echo "行数: $(wc -l < "$LOG_DIR/test2_no_save_logs.log")"

echo ""
echo "----------------------------------------"
echo ""

# 测试3: 带--silent
echo "测试3: silent模式"
echo "运行命令:"
echo "python smart_batch_runner.py --model gpt-4o-mini --prompt-types baseline --difficulty easy --task-types simple_task --num-instances 1 --max-workers 1 --tool-success-rate 0.8 --batch-commit --checkpoint-interval 1 --ai-classification --no-save-logs --silent"
echo ""

python smart_batch_runner.py \
    --model gpt-4o-mini \
    --prompt-types baseline \
    --difficulty easy \
    --task-types simple_task \
    --num-instances 1 \
    --max-workers 1 \
    --tool-success-rate 0.8 \
    --batch-commit \
    --checkpoint-interval 1 \
    --ai-classification \
    --no-save-logs \
    --silent \
    2>&1 | tee "$LOG_DIR/test3_silent.log"

echo ""
echo "输出保存到: $LOG_DIR/test3_silent.log"
echo "行数: $(wc -l < "$LOG_DIR/test3_silent.log")"

echo ""
echo "======================================"
echo "测试完成"
echo "======================================"
echo ""
echo "比较三种模式的输出："
echo "1. 完整输出: $(wc -l < "$LOG_DIR/test1_full_output.log") 行"
echo "2. no-save-logs: $(wc -l < "$LOG_DIR/test2_no_save_logs.log") 行"
echo "3. silent: $(wc -l < "$LOG_DIR/test3_silent.log") 行"
echo ""
echo "查看日志："
echo "ls -la $LOG_DIR/"