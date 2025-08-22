#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  测试并发修复效果${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

echo -e "${YELLOW}测试配置：${NC}"
echo "  - 模型: gpt-4o-mini (Azure)"
echo "  - 缺陷类型: 3种 (会创建3个分片)"
echo "  - 实例数: 1 (快速测试)"
echo "  - 任务类型: simple_task (单一类型)"
echo ""

echo -e "${GREEN}启动测试...${NC}"

# 运行测试并记录时间
START_TIME=$(date +%s)

python ultra_parallel_runner.py \
    --model gpt-4o-mini \
    --prompt-types flawed_sequence_disorder,flawed_tool_misuse,flawed_parameter_error \
    --difficulty easy \
    --task-types simple_task \
    --num-instances 1 \
    --rate-mode fixed \
    --silent 2>&1 | tee test_parallel_output.log

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  测试结果分析${NC}"
echo -e "${CYAN}========================================${NC}"

# 分析日志
echo -e "${YELLOW}分片启动时间：${NC}"
grep -E "启动分片|延迟.*秒" test_parallel_output.log

echo ""
echo -e "${YELLOW}分片完成时间：${NC}"
grep "分片.*完成" test_parallel_output.log

echo ""
echo -e "${GREEN}总耗时: ${DURATION} 秒${NC}"

# 检查是否真的并发
echo ""
echo -e "${YELLOW}并发性分析：${NC}"
if grep -q "并发等待" test_parallel_output.log; then
    echo -e "${GREEN}✓ 使用了并发等待机制${NC}"
else
    echo -e "${RED}✗ 未检测到并发等待${NC}"
fi

# 计算理论时间
echo ""
echo -e "${CYAN}理论分析：${NC}"
echo "  - 如果串行: 预计 3 × 单个分片时间"
echo "  - 如果并发: 预计 1 × 单个分片时间 + 120秒延迟"
echo "  - 实际耗时: ${DURATION} 秒"

# 清理
rm -f test_parallel_output.log