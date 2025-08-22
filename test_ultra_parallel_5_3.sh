#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  测试5.3超并发写入 - 模拟脚本行为${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# 定义测试模型（选择2个快速测试的模型）
MODELS=("gpt-4o-mini" "gpt-5-mini")

# 定义所有7种缺陷类型
FLAWED_TYPES=(
    "flawed_sequence_disorder"
    "flawed_tool_misuse"
    "flawed_parameter_error"
    "flawed_missing_step"
    "flawed_redundant_operations"
    "flawed_logical_inconsistency"
    "flawed_semantic_drift"
)

echo -e "${YELLOW}📋 模拟 run_systematic_test_final.sh 的超并发行为${NC}"
echo -e "${YELLOW}   测试 ${#MODELS[@]} 个模型 × ${#FLAWED_TYPES[@]} 种缺陷类型${NC}"
echo -e "${YELLOW}   每个配置只运行1个实例以快速验证${NC}"
echo ""

# 启动所有模型的并行测试
pids=()

for model in "${MODELS[@]}"; do
    echo -e "${CYAN}🚀 启动 $model 的7种缺陷测试（并发）...${NC}"
    
    # 将所有7种缺陷类型合并成一个命令
    flawed_list=$(IFS=,; echo "${FLAWED_TYPES[*]}")
    
    # 后台运行测试
    (
        echo -e "${GREEN}  ✓ $model 开始缺陷工作流测试${NC}"
        python smart_batch_runner.py \
            --model "$model" \
            --prompt-types "$flawed_list" \
            --difficulty easy \
            --task-types simple_task \
            --num-instances 1 \
            --tool-success-rate 0.8 \
            --max-workers 7 \
            --adaptive \
            --no-save-logs 2>&1 | grep -E "(成功:|失败:|Database saved)" | tail -5
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}  ✓ $model 缺陷测试完成${NC}"
        else
            echo -e "${RED}  ✗ $model 缺陷测试失败${NC}"
        fi
    ) &
    pids+=($!)
    
    echo -e "${CYAN}  🚀 $model 已启动 (PID: ${pids[-1]})${NC}"
    
    # 短暂延迟避免同时启动造成冲突
    sleep 2
done

# 等待所有模型完成
echo ""
echo -e "${CYAN}⏳ 等待所有并发测试完成...${NC}"
for pid in "${pids[@]}"; do
    wait $pid
done

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}         检查并发写入结果${NC}"
echo -e "${GREEN}========================================${NC}"

# 检查数据库中的记录
python -c "
import json
from pathlib import Path

db_path = Path('pilot_bench_cumulative_results/master_database.json')
if db_path.exists():
    with open(db_path, 'r') as f:
        db = json.load(f)
    
    models = ['gpt-4o-mini', 'gpt-5-mini']
    expected_flawed = [
        'flawed_sequence_disorder',
        'flawed_tool_misuse',
        'flawed_parameter_error',
        'flawed_missing_step',
        'flawed_redundant_operations',
        'flawed_logical_inconsistency',
        'flawed_semantic_drift'
    ]
    
    all_success = True
    
    for model in models:
        if model in db.get('models', {}):
            print(f'\n=== {model} ===')
            model_data = db['models'][model]
            flawed_found = []
            
            if 'by_prompt_type' in model_data:
                for prompt_type in model_data['by_prompt_type'].keys():
                    if 'flawed' in prompt_type:
                        flawed_found.append(prompt_type)
                        # 获取测试数量
                        pt_data = model_data['by_prompt_type'][prompt_type]
                        total = 0
                        if 'by_tool_success_rate' in pt_data:
                            for rate in pt_data['by_tool_success_rate'].values():
                                if 'by_difficulty' in rate:
                                    for diff in rate['by_difficulty'].values():
                                        if 'by_task_type' in diff:
                                            for task in diff['by_task_type'].values():
                                                total += task.get('total', 0)
                        
                        status = '✅' if total > 0 else '❌'
                        print(f'  {status} {prompt_type}: {total} 个测试')
            
            # 检查是否所有预期的缺陷类型都被记录
            missing = []
            for expected in expected_flawed:
                if expected not in flawed_found:
                    missing.append(expected)
            
            if missing:
                print(f'  ❌ 缺失的类型: {missing}')
                all_success = False
            else:
                print(f'  ✅ 所有7种缺陷类型都已记录！')
            
            print(f'  记录的缺陷类型数: {len(flawed_found)}/7')
        else:
            print(f'\n❌ {model} 未找到')
            all_success = False
    
    print('\n' + '='*40)
    if all_success:
        print('✅ 超并发写入测试成功！')
        print('   所有模型的所有缺陷类型都被正确记录到数据库')
    else:
        print('❌ 超并发写入测试失败！')
        print('   部分缺陷类型未被正确记录到数据库')
else:
    print('数据库文件不存在')
"
