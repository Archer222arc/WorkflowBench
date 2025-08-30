#!/bin/bash

# 测试环境变量修复的验证脚本
# 用于检查5.2测试是否能正确使用内存优化

echo "=================================="
echo "环境变量传递修复验证"
echo "=================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}1. 检查全局环境变量设置...${NC}"
grep -n "全局环境变量设置" run_systematic_test_final.sh
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 全局环境变量设置已添加${NC}"
else
    echo -e "${RED}✗ 未找到全局环境变量设置${NC}"
fi

echo ""
echo -e "${YELLOW}2. 检查5.2子进程环境变量传递...${NC}"
grep -B 10 "Qwen规模效应(very_easy)" run_systematic_test_final.sh | grep "USE_PARTIAL_LOADING" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 5.2 very_easy子进程包含USE_PARTIAL_LOADING${NC}"
else
    echo -e "${RED}✗ 5.2 very_easy子进程缺少USE_PARTIAL_LOADING${NC}"
fi

grep -B 10 "Qwen规模效应(medium)" run_systematic_test_final.sh | grep "USE_PARTIAL_LOADING" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 5.2 medium子进程包含USE_PARTIAL_LOADING${NC}"
else
    echo -e "${RED}✗ 5.2 medium子进程缺少USE_PARTIAL_LOADING${NC}"
fi

echo ""
echo -e "${YELLOW}3. 检查其他阶段的环境变量传递...${NC}"
phases=("基准测试" "缺陷工作流" "工具可靠性" "提示敏感性")
for phase in "${phases[@]}"; do
    grep -B 5 "$phase" run_systematic_test_final.sh | grep "USE_PARTIAL_LOADING" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $phase 包含USE_PARTIAL_LOADING${NC}"
    else
        echo -e "${YELLOW}⚠ $phase 可能需要检查（可以进一步验证）${NC}"
    fi
done

echo ""
echo -e "${YELLOW}4. 测试实际环境变量传递...${NC}"
# 创建一个简单的测试
cat > test_env_var.sh << 'EOF'
#!/bin/bash
export USE_PARTIAL_LOADING="true"
export TASK_LOAD_COUNT="20"

(
    # 子进程测试
    if [ "$USE_PARTIAL_LOADING" = "true" ]; then
        echo "✓ 子进程可以访问USE_PARTIAL_LOADING"
    else
        echo "✗ 子进程无法访问USE_PARTIAL_LOADING"
    fi
) &
wait
EOF

chmod +x test_env_var.sh
./test_env_var.sh
rm test_env_var.sh

echo ""
echo "=================================="
echo -e "${GREEN}验证完成！${NC}"
echo "=================================="
echo ""
echo "建议："
echo "1. 运行小规模5.2测试验证内存使用："
echo "   ./run_systematic_test_final.sh --phase 5.2 --instances 2"
echo ""
echo "2. 监控内存使用："
echo "   在另一个终端运行: watch -n 1 'ps aux | grep python | grep -v grep'"
echo ""