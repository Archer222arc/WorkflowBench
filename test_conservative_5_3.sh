#!/bin/bash

# 测试5.3缺陷工作流的保守模式
# 这个脚本用于验证保守模式能否避免系统过载问题

echo "====================================="
echo "测试5.3缺陷工作流 - 保守并发模式"
echo "====================================="
echo ""
echo "测试配置:"
echo "- 使用保守并发模式（--conservative）"
echo "- 模型串行执行，避免系统过载"
echo "- 每个模型内部仍使用适度并行"
echo ""

# 设置环境变量
export STORAGE_FORMAT="json"
export USE_RESULT_COLLECTOR="true"
export CUSTOM_WORKERS=10  # 限制每个模型的并发数
export MAX_CONCURRENT_PROCESSES=5  # 限制总进程数

echo "开始测试5.3缺陷工作流..."
echo "使用参数: --conservative --phase 5.3 --workers 10"
echo ""

# 运行测试
./run_systematic_test_final.sh --conservative --phase 5.3 --workers 10

echo ""
echo "测试完成！"
echo ""
echo "请检查："
echo "1. 是否所有模型都成功完成测试"
echo "2. 系统是否保持稳定（没有崩溃）"
echo "3. 测试结果是否正确保存"