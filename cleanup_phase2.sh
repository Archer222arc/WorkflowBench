#!/bin/bash

# 第二阶段清理脚本 - 处理剩余的调试测试文件
echo "🧹 开始第二阶段清理..."

# 创建时间戳
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
ARCHIVE_DIR="scripts/archive/cleanup_phase2_${TIMESTAMP}"

# 确保目录存在
mkdir -p "${ARCHIVE_DIR}/debug_scripts"
mkdir -p "${ARCHIVE_DIR}/test_scripts" 
mkdir -p "${ARCHIVE_DIR}/analysis_scripts"
mkdir -p "${ARCHIVE_DIR}/temp_scripts"

echo "📁 创建归档目录: ${ARCHIVE_DIR}"

# 获取所有匹配的文件并逐一处理
echo "🔧 处理调试和测试脚本..."

# 方法1：使用find处理所有匹配文件
find . -maxdepth 1 -name "*.py" -type f | while read file; do
    filename=$(basename "$file")
    
    # 调试相关文件
    if [[ "$filename" =~ ^(debug|diagnose|analyze|deep|monitor).*\.py$ ]]; then
        echo "  📝 归档调试脚本: $filename"
        mv "$file" "${ARCHIVE_DIR}/debug_scripts/" 2>/dev/null || true
        continue
    fi
    
    # 测试相关文件
    if [[ "$filename" =~ ^(test|verify|check|validate).*\.py$ ]]; then
        echo "  🧪 归档测试脚本: $filename" 
        mv "$file" "${ARCHIVE_DIR}/test_scripts/" 2>/dev/null || true
        continue
    fi
    
    # 修复相关文件
    if [[ "$filename" =~ ^(fix|repair|patch).*\.py$ ]]; then
        echo "  🔧 归档修复脚本: $filename"
        mv "$file" "${ARCHIVE_DIR}/debug_scripts/" 2>/dev/null || true
        continue
    fi
    
    # 分析相关文件
    if [[ "$filename" =~ ^(analyze|analysis|report).*\.py$ ]]; then
        echo "  📊 归档分析脚本: $filename"
        mv "$file" "${ARCHIVE_DIR}/analysis_scripts/" 2>/dev/null || true
        continue
    fi
    
    # 临时/清理相关文件
    if [[ "$filename" =~ ^(temp|tmp|clean|migrate|sync|update|consolidate|optimize|enhance).*\.py$ ]]; then
        echo "  🗂️  归档临时脚本: $filename"
        mv "$file" "${ARCHIVE_DIR}/temp_scripts/" 2>/dev/null || true
        continue
    fi
done

# 方法2：处理shell脚本
find . -maxdepth 1 -name "*.sh" -type f | while read file; do
    filename=$(basename "$file")
    
    # 跳过主要的运行脚本
    if [[ "$filename" =~ ^(run_systematic_test|cleanup).*\.sh$ ]]; then
        continue
    fi
    
    # 测试相关shell脚本
    if [[ "$filename" =~ ^(test|debug|fix|run_5|demo).*\.sh$ ]]; then
        echo "  🧪 归档shell测试脚本: $filename"
        mv "$file" "${ARCHIVE_DIR}/test_scripts/" 2>/dev/null || true
        continue
    fi
done

# 3. 清理特定的文件模式
echo "🗑️  清理特定文件..."

# 清理JSON结果文件
find . -maxdepth 1 -name "*results*.json" -not -name "pilot_bench_cumulative_results" -delete 2>/dev/null || true
find . -maxdepth 1 -name "*test*.json" -delete 2>/dev/null || true
find . -maxdepth 1 -name "*config*.json" -not -path "./config/*" -delete 2>/dev/null || true

# 清理MD文档（保留重要文档）
find . -maxdepth 1 -name "*.md" -type f | while read file; do
    filename=$(basename "$file")
    
    # 保留重要的文档
    if [[ "$filename" =~ ^(README|CLAUDE|CHANGELOG|PROJECT_STRUCTURE|QUICK_REFERENCE)\.md$ ]]; then
        continue
    fi
    
    # 归档其他文档到docs/analysis
    echo "  📚 移动文档到docs/analysis: $filename"
    mkdir -p docs/analysis 2>/dev/null
    mv "$file" docs/analysis/ 2>/dev/null || true
done

# 4. 删除临时文件
echo "🗑️  删除临时文件..."
rm -f *.log 2>/dev/null || true
rm -f *.txt 2>/dev/null || true
rm -f *.patch 2>/dev/null || true

# 5. 清理空目录
echo "🗂️  清理空目录..."
find . -maxdepth 2 -type d -empty -delete 2>/dev/null || true

# 6. 创建清理报告
REPORT_FILE="${ARCHIVE_DIR}/phase2_cleanup_report.md"
cat > "${REPORT_FILE}" << EOF
# 第二阶段工作空间清理报告

**时间**: $(date)
**清理版本**: ${TIMESTAMP}

## 归档文件统计

### 调试脚本
\`\`\`
$(find "${ARCHIVE_DIR}/debug_scripts/" -name "*.py" 2>/dev/null | wc -l) 个Python文件
\`\`\`

### 测试脚本  
\`\`\`
$(find "${ARCHIVE_DIR}/test_scripts/" -name "*.*" 2>/dev/null | wc -l) 个文件
\`\`\`

### 分析脚本
\`\`\`
$(find "${ARCHIVE_DIR}/analysis_scripts/" -name "*.py" 2>/dev/null | wc -l) 个Python文件
\`\`\`

### 临时脚本
\`\`\`
$(find "${ARCHIVE_DIR}/temp_scripts/" -name "*.py" 2>/dev/null | wc -l) 个Python文件
\`\`\`

## 清理动作

- ✅ 使用find命令精确匹配和归档文件
- ✅ 归档调试脚本 (debug*, diagnose*, analyze*, monitor*)
- ✅ 归档测试脚本 (test*, verify*, check*, validate*)  
- ✅ 归档修复脚本 (fix*, repair*, patch*)
- ✅ 归档分析脚本 (analyze*, analysis*, report*)
- ✅ 归档临时脚本 (temp*, clean*, migrate*, sync*, update*)
- ✅ 移动文档到docs/analysis/
- ✅ 删除临时JSON文件
- ✅ 删除日志和补丁文件
- ✅ 清理空目录

## 当前目录状态

### 剩余Python文件数量
\`\`\`
$(find . -maxdepth 1 -name "*.py" | wc -l)
\`\`\`

### 剩余调试测试文件
\`\`\`
$(find . -maxdepth 1 -name "*.py" | grep -E "(debug|test|temp|fix|analyze)" | wc -l)
\`\`\`

## 建议

- 核心功能文件现在应该更加突出
- 如需要调试脚本，可以从归档目录恢复
- 定期运行清理脚本保持工作空间整洁

EOF

echo "📋 生成清理报告: ${REPORT_FILE}"

echo "✨ 第二阶段清理完成！"
echo "📁 归档位置: ${ARCHIVE_DIR}"

# 显示最终状态
echo ""
echo "📊 最终统计:"
echo "  Python文件总数: $(find . -maxdepth 1 -name "*.py" | wc -l)"
echo "  调试测试文件: $(find . -maxdepth 1 -name "*.py" | grep -E "(debug|test|temp|fix|analyze)" | wc -l || echo 0)"
echo "  核心功能文件占比: $(echo "scale=1; $(find . -maxdepth 1 -name "*.py" | wc -l) * 100 / 173" | bc)%"

echo ""
echo "✅ 工作空间清理完成！现在更加整洁了。"