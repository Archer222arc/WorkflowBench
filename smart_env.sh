#!/bin/bash
# 智能数据收集器环境变量设置
# 解决5.1超并发实验的数据记录问题

echo "🔧 设置智能数据收集环境变量..."

# 基本配置
export USE_SMART_COLLECTOR="true"
export COLLECTOR_SCALE="small"  # 适合5个测试/分片的小规模配置
export NUM_TESTS="5"            # 每个分片的测试数量

# 存储格式
export STORAGE_FORMAT="json"    # 继续使用JSON格式

# 调试选项
export DEBUG_COLLECTOR="false"

echo "✅ 环境变量设置完成"
echo "   USE_SMART_COLLECTOR: $USE_SMART_COLLECTOR"
echo "   COLLECTOR_SCALE: $COLLECTOR_SCALE"
echo "   NUM_TESTS: $NUM_TESTS"
echo "   STORAGE_FORMAT: $STORAGE_FORMAT"

echo ""
echo "🎯 使用方法:"
echo "1. source ./smart_env.sh"  
echo "2. ./run_systematic_test_final.sh --phase 5.1"
echo ""
echo "或者直接运行:"
echo "USE_SMART_COLLECTOR=true COLLECTOR_SCALE=small ./run_systematic_test_final.sh --phase 5.1"
