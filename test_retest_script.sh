#!/bin/bash

# 自动生成的重测脚本 - 基于现有进度
# 生成时间: 2025-08-14T17:22:38.840815
# 涉及模型: 1

set -e

echo "开始基于现有进度的自动重测..."
echo "涉及 1 个模型"
echo ""


echo "=== 处理模型: gpt-4o-mini ==="
echo "未完成测试: 4 个配置"

echo "  配置 1: baseline / simple_task"
echo "    需要补充: 20 个测试"

python smart_batch_runner.py \
    --model "gpt-4o-mini" \
    --prompt-types "baseline" \
    --difficulty "easy" \
    --task-types "simple_task" \
    --num-instances 20 \
    --tool-success-rate 0.8 \
    --max-workers 2 \
    --adaptive \
    --no-save-logs

echo ""

echo "  配置 2: baseline / basic_task"
echo "    需要补充: 20 个测试"

python smart_batch_runner.py \
    --model "gpt-4o-mini" \
    --prompt-types "baseline" \
    --difficulty "easy" \
    --task-types "basic_task" \
    --num-instances 20 \
    --tool-success-rate 0.8 \
    --max-workers 2 \
    --adaptive \
    --no-save-logs

echo ""

echo "  配置 3: cot / simple_task"
echo "    需要补充: 20 个测试"

python smart_batch_runner.py \
    --model "gpt-4o-mini" \
    --prompt-types "cot" \
    --difficulty "easy" \
    --task-types "simple_task" \
    --num-instances 20 \
    --tool-success-rate 0.8 \
    --max-workers 2 \
    --adaptive \
    --no-save-logs

echo ""

echo "  配置 4: optimal / simple_task"
echo "    需要补充: 20 个测试"

python smart_batch_runner.py \
    --model "gpt-4o-mini" \
    --prompt-types "optimal" \
    --difficulty "easy" \
    --task-types "simple_task" \
    --num-instances 20 \
    --tool-success-rate 0.8 \
    --max-workers 2 \
    --adaptive \
    --no-save-logs

echo ""

echo "重测完成！"
echo "总共处理了 4 个测试配置"

# 生成状态报告
echo ""
echo "=== 最终状态报告 ==="
python auto_failure_maintenance_system.py status
