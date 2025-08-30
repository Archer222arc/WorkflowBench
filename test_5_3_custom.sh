#!/bin/bash

# 5.3 缺陷工作流测试专用脚本
# 支持自主选择flawed类型，使用超并发+JSON+ResultCollector存储

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
LOG_FILE="$LOG_DIR/test_5_3_custom_${TIMESTAMP}.log"

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

# 环境变量设置 - 严格匹配run_systematic_test_final.sh的设置
export USE_RESULT_COLLECTOR=true
export STORAGE_FORMAT=json
export MODEL_TYPE="opensource"  # 默认开源模型类型
export NUM_INSTANCES=20
export RATE_MODE="fixed"
export USE_PARTIAL_LOADING=true
export TASK_LOAD_COUNT=20
export SKIP_MODEL_LOADING=true
export ULTRA_PARALLEL_MODE=true  # 启用超并行模式
export CONSERVATIVE_MODE=false   # 不使用保守模式
export CUSTOM_WORKERS=50
export MAX_PARALLEL_PROCESSES=10  # 最大并行进程数

# 激活conda环境
if [ -f ~/miniconda3/bin/activate ]; then
    source ~/miniconda3/bin/activate
    log_info "✅ 已激活conda环境: $(which python)"
else
    log_warning "⚠️ 未找到conda环境，使用系统Python"
fi

log_info "=== 5.3 缺陷工作流测试脚本启动 ==="
log_info "时间戳: $TIMESTAMP"
log_info "日志文件: $LOG_FILE"

# 检查必需文件
check_files() {
    local required_files=(
        "./ultra_parallel_runner.py"
        "./smart_batch_runner.py" 
        "./config/config.json"
        "./result_collector.py"
    )
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            log_error "缺少必需文件: $file"
            exit 1
        fi
    done
    log_success "所有必需文件检查完成"
}

# 显示可用的flawed类型 - 严格匹配run_systematic_test_final.sh的7种缺陷类型
show_flawed_types() {
    echo -e "\n${CYAN}📋 可用的缺陷工作流类型:${NC}"
    echo "1) flawed_sequence_disorder     - 工具调用顺序错误"
    echo "2) flawed_tool_misuse           - 工具误用"  
    echo "3) flawed_parameter_error       - 参数错误"
    echo "4) flawed_missing_step          - 缺少步骤"
    echo "5) flawed_redundant_operations  - 冗余操作"
    echo "6) flawed_logical_inconsistency - 逻辑不一致"
    echo "7) flawed_semantic_drift        - 语义偏移"
    echo "8) all                          - 测试所有类型"
    echo
}

# 获取用户选择
get_user_choice() {
    while true; do
        show_flawed_types
        read -p "请选择要测试的缺陷类型 (输入数字或类型名): " choice
        
        case $choice in
            1|flawed_sequence_disorder)
                selected_types=("flawed_sequence_disorder")
                break
                ;;
            2|flawed_tool_misuse)
                selected_types=("flawed_tool_misuse")
                break
                ;;
            3|flawed_parameter_error)
                selected_types=("flawed_parameter_error")
                break
                ;;
            4|flawed_missing_step)
                selected_types=("flawed_missing_step")
                break
                ;;
            5|flawed_redundant_operations)
                selected_types=("flawed_redundant_operations")
                break
                ;;
            6|flawed_logical_inconsistency)
                selected_types=("flawed_logical_inconsistency")
                break
                ;;
            7|flawed_semantic_drift)
                selected_types=("flawed_semantic_drift")
                break
                ;;
            8|all)
                selected_types=(
                    "flawed_sequence_disorder"
                    "flawed_tool_misuse" 
                    "flawed_parameter_error"
                    "flawed_missing_step"
                    "flawed_redundant_operations"
                    "flawed_logical_inconsistency"
                    "flawed_semantic_drift"
                )
                break
                ;;
            *)
                log_warning "无效选择: $choice，请重新选择"
                ;;
        esac
    done
    
    log_info "用户选择的缺陷类型: ${selected_types[*]}"
}

# 显示模型选择
show_model_options() {
    echo -e "\n${CYAN}🤖 选择测试模型:${NC}"
    echo "1) 开源模型 (Azure + IdealLab)"
    echo "2) 闭源模型 (Azure + IdealLab)" 
    echo "3) 所有模型"
    echo "4) 单个模型"
    echo
}

# 获取模型选择
get_model_choice() {
    while true; do
        show_model_options
        read -p "请选择模型类型 (1-4): " model_choice
        
        case $model_choice in
            1)
                model_type="opensource"
                export MODEL_TYPE="opensource"
                log_info "选择开源模型进行测试"
                break
                ;;
            2)
                model_type="closed_source"
                export MODEL_TYPE="closed_source"
                log_info "选择闭源模型进行测试"
                break
                ;;
            3)
                model_type="all"
                export MODEL_TYPE="all"
                log_info "选择所有模型进行测试"
                break
                ;;
            4)
                echo -e "\n${CYAN}可用模型:${NC}"
                echo "开源: DeepSeek-V3-0324, DeepSeek-R1-0528, Llama-3.3-70B-Instruct"
                echo "     qwen2.5-72b-instruct, qwen2.5-32b-instruct, qwen2.5-14b-instruct"
                echo "     qwen2.5-7b-instruct, qwen2.5-3b-instruct"
                echo "闭源: gpt-4o-mini, gpt-5-mini, o3-0416-global, gemini-2.5-flash-06-17, kimi-k2"
                echo
                read -p "请输入具体模型名: " single_model
                model_type="single"
                # 确定单个模型的类型
                if [[ "$single_model" == *"DeepSeek"* ]] || [[ "$single_model" == *"Llama"* ]] || [[ "$single_model" == *"qwen"* ]]; then
                    export MODEL_TYPE="opensource"
                else
                    export MODEL_TYPE="closed_source"
                fi
                log_info "选择单个模型: $single_model (类型: $MODEL_TYPE)"
                break
                ;;
            *)
                log_warning "无效选择: $model_choice，请重新选择"
                ;;
        esac
    done
}

# 运行单个模型的测试
run_single_model_test() {
    local prompt_type="$1"
    local model_name="$2"
    
    log_info "🚀 开始测试 - 模型: $model_name, 缺陷类型: $prompt_type"
    
    local sanitized_model=$(echo "$model_name" | tr '.' '_' | tr '-' '_')
    local test_log="$LOG_DIR/ultra_parallel_${sanitized_model}_${prompt_type}_${TIMESTAMP}.log"
    
    # 构建命令 - 严格匹配run_systematic_test_final.sh中run_smart_test的ultra_parallel_runner调用
    # 对于qwen模型，强制使用--max-workers 1避免限流（匹配system bash逻辑）
    local workers_param=""
    if [[ "$model_name" == *"qwen"* ]]; then
        workers_param="--max-workers 1"
    else
        workers_param="--max-workers $CUSTOM_WORKERS"
    fi
    
    local python_cmd=(
        "python3" "./ultra_parallel_runner.py"
        "--model" "$model_name"
        "--prompt-types" "$prompt_type" 
        "--difficulty" "easy"
        "--task-types" "all"
        "--num-instances" "20"
        "--rate-mode" "fixed"
        $workers_param
    )
    
    log_info "执行命令: USE_RESULT_COLLECTOR='$USE_RESULT_COLLECTOR' STORAGE_FORMAT='$STORAGE_FORMAT' KMP_DUPLICATE_LIB_OK=TRUE ${python_cmd[*]}"
    
    # 运行测试 - 匹配system bash的输出方式，同时保存日志和显示实时输出
    echo "=== 测试开始时间: $(date) ===" | tee "$test_log"
    echo "=== 环境变量 ===" | tee -a "$test_log"
    echo "USE_RESULT_COLLECTOR=$USE_RESULT_COLLECTOR" | tee -a "$test_log"
    echo "STORAGE_FORMAT=$STORAGE_FORMAT" | tee -a "$test_log"
    echo "CUSTOM_WORKERS=$CUSTOM_WORKERS" | tee -a "$test_log"
    echo "=== 命令执行 ===" | tee -a "$test_log"
    
    # 匹配run_systematic_test_final.sh中的环境变量传递方式，并使用tee同时显示和保存输出
    USE_RESULT_COLLECTOR="$USE_RESULT_COLLECTOR" STORAGE_FORMAT="$STORAGE_FORMAT" KMP_DUPLICATE_LIB_OK=TRUE "${python_cmd[@]}" 2>&1 | tee -a "$test_log"
    exit_code=${PIPESTATUS[0]}
    
    echo "=== 测试结束时间: $(date) ===" | tee -a "$test_log"
    echo "=== 退出码: $exit_code ===" | tee -a "$test_log"
    
    local test_result=$exit_code
    
    # 检查结果
    if [[ $test_result -eq 0 ]]; then
        log_success "✅ 模型 $model_name 测试完成"
        log_info "详细日志: $test_log"
        
        # 检查输出文件大小
        if [[ -f "$test_log" ]]; then
            local log_size=$(wc -l < "$test_log")
            log_info "日志行数: $log_size"
        fi
        return 0
    else
        log_error "❌ 模型 $model_name 测试失败 (退出码: $test_result)"
        log_error "检查日志: $test_log"
        
        # 显示错误详情和traceback
        if [[ -f "$test_log" ]]; then
            log_error "=== 最后50行日志内容 ==="
            tail -50 "$test_log" | while IFS= read -r line; do
                log_error "  $line"
            done
            log_error "=== 日志结束 ==="
            
            # 特别检查Python traceback
            if grep -q "Traceback\|Error\|Exception" "$test_log"; then
                log_error "=== Python错误traceback ==="
                grep -A 20 -B 5 "Traceback\|Error\|Exception" "$test_log" | while IFS= read -r line; do
                    log_error "  $line"
                done
                log_error "=== Traceback结束 ==="
            fi
        else
            log_error "日志文件不存在: $test_log"
        fi
        
        return 1
    fi
}

# 运行所有选定模型的测试
run_test() {
    local prompt_type="$1"
    local model_list="$2"
    
    log_info "🚀 开始测试 - 缺陷类型: $prompt_type"
    
    local failed_models=()
    local successful_models=()
    
    # 将模型字符串转换为数组
    local models=($model_list)
    local total_models=${#models[@]}
    local current=0
    
    for model in "${models[@]}"; do
        ((current++))
        log_info "进度: $current/$total_models - 测试模型: $model"
        
        if run_single_model_test "$prompt_type" "$model"; then
            successful_models+=("$model")
        else
            failed_models+=("$model")
        fi
        
        # 模型间隔时间
        if [[ $current -lt $total_models ]]; then
            log_info "等待 3 秒后测试下一个模型..."
            sleep 3
        fi
    done
    
    # 报告结果
    log_info "缺陷类型 $prompt_type 测试完成："
    log_success "成功: ${#successful_models[@]}/${total_models} 模型"
    
    if [[ ${#failed_models[@]} -gt 0 ]]; then
        log_warning "失败的模型: ${failed_models[*]}"
        return 1
    else
        log_success "所有模型都测试成功！"
        return 0
    fi
}

# 获取模型列表
get_model_list() {
    case $model_type in
        "opensource")
            echo "DeepSeek-V3-0324 DeepSeek-R1-0528 Llama-3.3-70B-Instruct qwen2.5-72b-instruct qwen2.5-32b-instruct qwen2.5-14b-instruct qwen2.5-7b-instruct qwen2.5-3b-instruct"
            ;;
        "closed_source") 
            echo "gpt-4o-mini gpt-5-mini o3-0416-global gemini-2.5-flash-06-17 kimi-k2"
            ;;
        "all")
            echo "DeepSeek-V3-0324 DeepSeek-R1-0528 Llama-3.3-70B-Instruct qwen2.5-72b-instruct qwen2.5-32b-instruct qwen2.5-14b-instruct qwen2.5-7b-instruct qwen2.5-3b-instruct gpt-4o-mini gpt-5-mini o3-0416-global gemini-2.5-flash-06-17 kimi-k2"
            ;;
        "single")
            echo "$single_model"
            ;;
    esac
}

# 显示进度
show_progress() {
    local current=$1
    local total=$2
    local prompt_type=$3
    
    local percent=$((current * 100 / total))
    echo -e "\n${PURPLE}📊 测试进度: ${current}/${total} (${percent}%) - 当前: ${prompt_type}${NC}\n"
}

# 主函数
main() {
    log_info "检查环境和依赖文件..."
    check_files
    
    log_info "获取用户选择..."
    get_user_choice
    get_model_choice
    
    local model_list=$(get_model_list)
    local total_tests=${#selected_types[@]}
    local completed=0
    local failed_tests=()
    
    # 计算总模型数
    local models=($model_list)
    local total_models=${#models[@]}
    
    log_info "开始执行 5.3 缺陷工作流测试"
    log_info "缺陷类型数: $total_tests"
    log_info "测试模型数: $total_models"
    log_info "总测试组合: $((total_tests * total_models))"
    log_info "模型配置: $model_type"
    log_info "并发配置: $CUSTOM_WORKERS workers, $MAX_PARALLEL_PROCESSES processes"
    log_info "存储配置: JSON + ResultCollector"
    
    echo -e "\n${GREEN}🎯 测试配置确认:${NC}"
    echo "- 缺陷类型: ${selected_types[*]}"
    echo "- 模型选择: $model_type ($total_models 个模型)"
    echo "- 测试模型: ${models[*]}"
    echo "- 并发设置: $CUSTOM_WORKERS workers"
    echo "- 存储方式: JSON + ResultCollector"
    echo "- 日志目录: $LOG_DIR"
    echo "- 总测试组合: $((total_tests * total_models))"
    echo
    
    read -p "确认开始测试? [y/N]: " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        log_info "测试已取消"
        exit 0
    fi
    
    # 执行所有选定的测试
    for prompt_type in "${selected_types[@]}"; do
        ((completed++))
        show_progress $completed $total_tests "$prompt_type"
        
        if run_test "$prompt_type" "$model_list"; then
            log_success "✅ 完成: $prompt_type"
        else
            log_error "❌ 失败: $prompt_type"
            failed_tests+=("$prompt_type")
        fi
        
        # 测试间隔
        if [[ $completed -lt $total_tests ]]; then
            log_info "等待 10 秒后继续下一个缺陷类型..."
            sleep 10
        fi
    done
    
    # 最终报告
    echo -e "\n${CYAN}📋 测试完成报告${NC}"
    echo "================================"
    echo "总测试数: $total_tests"
    echo "成功: $((total_tests - ${#failed_tests[@]}))"
    echo "失败: ${#failed_tests[@]}"
    
    if [[ ${#failed_tests[@]} -gt 0 ]]; then
        echo -e "\n${RED}失败的测试:${NC}"
        for failed in "${failed_tests[@]}"; do
            echo "  - $failed"
        done
        log_warning "部分测试失败，请检查日志"
        exit 1
    else
        log_success "🎉 所有测试都成功完成!"
        echo -e "\n${GREEN}🎉 所有测试都成功完成!${NC}"
        exit 0
    fi
}

# 信号处理
cleanup() {
    log_warning "接收到中断信号，正在清理..."
    # 杀死所有子进程
    pkill -f "ultra_parallel_runner.py" 2>/dev/null || true
    pkill -f "smart_batch_runner.py" 2>/dev/null || true
    log_info "清理完成"
    exit 130
}

trap cleanup SIGINT SIGTERM

# 运行主函数
main "$@"