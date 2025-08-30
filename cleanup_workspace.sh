#!/bin/bash

# 工作空间清理脚本
# 按照代码库规范整理和归档文件

echo "🧹 开始清理工作空间..."

# 创建时间戳
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
ARCHIVE_DIR="scripts/archive/cleanup_${TIMESTAMP}"

# 确保目录存在
mkdir -p "${ARCHIVE_DIR}/debug_scripts"
mkdir -p "${ARCHIVE_DIR}/test_scripts" 
mkdir -p "${ARCHIVE_DIR}/backup_files"
mkdir -p "${ARCHIVE_DIR}/temp_files"
mkdir -p "${ARCHIVE_DIR}/analysis_scripts"

echo "📁 创建归档目录: ${ARCHIVE_DIR}"

# 1. 归档调试脚本
echo "🔧 归档调试脚本..."
mv debug_none_error.py "${ARCHIVE_DIR}/debug_scripts/" 2>/dev/null
mv analyze_*.py "${ARCHIVE_DIR}/analysis_scripts/" 2>/dev/null
mv diagnose_*.py "${ARCHIVE_DIR}/debug_scripts/" 2>/dev/null
mv deep_*.py "${ARCHIVE_DIR}/analysis_scripts/" 2>/dev/null

# 2. 归档测试脚本
echo "🧪 归档临时测试脚本..."
mv test_conservative.sh "${ARCHIVE_DIR}/test_scripts/" 2>/dev/null
mv test_*_debug.* "${ARCHIVE_DIR}/test_scripts/" 2>/dev/null
mv test_*_simple.* "${ARCHIVE_DIR}/test_scripts/" 2>/dev/null

# 3. 归档备份文件
echo "💾 归档备份文件..."
mv *.backup* "${ARCHIVE_DIR}/backup_files/" 2>/dev/null
mv *.bak "${ARCHIVE_DIR}/backup_files/" 2>/dev/null

# 4. 归档修复脚本（已完成的）
echo "🔧 归档已完成的修复脚本..."
mv fix_concurrent_*.py "${ARCHIVE_DIR}/debug_scripts/" 2>/dev/null
mv fix_*_error*.py "${ARCHIVE_DIR}/debug_scripts/" 2>/dev/null

# 5. 归档验证脚本
echo "✅ 归档验证脚本..."
mv verify_*.py "${ARCHIVE_DIR}/test_scripts/" 2>/dev/null

# 6. 删除不必要的临时文件
echo "🗑️ 删除临时文件..."
# 删除旧的日志文件（超过7天的）
find logs/ -name "*.log" -mtime +7 -delete 2>/dev/null

# 删除临时配置文件
rm -f test_debug_config.txt 2>/dev/null
rm -f cleanup_plan.txt 2>/dev/null

# 删除空的结果目录
find . -name "*_results" -type d -empty -delete 2>/dev/null

# 7. 整理文档
echo "📚 整理文档..."
# 将分析文档移到docs目录
mkdir -p docs/analysis 2>/dev/null
mv *_ANALYSIS.md docs/analysis/ 2>/dev/null
mv *_SUMMARY.md docs/analysis/ 2>/dev/null

# 8. 清理构建文件
echo "🔨 清理构建缓存..."
# Python缓存
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null

# 9. 创建清理报告
REPORT_FILE="${ARCHIVE_DIR}/cleanup_report.md"
cat > "${REPORT_FILE}" << EOF
# 工作空间清理报告

**时间**: $(date)
**清理版本**: ${TIMESTAMP}

## 归档文件统计

### 调试脚本
\`\`\`
$(ls -la "${ARCHIVE_DIR}/debug_scripts/" | wc -l) 个文件
\`\`\`

### 测试脚本  
\`\`\`
$(ls -la "${ARCHIVE_DIR}/test_scripts/" | wc -l) 个文件
\`\`\`

### 备份文件
\`\`\`
$(ls -la "${ARCHIVE_DIR}/backup_files/" | wc -l) 个文件
\`\`\`

### 分析脚本
\`\`\`
$(ls -la "${ARCHIVE_DIR}/analysis_scripts/" | wc -l) 个文件
\`\`\`

## 清理动作

- ✅ 归档调试脚本到 debug_scripts/
- ✅ 归档测试脚本到 test_scripts/ 
- ✅ 归档备份文件到 backup_files/
- ✅ 归档分析脚本到 analysis_scripts/
- ✅ 删除7天以上的日志文件
- ✅ 删除临时配置文件
- ✅ 清理Python缓存
- ✅ 整理文档到docs/analysis/

## 建议

- 定期运行此脚本保持工作空间整洁
- 重要的调试脚本可以移回主目录使用
- 备份文件可以在确认无需时删除

EOF

echo "📋 生成清理报告: ${REPORT_FILE}"

echo "✨ 工作空间清理完成！"
echo "📁 归档位置: ${ARCHIVE_DIR}"
echo "📋 查看报告: ${REPORT_FILE}"

# 显示当前目录下剩余的Python文件
echo ""
echo "🐍 当前目录下剩余的Python文件:"
ls -1 *.py 2>/dev/null | head -10 || echo "无Python文件或已全部整理"

echo ""
echo "✅ 清理完成！工作空间现在更整洁了。"