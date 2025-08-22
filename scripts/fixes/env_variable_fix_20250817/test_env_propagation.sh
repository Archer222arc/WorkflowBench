#!/bin/bash

# 测试环境变量是否正确传递到Python脚本

echo "测试环境变量传递"
echo "=================="

# 设置环境变量
export STORAGE_FORMAT="parquet"
export MODEL_TYPE="opensource"
export NUM_INSTANCES="2"
export RATE_MODE="fixed"

echo "设置的环境变量:"
echo "  STORAGE_FORMAT=$STORAGE_FORMAT"
echo "  MODEL_TYPE=$MODEL_TYPE"
echo "  NUM_INSTANCES=$NUM_INSTANCES"
echo "  RATE_MODE=$RATE_MODE"

# 测试后台进程中的环境变量传递
echo ""
echo "测试后台进程:"

(
    # 确保环境变量在子进程中可用
    export STORAGE_FORMAT="${STORAGE_FORMAT}"
    export MODEL_TYPE="${MODEL_TYPE}"
    export NUM_INSTANCES="${NUM_INSTANCES}"
    export RATE_MODE="${RATE_MODE}"
    
    python3 -c "
import os
print('后台进程中的环境变量:')
print(f'  STORAGE_FORMAT={os.environ.get(\"STORAGE_FORMAT\", \"未设置\")}')
print(f'  MODEL_TYPE={os.environ.get(\"MODEL_TYPE\", \"未设置\")}')
print(f'  NUM_INSTANCES={os.environ.get(\"NUM_INSTANCES\", \"未设置\")}')
print(f'  RATE_MODE={os.environ.get(\"RATE_MODE\", \"未设置\")}')

# 验证
if os.environ.get('STORAGE_FORMAT') == 'parquet':
    print('✅ 环境变量传递成功!')
else:
    print('❌ 环境变量传递失败!')
"
) &

# 等待后台进程完成
wait

echo ""
echo "测试完成"
