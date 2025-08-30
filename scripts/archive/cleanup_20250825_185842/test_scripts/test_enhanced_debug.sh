#!/bin/bash

# 测试增强的调试日志功能
# 这个脚本展示了如何捕获多层次的子进程输出

echo "======================================"
echo "测试增强调试日志功能"
echo "======================================"
echo ""
echo "这个测试将："
echo "1. 运行ultra_parallel_runner的调试版本"
echo "2. 每个分片的输出保存到独立日志文件"
echo "3. 捕获smart_batch_runner.py的详细输出"
echo "4. 生成调试报告"
echo ""

# 设置环境变量
export STORAGE_FORMAT=parquet
export PYTHONFAULTHANDLER=1
export PYTHONUNBUFFERED=1

# 运行测试
./run_systematic_test_final.sh --debug-log

# 测试完成后，显示日志目录
echo ""
echo "======================================"
echo "调试完成"
echo "======================================"
echo ""
echo "查看最新的调试日志："
echo ""

# 找到最新的debug目录
LATEST_DEBUG_DIR=$(ls -dt logs/debug_ultra_* 2>/dev/null | head -1)

if [ -n "$LATEST_DEBUG_DIR" ]; then
    echo "调试目录: $LATEST_DEBUG_DIR"
    echo ""
    echo "包含的文件："
    ls -la "$LATEST_DEBUG_DIR/" | grep -E "(shard_|report)"
    
    echo ""
    echo "查看调试报告："
    echo "cat $LATEST_DEBUG_DIR/debug_report.md"
    
    echo ""
    echo "查看特定分片日志："
    echo "less $LATEST_DEBUG_DIR/shard_01_*.log"
else
    echo "未找到调试日志目录"
fi