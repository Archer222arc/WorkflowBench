#!/bin/bash

# 系统化测试脚本 - 开源模型（支持断点续测）
# 根据综合实验评估计划.md执行

echo "=========================================="
echo "PILOT-Bench 系统化测试 - 开源模型"
echo "=========================================="
echo ""

# 定义开源模型列表（全部8个开源模型）
OPENSOURCE_MODELS=(
    "deepseek-v3-671b"
    "qwen2.5-72b-instruct"
    "qwen2.5-32b-instruct"
    "qwen2.5-14b-instruct"
    "qwen2.5-7b-instruct"
    "qwen2.5-3b-instruct"
    "llama-3.3-70b-instruct"
    "llama-4-scout-17b"
)

# Qwen全系列（用于5.2规模效应测试）
QWEN_FULL_SERIES=(
    "qwen2.5-3b-instruct"
    "qwen2.5-7b-instruct"
    "qwen2.5-14b-instruct"
    "qwen2.5-32b-instruct"
    "qwen2.5-72b-instruct"
)

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 进度文件
PROGRESS_FILE="test_progress.txt"
COMPLETED_FILE="completed_tests.txt"

# 初始化进度文件
if [ ! -f "$PROGRESS_FILE" ]; then
    echo "STEP=1" > "$PROGRESS_FILE"
    echo "MODEL_INDEX=0" >> "$PROGRESS_FILE"
    echo "SUBSTEP=" >> "$PROGRESS_FILE"
fi

if [ ! -f "$COMPLETED_FILE" ]; then
    touch "$COMPLETED_FILE"
fi

# 读取当前进度
source "$PROGRESS_FILE"

# 检查测试是否已完成
is_test_completed() {
    local test_id=$1
    grep -q "^$test_id$" "$COMPLETED_FILE"
    return $?
}

# 标记测试完成
mark_test_completed() {
    local test_id=$1
    echo "$test_id" >> "$COMPLETED_FILE"
}

# 更新进度
update_progress() {
    local step=$1
    local model_idx=$2
    local substep=$3
    
    echo "STEP=$step" > "$PROGRESS_FILE"
    echo "MODEL_INDEX=$model_idx" >> "$PROGRESS_FILE"
    echo "SUBSTEP=$substep" >> "$PROGRESS_FILE"
}

# 用户确认函数
confirm_continue() {
    echo -e "${YELLOW}$1${NC}"
    echo "按Enter继续，按Ctrl+C退出..."
    read -r
}

# 测试函数
run_test() {
    local model=$1
    local prompt_types=$2
    local difficulty=$3
    local task_types=$4
    local num_instances=$5
    local description=$6
    local test_id="${model}_${prompt_types}_${difficulty}"
    
    # 检查是否已完成
    if is_test_completed "$test_id"; then
        echo -e "${BLUE}⊙ $model - $description 已完成，跳过${NC}"
        return 0
    fi
    
    echo -e "${GREEN}开始测试: $model${NC}"
    echo "配置: $description"
    echo "Prompt类型: $prompt_types"
    echo "难度: $difficulty"
    echo "任务类型: $task_types"
    echo "实例数: $num_instances"
    echo ""
    
    # 使用智能批测试运行器（自动处理部分完成的情况）
    python smart_batch_runner.py \
        --model "$model" \
        --prompt-types "$prompt_types" \
        --difficulty "$difficulty" \
        --task-types "$task_types" \
        --num-instances "$num_instances" \
        --max-workers 5 \
        --save-logs
        
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $model 测试完成${NC}"
        mark_test_completed "$test_id"
    else
        echo -e "${RED}✗ $model 测试失败${NC}"
        echo -e "${YELLOW}提示：可以重新运行脚本从此处继续${NC}"
        exit 1
    fi
    echo ""
}

# 显示恢复信息
if [ "$STEP" -gt 1 ] || [ "$MODEL_INDEX" -gt 0 ]; then
    echo -e "${BLUE}检测到之前的进度：${NC}"
    echo "  步骤: $STEP"
    echo "  模型索引: $MODEL_INDEX"
    echo "  子步骤: $SUBSTEP"
    echo ""
    confirm_continue "从上次中断处继续..."
fi

# ========================================
# 5.1 第一步：基准测试
# ========================================
if [ "$STEP" -eq 1 ]; then
    echo "================================================"
    echo "5.1 第一步：基准测试"
    echo "================================================"
    echo "测试配置："
    echo "- Prompt类型: optimal"
    echo "- 难度: easy"
    echo "- 任务类型: 全部5种"
    echo "- 每种任务类型: 20个实例"
    echo "- 模型数量: 8个开源模型"
    echo ""
    
    if [ "$MODEL_INDEX" -eq 0 ]; then
        confirm_continue "即将开始基准测试..."
    fi
    
    for i in "${!OPENSOURCE_MODELS[@]}"; do
        if [ $i -ge $MODEL_INDEX ]; then
            model="${OPENSOURCE_MODELS[$i]}"
            update_progress 1 $i ""
            run_test "$model" "optimal" "easy" "all" "20" "基准测试(optimal+easy)"
        fi
    done
    
    echo -e "${GREEN}5.1 基准测试完成！${NC}"
    update_progress 2 0 ""
    confirm_continue "基准测试已完成，准备进行5.2 Qwen规模效应测试..."
fi

# ========================================
# 5.2 第二步：Qwen系列规模效应测试
# ========================================
if [ "$STEP" -eq 2 ]; then
    echo "================================================"
    echo "5.2 第二步：Qwen系列规模效应测试"
    echo "================================================"
    echo "测试配置："
    echo "- Prompt类型: optimal"
    echo "- 难度: very_easy 和 medium（分别测试）"
    echo "- 任务类型: 全部5种"
    echo "- 每种任务类型: 20个实例"
    echo "- 模型数量: 5个Qwen规模"
    echo ""
    
    if [ "$MODEL_INDEX" -eq 0 ] && [ -z "$SUBSTEP" ]; then
        confirm_continue "即将开始Qwen规模效应测试..."
    fi
    
    # 测试very_easy难度
    if [ -z "$SUBSTEP" ] || [ "$SUBSTEP" == "very_easy" ]; then
        echo -e "${YELLOW}测试 very_easy 难度...${NC}"
        for i in "${!QWEN_FULL_SERIES[@]}"; do
            if [ "$SUBSTEP" == "very_easy" ] && [ $i -lt $MODEL_INDEX ]; then
                continue
            fi
            model="${QWEN_FULL_SERIES[$i]}"
            update_progress 2 $i "very_easy"
            run_test "$model" "optimal" "very_easy" "all" "20" "Qwen规模效应(very_easy)"
        done
        SUBSTEP="medium"
        MODEL_INDEX=0
    fi
    
    # 测试medium难度
    if [ "$SUBSTEP" == "medium" ]; then
        echo -e "${YELLOW}测试 medium 难度...${NC}"
        for i in "${!QWEN_FULL_SERIES[@]}"; do
            if [ $i -ge $MODEL_INDEX ]; then
                model="${QWEN_FULL_SERIES[$i]}"
                update_progress 2 $i "medium"
                run_test "$model" "optimal" "medium" "all" "20" "Qwen规模效应(medium)"
            fi
        done
    fi
    
    echo -e "${GREEN}5.2 Qwen规模效应测试完成！${NC}"
    update_progress 3 0 ""
    confirm_continue "Qwen规模效应测试已完成，准备进行5.3 缺陷工作流测试..."
fi

# ========================================
# 5.3 第三步：缺陷工作流适应性测试
# ========================================
if [ "$STEP" -eq 3 ]; then
    echo "================================================"
    echo "5.3 第三步：缺陷工作流适应性测试"
    echo "================================================"
    echo "测试配置："
    echo "- Prompt类型: 7种缺陷类型"
    echo "- 难度: easy"
    echo "- 任务类型: 全部5种"
    echo "- 每种任务类型: 20个实例"
    echo "- 模型数量: 8个开源模型"
    echo ""
    
    # 7种缺陷类型
    FLAW_TYPES=(
        "flawed_sequence_disorder"
        "flawed_tool_misuse"
        "flawed_parameter_error"
        "flawed_missing_step"
        "flawed_redundant_operations"
        "flawed_logical_inconsistency"
        "flawed_semantic_drift"
    )
    
    if [ "$MODEL_INDEX" -eq 0 ] && [ -z "$SUBSTEP" ]; then
        confirm_continue "即将开始缺陷工作流测试（7种缺陷×8个模型）..."
    fi
    
    for i in "${!OPENSOURCE_MODELS[@]}"; do
        if [ $i -ge $MODEL_INDEX ]; then
            model="${OPENSOURCE_MODELS[$i]}"
            echo -e "${YELLOW}测试模型: $model${NC}"
            
            # 确定从哪个缺陷类型开始
            start_flaw=0
            if [ $i -eq $MODEL_INDEX ] && [ -n "$SUBSTEP" ]; then
                # 找到子步骤对应的索引
                for j in "${!FLAW_TYPES[@]}"; do
                    if [ "${FLAW_TYPES[$j]}" == "$SUBSTEP" ]; then
                        start_flaw=$j
                        break
                    fi
                done
            fi
            
            for j in "${!FLAW_TYPES[@]}"; do
                if [ $j -ge $start_flaw ]; then
                    flaw="${FLAW_TYPES[$j]}"
                    update_progress 3 $i "$flaw"
                    run_test "$model" "$flaw" "easy" "all" "20" "缺陷工作流($flaw)"
                fi
            done
            start_flaw=0  # 下一个模型从第一个缺陷开始
        fi
    done
    
    echo -e "${GREEN}5.3 缺陷工作流测试完成！${NC}"
    update_progress 4 0 ""
    confirm_continue "缺陷工作流测试已完成，准备进行5.4 工具可靠性测试..."
fi

# ========================================
# 5.4 第四步：工具可靠性敏感性测试
# ========================================
if [ "$STEP" -eq 4 ]; then
    echo "================================================"
    echo "5.4 第四步：工具可靠性敏感性测试"
    echo "================================================"
    echo "测试配置："
    echo "- Prompt类型: optimal"
    echo "- 难度: easy"
    echo "- 工具成功率: 90%, 70%, 60%（80%使用5.1的结果）"
    echo "- 任务类型: 全部5种"
    echo "- 每种任务类型: 20个实例"
    echo "- 模型数量: 8个开源模型"
    echo ""
    
    # 工具成功率设置
    TOOL_RELIABILITIES=(
        "0.9"
        "0.7"
        "0.6"
    )
    
    if [ "$MODEL_INDEX" -eq 0 ] && [ -z "$SUBSTEP" ]; then
        confirm_continue "即将开始工具可靠性测试（3个成功率×8个模型）..."
    fi
    
    for i in "${!OPENSOURCE_MODELS[@]}"; do
        if [ $i -ge $MODEL_INDEX ]; then
            model="${OPENSOURCE_MODELS[$i]}"
            echo -e "${YELLOW}测试模型: $model${NC}"
            
            # 确定从哪个可靠性开始
            start_rel=0
            if [ $i -eq $MODEL_INDEX ] && [ -n "$SUBSTEP" ]; then
                for j in "${!TOOL_RELIABILITIES[@]}"; do
                    if [ "${TOOL_RELIABILITIES[$j]}" == "$SUBSTEP" ]; then
                        start_rel=$j
                        break
                    fi
                done
            fi
            
            for j in "${!TOOL_RELIABILITIES[@]}"; do
                if [ $j -ge $start_rel ]; then
                    reliability="${TOOL_RELIABILITIES[$j]}"
                    update_progress 4 $i "$reliability"
                    
                    test_id="${model}_optimal_easy_tool${reliability}"
                    if is_test_completed "$test_id"; then
                        echo -e "${BLUE}⊙ $model (reliability=$reliability) 已完成，跳过${NC}"
                        continue
                    fi
                    
                    echo -e "${YELLOW}工具成功率: ${reliability}${NC}"
                    python batch_test_runner.py \
                        --model "$model" \
                        --prompt-types "optimal" \
                        --difficulty "easy" \
                        --task-types "all" \
                        --num-instances "20" \
                        --tool-success-rate "$reliability" \
                        --max-workers 5 \
                        --save-logs
                        
                    if [ $? -eq 0 ]; then
                        echo -e "${GREEN}✓ $model (reliability=$reliability) 测试完成${NC}"
                        mark_test_completed "$test_id"
                    else
                        echo -e "${RED}✗ $model (reliability=$reliability) 测试失败${NC}"
                        exit 1
                    fi
                fi
            done
            start_rel=0
        fi
    done
    
    echo -e "${GREEN}5.4 工具可靠性测试完成！${NC}"
    update_progress 5 0 ""
    confirm_continue "工具可靠性测试已完成，准备进行5.5 提示类型敏感性测试..."
fi

# ========================================
# 5.5 第五步：提示类型敏感性测试
# ========================================
if [ "$STEP" -eq 5 ]; then
    echo "================================================"
    echo "5.5 第五步：提示类型敏感性测试"
    echo "================================================"
    echo "测试配置："
    echo "- Prompt类型: baseline, cot（optimal使用5.1的结果）"
    echo "- 难度: easy"
    echo "- 任务类型: 全部5种"
    echo "- 每种任务类型: 20个实例"
    echo "- 模型数量: 8个开源模型"
    echo ""
    
    # 提示类型（optimal已在5.1测试）
    PROMPT_TYPES=(
        "baseline"
        "cot"
    )
    
    if [ "$MODEL_INDEX" -eq 0 ] && [ -z "$SUBSTEP" ]; then
        confirm_continue "即将开始提示类型敏感性测试（2种提示×8个模型）..."
    fi
    
    for i in "${!OPENSOURCE_MODELS[@]}"; do
        if [ $i -ge $MODEL_INDEX ]; then
            model="${OPENSOURCE_MODELS[$i]}"
            echo -e "${YELLOW}测试模型: $model${NC}"
            
            # 确定从哪个提示类型开始
            start_prompt=0
            if [ $i -eq $MODEL_INDEX ] && [ -n "$SUBSTEP" ]; then
                for j in "${!PROMPT_TYPES[@]}"; do
                    if [ "${PROMPT_TYPES[$j]}" == "$SUBSTEP" ]; then
                        start_prompt=$j
                        break
                    fi
                done
            fi
            
            for j in "${!PROMPT_TYPES[@]}"; do
                if [ $j -ge $start_prompt ]; then
                    prompt="${PROMPT_TYPES[$j]}"
                    update_progress 5 $i "$prompt"
                    run_test "$model" "$prompt" "easy" "all" "20" "提示类型($prompt)"
                fi
            done
            start_prompt=0
        fi
    done
    
    echo -e "${GREEN}5.5 提示类型敏感性测试完成！${NC}"
    update_progress 6 0 ""
fi

# ========================================
# 测试完成总结
# ========================================
echo ""
echo "=========================================="
echo -e "${GREEN}所有测试已完成！${NC}"
echo "=========================================="
echo "测试总结："
echo "- 5.1 基准测试: 8个模型 × 100个测试 = 800个测试"
echo "- 5.2 Qwen规模效应: 5个模型 × 2个难度 × 100个测试 = 1000个测试"
echo "- 5.3 缺陷工作流: 8个模型 × 7种缺陷 × 100个测试 = 5600个测试"
echo "- 5.4 工具可靠性: 8个模型 × 3个成功率 × 100个测试 = 2400个测试"
echo "- 5.5 提示类型: 8个模型 × 2种提示 × 100个测试 = 1600个测试"
echo ""
echo "总计: 11400个测试"
echo ""
echo "清理进度文件..."
rm -f "$PROGRESS_FILE"
echo ""
echo "请运行以下命令生成报告："
echo "python generate_report.py --input-dir pilot_bench_cumulative_results"