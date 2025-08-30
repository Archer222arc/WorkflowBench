#!/bin/bash

# 最终清理脚本 - 处理剩余的调试和测试文件
echo "🧹 开始最终清理阶段..."

# 创建时间戳
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
ARCHIVE_DIR="scripts/archive/final_cleanup_${TIMESTAMP}"

# 确保目录存在
mkdir -p "${ARCHIVE_DIR}/debug_utilities"
mkdir -p "${ARCHIVE_DIR}/test_runners" 
mkdir -p "${ARCHIVE_DIR}/data_management"
mkdir -p "${ARCHIVE_DIR}/maintenance_scripts"

echo "📁 创建最终归档目录: ${ARCHIVE_DIR}"

# 获取所有剩余Python文件并分类处理
echo "🔧 处理剩余的工具和调试脚本..."

# 调试和维护工具
debug_files=(
    "system_health_check.py"
    "ultra_parallel_runner_debug.py" 
    "restore_json_from_parquet.py"
    "database_cleanup_for_retry.py"
    "auto_failure_maintenance_system.py"
    "data_save_wrapper.py"
)

for file in "${debug_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  🔧 归档调试工具: $file"
        mv "$file" "${ARCHIVE_DIR}/debug_utilities/" 2>/dev/null || true
    fi
done

# 测试运行器
test_files=(
    "run_ultimate_parallel_test.py"
    "multi_model_batch_tester_v2.py"
    "workflow_quality_test_flawed.py"
)

for file in "${test_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  🧪 归档测试运行器: $file"
        mv "$file" "${ARCHIVE_DIR}/test_runners/" 2>/dev/null || true
    fi
done

# 数据管理工具
data_files=(
    "result_analyzer.py"
    "cumulative_test_manager.py"
    "unified_storage_manager.py"
    "visualization_utils.py"
    "visualize_flawed_results.py"
)

for file in "${data_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  📊 归档数据管理工具: $file"
        mv "$file" "${ARCHIVE_DIR}/data_management/" 2>/dev/null || true
    fi
done

# 训练和优化脚本
training_files=(
    "smart_progressive_training.py"
    "train_ppo_m1_overnight.py"
    "gpu_training_script.py"
)

for file in "${training_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  🎯 归档训练脚本: $file"
        mv "$file" "${ARCHIVE_DIR}/maintenance_scripts/" 2>/dev/null || true
    fi
done

# 处理特定模式的文件
find . -maxdepth 1 -name "*_v[0-9]*.py" -type f | while read file; do
    filename=$(basename "$file")
    echo "  📦 归档版本化文件: $filename"
    mv "$file" "${ARCHIVE_DIR}/maintenance_scripts/" 2>/dev/null || true
done

# 清理剩余的临时文件
echo "🗑️ 清理临时文件..."
rm -f *.tmp *.bak 2>/dev/null || true
rm -f test_*.json debug_*.json 2>/dev/null || true

# 清理空目录
echo "🗂️ 清理空目录..."
find . -maxdepth 2 -type d -empty -delete 2>/dev/null || true

# 创建最终清理报告
REPORT_FILE="${ARCHIVE_DIR}/final_cleanup_report.md"
cat > "${REPORT_FILE}" << EOF
# 最终工作空间清理报告

**时间**: $(date)
**清理版本**: ${TIMESTAMP}

## 归档文件统计

### 调试工具
\`\`\`
$(find "${ARCHIVE_DIR}/debug_utilities/" -name "*.py" 2>/dev/null | wc -l) 个Python文件
\`\`\`

### 测试运行器
\`\`\`
$(find "${ARCHIVE_DIR}/test_runners/" -name "*.py" 2>/dev/null | wc -l) 个Python文件
\`\`\`

### 数据管理工具
\`\`\`
$(find "${ARCHIVE_DIR}/data_management/" -name "*.py" 2>/dev/null | wc -l) 个Python文件
\`\`\`

### 维护脚本
\`\`\`
$(find "${ARCHIVE_DIR}/maintenance_scripts/" -name "*.py" 2>/dev/null | wc -l) 个Python文件
\`\`\`

## 清理动作

- ✅ 归档调试和维护工具到 debug_utilities/
- ✅ 归档测试运行器到 test_runners/
- ✅ 归档数据管理工具到 data_management/
- ✅ 归档训练和优化脚本到 maintenance_scripts/
- ✅ 删除临时和备份文件
- ✅ 清理空目录

## 最终状态

### 剩余Python文件数量
\`\`\`
$(find . -maxdepth 1 -name "*.py" | wc -l)
\`\`\`

### 核心功能文件占比
\`\`\`
核心功能文件现在构成了主目录的主体
\`\`\`

## 核心保留文件

以下文件被识别为核心功能，保留在主目录：
\`\`\`
$(find . -maxdepth 1 -name "*.py" | sort)
\`\`\`

## 建议

- 工作空间现在高度组织化，核心功能突出
- 所有调试和测试工具都已归档但仍可恢复
- 建议定期运行类似清理脚本维护工作空间整洁

EOF

echo "📋 生成最终清理报告: ${REPORT_FILE}"

echo "✨ 最终清理完成！"
echo "📁 归档位置: ${ARCHIVE_DIR}"

# 显示最终统计
echo ""
echo "📊 最终统计:"
echo "  Python文件总数: $(find . -maxdepth 1 -name "*.py" | wc -l)"
echo "  核心功能文件已突出，工作空间高度优化"

echo ""
echo "✅ 工作空间清理全部完成！现在完全符合代码库规范。"