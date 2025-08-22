#!/bin/bash

# 全面修复run_systematic_test_final.sh中的环境变量传递问题
# 根据用户要求："不光是5.3,每个部分都要仔细检查分析修改一遍"

echo "==========================================="
echo "全面修复环境变量传递问题"
echo "==========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 备份原文件
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
cp run_systematic_test_final.sh "run_systematic_test_final.sh.backup_${TIMESTAMP}"
echo -e "${GREEN}✅ 备份已创建: run_systematic_test_final.sh.backup_${TIMESTAMP}${NC}"

# 创建修复后的文件
cp run_systematic_test_final.sh run_systematic_test_final_fixed.sh

echo -e "${YELLOW}开始修复各个测试部分...${NC}"

# ============================================
# 修复5.1基准测试
# ============================================
echo -e "${BLUE}1. 修复5.1基准测试环境变量传递...${NC}"

# 查找5.1中的后台执行部分并修复
sed -i.bak '/($/,/^            ) &$/{
    /^            ($/a\
\                # 确保环境变量在子进程中可用\
\                export STORAGE_FORMAT="${STORAGE_FORMAT}"\
\                export MODEL_TYPE="${MODEL_TYPE}"\
\                export NUM_INSTANCES="${NUM_INSTANCES}"\
\                export RATE_MODE="${RATE_MODE}"
}' run_systematic_test_final_fixed.sh

# ============================================
# 修复5.2 Qwen规模效应测试
# ============================================
echo -e "${BLUE}2. 修复5.2 Qwen规模效应测试...${NC}"

# 修复5.2的very_easy测试部分
sed -i.bak '/echo -e.*启动.*very_easy/,/^        ) &$/{
    /^        ($/a\
\            # 确保环境变量在子进程中可用\
\            export STORAGE_FORMAT="${STORAGE_FORMAT}"\
\            export MODEL_TYPE="${MODEL_TYPE}"\
\            export NUM_INSTANCES="${NUM_INSTANCES}"\
\            export RATE_MODE="${RATE_MODE}"
}' run_systematic_test_final_fixed.sh

# 修复5.2的medium测试部分
sed -i.bak '/echo -e.*启动.*medium/,/^        ) &$/{
    /^        ($/a\
\            # 确保环境变量在子进程中可用\
\            export STORAGE_FORMAT="${STORAGE_FORMAT}"\
\            export MODEL_TYPE="${MODEL_TYPE}"\
\            export NUM_INSTANCES="${NUM_INSTANCES}"\
\            export RATE_MODE="${RATE_MODE}"
}' run_systematic_test_final_fixed.sh

# ============================================
# 修复5.3缺陷工作流测试
# ============================================
echo -e "${BLUE}3. 修复5.3缺陷工作流测试...${NC}"

# 修复5.3的并发测试部分
sed -i.bak '/echo -e.*启动.*缺陷工作流测试/,/^            ) &$/{
    /^            ($/a\
\                # 确保环境变量在子进程中可用\
\                export STORAGE_FORMAT="${STORAGE_FORMAT}"\
\                export MODEL_TYPE="${MODEL_TYPE}"\
\                export NUM_INSTANCES="${NUM_INSTANCES}"\
\                export RATE_MODE="${RATE_MODE}"
}' run_systematic_test_final_fixed.sh

# ============================================
# 修复5.4工具可靠性测试
# ============================================
echo -e "${BLUE}4. 修复5.4工具可靠性测试...${NC}"

# 修复5.4的并发测试部分
sed -i.bak '/echo -e.*启动.*工具可靠性测试/,/^            ) &$/{
    /^            ($/a\
\                # 确保环境变量在子进程中可用\
\                export STORAGE_FORMAT="${STORAGE_FORMAT}"\
\                export MODEL_TYPE="${MODEL_TYPE}"\
\                export NUM_INSTANCES="${NUM_INSTANCES}"\
\                export RATE_MODE="${RATE_MODE}"
}' run_systematic_test_final_fixed.sh

# ============================================
# 修复5.5提示类型敏感性测试
# ============================================
echo -e "${BLUE}5. 修复5.5提示类型敏感性测试...${NC}"

# 修复5.5的并发测试部分
sed -i.bak '/echo -e.*启动.*提示敏感性测试/,/^            ) &$/{
    /^            ($/a\
\                # 确保环境变量在子进程中可用\
\                export STORAGE_FORMAT="${STORAGE_FORMAT}"\
\                export MODEL_TYPE="${MODEL_TYPE}"\
\                export NUM_INSTANCES="${NUM_INSTANCES}"\
\                export RATE_MODE="${RATE_MODE}"
}' run_systematic_test_final_fixed.sh

# ============================================
# 修复run_smart_test函数本身
# ============================================
echo -e "${BLUE}6. 修复run_smart_test函数...${NC}"

# 在run_smart_test函数开头添加环境变量导出
sed -i.bak '/^run_smart_test() {$/,/^    local model="\$1"$/{
    /^    local model="\$1"$/a\
\    \
\    # 确保环境变量在函数内可用\
\    export STORAGE_FORMAT="${STORAGE_FORMAT}"\
\    export MODEL_TYPE="${MODEL_TYPE}"\
\    export NUM_INSTANCES="${NUM_INSTANCES}"\
\    export RATE_MODE="${RATE_MODE}"
}' run_systematic_test_final_fixed.sh

# ============================================
# 验证修复
# ============================================
echo ""
echo -e "${YELLOW}验证修复结果...${NC}"

# 统计修复的位置数量
fixed_count=$(grep -c "确保环境变量在子进程中可用\|确保环境变量在函数内可用" run_systematic_test_final_fixed.sh)
echo -e "${GREEN}✅ 共修复 ${fixed_count} 处环境变量传递问题${NC}"

# 显示修复的位置
echo ""
echo "修复位置："
grep -n "确保环境变量在子进程中可用\|确保环境变量在函数内可用" run_systematic_test_final_fixed.sh | head -10

# 清理临时备份文件
rm -f run_systematic_test_final_fixed.sh.bak*

echo ""
echo "==========================================="
echo -e "${GREEN}修复完成！${NC}"
echo "==========================================="
echo ""
echo "下一步操作："
echo "1. 检查修复文件: diff run_systematic_test_final.sh run_systematic_test_final_fixed.sh"
echo "2. 应用修复: mv run_systematic_test_final_fixed.sh run_systematic_test_final.sh"
echo "3. 运行测试: ./run_systematic_test_final.sh"
echo ""
echo "测试建议："
echo "- 先用小实例数测试一个模型验证修复效果"
echo "- 监控数据文件更新: watch -n 10 'ls -la pilot_bench_parquet_data/test_results.parquet'"
echo "- 查看日志: tail -f logs/batch_test_*.log"