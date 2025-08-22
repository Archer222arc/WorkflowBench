#!/bin/bash
#
# 批测试运行脚本 - 使用集成的smart_batch_runner.py
# 支持所有并行功能
#

# 默认配置
NUM_INSTANCES=${NUM_INSTANCES:-20}
DIFFICULTY=${DIFFICULTY:-easy}
TASK_TYPES=${TASK_TYPES:-all}
PROMPT_TYPES=${PROMPT_TYPES:-all}
MODEL=${MODEL:-""}
SAVE_LOGS=${SAVE_LOGS:-true}
SILENT=${SILENT:-false}
PROMPT_PARALLEL=${PROMPT_PARALLEL:-true}
ADAPTIVE=${ADAPTIVE:-true}
BATCH_COMMIT=${BATCH_COMMIT:-false}
AI_CLASSIFICATION=${AI_CLASSIFICATION:-false}

# 显示帮助信息
show_help() {
    cat << EOF
使用方法: $0 [选项]

选项:
    -m, --model MODEL           指定模型名称（必需，除非使用--all-models）
    -p, --prompt-types TYPES    Prompt类型(all/baseline/cot/optimal/逗号分隔)
    -t, --task-types TYPES      任务类型(all/simple_task/basic_task/等)
    -n, --num-instances NUM     每种配置的实例数(默认20)
    -d, --difficulty LEVEL      难度级别(easy/medium/hard，默认easy)
    --all-models               测试所有主要模型
    --no-logs                  不保存详细日志
    --silent                   静默模式
    --no-parallel              禁用prompt并行
    --batch-commit             批量提交模式
    --ai-classification        启用AI错误分类

环境变量:
    NUM_INSTANCES              实例数(默认20)
    DIFFICULTY                 难度(默认easy)
    TASK_TYPES                 任务类型(默认all)
    PROMPT_TYPES               Prompt类型(默认all)

示例:
    # 测试单个模型的所有prompt types
    $0 -m gpt-4o-mini

    # 测试多个prompt types并行
    $0 -m qwen2.5-3b-instruct -p baseline,cot,optimal

    # 测试所有主要模型
    $0 --all-models

    # 自定义配置
    $0 -m gpt-5-nano -n 50 -d medium -t all
EOF
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -m|--model)
            MODEL="$2"
            shift 2
            ;;
        -p|--prompt-types)
            PROMPT_TYPES="$2"
            shift 2
            ;;
        -t|--task-types)
            TASK_TYPES="$2"
            shift 2
            ;;
        -n|--num-instances)
            NUM_INSTANCES="$2"
            shift 2
            ;;
        -d|--difficulty)
            DIFFICULTY="$2"
            shift 2
            ;;
        --all-models)
            RUN_ALL_MODELS=true
            shift
            ;;
        --no-logs)
            SAVE_LOGS=false
            shift
            ;;
        --silent)
            SILENT=true
            shift
            ;;
        --no-parallel)
            PROMPT_PARALLEL=false
            shift
            ;;
        --batch-commit)
            BATCH_COMMIT=true
            shift
            ;;
        --ai-classification)
            AI_CLASSIFICATION=true
            shift
            ;;
        *)
            echo "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
done

# 构建通用参数
build_args() {
    local args=""
    
    args="$args --num-instances $NUM_INSTANCES"
    args="$args --difficulty $DIFFICULTY"
    args="$args --task-types $TASK_TYPES"
    args="$args --prompt-types $PROMPT_TYPES"
    
    if [ "$SAVE_LOGS" = "false" ]; then
        args="$args --no-save-logs"
    fi
    
    if [ "$SILENT" = "true" ]; then
        args="$args --silent"
    fi
    
    if [ "$PROMPT_PARALLEL" = "true" ] && [[ "$PROMPT_TYPES" == *","* ]] || [[ "$PROMPT_TYPES" == "all" ]]; then
        args="$args --prompt-parallel"
    fi
    
    if [ "$ADAPTIVE" = "true" ]; then
        args="$args --adaptive"
    else
        args="$args --no-adaptive"
    fi
    
    if [ "$BATCH_COMMIT" = "true" ]; then
        args="$args --batch-commit"
    fi
    
    if [ "$AI_CLASSIFICATION" = "true" ]; then
        args="$args --ai-classification"
    fi
    
    echo "$args"
}

# 运行单个模型测试
run_model_test() {
    local model=$1
    local args=$(build_args)
    
    echo ""
    echo "=========================================="
    echo "测试模型: $model"
    echo "=========================================="
    echo "配置:"
    echo "  Prompt类型: $PROMPT_TYPES"
    echo "  任务类型: $TASK_TYPES"
    echo "  实例数: $NUM_INSTANCES"
    echo "  难度: $DIFFICULTY"
    
    # 根据模型类型显示策略
    if [[ "$model" == *"gpt"* ]] || [[ "$model" == *"deepseek"* ]] || [[ "$model" == *"llama"* ]]; then
        echo "  策略: Azure高并发(50+ workers)"
    elif [[ "$model" == *"qwen"* ]] || [[ "$model" == *"kimi"* ]]; then
        echo "  策略: IdealLab多API Key并行"
    fi
    
    echo ""
    echo "运行命令:"
    echo "python smart_batch_runner.py --model $model $args"
    echo ""
    
    # 运行测试
    python smart_batch_runner.py --model "$model" $args
    
    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        echo "✅ $model 测试完成"
    else
        echo "❌ $model 测试失败 (exit code: $exit_code)"
    fi
    
    return $exit_code
}

# 主逻辑
main() {
    echo "=========================================="
    echo "批测试运行脚本 - 集成版"
    echo "=========================================="
    echo ""
    echo "全局配置:"
    echo "  实例数: $NUM_INSTANCES"
    echo "  难度: $DIFFICULTY"
    echo "  任务类型: $TASK_TYPES"
    echo "  Prompt类型: $PROMPT_TYPES"
    echo "  保存日志: $SAVE_LOGS"
    echo "  Prompt并行: $PROMPT_PARALLEL"
    echo ""
    
    if [ "$RUN_ALL_MODELS" = "true" ]; then
        # 测试所有主要模型
        echo "测试所有主要模型..."
        echo ""
        
        # 定义模型列表
        MODELS=(
            "gpt-4o-mini"
            "qwen2.5-3b-instruct"
            "qwen2.5-7b-instruct"
            "gpt-5-nano"
            "DeepSeek-V3-671B"
        )
        
        # 并行运行所有模型测试
        for model in "${MODELS[@]}"; do
            echo "启动 $model 测试..."
            run_model_test "$model" &
        done
        
        # 等待所有后台任务完成
        echo ""
        echo "等待所有模型测试完成..."
        wait
        
        echo ""
        echo "✅ 所有模型测试完成"
        
    elif [ -n "$MODEL" ]; then
        # 测试单个模型
        run_model_test "$MODEL"
    else
        echo "错误: 必须指定模型名称 (-m MODEL) 或使用 --all-models"
        show_help
        exit 1
    fi
    
    # 显示最终统计
    echo ""
    echo "=========================================="
    echo "测试统计"
    echo "=========================================="
    
    python -c "
import json
from pathlib import Path

db_path = Path('pilot_bench_cumulative_results/master_database.json')
if db_path.exists():
    with open(db_path) as f:
        db = json.load(f)
    
    print(f'总测试数: {db.get(\"summary\", {}).get(\"total_tests\", 0)}')
    print(f'总成功数: {db.get(\"summary\", {}).get(\"total_success\", 0)}')
    
    # 显示每个模型的统计
    if 'models' in db:
        print('\n各模型统计:')
        for model in sorted(db['models'].keys()):
            stats = db['models'][model].get('overall_stats', {})
            total = stats.get('total', 0)
            success = stats.get('success', 0)
            if total > 0:
                rate = success / total * 100
                print(f'  {model}: {success}/{total} ({rate:.1f}%)')
"
    
    echo ""
    echo "测试完成时间: $(date)"
    echo "=========================================="
}

# 运行主函数
main