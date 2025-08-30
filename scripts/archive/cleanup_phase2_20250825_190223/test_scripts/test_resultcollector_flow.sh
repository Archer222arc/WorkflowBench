#!/bin/bash
# 测试ResultCollector完整流程

echo "🧪 测试ResultCollector完整流程"
echo "=================================="

# 模拟选择格式3
echo "1. 设置环境变量（模拟选择格式3）"
export STORAGE_FORMAT="json"
export USE_RESULT_COLLECTOR="true"

echo "✅ 环境变量设置:"
echo "  STORAGE_FORMAT: $STORAGE_FORMAT"
echo "  USE_RESULT_COLLECTOR: $USE_RESULT_COLLECTOR"
echo ""

# 测试Python脚本能否正确检测
echo "2. 测试Python脚本检测"
USE_RESULT_COLLECTOR="$USE_RESULT_COLLECTOR" STORAGE_FORMAT="$STORAGE_FORMAT" python3 -c "
import os
print('Python进程中的环境变量:')
print(f'  USE_RESULT_COLLECTOR: {os.environ.get(\"USE_RESULT_COLLECTOR\")}')
print(f'  STORAGE_FORMAT: {os.environ.get(\"STORAGE_FORMAT\")}')

try:
    from ultra_parallel_runner import UltraParallelRunner
    runner = UltraParallelRunner()
    print(f'✅ UltraParallelRunner检测结果: use_collector_mode={runner.use_collector_mode}')
    print(f'✅ ResultCollector实例存在: {runner.result_collector is not None}')
except Exception as e:
    print(f'❌ 测试失败: {e}')
"

echo ""
echo "3. 测试smart_batch_runner检测"
USE_RESULT_COLLECTOR="$USE_RESULT_COLLECTOR" STORAGE_FORMAT="$STORAGE_FORMAT" python3 -c "
import os
print('smart_batch_runner环境检测:')
print(f'  USE_RESULT_COLLECTOR: {os.environ.get(\"USE_RESULT_COLLECTOR\")}')

# 简单测试导入
try:
    from smart_batch_runner import run_batch_test_smart
    print('✅ smart_batch_runner导入成功')
except Exception as e:
    print(f'❌ 导入失败: {e}')
"

echo ""
echo "🎯 测试完成"