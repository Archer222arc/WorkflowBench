# WorkflowBench 缺陷工作流测试完整文档

## 一、项目概述

WorkflowBench Scale-Up 是基于MDP的智能工作流质量测试系统，用于评估语言模型在工作流执行任务中的鲁棒性和性能。

## 二、实验计划

### 2.1 核心概念
缺陷工作流测试的核心理念是将缺陷作为"提示策略"（Prompt Strategy），通过在提示中嵌入有缺陷的执行计划来测试模型的鲁棒性，而不是修改工作流对象本身。

### 2.2 10种Prompt策略
根据实验计划，系统实现了10种不同的prompt策略：

#### 3种基本Prompt
1. **baseline** - 纯任务描述，无工作流指导
2. **optimal** - 包含最优工作流执行序列
3. **cot** - Chain of Thought，要求模型逐步推理

#### 7种缺陷Prompt（prompt_type='flawed'）
1. **sequence_disorder** - 工具执行顺序错误
2. **tool_misuse** - 工具使用不当
3. **parameter_error** - 参数错误
4. **missing_step** - 缺少必要步骤
5. **redundant_operations** - 冗余操作
6. **logical_inconsistency** - 逻辑不一致
7. **semantic_drift** - 语义偏移

### 2.3 测试分配策略
- **均衡分配**：每种策略获得 `count/10` 个测试
- **余数处理**：前面的策略各多分配1个
- **示例分配**：
  - count=10 → 每种1个
  - count=100 → 每种10个
  - count=105 → 前5种11个，后5种10个

## 三、核心实现

### 3.1 workflow_quality_test_flawed.py 标准实现

#### 关键方法
```python
def _create_flawed_prompt(self, task_type: str, workflow: Dict, 
                        flaw_type: str, fixed_task_instance: Optional[Dict] = None) -> str:
    """创建带缺陷的prompt - 不透露缺陷信息以确保公平性"""
    baseline = self._create_baseline_prompt(task_type, fixed_task_instance)
    flawed_sequence = workflow.get('optimal_sequence', [])
    
    # 根据是否有智能信息选择不同的工作流指导格式
    if 'smart_actions' in workflow and workflow['smart_actions']:
        # 使用 RAG 增强的执行计划
        execution_plan = self.generator._generate_smart_execution_plan(workflow['smart_actions'])
        workflow_guidance = f"""
## Workflow Execution Plan
{execution_plan}
### Execution Strategy:
1. Follow the recommended sequence for optimal results
2. Use alternatives if primary tools fail
3. Pay special attention to critical tools
4. ALWAYS use default parameters - never ask for user input
5. Execute ONE tool at a time and wait for feedback
"""
    else:
        # 使用简单的 workflow 指导
        workflow_guidance = f"""
## Workflow Execution Plan
### Recommended Tool Sequence:
{self._format_workflow_sequence(flawed_sequence)}
### Execution Strategy:
1. Follow the recommended sequence for optimal results
2. Use alternatives if primary tools fail
3. Validate outputs at each step
4. ALWAYS use default parameters - never ask for user input
5. Execute ONE tool at a time and wait for feedback
"""
    
    # 在特定插入点插入workflow guidance
    insertion_point = "Begin by searching for the first tool you need."
    if insertion_point in baseline:
        return baseline.replace(insertion_point, workflow_guidance + "\n\n" + insertion_point)
    else:
        return baseline + workflow_guidance
```

### 3.2 batch_test_runner.py 实现

#### 组合模式继承
```python
class BatchTestRunner:
    def __init__(self, debug: bool = False, silent: bool = False):
        # ... 其他初始化 ...
        self.quality_tester = None  # WorkflowQualityTester 实例
        
    def _lazy_init(self):
        # 初始化 WorkflowQualityTester（用于继承prompt创建方法）
        self.quality_tester = WorkflowQualityTester(
            model='gpt-4o-mini',
            use_phase2_scoring=False  # 批测试不需要Phase2评分
        )
```

#### 均衡分配实现
```python
def get_smart_tasks(self, model: str, count: int, difficulty: str = "easy") -> List[TestTask]:
    """智能选择需要测试的任务 - 均衡分配10种prompt策略"""
    
    # 定义10种prompt策略
    prompt_strategies = [
        # 3种基础prompt
        {"prompt_type": "baseline", "is_flawed": False, "flaw_type": None},
        {"prompt_type": "optimal", "is_flawed": False, "flaw_type": None},
        {"prompt_type": "cot", "is_flawed": False, "flaw_type": None},
        # 7种缺陷prompt
        {"prompt_type": "flawed", "is_flawed": True, "flaw_type": "sequence_disorder"},
        {"prompt_type": "flawed", "is_flawed": True, "flaw_type": "tool_misuse"},
        # ... 其他5种 ...
    ]
    
    # 计算每种策略应该测试多少个
    tests_per_strategy = count // len(prompt_strategies)
    remaining_tests = count % len(prompt_strategies)
    
    # 为每种策略创建指定数量的测试
    for i, strategy in enumerate(prompt_strategies):
        strategy_count = tests_per_strategy + (1 if i < remaining_tests else 0)
        # ... 创建测试任务 ...
```

### 3.3 执行流程一致性

#### InteractiveExecutor 初始化
```python
# 两个实现都使用相同的参数
executor = InteractiveExecutor(
    tool_registry=...,      # 工具注册表
    llm_client=None,        # 自动获取
    max_turns=10,           # 最大轮数
    success_rate=0.8,       # 成功率
    model=model             # 模型名称
)
```

#### execute_interactive 调用
```python
# 完全一致的参数结构
result = executor.execute_interactive(
    initial_prompt=prompt,           # 生成的prompt
    task_instance=task_instance,     # 任务实例
    workflow=workflow,               # 工作流
    prompt_type=prompt_type          # prompt类型
)
```

## 四、使用指南

### 4.1 推荐测试命令

#### 完整测试（100个测试，每种策略10个）
```bash
python batch_test_runner.py \
  --model qwen2.5-3b-instruct \
  --count 100 \
  --difficulty very_easy \
  --concurrent \
  --workers 20 \
  --qps 20 \
  --smart \
  --silent
```

#### 快速测试（10个测试，每种策略1个）
```bash
python batch_test_runner.py \
  --model qwen2.5-3b-instruct \
  --count 10 \
  --difficulty very_easy \
  --concurrent \
  --workers 5 \
  --qps 10 \
  --smart \
  --debug
```

### 4.2 参数说明
- `--count`: 总测试数量（建议100以上）
- `--difficulty`: 任务难度（very_easy, easy, medium, hard, very_hard）
- `--concurrent`: 启用并发执行
- `--workers`: 并发工作线程数
- `--qps`: 每秒查询限制
- `--smart`: 智能选择任务（均衡分配）
- `--silent`: 静默模式（减少输出）
- `--debug`: 调试模式（详细输出）

## 五、重要注意事项

### 5.1 必须遵守的规则

1. **prompt_type 使用规则**
   - 缺陷测试必须使用 `prompt_type='flawed'`
   - 不要使用 `'baseline'` 作为缺陷测试的 prompt_type

2. **工作流生成规则**
   - 必须先生成正常工作流，再注入缺陷
   - 使用 `FlawedWorkflowGenerator.inject_specific_flaw()` 注入缺陷

3. **属性引用规则**
   - MDPWorkflowGenerator 使用 `full_tool_registry` 而不是 `tool_registry`
   - FlawedWorkflowGenerator 初始化需要 tool_capabilities 字典

4. **测试数据记录**
   - 缺陷测试必须记录 flaw_type 和 flaw_severity
   - 使用 CumulativeTestManager 保存测试结果

### 5.2 代码维护规范

1. **禁止创建 fallback 方法** - 避免代码复杂化
2. **禁止创建临时修复脚本** - 直接修复源文件
3. **使用 MultiEdit 进行批量修改** - 提高效率
4. **避免创建重复功能的脚本** - 保持代码库精简
5. **修复必须完整** - 不能只是禁用功能
6. **必须理解现有代码结构** - 修改前先理解核心文件的实现模式

## 六、文件结构

### 核心脚本（重要，不要删除）
- `main.py` - 主入口文件
- `generalized_mdp_framework.py` - MDP核心框架
- `unified_training_manager.py` - 统一训练管理
- `mdp_workflow_generator.py` - 工作流生成器
- `workflow_quality_test_flawed.py` - 工作流质量测试（标准实现）
- `flawed_workflow_generator.py` - 缺陷工作流生成
- `batch_test_runner.py` - 批量测试运行器
- `interactive_executor.py` - 交互式执行器
- `cumulative_test_manager.py` - 累积测试管理

### 重要目录
- `workflow_quality_results/` - 当前测试结果
- `workflow_quality_results_backup_20250802_005542/` - 重要备份（不要删除）
- `checkpoints/` - 训练模型检查点
- `mcp_generated_library/` - MCP工具库
- `config/` - 配置文件

## 七、测试验证

### 7.1 验证脚本
- `test_balanced_distribution.py` - 测试均衡分配逻辑
- `test_batch_runner_prompts.py` - 测试prompt创建功能
- `test_experiment_compliance.py` - 验证实验计划合规性

### 7.2 验证命令
```bash
# 验证均衡分配
python test_balanced_distribution.py

# 验证prompt继承
python test_batch_runner_prompts.py

# 验证实验合规性
python test_experiment_compliance.py
```

## 八、调试和故障排除

### 8.1 常见问题

1. **属性错误 'tool_registry'**
   - 解决：使用 `full_tool_registry` 代替

2. **缺陷测试不工作**
   - 检查：prompt_type 是否设置为 'flawed'
   - 检查：FlawedWorkflowGenerator 是否正确初始化

3. **分配不均衡**
   - 确保使用 `--smart` 参数
   - 检查 count 是否足够大

### 8.2 调试技巧
```bash
# 使用debug模式查看详细执行过程
python batch_test_runner.py --model qwen2.5-3b-instruct --count 10 --debug

# 查看任务分配
python batch_test_runner.py --model qwen2.5-3b-instruct --count 100 --smart --progress
```

---

**文档版本**: 2.0
**创建时间**: 2025-08-02
**最后更新**: 2025-08-06
**维护状态**: ✅ 活跃维护中
**作者**: Claude Assistant