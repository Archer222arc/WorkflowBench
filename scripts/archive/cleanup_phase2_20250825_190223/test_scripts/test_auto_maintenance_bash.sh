#!/bin/bash

# ============================================
# 自动失败维护系统 - Bash接口测试脚本
# 演示如何在bash脚本中使用自动维护功能
# ============================================

# 加载自动失败维护函数库
if [ -f "auto_failure_maintenance_lib.sh" ]; then
    source auto_failure_maintenance_lib.sh
    echo -e "${GREEN}✅ 已加载自动失败维护函数库${NC}"
else
    echo -e "${RED}❌ 未找到自动失败维护函数库${NC}"
    exit 1
fi

# 颜色定义（如果函数库没有定义的话）
if [ -z "$RED" ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    CYAN='\033[0;36m'
    PURPLE='\033[0;35m'
    NC='\033[0m'
fi

echo "============================================"
echo "🔧 自动失败维护系统 - Bash接口测试"
echo "============================================"
echo ""

# 解析命令行参数
DEMO_MODE="interactive"
TEST_MODELS=""
SPECIFIC_FUNCTION=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --demo)
            DEMO_MODE="demo"
            shift
            ;;
        --models)
            TEST_MODELS="$2"
            shift 2
            ;;
        --function)
            SPECIFIC_FUNCTION="$2"
            shift 2
            ;;
        --help|-h)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --demo              演示模式（非交互）"
            echo "  --models MODEL1,MODEL2  指定测试模型"
            echo "  --function FUNC     测试特定函数"
            echo "  --help, -h         显示帮助信息"
            echo ""
            echo "可用函数:"
            echo "  check_status       检查系统状态"
            echo "  analyze_completion 分析完成情况"
            echo "  generate_script    生成重测脚本"
            echo "  run_maintenance    执行自动维护"
            echo "  wizard             维护向导"
            echo ""
            exit 0
            ;;
        *)
            echo "未知参数: $1"
            echo "使用 --help 查看帮助"
            exit 1
            ;;
    esac
done

# 函数测试
test_function() {
    local func_name="$1"
    local description="$2"
    
    echo -e "${BLUE}🧪 测试函数: $func_name${NC}"
    echo -e "${CYAN}描述: $description${NC}"
    echo ""
    
    case $func_name in
        "check_status")
            check_auto_maintenance_status
            ;;
        "analyze_completion")
            get_models_completion_summary "$TEST_MODELS"
            ;;
        "check_incomplete")
            check_incomplete_tests "$TEST_MODELS"
            ;;
        "generate_script")
            generate_retest_script "$TEST_MODELS" "test_retest_script.sh"
            ;;
        "run_maintenance")
            run_auto_maintenance "$TEST_MODELS" "true"  # dry run
            ;;
        "incremental_retest")
            run_incremental_retest "$TEST_MODELS" "0.8" "true"  # dry run
            ;;
        "show_progress")
            show_progress_summary
            ;;
        "wizard")
            auto_maintenance_wizard "$TEST_MODELS" "false"  # 非交互模式
            ;;
        "smart_entry")
            smart_maintenance_entry "check" "$TEST_MODELS" "false"
            ;;
        *)
            echo -e "${RED}❌ 未知函数: $func_name${NC}"
            return 1
            ;;
    esac
    
    echo ""
    echo -e "${GREEN}✅ 函数测试完成${NC}"
    echo "----------------------------------------"
    echo ""
}

# 演示模式
if [ "$DEMO_MODE" = "demo" ]; then
    echo -e "${CYAN}🎭 演示模式启动${NC}"
    echo ""
    
    if [ -n "$SPECIFIC_FUNCTION" ]; then
        test_function "$SPECIFIC_FUNCTION" "特定函数测试"
    else
        # 测试所有主要函数
        test_function "check_status" "检查系统状态和配置"
        test_function "analyze_completion" "分析模型完成情况"
        test_function "check_incomplete" "检查未完成的测试"
        test_function "show_progress" "显示进度概要"
        test_function "generate_script" "生成重测脚本"
        test_function "run_maintenance" "执行自动维护（仅分析）"
        test_function "smart_entry" "智能维护入口"
    fi
    
    echo -e "${PURPLE}🎉 演示完成${NC}"
    exit 0
fi

# 交互模式
echo -e "${CYAN}🎮 交互测试模式${NC}"
echo ""

while true; do
    echo -e "${YELLOW}========================================${NC}"
    echo -e "${YELLOW}🔧 自动失败维护系统 - 功能测试${NC}"
    echo -e "${YELLOW}========================================${NC}"
    echo "1.  🔍 检查系统状态"
    echo "2.  📊 分析模型完成情况"
    echo "3.  📋 检查未完成测试"
    echo "4.  📈 显示进度概要"
    echo "5.  📝 生成重测脚本"
    echo "6.  🔧 执行自动维护（仅分析）"
    echo "7.  🔄 执行增量重测（仅分析）"
    echo "8.  🧙 自动维护向导"
    echo "9.  🎯 智能维护入口"
    echo "10. 🧪 测试失败记录"
    echo "11. 🔬 测试并行执行"
    echo "12. ⚙️  配置测试"
    echo "0.  ❌ 退出"
    echo ""
    echo -e "${YELLOW}当前测试模型: ${TEST_MODELS:-所有模型}${NC}"
    echo -n "请选择功能 [0-12]: "
    
    read -r choice
    echo ""
    
    case $choice in
        1)
            test_function "check_status" "检查系统状态和配置"
            ;;
        2)
            test_function "analyze_completion" "分析模型完成情况"
            ;;
        3)
            test_function "check_incomplete" "检查未完成的测试"
            ;;
        4)
            test_function "show_progress" "显示进度概要"
            ;;
        5)
            test_function "generate_script" "生成重测脚本"
            ;;
        6)
            test_function "run_maintenance" "执行自动维护（仅分析）"
            ;;
        7)
            test_function "incremental_retest" "执行增量重测（仅分析）"
            ;;
        8)
            test_function "wizard" "自动维护向导"
            ;;
        9)
            test_function "smart_entry" "智能维护入口"
            ;;
        10)
            echo -e "${BLUE}🧪 测试失败记录功能${NC}"
            echo ""
            # 模拟记录失败
            if command -v record_test_failure >/dev/null 2>&1; then
                record_test_failure "test-model" "test-group" "bash-test" "Simulated failure for testing"
                echo -e "${GREEN}✅ 已记录模拟失败${NC}"
            else
                echo -e "${YELLOW}⚠️  失败记录函数不可用${NC}"
            fi
            echo ""
            ;;
        11)
            echo -e "${BLUE}🔬 测试并行执行功能${NC}"
            echo ""
            if [ -n "$TEST_MODELS" ]; then
                parallel_model_testing "$TEST_MODELS" "echo 'Testing {MODEL}'" 2
            else
                echo -e "${YELLOW}⚠️  请先设置测试模型${NC}"
                echo -n "输入模型列表（逗号分隔）: "
                read -r models
                if [ -n "$models" ]; then
                    parallel_model_testing "$models" "echo 'Testing {MODEL}'" 2
                fi
            fi
            echo ""
            ;;
        12)
            echo -e "${BLUE}⚙️  配置测试${NC}"
            echo ""
            if command -v load_maintenance_config >/dev/null 2>&1; then
                load_maintenance_config
            else
                echo -e "${YELLOW}⚠️  配置加载函数不可用${NC}"
            fi
            echo ""
            ;;
        0)
            echo -e "${GREEN}👋 感谢使用自动失败维护系统！${NC}"
            break
            ;;
        *)
            echo -e "${RED}❌ 无效选择，请重新输入${NC}"
            sleep 1
            ;;
    esac
    
    if [ "$choice" != "0" ]; then
        echo -e "${YELLOW}按Enter键继续...${NC}"
        read -r
        clear
    fi
done

echo ""
echo "============================================"
echo "🎉 测试完成"
echo "============================================"