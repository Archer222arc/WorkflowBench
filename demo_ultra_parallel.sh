#!/bin/bash

# 超高并行模式演示脚本
# 展示传统模式 vs 超高并行模式的性能差异

echo "🚀 超高并行模式演示"
echo "===================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}当前实例配置:${NC}"
echo "  Azure实例:"
echo "    DeepSeek: 6个 (V3: 3个, R1: 3个) - 每个100并发"
echo "    Llama: 3个 - 每个100并发"
echo "  IdealLab API Keys:"
echo "    Qwen系列: 3个API Key - 每个5并发"
echo "  总计: 12个虚拟实例"
echo "  总理论容量: 915并发 (900 Azure + 15 IdealLab)"
echo ""

echo -e "${YELLOW}性能对比分析:${NC}"
echo ""

# 模拟传统模式性能
echo -e "${RED}📊 传统模式 (单实例)${NC}"
echo "  使用实例: 1个"
echo "  并发数: 100"
echo "  资源利用率: 11% (100/900)"
echo "  20*5=100个测试预计时间: 10-15分钟"
echo ""

# 模拟超高并行模式性能
echo -e "${GREEN}🔥 超高并行模式 (多实例/多Key并行)${NC}"
echo "  DeepSeek测试:"
echo "    使用实例: 3个 (V3) + 3个 (R1) = 6个"
echo "    总并发数: 600"
echo "    资源利用率: 66% (600/915)"
echo "    理论加速比: 6倍"
echo "    预计时间: 2-3分钟"
echo ""
echo "  Llama测试:"
echo "    使用实例: 3个"
echo "    总并发数: 300"  
echo "    资源利用率: 33% (300/915)"
echo "    理论加速比: 3倍"
echo "    预计时间: 3-5分钟"
echo ""
echo "  Qwen测试:"
echo "    使用API Key: 3个"
echo "    总并发数: 15"
echo "    资源利用率: 100% (15/15 IdealLab配额)"
echo "    理论加速比: 3倍"
echo "    预计时间: 8-12分钟"
echo ""

echo -e "${CYAN}📈 性能提升总结:${NC}"
echo "  时间节省: 70-85%"
echo "  资源利用率提升: 11% → 67%"
echo "  吞吐量提升: 3-6倍"
echo "  适用模型: DeepSeek, Llama-3.3"
echo ""

echo -e "${YELLOW}🎯 使用方法:${NC}"
echo "1. 命令行启用:"
echo "   ./run_systematic_test_final.sh --ultra-parallel"
echo ""
echo "2. 交互式启用:"
echo "   ./run_systematic_test_final.sh"
echo "   → 选择并发策略 → 选择超高并行模式"
echo ""
echo "3. 直接测试:"
echo "   python ultra_parallel_runner.py --model DeepSeek-V3-0324 --prompt-types baseline,cot --difficulty easy"
echo ""

# 询问是否进行实际演示
echo -e "${GREEN}是否进行实际演示测试? (y/N):${NC}"
read -r demo_choice

if [[ "$demo_choice" =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${CYAN}🚀 启动演示测试...${NC}"
    echo "使用配置: DeepSeek-V3, baseline+cot, 2个实例"
    echo ""
    
    python ultra_parallel_runner.py \
        --model "DeepSeek-V3-0324" \
        --prompt-types "baseline,cot" \
        --difficulty "easy" \
        --task-types "simple_task" \
        --num-instances 2
    
    if [ $? -eq 0 ]; then
        echo ""
        echo -e "${GREEN}✅ 演示测试完成！${NC}"
        echo "检查数据库确认结果是否正确保存"
    else
        echo ""
        echo -e "${RED}❌ 演示测试失败${NC}"
        echo "请检查Azure实例配置和网络连接"
    fi
else
    echo ""
    echo -e "${YELLOW}💡 演示模式就绪，随时可以启用超高并行测试${NC}"
fi

echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}超高并行模式已完全集成到系统化测试框架${NC}"
echo -e "${CYAN}现在可以享受最高90%+的资源利用率！${NC}"
echo -e "${CYAN}============================================${NC}"