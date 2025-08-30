#!/bin/bash

# 测试超高并行模式的自定义workers功能

echo "============================================"
echo "测试超高并行模式自定义Workers功能"
echo "============================================"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "\n${CYAN}🎉 超高并行模式现在支持自定义Workers数！${NC}"
echo ""

echo -e "${GREEN}✨ 新功能：${NC}"
echo "• 在选择超高并行模式后，会询问是否自定义workers数"
echo "• 提供预设选项：20、30、50、100 workers"
echo "• 支持自定义输入（1-200范围）"
echo "• 每个分片独立使用指定的workers数"
echo ""

echo -e "${YELLOW}使用方法：${NC}"
echo "1. 运行主脚本并选择开源模型测试："
echo "   ./run_systematic_test_final.sh"
echo ""
echo "2. 在并发策略菜单选择选项3："
echo "   3) 🔥 超高并行模式 (Ultra Parallel)"
echo ""
echo "3. 选择速率模式后，会出现新的提示："
echo "   ━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   是否要自定义每个分片的Workers数？"
echo "   1) 使用默认配置（推荐）"
echo "   2) 🔧 自定义Workers数"
echo "   ━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "4. 选择2后，可以选择预设值或输入自定义值"
echo ""

echo -e "${BLUE}📝 示例测试命令：${NC}"
echo ""
echo "# 使用20 workers（超稳定）"
echo "CUSTOM_WORKERS=20 python ultra_parallel_runner.py \\"
echo "  --model DeepSeek-V3-0324 \\"
echo "  --prompt-types baseline \\"
echo "  --difficulty easy \\"
echo "  --task-types simple_task \\"
echo "  --num-instances 2 \\"
echo "  --rate-mode fixed \\"
echo "  --max-workers 20"
echo ""

echo -e "${GREEN}💡 建议配置：${NC}"
echo "• DeepSeek/Llama模型："
echo "  - 20 workers: 稳定运行，内存占用低"
echo "  - 30 workers: 平衡性能与稳定性"
echo "  - 50 workers: 默认配置，较快速度"
echo "  - 100 workers: 极速模式，需充足内存"
echo ""
echo "• Qwen模型（IdealLab）："
echo "  - 建议使用5-10 workers，避免API限流"
echo ""

echo -e "${CYAN}🚀 立即测试新功能：${NC}"
echo -e "${GREEN}./run_systematic_test_final.sh${NC}"
echo ""

# 演示直接命令行使用
echo -e "${YELLOW}直接命令行测试（2个实例，20 workers）：${NC}"
read -p "是否运行测试? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}运行测试...${NC}"
    export STORAGE_FORMAT=json
    python ultra_parallel_runner.py \
        --model DeepSeek-V3-0324 \
        --prompt-types baseline \
        --difficulty easy \
        --task-types simple_task \
        --num-instances 2 \
        --rate-mode fixed \
        --max-workers 20 \
        --silent 2>&1 | head -20
fi

echo -e "\n${GREEN}✅ 功能说明完成！${NC}"