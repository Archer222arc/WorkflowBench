#!/bin/bash

# 系统化测试脚本 - 开源模型
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
NC='\033[0m' # No Color

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
    
    echo -e "${GREEN}开始测试: $model${NC}"
    echo "配置: $description"
    echo "Prompt类型: $prompt_types"
    echo "难度: $difficulty"
    echo "任务类型: $task_types"
    echo "实例数: $num_instances"
    echo ""
    
    python batch_test_runner.py \
        --model "$model" \
        --prompt-types "$prompt_types" \
        --difficulty "$difficulty" \
        --task-types "$task_types" \
        --num-instances "$num_instances" \
        --max-workers 5 \
        --save-logs
        
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $model 测试完成${NC}"
    else
        echo -e "${RED}✗ $model 测试失败${NC}"
    fi
    echo ""
}

# ========================================
# 5.1 第一步：基准测试
# ========================================
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

confirm_continue "即将开始基准测试..."

for model in "${OPENSOURCE_MODELS[@]}"; do
    run_test "$model" "optimal" "easy" "all" "20" "基准测试(optimal+easy)"
done

echo -e "${GREEN}5.1 基准测试完成！${NC}"
confirm_continue "基准测试已完成，准备进行5.2 Qwen规模效应测试..."

# ========================================
# 5.2 第二步：Qwen系列规模效应测试
# ========================================
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

confirm_continue "即将开始Qwen规模效应测试..."

# 测试very_easy难度
echo -e "${YELLOW}测试 very_easy 难度...${NC}"
for model in "${QWEN_FULL_SERIES[@]}"; do
    run_test "$model" "optimal" "very_easy" "all" "20" "Qwen规模效应(very_easy)"
done

# 测试medium难度
echo -e "${YELLOW}测试 medium 难度...${NC}"
for model in "${QWEN_FULL_SERIES[@]}"; do
    run_test "$model" "optimal" "medium" "all" "20" "Qwen规模效应(medium)"
done

echo -e "${GREEN}5.2 Qwen规模效应测试完成！${NC}"
confirm_continue "Qwen规模效应测试已完成，准备进行5.3 缺陷工作流测试..."

# ========================================
# 5.3 第三步：缺陷工作流适应性测试
# ========================================
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

confirm_continue "即将开始缺陷工作流测试（7种缺陷×8个模型）..."

for model in "${OPENSOURCE_MODELS[@]}"; do
    echo -e "${YELLOW}测试模型: $model${NC}"
    for flaw in "${FLAW_TYPES[@]}"; do
        run_test "$model" "$flaw" "easy" "all" "20" "缺陷工作流($flaw)"
    done
done

echo -e "${GREEN}5.3 缺陷工作流测试完成！${NC}"
confirm_continue "缺陷工作流测试已完成，准备进行5.4 工具可靠性测试..."

# ========================================
# 5.4 第四步：工具可靠性敏感性测试
# ========================================
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

confirm_continue "即将开始工具可靠性测试（3个成功率×8个模型）..."

for model in "${OPENSOURCE_MODELS[@]}"; do
    echo -e "${YELLOW}测试模型: $model${NC}"
    for reliability in "${TOOL_RELIABILITIES[@]}"; do
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
        else
            echo -e "${RED}✗ $model (reliability=$reliability) 测试失败${NC}"
        fi
    done
done

echo -e "${GREEN}5.4 工具可靠性测试完成！${NC}"
confirm_continue "工具可靠性测试已完成，准备进行5.5 提示类型敏感性测试..."

# ========================================
# 5.5 第五步：提示类型敏感性测试
# ========================================
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

confirm_continue "即将开始提示类型敏感性测试（2种提示×8个模型）..."

for model in "${OPENSOURCE_MODELS[@]}"; do
    echo -e "${YELLOW}测试模型: $model${NC}"
    for prompt in "${PROMPT_TYPES[@]}"; do
        run_test "$model" "$prompt" "easy" "all" "20" "提示类型($prompt)"
    done
done

echo -e "${GREEN}5.5 提示类型敏感性测试完成！${NC}"

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
echo "请运行以下命令生成报告："
echo "python generate_report.py --input-dir pilot_bench_cumulative_results"