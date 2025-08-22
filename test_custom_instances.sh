#!/bin/bash

# ============================================
# 自定义测试配置脚本
# 支持灵活配置每个测试的instance数量和task_types
# ============================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# 默认配置
DEFAULT_MODEL="gpt-4o-mini"
DEFAULT_PROMPT_TYPE="baseline"
DEFAULT_DIFFICULTY="easy"
DEFAULT_INSTANCES=2
DEFAULT_TASK_TYPES="simple_task"
DEFAULT_TOOL_SUCCESS_RATE=0.8

# 解析参数
MODEL=""
PROMPT_TYPE=""
DIFFICULTY=""
INSTANCES=""
TASK_TYPES=""
TOOL_SUCCESS_RATE=""
MAX_WORKERS=""
INTERACTIVE=false
CONFIG_FILE=""

# 显示帮助
show_help() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -m, --model MODEL            指定模型 (默认: $DEFAULT_MODEL)"
    echo "  -p, --prompt PROMPT_TYPE     指定prompt类型 (默认: $DEFAULT_PROMPT_TYPE)"
    echo "  -d, --difficulty LEVEL       指定难度 (默认: $DEFAULT_DIFFICULTY)"
    echo "  -n, --instances N            指定实例数 (默认: $DEFAULT_INSTANCES)"
    echo "  -t, --tasks TASK_TYPES       指定任务类型 (默认: $DEFAULT_TASK_TYPES)"
    echo "                               可以是: simple_task,basic_task,data_pipeline,api_integration,multi_stage_pipeline"
    echo "                               或使用 'all' 表示所有任务类型"
    echo "  -r, --rate RATE              工具成功率 (默认: $DEFAULT_TOOL_SUCCESS_RATE)"
    echo "  -w, --workers N              最大并发数"
    echo "  -i, --interactive            交互式配置模式"
    echo "  -c, --config FILE            从配置文件读取设置"
    echo "  -h, --help                   显示帮助"
    echo ""
    echo "特殊格式:"
    echo "  --instances NxT              N个实例，每个测试T种任务类型"
    echo "                               例如: 5x3 表示5个实例，每个测试3种任务类型"
    echo ""
    echo "示例:"
    echo "  $0 -m gpt-4o-mini -n 10 -t simple_task"
    echo "  $0 -m gpt-5-mini -n 5x3 -t simple_task,basic_task,data_pipeline"
    echo "  $0 -i  # 交互式模式"
    echo "  $0 -c test_config.txt  # 从配置文件读取"
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--model)
            MODEL="$2"
            shift 2
            ;;
        -p|--prompt)
            PROMPT_TYPE="$2"
            shift 2
            ;;
        -d|--difficulty)
            DIFFICULTY="$2"
            shift 2
            ;;
        -n|--instances)
            INSTANCES="$2"
            shift 2
            ;;
        -t|--tasks)
            TASK_TYPES="$2"
            shift 2
            ;;
        -r|--rate)
            TOOL_SUCCESS_RATE="$2"
            shift 2
            ;;
        -w|--workers)
            MAX_WORKERS="$2"
            shift 2
            ;;
        -i|--interactive)
            INTERACTIVE=true
            shift
            ;;
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}未知参数: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# 交互式模式
if [ "$INTERACTIVE" = true ]; then
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}       自定义测试配置 - 交互式模式${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""
    
    # 选择模型
    echo -e "${YELLOW}1. 选择模型:${NC}"
    echo "   1) gpt-4o-mini (Azure)"
    echo "   2) gpt-5-mini (Azure)"
    echo "   3) o3-0416-global (IdealLab)"
    echo "   4) gemini-2.5-flash-06-17 (IdealLab)"
    echo "   5) kimi-k2 (IdealLab)"
    echo "   6) DeepSeek-V3-0324 (Azure)"
    echo "   7) DeepSeek-R1-0528 (Azure)"
    echo "   8) Llama-3.3-70B-Instruct (Azure)"
    echo "   9) 自定义输入"
    read -p "请选择 (1-9): " model_choice
    
    case $model_choice in
        1) MODEL="gpt-4o-mini" ;;
        2) MODEL="gpt-5-mini" ;;
        3) MODEL="o3-0416-global" ;;
        4) MODEL="gemini-2.5-flash-06-17" ;;
        5) MODEL="kimi-k2" ;;
        6) MODEL="DeepSeek-V3-0324" ;;
        7) MODEL="DeepSeek-R1-0528" ;;
        8) MODEL="Llama-3.3-70B-Instruct" ;;
        9)
            read -p "输入模型名称: " MODEL
            ;;
        *)
            MODEL="$DEFAULT_MODEL"
            ;;
    esac
    
    # 选择实例配置
    echo ""
    echo -e "${YELLOW}2. 配置实例数:${NC}"
    echo "   1) 快速测试 (2个实例)"
    echo "   2) 小规模测试 (5个实例)"
    echo "   3) 中等规模 (10个实例)"
    echo "   4) 大规模测试 (20个实例)"
    echo "   5) 自定义 (输入数量)"
    echo "   6) 矩阵模式 (NxT格式)"
    read -p "请选择 (1-6): " instance_choice
    
    case $instance_choice in
        1) INSTANCES=2 ;;
        2) INSTANCES=5 ;;
        3) INSTANCES=10 ;;
        4) INSTANCES=20 ;;
        5)
            read -p "输入实例数: " INSTANCES
            ;;
        6)
            read -p "输入实例数 (N): " num_inst
            read -p "每个实例的任务类型数 (T): " num_tasks
            INSTANCES="${num_inst}x${num_tasks}"
            ;;
        *)
            INSTANCES="$DEFAULT_INSTANCES"
            ;;
    esac
    
    # 选择任务类型
    echo ""
    echo -e "${YELLOW}3. 选择任务类型:${NC}"
    echo "   1) simple_task (简单任务)"
    echo "   2) basic_task (基础任务)"
    echo "   3) data_pipeline (数据流水线)"
    echo "   4) api_integration (API集成)"
    echo "   5) multi_stage_pipeline (多阶段流水线)"
    echo "   6) 前2种 (simple + basic)"
    echo "   7) 前3种 (simple + basic + data)"
    echo "   8) 前4种 (除multi_stage外所有)"
    echo "   9) 所有任务类型"
    echo "   10) 自定义组合"
    read -p "请选择 (1-10): " task_choice
    
    case $task_choice in
        1) TASK_TYPES="simple_task" ;;
        2) TASK_TYPES="basic_task" ;;
        3) TASK_TYPES="data_pipeline" ;;
        4) TASK_TYPES="api_integration" ;;
        5) TASK_TYPES="multi_stage_pipeline" ;;
        6) TASK_TYPES="simple_task,basic_task" ;;
        7) TASK_TYPES="simple_task,basic_task,data_pipeline" ;;
        8) TASK_TYPES="simple_task,basic_task,data_pipeline,api_integration" ;;
        9) TASK_TYPES="all" ;;
        10)
            echo "输入任务类型 (逗号分隔):"
            read -p "> " TASK_TYPES
            ;;
        *)
            TASK_TYPES="$DEFAULT_TASK_TYPES"
            ;;
    esac
    
    # 其他配置
    echo ""
    echo -e "${YELLOW}4. 其他配置:${NC}"
    read -p "Prompt类型 (baseline/cot/optimal) [默认: baseline]: " PROMPT_TYPE
    [ -z "$PROMPT_TYPE" ] && PROMPT_TYPE="baseline"
    
    read -p "难度 (very_easy/easy/medium/hard) [默认: easy]: " DIFFICULTY
    [ -z "$DIFFICULTY" ] && DIFFICULTY="easy"
    
    read -p "工具成功率 (0.6-1.0) [默认: 0.8]: " TOOL_SUCCESS_RATE
    [ -z "$TOOL_SUCCESS_RATE" ] && TOOL_SUCCESS_RATE="0.8"
    
    read -p "最大并发数 (留空使用自动): " MAX_WORKERS
fi

# 从配置文件读取
if [ -n "$CONFIG_FILE" ] && [ -f "$CONFIG_FILE" ]; then
    echo -e "${CYAN}📄 从配置文件读取: $CONFIG_FILE${NC}"
    source "$CONFIG_FILE"
fi

# 使用默认值填充空值
[ -z "$MODEL" ] && MODEL="$DEFAULT_MODEL"
[ -z "$PROMPT_TYPE" ] && PROMPT_TYPE="$DEFAULT_PROMPT_TYPE"
[ -z "$DIFFICULTY" ] && DIFFICULTY="$DEFAULT_DIFFICULTY"
[ -z "$INSTANCES" ] && INSTANCES="$DEFAULT_INSTANCES"
[ -z "$TASK_TYPES" ] && TASK_TYPES="$DEFAULT_TASK_TYPES"
[ -z "$TOOL_SUCCESS_RATE" ] && TOOL_SUCCESS_RATE="$DEFAULT_TOOL_SUCCESS_RATE"

# 解析实例配置
ACTUAL_INSTANCES="$INSTANCES"
INSTANCES_PER_TASK=""

if [[ "$INSTANCES" =~ ^([0-9]+)x([0-9]+)$ ]]; then
    # NxT格式
    ACTUAL_INSTANCES="${BASH_REMATCH[1]}"
    INSTANCES_PER_TASK="${BASH_REMATCH[2]}"
    
    # 调整任务类型列表
    if [ "$TASK_TYPES" = "all" ]; then
        case $INSTANCES_PER_TASK in
            1) TASK_TYPES="simple_task" ;;
            2) TASK_TYPES="simple_task,basic_task" ;;
            3) TASK_TYPES="simple_task,basic_task,data_pipeline" ;;
            4) TASK_TYPES="simple_task,basic_task,data_pipeline,api_integration" ;;
            *) TASK_TYPES="all" ;;
        esac
    fi
fi

# 显示配置摘要
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}           测试配置摘要${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${CYAN}模型:${NC} $MODEL"
echo -e "${CYAN}Prompt类型:${NC} $PROMPT_TYPE"
echo -e "${CYAN}难度:${NC} $DIFFICULTY"
echo -e "${CYAN}实例配置:${NC} $INSTANCES"
if [ -n "$INSTANCES_PER_TASK" ]; then
    echo -e "${CYAN}  → 实际实例数:${NC} $ACTUAL_INSTANCES"
    echo -e "${CYAN}  → 每实例任务数:${NC} $INSTANCES_PER_TASK"
fi
echo -e "${CYAN}任务类型:${NC} $TASK_TYPES"
echo -e "${CYAN}工具成功率:${NC} $TOOL_SUCCESS_RATE"
[ -n "$MAX_WORKERS" ] && echo -e "${CYAN}最大并发数:${NC} $MAX_WORKERS"
echo -e "${GREEN}========================================${NC}"
echo ""

# 确认执行
if [ "$INTERACTIVE" = true ]; then
    read -p "是否执行测试？(y/n): " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo -e "${YELLOW}测试已取消${NC}"
        exit 0
    fi
fi

# 构建命令
CMD="python smart_batch_runner.py"
CMD="$CMD --model $MODEL"
CMD="$CMD --prompt-types $PROMPT_TYPE"
CMD="$CMD --difficulty $DIFFICULTY"
CMD="$CMD --task-types $TASK_TYPES"
CMD="$CMD --num-instances $ACTUAL_INSTANCES"
CMD="$CMD --tool-success-rate $TOOL_SUCCESS_RATE"
[ -n "$MAX_WORKERS" ] && CMD="$CMD --max-workers $MAX_WORKERS"
CMD="$CMD --adaptive --no-save-logs"

# 显示命令
echo -e "${BLUE}执行命令:${NC}"
echo "$CMD"
echo ""

# 保存配置到历史
HISTORY_FILE="test_history_$(date +%Y%m%d).log"
echo "# $(date '+%Y-%m-%d %H:%M:%S')" >> "$HISTORY_FILE"
echo "MODEL=$MODEL" >> "$HISTORY_FILE"
echo "PROMPT_TYPE=$PROMPT_TYPE" >> "$HISTORY_FILE"
echo "DIFFICULTY=$DIFFICULTY" >> "$HISTORY_FILE"
echo "INSTANCES=$INSTANCES" >> "$HISTORY_FILE"
echo "TASK_TYPES=$TASK_TYPES" >> "$HISTORY_FILE"
echo "TOOL_SUCCESS_RATE=$TOOL_SUCCESS_RATE" >> "$HISTORY_FILE"
[ -n "$MAX_WORKERS" ] && echo "MAX_WORKERS=$MAX_WORKERS" >> "$HISTORY_FILE"
echo "" >> "$HISTORY_FILE"

# 执行测试
echo -e "${GREEN}🚀 开始测试...${NC}"
eval "$CMD"

# 检查结果
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ 测试完成！${NC}"
    
    # 显示简单统计
    echo ""
    echo -e "${CYAN}📊 查看统计:${NC}"
    python -c "
import json
from pathlib import Path

db_path = Path('pilot_bench_cumulative_results/master_database.json')
if db_path.exists():
    with open(db_path, 'r') as f:
        db = json.load(f)
    
    model = '$MODEL'
    if model in db.get('models', {}):
        model_data = db['models'][model]
        if 'by_prompt_type' in model_data:
            pt_data = model_data['by_prompt_type'].get('$PROMPT_TYPE', {})
            if 'by_tool_success_rate' in pt_data:
                rate_key = str(round($TOOL_SUCCESS_RATE, 1))
                rate_data = pt_data['by_tool_success_rate'].get(rate_key, {})
                if 'by_difficulty' in rate_data:
                    diff_data = rate_data['by_difficulty'].get('$DIFFICULTY', {})
                    if 'by_task_type' in diff_data:
                        print(f'模型 {model} 在当前配置下的结果:')
                        for task_type, task_data in diff_data['by_task_type'].items():
                            total = task_data.get('total', 0)
                            success_rate = task_data.get('success_rate', 0)
                            print(f'  {task_type}: {total} 个测试, 成功率 {success_rate:.1%}')
" 2>/dev/null
else
    echo ""
    echo -e "${RED}❌ 测试失败${NC}"
fi
