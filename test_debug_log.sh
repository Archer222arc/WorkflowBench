#!/bin/bash

# 测试调试日志功能
# 这个脚本演示如何使用新添加的调试日志功能来捕获API阻塞问题

echo "=========================================="
echo "测试调试日志功能"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}这个测试将：${NC}"
echo "1. 运行一个小批量测试（3个实例）"
echo "2. 只保存第1个进程的详细日志"
echo "3. 捕获所有Python输出、错误和API调用"
echo ""

echo -e "${YELLOW}提示：如果进程卡死，日志会显示最后的API调用位置${NC}"
echo ""

# 测试命令
echo -e "${GREEN}运行测试...${NC}"
echo "命令: ./run_systematic_test_final.sh --debug-log --model gpt-4o-mini --instances 3 --auto"
echo ""

# 运行实际测试
./run_systematic_test_final.sh \
    --debug-log \
    --debug-process 1 \
    --model gpt-4o-mini \
    --instances 3 \
    --workers 5 \
    --auto

echo ""
echo -e "${GREEN}✅ 测试完成！${NC}"
echo ""
echo -e "${CYAN}查看调试日志：${NC}"
echo "ls -lt logs/debug_*.log | head -5"
ls -lt logs/debug_*.log 2>/dev/null | head -5

echo ""
echo -e "${CYAN}查看最新日志内容：${NC}"
latest_log=$(ls -t logs/debug_*.log 2>/dev/null | head -1)
if [ -n "$latest_log" ]; then
    echo "文件: $latest_log"
    echo "前20行："
    head -20 "$latest_log"
    echo ""
    echo "最后20行："
    tail -20 "$latest_log"
else
    echo -e "${YELLOW}未找到调试日志文件${NC}"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}调试日志功能测试完成${NC}"
echo "=========================================="
echo ""
echo "使用说明："
echo "  --debug-log           启用调试日志"
echo "  --debug-process N     调试第N个进程（默认1）"
echo ""
echo "日志位置："
echo "  logs/debug_<model>_<prompt>_<difficulty>_<timestamp>.log"
echo ""
echo "日志内容包括："
echo "  - Python完整输出"
echo "  - API调用详情"
echo "  - 错误堆栈信息"
echo "  - 环境变量状态"