#!/bin/bash

# 自动生成的重测脚本 - 基于现有进度
# 生成时间: 2025-08-14T17:41:52.668855
# 涉及模型: 10

set -e

echo "开始基于现有进度的自动重测..."
echo "涉及 10 个模型"
echo ""


echo "=== 处理模型: DeepSeek-V3-0324 ==="
echo "未完成测试: 3 个配置"

echo "  配置 1: baseline / simple_task"
echo "    需要补充: 18 个测试"

python smart_batch_runner.py \
    --model "DeepSeek-V3-0324" \
    --prompt-types "baseline" \
    --difficulty "easy" \
    --task-types "simple_task" \
    --num-instances 18 \
    --tool-success-rate 0.8 \
    --max-workers 2 \
    --adaptive \
    --no-save-logs

echo ""

echo "  配置 2: baseline / basic_task"
echo "    需要补充: 20 个测试"

python smart_batch_runner.py \
    --model "DeepSeek-V3-0324" \
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
    --model "DeepSeek-V3-0324" \
    --prompt-types "cot" \
    --difficulty "easy" \
    --task-types "simple_task" \
    --num-instances 20 \
    --tool-success-rate 0.8 \
    --max-workers 2 \
    --adaptive \
    --no-save-logs

echo ""

echo "=== 处理模型: DeepSeek-R1-0528 ==="
echo "未完成测试: 3 个配置"

echo "  配置 4: baseline / simple_task"
echo "    需要补充: 20 个测试"

python smart_batch_runner.py \
    --model "DeepSeek-R1-0528" \
    --prompt-types "baseline" \
    --difficulty "easy" \
    --task-types "simple_task" \
    --num-instances 20 \
    --tool-success-rate 0.8 \
    --max-workers 2 \
    --adaptive \
    --no-save-logs

echo ""

echo "  配置 5: baseline / basic_task"
echo "    需要补充: 20 个测试"

python smart_batch_runner.py \
    --model "DeepSeek-R1-0528" \
    --prompt-types "baseline" \
    --difficulty "easy" \
    --task-types "basic_task" \
    --num-instances 20 \
    --tool-success-rate 0.8 \
    --max-workers 2 \
    --adaptive \
    --no-save-logs

echo ""

echo "  配置 6: cot / simple_task"
echo "    需要补充: 20 个测试"

python smart_batch_runner.py \
    --model "DeepSeek-R1-0528" \
    --prompt-types "cot" \
    --difficulty "easy" \
    --task-types "simple_task" \
    --num-instances 20 \
    --tool-success-rate 0.8 \
    --max-workers 2 \
    --adaptive \
    --no-save-logs

echo ""

echo "=== 处理模型: qwen2.5-72b-instruct ==="
echo "未完成测试: 3 个配置"

echo "  配置 7: baseline / simple_task"
echo "    需要补充: 5 个测试"

python smart_batch_runner.py \
    --model "qwen2.5-72b-instruct" \
    --prompt-types "baseline" \
    --difficulty "easy" \
    --task-types "simple_task" \
    --num-instances 5 \
    --tool-success-rate 0.8 \
    --max-workers 2 \
    --adaptive \
    --no-save-logs

echo ""

echo "  配置 8: baseline / basic_task"
echo "    需要补充: 20 个测试"

python smart_batch_runner.py \
    --model "qwen2.5-72b-instruct" \
    --prompt-types "baseline" \
    --difficulty "easy" \
    --task-types "basic_task" \
    --num-instances 20 \
    --tool-success-rate 0.8 \
    --max-workers 2 \
    --adaptive \
    --no-save-logs

echo ""

echo "  配置 9: cot / simple_task"
echo "    需要补充: 20 个测试"

python smart_batch_runner.py \
    --model "qwen2.5-72b-instruct" \
    --prompt-types "cot" \
    --difficulty "easy" \
    --task-types "simple_task" \
    --num-instances 20 \
    --tool-success-rate 0.8 \
    --max-workers 2 \
    --adaptive \
    --no-save-logs

echo ""

echo "=== 处理模型: qwen2.5-32b-instruct ==="
echo "未完成测试: 3 个配置"

echo "  配置 10: baseline / simple_task"
echo "    需要补充: 20 个测试"

python smart_batch_runner.py \
    --model "qwen2.5-32b-instruct" \
    --prompt-types "baseline" \
    --difficulty "easy" \
    --task-types "simple_task" \
    --num-instances 20 \
    --tool-success-rate 0.8 \
    --max-workers 2 \
    --adaptive \
    --no-save-logs

echo ""

echo "  配置 11: baseline / basic_task"
echo "    需要补充: 20 个测试"

python smart_batch_runner.py \
    --model "qwen2.5-32b-instruct" \
    --prompt-types "baseline" \
    --difficulty "easy" \
    --task-types "basic_task" \
    --num-instances 20 \
    --tool-success-rate 0.8 \
    --max-workers 2 \
    --adaptive \
    --no-save-logs

echo ""

echo "  配置 12: cot / simple_task"
echo "    需要补充: 20 个测试"

python smart_batch_runner.py \
    --model "qwen2.5-32b-instruct" \
    --prompt-types "cot" \
    --difficulty "easy" \
    --task-types "simple_task" \
    --num-instances 20 \
    --tool-success-rate 0.8 \
    --max-workers 2 \
    --adaptive \
    --no-save-logs

echo ""

echo "=== 处理模型: qwen2.5-14b-instruct ==="
echo "未完成测试: 3 个配置"

echo "  配置 13: baseline / simple_task"
echo "    需要补充: 20 个测试"

python smart_batch_runner.py \
    --model "qwen2.5-14b-instruct" \
    --prompt-types "baseline" \
    --difficulty "easy" \
    --task-types "simple_task" \
    --num-instances 20 \
    --tool-success-rate 0.8 \
    --max-workers 2 \
    --adaptive \
    --no-save-logs

echo ""

echo "  配置 14: baseline / basic_task"
echo "    需要补充: 20 个测试"

python smart_batch_runner.py \
    --model "qwen2.5-14b-instruct" \
    --prompt-types "baseline" \
    --difficulty "easy" \
    --task-types "basic_task" \
    --num-instances 20 \
    --tool-success-rate 0.8 \
    --max-workers 2 \
    --adaptive \
    --no-save-logs

echo ""

echo "  配置 15: cot / simple_task"
echo "    需要补充: 20 个测试"

python smart_batch_runner.py \
    --model "qwen2.5-14b-instruct" \
    --prompt-types "cot" \
    --difficulty "easy" \
    --task-types "simple_task" \
    --num-instances 20 \
    --tool-success-rate 0.8 \
    --max-workers 2 \
    --adaptive \
    --no-save-logs

echo ""

echo "=== 处理模型: qwen2.5-7b-instruct ==="
echo "未完成测试: 3 个配置"

echo "  配置 16: baseline / simple_task"
echo "    需要补充: 20 个测试"

python smart_batch_runner.py \
    --model "qwen2.5-7b-instruct" \
    --prompt-types "baseline" \
    --difficulty "easy" \
    --task-types "simple_task" \
    --num-instances 20 \
    --tool-success-rate 0.8 \
    --max-workers 2 \
    --adaptive \
    --no-save-logs

echo ""

echo "  配置 17: baseline / basic_task"
echo "    需要补充: 20 个测试"

python smart_batch_runner.py \
    --model "qwen2.5-7b-instruct" \
    --prompt-types "baseline" \
    --difficulty "easy" \
    --task-types "basic_task" \
    --num-instances 20 \
    --tool-success-rate 0.8 \
    --max-workers 2 \
    --adaptive \
    --no-save-logs

echo ""

echo "  配置 18: cot / simple_task"
echo "    需要补充: 20 个测试"

python smart_batch_runner.py \
    --model "qwen2.5-7b-instruct" \
    --prompt-types "cot" \
    --difficulty "easy" \
    --task-types "simple_task" \
    --num-instances 20 \
    --tool-success-rate 0.8 \
    --max-workers 2 \
    --adaptive \
    --no-save-logs

echo ""

echo "=== 处理模型: qwen2.5-3b-instruct ==="
echo "未完成测试: 3 个配置"

echo "  配置 19: baseline / simple_task"
echo "    需要补充: 20 个测试"

python smart_batch_runner.py \
    --model "qwen2.5-3b-instruct" \
    --prompt-types "baseline" \
    --difficulty "easy" \
    --task-types "simple_task" \
    --num-instances 20 \
    --tool-success-rate 0.8 \
    --max-workers 2 \
    --adaptive \
    --no-save-logs

echo ""

echo "  配置 20: baseline / basic_task"
echo "    需要补充: 20 个测试"

python smart_batch_runner.py \
    --model "qwen2.5-3b-instruct" \
    --prompt-types "baseline" \
    --difficulty "easy" \
    --task-types "basic_task" \
    --num-instances 20 \
    --tool-success-rate 0.8 \
    --max-workers 2 \
    --adaptive \
    --no-save-logs

echo ""

echo "  配置 21: cot / simple_task"
echo "    需要补充: 20 个测试"

python smart_batch_runner.py \
    --model "qwen2.5-3b-instruct" \
    --prompt-types "cot" \
    --difficulty "easy" \
    --task-types "simple_task" \
    --num-instances 20 \
    --tool-success-rate 0.8 \
    --max-workers 2 \
    --adaptive \
    --no-save-logs

echo ""

echo "=== 处理模型: Llama-3.3-70B-Instruct ==="
echo "未完成测试: 3 个配置"

echo "  配置 22: baseline / simple_task"
echo "    需要补充: 20 个测试"

python smart_batch_runner.py \
    --model "Llama-3.3-70B-Instruct" \
    --prompt-types "baseline" \
    --difficulty "easy" \
    --task-types "simple_task" \
    --num-instances 20 \
    --tool-success-rate 0.8 \
    --max-workers 2 \
    --adaptive \
    --no-save-logs

echo ""

echo "  配置 23: baseline / basic_task"
echo "    需要补充: 20 个测试"

python smart_batch_runner.py \
    --model "Llama-3.3-70B-Instruct" \
    --prompt-types "baseline" \
    --difficulty "easy" \
    --task-types "basic_task" \
    --num-instances 20 \
    --tool-success-rate 0.8 \
    --max-workers 2 \
    --adaptive \
    --no-save-logs

echo ""

echo "  配置 24: cot / simple_task"
echo "    需要补充: 20 个测试"

python smart_batch_runner.py \
    --model "Llama-3.3-70B-Instruct" \
    --prompt-types "cot" \
    --difficulty "easy" \
    --task-types "simple_task" \
    --num-instances 20 \
    --tool-success-rate 0.8 \
    --max-workers 2 \
    --adaptive \
    --no-save-logs

echo ""

echo "=== 处理模型: llama-4-scout-17b ==="
echo "未完成测试: 3 个配置"

echo "  配置 25: baseline / simple_task"
echo "    需要补充: 20 个测试"

python smart_batch_runner.py \
    --model "llama-4-scout-17b" \
    --prompt-types "baseline" \
    --difficulty "easy" \
    --task-types "simple_task" \
    --num-instances 20 \
    --tool-success-rate 0.8 \
    --max-workers 2 \
    --adaptive \
    --no-save-logs

echo ""

echo "  配置 26: baseline / basic_task"
echo "    需要补充: 20 个测试"

python smart_batch_runner.py \
    --model "llama-4-scout-17b" \
    --prompt-types "baseline" \
    --difficulty "easy" \
    --task-types "basic_task" \
    --num-instances 20 \
    --tool-success-rate 0.8 \
    --max-workers 2 \
    --adaptive \
    --no-save-logs

echo ""

echo "  配置 27: cot / simple_task"
echo "    需要补充: 20 个测试"

python smart_batch_runner.py \
    --model "llama-4-scout-17b" \
    --prompt-types "cot" \
    --difficulty "easy" \
    --task-types "simple_task" \
    --num-instances 20 \
    --tool-success-rate 0.8 \
    --max-workers 2 \
    --adaptive \
    --no-save-logs

echo ""

echo "=== 处理模型: gpt-4o-mini ==="
echo "未完成测试: 4 个配置"

echo "  配置 28: baseline / simple_task"
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

echo "  配置 29: baseline / basic_task"
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

echo "  配置 30: cot / simple_task"
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

echo "  配置 31: optimal / simple_task"
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
echo "总共处理了 31 个测试配置"

# 生成状态报告
echo ""
echo "=== 最终状态报告 ==="
python auto_failure_maintenance_system.py status
