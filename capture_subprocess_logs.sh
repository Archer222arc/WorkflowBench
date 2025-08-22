#!/bin/bash

# 增强的子进程日志捕获脚本
# 用于捕获smart_batch_runner的详细输出

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}增强调试模式 - 多层次日志捕获${NC}"
echo -e "${CYAN}========================================${NC}"

# 创建日志目录
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="logs/debug_enhanced_${TIMESTAMP}"
mkdir -p "$LOG_DIR"

echo -e "${GREEN}✅ 创建日志目录: $LOG_DIR${NC}"

# 设置环境变量
export PYTHONFAULTHANDLER=1
export PYTHONUNBUFFERED=1
export PYTHONTRACEMALLOC=1  # 跟踪内存分配
export STORAGE_FORMAT="${STORAGE_FORMAT:-parquet}"
export DEBUG_LOG=true
export DEBUG_PROCESS_NUM=1

echo -e "${YELLOW}环境变量设置:${NC}"
echo "  STORAGE_FORMAT=$STORAGE_FORMAT"
echo "  DEBUG_LOG=$DEBUG_LOG"
echo "  DEBUG_PROCESS_NUM=$DEBUG_PROCESS_NUM"
echo ""

# 修改smart_batch_runner.py临时添加更多日志
echo -e "${CYAN}准备修改smart_batch_runner.py添加详细日志...${NC}"

# 备份原文件
cp smart_batch_runner.py smart_batch_runner.py.backup_debug

# 创建增强版smart_batch_runner
cat > smart_batch_runner_debug.py << 'EOF'
#!/usr/bin/env python3
"""
调试版本的smart_batch_runner - 添加详细日志
"""

import sys
import os
import logging
from pathlib import Path

# 设置详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'logs/smart_batch_debug_{os.getpid()}.log')
    ]
)

logger = logging.getLogger(__name__)

# 记录启动信息
logger.info("="*60)
logger.info(f"smart_batch_runner调试版本启动")
logger.info(f"PID: {os.getpid()}")
logger.info(f"命令行参数: {sys.argv}")
logger.info(f"环境变量:")
for key in ['STORAGE_FORMAT', 'DEBUG_LOG', 'PYTHONFAULTHANDLER']:
    logger.info(f"  {key}={os.environ.get(key, 'NOT SET')}")
logger.info("="*60)

# 导入原始模块
sys.path.insert(0, str(Path(__file__).parent))

# 劫持print函数
original_print = print
def debug_print(*args, **kwargs):
    """增强的print函数，同时记录到日志"""
    message = ' '.join(str(arg) for arg in args)
    logger.info(f"[PRINT] {message}")
    original_print(*args, **kwargs)

# 替换全局print
import builtins
builtins.print = debug_print

# 导入并运行原始代码
logger.info("导入原始smart_batch_runner模块...")
exec(open('smart_batch_runner.py').read())
EOF

# 创建测试脚本
cat > "$LOG_DIR/test_command.sh" << 'EOF'
#!/bin/bash
# 测试命令

# 使用调试版本替换原版本
mv smart_batch_runner.py smart_batch_runner.py.original
cp smart_batch_runner_debug.py smart_batch_runner.py

# 运行小规模测试
python smart_batch_runner.py \
    --model gpt-4o-mini \
    --prompt-types baseline \
    --difficulty easy \
    --task-types simple_task \
    --num-instances 1 \
    --max-workers 1 \
    --tool-success-rate 0.8 \
    --batch-commit \
    --checkpoint-interval 1 \
    --no-save-logs \
    --no-adaptive \
    --qps 5

# 恢复原版本
mv smart_batch_runner.py.original smart_batch_runner.py
EOF

chmod +x "$LOG_DIR/test_command.sh"

echo -e "${GREEN}运行测试...${NC}"

# 捕获所有输出
{
    echo "开始时间: $(date)"
    echo "================================"
    
    # 运行测试
    "$LOG_DIR/test_command.sh" 2>&1
    
    echo "================================"
    echo "结束时间: $(date)"
    
    # 收集日志
    echo ""
    echo "收集的日志文件:"
    ls -la logs/smart_batch_debug_*.log 2>/dev/null || echo "没有找到子进程日志"
    
    # 检查数据保存
    echo ""
    echo "数据保存检查:"
    python -c "
import json
from pathlib import Path
import pandas as pd

# 检查JSON
json_path = Path('pilot_bench_cumulative_results/master_database.json')
if json_path.exists():
    with open(json_path, 'r') as f:
        db = json.load(f)
    print(f'JSON数据库: {db[\"summary\"][\"total_tests\"]} 个测试')
    print(f'最后更新: {db.get(\"last_updated\", \"Unknown\")}')

# 检查Parquet
parquet_path = Path('pilot_bench_parquet_data/test_results.parquet')
if parquet_path.exists():
    df = pd.read_parquet(parquet_path)
    print(f'Parquet文件: {len(df)} 条记录')
    "
    
} | tee "$LOG_DIR/main.log"

# 清理
rm -f smart_batch_runner_debug.py
rm -f smart_batch_runner.py.backup_debug
rm -f logs/smart_batch_debug_*.log

echo ""
echo -e "${GREEN}✅ 调试完成！${NC}"
echo -e "${CYAN}日志保存在: $LOG_DIR${NC}"
echo ""
echo "主要日志文件:"
echo "  - $LOG_DIR/main.log (主输出)"
echo "  - $LOG_DIR/test_command.sh (测试脚本)"
echo ""
echo "要查看日志:"
echo "  cat $LOG_DIR/main.log"