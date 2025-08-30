#!/bin/bash

# 测试所有runner的存储格式支持

echo "=========================================="
echo "测试Runner存储格式支持"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 测试函数
test_runner() {
    local runner=$1
    local storage_format=$2
    local test_cmd=$3
    
    echo -e "${BLUE}测试 $runner 使用 $storage_format 格式...${NC}"
    
    # 设置存储格式
    export STORAGE_FORMAT=$storage_format
    
    # 运行测试（只运行很短时间）
    timeout 5 $test_cmd 2>&1 | grep -E "\[INFO\].*存储格式|使用.*存储" | head -1
    
    if [ $? -eq 0 ] || [ $? -eq 124 ]; then  # 124是timeout的退出码
        echo -e "${GREEN}✅ $runner 支持 $storage_format${NC}"
        return 0
    else
        echo -e "${RED}❌ $runner 可能不支持 $storage_format${NC}"
        return 1
    fi
    echo ""
}

# 测试smart_batch_runner
echo -e "${YELLOW}1. 测试 smart_batch_runner.py${NC}"
test_runner "smart_batch_runner" "json" "python smart_batch_runner.py --help"
test_runner "smart_batch_runner" "parquet" "python smart_batch_runner.py --help"
echo ""

# 测试batch_test_runner
echo -e "${YELLOW}2. 测试 batch_test_runner.py${NC}"
test_runner "batch_test_runner" "json" "python batch_test_runner.py --help"
test_runner "batch_test_runner" "parquet" "python batch_test_runner.py --help"
echo ""

# 测试enhanced_cumulative_manager
echo -e "${YELLOW}3. 测试 enhanced_cumulative_manager.py${NC}"
export STORAGE_FORMAT=json
echo "测试JSON格式..."
python -c "from enhanced_cumulative_manager import EnhancedCumulativeManager; print('✅ JSON导入成功')" 2>/dev/null || echo "❌ JSON导入失败"

export STORAGE_FORMAT=parquet
echo "测试Parquet格式..."
python -c "from enhanced_cumulative_manager import EnhancedCumulativeManager; print('✅ Parquet导入成功')" 2>/dev/null || echo "❌ Parquet导入失败"
echo ""

# 测试实际写入
echo -e "${YELLOW}4. 测试实际数据写入${NC}"

# JSON写入测试
export STORAGE_FORMAT=json
echo "测试JSON写入..."
python -c "
import os
os.environ['STORAGE_FORMAT'] = 'json'
from cumulative_test_manager import add_test_result
result = add_test_result(
    model='test-runner-json',
    task_type='test',
    prompt_type='baseline',
    success=True,
    execution_time=1.0
)
print(f'JSON写入: {'✅ 成功' if result else '❌ 失败'}')
"

# Parquet写入测试
export STORAGE_FORMAT=parquet
echo "测试Parquet写入..."
python -c "
import os
os.environ['STORAGE_FORMAT'] = 'parquet'
try:
    from parquet_cumulative_manager import add_test_result
    result = add_test_result(
        model='test-runner-parquet',
        task_type='test',
        prompt_type='baseline',
        success=True,
        execution_time=1.0
    )
    print(f'Parquet写入: {'✅ 成功' if result else '❌ 失败'}')
except ImportError:
    print('⚠️ Parquet未安装')
"

echo ""
echo "=========================================="
echo -e "${GREEN}测试完成${NC}"
echo "=========================================="
echo ""
echo "建议："
echo "1. 使用Parquet格式运行并发测试："
echo "   export STORAGE_FORMAT=parquet"
echo "   ./run_systematic_test_final.sh"
echo ""
echo "2. 使用JSON格式进行调试："
echo "   export STORAGE_FORMAT=json"
echo "   python smart_batch_runner.py --model gpt-4o-mini --debug"