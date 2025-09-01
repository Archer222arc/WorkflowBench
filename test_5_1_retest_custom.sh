#!/bin/bash

# 5.1 基准测试重测专用脚本
# 基于test_5_3_custom.sh修改，专门用于重测optimal prompt的模型
# 解决DeepSeek-R1在optimal配置下表现异常差的问题

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
LOG_FILE="$LOG_DIR/test_5_1_retest_${TIMESTAMP}.log"

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

# 环境变量设置 - 严格匹配5.1基准测试的配置
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

# 5.1基准测试专用配置
PROMPT_TYPE="optimal"      # 固定为optimal prompt
DIFFICULTY="easy"          # 固定为easy难度
TOOL_SUCCESS_RATE="0.8"   # 固定为0.8工具成功率

# 激活conda环境
if [ -f ~/miniconda3/bin/activate ]; then
    source ~/miniconda3/bin/activate
    log_info "✅ 已激活conda环境: $(which python)"
else
    log_warning "⚠️ 未找到conda环境，使用系统Python"
fi

log_info "=== 5.1 基准测试重测脚本启动 ==="
log_info "时间戳: $TIMESTAMP"
log_info "日志文件: $LOG_FILE"
log_info "测试配置: $PROMPT_TYPE prompt, $DIFFICULTY 难度, $TOOL_SUCCESS_RATE 工具成功率"

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

# 显示可用模型
show_model_options() {
    echo -e "\n${CYAN}🤖 选择重测模型:${NC}"
    echo "1) DeepSeek-R1-0528 (主要目标)"
    echo "2) 所有开源模型"
    echo "3) 所有模型 (开源+闭源)"
    echo "4) 自定义模型列表"
    echo
}

# 获取模型选择
get_model_choice() {
    while true; do
        show_model_options
        read -p "请选择要重测的模型 (1-4): " model_choice
        
        case $model_choice in
            1)
                model_type="single"
                single_model="DeepSeek-R1-0528"
                export MODEL_TYPE="opensource"
                log_info "选择重测 DeepSeek-R1-0528"
                break
                ;;
            2)
                model_type="opensource"
                export MODEL_TYPE="opensource"
                log_info "选择重测所有开源模型"
                break
                ;;
            3)
                model_type="all"
                export MODEL_TYPE="all"
                log_info "选择重测所有模型"
                break
                ;;
            4)
                echo -e "\n${CYAN}可用模型:${NC}"
                echo "开源: DeepSeek-V3-0324, DeepSeek-R1-0528, Llama-3.3-70B-Instruct"
                echo "     qwen2.5-72b-instruct, qwen2.5-32b-instruct, qwen2.5-14b-instruct"
                echo "     qwen2.5-7b-instruct, qwen2.5-3b-instruct"
                echo "闭源: gpt-4o-mini, gpt-5-mini, o3-0416-global, gemini-2.5-flash-06-17, kimi-k2"
                echo
                read -p "请输入模型名 (用空格分隔多个): " custom_models
                model_type="custom"
                custom_model_list="$custom_models"
                # 判断第一个模型的类型
                first_model=$(echo $custom_models | awk '{print $1}')
                if [[ "$first_model" == *"DeepSeek"* ]] || [[ "$first_model" == *"Llama"* ]] || [[ "$first_model" == *"qwen"* ]]; then
                    export MODEL_TYPE="opensource"
                else
                    export MODEL_TYPE="closed_source"
                fi
                log_info "选择自定义模型: $custom_models (类型: $MODEL_TYPE)"
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
    
    log_info "🚀 开始重测 - 模型: $model_name, 配置: $PROMPT_TYPE/$DIFFICULTY/$TOOL_SUCCESS_RATE"
    
    local sanitized_model=$(echo "$model_name" | tr '.' '_' | tr '-' '_')
    local test_log="$LOG_DIR/ultra_parallel_${sanitized_model}_${PROMPT_TYPE}_retest_${TIMESTAMP}.log"
    
    # 构建命令 - 使用5.1基准测试的标准配置
    # 对于qwen模型，强制使用--max-workers 1避免限流
    local workers_param=""
    if [[ "$model_name" == *"qwen"* ]]; then
        workers_param="--max-workers 1"
        log_info "Qwen模型检测，使用限流配置: max-workers=1"
    else
        workers_param="--max-workers $CUSTOM_WORKERS"
        log_info "Azure模型检测，使用高并发配置: max-workers=$CUSTOM_WORKERS"
    fi
    
    local python_cmd=(
        "python3" "./ultra_parallel_runner.py"
        "--model" "$model_name"
        "--prompt-types" "$PROMPT_TYPE"      # optimal
        "--difficulty" "$DIFFICULTY"         # easy
        "--task-types" "all"                 # 所有5种任务类型
        "--num-instances" "20"
        "--rate-mode" "fixed"
        "--tool-success-rate" "$TOOL_SUCCESS_RATE"  # 0.8
        $workers_param
    )
    
    log_info "执行命令: USE_RESULT_COLLECTOR='$USE_RESULT_COLLECTOR' STORAGE_FORMAT='$STORAGE_FORMAT' KMP_DUPLICATE_LIB_OK=TRUE ${python_cmd[*]}"
    
    # 运行测试
    echo "=== 5.1基准测试重测开始时间: $(date) ===" | tee "$test_log"
    echo "=== 环境变量 ===" | tee -a "$test_log"
    echo "USE_RESULT_COLLECTOR=$USE_RESULT_COLLECTOR" | tee -a "$test_log"
    echo "STORAGE_FORMAT=$STORAGE_FORMAT" | tee -a "$test_log"
    echo "PROMPT_TYPE=$PROMPT_TYPE" | tee -a "$test_log"
    echo "DIFFICULTY=$DIFFICULTY" | tee -a "$test_log"
    echo "TOOL_SUCCESS_RATE=$TOOL_SUCCESS_RATE" | tee -a "$test_log"
    echo "CUSTOM_WORKERS=$CUSTOM_WORKERS" | tee -a "$test_log"
    echo "=== 命令执行 ===" | tee -a "$test_log"
    
    # 执行测试命令
    USE_RESULT_COLLECTOR="$USE_RESULT_COLLECTOR" STORAGE_FORMAT="$STORAGE_FORMAT" KMP_DUPLICATE_LIB_OK=TRUE "${python_cmd[@]}" 2>&1 | tee -a "$test_log"
    exit_code=${PIPESTATUS[0]}
    
    echo "=== 测试结束时间: $(date) ===" | tee -a "$test_log"
    echo "=== 退出码: $exit_code ===" | tee -a "$test_log"
    
    # 检查结果
    if [[ $exit_code -eq 0 ]]; then
        log_success "✅ 模型 $model_name 5.1基准测试重测完成"
        log_info "详细日志: $test_log"
        
        # 检查输出文件大小
        if [[ -f "$test_log" ]]; then
            local log_size=$(wc -l < "$test_log")
            log_info "日志行数: $log_size"
        fi
        
        # 显示测试完成后的数据提取
        log_info "正在提取重测后的数据..."
        python3 extract_experiment_results.py 5.1
        
        return 0
    else
        log_error "❌ 模型 $model_name 5.1基准测试重测失败 (退出码: $exit_code)"
        log_error "检查日志: $test_log"
        
        # 显示错误详情
        if [[ -f "$test_log" ]]; then
            log_error "=== 最后50行日志内容 ==="
            tail -50 "$test_log" | while IFS= read -r line; do
                log_error "  $line"
            done
            
            # 检查Python错误
            if grep -q "Traceback\|Error\|Exception" "$test_log"; then
                log_error "=== Python错误traceback ==="
                grep -A 20 -B 5 "Traceback\|Error\|Exception" "$test_log" | while IFS= read -r line; do
                    log_error "  $line"
                done
            fi
        fi
        
        return 1
    fi
}

# 运行选定模型的测试
run_test() {
    local model_list="$1"
    
    log_info "🚀 开始5.1基准测试重测 - optimal prompt"
    
    local failed_models=()
    local successful_models=()
    
    # 将模型字符串转换为数组
    local models=($model_list)
    local total_models=${#models[@]}
    local current=0
    
    for model in "${models[@]}"; do
        ((current++))
        log_info "进度: $current/$total_models - 重测模型: $model"
        
        if run_single_model_test "$model"; then
            successful_models+=("$model")
        else
            failed_models+=("$model")
        fi
        
        # 模型间隔时间
        if [[ $current -lt $total_models ]]; then
            log_info "等待 5 秒后测试下一个模型..."
            sleep 5
        fi
    done
    
    # 报告结果
    log_info "5.1基准测试重测完成："
    log_success "成功: ${#successful_models[@]}/${total_models} 模型"
    
    if [[ ${#successful_models[@]} -gt 0 ]]; then
        log_success "成功的模型: ${successful_models[*]}"
    fi
    
    if [[ ${#failed_models[@]} -gt 0 ]]; then
        log_warning "失败的模型: ${failed_models[*]}"
        return 1
    else
        log_success "所有模型都重测成功！"
        return 0
    fi
}

# 获取模型列表
get_model_list() {
    case $model_type in
        "single")
            echo "$single_model"
            ;;
        "opensource")
            echo "DeepSeek-V3-0324 DeepSeek-R1-0528 Llama-3.3-70B-Instruct qwen2.5-72b-instruct qwen2.5-32b-instruct qwen2.5-14b-instruct qwen2.5-7b-instruct qwen2.5-3b-instruct"
            ;;
        "all")
            echo "DeepSeek-V3-0324 DeepSeek-R1-0528 Llama-3.3-70B-Instruct qwen2.5-72b-instruct qwen2.5-32b-instruct qwen2.5-14b-instruct qwen2.5-7b-instruct qwen2.5-3b-instruct gpt-4o-mini gpt-5-mini o3-0416-global gemini-2.5-flash-06-17 kimi-k2"
            ;;
        "custom")
            echo "$custom_model_list"
            ;;
    esac
}

# 清理旧数据 (可选)
cleanup_old_data() {
    local model_name="$1"
    
    echo -e "\n${YELLOW}🧹 数据清理选项:${NC}"
    echo "1) 保留现有数据，追加新测试结果"
    echo "2) 清理指定模型的optimal数据，重新开始"
    echo "3) 跳过清理，直接开始测试"
    echo
    
    read -p "请选择数据处理方式 (1-3): " cleanup_choice
    
    case $cleanup_choice in
        1)
            log_info "保留现有数据，将追加新的测试结果"
            ;;
        2)
            log_warning "将清理模型 $model_name 的 optimal 数据"
            read -p "确认清理? 这将删除该模型所有optimal测试数据 [y/N]: " confirm_cleanup
            if [[ "$confirm_cleanup" =~ ^[Yy]$ ]]; then
                # 创建数据清理脚本调用
                python3 -c "
import json
from pathlib import Path

# 备份并清理指定模型的optimal数据
db_path = Path('pilot_bench_cumulative_results/master_database.json')
with open(db_path, 'r') as f:
    db = json.load(f)

model_name = '$model_name'
if model_name in db['models']:
    model_data = db['models'][model_name]
    if 'by_prompt_type' in model_data and 'optimal' in model_data['by_prompt_type']:
        # 清理optimal数据
        del model_data['by_prompt_type']['optimal']
        print(f'✅ 已清理模型 {model_name} 的 optimal 数据')
        
        # 保存清理后的数据库
        with open(db_path, 'w') as f:
            json.dump(db, f, indent=2, ensure_ascii=False)
        print(f'✅ 数据库已更新')
    else:
        print(f'⚠️ 模型 {model_name} 没有 optimal 数据需要清理')
else:
    print(f'❌ 模型 {model_name} 不存在于数据库中')
"
                log_success "✅ 数据清理完成"
            else
                log_info "取消清理，保留现有数据"
            fi
            ;;
        3)
            log_info "跳过清理，直接开始测试"
            ;;
        *)
            log_warning "无效选择，默认跳过清理"
            ;;
    esac
}

# 显示当前数据状态
show_current_data() {
    log_info "当前数据库状态检查..."
    python3 -c "
import json
from pathlib import Path

db_path = Path('pilot_bench_cumulative_results/master_database.json')
if db_path.exists():
    with open(db_path, 'r') as f:
        db = json.load(f)
    
    print('📊 当前5.1基准测试数据状态:')
    models = ['DeepSeek-V3-0324', 'DeepSeek-R1-0528', 'Llama-3.3-70B-Instruct']
    
    for model in models:
        if model in db['models']:
            model_data = db['models'][model]
            try:
                optimal_data = model_data['by_prompt_type']['optimal']['by_tool_success_rate']['0.8']['by_difficulty']['easy']
                total_tests = sum(task_data.get('total', 0) for task_data in optimal_data['by_task_type'].values())
                total_success = sum(task_data.get('success', 0) for task_data in optimal_data['by_task_type'].values())
                success_rate = total_success / total_tests * 100 if total_tests > 0 else 0
                print(f'  {model}: {total_tests} 测试, {success_rate:.1f}% 成功率')
            except KeyError:
                print(f'  {model}: ❌ 缺少optimal数据')
        else:
            print(f'  {model}: ❌ 模型不存在')
"
}

# 主函数
main() {
    log_info "检查环境和依赖文件..."
    check_files
    
    log_info "显示当前数据状态..."
    show_current_data
    
    log_info "获取用户选择..."
    get_model_choice
    
    local model_list=$(get_model_list)
    local models=($model_list)
    local total_models=${#models[@]}
    
    log_info "开始执行 5.1 基准测试重测"
    log_info "测试模型数: $total_models"
    log_info "配置: $PROMPT_TYPE prompt, $DIFFICULTY 难度, $TOOL_SUCCESS_RATE 工具成功率"
    log_info "模型配置: $model_type"
    log_info "并发配置: $CUSTOM_WORKERS workers, $MAX_PARALLEL_PROCESSES processes"
    log_info "存储配置: JSON + ResultCollector"
    
    echo -e "\n${GREEN}🎯 重测配置确认:${NC}"
    echo "- 测试类型: 5.1 基准测试 (optimal prompt)"
    echo "- 模型选择: $model_type ($total_models 个模型)"
    echo "- 测试模型: ${models[*]}"
    echo "- 测试配置: $PROMPT_TYPE/$DIFFICULTY/$TOOL_SUCCESS_RATE"
    echo "- 并发设置: $CUSTOM_WORKERS workers"
    echo "- 存储方式: JSON + ResultCollector"
    echo "- 日志目录: $LOG_DIR"
    echo "- 数据备份: ✅ 已备份到 pilot_bench_cumulative_results/master_database_backup_before_r1_retest_*"
    echo
    
    # 对于单个模型，提供数据清理选项
    if [[ "$model_type" == "single" ]]; then
        cleanup_old_data "$single_model"
    fi
    
    read -p "确认开始5.1基准测试重测? [y/N]: " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        log_info "测试已取消"
        exit 0
    fi
    
    # 执行测试
    if run_test "$model_list"; then
        echo -e "\n${GREEN}🎉 5.1基准测试重测成功完成!${NC}"
        log_success "🎉 所有模型重测完成"
        
        # 显示重测后的结果对比
        echo -e "\n${CYAN}📊 重测后结果对比:${NC}"
        python3 extract_experiment_results.py 5.1
        
        exit 0
    else
        echo -e "\n${RED}❌ 部分模型重测失败${NC}"
        log_warning "部分测试失败，请检查日志"
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

# 检查命令行参数
if [[ $# -gt 0 ]]; then
    case $1 in
        "--deepseek-r1")
            model_type="single"
            single_model="DeepSeek-R1-0528"
            export MODEL_TYPE="opensource"
            log_info "命令行模式: 重测 DeepSeek-R1-0528"
            ;;
        "--help"|"-h")
            echo "5.1 基准测试重测脚本"
            echo "用法:"
            echo "  $0                    # 交互模式"
            echo "  $0 --deepseek-r1     # 直接重测 DeepSeek-R1-0528"
            echo "  $0 --help            # 显示帮助"
            exit 0
            ;;
        *)
            log_warning "未知参数: $1，进入交互模式"
            ;;
    esac
fi

# 运行主函数
main "$@"