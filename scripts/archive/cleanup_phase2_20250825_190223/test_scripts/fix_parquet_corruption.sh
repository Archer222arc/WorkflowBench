#!/bin/bash

echo "修复 Parquet 文件损坏问题"
echo "========================================"

# 备份现有的 Parquet 数据
if [ -d "pilot_bench_parquet_data" ]; then
    echo "备份现有 Parquet 数据..."
    mv pilot_bench_parquet_data pilot_bench_parquet_data.backup.$(date +%Y%m%d_%H%M%S)
fi

# 重新创建 Parquet 目录
echo "创建新的 Parquet 目录结构..."
mkdir -p pilot_bench_parquet_data/incremental

echo "✅ Parquet 目录已重置"
echo ""
echo "现在可以重新运行测试，警告应该消失了。"
echo "如果需要恢复旧数据，请查看 pilot_bench_parquet_data.backup.* 目录"