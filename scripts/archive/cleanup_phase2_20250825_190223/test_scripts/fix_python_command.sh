#!/bin/bash

# 修复run_systematic_test_final.sh中的python命令问题

echo "==========================================="
echo "修复Python命令执行问题"
echo "==========================================="

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 备份原文件
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
cp run_systematic_test_final.sh "run_systematic_test_final.sh.backup_${TIMESTAMP}"
echo -e "${GREEN}✅ 备份已创建: run_systematic_test_final.sh.backup_${TIMESTAMP}${NC}"

# 创建修复文件
cp run_systematic_test_final.sh run_systematic_test_final_fixed.sh

echo -e "${YELLOW}开始修复...${NC}"

# 1. 修复所有python命令为python3
echo -e "${BLUE}1. 修复python命令为python3...${NC}"
sed -i.bak 's/cmd="python smart_batch_runner.py/cmd="python3 smart_batch_runner.py/g' run_systematic_test_final_fixed.sh
sed -i.bak 's/ python smart_batch_runner.py/ python3 smart_batch_runner.py/g' run_systematic_test_final_fixed.sh

# 2. 在eval执行前确保环境变量设置
echo -e "${BLUE}2. 修复eval执行前的环境变量...${NC}"

# 在第3089行的eval前添加环境变量导出
sed -i.bak '/eval "\$cmd"/i\
        # 确保环境变量在eval执行时生效\
        export STORAGE_FORMAT="${STORAGE_FORMAT}"\
        export MODEL_TYPE="${MODEL_TYPE}"\
        export NUM_INSTANCES="${NUM_INSTANCES}"\
        export RATE_MODE="${RATE_MODE}"' run_systematic_test_final_fixed.sh

# 3. 统计修复数量
echo ""
echo -e "${YELLOW}统计修复结果...${NC}"

python_count=$(grep -c "python3 smart_batch_runner.py" run_systematic_test_final_fixed.sh)
export_count=$(grep -c "export STORAGE_FORMAT" run_systematic_test_final_fixed.sh)

echo -e "  python3命令: ${GREEN}${python_count}${NC} 处"
echo -e "  环境变量导出: ${GREEN}${export_count}${NC} 处"

# 清理临时文件
rm -f run_systematic_test_final_fixed.sh.bak*

echo ""
echo "==========================================="
echo -e "${GREEN}修复完成！${NC}"
echo "==========================================="
echo ""
echo "应用修复："
echo "  mv run_systematic_test_final_fixed.sh run_systematic_test_final.sh"
echo ""
echo "测试修复："
echo "  export STORAGE_FORMAT=parquet"
echo "  ./run_systematic_test_final.sh"