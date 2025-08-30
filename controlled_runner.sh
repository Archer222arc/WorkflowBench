#!/bin/bash

# 受控并发执行器 - 防止进程爆炸
# 特点：
# 1. 限制最大并发进程数
# 2. 顺序执行模型，避免同时启动太多
# 3. 实时监控系统资源

# 配置参数
MAX_CONCURRENT_PROCESSES=${MAX_CONCURRENT_PROCESSES:-10}  # 最大并发进程数
WAIT_BETWEEN_MODELS=${WAIT_BETWEEN_MODELS:-30}  # 模型之间等待时间（秒）
MEMORY_THRESHOLD=${MEMORY_THRESHOLD:-70}  # 内存使用率阈值（%）
CHECK_INTERVAL=${CHECK_INTERVAL:-10}  # 检查间隔（秒）

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}受控并发执行器 - 5.3缺陷工作流测试${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}配置：${NC}"
echo "  最大并发进程: $MAX_CONCURRENT_PROCESSES"
echo "  内存阈值: $MEMORY_THRESHOLD%"
echo "  模型间隔: ${WAIT_BETWEEN_MODELS}秒"
echo ""

# 函数：检查当前运行的测试进程数
count_test_processes() {
    ps aux | grep -E "(smart_batch_runner|ultra_parallel_runner)" | grep -v grep | wc -l | tr -d ' '
}

# 函数：等待进程数降到限制以下
wait_for_slot() {
    local current=$(count_test_processes)
    while [ $current -ge $MAX_CONCURRENT_PROCESSES ]; do
        echo -e "${YELLOW}⏳ 当前有 $current 个进程运行，等待空闲槽位...${NC}"
        sleep $CHECK_INTERVAL
        current=$(count_test_processes)
    done
    echo -e "${GREEN}✅ 找到空闲槽位，当前进程数: $current${NC}"
}

# 函数：检查内存使用率（macOS兼容）
check_memory() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        local mem_info=$(vm_stat | grep "Pages free")
        local free_pages=$(echo $mem_info | awk '{print $3}' | sed 's/\.//')
        local total_mem=$(sysctl -n hw.memsize)
        local page_size=4096
        local free_mem=$((free_pages * page_size))
        local used_percent=$((100 - (free_mem * 100 / total_mem)))
        echo $used_percent
    else
        # Linux
        free | grep Mem | awk '{print int($3/$2 * 100)}'
    fi
}

# 函数：等待内存释放
wait_for_memory() {
    local mem_usage=$(check_memory)
    while [ $mem_usage -gt $MEMORY_THRESHOLD ]; do
        echo -e "${YELLOW}⚠️ 内存使用率 ${mem_usage}% 超过阈值，等待释放...${NC}"
        sleep $CHECK_INTERVAL
        mem_usage=$(check_memory)
    done
}

# 函数：运行单个模型的测试
run_model_test() {
    local model=$1
    local phase=$2
    
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo -e "${BLUE}开始测试模型: $model${NC}"
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    
    # 等待资源
    wait_for_slot
    wait_for_memory
    
    # 5.3缺陷工作流的三组测试
    if [ "$phase" == "5.3" ]; then
        # 组1：结构缺陷
        echo -e "${GREEN}→ 启动组1：结构缺陷（sequence_disorder, tool_misuse, parameter_error）${NC}"
        ./run_systematic_test_final.sh \
            --model "$model" \
            --phase 5.3 \
            --prompt-types "flawed_sequence_disorder,flawed_tool_misuse,flawed_parameter_error" \
            --workers 1 \
            --auto &
        
        sleep 5  # 组之间短暂延迟
        
        # 等待下一个槽位
        wait_for_slot
        wait_for_memory
        
        # 组2：操作缺陷
        echo -e "${GREEN}→ 启动组2：操作缺陷（missing_step, redundant_operations）${NC}"
        ./run_systematic_test_final.sh \
            --model "$model" \
            --phase 5.3 \
            --prompt-types "flawed_missing_step,flawed_redundant_operations" \
            --workers 1 \
            --auto &
        
        sleep 5
        
        # 等待下一个槽位
        wait_for_slot
        wait_for_memory
        
        # 组3：逻辑缺陷
        echo -e "${GREEN}→ 启动组3：逻辑缺陷（logical_inconsistency, semantic_drift）${NC}"
        ./run_systematic_test_final.sh \
            --model "$model" \
            --phase 5.3 \
            --prompt-types "flawed_logical_inconsistency,flawed_semantic_drift" \
            --workers 1 \
            --auto &
    else
        # 其他阶段的单一测试
        ./run_systematic_test_final.sh \
            --model "$model" \
            --phase "$phase" \
            --workers 1 \
            --auto &
    fi
    
    echo -e "${GREEN}✓ 模型 $model 的所有测试已启动${NC}"
}

# 函数：等待所有进程完成
wait_all_complete() {
    echo ""
    echo -e "${BLUE}等待所有测试完成...${NC}"
    
    while true; do
        local current=$(count_test_processes)
        if [ $current -eq 0 ]; then
            echo -e "${GREEN}✅ 所有测试已完成！${NC}"
            break
        fi
        
        echo -e "${YELLOW}仍有 $current 个测试在运行...${NC}"
        
        # 显示当前运行的进程
        echo -e "${BLUE}当前运行的进程：${NC}"
        ps aux | grep -E "(smart_batch_runner|ultra_parallel_runner)" | grep -v grep | awk '{print $2, $11, $12, $13}' | head -5
        
        sleep 30
    done
}

# 主程序
main() {
    local phase=${1:-"5.3"}
    local models=${2:-"qwen2.5-7b-instruct,qwen2.5-14b-instruct,qwen2.5-32b-instruct"}
    local mode=${3:-"sequential"}  # sequential 或 parallel
    
    echo -e "${BLUE}测试配置：${NC}"
    echo "  阶段: $phase"
    echo "  模型: $models"
    echo "  模式: $mode"
    echo ""
    
    # 转换模型列表为数组
    IFS=',' read -ra MODEL_ARRAY <<< "$models"
    
    if [ "$mode" == "sequential" ]; then
        # 顺序模式：一个模型完成后再开始下一个
        echo -e "${GREEN}使用顺序模式：一次一个模型${NC}"
        
        for model in "${MODEL_ARRAY[@]}"; do
            run_model_test "$model" "$phase"
            
            # 等待当前模型完成
            echo -e "${BLUE}等待模型 $model 完成...${NC}"
            wait_all_complete
            
            # 模型之间休息
            if [ "$model" != "${MODEL_ARRAY[-1]}" ]; then
                echo -e "${YELLOW}休息 ${WAIT_BETWEEN_MODELS} 秒...${NC}"
                sleep $WAIT_BETWEEN_MODELS
            fi
        done
    else
        # 并行模式：控制最大并发数
        echo -e "${GREEN}使用并行模式：最多 $MAX_CONCURRENT_PROCESSES 个并发${NC}"
        
        for model in "${MODEL_ARRAY[@]}"; do
            run_model_test "$model" "$phase"
            
            # 短暂延迟避免同时启动
            sleep 10
        done
        
        # 等待所有完成
        wait_all_complete
    fi
    
    echo ""
    echo -e "${GREEN}════════════════════════════════════════${NC}"
    echo -e "${GREEN}所有测试完成！${NC}"
    echo -e "${GREEN}════════════════════════════════════════${NC}"
}

# 处理命令行参数
case "$1" in
    "5.3")
        # 5.3缺陷工作流测试
        echo -e "${BLUE}执行5.3缺陷工作流测试${NC}"
        main "5.3" "qwen2.5-7b-instruct,qwen2.5-14b-instruct" "sequential"
        ;;
    
    "5.2")
        # 5.2规模效应测试
        echo -e "${BLUE}执行5.2规模效应测试${NC}"
        main "5.2" "qwen2.5-72b-instruct,qwen2.5-32b-instruct,qwen2.5-14b-instruct" "sequential"
        ;;
    
    "test")
        # 测试模式：单个模型
        echo -e "${BLUE}测试模式：单个模型${NC}"
        MAX_CONCURRENT_PROCESSES=1
        main "5.3" "qwen2.5-7b-instruct" "sequential"
        ;;
    
    "monitor")
        # 监控模式
        while true; do
            clear
            echo -e "${GREEN}═══════════════════════════════════════${NC}"
            echo -e "${GREEN}系统资源监控${NC}"
            echo -e "${GREEN}═══════════════════════════════════════${NC}"
            echo ""
            
            echo -e "${BLUE}进程状态：${NC}"
            echo "  测试进程数: $(count_test_processes)"
            echo "  内存使用率: $(check_memory)%"
            echo ""
            
            echo -e "${BLUE}运行中的测试：${NC}"
            ps aux | grep -E "(smart_batch_runner|ultra_parallel_runner)" | grep -v grep | awk '{printf "  PID %s: %s\n", $2, $12}' | head -10
            
            sleep 5
        done
        ;;
    
    *)
        echo "用法: $0 [5.3|5.2|test|monitor]"
        echo ""
        echo "选项:"
        echo "  5.3     - 运行5.3缺陷工作流测试（顺序执行）"
        echo "  5.2     - 运行5.2规模效应测试"
        echo "  test    - 测试单个模型"
        echo "  monitor - 监控系统资源"
        echo ""
        echo "环境变量:"
        echo "  MAX_CONCURRENT_PROCESSES - 最大并发进程数（默认3）"
        echo "  MEMORY_THRESHOLD - 内存使用率阈值（默认70%）"
        echo "  WAIT_BETWEEN_MODELS - 模型间等待时间（默认30秒）"
        exit 1
        ;;
esac