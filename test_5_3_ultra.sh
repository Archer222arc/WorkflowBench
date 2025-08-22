#!/bin/bash

# ============================================
# 5.3 超并行测试 - 小规模验证
# ============================================

echo "============================================"
echo "5.3 超并行测试 - qwen2.5-7b-instruct"
echo "测试3种缺陷类型，每种2个实例"
echo "============================================"
echo ""

# 设置存储格式
export STORAGE_FORMAT="${STORAGE_FORMAT:-parquet}"
echo "存储格式: $STORAGE_FORMAT"

# 运行超并行测试
echo "启动超并行测试..."
python ultra_parallel_runner.py \
    --model "qwen2.5-7b-instruct" \
    --prompt-types "flawed_sequence_disorder,flawed_tool_misuse,flawed_parameter_error" \
    --difficulty "easy" \
    --task-types "simple_task" \
    --num-instances 2 \
    --tool-success-rate 0.8 \
    --rate-mode "fixed" \
    --max-workers 10 \
    --silent

echo ""
echo "测试完成，检查数据更新..."
python generate_5_3_report.py | grep -E "(qwen2.5-7b-instruct|总计)"