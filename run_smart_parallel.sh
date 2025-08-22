#!/bin/bash
#===============================================================================
# 智能并行测试脚本 - 简化版
# 最大化利用API provider级别的并行性
#===============================================================================

set -e  # 遇到错误立即退出

# 配置
NUM_INSTANCES=${1:-20}
DIFFICULTY=${2:-easy}
TASK_TYPES=${3:-all}

# IdealLab API Keys
IDEALAB_KEY1="956c41bd0f31beaf68b871d4987af4bb"
IDEALAB_KEY2="3d906058842b6cf4cee8aaa019f7e77b"
IDEALAB_KEY3="88a9a9010f2864bfb53996279dc6c3b9"

# 日志目录
LOG_DIR="logs/parallel_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"

echo "========================================"
echo "智能并行批测试"
echo "配置: instances=$NUM_INSTANCES, difficulty=$DIFFICULTY, tasks=$TASK_TYPES"
echo "日志目录: $LOG_DIR"
echo "========================================"

#===============================================================================
# 函数定义
#===============================================================================

# 运行单个测试
run_test() {
    local model=$1
    local prompt=$2
    local rate=${3:-0.8}
    local api_key=$4
    
    echo "[$(date +%H:%M:%S)] 开始: $model | $prompt"
    
    # 设置API Key环境变量
    if [ ! -z "$api_key" ]; then
        export IDEALAB_API_KEY_OVERRIDE=$api_key
    fi
    
    # 运行测试
    python smart_batch_runner.py \
        --model "$model" \
        --prompt-types "$prompt" \
        --difficulty "$DIFFICULTY" \
        --task-types "$TASK_TYPES" \
        --num-instances "$NUM_INSTANCES" \
        --tool-success-rate "$rate" \
        --adaptive \
        --batch-commit \
        --silent \
        > "$LOG_DIR/${model}_${prompt}.log" 2>&1
    
    local exit_code=$?
    
    # 清理环境变量
    unset IDEALAB_API_KEY_OVERRIDE
    
    if [ $exit_code -eq 0 ]; then
        echo "[$(date +%H:%M:%S)] ✓ 完成: $model | $prompt"
    else
        echo "[$(date +%H:%M:%S)] ✗ 失败: $model | $prompt"
    fi
    
    return $exit_code
}

export -f run_test

#===============================================================================
# Azure模型 - 所有prompt并行
#===============================================================================
echo ""
echo "【Azure模型】"
echo "策略: 所有prompt types并行 (高并发能力)"

# Azure模型列表
AZURE_MODELS="gpt-4o-mini"

# 生成所有任务
for model in $AZURE_MODELS; do
    # 常规prompts
    for prompt in baseline cot optimal; do
        echo "run_test '$model' '$prompt' 0.8 ''" >> "$LOG_DIR/azure_tasks.txt"
    done
    
    # Flawed prompts
    for flaw in sequence_disorder tool_misuse parameter_error missing_step redundant_operations logical_inconsistency semantic_drift; do
        echo "run_test '$model' 'flawed_$flaw' 0.8 ''" >> "$LOG_DIR/azure_tasks.txt"
    done
done

# 并行执行Azure任务
if [ -f "$LOG_DIR/azure_tasks.txt" ]; then
    echo "Azure任务数: $(wc -l < "$LOG_DIR/azure_tasks.txt")"
    cat "$LOG_DIR/azure_tasks.txt" | xargs -P 10 -I {} bash -c "{}"
fi

#===============================================================================
# User Azure模型 (包括DeepSeek)
#===============================================================================
echo ""
echo "【User Azure模型】"
echo "策略: 包括DeepSeek模型，中等并发"

USER_AZURE_MODELS="gpt-5-nano DeepSeek-R1-0528 DeepSeek-V3-0324"

# 生成任务
for model in $USER_AZURE_MODELS; do
    for prompt in baseline cot optimal; do
        echo "run_test '$model' '$prompt' 0.8 ''" >> "$LOG_DIR/user_azure_tasks.txt"
    done
    
    for flaw in sequence_disorder tool_misuse parameter_error; do
        echo "run_test '$model' 'flawed_$flaw' 0.8 ''" >> "$LOG_DIR/user_azure_tasks.txt"
    done
done

# 并行执行
if [ -f "$LOG_DIR/user_azure_tasks.txt" ]; then
    echo "User Azure任务数: $(wc -l < "$LOG_DIR/user_azure_tasks.txt")"
    cat "$LOG_DIR/user_azure_tasks.txt" | xargs -P 8 -I {} bash -c "{}"
fi

#===============================================================================
# IdealLab模型 - 使用3个API Keys
#===============================================================================
echo ""
echo "【IdealLab模型】"
echo "策略: 3个API Keys，每个prompt type用不同的key"

# IdealLab模型列表
IDEALAB_MODELS="qwen2.5-3b-instruct qwen2.5-7b-instruct qwen2.5-14b-instruct DeepSeek-V3-671B claude37_sonnet"

# Baseline使用Key1
for model in $IDEALAB_MODELS; do
    echo "run_test '$model' 'baseline' 0.8 '$IDEALAB_KEY1'" >> "$LOG_DIR/idealab_tasks.txt"
done

# CoT使用Key2
for model in $IDEALAB_MODELS; do
    echo "run_test '$model' 'cot' 0.8 '$IDEALAB_KEY2'" >> "$LOG_DIR/idealab_tasks.txt"
done

# Optimal使用Key3
for model in $IDEALAB_MODELS; do
    echo "run_test '$model' 'optimal' 0.8 '$IDEALAB_KEY3'" >> "$LOG_DIR/idealab_tasks.txt"
done

# Flawed轮询使用3个keys
FLAWED_TYPES=(sequence_disorder tool_misuse parameter_error missing_step redundant_operations logical_inconsistency semantic_drift)
KEY_INDEX=0

for model in $IDEALAB_MODELS; do
    for flaw in "${FLAWED_TYPES[@]}"; do
        # 轮询选择API Key
        case $((KEY_INDEX % 3)) in
            0) KEY=$IDEALAB_KEY1 ;;
            1) KEY=$IDEALAB_KEY2 ;;
            2) KEY=$IDEALAB_KEY3 ;;
        esac
        
        echo "run_test '$model' 'flawed_$flaw' 0.8 '$KEY'" >> "$LOG_DIR/idealab_tasks.txt"
        ((KEY_INDEX++))
    done
done

# 并行执行IdealLab任务
if [ -f "$LOG_DIR/idealab_tasks.txt" ]; then
    echo "IdealLab任务数: $(wc -l < "$LOG_DIR/idealab_tasks.txt")"
    cat "$LOG_DIR/idealab_tasks.txt" | xargs -P 20 -I {} bash -c "{}"
fi

#===============================================================================
# 等待所有任务完成并生成报告
#===============================================================================
echo ""
echo "========================================"
echo "所有任务已提交，等待完成..."
echo "========================================"

# 等待所有python进程完成
while pgrep -f "smart_batch_runner.py" > /dev/null; do
    RUNNING=$(pgrep -f "smart_batch_runner.py" | wc -l)
    echo -ne "\r运行中的任务: $RUNNING  "
    sleep 5
done

echo ""
echo "========================================"
echo "测试完成!"
echo "========================================"

# 统计结果
echo ""
echo "结果统计:"
SUCCESS=$(grep -h "✅.*成功" "$LOG_DIR"/*.log 2>/dev/null | wc -l || echo 0)
FAILED=$(grep -h "✗.*失败" "$LOG_DIR"/*.log 2>/dev/null | wc -l || echo 0)
echo "  成功: $SUCCESS"
echo "  失败: $FAILED"

# 显示日志文件
echo ""
echo "日志文件:"
ls -lh "$LOG_DIR"/*.log 2>/dev/null | head -10

echo ""
echo "完成时间: $(date)"
echo "日志目录: $LOG_DIR"