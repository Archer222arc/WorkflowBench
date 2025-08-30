#!/bin/bash

# ============================================
# 5.3 缺陷工作流测试 - 调试版本
# 添加详细日志记录以定位问题
# ============================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 日志文件
DEBUG_LOG="logs/test_5_3_debug_$(date +%Y%m%d_%H%M%S).log"
MONITOR_LOG="logs/test_5_3_monitor_$(date +%Y%m%d_%H%M%S).log"

# 创建日志目录
mkdir -p logs

# 日志函数
log_debug() {
    local msg="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $msg" | tee -a "$DEBUG_LOG"
    echo -e "${CYAN}[DEBUG]${NC} $msg"
}

log_info() {
    local msg="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [INFO] $msg" | tee -a "$DEBUG_LOG"
    echo -e "${GREEN}[INFO]${NC} $msg"
}

log_error() {
    local msg="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [ERROR] $msg" | tee -a "$DEBUG_LOG"
    echo -e "${RED}[ERROR]${NC} $msg"
}

log_warning() {
    local msg="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [WARN] $msg" | tee -a "$DEBUG_LOG"
    echo -e "${YELLOW}[WARN]${NC} $msg"
}

# 监控函数
monitor_process() {
    local pid=$1
    local name=$2
    local start_time=$(date +%s)
    
    log_debug "开始监控进程 $name (PID: $pid)"
    
    while kill -0 $pid 2>/dev/null; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        # 获取进程状态
        if ps -p $pid > /dev/null; then
            local cpu=$(ps -p $pid -o %cpu= 2>/dev/null || echo "0")
            local mem=$(ps -p $pid -o %mem= 2>/dev/null || echo "0")
            local state=$(ps -p $pid -o state= 2>/dev/null || echo "?")
            local cmd=$(ps -p $pid -o comm= 2>/dev/null || echo "unknown")
            
            # 记录到监控日志
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] PID=$pid NAME=$name ELAPSED=${elapsed}s CPU=$cpu% MEM=$mem% STATE=$state CMD=$cmd" >> "$MONITOR_LOG"
            
            # 每30秒输出一次状态
            if [ $((elapsed % 30)) -eq 0 ]; then
                log_debug "进程 $name 运行中: ${elapsed}秒, CPU=$cpu%, MEM=$mem%, STATE=$state"
            fi
            
            # 检查是否卡死（CPU使用率为0且运行时间超过5分钟）
            if [ $elapsed -gt 300 ] && [ "$(echo "$cpu < 0.1" | bc)" -eq 1 ]; then
                log_warning "进程 $name 可能卡死: CPU使用率过低($cpu%)，已运行${elapsed}秒"
                
                # 获取进程堆栈（如果可能）
                if command -v gstack &> /dev/null; then
                    gstack $pid >> "$DEBUG_LOG" 2>&1
                elif command -v pstack &> /dev/null; then
                    pstack $pid >> "$DEBUG_LOG" 2>&1
                else
                    # 尝试使用lldb获取堆栈
                    echo "thread backtrace all" | lldb -p $pid 2>&1 | head -100 >> "$DEBUG_LOG"
                fi
            fi
        fi
        
        sleep 5
    done
    
    local end_time=$(date +%s)
    local total_time=$((end_time - start_time))
    log_info "进程 $name (PID: $pid) 已结束，总运行时间: ${total_time}秒"
}

# 系统状态记录
record_system_state() {
    local label="$1"
    log_debug "记录系统状态: $label"
    
    # 内存使用
    echo "=== 内存状态 ($label) ===" >> "$DEBUG_LOG"
    if command -v free &> /dev/null; then
        free -h >> "$DEBUG_LOG"
    else
        vm_stat >> "$DEBUG_LOG"
    fi
    
    # CPU负载
    echo "=== CPU负载 ($label) ===" >> "$DEBUG_LOG"
    uptime >> "$DEBUG_LOG"
    
    # 磁盘空间
    echo "=== 磁盘空间 ($label) ===" >> "$DEBUG_LOG"
    df -h . >> "$DEBUG_LOG"
    
    # Python进程
    echo "=== Python进程 ($label) ===" >> "$DEBUG_LOG"
    ps aux | grep -E "python|smart_batch|ultra_parallel" | grep -v grep >> "$DEBUG_LOG"
    
    # 网络连接
    echo "=== 网络连接 ($label) ===" >> "$DEBUG_LOG"
    netstat -an 2>/dev/null | grep -E "ESTABLISHED|TIME_WAIT" | wc -l >> "$DEBUG_LOG"
}

# 测试单个缺陷类型（带详细日志）
test_single_flaw() {
    local model=$1
    local flaw_type=$2
    local instances=$3
    
    log_info "=========================================="
    log_info "测试: $model - $flaw_type"
    log_info "实例数: $instances"
    log_info "=========================================="
    
    # 记录开始时的系统状态
    record_system_state "测试开始前"
    
    # 设置环境变量
    export STORAGE_FORMAT="${STORAGE_FORMAT:-parquet}"
    export PYTHONUNBUFFERED=1  # 禁用Python缓冲，立即输出
    
    log_debug "存储格式: $STORAGE_FORMAT"
    log_debug "构建命令..."
    
    # 构建命令
    local cmd="python smart_batch_runner.py \
        --model $model \
        --prompt-types $flaw_type \
        --difficulty easy \
        --task-types simple_task \
        --num-instances $instances \
        --tool-success-rate 0.8 \
        --max-workers 10 \
        --checkpoint-interval 2 \
        --batch-commit \
        --no-adaptive \
        --qps 5 \
        --no-save-logs"
    
    log_debug "执行命令: $cmd"
    
    # 创建临时日志文件
    local temp_log="logs/temp_${model}_${flaw_type}_$(date +%Y%m%d_%H%M%S).log"
    
    # 启动测试进程
    log_info "启动测试进程..."
    eval "$cmd" > "$temp_log" 2>&1 &
    local test_pid=$!
    
    log_info "测试进程PID: $test_pid"
    
    # 启动监控进程
    monitor_process $test_pid "$model-$flaw_type" &
    local monitor_pid=$!
    
    # 等待测试完成或超时
    local timeout=600  # 10分钟超时
    local elapsed=0
    
    while kill -0 $test_pid 2>/dev/null && [ $elapsed -lt $timeout ]; do
        sleep 10
        elapsed=$((elapsed + 10))
        
        # 每分钟输出一次日志末尾
        if [ $((elapsed % 60)) -eq 0 ]; then
            log_debug "--- 最近的输出 (${elapsed}秒) ---"
            tail -5 "$temp_log" | while read line; do
                log_debug "OUTPUT: $line"
            done
        fi
    done
    
    # 检查结果
    if kill -0 $test_pid 2>/dev/null; then
        log_error "测试超时（${timeout}秒），终止进程"
        kill -TERM $test_pid 2>/dev/null
        sleep 5
        kill -KILL $test_pid 2>/dev/null
        local exit_code=124  # timeout exit code
    else
        wait $test_pid
        local exit_code=$?
        log_info "测试完成，退出码: $exit_code"
    fi
    
    # 终止监控进程
    kill $monitor_pid 2>/dev/null
    
    # 保存完整日志
    log_debug "--- 完整输出 ---"
    cat "$temp_log" >> "$DEBUG_LOG"
    
    # 记录结束时的系统状态
    record_system_state "测试结束后"
    
    # 检查数据更新
    log_info "检查数据更新..."
    python -c "
import json
from pathlib import Path
db_path = Path('pilot_bench_cumulative_results/master_database.json')
if db_path.exists():
    with open(db_path, 'r') as f:
        db = json.load(f)
    if '$model' in db['models']:
        model_data = db['models']['$model']
        if 'by_prompt_type' in model_data and '$flaw_type' in model_data['by_prompt_type']:
            flaw_data = model_data['by_prompt_type']['$flaw_type']
            print(f'✅ 找到 $flaw_type 数据')
            # 输出简要统计
            if 'by_tool_success_rate' in flaw_data and '0.8' in flaw_data['by_tool_success_rate']:
                rate_data = flaw_data['by_tool_success_rate']['0.8']
                if 'by_difficulty' in rate_data and 'easy' in rate_data['by_difficulty']:
                    diff_data = rate_data['by_difficulty']['easy']
                    if 'by_task_type' in diff_data and 'simple_task' in diff_data['by_task_type']:
                        task_data = diff_data['by_task_type']['simple_task']
                        print(f'  总测试: {task_data.get(\"total\", 0)}')
                        print(f'  成功: {task_data.get(\"success\", 0)}')
        else:
            print(f'❌ 未找到 $flaw_type 数据')
" | tee -a "$DEBUG_LOG"
    
    return $exit_code
}

# 主测试流程
main() {
    log_info "============================================"
    log_info "5.3 缺陷工作流测试 - 调试版本"
    log_info "日志文件: $DEBUG_LOG"
    log_info "监控文件: $MONITOR_LOG"
    log_info "============================================"
    
    # 系统信息
    log_info "系统信息:"
    log_debug "操作系统: $(uname -a)"
    log_debug "Python版本: $(python --version 2>&1)"
    log_debug "当前目录: $(pwd)"
    log_debug "用户: $(whoami)"
    
    # 测试一个小案例
    MODEL="DeepSeek-V3-0324"
    FLAW_TYPE="flawed_sequence_disorder"
    INSTANCES=2
    
    log_info "开始测试: $MODEL 的 $FLAW_TYPE"
    
    # 运行测试
    test_single_flaw "$MODEL" "$FLAW_TYPE" "$INSTANCES"
    local result=$?
    
    if [ $result -eq 0 ]; then
        log_info "✅ 测试成功完成"
    else
        log_error "❌ 测试失败，退出码: $result"
    fi
    
    # 生成总结
    log_info "============================================"
    log_info "测试总结"
    log_info "============================================"
    log_info "详细日志: $DEBUG_LOG"
    log_info "监控日志: $MONITOR_LOG"
    
    # 统计日志中的关键信息
    log_info "错误统计:"
    grep -c ERROR "$DEBUG_LOG" | xargs echo "  ERROR数量:"
    grep -c WARN "$DEBUG_LOG" | xargs echo "  WARNING数量:"
    grep -c "超时" "$DEBUG_LOG" | xargs echo "  超时次数:"
    grep -c "卡死" "$DEBUG_LOG" | xargs echo "  疑似卡死:"
    
    log_info "建议查看日志文件以获取详细信息"
}

# 运行主函数
main