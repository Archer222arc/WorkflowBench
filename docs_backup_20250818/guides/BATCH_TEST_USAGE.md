# 批测试框架使用说明

## 🚀 快速开始

所有并行功能已完全集成，支持Python和Bash两种方式

### 方式1: Bash脚本（推荐）

```bash
# 最简单 - 一键测试所有
./test_all.sh

# 快速功能验证
./quick_test.sh

# 完整批测试
./run_batch_test.sh -m gpt-4o-mini

# 测试所有主要模型
./run_batch_test.sh --all-models

# 并行测试多个模型
./run_parallel_test.sh

# 自定义配置
NUM_INSTANCES=50 MODELS="gpt-4o-mini qwen2.5-3b-instruct" ./test_all.sh
```

### 方式2: Python命令

```bash
# 测试单个prompt type
python smart_batch_runner.py \
  --model gpt-4o-mini \
  --prompt-types baseline \
  --task-types all \
  --num-instances 20

# 测试多个prompt types（自动并行）
python smart_batch_runner.py \
  --model gpt-4o-mini \
  --prompt-types baseline,cot,optimal \
  --task-types all \
  --num-instances 20 \
  --prompt-parallel

# 测试所有基本prompt types
python smart_batch_runner.py \
  --model qwen2.5-3b-instruct \
  --prompt-types all \
  --task-types all \
  --num-instances 20 \
  --prompt-parallel
```

## 🔑 核心特性

### 1. 智能API Key分配（IdealLab模型）
- `baseline` → API Key 1
- `cot` → API Key 2  
- `optimal` → API Key 3
- 自动实现3倍并发能力

### 2. 自动参数优化
- **Azure模型**: 50+ workers, 100+ QPS
- **IdealLab模型**: 5 workers, 10 QPS per prompt
- **User Azure**: 30 workers, 50 QPS

### 3. 多Prompt并行策略
- **Azure**: 所有prompt types同时运行
- **IdealLab**: 每个prompt type独立运行，使用不同API key

## 📊 性能提升

| 模式 | 时间 | 加速比 |
|-----|------|--------|
| 串行执行 | 6.4小时 | 1x |
| 单prompt并行 | 2.9小时 | 2.2x |
| 多prompt并行+3keys | <1小时 | 6x+ |

## 🛠️ 高级选项

```bash
# 参数说明
--prompt-parallel      # 启用多prompt并行（自动检测）
--provider-parallel    # 跨提供商并行（多模型）
--adaptive            # 自适应速率控制（默认开启）
--batch-commit        # 批量提交避免并发冲突
--checkpoint-interval # 检查点间隔（默认20）
--ai-classification   # AI错误分类（使用gpt-5-nano）
--no-save-logs       # 不保存详细日志
--silent             # 静默模式
```

## 📋 Bash脚本说明

| 脚本 | 用途 | 主要参数 |
|-----|------|---------|
| `test_all.sh` | 一键测试所有模型 | NUM_INSTANCES, MODELS |
| `quick_test.sh` | 快速功能验证 | 无参数 |
| `run_batch_test.sh` | 灵活的批测试 | -m MODEL, -p PROMPTS, -n NUM |
| `run_parallel_test.sh` | 多模型并行测试 | NUM_INSTANCES, TASK_TYPES |

### run_batch_test.sh 详细用法

```bash
# 查看帮助
./run_batch_test.sh --help

# 测试单个模型
./run_batch_test.sh -m gpt-4o-mini

# 指定prompt types
./run_batch_test.sh -m qwen2.5-3b-instruct -p baseline,cot,optimal

# 自定义实例数和难度
./run_batch_test.sh -m gpt-5-nano -n 50 -d medium

# 测试所有模型
./run_batch_test.sh --all-models

# 静默模式不保存日志
./run_batch_test.sh -m gpt-4o-mini --no-logs --silent
```

## 📝 常用场景

### 场景1: 快速测试配置
```bash
python smart_batch_runner.py \
  --model gpt-4o-mini \
  --prompt-types baseline \
  --task-types simple_task \
  --num-instances 2 \
  --no-save-logs
```

### 场景2: 完整测试所有prompt types
```bash
python smart_batch_runner.py \
  --model qwen2.5-3b-instruct \
  --prompt-types all \
  --task-types all \
  --num-instances 50 \
  --prompt-parallel \
  --adaptive
```

### 场景3: 批量测试多个模型
```bash
# 创建脚本循环测试
for model in gpt-4o-mini qwen2.5-3b-instruct gpt-5-nano; do
  python smart_batch_runner.py \
    --model $model \
    --prompt-types all \
    --task-types all \
    --num-instances 20 \
    --prompt-parallel &
done
wait
```

## 🔍 监控和调试

```bash
# 查看运行状态
ps aux | grep smart_batch_runner

# 查看最新日志
tail -f logs/batch_test_*.log

# 查看数据库统计
python -c "
import json
with open('pilot_bench_cumulative_results/master_database.json') as f:
    db = json.load(f)
    print(f'总测试数: {db[\"summary\"][\"total_tests\"]}')
"
```

## ✅ 验证集成

```bash
# 运行验证脚本
python verify_integration.py
```

---

**最后更新**: 2025-08-14
**版本**: 完全集成版