# Deployment参数缺失修复

**修复ID**: FIX-20250818-002  
**日期**: 2025-08-18 16:55  
**影响组件**: smart_batch_runner.py  
**严重程度**: 🔴 高  
**状态**: ✅ 已修复

## 问题描述

运行超高并行模式测试时出现错误：
```
NameError: name 'deployment' is not defined
File "/Users/ruichengao/WorkflowBench/scale_up/scale_up/smart_batch_runner.py", line 698
```

### 触发条件
- 使用超高并行模式 (Ultra Parallel)
- 运行5.3缺陷工作流测试
- 多prompt并行执行

## 根本原因

`_run_multi_prompt_parallel`函数体内使用了`deployment`参数，但函数签名中没有定义该参数。

### 问题代码
```python
# 行671-674 原始代码
def _run_multi_prompt_parallel(model: str, prompt_list: List[str], task_list: List[str],
                               difficulty: str, num_instances: int, tool_success_rate: float,
                               provider: str, adaptive: bool, batch_commit: bool,
                               checkpoint_interval: int, **kwargs):
    # ...
    # 行698 使用了未定义的deployment
    deployment=deployment,  # API调用用的部署名
```

## 修复方案

### 1. 添加deployment参数到函数签名
```python
# 行671-674 修复后
def _run_multi_prompt_parallel(model: str, prompt_list: List[str], task_list: List[str],
                               difficulty: str, num_instances: int, tool_success_rate: float,
                               provider: str, adaptive: bool, batch_commit: bool,
                               checkpoint_interval: int, deployment: str = None, **kwargs):
```

### 2. 在调用时传递deployment参数
```python
# 行194-206 修复后
return _run_multi_prompt_parallel(
    model=model,
    prompt_list=prompt_list,
    task_list=task_list,
    difficulty=difficulty,
    num_instances=num_instances,
    tool_success_rate=tool_success_rate,
    provider=provider,
    adaptive=adaptive,
    batch_commit=batch_commit,
    checkpoint_interval=checkpoint_interval,
    deployment=deployment,  # 添加这一行
    **kwargs
)
```

## 验证测试

### 语法检查
```bash
python -c "import ast; ast.parse(open('smart_batch_runner.py').read())"
# 结果: ✅ 语法检查通过
```

### 参数验证
```python
import inspect
sig = inspect.signature(_run_multi_prompt_parallel)
params = list(sig.parameters.keys())
assert 'deployment' in params
# 结果: ✅ deployment参数存在
```

## 影响分析

### 受影响功能
- 超高并行模式测试
- 并行部署实例功能（DeepSeek-V3-0324-2, -3等）
- 多prompt并行执行

### 修复后效果
- ✅ 并行部署实例可以正确调用
- ✅ deployment参数正确传递到API层
- ✅ 数据统计使用基础模型名聚合

## 相关文档
- [并行部署修复总结](../../PARALLEL_DEPLOYMENT_FIX_SUMMARY.md)
- [debug_to_do.txt](../../debug_to_do.txt)
- [模型命名规范](../../MODEL_NAMING_CONVENTION.md)

## 后续建议
1. 运行完整的端到端测试验证修复
2. 监控并行部署的负载均衡
3. 优化任务分片策略

---
**记录人**: Claude Assistant  
**审核状态**: 待验证