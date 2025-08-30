#!/bin/bash

# 模拟run_systematic_test_final.sh的行为
source /etc/profile

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 全局调试日志目录
GLOBAL_DEBUG_LOG_DIR=""
DEBUG_LOG=true

echo "============================================================"
echo "测试bash脚本集成 - 共享调试日志目录"
echo "============================================================"

# 函数：运行单个模型（模拟run_single_model_parallel）
run_single_model() {
    local model=$1
    
    echo -e "\n${CYAN}运行模型: $model${NC}"
    
    # 如果全局调试目录未设置，创建一个新的（整个测试会话共享）
    if [ -z "$GLOBAL_DEBUG_LOG_DIR" ]; then
        GLOBAL_DEBUG_LOG_DIR="logs/debug_ultra_bash_test_$(date +%Y%m%d_%H%M%S)"
        echo -e "${CYAN}📁 创建全局调试日志目录: $GLOBAL_DEBUG_LOG_DIR${NC}"
    fi
    echo -e "${CYAN}📝 使用调试版本，日志保存到: $GLOBAL_DEBUG_LOG_DIR${NC}"
    
    # 运行调试版本
    timeout 5 python -u ultra_parallel_runner_debug.py \
        --model "$model" \
        --prompt-types baseline \
        --difficulty easy \
        --task-types simple_task \
        --num-instances 1 \
        --rate-mode adaptive \
        --max-workers 2 \
        --debug-log-dir "$GLOBAL_DEBUG_LOG_DIR" \
        > /dev/null 2>&1
    
    echo -e "${GREEN}  ✓ $model 测试完成${NC}"
    
    # 显示当前日志文件
    echo "  当前日志文件:"
    ls -la "$GLOBAL_DEBUG_LOG_DIR" 2>/dev/null | grep "\.log$" | tail -3 | while read line; do
        filename=$(echo "$line" | awk '{print $NF}')
        echo "    - $filename"
    done
}

# 测试多个模型
echo -e "\n${YELLOW}开始测试多个模型...${NC}"

run_single_model "DeepSeek-V3-0324"
sleep 1

run_single_model "DeepSeek-R1-0528"
sleep 1

run_single_model "qwen2.5-72b-instruct"
sleep 1

# 再次测试同一个模型
run_single_model "DeepSeek-V3-0324"

# 最终检查
echo -e "\n============================================================"
echo -e "${YELLOW}最终检查${NC}"
echo "============================================================"

if [ -d "$GLOBAL_DEBUG_LOG_DIR" ]; then
    total_files=$(ls -la "$GLOBAL_DEBUG_LOG_DIR" | grep "\.log$" | wc -l)
    echo -e "\n${GREEN}总共创建了 $total_files 个日志文件:${NC}"
    
    # 显示所有日志文件
    ls -la "$GLOBAL_DEBUG_LOG_DIR" | grep "\.log$" | while read line; do
        filename=$(echo "$line" | awk '{print $NF}')
        echo "  📄 $filename"
    done
    
    # 统计每个模型的日志数
    echo -e "\n📊 统计结果:"
    
    v3_count=$(ls "$GLOBAL_DEBUG_LOG_DIR" | grep -i "deepseek_v3" | wc -l)
    r1_count=$(ls "$GLOBAL_DEBUG_LOG_DIR" | grep -i "deepseek_r1" | wc -l)
    qwen_count=$(ls "$GLOBAL_DEBUG_LOG_DIR" | grep -i "qwen" | wc -l)
    
    echo "  DeepSeek-V3-0324: $v3_count 个日志文件"
    echo "  DeepSeek-R1-0528: $r1_count 个日志文件"
    echo "  qwen2.5-72b-instruct: $qwen_count 个日志文件"
    
    if [ "$total_files" -ge 4 ]; then
        echo -e "\n${GREEN}✅ 测试成功！${NC}"
        echo "   - 所有模型的日志都保存在同一个目录"
        echo "   - 没有日志被覆盖"
        echo "   - 共享目录: $GLOBAL_DEBUG_LOG_DIR"
    else
        echo -e "\n${RED}❌ 可能有日志被覆盖！${NC}"
        echo "   - 期望至少4个文件，实际只有 $total_files 个"
    fi
else
    echo -e "${RED}❌ 调试目录不存在！${NC}"
fi

echo -e "\n============================================================"
echo "测试完成"
echo "============================================================"