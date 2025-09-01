#!/bin/bash

# 5.1 基准测试完整重测脚本
# 基于test_5_3_custom.sh修改，用于重测所有8个开源模型的5.1基准数据
# 配置: optimal prompt + easy难度 + 0.8工具成功率

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
LOG_FILE="$LOG_DIR/test_5_1_complete_retest_${TIMESTAMP}.log"

# 5.1 固定配置
PROMPT_TYPE="optimal"
DIFFICULTY="easy"
TOOL_SUCCESS_RATE="0.8"

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

log_info "=== 5.1 基准测试完整重测脚本启动 ==="
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

# 显示5.1配置
show_config() {
    echo -e "\n${CYAN}📋 5.1基准测试重测配置:${NC}"
    echo "- Prompt类型: ${GREEN}$PROMPT_TYPE${NC}"
    echo "- 难度等级: ${GREEN}$DIFFICULTY${NC}"
    echo "- 工具成功率: ${GREEN}$TOOL_SUCCESS_RATE${NC}"
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
}

# 显示模型选择
show_model_options() {
    echo -e "${CYAN}🤖 选择测试范围:${NC}"
    echo "1) 所有模型 (推荐)"
    echo "2) 单个模型"
    echo "3) 从某个模型开始"
    echo "4) 只运行预测试"
    echo
}

# 获取模型选择
get_model_choice() {
    while true; do
        show_model_options
        read -p "请选择测试范围 (1-4): " model_choice
        
        case $model_choice in
            1)
                test_models=("${OPENSOURCE_MODELS[@]}")
                test_mode="all"
                log_info "选择测试所有${#test_models[@]}个模型"
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
                test_mode="single"
                log_info "选择单个模型: ${test_models[0]}"
                break
                ;;
            3)
                echo -e "\n${CYAN}从哪个模型开始:${NC}"
                local i=1
                for model in "${OPENSOURCE_MODELS[@]}"; do
                    echo "  $i) $model"
                    ((i++))
                done
                echo
                read -p "请输入起始模型编号或名称: " start_choice
                
                local start_index=-1
                if [[ "$start_choice" =~ ^[0-9]+$ ]] && [[ $start_choice -ge 1 ]] && [[ $start_choice -le ${#OPENSOURCE_MODELS[@]} ]]; then
                    start_index=$((start_choice-1))
                else
                    # 查找模型名对应的索引
                    for i in "${!OPENSOURCE_MODELS[@]}"; do
                        if [[ "${OPENSOURCE_MODELS[$i]}" == "$start_choice" ]]; then
                            start_index=$i
                            break
                        fi
                    done
                fi
                
                if [[ $start_index -eq -1 ]]; then
                    log_warning "无效选择: $start_choice，请重新选择"
                    continue
                fi
                
                # 从指定模型开始到结束
                test_models=()
                for (( i=start_index; i<${#OPENSOURCE_MODELS[@]}; i++ )); do
                    test_models+=("${OPENSOURCE_MODELS[$i]}")
                done
                test_mode="from_start"
                log_info "从模型 ${OPENSOURCE_MODELS[$start_index]} 开始，共${#test_models[@]}个模型"
                break
                ;;
            4)
                test_models=("qwen2.5-3b-instruct")  # 使用最小模型预测试
                test_mode="pretest"
                log_info "选择预测试模式，使用模型: ${test_models[0]}"
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
    local model_name="$1"
    local model_index="$2"
    local total_models="$3"
    
    log_info "🚀 开始测试 [$model_index/$total_models] - 模型: $model_name"
    log_info "配置: $PROMPT_TYPE + $DIFFICULTY + 工具成功率$TOOL_SUCCESS_RATE"
    
    local sanitized_model=$(echo "$model_name" | tr '.' '_' | tr '-' '_')
    local test_log="$LOG_DIR/ultra_parallel_${sanitized_model}_${PROMPT_TYPE}_${TIMESTAMP}.log"
    
    # 构建命令 - 严格匹配run_systematic_test_final.sh中run_smart_test的ultra_parallel_runner调用
    # 对于qwen模型，强制使用--max-workers 1避免限流（匹配system bash逻辑）
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
    echo "=== 5.1配置 ===" | tee -a "$test_log"
    echo "PROMPT_TYPE=$PROMPT_TYPE" | tee -a "$test_log"
    echo "DIFFICULTY=$DIFFICULTY" | tee -a "$test_log"
    echo "TOOL_SUCCESS_RATE=$TOOL_SUCCESS_RATE" | tee -a "$test_log"
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
        log_success "✅ 模型 $model_name 测试完成 (${minutes}分${seconds}秒)"
        log_info "详细日志: $test_log"
        
        # 快速验证数据是否保存
        log_info "验证数据保存情况..."
        if python3 extract_experiment_results.py 5.1 2>/dev/null | grep -q "$model_name"; then
            log_success "✅ 数据已保存到数据库"
        else
            log_warning "⚠️  数据库中未找到结果，可能需要手动检查"
        fi
        
        return 0
    else
        log_error "❌ 模型 $model_name 测试失败 (退出码: $exit_code, 用时: ${minutes}分${seconds}秒)"
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
    local total_models=${#test_models[@]}
    local successful_models=()
    local failed_models=()
    local current=0
    
    log_info "🚀 开始执行 5.1 基准测试"
    log_info "测试模型数: $total_models"
    log_info "并发配置: $CUSTOM_WORKERS workers, $MAX_PARALLEL_PROCESSES processes"
    log_info "存储配置: JSON + ResultCollector"
    
    # 记录总开始时间
    local total_start_time=$(date +%s)
    
    for model in "${test_models[@]}"; do
        ((current++))
        
        if run_single_model_test "$model" "$current" "$total_models"; then
            successful_models+=("$model")
        else
            failed_models+=("$model")
            
            # 询问是否继续
            if [[ "$test_mode" != "pretest" ]] && [[ $current -lt $total_models ]]; then
                read -p "模型 $model 测试失败，是否继续测试下一个模型? [Y/n]: " continue_choice
                if [[ "$continue_choice" =~ ^[Nn]$ ]]; then
                    log_warning "用户选择停止测试"
                    break
                fi
            fi
        fi
        
        # 模型间隔时间（预测试不需要间隔）
        if [[ $current -lt $total_models ]] && [[ "$test_mode" != "pretest" ]]; then
            log_info "等待 10 秒后测试下一个模型..."
            sleep 10
        fi
    done
    
    # 计算总时间
    local total_end_time=$(date +%s)
    local total_duration=$((total_end_time - total_start_time))
    local total_hours=$((total_duration / 3600))
    local total_minutes=$(((total_duration % 3600) / 60))
    local total_seconds=$((total_duration % 60))
    
    # 最终报告
    echo -e "\n${CYAN}📋 5.1基准测试重测完成报告${NC}"
    echo "======================================="
    echo "测试模式: $test_mode"
    echo "总模型数: $total_models"
    echo "成功: ${GREEN}${#successful_models[@]}${NC}"
    echo "失败: ${RED}${#failed_models[@]}${NC}"
    echo "总用时: ${total_hours}时${total_minutes}分${total_seconds}秒"
    echo
    
    if [[ ${#successful_models[@]} -gt 0 ]]; then
        echo -e "${GREEN}成功的模型:${NC}"
        for model in "${successful_models[@]}"; do
            echo "  ✅ $model"
        done
        echo
    fi
    
    if [[ ${#failed_models[@]} -gt 0 ]]; then
        echo -e "${RED}失败的模型:${NC}"
        for model in "${failed_models[@]}"; do
            echo "  ❌ $model"
        done
        echo
        log_warning "部分模型测试失败，请检查日志"
        
        if [[ "$test_mode" == "pretest" ]]; then
            log_error "预测试失败，请检查环境配置"
            return 1
        fi
    fi
    
    # 生成最新结果报告
    if [[ ${#successful_models[@]} -gt 0 ]] && [[ "$test_mode" != "pretest" ]]; then
        log_info "生成最新5.1测试结果..."
        python3 extract_experiment_results.py 5.1 > /tmp/5_1_latest_results.txt 2>&1
        if [[ -s /tmp/5_1_latest_results.txt ]]; then
            echo -e "\n${CYAN}📊 最新5.1测试结果概览:${NC}"
            head -20 /tmp/5_1_latest_results.txt
            log_success "完整结果报告: /tmp/5_1_latest_results.txt"
        fi
    fi
    
    if [[ ${#failed_models[@]} -gt 0 ]]; then
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
    echo "- 测试类型: 5.1基准测试 (optimal + easy + 0.8)"
    echo "- 测试模式: $test_mode"
    echo "- 测试模型: ${test_models[*]}"
    echo "- 并发设置: $CUSTOM_WORKERS workers"
    echo "- 存储方式: JSON + ResultCollector"
    echo "- 日志目录: $LOG_DIR"
    echo "- 预计时间: $((${#test_models[@]} * 20))分钟 (每模型约20分钟)"
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
        log_success "🎉 5.1基准测试重测完成!"
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