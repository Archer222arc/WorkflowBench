#!/bin/bash

# 测试全局调试目录是否正确共享
# 模拟run_systematic_test_final.sh的简化版本

# 颜色定义
CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 全局变量
GLOBAL_DEBUG_LOG_DIR=""
DEBUG_LOG=true
STORAGE_FORMAT="json"
MODEL_TYPE="opensource"
NUM_INSTANCES=1
RATE_MODE="fixed"

# 初始化全局调试目录
if [ "$DEBUG_LOG" = true ] && [ -z "$GLOBAL_DEBUG_LOG_DIR" ]; then
    GLOBAL_DEBUG_LOG_DIR="logs/debug_ultra_test_global_$(date +%Y%m%d_%H%M%S)"
    echo -e "${CYAN}📁 初始化全局调试日志目录: $GLOBAL_DEBUG_LOG_DIR${NC}"
    mkdir -p "$GLOBAL_DEBUG_LOG_DIR"
    export GLOBAL_DEBUG_LOG_DIR
fi

# 模拟run_smart_test函数
run_smart_test() {
    local model=$1
    local prompt=$2
    local difficulty=$3
    
    echo -e "${GREEN}  运行测试: $model ($prompt, $difficulty)${NC}"
    
    # 检查是否使用共享的调试目录
    if [ -n "$GLOBAL_DEBUG_LOG_DIR" ]; then
        echo -e "${CYAN}    使用调试目录: $GLOBAL_DEBUG_LOG_DIR${NC}"
        
        # 模拟运行ultra_parallel_runner_debug.py
        timeout 3 python ultra_parallel_runner_debug.py \
            --model "$model" \
            --prompt-types "$prompt" \
            --difficulty "$difficulty" \
            --task-types "simple_task" \
            --num-instances 1 \
            --max-workers 2 \
            --debug-log-dir "$GLOBAL_DEBUG_LOG_DIR" \
            > /dev/null 2>&1
    fi
}

echo "============================================================"
echo "测试全局调试目录共享"
echo "============================================================"

# 测试多个模型（在子shell中运行，模拟并发）
models=("DeepSeek-V3-0324" "DeepSeek-R1-0528" "qwen2.5-72b-instruct")
pids=()

for model in "${models[@]}"; do
    echo -e "${YELLOW}启动 $model 测试...${NC}"
    
    (
        # 确保环境变量在子进程中可用
        export STORAGE_FORMAT="${STORAGE_FORMAT}"
        export MODEL_TYPE="${MODEL_TYPE}"
        export NUM_INSTANCES="${NUM_INSTANCES}"
        export RATE_MODE="${RATE_MODE}"
        export GLOBAL_DEBUG_LOG_DIR="${GLOBAL_DEBUG_LOG_DIR}"
        export DEBUG_LOG="${DEBUG_LOG}"
        
        run_smart_test "$model" "baseline" "easy"
    ) &
    
    pids+=($!)
    sleep 1
done

# 等待所有后台任务完成
echo -e "\n${YELLOW}等待所有测试完成...${NC}"
for pid in "${pids[@]}"; do
    wait $pid
done

# 检查结果
echo -e "\n============================================================"
echo "检查结果"
echo "============================================================"

if [ -d "$GLOBAL_DEBUG_LOG_DIR" ]; then
    echo -e "${GREEN}✅ 全局调试目录存在: $GLOBAL_DEBUG_LOG_DIR${NC}"
    
    # 统计日志文件
    log_count=$(ls -1 "$GLOBAL_DEBUG_LOG_DIR"/*.log 2>/dev/null | wc -l)
    echo -e "${CYAN}   日志文件数: $log_count${NC}"
    
    # 显示每个模型的日志
    for model in "${models[@]}"; do
        model_key=$(echo "$model" | tr '.-' '_' | tr '[:upper:]' '[:lower:]')
        model_logs=$(ls "$GLOBAL_DEBUG_LOG_DIR" | grep -i "$model_key" | wc -l)
        echo "   $model: $model_logs 个日志文件"
    done
    
    # 列出所有日志文件
    echo -e "\n日志文件列表:"
    ls -la "$GLOBAL_DEBUG_LOG_DIR" | grep "\.log$" | while read line; do
        filename=$(echo "$line" | awk '{print $NF}')
        echo "   📄 $filename"
    done
    
    if [ "$log_count" -ge "${#models[@]}" ]; then
        echo -e "\n${GREEN}✅ 测试成功！所有模型共享同一个调试目录${NC}"
    else
        echo -e "\n${RED}❌ 日志文件数量不足，可能有问题${NC}"
    fi
else
    echo -e "${RED}❌ 全局调试目录不存在！${NC}"
fi

echo -e "\n============================================================"
echo "测试完成"
echo "============================================================"