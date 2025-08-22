#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  测试5.3缺陷工作流 - 1实例快速验证${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# 设置进度文件直接到5.3阶段
echo "STEP=3" > test_progress_opensource.txt
echo "MODEL_INDEX=0" >> test_progress_opensource.txt
echo "SUBSTEP=" >> test_progress_opensource.txt

# 清理旧的完成记录
rm -f completed_tests_opensource.txt
touch completed_tests_opensource.txt

echo -e "${GREEN}✅ 已设置从5.3缺陷工作流测试开始${NC}"
echo ""

# 运行所有7种缺陷类型，每个只用1个实例
FLAWED_TYPES=(
    "flawed_sequence_disorder"
    "flawed_tool_misuse"
    "flawed_parameter_error"
    "flawed_missing_step"
    "flawed_redundant_operations"
    "flawed_logical_inconsistency"
    "flawed_semantic_drift"
)

echo -e "${YELLOW}📋 将测试以下缺陷类型（每个1实例）:${NC}"
for flaw in "${FLAWED_TYPES[@]}"; do
    echo "  - $flaw"
done
echo ""

# 选择测试模型
MODEL="gpt-4o-mini"
echo -e "${CYAN}使用模型: $MODEL${NC}"
echo ""

# 运行每个缺陷类型测试
for i in "${!FLAWED_TYPES[@]}"; do
    flaw="${FLAWED_TYPES[$i]}"
    echo -e "${BLUE}▶ 测试 $((i+1))/7: $flaw${NC}"
    
    # 运行测试
    python smart_batch_runner.py \
        --model "$MODEL" \
        --prompt-types "$flaw" \
        --difficulty easy \
        --task-types simple_task \
        --num-instances 1 \
        --tool-success-rate 0.8 \
        --max-workers 1 \
        --adaptive \
        --no-save-logs 2>&1 | grep -E "(成功:|失败:|Database saved)" | tail -3
    
    echo ""
done

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}         测试完成，检查结果${NC}"
echo -e "${GREEN}========================================${NC}"

# 检查数据库中的记录
python -c "
import json
from pathlib import Path

db_path = Path('pilot_bench_cumulative_results/master_database.json')
if db_path.exists():
    with open(db_path, 'r') as f:
        db = json.load(f)
    
    print('\n=== 数据库中的缺陷测试记录 ===')
    if '$MODEL' in db.get('models', {}):
        model_data = db['models']['$MODEL']
        flawed_count = 0
        total_tests = 0
        
        if 'by_prompt_type' in model_data:
            for prompt_type in sorted(model_data['by_prompt_type'].keys()):
                if 'flawed' in prompt_type:
                    flawed_count += 1
                    pt_data = model_data['by_prompt_type'][prompt_type]
                    if 'by_tool_success_rate' in pt_data:
                        rate_data = pt_data['by_tool_success_rate'].get('0.8', {})
                        if 'by_difficulty' in rate_data:
                            diff_data = rate_data['by_difficulty'].get('easy', {})
                            if 'by_task_type' in diff_data:
                                task_data = diff_data['by_task_type'].get('simple_task', {})
                                total = task_data.get('total', 0)
                                success = task_data.get('success', 0)
                                total_tests += total
                                status = '✅' if total > 0 else '❌'
                                print(f'{status} {prompt_type}: {total} 个测试, {success} 成功')
        
        print(f'\n总结:')
        print(f'  应记录缺陷类型: 7')
        print(f'  实际记录缺陷类型: {flawed_count}')
        print(f'  总测试数: {total_tests}')
        
        if flawed_count == 7:
            print(f'  状态: ✅ 并发写入修复有效！所有缺陷类型都已正确记录')
        else:
            print(f'  状态: ❌ 并发写入可能仍有问题，只记录了 {flawed_count}/7 种缺陷')
            missing = []
            expected = [
                'flawed_sequence_disorder',
                'flawed_tool_misuse', 
                'flawed_parameter_error',
                'flawed_missing_step',
                'flawed_redundant_operations',
                'flawed_logical_inconsistency',
                'flawed_semantic_drift'
            ]
            for flaw in expected:
                if flaw not in model_data['by_prompt_type']:
                    missing.append(flaw)
            if missing:
                print(f'  缺失的类型: {missing}')
else:
    print('数据库文件不存在')
"

# 清理测试用的进度文件
rm -f test_progress_opensource.txt
rm -f completed_tests_opensource.txt
