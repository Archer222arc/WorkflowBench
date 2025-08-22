import json
from pathlib import Path

db_path = Path('pilot_bench_cumulative_results/master_database.json')
with open(db_path, 'r') as f:
    db = json.load(f)

print('='*70)
print('🔍 5.1 基准测试深度分析')
print('='*70)

# 检查一个模型的详细数据
model = 'DeepSeek-V3-0324'
model_data = db['models'][model]
optimal_data = model_data.get('by_prompt_type', {}).get('optimal', {})
by_tool_rate = optimal_data.get('by_tool_success_rate', {})

print(f'\n分析模型: {model}')
print('-'*70)

# 显示所有tool_success_rate配置
print('\ntool_success_rate 配置:')
for rate_key in sorted(by_tool_rate.keys()):
    rate_data = by_tool_rate[rate_key]
    by_diff = rate_data.get('by_difficulty', {})
    if 'easy' in by_diff:
        easy_data = by_diff['easy']
        total = easy_data.get('total', 0)
        success = easy_data.get('success', 0)
        success_rate = easy_data.get('success_rate', 0)
        
        print(f'  rate={rate_key}: {total}个测试, 成功率={success_rate*100:.1f}%')
        
        # 显示任务类型分布
        by_task = easy_data.get('by_task_type', {})
        for task_type, task_data in by_task.items():
            task_total = task_data.get('total', 0)
            task_success = task_data.get('success', 0)
            task_rate = task_data.get('success_rate', 0)
            print(f'    - {task_type}: {task_total}个测试, 成功率={task_rate*100:.1f}%')

# 预期 vs 实际
print('\n测试覆盖分析:')
print('-'*70)
expected_tasks = ['simple_task', 'basic_task', 'multistep_task', 
                  'comprehensive_task', 'challenging_task']
print(f'预期任务类型: {expected_tasks}')
print(f'预期每种任务: 20个')
print(f'预期总数: 100个 (5种 × 20个)')

actual_tasks = set()
actual_total = 0
for rate_key, rate_data in by_tool_rate.items():
    by_diff = rate_data.get('by_difficulty', {})
    if 'easy' in by_diff:
        easy_data = by_diff['easy']
        by_task = easy_data.get('by_task_type', {})
        for task_type in by_task.keys():
            actual_tasks.add(task_type)
        actual_total += easy_data.get('total', 0)

print(f'\n实际任务类型: {list(actual_tasks)}')
print(f'实际总数: {actual_total}个')

missing_tasks = set(expected_tasks) - actual_tasks
if missing_tasks:
    print(f'\n⚠️ 缺失的任务类型: {list(missing_tasks)}')
    print('   这些任务类型应该每个有20个测试，但实际为0')
else:
    print('\n✅ 所有任务类型都已测试')
