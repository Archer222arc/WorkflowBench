#!/bin/bash

# ============================================
# 自动失败维护函数库
# 提供bash脚本中的失败检测、记录和重测功能
# ============================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# 图标定义
ICON_SUCCESS="✅"
ICON_FAILURE="❌"
ICON_WARNING="⚠️"
ICON_INFO="ℹ️"
ICON_RETRY="🔄"
ICON_MAINTENANCE="🔧"
ICON_PROGRESS="📊"
ICON_CONFIG="⚙️"

# ==============================================
# 核心功能函数
# ==============================================

# 检查系统状态
check_auto_maintenance_status() {
    echo -e "${CYAN}${ICON_MAINTENANCE} 检查自动维护系统状态...${NC}"
    
    if python3 auto_failure_maintenance_system.py status >/dev/null 2>&1; then
        echo -e "${GREEN}${ICON_SUCCESS} 自动维护系统正常${NC}"
        return 0
    else
        echo -e "${RED}${ICON_FAILURE} 自动维护系统异常${NC}"
        return 1
    fi
}

# 获取模型完成情况概要
get_models_completion_summary() {
    local models="$1"
    
    echo -e "${BLUE}${ICON_PROGRESS} 分析模型完成情况...${NC}"
    
    if [ -n "$models" ]; then
        python3 -c "
import sys
sys.path.insert(0, '.')
from auto_failure_maintenance_system import AutoFailureMaintenanceSystem

system = AutoFailureMaintenanceSystem(enable_auto_retry=False)
models_list = '$models'.split(',') if '$models' else None
analysis = system.analyze_test_completion(models_list)

print(f'分析了 {len(analysis[\"models_analyzed\"])} 个模型')
print(f'发现失败模式: {len(analysis[\"failure_patterns\"])} 个')
print(f'重试建议: {len(analysis[\"retry_recommendations\"])} 个')

for model in analysis['models_analyzed']:
    summary = analysis['completion_summary'][model]
    if summary['status'] == 'analyzed':
        completion_rate = summary['completion_rate']
        avg_exec_time = summary.get('avg_execution_time', 0)
        complete_failure = summary.get('needs_retry_complete_failure', False)
        high_exec_time = summary.get('needs_retry_high_execution_time', False)
        
        status_icon = '⚠️ ' if (complete_failure or high_exec_time) else '✅'
        issues = []
        if complete_failure:
            failure_configs = summary.get('complete_failure_configs', [])
            issues.append(f'完全失败配置:{len(failure_configs)}个')
        if high_exec_time:
            issues.append(f'执行时间过长:{avg_exec_time:.1f}s')
        
        issue_text = f' | {\" | \".join(issues)}' if issues else ''
        print(f'{status_icon} {model}: 完成率 {completion_rate:.1%}, 平均执行时间 {avg_exec_time:.1f}s{issue_text}')
" 2>/dev/null
    else
        echo -e "${YELLOW}${ICON_WARNING} 未指定模型，分析所有模型${NC}"
        python3 -c "
import sys
sys.path.insert(0, '.')
from auto_failure_maintenance_system import AutoFailureMaintenanceSystem

system = AutoFailureMaintenanceSystem(enable_auto_retry=False)
analysis = system.analyze_test_completion()

print(f'分析了 {len(analysis[\"models_analyzed\"])} 个模型')
print(f'发现失败模式: {len(analysis[\"failure_patterns\"])} 个')
print(f'重试建议: {len(analysis[\"retry_recommendations\"])} 个')

for model in analysis['models_analyzed']:
    summary = analysis['completion_summary'][model]
    if summary['status'] == 'analyzed':
        completion_rate = summary['completion_rate']
        avg_exec_time = summary.get('avg_execution_time', 0)
        complete_failure = summary.get('needs_retry_complete_failure', False)
        high_exec_time = summary.get('needs_retry_high_execution_time', False)
        
        status_icon = '⚠️ ' if (complete_failure or high_exec_time) else '✅'
        issues = []
        if complete_failure:
            failure_configs = summary.get('complete_failure_configs', [])
            issues.append(f'完全失败配置:{len(failure_configs)}个')
        if high_exec_time:
            issues.append(f'执行时间过长:{avg_exec_time:.1f}s')
        
        issue_text = f' | {\" | \".join(issues)}' if issues else ''
        print(f'{status_icon} {model}: 完成率 {completion_rate:.1%}, 平均执行时间 {avg_exec_time:.1f}s{issue_text}')
" 2>/dev/null
    fi
}

# 检查是否有未完成的测试
check_incomplete_tests() {
    local models="$1"
    
    echo -e "${BLUE}${ICON_INFO} 检查未完成的测试...${NC}"
    
    local incomplete_count
    incomplete_count=$(python3 -c "
import sys
sys.path.insert(0, '.')
from auto_failure_maintenance_system import AutoFailureMaintenanceSystem

system = AutoFailureMaintenanceSystem(enable_auto_retry=False)
models_list = '$models'.split(',') if '$models' else None
incomplete_tests = system.get_incomplete_tests(models_list)

total_missing = 0
for model, configs in incomplete_tests.items():
    missing = sum(config['missing_count'] for config in configs)
    total_missing += missing
    if missing > 0:
        print(f'{model}: {len(configs)} 个配置，缺少 {missing} 个测试')

print(f'总共缺少: {total_missing} 个测试')
" 2>/dev/null | tail -1 | grep -o '[0-9]*' | head -1)
    
    if [ -z "$incomplete_count" ] || [ "$incomplete_count" -eq 0 ]; then
        echo -e "${GREEN}${ICON_SUCCESS} 所有测试已完成${NC}"
        return 1
    else
        echo -e "${YELLOW}${ICON_WARNING} 发现 $incomplete_count 个未完成测试${NC}"
        return 0
    fi
}

# 生成重测脚本
generate_retest_script() {
    local models="$1"
    local script_name="${2:-auto_retest_bash_generated.sh}"
    
    echo -e "${CYAN}${ICON_MAINTENANCE} 生成重测脚本...${NC}"
    
    if [ -n "$models" ]; then
        python3 auto_failure_maintenance_system.py retest $models >/dev/null 2>&1
    else
        python3 auto_failure_maintenance_system.py retest >/dev/null 2>&1
    fi
    
    if [ -f "auto_retest_incomplete.sh" ]; then
        mv "auto_retest_incomplete.sh" "$script_name"
        chmod +x "$script_name"
        echo -e "${GREEN}${ICON_SUCCESS} 重测脚本已生成: $script_name${NC}"
        return 0
    else
        echo -e "${RED}${ICON_FAILURE} 重测脚本生成失败${NC}"
        return 1
    fi
}

# 执行自动维护
run_auto_maintenance() {
    local models="$1"
    local dry_run="${2:-false}"
    
    echo -e "${CYAN}${ICON_MAINTENANCE} 执行自动维护...${NC}"
    
    if [ "$dry_run" = "true" ]; then
        echo -e "${YELLOW}${ICON_INFO} 仅分析模式，不执行实际测试${NC}"
        python3 auto_failure_maintenance_system.py maintain
    else
        if [ -n "$models" ]; then
            python3 smart_batch_runner.py --auto-maintain --models $models
        else
            python3 smart_batch_runner.py --auto-maintain
        fi
    fi
}

# 执行增量重测
run_incremental_retest() {
    local models="$1"
    local threshold="${2:-0.8}"
    local dry_run="${3:-false}"
    
    echo -e "${CYAN}${ICON_RETRY} 执行增量重测 (阈值: ${threshold})...${NC}"
    
    if [ "$dry_run" = "true" ]; then
        echo -e "${YELLOW}${ICON_INFO} 仅分析模式${NC}"
        get_models_completion_summary "$models"
    else
        local cmd="python3 smart_batch_runner.py --incremental-retest --completion-threshold $threshold"
        if [ -n "$models" ]; then
            cmd="$cmd --models $models"
        fi
        eval "$cmd"
    fi
}

# ==============================================
# 测试执行包装函数
# ==============================================

# 带失败检测的测试执行
execute_test_with_failure_tracking() {
    local test_command="$1"
    local test_description="$2"
    local model="$3"
    local config="$4"
    
    echo -e "${BLUE}${ICON_INFO} 执行: $test_description${NC}"
    echo -e "${CYAN}命令: $test_command${NC}"
    
    local start_time=$(date +%s)
    local success=false
    
    if eval "$test_command"; then
        success=true
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        echo -e "${GREEN}${ICON_SUCCESS} 测试成功 (耗时: ${duration}s)${NC}"
        
        # 记录成功
        if [ -n "$model" ] && [ -n "$config" ]; then
            record_test_success "$model" "$config" "true"
        fi
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        echo -e "${RED}${ICON_FAILURE} 测试失败 (耗时: ${duration}s)${NC}"
        
        # 记录失败
        if [ -n "$model" ] && [ -n "$config" ]; then
            record_test_failure "$model" "$config" "$test_description" "Test execution failed"
        fi
    fi
    
    return $([ "$success" = true ] && echo 0 || echo 1)
}

# 记录测试失败
record_test_failure() {
    local model="$1"
    local group_name="$2"
    local test_type="$3"
    local failure_reason="$4"
    
    python3 -c "
import sys
sys.path.insert(0, '.')
from enhanced_failed_tests_manager import EnhancedFailedTestsManager

manager = EnhancedFailedTestsManager()
manager.record_test_failure(
    model='$model',
    group_name='$group_name',
    prompt_types='bash_execution',
    test_type='$test_type',
    failure_reason='$failure_reason'
)
"
}

# 记录测试成功
record_test_success() {
    local model="$1"
    local group_name="$2"
    local was_retry="$3"
    
    python3 -c "
import sys
sys.path.insert(0, '.')
from enhanced_failed_tests_manager import EnhancedFailedTestsManager

manager = EnhancedFailedTestsManager()
manager.record_test_success(
    model='$model',
    group_name='$group_name',
    was_retry=$was_retry
)
"
}

# ==============================================
# 用户交互函数
# ==============================================

# 显示维护菜单
show_maintenance_menu() {
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}${ICON_MAINTENANCE} 自动失败维护选项${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo -e "${YELLOW}1.${NC} 检查系统状态"
    echo -e "${YELLOW}2.${NC} 分析模型完成情况"
    echo -e "${YELLOW}3.${NC} 生成重测脚本"
    echo -e "${YELLOW}4.${NC} 执行自动维护"
    echo -e "${YELLOW}5.${NC} 执行增量重测"
    echo -e "${YELLOW}6.${NC} 查看失败测试概要"
    echo -e "${YELLOW}0.${NC} 跳过维护，继续执行"
    echo -e "${CYAN}========================================${NC}"
}

# 处理维护菜单选择
handle_maintenance_choice() {
    local choice="$1"
    local models="$2"
    
    case $choice in
        1)
            check_auto_maintenance_status
            ;;
        2)
            get_models_completion_summary "$models"
            ;;
        3)
            generate_retest_script "$models"
            ;;
        4)
            echo -e "${YELLOW}${ICON_WARNING} 是否只分析不执行？ (y/n): ${NC}"
            read -r dry_run_choice
            local dry_run=$([ "$dry_run_choice" = "y" ] && echo "true" || echo "false")
            run_auto_maintenance "$models" "$dry_run"
            ;;
        5)
            echo -e "${YELLOW}完成率阈值 (0.0-1.0, 默认0.8): ${NC}"
            read -r threshold
            threshold=${threshold:-0.8}
            echo -e "${YELLOW}${ICON_WARNING} 是否只分析不执行？ (y/n): ${NC}"
            read -r dry_run_choice
            local dry_run=$([ "$dry_run_choice" = "y" ] && echo "true" || echo "false")
            run_incremental_retest "$models" "$threshold" "$dry_run"
            ;;
        6)
            if command -v show_failed_tests_summary >/dev/null 2>&1; then
                show_failed_tests_summary
            else
                python3 enhanced_failed_tests_manager.py status
            fi
            ;;
        0)
            echo -e "${GREEN}${ICON_SUCCESS} 跳过维护，继续执行...${NC}"
            return 0
            ;;
        *)
            echo -e "${RED}${ICON_FAILURE} 无效选择${NC}"
            return 1
            ;;
    esac
}

# 自动维护向导
auto_maintenance_wizard() {
    local models="$1"
    local interactive="${2:-true}"
    
    echo -e "${PURPLE}🧙 自动维护向导${NC}"
    echo -e "${BLUE}目标模型: ${models:-所有模型}${NC}"
    
    # 1. 检查系统状态
    if ! check_auto_maintenance_status; then
        echo -e "${RED}${ICON_FAILURE} 系统状态异常，无法继续${NC}"
        return 1
    fi
    
    # 2. 分析完成情况
    get_models_completion_summary "$models"
    
    # 3. 检查未完成测试
    if check_incomplete_tests "$models"; then
        echo -e "${YELLOW}${ICON_WARNING} 发现未完成的测试${NC}"
        
        if [ "$interactive" = "true" ]; then
            echo -e "${YELLOW}是否要执行增量重测？ (y/n): ${NC}"
            read -r retest_choice
            if [ "$retest_choice" = "y" ]; then
                run_incremental_retest "$models" "0.8" "false"
            fi
        else
            echo -e "${CYAN}${ICON_INFO} 自动执行增量重测...${NC}"
            run_incremental_retest "$models" "0.8" "false"
        fi
    else
        echo -e "${GREEN}${ICON_SUCCESS} 所有测试已完成${NC}"
    fi
    
    # 4. 生成重测脚本（备用）
    if [ "$interactive" = "true" ]; then
        echo -e "${YELLOW}是否生成重测脚本？ (y/n): ${NC}"
        read -r script_choice
        if [ "$script_choice" = "y" ]; then
            generate_retest_script "$models"
        fi
    fi
    
    echo -e "${GREEN}${ICON_SUCCESS} 维护向导完成${NC}"
}

# ==============================================
# 进度管理函数
# ==============================================

# 更新进度记录
update_progress() {
    local step="$1"
    local model_index="$2"
    local substep="$3"
    local current_model="$4"
    local current_group="$5"
    
    python3 -c "
import sys
sys.path.insert(0, '.')
from enhanced_progress_manager import EnhancedProgressManager

manager = EnhancedProgressManager()
manager.update_progress(
    step='$step',
    model_index=$model_index,
    substep='$substep',
    current_model='$current_model',
    current_group='$current_group'
)
"
}

# 显示进度概要
show_progress_summary() {
    echo -e "${CYAN}${ICON_PROGRESS} 当前进度概要:${NC}"
    python3 enhanced_progress_manager.py summary 2>/dev/null || echo -e "${YELLOW}进度信息不可用${NC}"
}

# 检查是否需要重试
check_retry_needed() {
    local models="$1"
    
    python3 -c "
import sys
sys.path.insert(0, '.')
from enhanced_progress_manager import EnhancedProgressManager

manager = EnhancedProgressManager()
if manager.has_failed_tests():
    print('true')
else:
    print('false')
" 2>/dev/null
}

# ==============================================
# 配置管理函数
# ==============================================

# 加载维护配置
load_maintenance_config() {
    if [ -f "auto_maintenance_config.json" ]; then
        echo -e "${GREEN}${ICON_CONFIG} 已加载维护配置${NC}"
        python3 -c "
import json
with open('auto_maintenance_config.json', 'r') as f:
    config = json.load(f)
    retry_config = config.get('retry_strategy', {})
    auto_config = config.get('auto_retest', {})
    print(f'最大重试次数: {retry_config.get(\"max_retries\", 3)}')
    print(f'最小完成率阈值: {auto_config.get(\"minimum_completion_rate\", 0.8):.0%}')
    print(f'最大失败率阈值: {auto_config.get(\"maximum_failure_rate\", 0.3):.0%}')
"
    else
        echo -e "${YELLOW}${ICON_WARNING} 使用默认维护配置${NC}"
    fi
}

# ==============================================
# 实用工具函数
# ==============================================

# 安全执行命令（带超时）
safe_execute() {
    local command="$1"
    local timeout="${2:-300}"  # 默认5分钟超时
    local description="$3"
    
    echo -e "${BLUE}${ICON_INFO} 执行: ${description:-$command}${NC}"
    
    if timeout "$timeout" bash -c "$command"; then
        echo -e "${GREEN}${ICON_SUCCESS} 命令执行成功${NC}"
        return 0
    else
        local exit_code=$?
        if [ $exit_code -eq 124 ]; then
            echo -e "${RED}${ICON_FAILURE} 命令超时 (${timeout}s)${NC}"
        else
            echo -e "${RED}${ICON_FAILURE} 命令执行失败 (退出码: $exit_code)${NC}"
        fi
        return $exit_code
    fi
}

# 并行执行多个模型测试
parallel_model_testing() {
    local models="$1"
    local test_command_template="$2"
    local max_parallel="${3:-3}"
    
    echo -e "${CYAN}${ICON_INFO} 并行测试模型: $models (最大并行数: $max_parallel)${NC}"
    
    # 将模型字符串转换为数组
    IFS=',' read -ra MODELS_ARRAY <<< "$models"
    
    local pids=()
    local model_count=0
    
    for model in "${MODELS_ARRAY[@]}"; do
        # 替换模板中的{MODEL}为实际模型名
        local command=${test_command_template//\{MODEL\}/$model}
        
        echo -e "${BLUE}${ICON_INFO} 启动模型测试: $model${NC}"
        
        # 后台执行
        (
            execute_test_with_failure_tracking "$command" "模型 $model 测试" "$model" "parallel_test"
        ) &
        
        pids+=($!)
        ((model_count++))
        
        # 控制并行数
        if [ $model_count -ge $max_parallel ]; then
            # 等待一个任务完成
            wait ${pids[0]}
            pids=("${pids[@]:1}")  # 移除第一个PID
            ((model_count--))
        fi
    done
    
    # 等待所有剩余任务完成
    for pid in "${pids[@]}"; do
        wait $pid
    done
    
    echo -e "${GREEN}${ICON_SUCCESS} 所有模型测试完成${NC}"
}

# 日志记录函数
log_maintenance_action() {
    local action="$1"
    local details="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo "[$timestamp] $action: $details" >> "auto_maintenance_log.txt"
}

# ==============================================
# 主要入口函数
# ==============================================

# 智能维护入口（供其他脚本调用）
smart_maintenance_entry() {
    local mode="$1"           # check, auto, incremental, wizard
    local models="$2"         # 模型列表，逗号分隔
    local interactive="$3"    # true/false
    local extra_params="$4"   # 额外参数
    
    # 加载配置
    load_maintenance_config
    
    case $mode in
        "check")
            check_auto_maintenance_status
            get_models_completion_summary "$models"
            ;;
        "auto")
            local dry_run=$(echo "$extra_params" | grep -q "dry_run" && echo "true" || echo "false")
            run_auto_maintenance "$models" "$dry_run"
            ;;
        "incremental")
            local threshold=$(echo "$extra_params" | grep -o 'threshold=[0-9.]*' | cut -d= -f2)
            threshold=${threshold:-0.8}
            local dry_run=$(echo "$extra_params" | grep -q "dry_run" && echo "true" || echo "false")
            run_incremental_retest "$models" "$threshold" "$dry_run"
            ;;
        "wizard")
            auto_maintenance_wizard "$models" "$interactive"
            ;;
        "menu")
            if [ "$interactive" = "true" ]; then
                show_maintenance_menu
                echo -n "请选择: "
                read -r choice
                handle_maintenance_choice "$choice" "$models"
            else
                auto_maintenance_wizard "$models" "false"
            fi
            ;;
        *)
            echo -e "${RED}${ICON_FAILURE} 未知维护模式: $mode${NC}"
            echo -e "${YELLOW}支持的模式: check, auto, incremental, wizard, menu${NC}"
            return 1
            ;;
    esac
}

# 导出主要函数
export -f check_auto_maintenance_status
export -f get_models_completion_summary
export -f check_incomplete_tests
export -f generate_retest_script
export -f run_auto_maintenance
export -f run_incremental_retest
export -f execute_test_with_failure_tracking
export -f auto_maintenance_wizard
export -f smart_maintenance_entry
export -f show_progress_summary
export -f update_progress
export -f safe_execute
export -f parallel_model_testing

echo -e "${GREEN}${ICON_SUCCESS} 自动失败维护函数库已加载${NC}"