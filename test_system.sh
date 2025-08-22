#!/bin/bash

# 系统测试脚本 - 验证基础功能
# 生成时间: 2025-08-19 20:35

echo "=========================================="
echo "🔍 系统基础功能测试"
echo "=========================================="
echo ""

# 1. 检查Python环境
echo "1️⃣ Python环境检查"
echo "-----------------------------------------"
python --version
echo ""

# 2. 检查必要的Python包
echo "2️⃣ 依赖包检查"
echo "-----------------------------------------"
python -c "
import sys
packages = ['requests', 'pandas', 'numpy', 'concurrent.futures', 'json', 'pathlib']
for pkg in packages:
    try:
        __import__(pkg.split('.')[0])
        print(f'✅ {pkg}: 已安装')
    except ImportError:
        print(f'❌ {pkg}: 未安装')
"
echo ""

# 3. 检查API配置
echo "3️⃣ API配置检查"
echo "-----------------------------------------"
python -c "
import json
from pathlib import Path

config_path = Path('config/config.json')
if config_path.exists():
    with open(config_path) as f:
        config = json.load(f)
    
    # 检查Azure配置
    if 'azure' in config:
        print(f'✅ Azure配置: {len(config[\"azure\"])} 个端点')
    else:
        print('❌ Azure配置缺失')
    
    # 检查IdealLab配置
    if 'ideallab' in config:
        keys = config['ideallab'].get('api_keys', [])
        print(f'✅ IdealLab配置: {len(keys)} 个API keys')
    else:
        print('❌ IdealLab配置缺失')
else:
    print('❌ 配置文件不存在')
"
echo ""

# 4. 检查数据库状态
echo "4️⃣ 数据库状态检查"
echo "-----------------------------------------"
python -c "
import json
from pathlib import Path

db_path = Path('pilot_bench_cumulative_results/master_database.json')
if db_path.exists():
    with open(db_path) as f:
        db = json.load(f)
    
    total_tests = db.get('summary', {}).get('total_tests', 0)
    models_count = len(db.get('models', {}))
    print(f'✅ 数据库存在')
    print(f'   - 总测试数: {total_tests}')
    print(f'   - 模型数量: {models_count}')
    
    # 检查qwen模型数据
    qwen_models = [m for m in db.get('models', {}) if 'qwen' in m.lower()]
    if qwen_models:
        print(f'   - qwen模型: {len(qwen_models)}个')
        for model in qwen_models:
            model_data = db['models'][model]
            total = model_data.get('overall_stats', {}).get('total_tests', 0)
            rate = model_data.get('overall_stats', {}).get('success_rate', 0)
            print(f'     • {model}: {total}个测试, {rate:.1%}成功率')
else:
    print('❌ 数据库不存在')
"
echo ""

# 5. 测试qwen API连接（小规模）
echo "5️⃣ qwen API连接测试"
echo "-----------------------------------------"
echo "测试最小的qwen模型连接..."
python -c "
import subprocess
import sys

# 运行极小规模测试
cmd = [
    'python', 'smart_batch_runner.py',
    '--model', 'qwen2.5-3b-instruct',
    '--prompt-types', 'optimal',
    '--difficulty', 'easy',
    '--task-types', 'simple_task',
    '--num-instances', '1',
    '--tool-success-rate', '0.8',
    '--max-workers', '1',
    '--no-save-logs',
    '--silent'
]

print('执行命令:', ' '.join(cmd))
print('⏳ 运行中（限时30秒）...')

try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    
    # 检查输出中的成功率
    if 'Success rate:' in result.stdout:
        for line in result.stdout.split('\n'):
            if 'Success rate:' in line:
                print(f'测试结果: {line.strip()}')
                if '0.0%' in line or '0%' in line:
                    print('⚠️ 警告: 成功率为0%，可能存在API问题')
                else:
                    print('✅ API连接正常')
                break
    elif result.returncode != 0:
        print(f'❌ 测试失败，退出码: {result.returncode}')
        if result.stderr:
            print('错误信息:', result.stderr[:200])
    else:
        print('⚠️ 测试完成但无法解析结果')
        
except subprocess.TimeoutExpired:
    print('❌ 测试超时（30秒）')
except Exception as e:
    print(f'❌ 测试异常: {e}')
"
echo ""

# 6. 检查并发优化状态
echo "6️⃣ 并发优化配置检查"
echo "-----------------------------------------"
python -c "
# 检查ultra_parallel_runner.py中的qwen优化
from pathlib import Path
import re

runner_path = Path('ultra_parallel_runner.py')
if runner_path.exists():
    content = runner_path.read_text()
    
    # 检查是否有qwen优化代码
    if '_create_qwen_smart_shards' in content:
        print('✅ qwen并发优化已实现')
        
        # 检查是否是简化版本
        if '统一策略' in content or 'instances_per_key = max(1, num_instances // 3)' in content:
            print('   - 使用统一简化策略（v3.3.0）')
        else:
            print('   - 使用复杂策略（需要更新）')
    else:
        print('❌ qwen并发优化未实现')
else:
    print('❌ ultra_parallel_runner.py不存在')
"
echo ""

# 7. 总结
echo "=========================================="
echo "📊 测试总结"
echo "=========================================="
echo ""
echo "如果看到0%成功率，可能的原因："
echo "1. API key配置错误"
echo "2. IdealLab服务暂时不可用"
echo "3. 网络连接问题"
echo "4. 模型配额用尽"
echo ""
echo "建议操作："
echo "1. 检查config/config.json中的API配置"
echo "2. 使用./run_systematic_test_final.sh运行正式测试"
echo "3. 查看logs/目录下的详细日志"
echo ""
echo "✅ 系统测试完成"