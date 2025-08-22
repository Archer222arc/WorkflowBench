#!/bin/bash

# 重新运行失败的测试组
# 生成时间: 2025-08-14

echo "=========================================="
echo "重新测试失败的测试组"
echo "=========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 运行测试的函数
run_test() {
    local model="$1"
    local prompt_types="$2"
    local test_name="$3"
    
    echo -e "${CYAN}▶ 开始重新测试: $model${NC}"
    echo -e "${BLUE}  测试组: $test_name${NC}"
    echo -e "${BLUE}  Prompt类型: $prompt_types${NC}"
    
    python ultra_parallel_runner.py \
        --model "$model" \
        --prompt-types "$prompt_types" \
        --difficulty easy \
        --task-types all \
        --num-instances 20
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $model - $test_name 重新测试成功${NC}"
    else
        echo -e "${RED}✗ $model - $test_name 重新测试仍然失败${NC}"
        return 1
    fi
}

echo "需要重新测试的模型和测试组："
echo "1. qwen2.5-3b-instruct (全部3组)"
echo "2. DeepSeek-R1-0528 (全部3组)"  
echo "3. Llama-3.3-70B-Instruct (全部3组)"
echo "4. qwen2.5-14b-instruct (剩余2组)"
echo ""
echo "按Enter开始，或Ctrl+C退出..."
read

echo ""
echo "=========================================="
echo "开始重新测试失败的组..."
echo "=========================================="

# 失败计数
failed_count=0

echo ""
echo "=== 重新测试 qwen2.5-3b-instruct ==="

# qwen2.5-3b-instruct - 结构缺陷组
run_test "qwen2.5-3b-instruct" "flawed_sequence_disorder,flawed_tool_misuse,flawed_parameter_error" "结构缺陷组"
if [ $? -ne 0 ]; then ((failed_count++)); fi

# qwen2.5-3b-instruct - 操作缺陷组  
run_test "qwen2.5-3b-instruct" "flawed_missing_step,flawed_redundant_operations" "操作缺陷组"
if [ $? -ne 0 ]; then ((failed_count++)); fi

# qwen2.5-3b-instruct - 逻辑缺陷组
run_test "qwen2.5-3b-instruct" "flawed_logical_inconsistency,flawed_semantic_drift" "逻辑缺陷组"
if [ $? -ne 0 ]; then ((failed_count++)); fi

echo ""
echo "=== 重新测试 DeepSeek-R1-0528 ==="

# DeepSeek-R1-0528 - 结构缺陷组
run_test "DeepSeek-R1-0528" "flawed_sequence_disorder,flawed_tool_misuse,flawed_parameter_error" "结构缺陷组"
if [ $? -ne 0 ]; then ((failed_count++)); fi

# DeepSeek-R1-0528 - 操作缺陷组
run_test "DeepSeek-R1-0528" "flawed_missing_step,flawed_redundant_operations" "操作缺陷组"
if [ $? -ne 0 ]; then ((failed_count++)); fi

# DeepSeek-R1-0528 - 逻辑缺陷组
run_test "DeepSeek-R1-0528" "flawed_logical_inconsistency,flawed_semantic_drift" "逻辑缺陷组"
if [ $? -ne 0 ]; then ((failed_count++)); fi

echo ""
echo "=== 重新测试 Llama-3.3-70B-Instruct ==="

# Llama-3.3-70B-Instruct - 结构缺陷组
run_test "Llama-3.3-70B-Instruct" "flawed_sequence_disorder,flawed_tool_misuse,flawed_parameter_error" "结构缺陷组"
if [ $? -ne 0 ]; then ((failed_count++)); fi

# Llama-3.3-70B-Instruct - 操作缺陷组
run_test "Llama-3.3-70B-Instruct" "flawed_missing_step,flawed_redundant_operations" "操作缺陷组"
if [ $? -ne 0 ]; then ((failed_count++)); fi

# Llama-3.3-70B-Instruct - 逻辑缺陷组
run_test "Llama-3.3-70B-Instruct" "flawed_logical_inconsistency,flawed_semantic_drift" "逻辑缺陷组"
if [ $? -ne 0 ]; then ((failed_count++)); fi

echo ""
echo "=== 重新测试 qwen2.5-14b-instruct (剩余组) ==="

# qwen2.5-14b-instruct - 操作缺陷组 (之前失败)
run_test "qwen2.5-14b-instruct" "flawed_missing_step,flawed_redundant_operations" "操作缺陷组"
if [ $? -ne 0 ]; then ((failed_count++)); fi

# qwen2.5-14b-instruct - 逻辑缺陷组
run_test "qwen2.5-14b-instruct" "flawed_logical_inconsistency,flawed_semantic_drift" "逻辑缺陷组"
if [ $? -ne 0 ]; then ((failed_count++)); fi

echo ""
echo "=========================================="
echo "重新测试完成！"
echo "=========================================="

if [ $failed_count -eq 0 ]; then
    echo -e "${GREEN}🎉 所有失败的测试都已成功重新运行！${NC}"
else
    echo -e "${RED}⚠️  仍有 $failed_count 个测试失败${NC}"
    echo "建议检查日志文件了解失败原因"
fi

echo ""
echo "可以运行以下命令继续原始测试流程："
echo "./run_systematic_test_final.sh"