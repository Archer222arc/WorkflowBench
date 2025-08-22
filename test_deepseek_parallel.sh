#!/bin/bash

# 测试新的DeepSeek并行部署
echo "🧪 测试新的DeepSeek并行部署..."

# 定义并行模型 - 6个实例
DEEPSEEK_MODELS=(
    "DeepSeek-V3-0324"      # V3原始实例（无后缀）
    "deepseek-v3-0324-2"    # V3并行实例2
    "deepseek-v3-0324-3"    # V3并行实例3
    "DeepSeek-R1-0528"      # R1原始实例（无后缀）
    "deepseek-r1-0528-2"    # R1并行实例2
    "deepseek-r1-0528-3"    # R1并行实例3
)

echo "将测试以下模型:"
for model in "${DEEPSEEK_MODELS[@]}"; do
    echo "  - $model"
done
echo ""

# 并行测试每个模型
pids=()

for model in "${DEEPSEEK_MODELS[@]}"; do
    echo "🚀 启动 $model 测试..."
    
    # 简单的1个测试验证连通性
    python smart_batch_runner.py \
        --model "$model" \
        --prompt-types baseline \
        --difficulty easy \
        --task-types simple_task \
        --num-instances 1 \
        --no-save-logs \
        --silent &
    
    pids+=($!)
    
    # 延迟避免瞬时峰值
    sleep 1
done

echo ""
echo "⏳ 等待所有测试完成..."

# 等待所有进程并检查结果
success_count=0
total_count=${#DEEPSEEK_MODELS[@]}

for i in "${!pids[@]}"; do
    pid=${pids[$i]}
    model=${DEEPSEEK_MODELS[$i]}
    
    if wait "$pid"; then
        echo "✅ $model: 测试成功"
        ((success_count++))
    else
        echo "❌ $model: 测试失败"
    fi
done

echo ""
echo "📊 测试结果:"
echo "  成功: $success_count/$total_count"
echo "  失败: $((total_count - success_count))/$total_count"

if [ "$success_count" -eq "$total_count" ]; then
    echo ""
    echo "🎉 所有DeepSeek并行实例测试成功！"
    echo "现在可以使用 run_deepseek_parallel_test() 函数进行加速测试"
    exit 0
else
    echo ""
    echo "⚠️  部分实例测试失败，请检查Azure部署配置"
    exit 1
fi