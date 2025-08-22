#!/bin/bash

# 快速重新运行丢失的DeepSeek缺陷测试数据
# 利用6个并行Azure实例，每个跑不同的缺陷类型

echo "🔄 重新运行丢失的DeepSeek缺陷测试数据"
echo "利用6个Azure并行实例快速完成"
echo ""

# 6个并行实例
DEEPSEEK_INSTANCES=(
    "DeepSeek-V3-0324"      # V3原始实例
    "deepseek-v3-0324-2"    # V3实例2
    "deepseek-v3-0324-3"    # V3实例3
    "DeepSeek-R1-0528"      # R1原始实例
    "deepseek-r1-0528-2"    # R1实例2
    "deepseek-r1-0528-3"    # R1实例3
)

# 7种缺陷类型分配到6个实例（更均匀分配）
FLAW_ASSIGNMENTS=(
    "flawed_sequence_disorder"                              # 实例1: 1种
    "flawed_tool_misuse"                                    # 实例2: 1种
    "flawed_parameter_error"                                # 实例3: 1种
    "flawed_missing_step"                                   # 实例4: 1种
    "flawed_redundant_operations"                           # 实例5: 1种
    "flawed_logical_inconsistency,flawed_semantic_drift"    # 实例6: 2种
)

echo "分配方案:"
for i in "${!DEEPSEEK_INSTANCES[@]}"; do
    echo "  ${DEEPSEEK_INSTANCES[$i]}: ${FLAW_ASSIGNMENTS[$i]}"
done
echo ""

pids=()
start_time=$(date +%s)

# 并行启动4个实例
for i in "${!DEEPSEEK_INSTANCES[@]}"; do
    model="${DEEPSEEK_INSTANCES[$i]}"
    flaws="${FLAW_ASSIGNMENTS[$i]}"
    
    echo "🚀 启动 $model 测试缺陷: $flaws"
    
    python smart_batch_runner.py \
        --model "$model" \
        --prompt-types "$flaws" \
        --difficulty easy \
        --task-types all \
        --num-instances 20 \
        --max-workers 100 \
        --adaptive \
        --prompt-parallel \
        --batch-commit \
        --checkpoint-interval 20 \
        --ai-classification \
        --save-logs &
    
    pids+=($!)
    sleep 2  # 避免瞬时峰值
done

echo ""
echo "⏳ 等待所有实例完成..."
echo "预计时间: 20-30分钟 (相比原来4小时的90%减少)"

# 等待所有进程完成
success_count=0
for i in "${!pids[@]}"; do
    pid=${pids[$i]}
    model=${DEEPSEEK_INSTANCES[$i]}
    
    if wait "$pid"; then
        echo "✅ $model 完成"
        ((success_count++))
    else
        echo "❌ $model 失败"
    fi
done

end_time=$(date +%s)
duration=$((end_time - start_time))

echo ""
echo "📊 恢复结果:"
echo "  成功: $success_count/6 实例"
echo "  总耗时: $((duration/60))分钟$((duration%60))秒"
echo ""

if [ "$success_count" -eq 6 ]; then
    echo "🎉 DeepSeek缺陷测试数据恢复完成！"
    echo "现在可以继续系统化测试流程"
else
    echo "⚠️  部分实例失败，请检查日志"
fi