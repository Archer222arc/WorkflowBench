# 并行批测试使用指南（完全集成版）

## 🎯 所有功能已完全集成到smart_batch_runner.py

### ✅ 集成的核心功能
1. **多API Key池管理** - 3个IdealLab API keys智能分配
2. **Prompt类型API Key映射** - baseline/cot/optimal分别使用不同keys
3. **多Prompt并行** - 支持baseline,cot,optimal或all同时运行
4. **Provider级别并行** - Azure/IdealLab/User Azure并行执行
5. **自动参数调整** - 根据模型自动设置并发参数

## 🚀 核心发现与优化策略

### 速率限制发现
1. **Azure**: 模型级别限制，高并发能力（50+）
2. **IdealLab**: 模型级别限制，每个模型约10个并发
3. **多API Key**: 3个IdealLab keys可实现5倍加速

### 最优并行策略（已集成到框架）
- **Azure模型**: 自动使用50+ workers和100+ QPS
- **IdealLab模型**: 自动分配不同API key给不同prompt types
- **User Azure**: 独立endpoint并行执行

## 📚 使用方法

### 🔥 统一使用方式（所有功能已集成）

#### 基本使用（单prompt）
```bash
# IdealLab模型 - 自动使用多API Key
python smart_batch_runner.py \
  --model qwen2.5-3b-instruct \
  --prompt-types baseline \
  --task-types all \
  --num-instances 20 \
  --adaptive

# Azure模型 - 自动使用高并发
python smart_batch_runner.py \
  --model gpt-4o-mini \
  --prompt-types baseline \
  --task-types all \
  --num-instances 50 \
  --adaptive
```

#### 多Prompt Types并行（集成功能）
```bash
# Azure模型 - 所有prompt types同时并行
python smart_batch_runner.py \
  --model gpt-4o-mini \
  --prompt-types baseline,cot,optimal \
  --task-types all \
  --num-instances 20 \
  --prompt-parallel  # 启用prompt并行

# 或使用all参数测试所有基本prompt types
python smart_batch_runner.py \
  --model gpt-4o-mini \
  --prompt-types all \
  --task-types all \
  --num-instances 20 \
  --prompt-parallel

# IdealLab模型 - 每个prompt type使用不同API key并行
python smart_batch_runner.py \
  --model qwen2.5-3b-instruct \
  --prompt-types baseline,cot,optimal \
  --task-types all \
  --num-instances 20 \
  --prompt-parallel  # 3个prompt types使用3个不同keys并行
```

**并行策略说明**：
- **Azure模型**: 所有prompt types直接并行，使用高并发参数（50+ workers）
- **IdealLab模型**: 
  - baseline → API Key 1 (后4位: f4bb)
  - cot → API Key 2 (后4位: e77b)
  - optimal → API Key 3 (后4位: c3b9)
  - 3个prompt types可以同时并行运行，互不干扰

#### Provider并行模式
```bash
# 启用provider级别并行（跨提供商并行执行）
python smart_batch_runner.py \
  --model gpt-4o-mini \
  --prompt-types baseline \
  --task-types all \
  --num-instances 20 \
  --provider-parallel  # 启用provider并行
```

#### API Key分配策略
框架会自动为IdealLab模型分配API keys：
- `baseline` → 使用第1个API key
- `cot` → 使用第2个API key  
- `optimal` → 使用第3个API key
- `flawed_*` → 轮询使用所有keys

#### 自动参数调整
框架会根据模型自动调整并发参数：
```python
# IdealLab模型（qwen, llama-4-scout, o1等）
- Adaptive模式: workers=5, QPS=10
- 非Adaptive: workers=3, QPS=5

# Azure模型（deepseek, llama-3.3, gpt-4o-mini, gpt-5等）
- Adaptive模式: workers=50+, QPS=100+
- 非Adaptive: workers=80, QPS=150
```

### 1. Bash脚本（用于批量测试）

#### 简化版（推荐）
```bash
# 使用默认配置
./run_smart_parallel.sh

# 自定义配置
./run_smart_parallel.sh 20 easy all  # 20个实例，easy难度，所有任务

# 后台运行
nohup ./run_smart_parallel.sh > test.log 2>&1 &
```

#### 完整版（更多控制）
```bash
# 编辑配置
vim run_parallel_batch_test.sh  # 修改模型列表等

# 运行
./run_parallel_batch_test.sh

# 只测试特定组
NUM_INSTANCES=10 ./run_parallel_batch_test.sh
```

### 2. Python脚本（推荐用于完整测试）

#### 终极并行测试
```bash
# 测试所有模型
python run_ultimate_parallel_test.py

# 自定义参数
python run_ultimate_parallel_test.py \
    --num-instances 50 \
    --difficulty medium \
    --task-types all

# 只测试特定组
python run_ultimate_parallel_test.py --test-group idealab
```

#### 使用provider并行运行器
```python
from provider_parallel_runner import ProviderParallelRunner
from batch_test_runner import TestTask

# 创建任务
tasks = []
for model in ['gpt-4o-mini', 'qwen2.5-3b-instruct', 'DeepSeek-V3-671B']:
    for prompt in ['baseline', 'cot', 'optimal']:
        task = TestTask(
            model=model,
            task_type='simple_task',
            prompt_type=prompt,
            difficulty='easy'
        )
        tasks.append(task)

# 运行
runner = ProviderParallelRunner()
results, stats = runner.run_parallel_by_provider(tasks)
```

### 3. 使用smart_batch_runner的provider并行模式

```bash
# 启用provider并行优化
python smart_batch_runner.py \
    --model gpt-4o-mini \
    --prompt-types baseline \
    --task-types all \
    --num-instances 20 \
    --provider-parallel  # 关键标志
```

## 🎯 并行策略详解

### Azure模型并行策略
```bash
# Azure支持高并发，所有prompt同时测试
for prompt in baseline cot optimal flawed_*; do
    run_test gpt-4o-mini $prompt &
done
wait
```

### IdealLab模型并行策略
```bash
# 使用3个API keys分配给不同prompt types
baseline -> API_KEY_1
cot      -> API_KEY_2  
optimal  -> API_KEY_3
flawed_* -> 轮询使用3个keys
```

### DeepSeek并行策略
```bash
# User Azure和IdealLab版本可同时测试
run_test DeepSeek-V3-0324 baseline &  # User Azure版本
run_test DeepSeek-V3-671B baseline &  # IdealLab版本
```

## 📊 性能对比

| 策略 | 预计时间 | 说明 |
|-----|---------|------|
| 串行执行 | 6.4小时 | 传统方式 |
| 单Key并行 | 2.9小时 | 模型级别并行 |
| 3Keys并行 | <1小时 | 最优策略 |

## 🔧 高级配置

### 环境变量
```bash
# 覆盖IdealLab API Key
export IDEALAB_API_KEY_OVERRIDE="your_key"

# 设置并发数
export MAX_WORKERS=20
```

### 修改API Key分配
编辑脚本中的key分配逻辑：
```python
# run_ultimate_parallel_test.py
self.idealab_keys = [
    "key1",  # 用于baseline
    "key2",  # 用于cot
    "key3"   # 用于optimal
]
```

### 调整并发参数
```python
# provider_parallel_runner.py
self.provider_configs = {
    'azure': {'max_parallel': 50},      # Azure高并发
    'user_azure': {'max_parallel': 30}, # User Azure中等
    'idealab': {'max_parallel_per_model': 8}  # 每个模型8并发
}
```

## 📈 监控与日志

### 实时监控
```bash
# 查看运行中的任务
watch -n 5 'pgrep -f smart_batch_runner.py | wc -l'

# 查看日志
tail -f logs/parallel_*/azure_tasks.log

# 统计进度
grep "✅.*成功" logs/parallel_*/*.log | wc -l
```

### 查看结果
```bash
# 查看数据库统计
python -c "
import json
with open('pilot_bench_cumulative_results/master_database.json') as f:
    db = json.load(f)
print(f'Total tests: {db[\"summary\"][\"total_tests\"]}')
"
```

## 🚨 常见问题

### Q: IdealLab速率限制错误
A: 降低每个模型的并发数，或使用更多API Keys轮询

### Q: 内存不足
A: 减少MAX_WORKERS或使用进程池代替线程池

### Q: 某些模型超时
A: 增加timeout参数，或将大模型单独测试

## 🔍 验证集成功能

### 运行集成测试
```bash
# 验证所有集成功能
python test_integrated_parallel.py

# 单独测试API Key分配
python -c "
from api_client_manager import APIClientManager
m = APIClientManager()
for pt in ['baseline', 'cot', 'optimal']:
    c = m.get_client('qwen2.5-3b-instruct', pt)
    print(f'{pt}: key后4位={c.api_key_used[-4:]}')
"
```

### 监控API Key使用
```bash
# 查看哪个API key正在使用
grep "api_key_used" logs/batch_test_*.log | tail -5

# 统计每个key的使用次数
grep "使用第" logs/debug_*.log | sort | uniq -c
```

## 💡 最佳实践

1. **先测试小批量**确认配置正确
2. **使用nohup**避免连接断开影响
3. **定期检查日志**及时发现问题
4. **按优先级测试**重要模型先测
5. **保存中间结果**使用--checkpoint-interval
6. **使用框架集成模式**自动获得最优配置

## 📝 示例工作流

### 基础测试流程
```bash
# 1. 快速测试配置
./run_smart_parallel.sh 2 easy simple_task

# 2. 查看结果
grep "成功\|失败" logs/parallel_*/gpt-4o-mini*.log

# 3. 如果正常，运行完整测试
nohup python run_ultimate_parallel_test.py > full_test.log 2>&1 &

# 4. 监控进度
tail -f full_test.log

# 5. 生成报告
python generate_test_report.py
```

### 🚀 综合并行测试（最大化速度）
```bash
# 测试单个模型的所有prompt types
python smart_batch_runner.py \
  --model qwen2.5-3b-instruct \
  --prompt-types all \
  --task-types all \
  --num-instances 20 \
  --prompt-parallel \
  --adaptive

# 或运行综合测试脚本（同时测试多个模型）
./run_comprehensive_parallel_test.sh

# 自定义参数
NUM_INSTANCES=50 TASK_TYPES=all ./run_comprehensive_parallel_test.sh
```

### 监控并行执行
```bash
# 查看正在运行的并行任务
ps aux | grep smart_batch_runner | grep -v grep

# 实时监控API key使用
watch -n 2 'grep "api_key_used" logs/batch_test_*.log | tail -10'

# 查看各prompt type进度
for pt in baseline cot optimal; do 
  echo "$pt: $(grep "$pt.*成功" logs/*.log | wc -l) 完成"
done
```

---

## 📊 集成效果总结

### 性能提升
- **串行执行**: 6.4小时（传统方式）
- **单Key并行**: 2.9小时（2.2倍加速）
- **3Keys集成**: <1小时（6倍以上加速）

### 集成优势
1. **零配置**: 框架自动识别模型并优化参数
2. **智能分配**: API keys根据prompt type自动分配
3. **Provider并行**: 不同提供商的模型并行执行
4. **自适应调整**: 根据响应动态调整并发参数

**最后更新**: 2025-08-14
**集成状态**: ✅ 完成
**预期性能**: 6.4小时 → <1小时（6倍以上加速）