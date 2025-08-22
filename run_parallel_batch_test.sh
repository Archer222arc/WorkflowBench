#!/bin/bash
#===============================================================================
# 智能并行批测试脚本
# 利用模型级别速率限制和多API Key实现最大并行
#===============================================================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 配置参数
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${SCRIPT_DIR}/logs/parallel_batch"
RESULTS_DIR="${SCRIPT_DIR}/pilot_bench_cumulative_results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 创建日志目录
mkdir -p "$LOG_DIR"

# IdealLab API Keys (3个)
IDEALAB_KEY1="956c41bd0f31beaf68b871d4987af4bb"
IDEALAB_KEY2="3d906058842b6cf4cee8aaa019f7e77b"  
IDEALAB_KEY3="88a9a9010f2864bfb53996279dc6c3b9"

# 测试配置
NUM_INSTANCES=${NUM_INSTANCES:-20}        # 每个组合的实例数
DIFFICULTY=${DIFFICULTY:-"easy"}          # 难度级别
TASK_TYPES=${TASK_TYPES:-"all"}          # 任务类型

# Azure模型列表 (可以所有prompt type并行)
AZURE_MODELS=(
    "gpt-4o-mini"
)

# User Azure模型列表 (可以并行)
USER_AZURE_MODELS=(
    "gpt-5-nano"
    "DeepSeek-R1-0528"
    "DeepSeek-V3-0324"
)

# IdealLab模型列表 (需要分配到不同的API Key)
IDEALAB_MODELS=(
    "qwen2.5-3b-instruct"
    "qwen2.5-7b-instruct"
    "qwen2.5-14b-instruct"
    "qwen2.5-32b-instruct"
    "DeepSeek-V3-671B"
    "DeepSeek-R1-671B"
    "claude37_sonnet"
    "gemini-2.0-flash"
    "kimi-k2"
)

# Prompt类型
PROMPT_TYPES=("baseline" "cot" "optimal")
FLAWED_TYPES=("sequence_disorder" "tool_misuse" "parameter_error" "missing_step" "redundant_operations" "logical_inconsistency" "semantic_drift")

#===============================================================================
# 辅助函数
#===============================================================================

log_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 运行单个测试任务
run_test_task() {
    local model=$1
    local prompt_type=$2
    local tool_success_rate=${3:-0.8}
    local log_file="${LOG_DIR}/${model}_${prompt_type}_${TIMESTAMP}.log"
    
    echo -e "${BLUE}[TASK]${NC} 开始: $model | $prompt_type | tool_rate=$tool_success_rate"
    
    # 使用环境变量传递API Key (如果需要)
    if [[ "$4" != "" ]]; then
        export IDEALAB_API_KEY_OVERRIDE=$4
    fi
    
    python smart_batch_runner.py \
        --model "$model" \
        --prompt-types "$prompt_type" \
        --difficulty "$DIFFICULTY" \
        --task-types "$TASK_TYPES" \
        --num-instances "$NUM_INSTANCES" \
        --tool-success-rate "$tool_success_rate" \
        --adaptive \
        --batch-commit \
        --checkpoint-interval 10 \
        > "$log_file" 2>&1
    
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        log_success "完成: $model | $prompt_type"
    else
        log_error "失败: $model | $prompt_type (退出码: $exit_code)"
    fi
    
    # 清理环境变量
    unset IDEALAB_API_KEY_OVERRIDE
    
    return $exit_code
}

# 并行运行一组任务
run_parallel_group() {
    local group_name=$1
    shift
    local tasks=("$@")
    
    log_info "启动并行组: $group_name (${#tasks[@]} 个任务)"
    
    # 使用GNU parallel或xargs并行执行
    if command -v parallel &> /dev/null; then
        # 使用GNU parallel
        printf "%s\n" "${tasks[@]}" | parallel -j 10 --bar {}
    else
        # 使用xargs作为备选
        printf "%s\n" "${tasks[@]}" | xargs -P 10 -I {} bash -c "{}"
    fi
    
    log_success "并行组完成: $group_name"
}

#===============================================================================
# Azure模型测试 (所有prompt types并行)
#===============================================================================
test_azure_models() {
    log_info "==================== Azure 模型测试 ===================="
    
    local tasks=()
    
    for model in "${AZURE_MODELS[@]}"; do
        # 常规prompt types
        for prompt_type in "${PROMPT_TYPES[@]}"; do
            tasks+=("run_test_task '$model' '$prompt_type' 0.8")
        done
        
        # Flawed types (每个作为独立的prompt type)
        for flaw_type in "${FLAWED_TYPES[@]}"; do
            tasks+=("run_test_task '$model' 'flawed_$flaw_type' 0.8")
        done
    done
    
    if [ ${#tasks[@]} -gt 0 ]; then
        log_info "Azure任务数: ${#tasks[@]}"
        run_parallel_group "Azure Models" "${tasks[@]}"
    fi
}

#===============================================================================
# User Azure模型测试 (包括DeepSeek)
#===============================================================================
test_user_azure_models() {
    log_info "==================== User Azure 模型测试 ===================="
    
    local tasks=()
    
    for model in "${USER_AZURE_MODELS[@]}"; do
        # 常规prompt types
        for prompt_type in "${PROMPT_TYPES[@]}"; do
            tasks+=("run_test_task '$model' '$prompt_type' 0.8")
        done
        
        # Flawed types
        for flaw_type in "${FLAWED_TYPES[@]}"; do
            tasks+=("run_test_task '$model' 'flawed_$flaw_type' 0.8")
        done
    done
    
    if [ ${#tasks[@]} -gt 0 ]; then
        log_info "User Azure任务数: ${#tasks[@]}"
        run_parallel_group "User Azure Models" "${tasks[@]}"
    fi
}

#===============================================================================
# IdealLab模型测试 (使用3个API Keys轮询)
#===============================================================================
test_idealab_models() {
    log_info "==================== IdealLab 模型测试 (3 API Keys) ===================="
    
    # 为每个prompt type分配不同的API Key
    local baseline_key=$IDEALAB_KEY1
    local cot_key=$IDEALAB_KEY2
    local optimal_key=$IDEALAB_KEY3
    local flawed_key=$IDEALAB_KEY1  # flawed循环使用
    
    # 按prompt type分组任务
    local baseline_tasks=()
    local cot_tasks=()
    local optimal_tasks=()
    local flawed_tasks=()
    
    for model in "${IDEALAB_MODELS[@]}"; do
        # Baseline (使用Key1)
        baseline_tasks+=("run_test_task '$model' 'baseline' 0.8 '$baseline_key'")
        
        # CoT (使用Key2)
        cot_tasks+=("run_test_task '$model' 'cot' 0.8 '$cot_key'")
        
        # Optimal (使用Key3)
        optimal_tasks+=("run_test_task '$model' 'optimal' 0.8 '$optimal_key'")
        
        # Flawed types (轮询使用3个keys)
        local key_index=0
        for flaw_type in "${FLAWED_TYPES[@]}"; do
            # 轮询分配API Key
            case $((key_index % 3)) in
                0) flawed_key=$IDEALAB_KEY1 ;;
                1) flawed_key=$IDEALAB_KEY2 ;;
                2) flawed_key=$IDEALAB_KEY3 ;;
            esac
            flawed_tasks+=("run_test_task '$model' 'flawed_$flaw_type' 0.8 '$flawed_key'")
            ((key_index++))
        done
    done
    
    # 并行运行所有IdealLab任务
    log_info "IdealLab Baseline任务 (Key1): ${#baseline_tasks[@]}"
    log_info "IdealLab CoT任务 (Key2): ${#cot_tasks[@]}"
    log_info "IdealLab Optimal任务 (Key3): ${#optimal_tasks[@]}"
    log_info "IdealLab Flawed任务 (轮询): ${#flawed_tasks[@]}"
    
    # 合并所有任务并并行运行
    local all_idealab_tasks=()
    all_idealab_tasks+=("${baseline_tasks[@]}")
    all_idealab_tasks+=("${cot_tasks[@]}")
    all_idealab_tasks+=("${optimal_tasks[@]}")
    all_idealab_tasks+=("${flawed_tasks[@]}")
    
    if [ ${#all_idealab_tasks[@]} -gt 0 ]; then
        log_info "总IdealLab任务数: ${#all_idealab_tasks[@]}"
        run_parallel_group "IdealLab Models" "${all_idealab_tasks[@]}"
    fi
}

#===============================================================================
# 测试不同tool_success_rate
#===============================================================================
test_tool_success_rates() {
    log_info "==================== Tool Success Rate 测试 ===================="
    
    local rates=(0.6 0.7 0.8 0.9)
    local test_models=("gpt-4o-mini" "qwen2.5-3b-instruct" "DeepSeek-V3-671B")
    local tasks=()
    
    for model in "${test_models[@]}"; do
        for rate in "${rates[@]}"; do
            # 根据模型类型分配API Key
            local api_key=""
            if [[ "$model" == "qwen"* ]] || [[ "$model" == "DeepSeek-V3"* ]]; then
                # IdealLab模型，轮询使用API Key
                case $(( RANDOM % 3 )) in
                    0) api_key=$IDEALAB_KEY1 ;;
                    1) api_key=$IDEALAB_KEY2 ;;
                    2) api_key=$IDEALAB_KEY3 ;;
                esac
                tasks+=("run_test_task '$model' 'baseline' $rate '$api_key'")
            else
                # Azure模型
                tasks+=("run_test_task '$model' 'baseline' $rate")
            fi
        done
    done
    
    if [ ${#tasks[@]} -gt 0 ]; then
        log_info "Tool Success Rate任务数: ${#tasks[@]}"
        run_parallel_group "Tool Success Rate Tests" "${tasks[@]}"
    fi
}

#===============================================================================
# 监控进度
#===============================================================================
monitor_progress() {
    log_info "监控测试进度..."
    
    while true; do
        # 统计日志文件中的成功/失败
        local success_count=$(grep -h "✅.*成功" "$LOG_DIR"/*_${TIMESTAMP}.log 2>/dev/null | wc -l)
        local fail_count=$(grep -h "✗.*失败" "$LOG_DIR"/*_${TIMESTAMP}.log 2>/dev/null | wc -l)
        local running=$(pgrep -f "smart_batch_runner.py" | wc -l)
        
        echo -ne "\r${CYAN}[MONITOR]${NC} 运行中: $running | 成功: $success_count | 失败: $fail_count"
        
        if [ $running -eq 0 ]; then
            echo ""
            break
        fi
        
        sleep 5
    done
}

#===============================================================================
# 生成测试报告
#===============================================================================
generate_report() {
    log_info "生成测试报告..."
    
    local report_file="${LOG_DIR}/report_${TIMESTAMP}.txt"
    
    {
        echo "========================================"
        echo "批测试报告"
        echo "时间: $(date)"
        echo "========================================"
        echo ""
        
        echo "配置:"
        echo "  实例数: $NUM_INSTANCES"
        echo "  难度: $DIFFICULTY"
        echo "  任务类型: $TASK_TYPES"
        echo ""
        
        echo "模型统计:"
        echo "  Azure: ${#AZURE_MODELS[@]}"
        echo "  User Azure: ${#USER_AZURE_MODELS[@]}"
        echo "  IdealLab: ${#IDEALAB_MODELS[@]}"
        echo ""
        
        echo "日志文件:"
        ls -lh "$LOG_DIR"/*_${TIMESTAMP}.log 2>/dev/null | tail -20
        
    } > "$report_file"
    
    log_success "报告已生成: $report_file"
}

#===============================================================================
# 主流程
#===============================================================================
main() {
    log_info "========================================"
    log_info "智能并行批测试"
    log_info "时间: $(date)"
    log_info "========================================"
    
    # 检查依赖
    if ! command -v python &> /dev/null; then
        log_error "未找到Python"
        exit 1
    fi
    
    # 显示配置
    log_info "测试配置:"
    log_info "  实例数: $NUM_INSTANCES"
    log_info "  难度: $DIFFICULTY"
    log_info "  任务类型: $TASK_TYPES"
    log_info "  日志目录: $LOG_DIR"
    
    # 询问确认
    echo -ne "${YELLOW}是否开始测试? (y/n): ${NC}"
    read -r response
    if [[ "$response" != "y" ]]; then
        log_warning "测试取消"
        exit 0
    fi
    
    # 记录开始时间
    START_TIME=$(date +%s)
    
    # 并行运行所有测试组
    {
        test_azure_models &
        azure_pid=$!
        
        test_user_azure_models &
        user_azure_pid=$!
        
        test_idealab_models &
        idealab_pid=$!
        
        # 可选：测试不同的tool_success_rate
        # test_tool_success_rates &
        # tool_rate_pid=$!
        
        # 等待所有后台任务完成
        wait $azure_pid
        wait $user_azure_pid
        wait $idealab_pid
        # wait $tool_rate_pid
    }
    
    # 记录结束时间
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    log_success "========================================"
    log_success "所有测试完成!"
    log_success "总耗时: $((DURATION / 60))分 $((DURATION % 60))秒"
    log_success "========================================"
    
    # 生成报告
    generate_report
    
    # 显示数据库统计
    log_info "更新后的数据库统计:"
    python -c "
import json
from pathlib import Path

db_path = Path('pilot_bench_cumulative_results/master_database.json')
if db_path.exists():
    with open(db_path, 'r') as f:
        db = json.load(f)
    
    print(f'总测试数: {db[\"summary\"][\"total_tests\"]}')
    print(f'模型数: {len(db[\"models\"])}')
    
    # 显示每个模型的测试数
    for model in list(db['models'].keys())[:5]:
        model_data = db['models'][model]
        total = model_data.get('overall_stats', {}).get('total_tests', 0)
        print(f'  {model}: {total} 个测试')
"
}

# 运行主流程
main "$@"