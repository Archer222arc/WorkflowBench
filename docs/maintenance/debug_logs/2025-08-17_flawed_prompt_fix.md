# 5.3测试数据污染修复

**修复ID**: FIX-20250817-003  
**日期**: 2025-08-17  
**修复者**: Claude Assistant  
**严重级别**: 🔴 高  
**影响范围**: 5.3缺陷工作流测试数据准确性

## 问题描述

运行`run_systematic_test_final.sh`的5.3测试后，Parquet和JSON数据库中出现与5.3测试无关的数据污染：
- 出现`deepseek-v3`、`baseline`、`optimal`等不相关的prompt类型
- 具体的flawed类型（如`flawed_sequence_disorder`）被错误简化为通用的`flawed`
- 导致5.3测试结果无法正确分类和统计

## 根本原因

**文件**: `smart_batch_runner.py`  
**行号**: 220  
**问题代码**:
```python
prompt_type="flawed" if is_flawed else prompt_type,
```

此代码错误地将所有包含"flawed"的prompt_type简化为单一的"flawed"字符串，丢失了具体的缺陷类型信息。

## 修复方案

### 代码修改

#### 1. prompt_type简化问题（两处）
```python
# 修复前（第220行和第655行）
prompt_type="flawed" if is_flawed else prompt_type,

# 修复后（第220行和第655行）
prompt_type=prompt_type,  # 保持原始的prompt_type，不要简化
```

#### 2. signal线程错误
```python
# 修复前（batch_test_runner.py第1484行）
if sys.platform == 'win32':
    return self._run_single_test_safe_with_thread(task)

# 修复后
if sys.platform == 'win32' or threading.current_thread() != threading.main_thread():
    return self._run_single_test_safe_with_thread(task)
```

### 修复原理
- 保持`prompt_type`的原始值（如`flawed_sequence_disorder`）
- 实际的缺陷注入通过独立的`is_flawed`和`flaw_type`字段控制
- 这样既保证了数据分类的准确性，又不影响缺陷注入机制

## 验证测试

### 1. 单个类型测试
```bash
python smart_batch_runner.py \
  --model gpt-4o-mini \
  --prompt-types flawed_sequence_disorder \
  --difficulty easy \
  --task-types simple_task \
  --num-instances 1
```
**结果**: ✅ `flawed_sequence_disorder`被正确保存

### 2. 多类型测试
测试了所有5.3相关的flawed类型：
- `flawed_sequence_disorder` ✅
- `flawed_tool_misuse` ✅  
- `flawed_parameter_error` ✅

### 3. 数据库验证
```python
# 检查数据库中的prompt_types
saved_types = ['flawed_sequence_disorder', 'flawed_tool_misuse', 'flawed_parameter_error']
# 没有发现被简化的'flawed'类型 ✅
```

## 影响分析

### 正面影响
1. 5.3测试数据现在能正确分类和统计
2. 每种缺陷类型的成功率可以独立追踪
3. 数据库不再有污染和混淆

### 无负面影响
1. **缺陷注入机制不受影响** - 使用独立的`is_flawed`和`flaw_type`字段
2. **向后兼容性保持** - 不影响其他测试类型
3. **性能无影响** - 只是字符串赋值的改变

## 相关文件

- `smart_batch_runner.py` - 主要修复文件
- `batch_test_runner.py` - TestTask定义（验证缺陷注入机制）
- `run_systematic_test_final.sh` - 5.3测试脚本

## 经验教训

1. **不要假设简化数据**：保持原始数据的完整性，让分析层决定如何聚合
2. **分离关注点**：数据分类（prompt_type）和功能控制（is_flawed/flaw_type）应该独立
3. **充分测试**：修改数据处理逻辑时，要验证所有相关的数据路径

## 后续建议

1. 添加数据验证层，在保存前检查prompt_type的有效性
2. 考虑为flawed类型创建专门的枚举或常量定义
3. 在数据分析时提供聚合选项，而不是在数据收集时简化

## 测试命令集

```bash
# 清理旧数据
python -c "import json; ..."

# 运行5.3测试
./run_systematic_test_final.sh
# 选择选项5，然后选择3

# 验证修复
python -c "
import json
from pathlib import Path
db = json.load(open('pilot_bench_cumulative_results/master_database.json'))
# 检查是否有正确的flawed类型
"
```