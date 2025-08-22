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
