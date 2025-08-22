#!/bin/bash

# 最终测试5.3缺陷工作流的脚本
# 验证环境变量传递修复是否成功

echo "==========================================="
echo "测试5.3缺陷工作流（修复后）"
echo "==========================================="

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# 1. 停止可能存在的旧进程
echo -e "${YELLOW}1. 清理旧进程...${NC}"
pkill -f "smart_batch_runner.*flawed" 2>/dev/null
pkill -f "ultra_parallel_runner.*flawed" 2>/dev/null
sleep 2
echo -e "${GREEN}   ✅ 清理完成${NC}"

# 2. 设置环境变量
echo -e "${YELLOW}2. 设置环境变量...${NC}"
export STORAGE_FORMAT="parquet"
export MODEL_TYPE="opensource" 
export NUM_INSTANCES="2"  # 使用小实例数测试
export RATE_MODE="fixed"

echo "   STORAGE_FORMAT=$STORAGE_FORMAT"
echo "   MODEL_TYPE=$MODEL_TYPE"
echo "   NUM_INSTANCES=$NUM_INSTANCES"
echo "   RATE_MODE=$RATE_MODE"

# 3. 记录测试前的数据状态
echo -e "${YELLOW}3. 记录测试前状态...${NC}"
python3 -c "
from pathlib import Path
from datetime import datetime
import pandas as pd
import json

# 记录Parquet状态
parquet_file = Path('pilot_bench_parquet_data/test_results.parquet')
if parquet_file.exists():
    mod_time = datetime.fromtimestamp(parquet_file.stat().st_mtime)
    df = pd.read_parquet(parquet_file)
    print(f'   Parquet: {len(df)} 条记录, 最后更新: {mod_time.strftime(\"%H:%M:%S\")}')
    # 记录初始记录数
    with open('.test_initial_count', 'w') as f:
        f.write(str(len(df)))
else:
    print('   Parquet: 文件不存在')
    with open('.test_initial_count', 'w') as f:
        f.write('0')

# 记录JSON状态
json_file = Path('pilot_bench_cumulative_results/master_database.json')
if json_file.exists():
    mod_time = datetime.fromtimestamp(json_file.stat().st_mtime)
    with open(json_file) as f:
        data = json.load(f)
    total = data.get('summary', {}).get('total_tests', 0)
    print(f'   JSON: {total} 个测试, 最后更新: {mod_time.strftime(\"%H:%M:%S\")}')
"

# 4. 运行测试
echo -e "${YELLOW}4. 启动5.3测试（单个模型，单个缺陷类型）...${NC}"

# 选择一个模型和一个缺陷类型进行快速测试
TEST_MODEL="DeepSeek-V3-0324"
TEST_FLAW="flawed_sequence_disorder"

echo -e "${BLUE}   模型: $TEST_MODEL${NC}"
echo -e "${BLUE}   缺陷: $TEST_FLAW${NC}"
echo -e "${BLUE}   实例: $NUM_INSTANCES${NC}"

# 直接运行测试
python3 smart_batch_runner.py \
    --model "$TEST_MODEL" \
    --prompt-types "$TEST_FLAW" \
    --difficulty "easy" \
    --task-types "simple_task" \
    --num-instances "$NUM_INSTANCES" \
    --max-workers 10 \
    --tool-success-rate 0.8 \
    --batch-commit \
    --checkpoint-interval 5 \
    --save-logs \
    --no-silent &

TEST_PID=$!
echo -e "${GREEN}   ✅ 测试已启动 (PID: $TEST_PID)${NC}"

# 5. 等待一段时间
echo -e "${YELLOW}5. 等待30秒让测试运行...${NC}"
for i in {1..6}; do
    sleep 5
    echo -n "."
done
echo ""

# 6. 检查数据更新
echo -e "${YELLOW}6. 检查数据是否更新...${NC}"
python3 -c "
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import json

success = False

# 检查Parquet更新
parquet_file = Path('pilot_bench_parquet_data/test_results.parquet')
if parquet_file.exists():
    mod_time = datetime.fromtimestamp(parquet_file.stat().st_mtime)
    age = datetime.now() - mod_time
    df = pd.read_parquet(parquet_file)
    
    # 读取初始记录数
    initial_count = 0
    if Path('.test_initial_count').exists():
        with open('.test_initial_count', 'r') as f:
            initial_count = int(f.read())
    
    new_records = len(df) - initial_count
    
    print(f'   Parquet: {len(df)} 条记录 (+{new_records}), 更新于 {age.seconds} 秒前')
    
    if age < timedelta(minutes=1):
        print('   ✅ Parquet已更新！')
        success = True
        
        # 检查是否有flawed_sequence_disorder记录
        if 'prompt_type' in df.columns:
            flawed_records = df[df['prompt_type'] == 'flawed_sequence_disorder']
            if not flawed_records.empty:
                print(f'   ✅ 找到 {len(flawed_records)} 条 flawed_sequence_disorder 记录')
    else:
        print('   ⚠️ Parquet未更新')

# 检查JSON更新
json_file = Path('pilot_bench_cumulative_results/master_database.json')
if json_file.exists():
    mod_time = datetime.fromtimestamp(json_file.stat().st_mtime)
    age = datetime.now() - mod_time
    
    with open(json_file) as f:
        data = json.load(f)
    
    print(f'   JSON: 更新于 {age.seconds} 秒前')
    
    # 检查是否有DeepSeek-V3-0324的flawed数据
    if 'DeepSeek-V3-0324' in data.get('models', {}):
        model_data = data['models']['DeepSeek-V3-0324']
        if 'by_prompt_type' in model_data:
            if 'flawed_sequence_disorder' in model_data['by_prompt_type']:
                print('   ✅ JSON包含 flawed_sequence_disorder 数据')
                success = True

# 清理临时文件
Path('.test_initial_count').unlink(missing_ok=True)

if success:
    print('')
    print('🎉 修复成功！数据正在正确保存。')
else:
    print('')
    print('⚠️ 数据可能仍在生成中，请再等待一段时间。')
"

# 7. 查看进程状态
echo -e "${YELLOW}7. 检查进程状态...${NC}"
if ps -p $TEST_PID > /dev/null; then
    echo -e "${GREEN}   ✅ 测试进程仍在运行${NC}"
    
    # 获取更多进程信息
    ps aux | grep -E "python.*smart_batch.*$TEST_MODEL.*flawed" | grep -v grep | head -2
else
    echo -e "${YELLOW}   ⚠️ 测试进程已结束${NC}"
fi

# 8. 显示最新日志
echo -e "${YELLOW}8. 最新日志（最后10行）...${NC}"
latest_log=$(ls -t logs/batch_test_*.log 2>/dev/null | head -1)
if [ -n "$latest_log" ]; then
    tail -10 "$latest_log"
else
    echo "   未找到日志文件"
fi

echo ""
echo "==========================================="
echo -e "${GREEN}测试完成！${NC}"
echo "==========================================="
echo ""
echo "后续操作："
echo "1. 如果数据已更新，说明修复成功"
echo "2. 停止测试: kill $TEST_PID"
echo "3. 查看完整日志: tail -f logs/batch_test_*.log"
echo "4. 运行完整测试: ./run_systematic_test_final.sh"
echo ""
echo "提示："
echo "- 如果数据成功更新，可以增加NUM_INSTANCES运行更大规模测试"
echo "- 使用 watch -n 10 'ls -la pilot_bench_parquet_data/' 监控文件更新"