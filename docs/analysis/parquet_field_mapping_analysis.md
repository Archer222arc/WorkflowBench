# Parquet字段映射问题深度分析

## 执行摘要
发现Parquet存储系统无法记录错误分类和failed统计的根本原因是字段名不匹配问题。

## 问题链分析

### 1. AI分类流程
```
batch_test_runner.py (1081行)
    ↓
record.ai_error_category = ai_error_category  # 动态添加字段
    ↓
TestRecord实例（没有定义此字段）
    ↓
parquet_cumulative_manager.py (368行)
    ↓
if hasattr(record, 'error_type'):  # 查找错误的字段名！
    ↓
找不到 → 错误分类全部为None
```

### 2. 字段名映射问题

| 组件 | 使用的字段名 | 行号 |
|------|------------|------|
| batch_test_runner.py | ai_error_category | 1081 |
| TestRecord类 | （未定义） | - |
| parquet_cumulative_manager.py | error_type | 368 |
| enhanced_cumulative_manager.py | error_classification | 269 |

### 3. TestRecord类缺失字段
```python
# cumulative_test_manager.py 第80-130行
@dataclass
class TestRecord:
    # 缺少以下字段：
    # - ai_error_category
    # - ai_error_reason  
    # - ai_confidence
    # - error_type
    # - error_classification
    # - tool_coverage_rate（动态添加）
```

### 4. JSON正确但Parquet错误的原因

**JSON（enhanced_cumulative_manager.py）**：
- 通过error_message进行分类（第262行）
- 使用_classify_error方法（第866行）
- 正确更新错误统计

**Parquet（parquet_cumulative_manager.py）**：
- 只查找error_type属性（第368行）
- 找不到则跳过错误统计
- 导致所有错误字段为0或None

### 5. failed字段问题
```python
# parquet_cumulative_manager.py 第438行
summary['failed'] = total - summary['success'] - summary['partial_success']
```
计算是正确的，但partial_success可能未正确统计。

## 修复方案

### 方案1：修改parquet_cumulative_manager.py（推荐）
```python
# 第368行改为：
if hasattr(record, 'ai_error_category'):
    error_type = record.ai_error_category
elif hasattr(record, 'error_type'):
    error_type = record.error_type
elif hasattr(record, 'error_classification'):
    error_type = record.error_classification
else:
    error_type = None

if error_type:
    # 现有的错误分类逻辑...
```

### 方案2：统一字段名
- 修改batch_test_runner使用error_type而不是ai_error_category
- 或者修改所有地方统一使用ai_error_category

### 方案3：扩展TestRecord类
```python
@dataclass
class TestRecord:
    # ... 现有字段 ...
    
    # AI分类字段
    ai_error_category: Optional[str] = None
    ai_error_reason: Optional[str] = None
    ai_confidence: float = 0.0
    error_type: Optional[str] = None  # 兼容字段
    error_classification: Optional[str] = None  # 兼容字段
    tool_coverage_rate: float = 0.0
```

## 验证步骤

1. 修复字段映射问题
2. 运行小规模测试
3. 检查Parquet中的错误分类字段
4. 验证failed统计是否正确

## 影响范围

- 所有使用Parquet存储的测试结果
- 错误分类统计全部缺失
- failed统计可能不准确
- 影响5.1-5.5所有测试阶段的统计准确性