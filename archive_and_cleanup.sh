#!/bin/bash

# 文件归档和整理脚本
# 按照代码管理规范进行分类归档

echo "============================================================"
echo "📦 开始归档和整理项目文件"
echo "============================================================"

# 设置颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 创建归档目录
echo -e "${BLUE}1. 创建归档目录结构...${NC}"
mkdir -p archive/{debug_scripts,test_scripts,fix_scripts,temp_files,analysis_scripts}
mkdir -p archive/logs_archive
mkdir -p archive/backup_files

# 归档调试脚本
echo -e "\n${BLUE}2. 归档调试脚本...${NC}"
for file in debug_*.py test_deepseek_api.py test_storage_consistency.py test_file_lock.py; do
    if [ -f "$file" ]; then
        mv "$file" archive/debug_scripts/ 2>/dev/null && echo "  ✓ $file"
    fi
done

# 归档测试脚本
echo -e "\n${BLUE}3. 归档测试脚本...${NC}"
for file in test_*.py api_connectivity_test.py simple_timeout_test.py; do
    if [ -f "$file" ]; then
        mv "$file" archive/test_scripts/ 2>/dev/null && echo "  ✓ $file"
    fi
done

# 归档修复脚本
echo -e "\n${BLUE}4. 归档修复脚本...${NC}"
for file in fix_*.py verify_system_fixes.py; do
    if [ -f "$file" ]; then
        mv "$file" archive/fix_scripts/ 2>/dev/null && echo "  ✓ $file"
    fi
done

# 归档分析脚本
echo -e "\n${BLUE}5. 归档分析脚本...${NC}"
for file in analyze_*.py view_*.py; do
    if [ -f "$file" ]; then
        mv "$file" archive/analysis_scripts/ 2>/dev/null && echo "  ✓ $file"
    fi
done

# 归档临时文件
echo -e "\n${BLUE}6. 归档临时文件...${NC}"
for file in *.bak *.backup temp_*.py tmp_*.py; do
    if [ -f "$file" ]; then
        mv "$file" archive/temp_files/ 2>/dev/null && echo "  ✓ $file"
    fi
done

# 归档旧日志（保留最近7天）
echo -e "\n${BLUE}7. 归档旧日志文件...${NC}"
find logs/ -name "*.log" -mtime +7 -exec mv {} archive/logs_archive/ \; 2>/dev/null
echo "  ✓ 归档7天前的日志"

# 压缩归档日志
if [ "$(ls -A archive/logs_archive 2>/dev/null)" ]; then
    tar -czf archive/logs_archive_$(date +%Y%m%d).tar.gz archive/logs_archive/*.log 2>/dev/null
    rm -f archive/logs_archive/*.log
    echo "  ✓ 压缩归档日志"
fi

# 清理空目录
echo -e "\n${BLUE}8. 清理空目录...${NC}"
find archive -type d -empty -delete 2>/dev/null
echo "  ✓ 已清理空目录"

# 生成归档报告
echo -e "\n${BLUE}9. 生成归档报告...${NC}"
cat > archive/ARCHIVE_REPORT_$(date +%Y%m%d).md << EOF
# 归档报告

**日期**: $(date +"%Y-%m-%d %H:%M:%S")
**执行者**: 自动归档脚本

## 归档统计

### 调试脚本 (archive/debug_scripts/)
$(ls -la archive/debug_scripts/*.py 2>/dev/null | wc -l) 个文件

### 测试脚本 (archive/test_scripts/)
$(ls -la archive/test_scripts/*.py 2>/dev/null | wc -l) 个文件

### 修复脚本 (archive/fix_scripts/)
$(ls -la archive/fix_scripts/*.py 2>/dev/null | wc -l) 个文件

### 分析脚本 (archive/analysis_scripts/)
$(ls -la archive/analysis_scripts/*.py 2>/dev/null | wc -l) 个文件

### 临时文件 (archive/temp_files/)
$(ls -la archive/temp_files/* 2>/dev/null | wc -l) 个文件

## 保留的核心文件

### 生产代码
- smart_batch_runner.py
- ultra_parallel_runner.py
- batch_test_runner.py
- cumulative_test_manager.py
- parquet_cumulative_manager.py
- enhanced_cumulative_manager.py

### 配置和文档
- CLAUDE.md
- README.md
- config/

### 数据文件
- pilot_bench_cumulative_results/
- pilot_bench_parquet_data/

## 清理操作
- 归档7天前的日志文件
- 删除空目录
- 压缩归档日志

---
归档完成时间: $(date +"%Y-%m-%d %H:%M:%S")
EOF

echo "  ✓ 生成归档报告: archive/ARCHIVE_REPORT_$(date +%Y%m%d).md"

# 显示归档结果
echo -e "\n${GREEN}============================================================${NC}"
echo -e "${GREEN}✅ 归档完成！${NC}"
echo -e "${GREEN}============================================================${NC}"

echo -e "\n归档统计:"
echo "  调试脚本: $(ls archive/debug_scripts/*.py 2>/dev/null | wc -l) 个"
echo "  测试脚本: $(ls archive/test_scripts/*.py 2>/dev/null | wc -l) 个"
echo "  修复脚本: $(ls archive/fix_scripts/*.py 2>/dev/null | wc -l) 个"
echo "  分析脚本: $(ls archive/analysis_scripts/*.py 2>/dev/null | wc -l) 个"

echo -e "\n${YELLOW}提示:${NC}"
echo "  • 归档文件保存在 archive/ 目录"
echo "  • 查看归档报告: cat archive/ARCHIVE_REPORT_$(date +%Y%m%d).md"
echo "  • 恢复文件: mv archive/{category}/file.py ."