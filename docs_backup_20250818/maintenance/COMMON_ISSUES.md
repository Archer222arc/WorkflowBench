# 常见问题解决方案 (Common Issues & Solutions)

## 📋 目录
1. [启动和配置问题](#启动和配置问题)
2. [运行时错误](#运行时错误)
3. [统计和数据问题](#统计和数据问题)
4. [性能问题](#性能问题)
5. [快速修复脚本](#快速修复脚本)

---

## 启动和配置问题

### 问题1: ModuleNotFoundError
```
ModuleNotFoundError: No module named 'openai'
```
**解决方案**:
```bash
pip install openai
pip install -r requirements.txt  # 如果有requirements文件
```

### 问题2: API密钥配置错误
```
ValueError: OpenAI API key not configured
```
**解决方案**:
1. 检查 `config/config.json`:
```json
{
    "openai_api_key": "your-key-here",
    "idealab_api_key": "your-key-here"
}
```
2. 或设置环境变量:
```bash
export OPENAI_API_KEY="your-key-here"
export IDEALAB_API_KEY="your-key-here"
```

### 问题3: 任务库文件缺失
```
FileNotFoundError: mcp_generated_library/task_library.json
```
**解决方案**:
```python
# 检查文件是否存在
import os
task_library_path = "mcp_generated_library/task_library.json"
if not os.path.exists(task_library_path):
    print("Task library missing! Please generate it first.")
```

### 问题4: 模型不支持
```
ValueError: Unsupported model: xxx
```
**解决方案**:
检查 `api_client_manager.py` 中的 `SUPPORTED_MODELS` 列表

---

## 运行时错误

### 问题1: AttributeError - 缺少 format_error_count
```python
AttributeError: 'TestRecord' object has no attribute 'format_error_count'
```
**原因**: TestRecord 创建时未设置该字段

**解决方案**:
```python
# batch_test_runner.py
record.format_error_count = result.get('format_error_count', 0)
record.api_issues = result.get('api_issues', [])
record.executed_tools = result.get('executed_tools', [])
```

### 问题2: KeyError - assisted_attempt
```python
KeyError: 'assisted_attempt'
```
**原因**: 旧版本使用了 assisted_attempt，新版本改为 assisted_failure/assisted_success

**解决方案**:
```python
# 不要使用
stats.assisted_attempt

# 使用
stats.assisted_failure  # 得到帮助但失败
stats.assisted_success  # 得到帮助后成功
```

### 问题3: TypeError - NoneType 运算
```python
TypeError: unsupported operand type(s) for +: 'NoneType' and 'float'
```
**原因**: 分数字段可能为 None

**解决方案**:
```python
# 添加 None 检查
if score is not None:
    total_score += score

# 或使用默认值
score = record.get('workflow_score') or 0.0
```

### 问题4: 并发写入冲突
```
PermissionError: [Errno 13] Permission denied: 'master_database.json'
```
**原因**: 多个进程同时写入同一文件

**解决方案**:
```python
# cumulative_test_manager.py
import uuid
temp_file = self.db_file.parent / f"{self.db_file.stem}_{uuid.uuid4().hex}.tmp"
```

---

## 统计和数据问题

### 问题1: 统计数据不一致
**症状**: total_tests != full_success + partial_success + failure

**检查步骤**:
```python
def validate_statistics(stats):
    total = stats.full_success + stats.partial_success + stats.failure
    assert stats.total_tests == total, f"Inconsistent: {stats.total_tests} != {total}"
```

**解决方案**:
确保 update_from_test() 中没有条件分支影响 total_tests 计数:
```python
# 正确 ✅
self.overall_success.total_tests += 1
if success_level == 'full_success':
    self.overall_success.full_success += 1

# 错误 ❌
if success_level == 'assisted_attempt':
    self.overall_success.assisted_attempt += 1
else:
    self.overall_success.total_tests += 1  # 条件分支！
```

### 问题2: tool_coverage_rate 为 0
**原因**: 没有正确记录工具使用

**解决方案**:
```python
# cumulative_data_structure.py
# 优先使用 executed_tools
tools_to_track = test_record.get('executed_tools', test_record.get('tool_calls', []))
```

### 问题3: 错误分类全为 0
**原因**: 错误消息被覆盖或 API 错误被错误分类

**解决方案**:
1. 保留原始错误消息
2. API 错误记录到 api_issues，不计入工作流错误

---

## 性能问题

### 问题1: API 调用频繁失败
**症状**: 大量 400 或限流错误

**解决方案**:
```python
# interactive_executor.py
# 增加重试和优化间隔
max_retries = 5  # 增加重试次数
base_wait = random.uniform(0.5, 1.5)  # 减少基础等待
wait_time = min(base_wait * (1.5 ** attempt), 10)  # 温和增长
```

### 问题2: 测试执行缓慢
**原因**: 串行执行或 QPS 限制过严

**解决方案**:
```bash
# 使用并发执行
python batch_test_runner.py --concurrent --workers 20 --qps 10
```

### 问题3: 内存占用过大
**原因**: 保存了所有测试实例

**解决方案**:
使用累积统计而不是保存实例:
```python
# 不要保存实例
"instances": []  # 保持为空

# 只更新统计
stats["total"] += 1
stats["success"] += 1 if success else 0
```

---

## 快速修复脚本

### 1. 清理损坏的数据库
```python
#!/usr/bin/env python3
"""fix_database.py - 修复损坏的数据库"""

import json
from pathlib import Path
from datetime import datetime

def fix_database():
    db_path = Path("pilot_bench_cumulative_results/master_database.json")
    
    # 备份
    backup_path = db_path.parent / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    if db_path.exists():
        import shutil
        shutil.copy(db_path, backup_path)
        print(f"Backed up to {backup_path}")
    
    # 尝试修复
    try:
        with open(db_path) as f:
            data = json.load(f)
        
        # 修复缺失字段
        for model_name, model_stats in data.get('models', {}).items():
            if 'overall_success' in model_stats:
                success = model_stats['overall_success']
                # 添加新字段
                if 'assisted_failure' not in success:
                    success['assisted_failure'] = 0
                if 'assisted_success' not in success:
                    success['assisted_success'] = 0
                if 'total_assisted_turns' not in success:
                    success['total_assisted_turns'] = 0
                if 'tests_with_assistance' not in success:
                    success['tests_with_assistance'] = 0
        
        # 保存修复后的数据
        with open(db_path, 'w') as f:
            json.dump(data, f, indent=2)
        print("Database fixed successfully")
        
    except Exception as e:
        print(f"Failed to fix database: {e}")
        print(f"Restore from backup: {backup_path}")

if __name__ == "__main__":
    fix_database()
```

### 2. 验证数据一致性
```python
#!/usr/bin/env python3
"""validate_stats.py - 验证统计一致性"""

import json
from pathlib import Path

def validate_database():
    db_path = Path("pilot_bench_cumulative_results/master_database.json")
    
    with open(db_path) as f:
        data = json.load(f)
    
    issues = []
    
    for model_name, model_stats in data.get('models', {}).items():
        if 'overall_success' in model_stats:
            s = model_stats['overall_success']
            
            # 检查基本统计
            total = s.get('full_success', 0) + s.get('partial_success', 0) + s.get('failure', 0)
            if s.get('total_tests', 0) != total:
                issues.append(f"{model_name}: total_tests mismatch")
            
            # 检查 assisted 统计
            assisted_total = s.get('assisted_success', 0) + s.get('assisted_failure', 0)
            if assisted_total > s.get('total_tests', 0):
                issues.append(f"{model_name}: assisted > total")
    
    if issues:
        print("Issues found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("All statistics are consistent ✓")

if __name__ == "__main__":
    validate_database()
```

### 3. 迁移旧数据格式
```python
#!/usr/bin/env python3
"""migrate_data.py - 迁移旧格式数据"""

def migrate_assisted_attempt_to_new_format(data):
    """将 assisted_attempt 迁移到 assisted_failure"""
    
    for model_stats in data.get('models', {}).values():
        if 'overall_success' in model_stats:
            success = model_stats['overall_success']
            
            # 迁移 assisted_attempt -> assisted_failure
            if 'assisted_attempt' in success:
                success['assisted_failure'] = success.pop('assisted_attempt')
                success['assisted_success'] = 0
                success['total_assisted_turns'] = 0
                success['tests_with_assistance'] = success['assisted_failure']
    
    return data
```

---

## 常用调试技巧

### 1. 添加调试输出
```python
# 在关键位置添加
print(f"[DEBUG] Variable: {variable_name}")
print(f"[DEBUG] Type: {type(variable_name)}")
print(f"[DEBUG] Keys: {variable_name.keys() if isinstance(variable_name, dict) else 'N/A'}")
```

### 2. 使用 pdb 调试器
```python
import pdb
pdb.set_trace()  # 设置断点
```

### 3. 记录详细日志
```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.debug(f"Processing: {item}")
```

### 4. 单元测试特定功能
```python
# 创建 test_specific.py
def test_error_classification():
    from cumulative_data_structure import ErrorMetrics
    
    metrics = ErrorMetrics()
    metrics.categorize_error("TIMEOUT: Operation timed out")
    assert metrics.timeout_errors == 1
    print("Test passed ✓")

if __name__ == "__main__":
    test_error_classification()
```

---

## 预防措施

### 1. 提交前检查清单
- [ ] 运行单个测试确认基本功能
- [ ] 检查所有新字段都有默认值
- [ ] 确认没有遗留的 print 调试语句
- [ ] 验证统计一致性

### 2. 定期维护
- 每周备份 master_database.json
- 定期运行验证脚本
- 记录所有已知问题和解决方案

### 3. 监控指标
- API 调用成功率
- 平均执行时间
- 错误分类分布
- assisted 统计趋势

---

**文档创建时间**: 2025-01-08
**最后更新**: 2025-01-08
**版本**: 1.0