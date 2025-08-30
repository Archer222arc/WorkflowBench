#!/bin/bash
# run_5_3_optimized.sh - 运行优化后的5.3测试

echo "============================================================"
echo "运行5.3缺陷工作流测试（内存优化版）"
echo "============================================================"
echo ""
echo "📊 内存优化措施："
echo "  1. Workflow预生成: 节省8.75GB"
echo "  2. 任务部分加载: 节省1.15GB"
echo "  3. 总内存使用: 10GB → 0.32GB (节省96.8%)"
echo ""
echo "🚀 运行选项："
echo "  1) 完整运行5.3测试（8个模型×7种缺陷）"
echo "  2) 快速测试（1个模型×3种缺陷）"
echo "  3) 自定义配置"
echo ""
read -p "请选择 [1-3]: " choice

# 设置内存优化环境变量
export USE_PARTIAL_LOADING="true"
export TASK_LOAD_COUNT="${TASK_LOAD_COUNT:-20}"

case $choice in
    1)
        echo "运行完整5.3测试..."
        echo "预计时间: 2-3小时"
        echo "预计内存: <0.5GB"
        ./run_systematic_test_final.sh --phase 5.3
        ;;
    2)
        echo "运行快速测试..."
        echo "测试模型: DeepSeek-V3-0324"
        echo "测试缺陷: sequence_disorder, tool_misuse, parameter_error"
        NUM_INSTANCES=3 TASK_LOAD_COUNT=10 python smart_batch_runner.py \
            --model DeepSeek-V3-0324 \
            --prompt-types flawed_sequence_disorder,flawed_tool_misuse,flawed_parameter_error \
            --difficulty easy \
            --task-types all \
            --num-instances 3 \
            --tool-success-rate 0.8 \
            --batch-commit \
            --checkpoint-interval 10 \
            --max-workers 10 \
            --adaptive \
            --qps 20
        ;;
    3)
        echo "自定义配置:"
        read -p "模型名称 [DeepSeek-V3-0324]: " model
        model="${model:-DeepSeek-V3-0324}"
        
        read -p "实例数量 [10]: " instances
        instances="${instances:-10}"
        
        read -p "每类型加载任务数 [20]: " load_count
        export TASK_LOAD_COUNT="$load_count"
        
        echo "运行自定义测试..."
        NUM_INSTANCES=$instances ./run_systematic_test_final.sh --model $model --phase 5.3
        ;;
esac

echo ""
echo "============================================================"
echo "测试完成！"
echo "============================================================"
echo ""
echo "📈 查看结果："
echo "  python view_test_progress.py"
echo ""
echo "📊 查看内存使用："
echo "  ps aux | grep python | grep smart_batch"
echo ""