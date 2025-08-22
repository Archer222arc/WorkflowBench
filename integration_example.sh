#!/bin/bash

# ============================================
# 集成示例：如何在现有脚本中添加自动失败维护
# ============================================

# 1. 在脚本开头加载维护函数库
if [ -f "auto_failure_maintenance_lib.sh" ]; then
    source auto_failure_maintenance_lib.sh
    echo -e "${GREEN}✅ 已加载自动维护功能${NC}"
else
    echo -e "${YELLOW}⚠️  未找到维护函数库，使用基本功能${NC}"
fi

# 2. 解析命令行参数，添加维护相关选项
AUTO_MAINTENANCE=false
WITH_RETRY=false
MODELS_TO_TEST=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --auto-maintain)
            AUTO_MAINTENANCE=true
            shift
            ;;
        --with-retry)
            WITH_RETRY=true
            shift
            ;;
        --models)
            MODELS_TO_TEST="$2"
            shift 2
            ;;
        --help|-h)
            echo "集成示例脚本"
            echo ""
            echo "选项:"
            echo "  --auto-maintain   启用自动维护模式"
            echo "  --with-retry      启用自动重试"
            echo "  --models MODELS   指定测试模型"
            echo "  --help, -h       显示帮助"
            echo ""
            echo "示例:"
            echo "  $0 --auto-maintain"
            echo "  $0 --with-retry --models gpt-4o-mini,claude-3-sonnet"
            exit 0
            ;;
        *)
            echo "未知参数: $1"
            exit 1
            ;;
    esac
done

echo "============================================"
echo "🔧 集成示例：自动失败维护"
echo "============================================"

# 3. 如果是纯维护模式，直接执行维护
if [ "$AUTO_MAINTENANCE" = "true" ]; then
    echo -e "${CYAN}🔧 执行自动维护模式${NC}"
    
    # 使用维护向导
    if command -v auto_maintenance_wizard >/dev/null 2>&1; then
        auto_maintenance_wizard "$MODELS_TO_TEST" "true"
    else
        echo -e "${YELLOW}⚠️  维护函数不可用，使用Python版本${NC}"
        python3 smart_batch_runner.py --auto-maintain
    fi
    exit 0
fi

# 4. 在测试开始前检查系统状态
echo -e "${BLUE}📋 测试前检查${NC}"

# 检查维护系统状态
if command -v check_auto_maintenance_status >/dev/null 2>&1; then
    check_auto_maintenance_status
fi

# 分析完成情况
if command -v get_models_completion_summary >/dev/null 2>&1; then
    get_models_completion_summary "$MODELS_TO_TEST"
fi

# 5. 定义带自动重试的测试执行函数
run_test_with_maintenance() {
    local model="$1"
    local test_config="$2"
    local description="$3"
    
    echo -e "${BLUE}🚀 开始测试: $model - $description${NC}"
    
    # 构建测试命令
    local cmd="python smart_batch_runner.py --model $model --prompt-types baseline --num-instances 5 --no-save-logs"
    
    # 使用自动重试执行测试
    if [ "$WITH_RETRY" = "true" ] && command -v execute_test_with_auto_retry >/dev/null 2>&1; then
        if execute_test_with_auto_retry "$cmd" "$description" "$model" "$test_config" 2; then
            echo -e "${GREEN}✅ 测试成功: $model${NC}"
            return 0
        else
            echo -e "${RED}❌ 测试失败: $model${NC}"
            return 1
        fi
    else
        # 基本执行
        if eval "$cmd"; then
            echo -e "${GREEN}✅ 测试成功: $model${NC}"
            return 0
        else
            echo -e "${RED}❌ 测试失败: $model${NC}"
            return 1
        fi
    fi
}

# 6. 主测试循环
echo -e "${CYAN}📋 开始批量测试${NC}"

# 设置要测试的模型列表
if [ -n "$MODELS_TO_TEST" ]; then
    IFS=',' read -ra MODELS_ARRAY <<< "$MODELS_TO_TEST"
else
    MODELS_ARRAY=("gpt-4o-mini" "claude-3-sonnet")
fi

# 统计变量
total_tests=0
successful_tests=0
failed_tests=0

# 测试每个模型
for model in "${MODELS_ARRAY[@]}"; do
    ((total_tests++))
    
    echo ""
    echo -e "${YELLOW}📋 测试模型 $total_tests/${#MODELS_ARRAY[@]}: $model${NC}"
    
    if run_test_with_maintenance "$model" "baseline_test" "基准测试"; then
        ((successful_tests++))
    else
        ((failed_tests++))
    fi
done

# 7. 测试后分析和维护
echo ""
echo "============================================"
echo -e "${CYAN}📊 测试完成统计${NC}"
echo "============================================"
echo -e "总测试数: $total_tests"
echo -e "成功: ${successful_tests}"
echo -e "失败: ${failed_tests}"

if [ $failed_tests -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}⚠️  检测到失败测试${NC}"
    
    # 检查是否有未完成的测试
    if command -v check_incomplete_tests >/dev/null 2>&1; then
        if check_incomplete_tests "$MODELS_TO_TEST"; then
            echo -e "${CYAN}💡 建议操作:${NC}"
            echo "1. 运行自动维护: $0 --auto-maintain"
            echo "2. 生成重测脚本: python auto_failure_maintenance_system.py retest"
            echo "3. 执行增量重测: python smart_batch_runner.py --incremental-retest"
        fi
    fi
    
    # 询问是否立即执行维护
    echo ""
    echo -e "${YELLOW}是否立即执行自动维护？ (y/n): ${NC}"
    read -r maintain_choice
    
    if [ "$maintain_choice" = "y" ] || [ "$maintain_choice" = "Y" ]; then
        echo -e "${CYAN}🔧 执行自动维护...${NC}"
        
        if command -v run_auto_maintenance >/dev/null 2>&1; then
            run_auto_maintenance "$MODELS_TO_TEST" "false"
        else
            python3 smart_batch_runner.py --auto-maintain --models $MODELS_TO_TEST
        fi
    fi
else
    echo -e "${GREEN}🎉 所有测试都成功完成！${NC}"
fi

# 8. 生成最终报告
echo ""
echo "============================================"
echo -e "${PURPLE}📋 最终报告${NC}"
echo "============================================"

# 显示进度概要
if command -v show_progress_summary >/dev/null 2>&1; then
    show_progress_summary
fi

# 显示维护建议
if [ $failed_tests -gt 0 ] && command -v smart_maintenance_entry >/dev/null 2>&1; then
    echo ""
    echo -e "${CYAN}🔧 维护建议:${NC}"
    smart_maintenance_entry "check" "$MODELS_TO_TEST" "false"
fi

echo ""
echo -e "${GREEN}✅ 集成示例完成${NC}"
echo "============================================"