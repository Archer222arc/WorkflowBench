#!/bin/bash

echo "========================================="
echo "PILOT-Bench 测试修复和监控工具"
echo "========================================="

# 1. 检查当前状态
echo -e "\n1️⃣ 当前测试状态:"
ps aux | grep -E "(smart_batch_runner|ultra_parallel)" | grep -v grep | wc -l | xargs -I {} echo "  运行中的进程: {} 个"

# 2. 检查数据更新
echo -e "\n2️⃣ 数据更新情况:"
if [ -f "pilot_bench_cumulative_results/master_database.json" ]; then
    LAST_UPDATE=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" pilot_bench_cumulative_results/master_database.json 2>/dev/null || \
                  stat -c "%y" pilot_bench_cumulative_results/master_database.json 2>/dev/null | cut -d. -f1)
    echo "  JSON数据库最后更新: $LAST_UPDATE"
    
    # 统计测试数
    TOTAL_TESTS=$(python3 -c "
import json
with open('pilot_bench_cumulative_results/master_database.json', 'r') as f:
    db = json.load(f)
total = 0
for m in db.get('models', {}).values():
    if 'by_prompt_type' in m:
        for p in m['by_prompt_type'].values():
            if 'by_tool_success_rate' in p:
                for r in p['by_tool_success_rate'].values():
                    if 'by_difficulty' in r:
                        for d in r['by_difficulty'].values():
                            if 'by_task_type' in d:
                                for t in d['by_task_type'].values():
                                    total += t.get('total', 0)
print(total)
" 2>/dev/null || echo "0")
    echo "  总测试数: $TOTAL_TESTS"
fi

# 3. 检查Parquet目录
echo -e "\n3️⃣ Parquet存储检查:"
if [ -d "pilot_bench_parquet_data" ]; then
    echo "  ✅ Parquet目录存在"
    PARQUET_FILES=$(find pilot_bench_parquet_data -name "*.parquet" 2>/dev/null | wc -l)
    echo "  Parquet文件数: $PARQUET_FILES"
else
    echo "  ❌ Parquet目录不存在"
fi

# 4. 提供选项
echo -e "\n请选择操作:"
echo "  1) 查看实时日志"
echo "  2) 检查测试进度"
echo "  3) 终止所有测试"
echo "  4) 设置Parquet模式并重启"
echo "  5) 退出"

read -p "选择 [1-5]: " choice

case $choice in
    1)
        echo "查看最新日志（Ctrl+C退出）..."
        tail -f logs/batch_test_*.log | grep -E "(成功|失败|完成|checkpoint|总计)"
        ;;
    2)
        python3 view_test_progress.py
        ;;
    3)
        echo "终止所有测试进程..."
        pkill -f "smart_batch_runner"
        pkill -f "ultra_parallel"
        echo "✅ 已发送终止信号"
        ;;
    4)
        echo "设置Parquet模式..."
        export STORAGE_FORMAT=parquet
        echo "export STORAGE_FORMAT=parquet" >> ~/.zshrc
        echo "export STORAGE_FORMAT=parquet" >> ~/.bashrc
        echo "✅ 已设置环境变量"
        echo ""
        echo "请在新终端中运行:"
        echo "  export STORAGE_FORMAT=parquet"
        echo "  ./run_systematic_test_final.sh"
        ;;
    5)
        exit 0
        ;;
esac
