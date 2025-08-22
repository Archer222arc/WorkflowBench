#!/bin/bash

echo "================================================"
echo "      Parquet 存储问题修复工具"
echo "================================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 1. 检查当前状态
echo -e "\n${BLUE}1. 检查当前状态...${NC}"

# 检查运行中的进程
RUNNING_PROCS=$(ps aux | grep -E "(smart_batch_runner|ultra_parallel)" | grep -v grep | wc -l | tr -d ' ')
echo "   运行中的测试进程: $RUNNING_PROCS 个"

# 检查环境变量
CURRENT_FORMAT="${STORAGE_FORMAT:-json}"
echo "   当前STORAGE_FORMAT: $CURRENT_FORMAT"

# 2. 修复run_systematic_test_final.sh
echo -e "\n${BLUE}2. 修复测试脚本...${NC}"

# 备份原脚本
cp run_systematic_test_final.sh run_systematic_test_final.sh.backup
echo "   ✓ 已备份原脚本"

# 修复脚本：确保环境变量传递给子进程
cat > fix_env_propagation.patch << 'PATCH'
--- 修复环境变量传递问题
+++ 在运行命令前确保导出环境变量
@@ run_test_with_runner部分
-    python ultra_parallel_runner.py \
+    STORAGE_FORMAT="${STORAGE_FORMAT}" python ultra_parallel_runner.py \
@@ run_single_test部分  
-    python smart_batch_runner.py \
+    STORAGE_FORMAT="${STORAGE_FORMAT}" python smart_batch_runner.py \
PATCH

# 应用修复
sed -i.bak 's/python ultra_parallel_runner.py/STORAGE_FORMAT="${STORAGE_FORMAT}" python ultra_parallel_runner.py/g' run_systematic_test_final.sh
sed -i.bak 's/python smart_batch_runner.py/STORAGE_FORMAT="${STORAGE_FORMAT}" python smart_batch_runner.py/g' run_systematic_test_final.sh

echo -e "   ${GREEN}✓ 已修复环境变量传递${NC}"

# 3. 创建Parquet目录结构
echo -e "\n${BLUE}3. 确保Parquet目录结构...${NC}"

mkdir -p pilot_bench_cumulative_results/parquet_data/incremental
mkdir -p pilot_bench_parquet_data/incremental

echo "   ✓ 目录结构已创建"

# 4. 验证Parquet依赖
echo -e "\n${BLUE}4. 验证Parquet依赖...${NC}"

python3 -c "import pandas, pyarrow" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "   ${GREEN}✓ Parquet依赖正常${NC}"
else
    echo -e "   ${RED}✗ 缺少Parquet依赖${NC}"
    echo "   请运行: pip install pandas pyarrow"
    exit 1
fi

# 5. 创建环境设置脚本
echo -e "\n${BLUE}5. 创建环境设置脚本...${NC}"

cat > set_parquet_env.sh << 'ENV'
#!/bin/bash
# Parquet环境设置脚本

export STORAGE_FORMAT=parquet
echo "✅ STORAGE_FORMAT已设置为: parquet"

# 验证设置
if [ "$STORAGE_FORMAT" = "parquet" ]; then
    echo "✅ 环境变量设置成功"
    echo ""
    echo "现在可以运行："
    echo "  ./run_systematic_test_final.sh"
else
    echo "❌ 环境变量设置失败"
fi
ENV

chmod +x set_parquet_env.sh
echo "   ✓ 已创建 set_parquet_env.sh"

# 6. 提供选项
echo -e "\n${YELLOW}================================================${NC}"
echo -e "${YELLOW}请选择操作:${NC}"
echo "  1) 终止当前测试并使用Parquet重启"
echo "  2) 保持当前测试，下次使用Parquet"
echo "  3) 查看当前测试进度"
echo "  4) 退出"

read -p "选择 [1-4]: " choice

case $choice in
    1)
        echo -e "\n${YELLOW}终止当前测试...${NC}"
        pkill -f smart_batch_runner
        pkill -f ultra_parallel
        sleep 2
        
        echo -e "${GREEN}✓ 已终止${NC}"
        echo ""
        echo "请执行以下命令重启测试："
        echo -e "${BLUE}source set_parquet_env.sh${NC}"
        echo -e "${BLUE}./run_systematic_test_final.sh${NC}"
        ;;
    2)
        echo -e "\n${GREEN}保持当前测试运行${NC}"
        echo "下次测试将使用Parquet格式"
        echo ""
        echo "下次运行前请执行："
        echo -e "${BLUE}source set_parquet_env.sh${NC}"
        ;;
    3)
        echo -e "\n${BLUE}当前测试进度：${NC}"
        python3 view_test_progress.py 2>/dev/null || echo "无法查看进度"
        ;;
    4)
        exit 0
        ;;
esac

echo -e "\n${GREEN}================================================${NC}"
echo -e "${GREEN}修复完成！${NC}"
echo -e "${GREEN}================================================${NC}"
