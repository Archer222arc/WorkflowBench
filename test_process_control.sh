#!/bin/bash

# 测试进程控制功能

echo "=================================="
echo "测试进程控制功能"
echo "=================================="

# 设置环境变量来控制最大进程数
export MAX_CONCURRENT_PROCESSES=3
export USE_RESULT_COLLECTOR=true
export STORAGE_FORMAT=json

echo ""
echo "配置："
echo "  MAX_CONCURRENT_PROCESSES=$MAX_CONCURRENT_PROCESSES"
echo "  只允许最多3个并发进程"
echo ""

# 清理旧进程
echo "清理旧进程..."
pkill -f "smart_batch_runner"
pkill -f "ultra_parallel_runner"
sleep 2

# 监控进程数
monitor_processes() {
    while true; do
        local count=$(ps aux | grep -E "(smart_batch_runner|ultra_parallel_runner)" | grep -v grep | wc -l | tr -d ' ')
        echo "[$(date '+%H:%M:%S')] 当前进程数: $count"
        
        if [ $count -gt 0 ]; then
            echo "  运行中的进程:"
            ps aux | grep -E "(smart_batch_runner|ultra_parallel_runner)" | grep -v grep | awk '{print "    PID", $2, "模型:", $13}' | head -5
        fi
        
        sleep 5
        
        # 如果没有进程了就退出
        if [ $count -eq 0 ]; then
            echo "所有进程已完成"
            break
        fi
    done
}

# 启动监控（后台）
echo "启动进程监控..."
monitor_processes &
MONITOR_PID=$!

# 测试5.3，会尝试启动多个进程
echo ""
echo "开始5.3测试（会触发进程控制）..."
echo ""

# 尝试启动多个模型测试
./run_systematic_test_final.sh --phase 5.3 --auto --ultra-parallel &

# 等待一段时间观察
sleep 60

# 清理
echo ""
echo "清理测试进程..."
pkill -f "smart_batch_runner"
pkill -f "ultra_parallel_runner"
kill $MONITOR_PID 2>/dev/null

echo ""
echo "✅ 测试完成！"
echo ""
echo "如果进程控制正常工作，你应该看到："
echo "1. 最多只有3个进程同时运行"
echo "2. 新进程会等待旧进程完成"
echo "3. 有等待提示信息"