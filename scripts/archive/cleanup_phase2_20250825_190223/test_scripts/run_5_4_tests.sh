#!/bin/bash

# 5.4 工具可靠性敏感性测试脚本
# 利用qwen优化策略并行测试不同的tool_success_rate

echo "=========================================="
echo "5.4 工具可靠性敏感性测试"
echo "利用qwen 3个API keys优化策略"
echo "生成时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

# 设置基础参数
MODELS=(
    "qwen2.5-72b-instruct"
    "qwen2.5-32b-instruct"
    "qwen2.5-14b-instruct"
    "qwen2.5-7b-instruct"
    "qwen2.5-3b-instruct"
)

# 测试配置
PROMPT_TYPE="optimal"
DIFFICULTY="easy"
TASK_TYPES="simple_task,basic_task,data_pipeline,api_integration,multi_stage_pipeline"
NUM_INSTANCES=20  # 每个任务类型20个实例

# 工具成功率配置（0.8已在5.1测试，这里测试其他3个）
TOOL_SUCCESS_RATES=(0.9 0.7 0.6)

echo ""
echo "📊 测试配置："
echo "- Prompt类型: $PROMPT_TYPE"
echo "- 难度: $DIFFICULTY"
echo "- 任务类型: 全部5种"
echo "- 每种任务: $NUM_INSTANCES 个实例"
echo "- 工具成功率: 90%, 70%, 60%"
echo ""

# 函数：运行单个模型的5.4测试
run_model_5_4_tests() {
    local model=$1
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🚀 开始测试模型: $model"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # 并行运行3个tool_success_rate（利用优化策略）
    # 0.9 -> key0, 0.7 -> key2, 0.6 -> key0（会自动分配）
    
    echo "启动并行测试..."
    
    for rate in "${TOOL_SUCCESS_RATES[@]}"; do
        echo ""
        echo "📍 启动 tool_success_rate=$rate 测试..."
        
        python ultra_parallel_runner.py \
            --model "$model" \
            --prompt-types "$PROMPT_TYPE" \
            --difficulty "$DIFFICULTY" \
            --task-types "$TASK_TYPES" \
            --num-instances "$NUM_INSTANCES" \
            --tool-success-rate "$rate" \
            --rate-mode adaptive \
            --silent &
        
        # 记录PID
        pid=$!
        echo "  PID: $pid"
        
        # 短暂延迟避免同时启动冲突
        sleep 5
    done
    
    echo ""
    echo "⏳ 等待所有测试完成..."
    wait
    
    echo "✅ $model 的5.4测试完成"
}

# 主执行流程
echo ""
echo "🎯 测试执行计划："
echo "1. 每个模型并行测试3个tool_success_rate"
echo "2. 利用qwen-key0, key1, key2智能分配"
echo "3. 预期性能提升: 3倍"
echo ""

# 询问用户选择
echo "请选择测试模式："
echo "1) 测试所有qwen模型"
echo "2) 测试单个模型（交互选择）"
echo "3) 快速测试（qwen2.5-72b，减少实例数）"
echo ""
read -p "请输入选择 (1-3): " choice

case $choice in
    1)
        echo ""
        echo "📦 开始测试所有qwen模型..."
        for model in "${MODELS[@]}"; do
            run_model_5_4_tests "$model"
            
            # 模型间间隔，避免资源争抢
            echo ""
            echo "⏸️ 模型间间隔30秒..."
            sleep 30
        done
        ;;
        
    2)
        echo ""
        echo "可选模型："
        for i in "${!MODELS[@]}"; do
            echo "$((i+1))) ${MODELS[$i]}"
        done
        echo ""
        read -p "请选择模型 (1-${#MODELS[@]}): " model_choice
        
        if [[ $model_choice -ge 1 && $model_choice -le ${#MODELS[@]} ]]; then
            selected_model="${MODELS[$((model_choice-1))]}"
            run_model_5_4_tests "$selected_model"
        else
            echo "❌ 无效选择"
            exit 1
        fi
        ;;
        
    3)
        echo ""
        echo "🚀 快速测试模式（减少实例数）..."
        
        # 快速测试参数
        QUICK_INSTANCES=5
        QUICK_TASK_TYPES="simple_task,basic_task"
        
        echo "- 模型: qwen2.5-72b-instruct"
        echo "- 实例数: $QUICK_INSTANCES"
        echo "- 任务类型: $QUICK_TASK_TYPES"
        echo ""
        
        for rate in "${TOOL_SUCCESS_RATES[@]}"; do
            echo "启动 tool_success_rate=$rate 测试..."
            
            python ultra_parallel_runner.py \
                --model "qwen2.5-72b-instruct" \
                --prompt-types "$PROMPT_TYPE" \
                --difficulty "$DIFFICULTY" \
                --task-types "$QUICK_TASK_TYPES" \
                --num-instances "$QUICK_INSTANCES" \
                --tool-success-rate "$rate" \
                --rate-mode adaptive \
                --silent &
            
            sleep 3
        done
        
        wait
        echo "✅ 快速测试完成"
        ;;
        
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "📊 查看测试结果："
echo "python view_5_4_results.py"
echo ""
echo "或查看完整数据库："
echo "python view_test_progress.py"
echo "=========================================="
echo ""
echo "✅ 5.4测试脚本执行完成"
echo "完成时间: $(date '+%Y-%m-%d %H:%M:%S')"