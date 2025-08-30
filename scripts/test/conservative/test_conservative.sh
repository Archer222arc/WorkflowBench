#!/bin/bash

# 测试保守并发模式
# 特点：
# 1. 低并发，高稳定性
# 2. 有效利用多个API keys
# 3. 动态资源监控

echo "=================================="
echo "🧪 测试保守并发模式"
echo "=================================="

# 设置环境变量
export USE_RESULT_COLLECTOR=true
export STORAGE_FORMAT=json
export PYTHONUNBUFFERED=1

# 测试选项
TEST_TYPE=${1:-"small"}  # small, medium, full

case $TEST_TYPE in
    "small")
        echo "📦 运行小规模测试..."
        python3 conservative_parallel_runner.py --test
        ;;
    
    "5.3")
        echo "🔬 测试5.3缺陷工作流（qwen模型）..."
        python3 conservative_parallel_runner.py \
            --phase 5.3 \
            --models "qwen2.5-7b-instruct"
        ;;
    
    "5.2")
        echo "📊 测试5.2规模效应..."
        
        # Very Easy测试
        python3 conservative_parallel_runner.py \
            --phase 5.2 \
            --models "qwen2.5-72b-instruct,qwen2.5-32b-instruct,qwen2.5-14b-instruct" \
            --difficulty "very_easy" \
            --num-instances 20
        
        sleep 30
        
        # Medium测试
        python3 conservative_parallel_runner.py \
            --phase 5.2 \
            --models "qwen2.5-72b-instruct,qwen2.5-32b-instruct,qwen2.5-14b-instruct" \
            --difficulty "medium" \
            --num-instances 20
        ;;
    
    "azure")
        echo "☁️ 测试Azure模型（保守模式）..."
        
        # 直接使用smart_batch_runner，但限制并发
        python3 smart_batch_runner.py \
            --model "DeepSeek-V3-0324" \
            --prompt-types "optimal" \
            --difficulty "easy" \
            --task-types "simple_task" \
            --num-instances 10 \
            --tool-success-rate 0.8 \
            --phase "5.1" \
            --workers 10 \
            --batch-commit \
            --enable-checkpoints
        ;;
    
    "monitor")
        echo "📊 监控系统资源..."
        
        # 启动资源监控
        while true; do
            clear
            echo "========== 系统资源监控 =========="
            echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
            echo ""
            
            # 内存使用
            echo "内存使用:"
            free -h | grep -E "^Mem|^Swap"
            echo ""
            
            # CPU使用
            echo "CPU使用:"
            top -l 1 | head -10
            echo ""
            
            # 进程统计
            echo "Python进程:"
            ps aux | grep -E "(smart_batch|conservative)" | grep -v grep | wc -l
            echo ""
            
            # 活跃连接
            echo "网络连接 (IdealLab):"
            netstat -an | grep "8000" | wc -l
            
            sleep 5
        done
        ;;
    
    *)
        echo "用法: $0 [small|5.3|5.2|azure|monitor]"
        echo ""
        echo "选项:"
        echo "  small   - 小规模测试（4个实例）"
        echo "  5.3     - 测试5.3缺陷工作流"
        echo "  5.2     - 测试5.2规模效应"
        echo "  azure   - 测试Azure模型"
        echo "  monitor - 监控系统资源"
        exit 1
        ;;
esac

echo ""
echo "✅ 测试完成！"
echo ""

# 显示结果统计
if [ "$TEST_TYPE" != "monitor" ]; then
    echo "📊 查看测试结果:"
    python3 -c "
import json
from pathlib import Path

db_path = Path('pilot_bench_cumulative_results/master_database.json')
if db_path.exists():
    with open(db_path, 'r') as f:
        db = json.load(f)
    
    print('最新测试结果:')
    print('='*50)
    
    # 获取最新的测试组
    test_groups = db.get('test_groups', {})
    if test_groups:
        latest_groups = sorted(test_groups.items(), key=lambda x: x[1].get('timestamp', ''), reverse=True)[:3]
        for group_id, group_data in latest_groups:
            print(f\"  {group_data.get('model')}: {group_data.get('total_tests')} tests\")
            print(f\"    时间: {group_data.get('timestamp', 'N/A')}\")
"
fi