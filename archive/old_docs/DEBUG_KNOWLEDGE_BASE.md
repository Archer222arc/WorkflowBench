# 调试知识库 (Debug Knowledge Base)

## 📋 目录
1. [常见错误模式](#常见错误模式)
2. [已解决的Bug记录](#已解决的bug记录)
3. [调试检查清单](#调试检查清单)
4. [性能优化点](#性能优化点)
5. [数据一致性检查](#数据一致性检查)

---

## 常见错误模式

### 1. AttributeError: 'XXX' object has no attribute 'YYY'

#### 模式1: ExecutionState缺少属性
```python
# 问题: state.format_error_count 不存在
# 原因: ExecutionState类定义中缺少该属性

# 解决方案:
# 1. 使用 hasattr() 检查
if hasattr(state, 'format_error_count'):
    count = state.format_error_count

# 2. 使用 getattr() 带默认值
count = getattr(state, 'format_error_count', 0)
```

#### 模式2: TestRecord字段缺失
```python
# 问题: record.execution_status 不存在
# 原因: TestRecord创建时未设置该字段

# 解决方案: 在创建TestRecord后立即设置
record.execution_status = result.get('success_level', 'failure')
record.format_error_count = result.get('format_error_count', 0)
```

### 2. KeyError: 字典键不存在

#### 模式1: test_record字典缺少键
```python
# 问题: test_record['executed_tools'] KeyError
# 原因: 旧版本数据没有该字段

# 解决方案: 使用 get() 方法
executed_tools = test_record.get('executed_tools', [])
# 或者使用回退
executed_tools = test_record.get('executed_tools', test_record.get('tool_calls', []))
```

### 3. TypeError: 类型不匹配

#### 模式1: None值运算
```python
# 问题: TypeError: unsupported operand type(s) for +: 'NoneType' and 'int'
# 原因: score可能为None

# 解决方案: 添加None检查
if score is not None:
    total += score
```

#### 模式2: 列表/字典混淆
```python
# 问题: 'list' object has no attribute 'get'
# 原因: tool_calls可能是列表或字典

# 解决方案: 类型检查
if isinstance(tool_calls, list):
    for tool in tool_calls:
        # 处理列表
elif isinstance(tool_calls, dict):
    # 处理字典
```

---

## 已解决的Bug记录

### Bug #1: 错误分类不正确 (2025-01-07)
**症状**: 所有错误率显示为0
**原因**: 
1. API错误被错误地分类为工作流错误
2. _generate_intelligent_error_message返回通用消息覆盖了原始错误

**解决方案**:
```python
# interactive_executor.py
# 保留原始错误消息
if 'timeout' in error_lower:
    return f"{error} (tool: {tool_name})"  # 保留原始错误
```

### Bug #2: tool_coverage_rate始终为0 (2025-01-07)
**症状**: tool_coverage_rate = 0.0
**原因**: 使用tool_calls而不是executed_tools

**解决方案**:
```python
# cumulative_data_structure.py
# 优先使用executed_tools
tools_to_track = test_record.get('executed_tools', test_record.get('tool_calls', []))
```

### Bug #3: assisted_attempt统计混乱 (2025-01-08)
**症状**: assisted统计影响了原有的success/failure统计
**原因**: 使用了条件分支导致某些测试不计入total_tests

**解决方案**:
```python
# 改为并行统计
self.overall_success.total_tests += 1  # 始终计入
if had_assistance:  # 额外统计
    if success:
        self.overall_success.assisted_success += 1
    else:
        self.overall_success.assisted_failure += 1
```

### Bug #4: 并发写入数据库冲突 (已解决)
**症状**: 多个进程同时写入导致数据丢失
**原因**: 临时文件名冲突

**解决方案**:
```python
# cumulative_test_manager.py
import uuid
temp_file = self.db_file.parent / f"{self.db_file.stem}_{uuid.uuid4().hex}.tmp"
```

---

## 调试检查清单

### 启动新测试前检查
- [ ] 检查 `master_database.json` 是否存在
- [ ] 确认模型名称在 `SUPPORTED_MODELS` 列表中
- [ ] 验证 API 密钥配置正确
- [ ] 确认 `mcp_generated_library/task_library.json` 存在

### 测试失败时检查
- [ ] 查看完整错误堆栈
- [ ] 检查 `test_record` 是否包含所有必需字段
- [ ] 验证 `success_level` 值是否合法
- [ ] 确认 `format_error_count` 是否正确传递

### 统计异常时检查
- [ ] 检查 `ModelStatistics.update_from_test()` 接收的字典
- [ ] 验证 `had_assistance` 计算逻辑
- [ ] 确认统计更新没有条件分支影响 `total_tests`
- [ ] 检查是否所有统计层级都更新了

---

## 性能优化点

### 1. 批量数据库写入
```python
# 不要每个测试都写数据库
local_records = []
for task in tasks:
    result = run_test(task)
    local_records.append(create_record(result))

# 批量写入
for record in local_records:
    manager.add_test_result(record)
manager.save_database()  # 一次性保存
```

### 2. LLM调用优化
```python
# 重试机制优化
max_retries = 5  # 而不是3
base_wait = random.uniform(0.5, 1.5)  # 减少基础等待
wait_time = min(base_wait * (1.5 ** attempt), 10)  # 上限10秒
```

### 3. 并发控制
```python
# QPS限制
min_interval = 1.0 / qps
with self._request_lock:
    time_since_last = now - self._last_request_time
    if time_since_last < min_interval:
        time.sleep(min_interval - time_since_last)
```

---

## 数据一致性检查

### 1. 验证统计总和
```python
def validate_stats(stats: SuccessMetrics):
    # 基本三元组必须等于总数
    assert stats.total_tests == (stats.full_success + 
                                 stats.partial_success + 
                                 stats.failure)
    
    # assisted统计是额外的
    assert stats.total_assisted_tests == (stats.assisted_success + 
                                          stats.assisted_failure)
    
    # assisted不能超过总测试数
    assert stats.tests_with_assistance <= stats.total_tests
```

### 2. 字段完整性检查
```python
REQUIRED_FIELDS = [
    'model', 'task_type', 'prompt_type', 'success', 
    'success_level', 'execution_time', 'timestamp'
]

def validate_record(record: Dict):
    for field in REQUIRED_FIELDS:
        assert field in record, f"Missing required field: {field}"
```

### 3. 分数范围检查
```python
def validate_scores(record: Dict):
    score_fields = ['workflow_score', 'phase2_score', 
                   'quality_score', 'final_score']
    for field in score_fields:
        if field in record and record[field] is not None:
            assert 0 <= record[field] <= 1, f"{field} out of range"
```

---

## 常用调试命令

### 1. 查看数据库内容
```python
import json
with open('pilot_bench_cumulative_results/master_database.json') as f:
    db = json.load(f)
    print(f"Models: {list(db['models'].keys())}")
    for model, stats in db['models'].items():
        print(f"{model}: {stats.get('overall_success', {}).get('total_tests', 0)} tests")
```

### 2. 清理测试数据
```python
from cumulative_test_manager import CumulativeTestManager
manager = CumulativeTestManager()
manager.clear_database()  # 会自动备份
```

### 3. 验证单个测试
```python
# 运行单个测试用于调试
python batch_test_runner.py --model gpt-4o-mini --count 1 --debug
```

### 4. 检查错误分类
```python
# 查看错误分类统计
stats = db['models']['gpt-4o-mini']['overall_errors']
print(f"Format errors: {stats.get('tool_call_format_errors', 0)}")
print(f"Timeout errors: {stats.get('timeout_errors', 0)}")
```

---

## 调试输出点

### 关键调试位置
1. `interactive_executor.py:_get_llm_response()` - API调用
2. `cumulative_data_structure.py:update_from_test()` - 统计更新
3. `batch_test_runner.py:run_single_test()` - 测试执行
4. `cumulative_test_manager.py:add_test_result()` - 数据保存

### 调试输出示例
```python
# 添加调试输出
print(f"[DEBUG] format_error_count: {format_error_count}")
print(f"[DEBUG] had_assistance: {had_assistance}")
print(f"[DEBUG] success_level: {success_level}")
print(f"[DEBUG] Updating stats - before: {stats.total_tests}")
```

---

**文档创建时间**: 2025-01-08
**最后更新**: 2025-01-08
**版本**: 1.0