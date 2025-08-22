#!/bin/bash

# 5.4 快速测试脚本 - 验证优化效果

echo "=========================================="
echo "5.4 工具可靠性测试 - 快速验证"
echo "测试qwen2.5-3b-instruct的优化效果"
echo "=========================================="

# 测试参数
MODEL="qwen2.5-3b-instruct"
PROMPT_TYPE="optimal"
DIFFICULTY="easy"
TASK_TYPES="simple_task"  # 只测试simple_task以加快速度
NUM_INSTANCES=2  # 减少实例数

echo ""
echo "📊 测试配置："
echo "- 模型: $MODEL"
echo "- Prompt: $PROMPT_TYPE"
echo "- 难度: $DIFFICULTY"
echo "- 任务: $TASK_TYPES"
echo "- 实例数: $NUM_INSTANCES"
echo ""

# 测试3个tool_success_rate，验证是否分配到不同的keys
echo "🚀 启动并行测试..."

# 0.9 -> 应该使用key0
echo "启动 tool_success_rate=0.9 测试..."
python ultra_parallel_runner.py \
    --model "$MODEL" \
    --prompt-types "$PROMPT_TYPE" \
    --difficulty "$DIFFICULTY" \
    --task-types "$TASK_TYPES" \
    --num-instances "$NUM_INSTANCES" \
    --tool-success-rate 0.9 \
    --rate-mode adaptive \
    --silent 2>&1 | grep -E "(Using qwen-key|Creating.*shards|Running shard)" &

pid1=$!

sleep 2

# 0.7 -> 应该使用key2
echo "启动 tool_success_rate=0.7 测试..."
python ultra_parallel_runner.py \
    --model "$MODEL" \
    --prompt-types "$PROMPT_TYPE" \
    --difficulty "$DIFFICULTY" \
    --task-types "$TASK_TYPES" \
    --num-instances "$NUM_INSTANCES" \
    --tool-success-rate 0.7 \
    --rate-mode adaptive \
    --silent 2>&1 | grep -E "(Using qwen-key|Creating.*shards|Running shard)" &

pid2=$!

sleep 2

# 0.6 -> 应该使用key0（轮询）
echo "启动 tool_success_rate=0.6 测试..."
python ultra_parallel_runner.py \
    --model "$MODEL" \
    --prompt-types "$PROMPT_TYPE" \
    --difficulty "$DIFFICULTY" \
    --task-types "$TASK_TYPES" \
    --num-instances "$NUM_INSTANCES" \
    --tool-success-rate 0.6 \
    --rate-mode adaptive \
    --silent 2>&1 | grep -E "(Using qwen-key|Creating.*shards|Running shard)" &

pid3=$!

echo ""
echo "⏳ 等待测试完成..."
wait $pid1 $pid2 $pid3

echo ""
echo "✅ 测试完成"
echo ""
echo "查看结果："
echo "python view_5_4_results.py"