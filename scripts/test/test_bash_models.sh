#!/bin/bash
# 测试run_systematic_test_final.sh中定义的所有模型API

echo "=================================================="
echo "测试Bash脚本中的所有模型API"
echo "=================================================="
echo ""

# 切换到项目根目录
cd "$(dirname "$0")/../.."

# 运行测试脚本
python scripts/test/api/test_api_detailed.py

echo ""
echo "测试完成！"
echo "日志文件位于: logs/api_test_*.log"