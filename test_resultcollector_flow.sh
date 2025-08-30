#!/bin/bash
# 测试ResultCollector完整流程

echo "🔍 测试ResultCollector合并机制"
echo "================================"

# 设置环境变量启用ResultCollector
export USE_RESULT_COLLECTOR=true
export STORAGE_FORMAT=json

echo "1. 清理旧的临时文件..."
rm -rf temp_results/*.json 2>/dev/null
mkdir -p temp_results

echo "2. 检查数据库当前状态..."
python3 -c "
import json
from pathlib import Path

db_path = Path('pilot_bench_cumulative_results/master_database.json')
if db_path.exists():
    with open(db_path, 'r') as f:
        db = json.load(f)
    
    print('📊 当前数据库状态:')
    models = db.get('models', {})
    for model_name in models:
        stats = models[model_name].get('overall_stats', {})
        total = stats.get('total_tests', 0)
        if total > 0:
            print(f'  - {model_name}: {total} tests')
"

echo ""
echo "3. 启动ResultMerger后台进程..."
python3 -c "
from result_merger import start_auto_merge, stop_auto_merge, force_merge
import time
import threading
import sys

def run_merger():
    print('🚀 ResultMerger启动')
    merger = start_auto_merge(interval=5)  # 每5秒检查一次
    
    # 运行60秒
    for i in range(12):
        time.sleep(5)
        print(f'⏰ Merger运行中... {i*5}/60秒')
    
    print('🛑 停止Merger并执行最终合并...')
    stop_auto_merge()
    count = force_merge()
    print(f'✅ 最终合并了{count}个文件')

# 在后台运行merger
merger_thread = threading.Thread(target=run_merger, daemon=True)
merger_thread.start()

# 等待merger启动
time.sleep(2)

print('4. 模拟并发测试...')

# 创建测试数据
import json
from pathlib import Path
import random
import time

temp_dir = Path('temp_results')
temp_dir.mkdir(exist_ok=True)

models = ['DeepSeek-V3-0324', 'qwen2.5-72b-instruct', 'gpt-4o-mini']

for i in range(3):
    for model in models:
        # 创建测试结果
        result = {
            'model': model,
            'results': []
        }
        
        # 添加5个测试结果
        for j in range(5):
            test_result = {
                'model': model,
                'task_type': random.choice(['simple_task', 'basic_task', 'data_pipeline']),
                'prompt_type': 'optimal',
                'difficulty': 'easy',
                'success': random.choice([True, False]),
                'execution_time': random.uniform(10, 60),
                'turns': random.randint(5, 15),
                'tool_calls': random.randint(3, 10),
                'workflow_score': random.uniform(0.6, 1.0),
                'phase2_score': random.uniform(0.6, 1.0),
                'quality_score': random.uniform(0.6, 1.0),
                'final_score': random.uniform(0.6, 1.0),
                'tool_success_rate': 0.8,
                'tool_coverage_rate': random.uniform(0.5, 1.0),
                'timestamp': time.time()
            }
            result['results'].append(test_result)
        
        # 写入临时文件
        filename = f'test_{model}_{i}_{int(time.time()*1000)}.json'
        filepath = temp_dir / filename
        with open(filepath, 'w') as f:
            json.dump(result, f, indent=2)
        print(f'  ✅ 创建测试文件: {filename}')
    
    print(f'  等待5秒让merger处理...')
    time.sleep(5)

print('')
print('5. 等待merger完成所有合并...')

# 等待merger线程完成
merger_thread.join()

print('')
print('6. 验证合并结果...')
" &

# 获取后台进程PID
MERGER_PID=$!

# 等待进程完成
wait $MERGER_PID

echo ""
echo "7. 检查数据库最终状态..."
python3 -c "
import json
from pathlib import Path

db_path = Path('pilot_bench_cumulative_results/master_database.json')
if db_path.exists():
    with open(db_path, 'r') as f:
        db = json.load(f)
    
    print('📊 最终数据库状态:')
    models = db.get('models', {})
    for model_name in models:
        stats = models[model_name].get('overall_stats', {})
        total = stats.get('total_tests', 0)
        if total > 0:
            print(f'  - {model_name}: {total} tests')
    
    # 统计新增的测试
    print('')
    print('🎯 测试统计:')
    print(f'  - 模型数量: {len(models)}')
    
    # 检查临时文件
    temp_dir = Path('temp_results')
    temp_files = list(temp_dir.glob('*.json'))
    print(f'  - 剩余临时文件: {len(temp_files)}')
"

echo ""
echo "✅ 测试完成！"