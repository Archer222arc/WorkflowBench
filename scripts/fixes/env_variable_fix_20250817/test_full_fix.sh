#!/bin/bash

# 测试完整修复效果

echo "=========================================="
echo "测试5.3修复效果"
echo "=========================================="

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 1. 设置存储格式
echo -e "${YELLOW}1. 设置存储格式为Parquet...${NC}"
export STORAGE_FORMAT="parquet"
echo "   STORAGE_FORMAT=$STORAGE_FORMAT"

# 2. 运行一个小测试
echo -e "${YELLOW}2. 运行测试（DeepSeek-V3-0324，2个实例）...${NC}"

# 直接调用run_smart_test函数
source run_systematic_test_final.sh 2>/dev/null

# 设置必要的变量
PROGRESS_FILE="test_progress.txt"
COMPLETED_FILE="completed_tests.txt"
NUM_INSTANCES=2
RATE_MODE="fixed"

# 运行测试
run_smart_test "DeepSeek-V3-0324" \
    "flawed_sequence_disorder" \
    "easy" \
    "simple_task" \
    "2" \
    "5.3测试-序列错误" \
    "--tool-success-rate 0.8"

echo -e "${GREEN}测试启动完成${NC}"

# 3. 等待一段时间让测试运行
echo -e "${YELLOW}3. 等待30秒让测试运行...${NC}"
sleep 30

# 4. 检查数据更新
echo -e "${YELLOW}4. 检查数据更新...${NC}"
python3 -c "
from pathlib import Path
from datetime import datetime, timedelta

# 检查Parquet文件
parquet_file = Path('pilot_bench_parquet_data/test_results.parquet')
if parquet_file.exists():
    mod_time = datetime.fromtimestamp(parquet_file.stat().st_mtime)
    age = datetime.now() - mod_time
    print(f'   Parquet最后更新: {mod_time.strftime(\"%H:%M:%S\")} ({age.seconds}秒前)')
    
    if age < timedelta(minutes=1):
        print('   ✅ Parquet文件已更新！')
    else:
        print('   ⚠️ Parquet文件未更新')

# 检查JSON文件
json_file = Path('pilot_bench_cumulative_results/master_database.json')
if json_file.exists():
    mod_time = datetime.fromtimestamp(json_file.stat().st_mtime)
    age = datetime.now() - mod_time
    print(f'   JSON最后更新: {mod_time.strftime(\"%H:%M:%S\")} ({age.seconds}秒前)')
    
    if age < timedelta(minutes=1):
        print('   ✅ JSON文件已更新！')
"

# 5. 查看进程
echo -e "${YELLOW}5. 检查运行进程...${NC}"
ps aux | grep -E "python.*smart_batch.*DeepSeek-V3-0324.*flawed" | grep -v grep | head -2

echo ""
echo "=========================================="
echo "测试完成"
echo "=========================================="
echo ""
echo "注意："
echo "1. 如果数据文件已更新，说明修复成功"
echo "2. 可以查看日志确认: tail -f logs/batch_test_*.log"
echo "3. 停止测试: pkill -f 'smart_batch.*DeepSeek-V3-0324.*flawed'"