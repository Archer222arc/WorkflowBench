#!/bin/bash

# 测试自定义workers数功能的脚本

echo "============================================"
echo "测试自定义workers数功能"
echo "============================================"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 测试1: 显示帮助信息
echo -e "\n${CYAN}测试1: 查看帮助信息${NC}"
./run_systematic_test_final.sh --help | grep -A 2 "workers"

# 测试2: 使用安全的workers数（20）进行小测试
echo -e "\n${CYAN}测试2: 使用20个workers进行小测试${NC}"
echo -e "${YELLOW}命令: ./run_systematic_test_final.sh --workers 20 --instances 2${NC}"

# 创建一个小的测试命令
cat > test_small_run.sh << 'EOF'
#!/bin/bash
export STORAGE_FORMAT=json
python smart_batch_runner.py \
    --model gpt-4o-mini \
    --prompt-types baseline \
    --difficulty easy \
    --task-types simple_task \
    --num-instances 2 \
    --max-workers ${CUSTOM_WORKERS:-20} \
    --tool-success-rate 0.8 \
    --no-adaptive \
    --qps 50 \
    --silent \
    --no-save-logs
EOF

chmod +x test_small_run.sh

# 设置环境变量并运行
export CUSTOM_WORKERS=20
echo -e "${GREEN}运行测试（workers=20, instances=2）...${NC}"
timeout 60 ./test_small_run.sh 2>&1 | tail -10

# 测试3: 验证参数验证
echo -e "\n${CYAN}测试3: 测试无效的workers值${NC}"
./run_systematic_test_final.sh --workers 0 2>&1 | grep "无效"
./run_systematic_test_final.sh --workers 501 2>&1 | grep "无效"
./run_systematic_test_final.sh --workers abc 2>&1 | grep "无效"

# 测试4: 验证环境变量设置
echo -e "\n${CYAN}测试4: 验证环境变量设置${NC}"
CUSTOM_WORKERS=30 bash -c 'echo "CUSTOM_WORKERS=$CUSTOM_WORKERS"'

echo -e "\n${GREEN}✅ 测试完成${NC}"
echo "============================================"
echo "建议的使用命令："
echo "  稳定运行（推荐）:"
echo "    ./run_systematic_test_final.sh --workers 20 --auto"
echo ""
echo "  中速运行:"
echo "    ./run_systematic_test_final.sh --workers 50 --auto"
echo ""
echo "  高速运行（需要足够内存）:"
echo "    ./run_systematic_test_final.sh --workers 100 --auto"
echo "============================================"

# 清理
rm -f test_small_run.sh