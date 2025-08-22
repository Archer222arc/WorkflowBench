# 5.4 测试策略更新说明

## 策略简化

根据用户反馈，5.4工具可靠性测试策略已更新为更简单的方案：

### 原策略（复杂）
- 不同的tool_success_rate分配到不同的API keys
- 0.9 → key0, 0.8 → key1, 0.7 → key2, 0.6 → key0
- 试图并行运行不同的tool_success_rate

### 新策略（简化）
- **与5.1/5.2相同的并发策略**
- 所有optimal prompt测试均匀分配到3个keys
- 不同的tool_success_rate在更高层次**串行执行**

## 实现方式

```python
# ultra_parallel_runner.py中的处理
if single_prompt == 'optimal':
    # 不管tool_success_rate是多少
    # 都均匀分配到3个keys实现3倍并发
    instances_per_key = num_instances // 3
    for key_idx in range(3):
        # 创建分片...
```

## 执行流程

### 5.4测试执行示例
```bash
# 串行执行不同的tool_success_rate
for rate in 0.9 0.8 0.7 0.6; do
    echo "测试 tool_success_rate=$rate"
    python ultra_parallel_runner.py \
        --model qwen2.5-72b-instruct \
        --prompt-types optimal \
        --tool-success-rate $rate \
        --num-instances 100
    # 内部会并行使用3个keys
done
```

### 并发层次
1. **Level 1**: tool_success_rate串行（0.9 → 0.8 → 0.7 → 0.6）
2. **Level 2**: 每个rate内部3倍并发（key0 + key1 + key2）
3. **Level 3**: 每个key的worker并发

## 优势

1. **代码简化**：5.1/5.2/5.4使用相同逻辑
2. **避免复杂性**：不需要特殊的rate→key映射
3. **性能不变**：每个rate测试仍有3倍并发
4. **更清晰**：tool_success_rate的差异在更高层次处理

## 性能影响

- **单个rate测试**：3倍并发（3个keys并行）
- **多个rate测试**：串行执行，但每个都是3倍速
- **总体效果**：与5.1/5.2一致的优化效果

## 总结

5.4现在使用与5.1/5.2完全相同的并发策略，简化了实现并保持了性能优化效果。不同的tool_success_rate值通过串行执行来区分，而不是通过复杂的key分配。

---
更新时间：2025-08-19 19:50
作者：Claude Assistant