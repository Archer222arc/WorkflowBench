#!/bin/bash
#
# 测试脚本：验证run_systematic_test_final.sh的并行功能
# 可以手动测试特定步骤的并行功能
#

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo "=========================================="
echo -e "${CYAN}测试系统化脚本的并行功能${NC}"
echo "=========================================="
echo ""

# 测试选项
echo "请选择要测试的功能："
echo "1. 测试5.5步骤 - 并行测试baseline和cot"
echo "2. 测试5.3步骤 - 分组并行测试缺陷类型"
echo "3. 测试单个模型的所有prompt types"
echo "4. 测试自定义配置"
echo ""
read -p "请输入选项 (1-4): " option

case $option in
    1)
        echo ""
        echo -e "${GREEN}测试5.5步骤 - 并行测试baseline和cot${NC}"
        echo "模拟运行：gpt-4o-mini 的 baseline,cot 并行测试"
        echo ""
        
        python smart_batch_runner.py \
            --model gpt-4o-mini \
            --prompt-types baseline,cot \
            --difficulty easy \
            --task-types simple_task \
            --num-instances 2 \
            --prompt-parallel \
            --adaptive \
            --no-save-logs
        ;;
        
    2)
        echo ""
        echo -e "${GREEN}测试5.3步骤 - 分组并行测试缺陷类型${NC}"
        echo "模拟运行：qwen2.5-3b-instruct 的缺陷类型分组测试"
        echo ""
        
        # 测试结构缺陷组
        echo -e "${CYAN}组1: 结构缺陷${NC}"
        python smart_batch_runner.py \
            --model qwen2.5-3b-instruct \
            --prompt-types flawed_sequence_disorder,flawed_tool_misuse,flawed_parameter_error \
            --difficulty easy \
            --task-types simple_task \
            --num-instances 2 \
            --prompt-parallel \
            --adaptive \
            --no-save-logs
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ 结构缺陷组测试成功${NC}"
        fi
        ;;
        
    3)
        echo ""
        echo -e "${GREEN}测试单个模型的所有prompt types${NC}"
        echo "选择模型："
        echo "1. gpt-4o-mini (Azure - 高并发)"
        echo "2. qwen2.5-3b-instruct (IdealLab - 多API key)"
        read -p "选择 (1-2): " model_choice
        
        if [ "$model_choice" == "1" ]; then
            MODEL="gpt-4o-mini"
            echo -e "${CYAN}使用Azure策略：所有prompt同时运行${NC}"
        else
            MODEL="qwen2.5-3b-instruct"
            echo -e "${CYAN}使用IdealLab策略：每个prompt使用不同API key${NC}"
        fi
        
        python smart_batch_runner.py \
            --model $MODEL \
            --prompt-types baseline,cot,optimal \
            --difficulty easy \
            --task-types simple_task \
            --num-instances 2 \
            --prompt-parallel \
            --adaptive \
            --no-save-logs
        ;;
        
    4)
        echo ""
        echo -e "${GREEN}自定义测试配置${NC}"
        read -p "模型名称: " MODEL
        read -p "Prompt类型 (逗号分隔): " PROMPTS
        read -p "难度 (easy/medium/hard): " DIFFICULTY
        read -p "任务类型 (all/simple_task/...): " TASKS
        read -p "实例数: " INSTANCES
        
        echo ""
        echo -e "${CYAN}执行自定义测试...${NC}"
        python smart_batch_runner.py \
            --model "$MODEL" \
            --prompt-types "$PROMPTS" \
            --difficulty "$DIFFICULTY" \
            --task-types "$TASKS" \
            --num-instances "$INSTANCES" \
            --prompt-parallel \
            --adaptive \
            --no-save-logs
        ;;
        
    *)
        echo -e "${RED}无效选项${NC}"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo -e "${GREEN}测试完成${NC}"
echo "=========================================="

# 显示统计
echo ""
echo "查看数据库统计："
python -c "
import json
from pathlib import Path

db_path = Path('pilot_bench_cumulative_results/master_database.json')
if db_path.exists():
    with open(db_path) as f:
        db = json.load(f)
    
    summary = db.get('summary', {})
    print(f'总测试数: {summary.get(\"total_tests\", 0)}')
    
    if 'models' in db:
        print('\n最近测试的模型:')
        for model in list(db['models'].keys())[-3:]:
            stats = db['models'][model].get('overall_stats', {})
            total = stats.get('total', 0)
            if total > 0:
                print(f'  {model}: {total} 个测试')
"