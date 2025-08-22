#!/bin/bash
# 安全的5.3测试脚本 - 避免资源竞争和进程卡死

set -e  # 遇到错误立即退出

echo "========================================="
echo "5.3 缺陷工作流适应性测试 - 安全模式"
echo "时间: $(date)"
echo "========================================="

# 设置存储格式
export STORAGE_FORMAT="${STORAGE_FORMAT:-json}"
echo "存储格式: $STORAGE_FORMAT"

# 创建日志目录
LOG_DIR="logs/test_5_3_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"
echo "日志目录: $LOG_DIR"

# 定义模型列表
OPENSOURCE_MODELS=(
    "DeepSeek-V3-0324"
    "DeepSeek-R1-0528"
    "qwen2.5-72b-instruct"
    "qwen2.5-32b-instruct"
    "qwen2.5-14b-instruct"
    "qwen2.5-7b-instruct"
    "qwen2.5-3b-instruct"
    "Llama-3.3-70B-Instruct"
)

CLOSED_MODELS=(
    "gpt-4o-mini"
    "gpt-5-mini"
    "o3-0416-global"
    "gemini-2.5-flash-06-17"
    "kimi-k2"
)

# 缺陷prompt类型
FLAWED_PROMPTS=(
    "flawed_partial_solution"
    "flawed_redundant_steps"
    "flawed_inefficient_approach"
    "flawed_vague_instruction"
    "flawed_sequence_disorder"
    "flawed_circular_dependency"
)

# 测试参数
NUM_INSTANCES=20
TOOL_SUCCESS_RATE=0.8

# 函数：运行单个测试
run_single_test() {
    local model=$1
    local prompt_type=$2
    local model_type=$3
    local log_file="$LOG_DIR/${model}_${prompt_type}.log"
    
    echo ""
    echo "🚀 测试: $model - $prompt_type"
    echo "   类型: $model_type"
    echo "   日志: $log_file"
    
    # 构建命令 - 使用保守参数避免资源竞争
    local cmd="python -u smart_batch_runner.py \
        --model $model \
        --prompt-types $prompt_type \
        --difficulty easy \
        --task-types all \
        --num-instances $NUM_INSTANCES \
        --tool-success-rate $TOOL_SUCCESS_RATE \
        --max-workers 20 \
        --batch-commit \
        --checkpoint-interval 10 \
        --ai-classification \
        --no-save-logs \
        --no-adaptive \
        --qps 20"
    
    # 添加超时控制（30分钟）
    echo "   执行命令（30分钟超时）..."
    
    # 使用timeout命令确保不会无限等待
    if timeout 1800 bash -c "
        export STORAGE_FORMAT='$STORAGE_FORMAT'
        $cmd
    " > "$log_file" 2>&1; then
        echo "   ✅ 完成"
        # 显示最后几行日志
        tail -n 5 "$log_file" | sed 's/^/     /'
    else
        exit_code=$?
        if [ $exit_code -eq 124 ]; then
            echo "   ⏱️ 超时（30分钟）"
        else
            echo "   ❌ 失败 (退出码: $exit_code)"
        fi
        # 显示错误信息
        echo "   最后的日志:"
        tail -n 10 "$log_file" | sed 's/^/     /'
    fi
    
    # 检查进程是否清理干净
    local remaining=$(ps aux | grep -c "smart_batch_runner.*$model" || true)
    if [ "$remaining" -gt 1 ]; then
        echo "   ⚠️ 发现残留进程，清理中..."
        pkill -f "smart_batch_runner.*$model" || true
    fi
    
    # 短暂休息，避免连续启动造成压力
    echo "   💤 休息10秒..."
    sleep 10
}

# 函数：测试模型组
test_model_group() {
    local model_type=$1
    shift
    local models=("$@")
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📊 测试${model_type}模型组"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    for model in "${models[@]}"; do
        echo ""
        echo "═══════════════════════════════════════"
        echo "🤖 模型: $model"
        echo "═══════════════════════════════════════"
        
        # 顺序测试每个缺陷类型
        for prompt in "${FLAWED_PROMPTS[@]}"; do
            run_single_test "$model" "$prompt" "$model_type"
        done
        
        echo ""
        echo "✅ $model 测试完成"
        echo ""
        
        # 模型间休息30秒
        echo "💤 模型间休息30秒..."
        sleep 30
    done
}

# 主执行流程
main() {
    echo ""
    echo "🎯 开始5.3缺陷工作流适应性测试"
    echo "配置："
    echo "  - 实例数: $NUM_INSTANCES"
    echo "  - 工具成功率: $TOOL_SUCCESS_RATE"
    echo "  - 存储格式: $STORAGE_FORMAT"
    echo "  - 超时限制: 30分钟/测试"
    echo ""
    
    # 清理可能的残留进程
    echo "🧹 清理残留进程..."
    pkill -f "smart_batch_runner" || true
    pkill -f "ultra_parallel" || true
    sleep 5
    
    # 依次测试两组模型
    test_model_group "开源" "${OPENSOURCE_MODELS[@]}"
    test_model_group "闭源" "${CLOSED_MODELS[@]}"
    
    # 生成汇总报告
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📊 测试汇总"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # 统计结果
    local total_tests=$((${#OPENSOURCE_MODELS[@]} * ${#FLAWED_PROMPTS[@]} + ${#CLOSED_MODELS[@]} * ${#FLAWED_PROMPTS[@]}))
    local successful=$(grep -c "✅ 完成" "$LOG_DIR"/*.log 2>/dev/null || echo "0")
    local timeouts=$(grep -c "⏱️ 超时" "$LOG_DIR"/*.log 2>/dev/null || echo "0")
    local failures=$(grep -c "❌ 失败" "$LOG_DIR"/*.log 2>/dev/null || echo "0")
    
    echo "总测试数: $total_tests"
    echo "成功: $successful"
    echo "超时: $timeouts"
    echo "失败: $failures"
    echo ""
    echo "日志目录: $LOG_DIR"
    echo "完成时间: $(date)"
    echo ""
    
    # 检查数据保存
    echo "🔍 检查数据保存..."
    python -c "
import json
from pathlib import Path

db_path = Path('pilot_bench_cumulative_results/master_database.json')
if db_path.exists():
    with open(db_path) as f:
        db = json.load(f)
    print(f'  总测试数: {db[\"summary\"].get(\"total_tests\", 0)}')
    print(f'  模型数: {len(db.get(\"models\", {}))}')
    
    # 检查是否有flawed类型的数据
    flawed_count = 0
    for model_data in db.get('models', {}).values():
        for prompt_type in model_data.get('by_prompt_type', {}).keys():
            if 'flawed' in prompt_type:
                flawed_count += 1
                break
    print(f'  包含flawed数据的模型: {flawed_count}')
"
}

# 运行主函数
main

echo "✅ 5.3测试脚本执行完成"