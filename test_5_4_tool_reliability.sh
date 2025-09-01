#!/bin/bash

# 5.4 工具可靠性测试完整脚本
# 基于test_5_1_complete_retest.sh修改，用于测试所有8个开源模型的5.4工具可靠性数据
# 配置: optimal prompt + easy难度 + 90%/70%/60%工具成功率（80%使用5.1结果）

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
LOG_FILE="$LOG_DIR/test_5_4_tool_reliability_${TIMESTAMP}.log"

# 5.4 固定配置
PROMPT_TYPE="optimal"
DIFFICULTY="easy"
TOOL_SUCCESS_RATES=("0.9" "0.7" "0.6")  # 90%, 70%, 60% (80%使用5.1结果)

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

log_info "=== 5.4 工具可靠性测试完整脚本启动 ==="
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

# 开源模型列表 - 完整8个模型
OPENSOURCE_MODELS=(
    "DeepSeek-V3-0324"
    "DeepSeek-R1-0528" 
    "Llama-3.3-70B-Instruct"
    "qwen2.5-72b-instruct"
    "qwen2.5-32b-instruct"
    "qwen2.5-14b-instruct"
    "qwen2.5-7b-instruct"
    "qwen2.5-3b-instruct"
)

# 显示5.4配置
show_config() {
    echo -e "\n${CYAN}📋 5.4工具可靠性测试配置:${NC}"
    echo "- Prompt类型: ${GREEN}$PROMPT_TYPE${NC}"
    echo "- 难度等级: ${GREEN}$DIFFICULTY${NC}"
    echo "- 工具成功率: ${GREEN}${TOOL_SUCCESS_RATES[*]}${NC} (80%使用5.1结果)"
    echo "- 并发设置: ${GREEN}$CUSTOM_WORKERS${NC} workers"
    echo "- 存储方式: ${GREEN}JSON + ResultCollector${NC}"
    echo
    
    echo -e "${CYAN}🤖 测试模型列表 (${#OPENSOURCE_MODELS[@]}个开源模型):${NC}"
    local i=1
    for model in "${OPENSOURCE_MODELS[@]}"; do
        echo "  $i) $model"
        ((i++))
    done
    echo
    
    echo -e "${CYAN}🔧 测试工具成功率组合:${NC}"
    for rate in "${TOOL_SUCCESS_RATES[@]}"; do
        local percentage=$(echo "$rate * 100" | bc)
        echo "  📊 ${percentage%.*}% 工具成功率"
    done
    echo "  📊 80% 工具成功率 (使用5.1基准测试结果)"
    echo
}

# 显示模型选择
show_model_options() {
    echo -e "${CYAN}🤖 选择测试范围:${NC}"
    echo "1) 所有模型 × 所有工具成功率 (推荐)"
    echo "2) 单个模型 × 所有工具成功率"
    echo "3) 所有模型 × 单个工具成功率"
    echo "4) 单个模型 × 单个工具成功率"
    echo "5) 只运行预测试"
    echo
}

# 获取模型选择
get_model_choice() {
    while true; do
        show_model_options
        read -p "请选择测试范围 (1-5): " model_choice
        
        case $model_choice in
            1)
                test_models=("${OPENSOURCE_MODELS[@]}")
                test_rates=("${TOOL_SUCCESS_RATES[@]}")
                test_mode="all"
                log_info "选择测试所有${#test_models[@]}个模型 × ${#test_rates[@]}个工具成功率"
                break
                ;;
            2)
                echo -e "\n${CYAN}可用模型:${NC}"
                local i=1
                for model in "${OPENSOURCE_MODELS[@]}"; do
                    echo "  $i) $model"
                    ((i++))
                done
                echo
                read -p "请输入模型编号或名称: " single_choice
                
                if [[ "$single_choice" =~ ^[0-9]+$ ]] && [[ $single_choice -ge 1 ]] && [[ $single_choice -le ${#OPENSOURCE_MODELS[@]} ]]; then
                    test_models=("${OPENSOURCE_MODELS[$((single_choice-1))]}")
                else
                    # 检查是否为有效模型名
                    local found=false
                    for model in "${OPENSOURCE_MODELS[@]}"; do
                        if [[ "$model" == "$single_choice" ]]; then
                            test_models=("$model")
                            found=true
                            break
                        fi
                    done
                    if [[ "$found" == false ]]; then
                        log_warning "无效选择: $single_choice，请重新选择"
                        continue
                    fi
                fi
                test_rates=("${TOOL_SUCCESS_RATES[@]}")
                test_mode="single_model"
                log_info "选择单个模型: ${test_models[0]} × ${#test_rates[@]}个工具成功率"
                break
                ;;
            3)
                echo -e "\n${CYAN}可用工具成功率:${NC}"
                for i in "${!TOOL_SUCCESS_RATES[@]}"; do
                    local rate="${TOOL_SUCCESS_RATES[$i]}"
                    local percentage=$(echo "$rate * 100" | bc)
                    echo "  $((i+1))) ${percentage%.*}%"
                done
                echo
                read -p "请输入工具成功率编号: " rate_choice
                
                if [[ "$rate_choice" =~ ^[0-9]+$ ]] && [[ $rate_choice -ge 1 ]] && [[ $rate_choice -le ${#TOOL_SUCCESS_RATES[@]} ]]; then
                    test_rates=("${TOOL_SUCCESS_RATES[$((rate_choice-1))]}")
                else
                    log_warning "无效选择: $rate_choice，请重新选择"
                    continue
                fi
                test_models=("${OPENSOURCE_MODELS[@]}")
                test_mode="single_rate"
                local percentage=$(echo "${test_rates[0]} * 100" | bc)
                log_info "选择所有${#test_models[@]}个模型 × ${percentage%.*}%工具成功率"
                break
                ;;
            4)
                # 单个模型 + 单个工具成功率
                echo -e "\n${CYAN}选择模型:${NC}"
                local i=1
                for model in "${OPENSOURCE_MODELS[@]}"; do
                    echo "  $i) $model"
                    ((i++))
                done
                echo
                read -p "请输入模型编号: " model_num
                
                if [[ "$model_num" =~ ^[0-9]+$ ]] && [[ $model_num -ge 1 ]] && [[ $model_num -le ${#OPENSOURCE_MODELS[@]} ]]; then
                    test_models=("${OPENSOURCE_MODELS[$((model_num-1))]}")
                else
                    log_warning "无效选择: $model_num，请重新选择"
                    continue
                fi
                
                echo -e "\n${CYAN}选择工具成功率:${NC}"
                for i in "${!TOOL_SUCCESS_RATES[@]}"; do
                    local rate="${TOOL_SUCCESS_RATES[$i]}"
                    local percentage=$(echo "$rate * 100" | bc)
                    echo "  $((i+1))) ${percentage%.*}%"
                done
                echo
                read -p "请输入工具成功率编号: " rate_num
                
                if [[ "$rate_num" =~ ^[0-9]+$ ]] && [[ $rate_num -ge 1 ]] && [[ $rate_num -le ${#TOOL_SUCCESS_RATES[@]} ]]; then
                    test_rates=("${TOOL_SUCCESS_RATES[$((rate_num-1))]}")
                else
                    log_warning "无效选择: $rate_num，请重新选择"
                    continue
                fi
                
                test_mode="single_both"
                local percentage=$(echo "${test_rates[0]} * 100" | bc)
                log_info "选择: ${test_models[0]} × ${percentage%.*}%工具成功率"
                break
                ;;
            5)
                test_models=("qwen2.5-3b-instruct")  # 使用最小模型预测试
                test_rates=("0.9")  # 使用第一个工具成功率
                test_mode="pretest"
                log_info "选择预测试模式，使用模型: ${test_models[0]}, 工具成功率: 90%"
                break
                ;;
            *)
                log_warning "无效选择: $model_choice，请重新选择"
                ;;
        esac
    done
}

# 运行单个模型+工具成功率的测试
run_single_test() {
    local model_name="$1"
    local tool_rate="$2"
    local test_index="$3"
    local total_tests="$4"
    
    local percentage=$(echo "$tool_rate * 100" | bc)
    log_info "🚀 开始测试 [$test_index/$total_tests] - 模型: $model_name, 工具成功率: ${percentage%.*}%"
    log_info "配置: $PROMPT_TYPE + $DIFFICULTY + 工具成功率$tool_rate"
    
    local sanitized_model=$(echo "$model_name" | tr '.' '_' | tr '-' '_')
    local sanitized_rate=$(echo "$tool_rate" | tr '.' '_')
    local test_log="$LOG_DIR/ultra_parallel_${sanitized_model}_${PROMPT_TYPE}_rate_${sanitized_rate}_${TIMESTAMP}.log"
    
    # 构建命令 - 完全匹配custom 5.1的成功参数
    local workers_param=""
    if [[ "$model_name" == *"qwen"* ]]; then
        workers_param="--max-workers 1"
        log_info "qwen模型使用限流配置: 1 worker"
    else
        workers_param="--max-workers $CUSTOM_WORKERS"
        log_info "Azure模型使用高并发配置: $CUSTOM_WORKERS workers"
    fi
    
    local python_cmd=(
        "python3" "./ultra_parallel_runner.py"
        "--model" "$model_name"
        "--prompt-types" "optimal" 
        "--difficulty" "easy"
        "--task-types" "all"
        "--num-instances" "20"
        "--rate-mode" "fixed"
        "--tool-success-rate" "$tool_rate"
        $workers_param
    )
    
    log_info "执行命令: USE_RESULT_COLLECTOR='$USE_RESULT_COLLECTOR' STORAGE_FORMAT='$STORAGE_FORMAT' KMP_DUPLICATE_LIB_OK=TRUE ${python_cmd[*]}"
    
    # DEBUG: 显示完整的命令数组内容
    echo "=== DEBUG: 命令数组详情 ===" | tee -a "$test_log"
    for i in "${!python_cmd[@]}"; do
        echo "  [$i]: '${python_cmd[$i]}'" | tee -a "$test_log"
    done
    echo "=== DEBUG: 准备执行 ===" | tee -a "$test_log"
    
    # 运行测试 - 匹配system bash的输出方式，同时保存日志和显示实时输出
    echo "=== 测试开始时间: $(date) ===" | tee "$test_log"
    echo "=== 环境变量 ===" | tee -a "$test_log"
    echo "USE_RESULT_COLLECTOR=$USE_RESULT_COLLECTOR" | tee -a "$test_log"
    echo "STORAGE_FORMAT=$STORAGE_FORMAT" | tee -a "$test_log"
    echo "CUSTOM_WORKERS=$CUSTOM_WORKERS" | tee -a "$test_log"
    echo "=== 5.4配置 ===" | tee -a "$test_log"
    echo "PROMPT_TYPE=$PROMPT_TYPE" | tee -a "$test_log"
    echo "DIFFICULTY=$DIFFICULTY" | tee -a "$test_log"
    echo "TOOL_SUCCESS_RATE=$tool_rate" | tee -a "$test_log"
    echo "=== 命令执行 ===" | tee -a "$test_log"
    
    # 记录开始时间
    local start_time=$(date +%s)
    
    # 匹配run_systematic_test_final.sh中的环境变量传递方式，并使用tee同时显示和保存输出
    USE_RESULT_COLLECTOR="$USE_RESULT_COLLECTOR" STORAGE_FORMAT="$STORAGE_FORMAT" KMP_DUPLICATE_LIB_OK=TRUE "${python_cmd[@]}" 2>&1 | tee -a "$test_log"
    exit_code=${PIPESTATUS[0]}
    
    # 记录结束时间
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))
    
    echo "=== 测试结束时间: $(date) ===" | tee -a "$test_log"
    echo "=== 测试用时: ${minutes}分${seconds}秒 ===" | tee -a "$test_log"
    echo "=== 退出码: $exit_code ===" | tee -a "$test_log"
    
    # 检查结果
    if [[ $exit_code -eq 0 ]]; then
        log_success "✅ 模型 $model_name (${percentage%.*}%工具成功率) 测试完成 (${minutes}分${seconds}秒)"
        log_info "详细日志: $test_log"
        
        # 快速验证数据是否保存
        log_info "验证数据保存情况..."
        if python3 extract_experiment_results.py 5.4 2>/dev/null | grep -q "$model_name.*${percentage%.*}%"; then
            log_success "✅ 数据已保存到数据库"
        else
            log_warning "⚠️  数据库中未找到结果，可能需要手动检查"
        fi
        
        return 0
    else
        log_error "❌ 模型 $model_name (${percentage%.*}%工具成功率) 测试失败 (退出码: $exit_code, 用时: ${minutes}分${seconds}秒)"
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

# 主测试函数
run_tests() {
    local total_tests=$((${#test_models[@]} * ${#test_rates[@]}))
    local successful_tests=0
    local failed_tests=0
    local current=0
    
    log_info "🚀 开始执行 5.4 工具可靠性测试"
    log_info "测试模型数: ${#test_models[@]}"
    log_info "工具成功率数: ${#test_rates[@]}"
    log_info "总测试组合: $total_tests"
    log_info "并发配置: $CUSTOM_WORKERS workers, $MAX_PARALLEL_PROCESSES processes"
    log_info "存储配置: JSON + ResultCollector"
    
    # 记录总开始时间
    local total_start_time=$(date +%s)
    
    for model in "${test_models[@]}"; do
        for rate in "${test_rates[@]}"; do
            ((current++))
            
            if run_single_test "$model" "$rate" "$current" "$total_tests"; then
                ((successful_tests++))
            else
                ((failed_tests++))
                
                # 询问是否继续
                if [[ "$test_mode" != "pretest" ]] && [[ $current -lt $total_tests ]]; then
                    read -p "测试失败，是否继续测试下一个组合? [Y/n]: " continue_choice
                    if [[ "$continue_choice" =~ ^[Nn]$ ]]; then
                        log_warning "用户选择停止测试"
                        break 2
                    fi
                fi
            fi
            
            # 测试间隔时间（预测试不需要间隔）
            if [[ $current -lt $total_tests ]] && [[ "$test_mode" != "pretest" ]]; then
                log_info "等待 10 秒后测试下一个组合..."
                sleep 10
            fi
        done
    done
    
    # 计算总时间
    local total_end_time=$(date +%s)
    local total_duration=$((total_end_time - total_start_time))
    local total_hours=$((total_duration / 3600))
    local total_minutes=$(((total_duration % 3600) / 60))
    local total_seconds=$((total_duration % 60))
    
    # 最终报告
    echo -e "\n${CYAN}📋 5.4工具可靠性测试完成报告${NC}"
    echo "======================================="
    echo "测试模式: $test_mode"
    echo "总测试组合: $total_tests"
    echo "成功: ${GREEN}${successful_tests}${NC}"
    echo "失败: ${RED}${failed_tests}${NC}"
    echo "总用时: ${total_hours}时${total_minutes}分${total_seconds}秒"
    echo
    
    # 生成最新结果报告
    if [[ ${#successful_tests} -gt 0 ]] && [[ "$test_mode" != "pretest" ]]; then
        log_info "生成最新5.4测试结果..."
        python3 extract_experiment_results.py 5.4 > /tmp/5_4_latest_results.txt 2>&1
        if [[ -s /tmp/5_4_latest_results.txt ]]; then
            echo -e "\n${CYAN}📊 最新5.4测试结果概览:${NC}"
            head -20 /tmp/5_4_latest_results.txt
            log_success "完整结果报告: /tmp/5_4_latest_results.txt"
        fi
    fi
    
    if [[ ${failed_tests} -gt 0 ]]; then
        return 1
    else
        log_success "🎉 所有测试都成功完成!"
        return 0
    fi
}

# 主函数
main() {
    log_info "检查环境和依赖文件..."
    check_files
    
    log_info "显示配置信息..."
    show_config
    
    log_info "获取用户选择..."
    get_model_choice
    
    echo -e "\n${GREEN}🎯 测试配置确认:${NC}"
    echo "- 测试类型: 5.4工具可靠性测试 (optimal + easy + 多工具成功率)"
    echo "- 测试模式: $test_mode"
    echo "- 测试模型: ${test_models[*]}"
    echo "- 工具成功率: ${test_rates[*]}"
    echo "- 并发设置: $CUSTOM_WORKERS workers"
    echo "- 存储方式: JSON + ResultCollector"
    echo "- 日志目录: $LOG_DIR"
    echo "- 预计时间: $((${#test_models[@]} * ${#test_rates[@]} * 20))分钟 (每组合约20分钟)"
    echo
    
    if [[ "$test_mode" != "pretest" ]]; then
        read -p "确认开始测试? [y/N]: " confirm
        if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
            log_info "测试已取消"
            exit 0
        fi
    fi
    
    # 执行测试
    if run_tests; then
        log_success "🎉 5.4工具可靠性测试完成!"
        exit 0
    else
        log_error "测试过程中出现失败"
        exit 1
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