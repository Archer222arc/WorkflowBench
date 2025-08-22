#!/bin/bash
# 5.3测试脚本 - macOS兼容版本

set -e  # 遇到错误立即退出

echo "========================================="
echo "5.3 缺陷工作流适应性测试 - macOS版本"
echo "时间: $(date)"
echo "========================================="

# 设置存储格式
export STORAGE_FORMAT="${STORAGE_FORMAT:-json}"
echo "存储格式: $STORAGE_FORMAT"

# 创建日志目录
LOG_DIR="logs/test_5_3_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"
echo "日志目录: $LOG_DIR"

# 定义模型列表 - 先测试Azure模型（速度快）
AZURE_MODELS=(
    "gpt-4o-mini"
    "DeepSeek-V3-0324"
)

# 缺陷prompt类型 - 先测试2个
FLAWED_PROMPTS=(
    "flawed_sequence_disorder"
    "flawed_redundant_steps"
)

# 测试参数
NUM_INSTANCES=2  # 减少到2个实例便于快速测试
TOOL_SUCCESS_RATE=0.8

# 函数：运行单个测试（macOS版本，不使用timeout）
run_single_test() {
    local model=$1
    local prompt_type=$2
    local log_file="$LOG_DIR/${model}_${prompt_type}.log"
    
    echo ""
    echo "🚀 测试: $model - $prompt_type"
    echo "   日志: $log_file"
    
    # 构建命令 - 使用batch-commit确保数据保存
    local cmd="python -u smart_batch_runner.py \
        --model $model \
        --prompt-types $prompt_type \
        --difficulty easy \
        --task-types simple_task \
        --num-instances $NUM_INSTANCES \
        --tool-success-rate $TOOL_SUCCESS_RATE \
        --max-workers 5 \
        --batch-commit \
        --checkpoint-interval 1 \
        --ai-classification \
        --no-save-logs \
        --no-adaptive \
        --qps 10"
    
    echo "   执行中..."
    
    # 在后台运行，使用Python脚本控制超时
    (
        export STORAGE_FORMAT="$STORAGE_FORMAT"
        eval "$cmd"
    ) > "$log_file" 2>&1 &
    
    local pid=$!
    local timeout=300  # 5分钟超时
    local elapsed=0
    
    # 等待进程完成或超时
    while kill -0 $pid 2>/dev/null; do
        if [ $elapsed -ge $timeout ]; then
            echo "   ⏱️ 超时（5分钟），终止进程..."
            kill -9 $pid 2>/dev/null || true
            break
        fi
        sleep 5
        elapsed=$((elapsed + 5))
        if [ $((elapsed % 30)) -eq 0 ]; then
            echo "   ⏳ 已运行 ${elapsed}秒..."
        fi
    done
    
    # 检查结果
    if wait $pid 2>/dev/null; then
        echo "   ✅ 完成"
        # 显示统计
        grep -E "(成功:|失败:|保存)" "$log_file" | tail -3 | sed 's/^/     /'
    else
        echo "   ❌ 失败或超时"
        tail -n 5 "$log_file" | sed 's/^/     /'
    fi
    
    # 短暂休息
    echo "   💤 休息5秒..."
    sleep 5
}

# 主执行流程
echo ""
echo "🎯 开始5.3测试（简化版）"
echo "配置："
echo "  - 模型数: ${#AZURE_MODELS[@]}"
echo "  - 缺陷类型: ${#FLAWED_PROMPTS[@]}"
echo "  - 实例数: $NUM_INSTANCES"
echo "  - 工具成功率: $TOOL_SUCCESS_RATE"

# 测试Azure模型
for model in "${AZURE_MODELS[@]}"; do
    echo ""
    echo "═══════════════════════════════════════"
    echo "🤖 模型: $model"
    echo "═══════════════════════════════════════"
    
    for prompt in "${FLAWED_PROMPTS[@]}"; do
        run_single_test "$model" "$prompt"
    done
    
    echo ""
    echo "✅ $model 测试完成"
done

# 统计结果
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 测试完成"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "日志目录: $LOG_DIR"

# 检查数据库更新
python -c "
import json
from pathlib import Path

db_path = Path('pilot_bench_cumulative_results/master_database.json')
with open(db_path) as f:
    db = json.load(f)

print(f'\\n数据库统计:')
print(f'  Total tests: {db[\"summary\"][\"total_tests\"]}')

# 检查flawed数据
for model in ['gpt-4o-mini', 'DeepSeek-V3-0324']:
    if model in db.get('models', {}):
        m = db['models'][model]
        if 'by_prompt_type' in m:
            flawed_count = sum(1 for k in m['by_prompt_type'].keys() if 'flawed' in k)
            if flawed_count > 0:
                print(f'  {model}: {flawed_count} flawed types')
"

echo ""
echo "✅ 所有测试完成！"