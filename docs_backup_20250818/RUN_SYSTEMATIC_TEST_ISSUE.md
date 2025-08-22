# run_systematic_test_final.sh 5.3部分卡死问题分析

## 问题定位

### 脚本中的关键代码
```bash
# 5.3测试调用
run_smart_test "$model" "flawed_sequence_disorder,flawed_tool_misuse,flawed_parameter_error" \
    "easy" "all" "$NUM_INSTANCES" "缺陷工作流(结构缺陷组)" ""
```

### run_smart_test函数最终执行
```bash
python3 smart_batch_runner.py \
    --model "$model" \
    --prompt-types "$prompt_types" \
    --difficulty "$difficulty" \
    --task-types "$actual_task_types" \
    --num-instances "$actual_instances" \
    --max-workers 100 \            # 🔴 过高并发
    --adaptive \
    --prompt-parallel \
    --batch-commit \                # 🔴 批量提交模式
    --checkpoint-interval $CHECKPOINT_INTERVAL \  # 🔴 默认20
    --ai-classification \
    --save-logs &                   # 🔴 后台运行，无超时控制
```

## 核心问题

### 1. **批量提交 + 高checkpoint间隔**
- `--batch-commit` + `--checkpoint-interval 20`
- 需要积累20个测试才保存一次
- 如果在第19个测试卡死，前18个永远不会保存

### 2. **过高并发**
- `--max-workers 100` 并发太高
- 多个prompt types并行运行
- 容易导致资源耗尽

### 3. **无超时控制**
- 使用`&`后台运行，无法控制超时
- 没有单测试超时
- 没有总批次超时

### 4. **并发等待死锁**
```bash
) &
pids+=($!)
# 后面会wait所有pids
```
- 如果某个后台进程卡死，wait会永远等待

## 为什么卡死40小时？

1. **API无响应**: IdealLab API可能无响应，无超时机制
2. **内存耗尽**: 100个workers + save-logs导致内存爆炸
3. **批量不触发**: 卡在第N个测试，checkpoint永不触发
4. **wait死锁**: 父进程wait卡死的子进程

## 解决方案

### 1. 修改脚本参数
```bash
# 在run_systematic_test_final.sh中修改
CHECKPOINT_INTERVAL=5  # 而不是20
max_workers=20         # 而不是100

# 或添加超时包装
timeout 3600 python3 smart_batch_runner.py ...
```

### 2. 修改run_smart_test函数
```bash
run_smart_test() {
    # ... 原有代码 ...
    
    # 添加超时控制
    if [ "$ULTRA_PARALLEL_MODE" = "true" ]; then
        timeout 7200 python ultra_parallel_runner.py ...  # 2小时超时
    else
        # 移除batch-commit，使用实时保存
        timeout 3600 python3 smart_batch_runner.py \
            --model "$model" \
            --prompt-types "$prompt_types" \
            --difficulty "$difficulty" \
            --task-types "$actual_task_types" \
            --num-instances "$actual_instances" \
            --max-workers 20 \     # 降低并发
            --checkpoint-interval 5 \  # 更频繁保存
            --no-adaptive \
            --qps 10 \
            --silent
    fi
}
```

### 3. 使用安全模式运行
```bash
# 安全运行5.3测试
CHECKPOINT_INTERVAL=5 \
MAX_WORKERS=20 \
timeout 7200 ./run_systematic_test_final.sh --ultra-parallel
```

## 总结

**根本原因**：
- `run_systematic_test_final.sh`使用了危险的参数组合
- batch-commit + checkpoint-interval 20 + max-workers 100
- 无超时控制 + 后台wait模式

**立即可行的修复**：
1. 编辑脚本，将CHECKPOINT_INTERVAL改为5
2. 将max_workers改为20
3. 添加timeout命令包装
4. 或移除--batch-commit参数