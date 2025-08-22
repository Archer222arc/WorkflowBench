#!/bin/bash

# ============================================
# 快速停止脚本 - 终止所有测试相关进程
# ============================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}🛑 开始终止所有测试相关进程...${NC}"
echo ""

# 1. 查找并显示所有测试相关进程
echo -e "${BLUE}📋 当前运行的测试进程:${NC}"
TEST_PROCESSES=$(ps aux | grep -E "(python.*batch|python.*test|python.*runner|python.*smart|python.*systematic|python.*ultra)" | grep -v grep | grep -v "stop.sh")

if [ -z "$TEST_PROCESSES" ]; then
    echo -e "${GREEN}✅ 没有发现运行中的测试进程${NC}"
else
    echo "$TEST_PROCESSES" | while read line; do
        PID=$(echo $line | awk '{print $2}')
        COMMAND=$(echo $line | awk '{for(i=11;i<=NF;i++) printf "%s ", $i; print ""}')
        echo -e "${YELLOW}  PID $PID: ${COMMAND}${NC}"
    done
fi

echo ""

# 2. 温和终止 (SIGTERM)
echo -e "${CYAN}🔄 步骤1: 温和终止 (SIGTERM)...${NC}"
PIDS=$(ps aux | grep -E "(python.*batch|python.*test|python.*runner|python.*smart|python.*systematic|python.*ultra)" | grep -v grep | grep -v "stop.sh" | awk '{print $2}')

if [ -n "$PIDS" ]; then
    echo "终止进程: $PIDS"
    echo $PIDS | xargs kill -TERM 2>/dev/null
    
    # 等待3秒让进程优雅退出
    echo "等待进程优雅退出..."
    sleep 3
else
    echo "没有进程需要终止"
fi

# 3. 检查是否还有残留进程
echo ""
echo -e "${CYAN}🔍 步骤2: 检查残留进程...${NC}"
REMAINING=$(ps aux | grep -E "(python.*batch|python.*test|python.*runner|python.*smart|python.*systematic|python.*ultra)" | grep -v grep | grep -v "stop.sh")

if [ -n "$REMAINING" ]; then
    echo -e "${YELLOW}⚠️  发现残留进程，强制终止...${NC}"
    REMAINING_PIDS=$(echo "$REMAINING" | awk '{print $2}')
    echo "强制终止进程: $REMAINING_PIDS"
    echo $REMAINING_PIDS | xargs kill -9 2>/dev/null
    sleep 1
else
    echo -e "${GREEN}✅ 没有残留进程${NC}"
fi

# 4. 最终验证
echo ""
echo -e "${CYAN}🔍 步骤3: 最终验证...${NC}"
FINAL_CHECK=$(ps aux | grep -E "(python.*batch|python.*test|python.*runner|python.*smart|python.*systematic|python.*ultra)" | grep -v grep | grep -v "stop.sh")

if [ -z "$FINAL_CHECK" ]; then
    echo -e "${GREEN}✅ 所有测试进程已成功终止${NC}"
else
    echo -e "${RED}❌ 仍有进程残留:${NC}"
    echo "$FINAL_CHECK"
fi

# 5. 清理后台作业
echo ""
echo -e "${CYAN}🧹 步骤4: 清理后台作业...${NC}"
# 终止当前shell的所有后台作业
jobs -p | xargs -r kill 2>/dev/null
echo -e "${GREEN}✅ 后台作业清理完成${NC}"

# 6. 显示统计信息
echo ""
echo -e "${CYAN}📊 终止统计:${NC}"
echo "  - 温和终止: $(echo $PIDS | wc -w) 个进程"
echo "  - 强制终止: $(echo $REMAINING_PIDS | wc -w) 个进程"

echo ""
echo -e "${GREEN}🎯 所有测试进程终止完成！${NC}"
echo -e "${BLUE}💡 提示: 使用 'ps aux | grep python' 可以查看剩余的Python进程${NC}"