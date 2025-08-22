# PILOT-Bench 累积测试API使用指南

## 快速开始

### 1. 最简单的使用方式

```python
from 累积测试管理系统 import add_test_result

# 添加一个测试结果
add_test_result(
    model="qwen2.5-3b-instruct",
    task_type="simple_task", 
    prompt_type="baseline",
    success=True,
    execution_time=2.5
)
```

就这么简单！结果会自动累积到数据库中。

### 2. 查看进度

```python
from 累积测试管理系统 import check_progress

# 查看模型的测试进度
progress = check_progress("qwen2.5-3b-instruct", target_count=100)
print(f"完成率: {progress['completion_rate']:.1f}%")
print(f"还需要: {progress['total_needed']}个测试")
```

## 完整API参考

### CumulativeTestManager 类

```python
from 累积测试管理系统 import CumulativeTestManager, TestRecord

manager = CumulativeTestManager()
```

#### 方法列表

| 方法名 | 功能 | 参数 | 返回值 |
|--------|------|------|--------|
| `add_test_result(record)` | 添加测试结果 | TestRecord对象 | bool |
| `get_test_count(...)` | 获取已测试次数 | model, task_type, prompt_type, difficulty, flaw_type | int |
| `needs_more_tests(...)` | 检查是否需要更多测试 | 同上 + target_count | bool |
| `get_remaining_tests(model, target)` | 获取剩余测试列表 | model, target_count | List[Dict] |
| `get_progress_report(model)` | 生成进度报告 | model (可选) | Dict |
| `export_for_report_generation()` | 导出报告数据 | 无 | Dict |
| `save_database()` | 手动保存数据库 | 无 | 无 |

### TestRecord 数据结构

```python
@dataclass
class TestRecord:
    # === 必填字段 ===
    model: str              # 模型名称，如 "qwen2.5-3b-instruct"
    task_type: str          # 任务类型: simple_task, basic_task, data_pipeline, 
                           # api_integration, multi_stage_pipeline
    prompt_type: str        # 提示类型: baseline, optimal, cot, expert, creative
    
    # === 结果字段 ===
    success: bool = False           # 是否完全成功
    partial_success: bool = False   # 是否部分成功
    execution_time: float = 0.0     # 执行时间（秒）
    error_message: Optional[str] = None  # 错误信息
    
    # === 可选字段 ===
    difficulty: str = "easy"        # 难度: very_easy, easy, medium, hard, very_hard
    
    # === 缺陷测试字段 ===
    is_flawed: bool = False         # 是否为缺陷测试
    flaw_type: Optional[str] = None # 缺陷类型: sequence_disorder, tool_misuse, 
                                    # parameter_error, missing_step, redundant_operations,
                                    # logical_inconsistency, semantic_drift
    
    # === 元数据（自动生成） ===
    timestamp: str = ""             # 时间戳
    task_id: Optional[str] = None   # 任务ID
    session_id: Optional[str] = None # 会话ID
    test_instance: int = 0          # 第几次测试（自动分配）
```

## 使用场景示例

### 场景1：运行单个测试

```python
from 累积测试管理系统 import add_test_result
from mdp_workflow_generator import MDPWorkflowGenerator
from interactive_executor import InteractiveExecutor

# 生成任务
generator = MDPWorkflowGenerator()
task = generator.generate_task("simple_task", "baseline")

# 执行任务
executor = InteractiveExecutor(model="qwen2.5-3b-instruct")
result = executor.execute(task)

# 累积结果
add_test_result(
    model="qwen2.5-3b-instruct",
    task_type="simple_task",
    prompt_type="baseline",
    success=result.success,
    execution_time=result.execution_time,
    error_message=result.error if not result.success else None
)
```

### 场景2：批量测试特定组合

```python
from 累积测试管理系统 import CumulativeTestManager

manager = CumulativeTestManager()

# 测试特定任务类型的所有提示类型
task_type = "data_pipeline"
prompt_types = ["baseline", "optimal", "cot"]

for prompt_type in prompt_types:
    # 检查是否需要更多测试
    if manager.needs_more_tests("gpt-4o-mini", task_type, prompt_type, target_count=100):
        # 运行一批测试
        for i in range(10):  # 每次运行10个
            # ... 执行测试 ...
            add_test_result(
                model="gpt-4o-mini",
                task_type=task_type,
                prompt_type=prompt_type,
                success=test_result['success'],
                execution_time=test_result['time']
            )
```

### 场景3：智能补充测试

```python
from 累积测试管理系统 import CumulativeTestManager

manager = CumulativeTestManager()

# 获取需要补充的测试
remaining = manager.get_remaining_tests("qwen2.5-7b-instruct", target_count=100)

# 按优先级排序（需要最多的优先）
remaining.sort(key=lambda x: x['needed'], reverse=True)

# 运行最需要的10个组合
for test_config in remaining[:10]:
    if test_config['needed'] > 0:
        print(f"测试: {test_config['task_type']} + {test_config['prompt_type']}")
        print(f"  当前: {test_config['current_count']}/100")
        print(f"  需要: {test_config['needed']}个")
        
        # 运行5个测试
        for i in range(min(5, test_config['needed'])):
            # ... 执行测试 ...
            add_test_result(
                model="qwen2.5-7b-instruct",
                task_type=test_config['task_type'],
                prompt_type=test_config['prompt_type'],
                is_flawed=test_config['is_flawed'],
                flaw_type=test_config['flaw_type'],
                success=result['success'],
                execution_time=result['time']
            )
```

### 场景4：缺陷测试

```python
# 测试缺陷工作流
flaw_types = ["tool_misuse", "sequence_disorder", "parameter_error"]

for flaw_type in flaw_types:
    # 生成缺陷工作流
    flawed_task = generator.generate_flawed_task("api_integration", flaw_type)
    
    # 执行测试
    result = executor.execute(flawed_task)
    
    # 记录结果
    add_test_result(
        model="claude-3.7-sonnet",
        task_type="api_integration",
        prompt_type="baseline",  # 缺陷测试通常用baseline
        success=result.success,
        execution_time=result.execution_time,
        is_flawed=True,
        flaw_type=flaw_type,
        error_message=result.error
    )
```

### 场景5：生成进度报告

```python
from 累积测试管理系统 import CumulativeTestManager

manager = CumulativeTestManager()

# 获取所有模型的进度
report = manager.get_progress_report()

print("=== 测试进度总览 ===")
print(f"总测试数: {report['summary']['total_tests']}")
print(f"总成功数: {report['summary']['total_success']}")
print(f"整体成功率: {report['summary']['overall_success_rate']:.1f}%")
print(f"测试的模型: {', '.join(report['summary']['models_tested'])}")

# 查看特定模型的详细进度
model_report = manager.get_progress_report("qwen2.5-3b-instruct")
for model_name, stats in model_report['models'].items():
    print(f"\n模型: {model_name}")
    print(f"  总测试: {stats['total_tests']}")
    print(f"  成功率: {stats['total_success']/stats['total_tests']*100:.1f}%")
    
    print("\n  按任务类型:")
    for task_type, task_stats in stats['by_task_type'].items():
        rate = task_stats['success']/task_stats['total']*100 if task_stats['total'] > 0 else 0
        print(f"    {task_type}: {task_stats['success']}/{task_stats['total']} ({rate:.1f}%)")
```

### 场景6：导出数据生成报告

```python
from 累积测试管理系统 import CumulativeTestManager
from comprehensive_report_generator import ComprehensiveReportGenerator

# 导出累积数据
manager = CumulativeTestManager()
export_data = manager.export_for_report_generation()

# 保存为报告生成器可用的格式
import json
with open("temp_export.json", "w") as f:
    json.dump(export_data['results'], f)

# 使用报告生成器
generator = ComprehensiveReportGenerator("temp_export.json")
report = generator.generate_full_report()

# 保存报告
with open("实验结果报告.md", "w") as f:
    f.write(report)
```

## 数据库位置和结构

### 数据库文件
- 位置: `pilot_bench_cumulative_results/master_database.json`
- 备份: 系统会自动创建 `.backup` 文件

### 数据库结构
```json
{
    "version": "1.0",
    "created_at": "2025-08-05T10:00:00",
    "last_updated": "2025-08-05T15:30:00",
    "test_groups": {
        "qwen2.5-3b-instruct_simple_task_baseline_easy": {
            "model": "qwen2.5-3b-instruct",
            "task_type": "simple_task",
            "prompt_type": "baseline",
            "difficulty": "easy",
            "is_flawed": false,
            "flaw_type": null,
            "statistics": {
                "total": 85,
                "success": 72,
                "partial_success": 8,
                "failure": 5,
                "success_rate": 84.7,
                "avg_execution_time": 2.3
            },
            "instances": [...]
        }
    },
    "summary": {
        "total_tests": 15000,
        "total_success": 12300,
        "overall_success_rate": 82.0,
        "models_tested": ["qwen2.5-3b-instruct", "gpt-4o-mini", ...]
    }
}
```

## 注意事项

1. **自动保存**: 每次调用 `add_test_result()` 都会自动保存数据库
2. **线程安全**: 支持多线程并发添加结果
3. **原子操作**: 使用临时文件确保数据安全
4. **防重复**: 同一组合可以运行多次，每次都会累积
5. **灵活查询**: 可以查询任意组合的测试进度

## 故障排除

### 问题1: 数据库损坏
```python
# 系统会自动创建备份
# 手动恢复：
cp pilot_bench_cumulative_results/master_database.json.backup \
   pilot_bench_cumulative_results/master_database.json
```

### 问题2: 查看原始数据
```python
import json
with open("pilot_bench_cumulative_results/master_database.json") as f:
    db = json.load(f)
    print(f"总测试组合数: {len(db['test_groups'])}")
    print(f"总测试次数: {db['summary']['total_tests']}")
```

### 问题3: 重置特定组合
```python
# 直接编辑数据库文件，删除对应的键
# 或使用代码：
manager = CumulativeTestManager()
key = "qwen2.5-3b-instruct_simple_task_baseline_easy"
if key in manager.database['test_groups']:
    del manager.database['test_groups'][key]
    manager.save_database()
```

---

**文档版本**: 1.0  
**创建时间**: 2025-08-05  
**维护状态**: ✅ 活跃