#!/bin/bash

# 这个脚本会自动运行5.3测试并选择1个实例

echo "开始运行5.3缺陷工作流测试（超并发模式）"
echo ""
echo "将在确认步骤自动选择："
echo "  - 选择2: 快速测试(2个实例)"
echo ""

# 运行脚本，自动输入选项
# 第一个2是选择快速测试（2个实例）
# 第二个空行是按Enter继续
printf "2\n\n" | ./run_systematic_test_final.sh --ultra-parallel

# 测试完成后检查结果
echo ""
echo "========================================="
echo "         检查数据库写入结果"
echo "========================================="

python -c "
import json
from pathlib import Path

db_path = Path('pilot_bench_cumulative_results/master_database.json')
if db_path.exists():
    with open(db_path, 'r') as f:
        db = json.load(f)
    
    # 检查所有开源模型的缺陷测试记录
    models = ['gpt-4o-mini', 'DeepSeek-V3-0324', 'Llama-3.3-70B-Instruct', 
              'qwen2.5-72b-instruct', 'qwen2.5-32b-instruct', 'qwen2.5-14b-instruct', 
              'qwen2.5-7b-instruct', 'qwen2.5-3b-instruct']
    
    for model in models:
        if model in db.get('models', {}):
            print(f'\n=== {model} ===')
            model_data = db['models'][model]
            flawed_count = 0
            
            if 'by_prompt_type' in model_data:
                for prompt_type in sorted(model_data['by_prompt_type'].keys()):
                    if 'flawed' in prompt_type:
                        flawed_count += 1
                        pt_data = model_data['by_prompt_type'][prompt_type]
                        # 获取测试数量
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
            
            if flawed_count > 0:
                print(f'  记录的缺陷类型数: {flawed_count}/7')
    
    print('\n========================================')
    print('超并发写入测试结果:')
    
    # 统计总体情况
    total_models_with_flawed = 0
    total_flawed_types = 0
    
    for model in models:
        if model in db.get('models', {}):
            model_data = db['models'][model]
            if 'by_prompt_type' in model_data:
                has_flawed = False
                for pt in model_data['by_prompt_type']:
                    if 'flawed' in pt:
                        has_flawed = True
                        total_flawed_types += 1
                if has_flawed:
                    total_models_with_flawed += 1
    
    if total_models_with_flawed > 0:
        avg_flawed = total_flawed_types / total_models_with_flawed
        print(f'  有缺陷测试的模型数: {total_models_with_flawed}')
        print(f'  平均每个模型的缺陷类型数: {avg_flawed:.1f}/7')
        
        if avg_flawed >= 6:
            print('  ✅ 超并发写入正常工作！大部分缺陷类型都被正确记录')
        elif avg_flawed >= 4:
            print('  ⚠️ 超并发写入部分工作，但有一些缺陷类型丢失')
        else:
            print('  ❌ 超并发写入可能有问题，大量缺陷类型未被记录')
    else:
        print('  ❌ 没有找到任何缺陷测试记录')
"
