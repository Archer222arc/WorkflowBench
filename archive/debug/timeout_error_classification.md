# 超时错误的分类和统计

## 回答你的问题：是的！

### 超时错误会被分类为 `timeout_errors` 并计入 `timeout_error_rate`

## 1. 错误分类流程

### 当任务超时时：
```python
# batch_test_runner.py 第1549-1554行
except TimeoutError as e:
    result = {
        'success': False,
        'error': str(e),
        'error_type': 'timeout',  # ← 标记为timeout
        'execution_time': timeout
    }
```

### 错误统计：
```python
# enhanced_cumulative_manager.py
class ModelPromptStatistics:
    timeout_errors: int = 0  # 超时错误计数
    
    def categorize_and_count(self, error_message):
        if 'test timeout after' in error_lower:
            self.timeout_errors += 1
            return 'timeout'
```

## 2. 统计指标

### 在数据库中的存储：
```json
{
  "models": {
    "DeepSeek-V3-0324": {
      "by_prompt_type": {
        "baseline": {
          "by_difficulty": {
            "easy": {
              "by_task_type": {
                "simple_task": {
                  "total": 100,
                  "failed": 30,
                  "timeout_errors": 20,  # ← 超时错误数
                  "timeout_error_rate": 0.667  # ← 20/30 = 66.7%的失败是超时
                }
              }
            }
          }
        }
      }
    }
  }
}
```

### 计算公式：
```python
# 超时错误率（占所有错误的比例）
timeout_error_rate = timeout_errors / total_errors

# 例如：
# 总共100个测试
# 30个失败
# 其中20个是超时
# timeout_error_rate = 20/30 = 0.667 (66.7%)
```

## 3. 错误分类类型

系统识别的错误类型：
1. **timeout_errors** - 执行超时（60秒无响应）
2. **format_errors** - 工具调用格式错误
3. **max_turns_errors** - 达到最大回合数（10个turn）
4. **tool_selection_errors** - 选择了错误的工具
5. **dependency_errors** - 依赖问题
6. **sequence_errors** - 执行顺序错误
7. **parameter_errors** - 参数配置错误
8. **other_errors** - 其他未分类错误

## 4. 查看超时统计

### 方法1：查看数据库
```python
import json
with open('pilot_bench_cumulative_results/master_database.json') as f:
    db = json.load(f)
    
model_data = db['models']['DeepSeek-V3-0324']
stats = model_data['by_prompt_type']['baseline']['by_difficulty']['easy']
print(f"超时错误: {stats.get('timeout_errors', 0)}")
print(f"超时错误率: {stats.get('timeout_error_rate', 0):.1%}")
```

### 方法2：查看实时日志
```bash
grep -c "timeout" logs/batch_test_*.log
grep "timeout_error_rate" logs/batch_test_*.log
```

## 5. 重要发现

### 如果超时很多，说明：
1. **API响应太慢** - 网络问题或服务器负载高
2. **模型太大** - DeepSeek-V3需要更长时间
3. **超时设置太短** - 60秒可能不够

### 解决方案：
1. **增加超时时间**（你提到的120秒）
```python
timeout=120  # 给大模型更多时间
```

2. **减少重试次数**
```python
max_retries=2  # 不要5次，避免等太久
```

3. **跳过经常超时的模型**
```python
if model_timeout_rate > 0.5:  # 超过50%超时
    skip_model()  # 跳过这个模型
```

## 6. 实际影响

### 如果大量超时：
- **时间浪费**：每个超时测试耗时5分钟（5次重试）
- **数据偏差**：超时的测试记为失败，影响成功率统计
- **资源浪费**：Worker被占用但没有有效输出

### 监控建议：
```python
# 如果某个模型超时率>30%，应该：
if timeout_error_rate > 0.3:
    # 1. 增加该模型的超时时间
    # 2. 减少测试实例数
    # 3. 或者直接跳过该模型
```
