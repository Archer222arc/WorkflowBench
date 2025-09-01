#!/bin/bash
# 5.1基准测试完整重测脚本
# 基于test_5_3_custom.sh修改，用于重测所有8个开源模型的5.1基准数据

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 固定的5.1测试配置
PROMPT_TYPE="optimal"
DIFFICULTY="easy" 
TOOL_SUCCESS_RATE="0.8"

# 开源模型列表
MODELS=(
    "DeepSeek-V3-0324"
    "DeepSeek-R1-0528"
    "Llama-3.3-70B-Instruct"
    "qwen2.5-72b-instruct"
    "qwen2.5-32b-instruct"
    "qwen2.5-14b-instruct"
    "qwen2.5-7b-instruct"
    "qwen2.5-3b-instruct"
)

# 获取模型显示名函数
get_model_display_name() {
    case "$1" in
        "DeepSeek-V3-0324") echo "🤖 DeepSeek-V3-0324" ;;
        "DeepSeek-R1-0528") echo "🧠 DeepSeek-R1-0528" ;;
        "Llama-3.3-70B-Instruct") echo "🦙 Llama-3.3-70B-Instruct" ;;
        "qwen2.5-72b-instruct") echo "🌟 Qwen2.5-72B-Instruct" ;;
        "qwen2.5-32b-instruct") echo "⭐ Qwen2.5-32B-Instruct" ;;
        "qwen2.5-14b-instruct") echo "✨ Qwen2.5-14B-Instruct" ;;
        "qwen2.5-7b-instruct") echo "💫 Qwen2.5-7B-Instruct" ;;
        "qwen2.5-3b-instruct") echo "🔸 Qwen2.5-3B-Instruct" ;;
        *) echo "$1" ;;
    esac
}

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
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

log_header() {
    echo -e "\n${PURPLE}========================================${NC}"
    echo -e "${PURPLE} $1${NC}"
    echo -e "${PURPLE}========================================${NC}\n"
}

# 检查脚本依赖
check_dependencies() {
    log_info "检查脚本依赖..."
    
    if [ ! -f "run_systematic_test_final.sh" ]; then
        log_error "未找到 run_systematic_test_final.sh"
        exit 1
    fi
    
    if [ ! -f "pilot_bench_cumulative_results/master_database.json" ]; then
        log_error "未找到数据库文件"
        exit 1
    fi
    
    log_success "所有依赖检查通过"
}

# 显示5.1配置信息
show_config() {
    log_header "5.1基准测试重测配置"
    echo -e "📋 ${CYAN}测试配置${NC}:"
    echo -e "  Prompt类型: ${GREEN}${PROMPT_TYPE}${NC}"
    echo -e "  难度等级: ${GREEN}${DIFFICULTY}${NC}"
    echo -e "  工具成功率: ${GREEN}${TOOL_SUCCESS_RATE}${NC}"
    echo -e "\n🤖 ${CYAN}测试模型 (${#MODELS[@]}个)${NC}:"
    for model in "${MODELS[@]}"; do
        echo -e "  $(get_model_display_name "$model")"
    done
    echo ""
}

# 预测试试运行
run_pretest() {
    local test_model="qwen2.5-3b-instruct"  # 使用最小模型进行预测试
    
    log_header "预测试 - $(get_model_display_name "$test_model")"
    log_info "运行小规模预测试验证脚本功能..."
    
    # 运行1个测试用例验证
    ./run_systematic_test_final.sh \
        --model "$test_model" \
        --phase "5.1" \
        --num-instances 1 \
        --workers 5 \
        --auto || {
        log_error "预测试失败，请检查脚本配置"
        exit 1
    }
    
    log_success "预测试完成"
}

# 运行单个模型测试
run_model_test() {
    local model="$1"
    local model_index="$2"
    local total_models="$3"
    
    log_header "模型 ${model_index}/${total_models}: $(get_model_display_name "$model")"
    
    local start_time=$(date +%s)
    
    log_info "开始5.1基准测试..."
    log_info "配置: ${PROMPT_TYPE} + ${DIFFICULTY} + ${TOOL_SUCCESS_RATE}"
    
    # 根据模型类型设置worker数量
    local workers=50
    if [[ "$model" == qwen* ]]; then
        workers=3  # qwen模型使用较少worker避免限流
    fi
    
    # 运行测试
    if ./run_systematic_test_final.sh \
        --model "$model" \
        --phase "5.1" \
        --workers "$workers" \
        --auto; then
        
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        local minutes=$((duration / 60))
        local seconds=$((duration % 60))
        
        log_success "$(get_model_display_name "$model") 测试完成 (${minutes}分${seconds}秒)"
        
        # 快速验证测试结果
        if python3 extract_experiment_results.py 5.1 2>/dev/null | grep -q "$model"; then
            log_success "✅ 数据已保存到数据库"
        else
            log_warning "⚠️  数据库中未找到结果，可能需要手动检查"
        fi
    else
        log_error "❌ $(get_model_display_name "$model") 测试失败或超时"
        return 1
    fi
    
    echo ""
}

# 生成测试报告
generate_report() {
    log_header "生成5.1基准测试报告"
    
    log_info "提取最新测试结果..."
    python3 extract_experiment_results.py 5.1 > /tmp/5_1_results.txt 2>&1
    
    if [ -s /tmp/5_1_results.txt ]; then
        echo -e "\n📊 ${CYAN}5.1基准测试结果概览${NC}:"
        echo -e "${BLUE}$(head -20 /tmp/5_1_results.txt)${NC}"
        
        log_success "完整报告已保存到: /tmp/5_1_results.txt"
    else
        log_warning "无法生成结果报告，请手动检查数据库"
    fi
}

# 主要执行逻辑
main() {
    local selected_models=()
    local start_model=""
    local pretest=false
    local report_only=false
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --model)
                selected_models+=("$2")
                shift 2
                ;;
            --start)
                start_model="$2"
                shift 2
                ;;
            --pretest)
                pretest=true
                shift
                ;;
            --report)
                report_only=true
                shift
                ;;
            --help)
                echo "用法: $0 [选项]"
                echo "选项:"
                echo "  --model MODEL     只测试指定模型"
                echo "  --start MODEL     从指定模型开始测试"
                echo "  --pretest         只运行预测试"
                echo "  --report          只生成报告"
                echo "  --help            显示帮助信息"
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                exit 1
                ;;
        esac
    done
    
    # 显示欢迎信息
    log_header "5.1基准测试完整重测工具"
    
    # 只生成报告
    if [ "$report_only" = true ]; then
        generate_report
        exit 0
    fi
    
    # 检查依赖
    check_dependencies
    
    # 显示配置
    show_config
    
    # 只运行预测试
    if [ "$pretest" = true ]; then
        run_pretest
        exit 0
    fi
    
    # 确认开始测试
    echo -e "${YELLOW}⚠️  这将重测所有8个开源模型的5.1基准数据${NC}"
    echo -e "${YELLOW}⚠️  预计总时间: 3-4小时${NC}"
    read -p "确认开始测试? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "测试已取消"
        exit 0
    fi
    
    # 确定要测试的模型列表
    local test_models=()
    if [ ${#selected_models[@]} -gt 0 ]; then
        test_models=("${selected_models[@]}")
        log_info "测试指定模型: ${test_models[*]}"
    elif [ -n "$start_model" ]; then
        local found=false
        for model in "${MODELS[@]}"; do
            if [ "$found" = true ] || [ "$model" = "$start_model" ]; then
                test_models+=("$model")
                found=true
            fi
        done
        if [ ${#test_models[@]} -eq 0 ]; then
            log_error "未找到起始模型: $start_model"
            exit 1
        fi
        log_info "从模型 $start_model 开始测试，共${#test_models[@]}个模型"
    else
        test_models=("${MODELS[@]}")
        log_info "测试所有${#test_models[@]}个模型"
    fi
    
    # 记录开始时间
    local total_start_time=$(date +%s)
    local successful_tests=0
    local failed_tests=0
    
    log_header "开始执行5.1基准测试"
    
    # 逐个运行模型测试
    for i in "${!test_models[@]}"; do
        local model="${test_models[$i]}"
        local model_index=$((i + 1))
        local total_models=${#test_models[@]}
        
        if run_model_test "$model" "$model_index" "$total_models"; then
            ((successful_tests++))
        else
            ((failed_tests++))
            log_warning "继续测试下一个模型..."
        fi
        
        # 在模型之间添加短暂延迟
        if [ $model_index -lt $total_models ]; then
            log_info "等待10秒后测试下一个模型..."
            sleep 10
        fi
    done
    
    # 计算总时间
    local total_end_time=$(date +%s)
    local total_duration=$((total_end_time - total_start_time))
    local total_hours=$((total_duration / 3600))
    local total_minutes=$(((total_duration % 3600) / 60))
    local total_seconds=$((total_duration % 60))
    
    # 显示最终统计
    log_header "5.1基准测试重测完成"
    echo -e "${CYAN}📈 测试统计${NC}:"
    echo -e "  成功: ${GREEN}${successful_tests}${NC} 个模型"
    echo -e "  失败: ${RED}${failed_tests}${NC} 个模型"
    echo -e "  总时间: ${BLUE}${total_hours}时${total_minutes}分${total_seconds}秒${NC}"
    
    # 生成最终报告
    generate_report
    
    if [ $successful_tests -gt 0 ]; then
        log_success "🎉 5.1基准测试重测完成！"
        log_info "使用以下命令查看结果:"
        log_info "python3 extract_experiment_results.py 5.1"
    else
        log_error "❌ 所有模型测试均失败，请检查配置和日志"
        exit 1
    fi
}

# 执行主函数
main "$@"