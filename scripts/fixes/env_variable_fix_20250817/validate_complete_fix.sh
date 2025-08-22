#!/bin/bash

# 验证完整修复效果的脚本
# 测试所有5个阶段的环境变量传递是否正确

echo "==========================================="
echo "验证环境变量传递修复"
echo "==========================================="

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# 检查修复文件是否存在
if [ ! -f "run_systematic_test_final_fixed.sh" ]; then
    echo -e "${RED}❌ 修复文件不存在: run_systematic_test_final_fixed.sh${NC}"
    echo "请先运行: python complete_fix.py"
    exit 1
fi

echo -e "${YELLOW}1. 检查修复内容...${NC}"

# 统计环境变量导出的数量
export_count=$(grep -c "export STORAGE_FORMAT=" run_systematic_test_final_fixed.sh)
echo -e "  环境变量导出次数: ${GREEN}${export_count}${NC}"

# 检查每个测试阶段
echo ""
echo -e "${YELLOW}2. 各测试阶段修复状态:${NC}"

# 5.1 基准测试
echo -n "  5.1 基准测试: "
if grep -A 5 "echo -e.*开始基准测试" run_systematic_test_final_fixed.sh | grep -q "export STORAGE_FORMAT"; then
    echo -e "${GREEN}✅ 已修复${NC}"
else
    echo -e "${RED}❌ 未修复${NC}"
fi

# 5.2 Qwen very_easy
echo -n "  5.2 Qwen very_easy: "
if grep -A 5 "echo.*very_easy" run_systematic_test_final_fixed.sh | grep -q "export STORAGE_FORMAT"; then
    echo -e "${GREEN}✅ 已修复${NC}"
else
    echo -e "${RED}❌ 未修复${NC}"
fi

# 5.2 Qwen medium
echo -n "  5.2 Qwen medium: "
if grep -A 5 "echo.*medium" run_systematic_test_final_fixed.sh | grep -q "export STORAGE_FORMAT"; then
    echo -e "${GREEN}✅ 已修复${NC}"
else
    echo -e "${RED}❌ 未修复${NC}"
fi

# 5.3 缺陷工作流
echo -n "  5.3 缺陷工作流: "
if grep -A 5 "echo -e.*开始缺陷工作流测试" run_systematic_test_final_fixed.sh | grep -q "export STORAGE_FORMAT"; then
    echo -e "${GREEN}✅ 已修复${NC}"
else
    echo -e "${RED}❌ 未修复${NC}"
fi

# 5.4 工具可靠性
echo -n "  5.4 工具可靠性: "
if grep -A 5 "echo -e.*开始工具可靠性测试" run_systematic_test_final_fixed.sh | grep -q "export STORAGE_FORMAT"; then
    echo -e "${GREEN}✅ 已修复${NC}"
else
    echo -e "${RED}❌ 未修复${NC}"
fi

# 5.5 提示敏感性
echo -n "  5.5 提示敏感性: "
if grep -A 5 "echo -e.*开始提示敏感性测试" run_systematic_test_final_fixed.sh | grep -q "export STORAGE_FORMAT"; then
    echo -e "${GREEN}✅ 已修复${NC}"
else
    echo -e "${RED}❌ 未修复${NC}"
fi

# 3. 创建小型测试
echo ""
echo -e "${YELLOW}3. 创建验证测试脚本...${NC}"

cat > test_env_propagation.sh << 'EOF'
#!/bin/bash

# 测试环境变量是否正确传递到Python脚本

echo "测试环境变量传递"
echo "=================="

# 设置环境变量
export STORAGE_FORMAT="parquet"
export MODEL_TYPE="opensource"
export NUM_INSTANCES="2"
export RATE_MODE="fixed"

echo "设置的环境变量:"
echo "  STORAGE_FORMAT=$STORAGE_FORMAT"
echo "  MODEL_TYPE=$MODEL_TYPE"
echo "  NUM_INSTANCES=$NUM_INSTANCES"
echo "  RATE_MODE=$RATE_MODE"

# 测试后台进程中的环境变量传递
echo ""
echo "测试后台进程:"

(
    # 确保环境变量在子进程中可用
    export STORAGE_FORMAT="${STORAGE_FORMAT}"
    export MODEL_TYPE="${MODEL_TYPE}"
    export NUM_INSTANCES="${NUM_INSTANCES}"
    export RATE_MODE="${RATE_MODE}"
    
    python3 -c "
import os
print('后台进程中的环境变量:')
print(f'  STORAGE_FORMAT={os.environ.get(\"STORAGE_FORMAT\", \"未设置\")}')
print(f'  MODEL_TYPE={os.environ.get(\"MODEL_TYPE\", \"未设置\")}')
print(f'  NUM_INSTANCES={os.environ.get(\"NUM_INSTANCES\", \"未设置\")}')
print(f'  RATE_MODE={os.environ.get(\"RATE_MODE\", \"未设置\")}')

# 验证
if os.environ.get('STORAGE_FORMAT') == 'parquet':
    print('✅ 环境变量传递成功!')
else:
    print('❌ 环境变量传递失败!')
"
) &

# 等待后台进程完成
wait

echo ""
echo "测试完成"
EOF

chmod +x test_env_propagation.sh

echo -e "${GREEN}✅ 测试脚本已创建: test_env_propagation.sh${NC}"

# 4. 运行环境变量传递测试
echo ""
echo -e "${YELLOW}4. 运行环境变量传递测试...${NC}"
./test_env_propagation.sh

echo ""
echo "==========================================="
echo -e "${GREEN}验证完成！${NC}"
echo "==========================================="
echo ""
echo "下一步操作:"
echo "1. 如果所有测试都通过，应用修复:"
echo "   cp run_systematic_test_final_fixed.sh run_systematic_test_final.sh"
echo ""
echo "2. 运行实际测试（建议先测试5.3）:"
echo "   export STORAGE_FORMAT=parquet"
echo "   ./run_systematic_test_final.sh"
echo "   选择: 4) 5.3 缺陷工作流测试"
echo ""
echo "3. 监控数据更新:"
echo "   watch -n 10 'ls -la pilot_bench_parquet_data/test_results.parquet'"
echo ""
echo "4. 查看日志:"
echo "   tail -f logs/batch_test_*.log"