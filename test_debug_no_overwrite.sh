#!/bin/bash

# 测试调试日志不被覆盖的修复
# 模拟5.3测试中多个模型的连续运行

set -e

# 设置颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}测试调试日志不覆盖修复${NC}"
echo -e "${CYAN}========================================${NC}"

# 创建测试目录
DEBUG_DIR="logs/debug_ultra_test_$(date +%Y%m%d_%H%M%S)"
echo -e "${GREEN}调试日志目录: $DEBUG_DIR${NC}"

# 测试3个不同的模型，每个只运行1个实例以快速测试
MODELS=("gpt-4o-mini" "qwen2.5-7b-instruct" "DeepSeek-V3-0324")

for model in "${MODELS[@]}"; do
    echo -e "\n${YELLOW}运行模型: $model${NC}"
    
    # 运行调试版本，使用相同的日志目录
    python ultra_parallel_runner_debug.py \
        --model "$model" \
        --prompt-types "baseline" \
        --difficulty "easy" \
        --task-types "simple_task" \
        --num-instances 1 \
        --tool-success-rate 0.8 \
        --rate-mode adaptive \
        --debug-log-dir "$DEBUG_DIR" \
        --silent &
    
    # 获取进程ID
    PID=$!
    
    # 等待5秒让进程启动
    sleep 5
    
    # 检查进程是否还在运行
    if ps -p $PID > /dev/null; then
        echo "进程 $PID 正在运行..."
        # 等待进程完成（最多30秒）
        WAIT_TIME=0
        while ps -p $PID > /dev/null && [ $WAIT_TIME -lt 30 ]; do
            sleep 1
            WAIT_TIME=$((WAIT_TIME + 1))
        done
        
        # 如果还在运行，终止它
        if ps -p $PID > /dev/null; then
            echo "终止进程 $PID"
            kill $PID 2>/dev/null || true
        fi
    fi
done

echo -e "\n${CYAN}========================================${NC}"
echo -e "${CYAN}检查日志文件${NC}"
echo -e "${CYAN}========================================${NC}"

# 检查日志文件
echo -e "\n${GREEN}日志文件列表:${NC}"
ls -la "$DEBUG_DIR"/*.log 2>/dev/null || echo "没有找到日志文件"

# 统计各模型的日志文件
echo -e "\n${GREEN}各模型的日志文件:${NC}"
for model in "${MODELS[@]}"; do
    model_safe=$(echo "$model" | tr '/.\\-' '_')
    count=$(ls "$DEBUG_DIR"/${model_safe}_shard_*.log 2>/dev/null | wc -l)
    echo "  $model: $count 个文件"
    
    # 列出该模型的文件
    if [ $count -gt 0 ]; then
        ls "$DEBUG_DIR"/${model_safe}_shard_*.log | while read file; do
            size=$(du -h "$file" | cut -f1)
            echo "    - $(basename "$file") ($size)"
        done
    fi
done

# 检查是否有文件被覆盖（通过检查文件内容）
echo -e "\n${GREEN}检查文件内容（确认没有覆盖）:${NC}"
for log_file in "$DEBUG_DIR"/*_shard_*.log; do
    if [ -f "$log_file" ]; then
        # 提取文件中记录的模型名
        model_in_file=$(grep "^模型:" "$log_file" | head -1 | cut -d' ' -f2)
        # 从文件名提取模型名
        filename=$(basename "$log_file")
        model_from_name=$(echo "$filename" | sed 's/_shard_.*//')
        
        echo -n "  $(basename "$log_file"): "
        if [ ! -z "$model_in_file" ]; then
            echo "内容模型=$model_in_file"
            
            # 检查是否匹配（考虑到名称转换）
            model_in_file_safe=$(echo "$model_in_file" | tr '/.\\-' '_')
            if [[ "$model_from_name" == "$model_in_file_safe" ]]; then
                echo -e "    ${GREEN}✓ 文件名和内容匹配${NC}"
            else
                echo -e "    ${YELLOW}⚠ 文件名($model_from_name)和内容($model_in_file_safe)不匹配 - 可能被覆盖！${NC}"
            fi
        else
            echo "无法检测模型名"
        fi
    fi
done

echo -e "\n${CYAN}========================================${NC}"
echo -e "${CYAN}测试完成${NC}"
echo -e "${CYAN}========================================${NC}"

# 生成简单报告
if [ -f "$DEBUG_DIR/debug_report.md" ]; then
    echo -e "\n${GREEN}调试报告已生成: $DEBUG_DIR/debug_report.md${NC}"
else
    echo -e "\n${YELLOW}未找到调试报告${NC}"
fi

echo -e "\n${GREEN}✅ 修复验证完成！${NC}"
echo "如果每个模型都有独立的日志文件且内容匹配，说明修复成功。"