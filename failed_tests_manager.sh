#!/bin/bash

# 失败测试管理器 - 读取和处理失败测试配置

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# 获取失败测试配置文件名（根据模型类型）
get_failed_tests_config_file() {
    if [ "$MODEL_TYPE" = "closed_source" ]; then
        echo "failed_tests_config_closed_source.json"
    else
        echo "failed_tests_config_opensource.json"
    fi
}

# 检查失败测试配置文件是否存在
check_failed_tests_config() {
    local config_file=$(get_failed_tests_config_file)
    if [ ! -f "$config_file" ]; then
        return 1
    fi
    return 0
}

# 显示失败测试概要
show_failed_tests_summary() {
    if ! check_failed_tests_config; then
        echo -e "${YELLOW}📝 没有发现失败测试记录${NC}"
        return 1
    fi
    
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}📋 失败测试会话概要${NC}"
    echo -e "${CYAN}========================================${NC}"
    
    # 使用python解析JSON配置
    local config_file=$(get_failed_tests_config_file)
    python3 -c "
import json
import sys

try:
    import sys
    config_file = sys.argv[1] if len(sys.argv) > 1 else 'failed_tests_config.json'
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    session = config['failed_tests_session']
    print(f\"📅 会话日期: {session['session_date']}\")
    print(f\"📄 描述: {session['session_description']}\")
    print(f\"❌ 失败模型数: {session['total_failed_models']}\")
    
    print('\n失败的模型和测试组:')
    for i, model_data in enumerate(session['failed_groups'], 1):
        model = model_data['model']
        status = model_data['status']
        failed_count = len(model_data['failed_groups'])
        remaining_count = len(model_data['remaining_groups'])
        
        print(f'  {i}. {model} ({status})')
        print(f'     ❌ 失败组数: {failed_count}')
        print(f'     ⏳ 剩余组数: {remaining_count}')
    
    cleanup = session['cleanup_status']
    if cleanup['database_cleaned']:
        print(f\"\n✅ 数据库已清理 (删除了 {len(cleanup['deleted_models'])} 个分片模型)\")
    
except Exception as e:
    print(f'❌ 解析配置文件失败: {e}', file=sys.stderr)
    sys.exit(1)
" "$config_file"
    
    return 0
}

# 显示详细的失败测试列表
show_failed_tests_details() {
    if ! check_failed_tests_config; then
        echo -e "${RED}❌ 没有找到失败测试配置文件${NC}"
        return 1
    fi
    
    echo -e "${PURPLE}========================================${NC}"
    echo -e "${PURPLE}🔍 失败测试详细信息${NC}"  
    echo -e "${PURPLE}========================================${NC}"
    
    local config_file=$(get_failed_tests_config_file)
    python3 -c "
import json
import sys

config_file = sys.argv[1] if len(sys.argv) > 1 else 'failed_tests_config.json'
with open(config_file, 'r', encoding='utf-8') as f:
    config = json.load(f)

session = config['failed_tests_session']
params = session['test_parameters']

print(f\"测试参数: 难度={params['difficulty']}, 任务类型={params['task_types']}, 实例数={params['num_instances']}\")
print()

for i, model_data in enumerate(session['failed_groups'], 1):
    model = model_data['model']
    print(f'{i}. 🔴 {model}')
    
    print('   失败的测试组:')
    for failed in model_data['failed_groups']:
        print(f'     ❌ {failed[\"group_name\"]}')
        print(f'        Prompt类型: {failed[\"prompt_types\"]}')
        print(f'        失败原因: {failed[\"reason\"]}')
    
    print('   需要重测的测试组:')
    for remaining in model_data['remaining_groups']:
        print(f'     ⏳ {remaining[\"group_name\"]}')
        print(f'        Prompt类型: {remaining[\"prompt_types\"]}')
    print()
" "$config_file"
    
    return 0
}

# 生成重测命令列表
generate_retest_commands() {
    if ! check_failed_tests_config; then
        echo -e "${RED}❌ 没有找到失败测试配置文件${NC}"
        return 1
    fi
    
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}🔄 生成重测命令${NC}"
    echo -e "${GREEN}========================================${NC}"
    
    local config_file=$(get_failed_tests_config_file)
    python3 -c "
import json
import sys

config_file = sys.argv[1] if len(sys.argv) > 1 else 'failed_tests_config.json'
with open(config_file, 'r', encoding='utf-8') as f:
    config = json.load(f)

session = config['failed_tests_session']
params = session['test_parameters']

print('# 重新测试失败的测试组命令')
print('# 生成时间: $(date)')
print()

for model_data in session['failed_groups']:
    model = model_data['model']
    print(f'# === {model} ===')
    
    # 重测失败的组
    for failed in model_data['failed_groups']:
        prompt_types = failed['prompt_types']
        group_name = failed['group_name']
        print(f'# 重测 {group_name} (之前失败)')
        print(f'run_smart_test \"{model}\" \"{prompt_types}\" \"{params[\"difficulty\"]}\" \"{params[\"task_types\"]}\" \"{params[\"num_instances\"]}\" \"{model}-{group_name}\" \"\"')
        print()
    
    # 完成剩余的组
    for remaining in model_data['remaining_groups']:
        prompt_types = remaining['prompt_types']
        group_name = remaining['group_name']
        print(f'# 完成 {group_name} (未完成)')
        print(f'run_smart_test \"{model}\" \"{prompt_types}\" \"{params[\"difficulty\"]}\" \"{params[\"task_types\"]}\" \"{params[\"num_instances\"]}\" \"{model}-{group_name}\" \"\"')
        print()
    
    print()
" "$config_file"
}

# 检查某个模型是否在失败列表中
is_model_in_failed_list() {
    local model_name="$1"
    
    if ! check_failed_tests_config; then
        return 1
    fi
    
    local config_file=$(get_failed_tests_config_file)
    python3 -c "
import json
import sys

config_file = sys.argv[1] if len(sys.argv) > 1 else 'failed_tests_config.json'
with open(config_file, 'r', encoding='utf-8') as f:
    config = json.load(f)

failed_models = [model_data['model'] for model_data in config['failed_tests_session']['failed_groups']]
sys.exit(0 if '$model_name' in failed_models else 1)
" "$config_file"
    
    return $?
}

# 获取某个模型的失败测试信息
get_model_failed_info() {
    local model_name="$1"
    
    if ! check_failed_tests_config; then
        return 1
    fi
    
    local config_file=$(get_failed_tests_config_file)
    python3 -c "
import json
import sys

config_file = sys.argv[1] if len(sys.argv) > 1 else 'failed_tests_config.json'
with open(config_file, 'r', encoding='utf-8') as f:
    config = json.load(f)

for model_data in config['failed_tests_session']['failed_groups']:
    if model_data['model'] == '$model_name':
        print('FAILED_GROUPS:')
        for failed in model_data['failed_groups']:
            print(f'{failed[\"group_name\"]}:{failed[\"prompt_types\"]}')
        
        print('REMAINING_GROUPS:')
        for remaining in model_data['remaining_groups']:
            print(f'{remaining[\"group_name\"]}:{remaining[\"prompt_types\"]}')
        
        break
" "$config_file"
}

# 标记失败测试为已完成
mark_failed_test_completed() {
    local model_name="$1"
    local group_name="$2"
    
    # 这里可以实现更新配置文件的逻辑
    # 暂时只是显示消息
    echo -e "${GREEN}✅ 标记 ${model_name} 的 ${group_name} 为已完成${NC}"
}

# 主要导出的函数
export -f check_failed_tests_config
export -f show_failed_tests_summary
export -f show_failed_tests_details
export -f generate_retest_commands
export -f is_model_in_failed_list
export -f get_model_failed_info
export -f mark_failed_test_completed