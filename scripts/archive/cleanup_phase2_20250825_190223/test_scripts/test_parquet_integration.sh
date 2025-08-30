#!/bin/bash

echo "================================================"
echo "     测试Parquet集成是否成功"
echo "================================================"

# 测试1：检查环境变量传递
echo -e "\n1. 测试环境变量传递..."
export STORAGE_FORMAT=parquet
output=$(python3 -c "
import os
print(f'Python收到的STORAGE_FORMAT: {os.environ.get(\"STORAGE_FORMAT\", \"未设置\")}')
")
echo "$output"

# 测试2：检查脚本修改
echo -e "\n2. 检查脚本是否正确修改..."
if grep -q "export STORAGE_FORMAT" run_systematic_test_final.sh; then
    echo "✅ 脚本包含export语句"
fi

if grep -q 'STORAGE_FORMAT="${STORAGE_FORMAT}"' run_systematic_test_final.sh; then
    echo "✅ Python调用包含环境变量传递"
fi

# 测试3：模拟运行测试
echo -e "\n3. 模拟测试运行（选择Parquet）..."
cat > test_input.txt << 'INPUT'
2
4
INPUT

# 运行脚本的前几步，看是否正确设置Parquet
timeout 5 bash -c '
export STORAGE_FORMAT=""
cat test_input.txt | ./run_systematic_test_final.sh 2>&1 | grep -E "(存储格式|PARQUET|Parquet)" | head -5
' || true

# 清理
rm -f test_input.txt

echo -e "\n================================================"
echo "测试完成！"
echo ""
echo "使用方法："
echo "  ./run_systematic_test_final.sh"
echo "  选择 2 即可自动使用Parquet格式"
echo "================================================"
