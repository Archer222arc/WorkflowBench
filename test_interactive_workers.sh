#!/bin/bash

# 测试交互式workers选择功能的演示脚本

echo "============================================"
echo "测试交互式Workers选择功能"
echo "============================================"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "\n${CYAN}📋 交互式Workers选择功能已实现！${NC}"
echo -e "${GREEN}这个功能允许您在运行测试时动态选择并发workers数量。${NC}\n"

echo "使用方法："
echo "1. 运行主脚本："
echo -e "   ${YELLOW}./run_systematic_test_final.sh${NC}"
echo ""
echo "2. 在主菜单中选择选项1（开源模型）或2（闭源模型）"
echo ""
echo "3. 在速率限制菜单中选择选项4："
echo -e "   ${BLUE}4) 🔧 自定义（交互式选择并发workers数）${NC}"
echo ""
echo "4. 系统会显示交互式菜单："
echo "   ┌─────────────────────────────────────┐"
echo "   │ 选择并发Workers数：                  │"
echo "   │                                     │"
echo "   │ 1) 20 workers (🟢 稳定推荐)        │"
echo "   │ 2) 30 workers (🟡 中速平衡)        │"
echo "   │ 3) 50 workers (🟠 高速运行)        │"
echo "   │ 4) 100 workers (🔴 极速模式)       │"
echo "   │ 5) 自定义输入 (1-500)              │"
echo "   └─────────────────────────────────────┘"
echo ""

echo -e "${GREEN}✨ 特性：${NC}"
echo "• 根据workers数自动计算最佳QPS"
echo "• 视觉指示器显示性能等级"
echo "• 防止内存溢出的安全限制"
echo "• 支持1-500范围的自定义值"
echo ""

echo -e "${YELLOW}💡 建议：${NC}"
echo "• 20 workers: 适合大多数场景，稳定可靠"
echo "• 30 workers: 平衡性能和稳定性"
echo "• 50 workers: 高性能，需要充足内存"
echo "• 100+ workers: 极速模式，可能导致内存问题"
echo ""

echo -e "${CYAN}🚀 立即尝试：${NC}"
echo -e "${GREEN}./run_systematic_test_final.sh${NC}"
echo ""
echo "============================================"

# 询问是否直接运行演示
echo -e "\n${YELLOW}是否立即运行主脚本查看交互式菜单? (y/n)${NC}"
read -r response

if [[ "$response" =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}启动主脚本...${NC}\n"
    exec ./run_systematic_test_final.sh
fi

echo -e "\n${GREEN}✅ 使用愉快！${NC}"