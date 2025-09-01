#!/bin/bash

# 5.5 提示敏感性测试脚本
# 基于test_5_1_complete_retest.sh修改，用于测试不同prompt类型的敏感性
# 配置: baseline/cot/optimal prompt + easy难度 + 0.8工具成功率

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/test_5_5_prompt_sensitivity_${TIMESTAMP}.log"

# 5.5 固定配置
DIFFICULTY="easy"
TOOL_SUCCESS_RATE="0.8"
PROMPT_TYPES=("baseline" "cot" "optimal")  # optimal使用5.1数据

# 模型配置 - 暂时只测试开源模型
OPENSOURCE_MODELS=(
    "DeepSeek-R1-0528"
    "DeepSeek-V3-0324" 
    "Llama-3.3-70B-Instruct"
    "qwen2.5-3b-instruct"
    "qwen2.5-7b-instruct"
    "qwen2.5-14b-instruct"
    "qwen2.5-32b-instruct"
    "qwen2.5-72b-instruct"
)

# 暂时不测试闭源模型
# CLOSED_SOURCE_MODELS=(
#     "gpt-4o-mini"
#     "gpt-5-mini"
#     "o3-0416-global"
#     "gemini-2.5-flash-06-17"
#     "kimi-k2"
# )

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

# 显示使用说明
show_usage() {
    echo -e "${CYAN}5.5 提示敏感性测试脚本${NC}"
    echo ""
    echo "用法: $0 [模型名|all] [提示类型|all]"
    echo ""
    echo "模型选项 (暂时只支持开源模型):"
    echo "  开源模型: DeepSeek-R1-0528, DeepSeek-V3-0324, Llama-3.3-70B-Instruct,"
    echo "           qwen2.5-3b-instruct, qwen2.5-7b-instruct, qwen2.5-14b-instruct,"
    echo "           qwen2.5-32b-instruct, qwen2.5-72b-instruct"
    echo "  all: 所有开源模型"
    echo ""
    echo "提示类型选项:"
    echo "  baseline: 基础提示策略"
    echo "  cot: 思维链提示策略"  
    echo "  optimal: 最优提示策略（使用5.1现有数据）"
    echo "  all: 所有提示类型"
    echo ""
    echo "示例:"
    echo "  $0 all all                    # 测试所有模型×所有提示类型"
    echo "  $0 DeepSeek-V3-0324 all       # 测试DeepSeek-V3所有提示类型"
    echo "  $0 all baseline               # 测试所有模型baseline提示"
    echo "  $0 DeepSeek-V3-0324 baseline  # 测试DeepSeek-V3 baseline提示"
}

# 检查模型是否为开源模型
is_opensource_model() {
    local model="$1"
    for opensource_model in "${OPENSOURCE_MODELS[@]}"; do
        if [[ "$model" == "$opensource_model" ]]; then
            return 0
        fi
    done
    return 1
}

# 检查模型是否为闭源模型 - 暂时不支持
is_closed_source_model() {
    local model="$1"
    # 暂时不支持闭源模型测试
    return 1
}

# 获取模型的worker配置
get_model_workers() {
    local model="$1"
    
    case "$model" in
        "DeepSeek-R1-0528"|"DeepSeek-V3-0324"|"Llama-3.3-70B-Instruct")
            echo "50"  # Azure开源模型高并发
            ;;
        "qwen2.5-"*)
            echo "3"   # IdealLab qwen模型3个API keys
            ;;
        "gpt-4o-mini"|"gpt-5-mini")
            echo "20"  # Azure闭源模型中等并发
            ;;
        "o3-0416-global"|"gemini-2.5-flash-06-17"|"kimi-k2")
            echo "1"   # IdealLab闭源模型限流
            ;;
        *)
            echo "10"  # 默认
            ;;
    esac
}

# 运行单个模型的提示类型测试
run_model_prompt_test() {
    local model="$1"
    local prompt_type="$2"
    
    log_info "🚀 开始测试 $model - $prompt_type"
    
    # optimal使用5.1现有数据，跳过测试
    if [[ "$prompt_type" == "optimal" ]]; then
        log_info "📊 $model - optimal 使用5.1现有数据，跳过测试"
        return 0
    fi
    
    local workers=$(get_model_workers "$model")
    local workers_param="--max-workers $workers"
    
    # 构建python命令数组 - 使用正确的参数名
    local python_cmd=(
        "python3" "./ultra_parallel_runner.py"
        "--model" "$model"
        "--prompt-types" "$prompt_type" 
        "--difficulty" "$DIFFICULTY"
        "--task-types" "all"
        "--num-instances" "20"
        "--rate-mode" "fixed"
        $workers_param
    )
    
    log_info "📋 执行命令: ${python_cmd[*]}"
    
    # 创建模型专用日志文件
    local sanitized_model=$(echo "$model" | tr '.' '_' | tr '-' '_')
    local test_log="$LOG_DIR/ultra_parallel_${sanitized_model}_${prompt_type}_${TIMESTAMP}.log"
    
    # 记录开始时间
    local start_time=$(date +%s)
    
    # 执行测试 - 使用tee同时显示输出和保存日志
    echo "=== 测试开始时间: $(date) ===" | tee "$test_log"
    echo "=== 执行命令: ${python_cmd[*]} ===" | tee -a "$test_log"
    
    if "${python_cmd[@]}" 2>&1 | tee -a "$test_log"; then
        local exit_code=${PIPESTATUS[0]}
        
        # 记录结束时间
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        echo "=== 测试结束时间: $(date) ===" | tee -a "$test_log"
        echo "=== 测试用时: ${duration}秒 ===" | tee -a "$test_log"
        
        if [[ $exit_code -eq 0 ]]; then
            log_success "✅ $model - $prompt_type 测试完成 (用时: ${duration}秒)"
            return 0
        else
            log_error "❌ $model - $prompt_type 测试失败 (退出码: $exit_code)"
            return 1
        fi
    else
        log_error "❌ $model - $prompt_type 执行失败"
        return 1
    fi
}

# 运行特定模型的所有提示类型测试
run_model_all_prompts() {
    local model="$1"
    local success_count=0
    local total_count=${#PROMPT_TYPES[@]}
    
    log_info "🎯 开始测试模型: $model (${total_count}个提示类型)"
    
    for prompt_type in "${PROMPT_TYPES[@]}"; do
        if run_model_prompt_test "$model" "$prompt_type"; then
            ((success_count++))
        fi
    done
    
    log_info "📊 $model 完成: $success_count/$total_count 个提示类型成功"
    
    if [[ $success_count -eq $total_count ]]; then
        return 0
    else
        return 1
    fi
}

# 运行特定提示类型的所有模型测试
run_all_models_prompt() {
    local prompt_type="$1"
    local success_count=0
    local total_models=${#OPENSOURCE_MODELS[@]}
    
    log_info "🎯 开始测试提示类型: $prompt_type (${total_models}个开源模型)"
    
    # 测试开源模型
    for model in "${OPENSOURCE_MODELS[@]}"; do
        if run_model_prompt_test "$model" "$prompt_type"; then
            ((success_count++))
        fi
    done
    
    log_info "📊 $prompt_type 完成: $success_count/$total_models 个模型成功"
    
    if [[ $success_count -eq $total_models ]]; then
        return 0
    else
        return 1
    fi
}

# 运行所有模型×所有提示类型测试
run_all_tests() {
    local total_tests=${#OPENSOURCE_MODELS[@]}
    local total_prompts=${#PROMPT_TYPES[@]}
    local total_combinations=$((total_tests * total_prompts))
    local success_count=0
    
    log_info "🎯 开始5.5提示敏感性完整测试（仅开源模型）"
    log_info "📊 总计: ${total_tests}个开源模型 × ${total_prompts}个提示类型 = ${total_combinations}个测试组合"
    
    # 按提示类型分组执行（便于批量处理）
    for prompt_type in "${PROMPT_TYPES[@]}"; do
        log_info "🔄 开始提示类型: $prompt_type"
        
        # 开源模型
        for model in "${OPENSOURCE_MODELS[@]}"; do
            if run_model_prompt_test "$model" "$prompt_type"; then
                ((success_count++))
            fi
        done
        
        log_info "✅ 提示类型 $prompt_type 完成"
    done
    
    log_info "🎉 5.5提示敏感性测试全部完成"
    log_info "📊 总体结果: $success_count/$total_combinations 个测试成功"
    
    if [[ $success_count -eq $total_combinations ]]; then
        log_success "🏆 所有测试成功完成！"
        return 0
    else
        log_warning "⚠️  部分测试失败，请查看日志详情"
        return 1
    fi
}

# 主函数
main() {
    log "🚀 启动5.5提示敏感性测试脚本"
    log "📝 日志文件: $LOG_FILE"
    log "⚙️  配置: 难度=$DIFFICULTY, 工具成功率=$TOOL_SUCCESS_RATE"
    log "📋 提示类型: ${PROMPT_TYPES[*]}"
    
    # 参数解析
    local model_param="${1:-}"
    local prompt_param="${2:-}"
    
    if [[ -z "$model_param" ]] || [[ -z "$prompt_param" ]]; then
        show_usage
        exit 1
    fi
    
    # 验证模型参数
    if [[ "$model_param" != "all" ]]; then
        if ! is_opensource_model "$model_param"; then
            log_error "❌ 未知模型或暂不支持的模型: $model_param"
            log_error "🔍 当前仅支持开源模型"
            show_usage
            exit 1
        fi
    fi
    
    # 验证提示类型参数
    if [[ "$prompt_param" != "all" ]]; then
        local valid_prompt=false
        for prompt_type in "${PROMPT_TYPES[@]}"; do
            if [[ "$prompt_param" == "$prompt_type" ]]; then
                valid_prompt=true
                break
            fi
        done
        if [[ "$valid_prompt" == "false" ]]; then
            log_error "❌ 未知提示类型: $prompt_param"
            show_usage
            exit 1
        fi
    fi
    
    # 执行测试
    local exit_code=0
    
    if [[ "$model_param" == "all" && "$prompt_param" == "all" ]]; then
        # 所有模型×所有提示类型
        run_all_tests || exit_code=$?
    elif [[ "$model_param" == "all" ]]; then
        # 所有模型×特定提示类型  
        run_all_models_prompt "$prompt_param" || exit_code=$?
    elif [[ "$prompt_param" == "all" ]]; then
        # 特定模型×所有提示类型
        run_model_all_prompts "$model_param" || exit_code=$?
    else
        # 特定模型×特定提示类型
        run_model_prompt_test "$model_param" "$prompt_param" || exit_code=$?
    fi
    
    if [[ $exit_code -eq 0 ]]; then
        log_success "🎉 测试任务完成！"
    else
        log_error "❌ 测试任务存在失败，请检查日志"
    fi
    
    log "📊 详细日志保存至: $LOG_FILE"
    exit $exit_code
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi