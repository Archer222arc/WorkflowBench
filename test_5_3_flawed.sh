#!/bin/bash

# ============================================
# 5.3 缺陷工作流测试 - 开源模型自动化脚本
# ============================================

echo "============================================"
echo "5.3 缺陷工作流适应性测试 - 开源模型"
echo "============================================"
echo ""
echo "测试配置："
echo "- 模型: 8个开源模型"
echo "- Prompt类型: 7种缺陷类型"
echo "- 难度: easy"
echo "- 工具成功率: 0.8"
echo "- 任务类型: 全部5种"
echo "- 每个测试: 20个实例"
echo ""

# 设置存储格式
export STORAGE_FORMAT="${STORAGE_FORMAT:-parquet}"
echo "存储格式: $STORAGE_FORMAT"

# 开源模型列表
OPENSOURCE_MODELS=(
    "DeepSeek-V3-0324"
    "DeepSeek-R1-0528"
    "qwen2.5-72b-instruct"
    "qwen2.5-32b-instruct"
    "qwen2.5-14b-instruct"
    "qwen2.5-7b-instruct"
    "qwen2.5-3b-instruct"
    "Llama-3.3-70B-Instruct"
)

# 测试单个模型的缺陷工作流
test_model_flawed() {
    local model=$1
    echo ""
    echo "----------------------------------------"
    echo "测试模型: $model"
    echo "----------------------------------------"
    
    # 使用超并行模式运行所有7种缺陷类型
    echo "启动缺陷测试组1: 结构缺陷 (sequence_disorder, tool_misuse, parameter_error)"
    python ultra_parallel_runner.py \
        --model "$model" \
        --prompt-types "flawed_sequence_disorder,flawed_tool_misuse,flawed_parameter_error" \
        --difficulty "easy" \
        --task-types "all" \
        --num-instances 20 \
        --tool-success-rate 0.8 \
        --rate-mode "adaptive" \
        --silent &
    
    local pid1=$!
    
    echo "启动缺陷测试组2: 操作缺陷 (missing_step, redundant_operations)"
    python ultra_parallel_runner.py \
        --model "$model" \
        --prompt-types "flawed_missing_step,flawed_redundant_operations" \
        --difficulty "easy" \
        --task-types "all" \
        --num-instances 20 \
        --tool-success-rate 0.8 \
        --rate-mode "adaptive" \
        --silent &
    
    local pid2=$!
    
    echo "启动缺陷测试组3: 逻辑缺陷 (logical_inconsistency, semantic_drift)"
    python ultra_parallel_runner.py \
        --model "$model" \
        --prompt-types "flawed_logical_inconsistency,flawed_semantic_drift" \
        --difficulty "easy" \
        --task-types "all" \
        --num-instances 20 \
        --tool-success-rate 0.8 \
        --rate-mode "adaptive" \
        --silent &
    
    local pid3=$!
    
    # 等待所有组完成
    echo "等待 $model 的所有缺陷测试完成..."
    wait $pid1
    local status1=$?
    wait $pid2
    local status2=$?
    wait $pid3
    local status3=$?
    
    if [ $status1 -eq 0 ] && [ $status2 -eq 0 ] && [ $status3 -eq 0 ]; then
        echo "✅ $model 缺陷工作流测试完成"
        return 0
    else
        echo "❌ $model 缺陷工作流测试失败"
        return 1
    fi
}

# 主测试流程
main() {
    echo "开始5.3缺陷工作流测试..."
    echo ""
    
    # 测试所有开源模型
    for model in "${OPENSOURCE_MODELS[@]}"; do
        test_model_flawed "$model"
        if [ $? -ne 0 ]; then
            echo "警告: $model 测试失败，继续下一个模型..."
        fi
        
        # 每个模型测试后查看数据更新
        echo ""
        echo "检查数据更新..."
        python monitor_parquet_updates.py | grep -E "(今天的记录|最后修改)"
        echo ""
    done
    
    echo ""
    echo "============================================"
    echo "5.3 缺陷工作流测试完成"
    echo "============================================"
    
    # 显示最终统计
    python -c "
import json
from pathlib import Path

db_path = Path('pilot_bench_cumulative_results/master_database.json')
with open(db_path, 'r') as f:
    db = json.load(f)

print('\n=== 5.3 测试结果汇总 ===\n')

models = ['DeepSeek-V3-0324', 'DeepSeek-R1-0528', 'qwen2.5-72b-instruct', 
          'qwen2.5-32b-instruct', 'qwen2.5-14b-instruct', 'qwen2.5-7b-instruct',
          'qwen2.5-3b-instruct', 'Llama-3.3-70B-Instruct']

for model in models:
    if model in db['models']:
        model_data = db['models'][model]
        print(f'{model}:')
        
        # 统计缺陷测试
        flawed_count = 0
        flawed_types = []
        if 'by_prompt_type' in model_data:
            for prompt_type in model_data['by_prompt_type']:
                if 'flawed' in prompt_type:
                    flawed_types.append(prompt_type)
                    if 'by_tool_success_rate' in model_data['by_prompt_type'][prompt_type]:
                        if '0.8' in model_data['by_prompt_type'][prompt_type]['by_tool_success_rate']:
                            rate_data = model_data['by_prompt_type'][prompt_type]['by_tool_success_rate']['0.8']
                            if 'by_difficulty' in rate_data and 'easy' in rate_data['by_difficulty']:
                                diff_data = rate_data['by_difficulty']['easy']
                                if 'by_task_type' in diff_data:
                                    for task_data in diff_data['by_task_type'].values():
                                        flawed_count += task_data.get('total', 0)
        
        if flawed_types:
            print(f'  缺陷类型: {len(flawed_types)}种')
            print(f'  总测试数: {flawed_count}')
            for flaw in flawed_types[:3]:  # 显示前3种
                print(f'    - {flaw}')
        else:
            print('  无缺陷测试数据')
        print()
"
}

# 运行主函数
main