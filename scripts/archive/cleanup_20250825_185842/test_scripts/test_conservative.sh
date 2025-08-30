#!/bin/bash

# 保守的测试配置脚本
echo "运行保守配置的测试..."

# 设置环境变量
export STORAGE_FORMAT=json
export PYTHONFAULTHANDLER=1
export PYTHONUNBUFFERED=1

# 使用低并发配置
echo "测试单个模型：qwen2.5-7b-instruct"
KMP_DUPLICATE_LIB_OK=TRUE python smart_batch_runner.py \
    --model qwen2.5-7b-instruct \
    --deployment qwen-key0 \
    --prompt-types optimal \
    --difficulty easy \
    --task-types simple_task \
    --num-instances 1 \
    --max-workers 5 \
    --tool-success-rate 0.8 \
    --batch-commit \
    --checkpoint-interval 5 \
    --ai-classification \
    --no-adaptive \
    --qps 10

echo "测试完成"