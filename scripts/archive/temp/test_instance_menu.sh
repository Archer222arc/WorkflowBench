#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# 测试变量
NUM_INSTANCES=20
INSTANCES_PER_TASK=""

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}        测试自定义实例数功能${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# 模拟 confirm_continue 函数的核心部分
echo -e "${YELLOW}即将开始基准测试（8个模型×100个测试）...${NC}"
echo ""

echo -e "${CYAN}当前实例数配置: ${NUM_INSTANCES}${NC}"
if [ -n "$INSTANCES_PER_TASK" ]; then
    echo -e "${CYAN}  每实例任务数: ${INSTANCES_PER_TASK}${NC}"
fi
echo ""
echo -e "${YELLOW}是否要修改实例数配置？${NC}"
echo "  1) 使用当前配置 (${NUM_INSTANCES})"
echo "  2) 快速测试 (2个实例)"
echo "  3) 小规模测试 (5个实例)"
echo "  4) 中等规模 (10个实例)"
echo "  5) 大规模测试 (20个实例)"
echo "  6) 完整测试 (100个实例)"
echo "  7) 自定义数量"
echo "  8) 矩阵模式 (NxT格式)"
echo ""
echo -e "${YELLOW}请选择 [1-8] (默认: 1):${NC}"

read -r instance_choice

# 如果用户直接按Enter，使用默认值
if [ -z "$instance_choice" ]; then
    instance_choice="1"
fi

case $instance_choice in
    1)
        echo -e "${GREEN}✓ 使用当前配置: ${NUM_INSTANCES}${NC}"
        ;;
    2)
        NUM_INSTANCES=2
        INSTANCES_PER_TASK=""
        echo -e "${GREEN}✓ 设置为快速测试: 2个实例${NC}"
        ;;
    3)
        NUM_INSTANCES=5
        INSTANCES_PER_TASK=""
        echo -e "${GREEN}✓ 设置为小规模测试: 5个实例${NC}"
        ;;
    4)
        NUM_INSTANCES=10
        INSTANCES_PER_TASK=""
        echo -e "${GREEN}✓ 设置为中等规模: 10个实例${NC}"
        ;;
    5)
        NUM_INSTANCES=20
        INSTANCES_PER_TASK=""
        echo -e "${GREEN}✓ 设置为大规模测试: 20个实例${NC}"
        ;;
    6)
        NUM_INSTANCES=100
        INSTANCES_PER_TASK=""
        echo -e "${GREEN}✓ 设置为完整测试: 100个实例${NC}"
        ;;
    7)
        echo -e "${CYAN}请输入自定义实例数:${NC}"
        read -r custom_num
        if [[ "$custom_num" =~ ^[0-9]+$ ]]; then
            NUM_INSTANCES="$custom_num"
            INSTANCES_PER_TASK=""
            echo -e "${GREEN}✓ 设置为自定义: ${NUM_INSTANCES}个实例${NC}"
        else
            echo -e "${YELLOW}⚠️ 无效输入，保持原配置: ${NUM_INSTANCES}${NC}"
        fi
        ;;
    8)
        echo -e "${CYAN}矩阵模式配置 (NxT: N个实例，每个T种任务类型)${NC}"
        echo -e "${CYAN}请输入实例数 (N):${NC}"
        read -r matrix_num
        echo -e "${CYAN}请输入每实例任务数 (T) [1-5]:${NC}"
        echo "  1 = simple_task"
        echo "  2 = simple_task, basic_task"
        echo "  3 = simple_task, basic_task, data_pipeline"
        echo "  4 = simple_task, basic_task, data_pipeline, api_integration"
        echo "  5 = 所有任务类型"
        read -r matrix_tasks
        
        if [[ "$matrix_num" =~ ^[0-9]+$ ]] && [[ "$matrix_tasks" =~ ^[1-5]$ ]]; then
            NUM_INSTANCES="$matrix_num"
            INSTANCES_PER_TASK="$matrix_tasks"
            echo -e "${GREEN}✓ 设置为矩阵模式: ${NUM_INSTANCES}×${INSTANCES_PER_TASK}${NC}"
        else
            echo -e "${YELLOW}⚠️ 无效输入，保持原配置: ${NUM_INSTANCES}${NC}"
        fi
        ;;
    *)
        echo -e "${GREEN}✓ 使用当前配置: ${NUM_INSTANCES}${NC}"
        ;;
esac

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}           最终配置${NC}"
echo -e "${CYAN}========================================${NC}"
echo -e "${GREEN}实例数: ${NUM_INSTANCES}${NC}"
if [ -n "$INSTANCES_PER_TASK" ]; then
    echo -e "${GREEN}矩阵模式: ${NUM_INSTANCES}×${INSTANCES_PER_TASK}${NC}"
    
    # 显示任务类型分配
    case $INSTANCES_PER_TASK in
        1)
            echo -e "${GREEN}  任务类型: simple_task${NC}"
            ;;
        2)
            echo -e "${GREEN}  任务类型: simple_task, basic_task${NC}"
            ;;
        3)
            echo -e "${GREEN}  任务类型: simple_task, basic_task, data_pipeline${NC}"
            ;;
        4)
            echo -e "${GREEN}  任务类型: simple_task, basic_task, data_pipeline, api_integration${NC}"
            ;;
        5)
            echo -e "${GREEN}  任务类型: 所有任务类型${NC}"
            ;;
    esac
fi
echo -e "${CYAN}========================================${NC}"
