#!/bin/bash

# Parquet增量测试环境设置脚本
# 用于配置和启动基于Parquet的增量测试

echo "============================================================"
echo "🚀 Parquet增量测试环境设置"
echo "============================================================"
echo ""

# 设置颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. 检查Parquet数据文件
echo -e "${BLUE}📊 检查Parquet数据文件...${NC}"
if [ -f "pilot_bench_parquet_data/test_results.parquet" ]; then
    echo -e "${GREEN}✅ 主数据文件存在${NC}"
    
    # 显示数据统计
    python -c "
import pandas as pd
df = pd.read_parquet('pilot_bench_parquet_data/test_results.parquet')
print(f'  - 总记录数: {len(df)}')
print(f'  - 模型数: {df[\"model\"].nunique()}')
print(f'  - 成功率: {df[\"success\"].mean():.1%}')
"
else
    echo -e "${YELLOW}⚠️  主数据文件不存在，需要先转换${NC}"
    echo "运行: python json_to_parquet_converter.py"
    exit 1
fi

echo ""

# 2. 设置环境变量
echo -e "${BLUE}⚙️  设置环境变量...${NC}"
export STORAGE_FORMAT=parquet
echo -e "${GREEN}✅ STORAGE_FORMAT=parquet${NC}"

# 3. 创建增量目录（如果不存在）
mkdir -p pilot_bench_parquet_data/incremental
echo -e "${GREEN}✅ 增量目录已准备${NC}"

echo ""

# 4. 显示测试选项
echo -e "${BLUE}📝 可用的测试命令：${NC}"
echo ""
echo "1) 测试单个模型（增量更新）:"
echo "   python smart_batch_runner.py --model gpt-4o-mini --prompt-types baseline --difficulty easy --task-types simple_task --num-instances 10"
echo ""
echo "2) 批量测试多个模型:"
echo "   python smart_batch_runner.py --model gpt-4o-mini,DeepSeek-V3-0324 --prompt-types optimal --difficulty easy --task-types all --num-instances 20"
echo ""
echo "3) 使用超高并发（Azure）:"
echo "   python ultra_parallel_runner.py --model DeepSeek-V3-0324 --num-instances 100 --workers 50"
echo ""
echo "4) 查看Parquet数据:"
echo "   python view_parquet_data.py"
echo ""
echo "5) 合并增量数据到主文件:"
echo "   python -c \"from parquet_data_manager import ParquetDataManager; m=ParquetDataManager(); m.consolidate_incremental_data()\""
echo ""

# 5. 提供交互式选项
echo -e "${YELLOW}选择要执行的操作：${NC}"
echo "1) 运行小规模测试（验证环境）"
echo "2) 查看当前数据统计"
echo "3) 合并增量数据"
echo "4) 退出（手动运行命令）"
echo ""
read -p "请选择 [1-4]: " choice

case $choice in
    1)
        echo -e "\n${BLUE}▶ 运行小规模测试...${NC}"
        STORAGE_FORMAT=parquet python smart_batch_runner.py \
            --model gpt-4o-mini \
            --prompt-types baseline \
            --difficulty easy \
            --task-types simple_task \
            --num-instances 5 \
            --max-workers 5 \
            --no-save-logs
        
        echo -e "\n${GREEN}✅ 测试完成！${NC}"
        
        # 显示增量文件
        echo -e "\n${BLUE}📁 新增的增量文件：${NC}"
        ls -lh pilot_bench_parquet_data/incremental/*.parquet 2>/dev/null | tail -5
        ;;
        
    2)
        echo -e "\n${BLUE}📊 当前数据统计：${NC}"
        python -c "
from parquet_data_manager import ParquetDataManager
import pandas as pd

manager = ParquetDataManager()
manager.consolidate_incremental_data()

if manager.test_results_path.exists():
    df = pd.read_parquet(manager.test_results_path)
    
    print(f'\\n总体统计:')
    print(f'  总测试数: {len(df)}')
    print(f'  成功数: {df[\"success\"].sum()}')
    print(f'  成功率: {df[\"success\"].mean():.1%}')
    
    print(f'\\n按模型统计:')
    model_stats = df.groupby('model').agg({
        'success': ['count', 'mean']
    }).round(3)
    print(model_stats.head(10))
else:
    print('没有数据')
"
        ;;
        
    3)
        echo -e "\n${BLUE}🔄 合并增量数据...${NC}"
        python -c "
from parquet_data_manager import ParquetDataManager
manager = ParquetDataManager()
result = manager.consolidate_incremental_data()
if result:
    print('✅ 合并成功')
else:
    print('❌ 合并失败')
"
        ;;
        
    4)
        echo -e "\n${GREEN}环境已配置完成！${NC}"
        echo "你可以手动运行上述命令进行测试。"
        echo ""
        echo "记住设置环境变量："
        echo "export STORAGE_FORMAT=parquet"
        ;;
        
    *)
        echo -e "${RED}无效选择${NC}"
        ;;
esac

echo ""
echo "============================================================"
echo -e "${GREEN}🎉 Parquet增量测试环境已就绪！${NC}"
echo "============================================================"