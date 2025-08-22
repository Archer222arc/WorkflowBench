#!/bin/bash
#
# 快速测试脚本 - 用于验证功能
#

echo "=========================================="
echo "快速功能测试"
echo "=========================================="
echo ""

# 测试1: Azure模型多prompt并行
echo "1. 测试Azure模型多prompt并行..."
python smart_batch_runner.py \
  --model gpt-4o-mini \
  --prompt-types baseline,cot \
  --task-types simple_task \
  --num-instances 1 \
  --prompt-parallel \
  --no-save-logs \
  --silent

if [ $? -eq 0 ]; then
    echo "✅ Azure模型测试通过"
else
    echo "❌ Azure模型测试失败"
fi

echo ""

# 测试2: IdealLab模型多API key并行
echo "2. 测试IdealLab模型多API key并行..."
python smart_batch_runner.py \
  --model qwen2.5-3b-instruct \
  --prompt-types all \
  --task-types simple_task \
  --num-instances 1 \
  --prompt-parallel \
  --no-save-logs

if [ $? -eq 0 ]; then
    echo "✅ IdealLab模型测试通过"
else
    echo "❌ IdealLab模型测试失败"
fi

echo ""
echo "=========================================="
echo "快速测试完成"
echo "=========================================="