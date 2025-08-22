#!/bin/bash

# 修复5.3测试环境变量问题的脚本

echo "=========================================="
echo "5.3测试环境变量修复脚本"
echo "=========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 1. 停止当前运行的5.3测试
echo -e "${YELLOW}1. 停止当前运行的测试...${NC}"
pkill -f "smart_batch_runner.*flawed" 2>/dev/null
pkill -f "ultra_parallel_runner.*flawed" 2>/dev/null
sleep 2

# 检查是否还有进程
remaining=$(ps aux | grep -E "python.*(smart_batch|ultra_parallel).*flawed" | grep -v grep | wc -l)
if [ $remaining -gt 0 ]; then
    echo -e "${RED}   还有 $remaining 个进程未停止，强制终止...${NC}"
    pkill -9 -f "smart_batch_runner.*flawed" 2>/dev/null
    pkill -9 -f "ultra_parallel_runner.*flawed" 2>/dev/null
    sleep 2
fi

echo -e "${GREEN}   ✅ 所有5.3测试进程已停止${NC}"

# 2. 设置环境变量
echo -e "${YELLOW}2. 设置环境变量...${NC}"
export STORAGE_FORMAT="parquet"
echo -e "${GREEN}   ✅ STORAGE_FORMAT=$STORAGE_FORMAT${NC}"

# 3. 验证环境变量
echo -e "${YELLOW}3. 验证环境变量...${NC}"
python3 -c "
import os
storage_format = os.environ.get('STORAGE_FORMAT', 'json')
print(f'   Python中的STORAGE_FORMAT: {storage_format}')
if storage_format == 'parquet':
    print('   ✅ 环境变量正确传递')
else:
    print('   ❌ 环境变量传递失败')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo -e "${RED}环境变量验证失败，退出${NC}"
    exit 1
fi

# 4. 创建测试命令（使用更少的实例进行快速测试）
echo -e "${YELLOW}4. 创建测试命令...${NC}"

# 选择一个模型进行测试
TEST_MODEL="DeepSeek-V3-0324"
PROMPT_TYPES="flawed_sequence_disorder"
NUM_INSTANCES=2  # 减少实例数用于快速测试

cat > run_5_3_test_fixed.sh << 'EOF'
#!/bin/bash

# 确保环境变量设置
export STORAGE_FORMAT="parquet"

echo "环境变量: STORAGE_FORMAT=$STORAGE_FORMAT"

# 运行测试
python3 smart_batch_runner.py \
    --model "DeepSeek-V3-0324" \
    --prompt-types "flawed_sequence_disorder" \
    --difficulty "easy" \
    --task-types "simple_task" \
    --num-instances 2 \
    --max-workers 10 \
    --tool-success-rate 0.8 \
    --batch-commit \
    --checkpoint-interval 5 \
    --save-logs \
    --no-silent

echo "测试完成"
EOF

chmod +x run_5_3_test_fixed.sh
echo -e "${GREEN}   ✅ 测试脚本已创建: run_5_3_test_fixed.sh${NC}"

# 5. 检查当前数据状态
echo -e "${YELLOW}5. 检查当前数据状态...${NC}"
python3 -c "
from pathlib import Path
from datetime import datetime

# 检查Parquet文件
parquet_file = Path('pilot_bench_parquet_data/test_results.parquet')
if parquet_file.exists():
    mod_time = datetime.fromtimestamp(parquet_file.stat().st_mtime)
    print(f'   Parquet最后更新: {mod_time.strftime(\"%Y-%m-%d %H:%M:%S\")}'
)
    
# 检查JSON文件
json_file = Path('pilot_bench_cumulative_results/master_database.json')
if json_file.exists():
    mod_time = datetime.fromtimestamp(json_file.stat().st_mtime)
    print(f'   JSON最后更新: {mod_time.strftime(\"%Y-%m-%d %H:%M:%S\")}')
"

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}修复完成！${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "建议操作："
echo "1. 运行测试脚本: ./run_5_3_test_fixed.sh"
echo "2. 监控数据更新: watch -n 10 'ls -la pilot_bench_parquet_data/test_results.parquet'"
echo "3. 查看日志: tail -f logs/batch_test_*.log"
echo ""
echo "如果测试成功，可以修改run_systematic_test_final.sh："
echo "  在run_smart_test函数开头添加: export STORAGE_FORMAT=\"\${STORAGE_FORMAT}\""
echo ""