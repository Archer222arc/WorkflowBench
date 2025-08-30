#!/bin/bash

echo "🧹 清理当前运行的测试进程..."

# 终止所有测试进程
pkill -f "smart_batch_runner.py"
pkill -f "ultra_parallel_runner"
pkill -f "run_systematic_test"

sleep 2

# 确认清理完成
RUNNING=$(ps aux | grep -E "(smart_batch|ultra_parallel)" | grep -v grep | wc -l)
if [ $RUNNING -eq 0 ]; then
    echo "✅ 所有测试进程已清理"
else
    echo "⚠️ 仍有 $RUNNING 个进程在运行，强制终止..."
    pkill -9 -f "smart_batch_runner.py"
    pkill -9 -f "ultra_parallel_runner"
fi

echo ""
echo "📊 系统资源状态："
echo "内存使用："
free -h | grep "^Mem"
echo ""
echo "CPU负载："
uptime

echo ""
echo "=================================="
echo "🚀 使用保守方案重新启动测试"
echo "=================================="
echo ""
echo "选项："
echo "1. 测试单个qwen模型（推荐）"
echo "2. 测试所有qwen模型（保守模式）"
echo "3. 使用conservative_parallel_runner"
echo ""

# 单个模型测试示例
cat << 'EOF'
# 方案1：测试单个模型（最安全）
./run_systematic_test_final.sh --phase 5.3 --model qwen2.5-7b-instruct --workers 1

# 方案2：使用保守执行器（自动管理资源）
python3 conservative_parallel_runner.py --phase 5.3 --models "qwen2.5-7b-instruct"

# 方案3：手动控制，每次只运行一个模型
for model in qwen2.5-7b-instruct qwen2.5-14b-instruct qwen2.5-32b-instruct; do
    echo "测试 $model..."
    ./run_systematic_test_final.sh --phase 5.3 --model $model --workers 1
    sleep 60  # 模型之间休息1分钟
done
EOF

echo ""
echo "💡 建议：先用方案1测试单个模型，确认稳定后再测试其他模型"