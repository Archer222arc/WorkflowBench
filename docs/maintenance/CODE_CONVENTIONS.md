# 代码规范文档 (Code Conventions)

## 📋 目录
1. [命名规范](#命名规范)
2. [代码结构规范](#代码结构规范)
3. [错误处理规范](#错误处理规范)
4. [文档和注释规范](#文档和注释规范)
5. [测试规范](#测试规范)
6. [Git提交规范](#git提交规范)

---

## 命名规范

### 1. 文件命名
```python
# 模块文件：小写下划线
cumulative_test_manager.py
workflow_quality_test_flawed.py

# 配置文件：小写下划线
config.json
task_library.json

# 文档文件：大写下划线
SYSTEM_ARCHITECTURE.md
DEBUG_KNOWLEDGE_BASE.md
```

### 2. 类命名
```python
# 使用 PascalCase
class MDPWorkflowGenerator:
class InteractiveExecutor:
class TestRecord:
class SuccessMetrics:
```

### 3. 函数/方法命名
```python
# 使用 snake_case
def execute_interactive():
def add_test_result():
def _generate_intelligent_error_message():  # 私有方法前缀_
```

### 4. 变量命名
```python
# 局部变量：snake_case
format_error_count = 0
had_assistance = False

# 常量：大写下划线
MAX_RETRIES = 5
SUPPORTED_MODELS = [...]
DEFAULT_TIMEOUT = 30

# 类属性：snake_case
self.tool_registry = {}
self.overall_success = SuccessMetrics()
```

### 5. 统计字段命名规范
```python
# 计数类：_count 后缀
format_error_count
total_assisted_turns

# 率/比例类：_rate 后缀
success_rate
tool_coverage_rate
assistance_rate

# 布尔类：is_ 或 has_ 前缀
is_flawed
had_assistance
has_output

# 统计类：_metrics 后缀
success_metrics
error_metrics
score_metrics
```

---

## 代码结构规范

### 1. 类定义结构
```python
class ClassName:
    """类的简要说明"""
    
    # 类变量
    DEFAULT_VALUE = 10
    
    def __init__(self, param1: Type1, param2: Type2):
        """初始化方法
        
        Args:
            param1: 参数1说明
            param2: 参数2说明
        """
        self.param1 = param1
        self.param2 = param2
        self._private_var = None  # 私有变量
    
    # 公有方法
    def public_method(self):
        pass
    
    # 私有方法
    def _private_method(self):
        pass
    
    # 属性
    @property
    def computed_value(self):
        return self.param1 + self.param2
```

### 2. 数据类定义
```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class DataClassName:
    """数据类说明"""
    # 必需字段
    required_field: str
    
    # 可选字段（带默认值）
    optional_field: int = 0
    optional_str: Optional[str] = None
    
    # 可变默认值必须使用 field(default_factory=...)
    list_field: List[str] = field(default_factory=list)
    dict_field: Dict[str, int] = field(default_factory=dict)
```

### 3. 字典数据结构
```python
# 测试记录字典结构（标准格式）
test_dict = {
    # 必需字段
    "model": str,
    "task_type": str,
    "prompt_type": str,
    "success": bool,
    "success_level": str,  # "full_success" | "partial_success" | "failure"
    
    # 执行信息
    "execution_time": float,
    "turns": int,
    "tool_calls": List[str],
    "executed_tools": List[str],
    "required_tools": List[str],
    
    # 错误和帮助信息
    "error_message": Optional[str],
    "format_error_count": int,
    "api_issues": List[Dict],
    
    # 分数（可选）
    "workflow_score": Optional[float],
    "phase2_score": Optional[float],
    "quality_score": Optional[float],
    "final_score": Optional[float],
}
```

---

## 错误处理规范

### 1. 使用 try-except 的场景
```python
# ✅ 好的做法：具体的异常处理
try:
    response = client.chat.completions.create(...)
except RateLimitError as e:
    # 处理限流
    time.sleep(retry_interval)
except BadRequestError as e:
    # 处理400错误
    return None
except Exception as e:
    # 记录未预期的错误
    logger.error(f"Unexpected error: {e}")
    raise

# ❌ 避免：过于宽泛的异常捕获
try:
    # 大段代码
    ...
except:  # 捕获所有异常且不记录
    pass
```

### 2. 防御性编程
```python
# ✅ 好的做法：检查None和默认值
def process_score(score: Optional[float]) -> float:
    if score is None:
        return 0.0
    return max(0.0, min(1.0, score))  # 确保在[0,1]范围

# ✅ 好的做法：使用 getattr 和 get
format_count = getattr(record, 'format_error_count', 0)
tools = test_dict.get('executed_tools', [])
```

### 3. 错误消息规范
```python
# ✅ 好的做法：包含上下文信息
error_msg = f"Tool '{tool_name}' execution failed: {error}"
error_msg = f"Max turns ({max_turns}) reached without completion"

# ❌ 避免：模糊的错误消息
error_msg = "Error occurred"
error_msg = "Failed"
```

---

## 文档和注释规范

### 1. 模块文档字符串
```python
#!/usr/bin/env python3
"""
模块名称和简要说明
================================
更详细的模块功能描述

主要组件：
- Component1: 说明
- Component2: 说明

使用示例：
    from module import Class
    instance = Class()
"""
```

### 2. 函数/方法文档
```python
def function_name(param1: Type1, param2: Type2 = None) -> ReturnType:
    """函数简要说明
    
    详细描述（如需要）
    
    Args:
        param1: 参数1说明
        param2: 参数2说明（默认值：None）
    
    Returns:
        返回值说明
    
    Raises:
        ValueError: 何时抛出
        
    Example:
        >>> result = function_name(value1, value2)
    """
```

### 3. 行内注释
```python
# ✅ 好的注释：解释为什么
# 使用 tool_capabilities 而不是 tool_registry，因为前者包含完整信息
generator = FlawedWorkflowGenerator(
    tool_registry=generator.tool_capabilities,  # 注意：必须是 tool_capabilities
)

# ❌ 避免：解释是什么（代码已经说明了）
count = count + 1  # 增加计数
```

### 4. TODO 和 FIXME
```python
# TODO: 实现批量处理优化 (2025-01-08)
# FIXME: 处理工具名称大小写不一致的问题
# NOTE: 这里使用同步调用是因为需要保证顺序
# WARNING: 不要修改这个顺序，依赖关系很重要
```

---

## 测试规范

### 1. 测试函数命名
```python
def test_error_classification():
    """测试错误分类功能"""
    
def test_assisted_statistics():
    """测试assisted统计功能"""
    
def test_edge_case_empty_tools():
    """测试边界情况：空工具列表"""
```

### 2. 测试数据准备
```python
# 使用fixture或setup方法
def setup_test_data():
    return {
        'model': 'test-model',
        'task_type': 'basic_task',
        'success': True,
        'success_level': 'full_success',
        # ... 其他必需字段
    }
```

### 3. 断言规范
```python
# ✅ 好的做法：具体的断言消息
assert stats.total_tests == 10, f"Expected 10 tests, got {stats.total_tests}"

# ✅ 好的做法：多个相关断言
assert stats.assisted_success >= 0
assert stats.assisted_failure >= 0
assert stats.assisted_success + stats.assisted_failure <= stats.total_tests
```

---

## Git提交规范

### 1. 提交消息格式
```
<type>: <subject>

<body>

<footer>
```

### 2. Type类型
- **feat**: 新功能
- **fix**: Bug修复
- **docs**: 文档更新
- **style**: 代码格式调整
- **refactor**: 重构
- **test**: 测试相关
- **chore**: 构建过程或辅助工具的变动

### 3. 示例
```bash
fix: 修复assisted统计不正确的问题

- 修改了SuccessMetrics的统计逻辑，确保assisted统计不影响原有统计
- 更新了所有相关的统计层级
- 添加了avg_assisted_turns计算

Closes #123
```

---

## 代码审查检查点

### 提交前检查
- [ ] 所有新增字段都有默认值处理
- [ ] 使用了 get() 或 getattr() 防止 KeyError
- [ ] 错误消息包含足够的上下文
- [ ] 添加了必要的类型注解
- [ ] 更新了相关文档
- [ ] 没有留下调试print语句
- [ ] 测试通过

### 常见问题检查
- [ ] TestRecord 的所有字段都正确传递
- [ ] 统计更新没有条件分支影响 total_tests
- [ ] API错误不会被计入工作流错误
- [ ] 所有统计层级都同步更新

---

**文档创建时间**: 2025-01-08
**最后更新**: 2025-01-08
**版本**: 1.0