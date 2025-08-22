# PILOT-Bench 测试到报告完整流程

## 一、测试系统架构概述

### 1. 核心组件
- **unified_test_runner.py** - 统一测试运行器（支持累积结果）
- **mdp_workflow_generator.py** - MDP工作流生成器
- **interactive_executor.py** - 交互式执行器
- **flawed_workflow_generator.py** - 缺陷工作流生成器
- **visualization_utils.py** - 可视化和报告生成工具

### 2. 结果存储机制
- **累积结果目录**: `cumulative_test_results/`
  - `results_database.json` - 累积测试数据库
  - 自动合并新测试结果，避免重复测试
- **批次结果目录**: `multi_model_test_results/`
  - 按时间戳组织的单次测试结果
- **综合报告目录**: `comprehensive_test_results/`
  - 按模型组织的完整测试报告

## 二、完整测试流程

### 步骤1：准备测试环境
```bash
# 1. 检查环境状态
python check_test_environment.py

# 2. 验证任务库
python -c "from mdp_workflow_generator import MDPWorkflowGenerator; g = MDPWorkflowGenerator(); print(f'任务总数: {sum(len(tasks) for tasks in g.task_instances.values())}')"

# 3. 清理旧的测试进程（如果需要）
pkill -f "unified_test_runner"
```

### 步骤2：运行测试

#### 方案A：使用集成测试运行器（推荐）

**integrated_test_runner.py** 提供了所有测试功能的统一接口：

1. **微量测试（5个混合测试）**
```bash
python integrated_test_runner.py micro --model gpt-4o-mini --count 5
```

2. **批量测试（指定任务和提示类型）**
```bash
python integrated_test_runner.py batch \
    --model qwen2.5-3b-instruct \
    --task-types simple_task basic_task \
    --prompt-types baseline optimal \
    --count 3
```

3. **智能测试（自动选择最需要的测试）**
```bash
python integrated_test_runner.py smart --model gpt-4o-mini --count 20
```

4. **查看进度**
```bash
python integrated_test_runner.py progress --model qwen2.5-3b-instruct
```

5. **只生成工作流（用于调试）**
```bash
python integrated_test_runner.py generate --task-type simple_task --prompt-type baseline
```

#### 方案B：直接使用累积测试API
```python
# 手动运行测试并累积结果
from cumulative_test_manager import add_test_result

# 添加测试结果
add_test_result(
    model="qwen2.5-3b-instruct",
    task_type="simple_task",
    prompt_type="baseline",
    success=True,
    execution_time=2.5
)

# 查看进度
from cumulative_test_manager import check_progress
progress = check_progress("qwen2.5-3b-instruct")
print(f"完成率: {progress['completion_rate']:.1f}%")
```

3. **批量测试示例**
```python
# 创建批量测试脚本
cat > batch_micro_test.py << 'EOF'
from cumulative_test_manager import add_test_result
import random

model = "qwen2.5-3b-instruct"
task_types = ["simple_task", "basic_task", "data_pipeline"]
prompt_types = ["baseline", "optimal", "cot"]

# 运行10个随机测试
for i in range(10):
    task_type = random.choice(task_types)
    prompt_type = random.choice(prompt_types)
    success = random.random() > 0.3  # 70%成功率
    
    add_test_result(
        model=model,
        task_type=task_type,
        prompt_type=prompt_type,
        success=success,
        execution_time=random.uniform(1, 5)
    )
    print(f"测试 {i+1}: {task_type}/{prompt_type} - {'成功' if success else '失败'}")

# 查看进度
from cumulative_test_manager import check_progress
progress = check_progress(model)
print(f"\n总完成率: {progress['completion_rate']:.1f}%")
print(f"已完成: {progress['total_completed']}个测试")
EOF

python 批量微测.py
```

#### 方案B：自定义测试计划
```bash
# 使用预定义测试计划
python unified_test_runner.py custom --model qwen2.5-3b-instruct --plan-file test_plans/quick_test.json

# 或使用默认综合测试
python unified_test_runner.py custom --model qwen2.5-3b-instruct
```

#### 方案B：累积测试（100次重复）
```bash
# 运行累积测试，自动跳过已完成的测试
python unified_test_runner.py accumulate --model gpt-4o-mini --continue
```

#### 方案C：批量多模型测试
```bash
# 创建批量测试脚本
cat > 批量测试.sh << 'EOF'
#!/bin/bash
MODELS=(
    "qwen2.5-3b-instruct"
    "qwen2.5-7b-instruct"
    "qwen2.5-14b-instruct"
    "qwen2.5-32b-instruct"
    "qwen2.5-72b-instruct"
    "gpt-4o-mini"
    "claude37_sonnet"
)

for model in "${MODELS[@]}"; do
    echo "测试模型: $model"
    python unified_test_runner.py custom \
        --model "$model" \
        --plan-file test_plans/comprehensive_test.json
done
EOF

chmod +x 批量测试.sh
./批量测试.sh
```

### 步骤3：监控测试进度

```bash
# 实时查看累积进度
python view_cumulative_progress.py

# 查看最新测试日志
tail -f multi_model_test_results/latest/*/test_logs/*.txt

# 检查累积结果数据库
python -c "
import json
with open('cumulative_test_results/results_database.json') as f:
    db = json.load(f)
    for key, stats in db.items():
        if stats['total'] > 0:
            print(f'{key}: {stats['success']}/{stats['total']} = {stats['success']/stats['total']*100:.1f}%')
"
```

### 步骤4：生成报告

#### 4.1 生成单模型报告
```bash
python generate_single_model_report.py --model qwen2.5-3b-instruct
```

#### 4.2 生成多模型对比报告
```bash
python generate_comprehensive_report.py
```

#### 4.3 生成特定表格
```python
# 创建报告生成脚本
cat > 生成实验表格.py << 'EOF'
#!/usr/bin/env python3
import json
from pathlib import Path
import pandas as pd

# 加载累积结果
db_path = Path("cumulative_test_results/results_database.json")
with open(db_path) as f:
    database = json.load(f)

# 生成表4.1.2 任务类型分解性能表
task_types = ["basic_task", "simple_task", "data_pipeline", "api_integration", "multi_stage_pipeline"]
models = ["gpt-4o-mini", "qwen2.5-3b-instruct", "qwen2.5-7b-instruct"]

print("## 表4.1.2 任务类型分解性能表")
print("| 模型名称 | " + " | ".join([f"{t}成功率" for t in task_types]) + " |")
print("|" + "-|" * (len(task_types) + 1))

for model in models:
    row = [model]
    for task_type in task_types:
        key_pattern = f"{model}_{task_type}_"
        total = success = 0
        for key, stats in database.items():
            if key.startswith(key_pattern):
                total += stats["total"]
                success += stats["success"]
        rate = f"{success/total*100:.1f}%" if total > 0 else "N/A"
        row.append(rate)
    print("| " + " | ".join(row) + " |")

# 生成表4.3.1 缺陷工作流适应性表
flaw_types = ["sequence_disorder", "tool_misuse", "parameter_error", "missing_step", 
              "redundant_operations", "logical_inconsistency", "semantic_drift"]

print("\n## 表4.3.1 缺陷工作流适应性表")
print("| 模型名称 | " + " | ".join([f"{f}成功率" for f in flaw_types]) + " |")
print("|" + "-|" * (len(flaw_types) + 1))

for model in models[:3]:  # 只测试前3个模型
    row = [model]
    for flaw in flaw_types:
        key_pattern = f"{model}_.*_flawed_{flaw}"
        total = success = 0
        for key, stats in database.items():
            if flaw in key and model in key:
                total += stats["total"]
                success += stats["success"]
        rate = f"{success/total*100:.1f}%" if total > 0 else "N/A"
        row.append(rate)
    print("| " + " | ".join(row) + " |")
EOF

python 生成实验表格.py > 实验结果表格.md
'''
```

### 步骤5：结果验证与分析

```bash
# 1. 验证数据完整性
python verify_test_completeness.py

# 2. 生成可视化图表
python generate_visualizations.py

# 3. 导出Excel报表
python export_to_excel.py
```

## 三、批测试接口说明

### 1. 累积测试管理系统 API (cumulative_test_manager.py)

#### 核心类：CumulativeTestManager
```python
from cumulative_test_manager import CumulativeTestManager, TestRecord

# 创建管理器实例
manager = CumulativeTestManager()
```

#### 主要方法：

**1) add_test_result(record: TestRecord) -> bool**
```python
# 添加单个测试结果
record = TestRecord(
    model="qwen2.5-3b-instruct",
    task_type="simple_task",
    prompt_type="baseline",
    difficulty="easy",
    success=True,
    partial_success=False,
    execution_time=2.5,
    error_message=None,
    is_flawed=False,
    flaw_type=None
)
manager.add_test_result(record)
```

**2) get_test_count(...) -> int**
```python
# 获取特定组合的已测试次数
count = manager.get_test_count(
    model="qwen2.5-3b-instruct",
    task_type="simple_task",
    prompt_type="baseline",
    difficulty="easy",
    flaw_type=None  # 如果是缺陷测试，填入缺陷类型
)
```

**3) needs_more_tests(...) -> bool**
```python
# 检查是否需要更多测试
needs_more = manager.needs_more_tests(
    model="qwen2.5-3b-instruct",
    task_type="simple_task",
    prompt_type="baseline",
    target_count=100  # 目标测试次数
)
```

**4) get_remaining_tests(model, target_count) -> List[Dict]**
```python
# 获取所有需要补充的测试组合
remaining = manager.get_remaining_tests("qwen2.5-3b-instruct", target_count=100)
for test in remaining:
    print(f"{test['task_type']} + {test['prompt_type']}: 需要{test['needed']}个")
```

**5) get_progress_report(model) -> Dict**
```python
# 生成进度报告
report = manager.get_progress_report("qwen2.5-3b-instruct")
```

**6) export_for_report_generation() -> Dict**
```python
# 导出数据用于生成报告
export_data = manager.export_for_report_generation()
```

### 2. 便捷函数

**add_test_result() - 快速添加测试结果**
```python
from cumulative_test_manager import add_test_result

# 正常测试
add_test_result(
    model="qwen2.5-3b-instruct",
    task_type="simple_task",
    prompt_type="baseline",
    success=True,
    execution_time=2.5,
    difficulty="easy"
)

# 缺陷测试
add_test_result(
    model="qwen2.5-3b-instruct",
    task_type="simple_task",
    prompt_type="baseline",
    success=False,
    execution_time=3.2,
    is_flawed=True,
    flaw_type="tool_misuse",
    error_message="工具调用失败"
)
```

**check_progress() - 检查进度**
```python
from cumulative_test_manager import check_progress

progress = check_progress("qwen2.5-3b-instruct", target_count=100)
print(f"完成率: {progress['completion_rate']:.1f}%")
print(f"剩余测试: {progress['total_needed']}个")
```

### 3. 数据结构

#### TestRecord 数据类
```python
@dataclass
class TestRecord:
    # 必填字段
    model: str              # 模型名称
    task_type: str          # 任务类型
    prompt_type: str        # 提示类型
    
    # 可选字段
    difficulty: str = "easy"        # 难度级别
    success: bool = False           # 是否成功
    partial_success: bool = False   # 是否部分成功
    execution_time: float = 0.0     # 执行时间
    error_message: Optional[str] = None  # 错误信息
    
    # 缺陷测试相关
    is_flawed: bool = False         # 是否为缺陷测试
    flaw_type: Optional[str] = None # 缺陷类型
    
    # 元数据
    timestamp: str = ""             # 时间戳（自动生成）
    task_id: Optional[str] = None   # 任务ID
    session_id: Optional[str] = None # 会话ID
    test_instance: int = 0          # 测试实例编号（自动分配）
```

### 4. 批量测试示例

```python
# 批量运行测试并累积结果
def run_batch_tests(model: str, batch_size: int = 10):
    manager = CumulativeTestManager()
    
    # 获取需要补充的测试
    remaining = manager.get_remaining_tests(model, target_count=100)
    
    # 按批次运行
    for i in range(0, min(batch_size, len(remaining))):
        test = remaining[i]
        
        # 运行实际测试（这里是伪代码）
        result = run_actual_test(
            model=model,
            task_type=test['task_type'],
            prompt_type=test['prompt_type'],
            is_flawed=test['is_flawed'],
            flaw_type=test['flaw_type']
        )
        
        # 添加结果
        add_test_result(
            model=model,
            task_type=test['task_type'],
            prompt_type=test['prompt_type'],
            success=result['success'],
            execution_time=result['time'],
            is_flawed=test['is_flawed'],
            flaw_type=test['flaw_type']
        )
    
    # 保存数据库
    manager.save_database()
```

### 5. 与unified_test_runner集成

```python
# 在unified_test_runner.py中使用累积系统
from cumulative_test_manager import CumulativeTestManager, TestRecord

class UnifiedTestRunner:
    def __init__(self):
        self.cum_manager = CumulativeTestManager()
    
    def run_test_and_accumulate(self, config):
        # 运行测试
        results = self.run_test_batch(config)
        
        # 累积结果
        for result in results:
            record = TestRecord(
                model=result.model,
                task_type=result.task_type,
                prompt_type=result.prompt_type,
                success=result.success,
                execution_time=result.execution_time
            )
            self.cum_manager.add_test_result(record)
        
        # 保存
        self.cum_manager.save_database()
```

### 6. 累积测试机制说明

#### 工作原理
- 所有测试结果自动保存到 `pilot_bench_cumulative_results/master_database.json`
- 每个测试组合（模型+任务类型+提示类型+缺陷类型）作为唯一键
- 支持中断续测，自动跳过已完成的测试
- 自动合并多次运行的结果

### 2. 数据结构
```json
{
  "qwen2.5-3b-instruct_simple_task_baseline": {
    "total": 100,
    "success": 85,
    "partial_success": 10,
    "results": [
      {
        "timestamp": "2024-08-04T10:30:00",
        "execution_time": 2.5,
        "success": true,
        ...
      }
    ]
  }
}
```

### 3. 累积策略
- **继续测试**: 使用 `--continue` 参数自动检测并继续未完成的测试
- **合并结果**: 使用 `--merge` 参数合并新旧结果
- **重置测试**: 删除对应的键值对可重新测试特定组合

## 四、报告生成模板

### 1. 综合报告结构
```
# PILOT-Bench 综合测试报告

## 1. 测试概述
- 测试时间范围
- 测试模型列表
- 测试规模统计

## 2. 整体性能评估
### 表4.1.1 主要性能指标对比表
### 表4.1.2 任务类型分解性能表

## 3. 模型规模效应分析
### 表4.2.1 Qwen系列规模效应表

## 4. Robustness评估
### 表4.3.1 缺陷工作流适应性表
### 表4.3.2 工具可靠性敏感性表

## 5. 提示类型敏感性
### 表4.4.1 不同提示类型性能表

## 6. 错误模式分析
### 表4.5.1 系统性错误分类表

## 7. 详细结果附录
```

### 2. 自动化报告生成
```python
# 使用 comprehensive_report_generator.py
python comprehensive_report_generator.py \
    --input cumulative_test_results/results_database.json \
    --output comprehensive_report.md \
    --format markdown \
    --include-charts
```

## 五、最佳实践建议

### 1. 测试策略
- 先用少量实例（如5个）验证配置
- 使用累积模式进行大规模测试
- 定期备份 `results_database.json`

### 2. 性能优化
- 使用 `--parallel` 参数控制并发数
- 对于大模型，减少并发避免OOM
- 使用 `--no-save-logs` 减少IO开销

### 3. 故障恢复
- 测试中断后使用 `--continue` 恢复
- 检查 `results_database.json.tmp` 恢复未保存的结果
- 使用 `view_cumulative_progress.py` 检查进度

### 4. 结果管理
- 定期归档旧的测试结果
- 使用Git管理报告版本
- 保留原始数据用于后续分析

## 六、常见问题解决

### Q1: 测试卡住怎么办？
```bash
# 1. 查看进程
ps aux | grep unified_test_runner

# 2. 强制终止
pkill -f unified_test_runner

# 3. 继续测试
python unified_test_runner.py accumulate --model <model> --continue
```

### Q2: 如何验证结果准确性？
```bash
# 检查特定测试的详细日志
find multi_model_test_results -name "*<model>*<task>*.txt" | head -5 | xargs less
```

### Q3: 如何合并多次测试结果？
```bash
# 自动合并（默认行为）
python unified_test_runner.py accumulate --merge

# 手动合并
python merge_test_results.py --input dir1 dir2 --output merged_results
```

---

**文档创建时间**: 2025-08-05
**版本**: 1.0
**维护状态**: ✅ 活跃维护中