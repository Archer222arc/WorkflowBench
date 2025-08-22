#!/bin/bash

# 项目组织脚本
# 按照代码管理规范整理项目结构

echo "================================================"
echo "         项目结构整理工具 v2.0"
echo "================================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 创建目录结构
create_directory_structure() {
    echo -e "${BLUE}📁 创建标准目录结构...${NC}"
    
    # 源代码目录
    mkdir -p src/{core,utils,managers,runners,testers,analyzers}
    
    # 配置目录
    mkdir -p config/{models,api,system}
    
    # 脚本目录
    mkdir -p scripts/{test,maintenance,analysis,deployment}
    
    # 文档目录
    mkdir -p docs/{api,guides,architecture,maintenance,reports}
    
    # 数据目录
    mkdir -p data/{raw,processed,results}
    
    # 测试目录
    mkdir -p tests/{unit,integration,performance}
    
    # 工具目录
    mkdir -p tools/{monitoring,debugging,optimization}
    
    echo -e "${GREEN}✓ 目录结构创建完成${NC}"
}

# 组织Python文件
organize_python_files() {
    echo -e "${BLUE}🐍 组织Python文件...${NC}"
    
    # 核心模块
    for file in batch_test_runner.py smart_batch_runner.py ultra_parallel_runner.py; do
        if [ -f "$file" ]; then
            cp "$file" src/runners/
            echo "  → $file -> src/runners/"
        fi
    done
    
    # 管理器
    for file in *_manager.py; do
        if [ -f "$file" ]; then
            cp "$file" src/managers/
            echo "  → $file -> src/managers/"
        fi
    done
    
    # 测试器
    for file in *_tester.py; do
        if [ -f "$file" ]; then
            cp "$file" src/testers/
            echo "  → $file -> src/testers/"
        fi
    done
    
    # 分析器
    for file in analyze_*.py view_*.py; do
        if [ -f "$file" ]; then
            cp "$file" src/analyzers/
            echo "  → $file -> src/analyzers/"
        fi
    done
    
    # 工具类
    for file in *_utils.py *_helper.py; do
        if [ -f "$file" ]; then
            cp "$file" src/utils/
            echo "  → $file -> src/utils/"
        fi
    done
    
    echo -e "${GREEN}✓ Python文件组织完成${NC}"
}

# 组织Shell脚本
organize_shell_scripts() {
    echo -e "${BLUE}🔧 组织Shell脚本...${NC}"
    
    # 测试脚本
    for file in test_*.sh run_*test*.sh; do
        if [ -f "$file" ]; then
            cp "$file" scripts/test/
            echo "  → $file -> scripts/test/"
        fi
    done
    
    # 维护脚本
    for file in *maintenance*.sh *cleanup*.sh archive_*.sh; do
        if [ -f "$file" ]; then
            cp "$file" scripts/maintenance/
            echo "  → $file -> scripts/maintenance/"
        fi
    done
    
    # 部署脚本
    for file in deploy_*.sh setup_*.sh install_*.sh; do
        if [ -f "$file" ]; then
            cp "$file" scripts/deployment/
            echo "  → $file -> scripts/deployment/"
        fi
    done
    
    echo -e "${GREEN}✓ Shell脚本组织完成${NC}"
}

# 组织文档
organize_documentation() {
    echo -e "${BLUE}📚 组织文档...${NC}"
    
    # API文档
    for file in *API*.md *api*.md; do
        if [ -f "$file" ]; then
            cp "$file" docs/api/
            echo "  → $file -> docs/api/"
        fi
    done
    
    # 指南文档
    for file in *GUIDE*.md *guide*.md *USAGE*.md; do
        if [ -f "$file" ]; then
            cp "$file" docs/guides/
            echo "  → $file -> docs/guides/"
        fi
    done
    
    # 架构文档
    for file in *ARCHITECTURE*.md *STRUCTURE*.md; do
        if [ -f "$file" ]; then
            cp "$file" docs/architecture/
            echo "  → $file -> docs/architecture/"
        fi
    done
    
    # 维护文档
    for file in *DEBUG*.md *MAINTENANCE*.md *ISSUES*.md; do
        if [ -f "$file" ]; then
            cp "$file" docs/maintenance/
            echo "  → $file -> docs/maintenance/"
        fi
    done
    
    echo -e "${GREEN}✓ 文档组织完成${NC}"
}

# 清理临时文件
cleanup_temp_files() {
    echo -e "${BLUE}🧹 清理临时文件...${NC}"
    
    # 创建临时文件目录
    mkdir -p .temp_cleanup
    
    # 移动临时文件
    for pattern in "*.tmp" "*.bak" "*.backup" "*~" ".*.swp"; do
        files=$(find . -maxdepth 1 -name "$pattern" 2>/dev/null)
        if [ ! -z "$files" ]; then
            for file in $files; do
                mv "$file" .temp_cleanup/
                echo "  → $file -> .temp_cleanup/"
            done
        fi
    done
    
    # 清理Python缓存
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
    find . -type f -name "*.pyc" -delete 2>/dev/null
    
    echo -e "${GREEN}✓ 临时文件清理完成${NC}"
}

# 生成项目结构文档
generate_structure_doc() {
    echo -e "${BLUE}📝 生成项目结构文档...${NC}"
    
    cat > PROJECT_STRUCTURE.md << 'EOFDOC'
# 项目结构说明

## 目录结构

\`\`\`
scale_up/
├── src/                    # 源代码目录
│   ├── core/              # 核心功能模块
│   ├── runners/           # 测试运行器
│   ├── managers/          # 管理器模块
│   ├── testers/           # 测试器模块
│   ├── analyzers/         # 分析器模块
│   └── utils/             # 工具函数
├── scripts/               # 脚本目录
│   ├── test/             # 测试脚本
│   ├── maintenance/      # 维护脚本
│   ├── analysis/         # 分析脚本
│   └── deployment/       # 部署脚本
├── config/               # 配置目录
│   ├── models/          # 模型配置
│   ├── api/             # API配置
│   └── system/          # 系统配置
├── docs/                 # 文档目录
│   ├── api/             # API文档
│   ├── guides/          # 使用指南
│   ├── architecture/    # 架构文档
│   ├── maintenance/     # 维护文档
│   └── reports/         # 测试报告
├── data/                 # 数据目录
│   ├── raw/             # 原始数据
│   ├── processed/       # 处理后数据
│   └── results/         # 结果数据
├── tests/                # 测试目录
│   ├── unit/            # 单元测试
│   ├── integration/     # 集成测试
│   └── performance/     # 性能测试
├── tools/                # 工具目录
│   ├── monitoring/      # 监控工具
│   ├── debugging/       # 调试工具
│   └── optimization/    # 优化工具
├── logs/                 # 日志目录
├── archive/              # 归档目录
└── pilot_bench_cumulative_results/  # 测试结果数据库
\`\`\`

## 核心模块说明

### Runners (运行器)
- \`batch_test_runner.py\` - 批量测试运行器
- \`smart_batch_runner.py\` - 智能批量运行器
- \`ultra_parallel_runner.py\` - 超并行运行器

### Managers (管理器)
- \`cumulative_test_manager.py\` - 累积测试管理器
- \`parquet_cumulative_manager.py\` - Parquet数据管理器
- \`model_config_manager.py\` - 模型配置管理器
- \`file_lock_manager.py\` - 文件锁管理器

### Testers (测试器)
- \`multi_model_batch_tester.py\` - 多模型批量测试器
- \`integrated_batch_tester.py\` - 集成批量测试器

### Analyzers (分析器)
- \`analyze_test_results.py\` - 测试结果分析
- \`view_test_progress.py\` - 测试进度查看
- \`analyze_5_3_test_coverage.py\` - 5.3测试覆盖分析

## 数据流向

\`\`\`
Input → Runners → Managers → Storage (JSON/Parquet)
                     ↓
              Analyzers → Reports
\`\`\`

## 使用说明

1. **运行测试**: 使用 \`scripts/test/\` 目录下的脚本
2. **查看进度**: 使用 \`src/analyzers/view_test_progress.py\`
3. **系统维护**: 使用 \`scripts/maintenance/\` 目录下的脚本
4. **生成报告**: 使用 \`src/analyzers/\` 目录下的分析工具

## 维护指南

详见 \`docs/maintenance/\` 目录下的文档。
EOFDOC
    
    echo -e "${GREEN}✓ 项目结构文档生成完成${NC}"
}

# 创建索引文件
create_index_files() {
    echo -e "${BLUE}📋 创建索引文件...${NC}"
    
    # Python包初始化文件
    for dir in src src/core src/runners src/managers src/testers src/analyzers src/utils; do
        if [ -d "$dir" ]; then
            touch "$dir/__init__.py"
        fi
    done
    
    # 创建README索引
    cat > src/README.md << 'EOFDOC'
# 源代码目录

## 模块索引

- **core/** - 核心功能模块
- **runners/** - 测试运行器
- **managers/** - 数据和配置管理器
- **testers/** - 测试执行器
- **analyzers/** - 结果分析器
- **utils/** - 工具函数库

## 导入示例

\`\`\`python
from src.runners.batch_test_runner import BatchTestRunner
from src.managers.cumulative_test_manager import CumulativeTestManager
from src.analyzers.view_test_progress import view_progress
\`\`\`
EOFDOC
    
    echo -e "${GREEN}✓ 索引文件创建完成${NC}"
}

# 生成组织报告
generate_report() {
    echo -e "${BLUE}📊 生成组织报告...${NC}"
    
    # 统计文件数量
    py_count=$(find . -maxdepth 1 -name "*.py" | wc -l)
    sh_count=$(find . -maxdepth 1 -name "*.sh" | wc -l)
    md_count=$(find . -maxdepth 1 -name "*.md" | wc -l)
    
    cat > ORGANIZATION_REPORT.md << EOFDOC
# 项目组织报告

生成时间: $(date '+%Y-%m-%d %H:%M:%S')

## 文件统计

- Python文件: $py_count 个
- Shell脚本: $sh_count 个
- Markdown文档: $md_count 个

## 已组织的目录

- src/ - 源代码
- scripts/ - 脚本
- config/ - 配置
- docs/ - 文档
- data/ - 数据
- tests/ - 测试
- tools/ - 工具

## 归档历史

- archive/ - 包含历史版本和调试脚本
- .temp_cleanup/ - 临时文件

## 下一步操作

1. 检查组织后的结构
2. 更新导入路径
3. 运行测试验证
4. 提交到版本控制

EOFDOC
    
    echo -e "${GREEN}✓ 组织报告生成完成${NC}"
}

# 主菜单
show_menu() {
    echo ""
    echo "请选择操作:"
    echo "1) 🏗️  完整组织（推荐）"
    echo "2) 📁  仅创建目录结构"
    echo "3) 🐍  仅组织Python文件"
    echo "4) 🔧  仅组织Shell脚本"
    echo "5) 📚  仅组织文档"
    echo "6) 🧹  仅清理临时文件"
    echo "7) 📝  生成结构文档"
    echo "8) ❌  退出"
    echo ""
}

# 执行完整组织
full_organize() {
    echo -e "${YELLOW}开始完整项目组织...${NC}"
    echo ""
    
    create_directory_structure
    echo ""
    organize_python_files
    echo ""
    organize_shell_scripts
    echo ""
    organize_documentation
    echo ""
    cleanup_temp_files
    echo ""
    generate_structure_doc
    echo ""
    create_index_files
    echo ""
    generate_report
    echo ""
    
    echo -e "${GREEN}✅ 项目组织完成！${NC}"
    echo ""
    echo "查看以下文件了解详情:"
    echo "  - PROJECT_STRUCTURE.md - 项目结构说明"
    echo "  - ORGANIZATION_REPORT.md - 组织报告"
}

# 主循环
while true; do
    show_menu
    read -p "选择 (1-8): " choice
    
    case $choice in
        1)
            full_organize
            break
            ;;
        2)
            create_directory_structure
            ;;
        3)
            organize_python_files
            ;;
        4)
            organize_shell_scripts
            ;;
        5)
            organize_documentation
            ;;
        6)
            cleanup_temp_files
            ;;
        7)
            generate_structure_doc
            ;;
        8)
            echo -e "${YELLOW}退出程序${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}无效选择，请重试${NC}"
            ;;
    esac
    
    echo ""
    read -p "按Enter继续..."
done
