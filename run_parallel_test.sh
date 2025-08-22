#!/bin/bash
#
# 并行测试脚本 - 同时测试多个模型
# 充分利用所有并行能力
#

# 配置
NUM_INSTANCES=${NUM_INSTANCES:-20}
DIFFICULTY=${DIFFICULTY:-easy}
TASK_TYPES=${TASK_TYPES:-all}
LOG_DIR=${LOG_DIR:-logs/parallel_test_$(date +%Y%m%d_%H%M%S)}

# 创建日志目录
mkdir -p "$LOG_DIR"

echo "=========================================="
echo "并行批测试 - 多模型同时运行"
echo "=========================================="
echo ""
echo "配置:"
echo "  实例数: $NUM_INSTANCES"
echo "  难度: $DIFFICULTY"
echo "  任务类型: $TASK_TYPES"
echo "  日志目录: $LOG_DIR"
echo ""

# 定义测试组
declare -A TEST_GROUPS

# Azure组 - 高并发
TEST_GROUPS["azure"]="gpt-4o-mini"

# IdealLab组 - 多API key并行
TEST_GROUPS["idealab"]="qwen2.5-3b-instruct qwen2.5-7b-instruct qwen2.5-14b-instruct"

# User Azure组
TEST_GROUPS["user_azure"]="gpt-5-nano DeepSeek-V3-0324"

# 混合组 - DeepSeek不同来源
TEST_GROUPS["deepseek"]="DeepSeek-V3-671B deepseek-v3-671b"

# 运行测试组
run_test_group() {
    local group_name=$1
    local models=$2
    local log_file="$LOG_DIR/${group_name}_test.log"
    
    echo "=========================================="
    echo "启动 $group_name 组测试"
    echo "模型: $models"
    echo "日志: $log_file"
    echo "=========================================="
    
    for model in $models; do
        echo "  启动 $model..."
        
        # 构建命令
        CMD="python smart_batch_runner.py"
        CMD="$CMD --model $model"
        CMD="$CMD --prompt-types all"  # 测试所有prompt types
        CMD="$CMD --task-types $TASK_TYPES"
        CMD="$CMD --num-instances $NUM_INSTANCES"
        CMD="$CMD --difficulty $DIFFICULTY"
        CMD="$CMD --prompt-parallel"  # 启用prompt并行
        CMD="$CMD --adaptive"
        
        # 根据组类型添加特定参数
        case $group_name in
            azure|user_azure)
                CMD="$CMD --max-workers 50"  # 高并发
                ;;
            idealab)
                CMD="$CMD --max-workers 5"   # 保守并发
                ;;
        esac
        
        # 后台运行并记录日志
        echo "命令: $CMD" >> "$log_file"
        nohup $CMD >> "$log_file" 2>&1 &
        
        local pid=$!
        echo "    PID: $pid"
        echo "$pid" >> "$LOG_DIR/pids.txt"
    done
    
    echo ""
}

# 主函数
main() {
    echo "开始时间: $(date)"
    echo ""
    
    # 启动所有测试组
    for group in "${!TEST_GROUPS[@]}"; do
        run_test_group "$group" "${TEST_GROUPS[$group]}"
    done
    
    echo "=========================================="
    echo "所有测试已启动"
    echo "=========================================="
    echo ""
    echo "监控命令:"
    echo "  查看进度: tail -f $LOG_DIR/*.log"
    echo "  查看进程: ps aux | grep smart_batch_runner"
    echo "  查看PID: cat $LOG_DIR/pids.txt"
    echo ""
    
    # 可选：等待所有测试完成
    if [ "$WAIT_COMPLETION" = "true" ]; then
        echo "等待所有测试完成..."
        
        while read pid; do
            if kill -0 $pid 2>/dev/null; then
                wait $pid
            fi
        done < "$LOG_DIR/pids.txt"
        
        echo ""
        echo "=========================================="
        echo "所有测试完成"
        echo "=========================================="
        
        # 显示统计
        show_statistics
    else
        echo "测试在后台运行中..."
        echo "使用 WAIT_COMPLETION=true $0 等待完成"
    fi
}

# 显示统计
show_statistics() {
    echo ""
    echo "测试统计:"
    python -c "
import json
from pathlib import Path

db_path = Path('pilot_bench_cumulative_results/master_database.json')
if db_path.exists():
    with open(db_path) as f:
        db = json.load(f)
    
    summary = db.get('summary', {})
    print(f'  总测试数: {summary.get(\"total_tests\", 0)}')
    print(f'  成功: {summary.get(\"total_success\", 0)}')
    print(f'  失败: {summary.get(\"total_failure\", 0)}')
    
    if 'models' in db:
        print('\n各模型完成情况:')
        for model in sorted(db['models'].keys()):
            stats = db['models'][model].get('overall_stats', {})
            total = stats.get('total', 0)
            if total > 0:
                print(f'  {model}: {total} 个测试')
"
    
    echo ""
    echo "结束时间: $(date)"
}

# 运行主函数
main