#!/bin/bash
# 测试API Key轮换策略的实际效果

echo "=========================================="
echo "测试API Key轮换策略 - 小规模测试"
echo "=========================================="
echo ""

# 设置环境变量
export KMP_DUPLICATE_LIB_OK=TRUE
export NUM_INSTANCES=2  # 小规模测试

echo "📊 测试配置："
echo "  - 测试2个qwen模型并发"
echo "  - 每个模型2个实例"
echo "  - 验证使用不同的API keys"
echo ""

echo "1. 清理旧的QPS状态文件..."
rm -f /tmp/qps_limiter/*.json
echo ""

echo "2. 启动第一个模型 (qwen2.5-72b，应该使用key0)..."
python ultra_parallel_runner.py \
    --model qwen2.5-72b-instruct \
    --prompt-types optimal \
    --difficulty easy \
    --task-types simple_task \
    --num-instances 2 \
    --silent &
PID1=$!
echo "   PID: $PID1"

# 延迟几秒，确保第一个模型已经开始
sleep 3

echo ""
echo "3. 启动第二个模型 (qwen2.5-32b，应该使用key1)..."
python ultra_parallel_runner.py \
    --model qwen2.5-32b-instruct \
    --prompt-types optimal \
    --difficulty easy \
    --task-types simple_task \
    --num-instances 2 \
    --silent &
PID2=$!
echo "   PID: $PID2"

echo ""
echo "4. 监控QPS状态文件 (10秒)..."
for i in {1..10}; do
    echo ""
    echo "   [第${i}秒] 当前状态文件："
    ls -la /tmp/qps_limiter/*.json 2>/dev/null | awk '{print "     " $9}' | grep -v "^$"
    
    # 检查是否有key冲突
    if ls /tmp/qps_limiter/*72b*key*.json 2>/dev/null | grep -q "key0"; then
        echo "     ✅ 72b模型使用key0"
    fi
    if ls /tmp/qps_limiter/*32b*key*.json 2>/dev/null | grep -q "key1"; then
        echo "     ✅ 32b模型使用key1"
    fi
    
    sleep 1
done

echo ""
echo "5. 终止测试进程..."
kill $PID1 $PID2 2>/dev/null
wait $PID1 $PID2 2>/dev/null

echo ""
echo "6. 最终状态检查..."
echo "   状态文件："
ls -la /tmp/qps_limiter/*.json 2>/dev/null | awk '{print "     " $9 " (大小: " $5 "字节)"}' | grep -v "^$"

echo ""
echo "=========================================="
echo "测试完成"
echo "=========================================="
echo ""
echo "预期结果："
echo "  - 应该看到两个不同的state文件"
echo "  - 72b模型使用key0"
echo "  - 32b模型使用key1"
echo "  - 没有key冲突"