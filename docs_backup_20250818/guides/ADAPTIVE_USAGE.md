# 自适应限流使用指南

## 快速开始

### 推荐命令（自适应模式）
```bash
# 使用自适应限流 - 系统会自动调整速度避免限流
python batch_test_runner.py \
  --model qwen2.5-3b-instruct \
  --count 5 \
  --difficulty very_easy \
  --adaptive \
  --workers 3 \
  --qps 5 \
  --smart \
  --silent
```

### 对比：固定并发模式
```bash
# 固定并发 - 可能触发限流
python batch_test_runner.py \
  --model qwen2.5-3b-instruct \
  --count 5 \
  --difficulty very_easy \
  --concurrent \
  --workers 10 \
  --qps 20 \
  --smart \
  --silent
```

## 参数说明

| 参数 | 说明 | 推荐值 |
|-----|------|--------|
| `--adaptive` | 启用自适应限流 | 总是推荐使用 |
| `--workers` | 初始并发数（自适应模式）或固定并发数 | 3-5（自适应）|
| `--qps` | 初始QPS（自适应模式）或固定QPS | 5-10（自适应）|
| `--concurrent` | 使用固定并发（不要与adaptive同时使用）| - |

## 工作原理

### 自适应模式特性
1. **动态调整**: 根据API响应自动调整并发和QPS
2. **限流检测**: 检测"TPM/RPM限流"错误
3. **自动降速**: 遇到限流时减少并发和QPS
4. **自动恢复**: 稳定运行后逐步提速
5. **智能重试**: 限流错误自动加入重试队列

### 调整策略
- **首次限流**: 降至80%
- **连续限流**: 降至60%、50%...
- **稳定运行**: 每10次成功后提速20%
- **上下限**: workers(1-20), QPS(1-30)

## 使用场景

### 场景1: 小批量测试（推荐自适应）
```bash
python batch_test_runner.py \
  --model qwen2.5-3b-instruct \
  --count 2 \
  --adaptive \
  --workers 3 \
  --qps 5 \
  --smart
```

### 场景2: 大批量测试（必须用自适应）
```bash
python batch_test_runner.py \
  --model qwen2.5-3b-instruct \
  --count 50 \
  --adaptive \
  --workers 2 \
  --qps 3 \
  --smart \
  --silent
```

### 场景3: 快速测试（可以尝试固定并发）
```bash
python batch_test_runner.py \
  --model qwen2.5-3b-instruct \
  --count 1 \
  --concurrent \
  --workers 5 \
  --qps 10
```

## 日志和监控

日志文件位置：`logs/batch_test_YYYYMMDD_HHMMSS.log`

查看自适应调整过程：
```bash
# 查看最新日志
ls -lt logs/ | head -2

# 查看限流和调整
grep -E "Rate limit|Slowing down|Speeding up" logs/batch_test_*.log

# 查看统计
grep "Adaptive stats" logs/batch_test_*.log
```

## 常见问题

### Q: 应该用 --adaptive 还是 --concurrent？
**A: 几乎总是用 --adaptive**。只有在测试很少（<5个）且确定不会触发限流时才用 --concurrent。

### Q: 初始workers和qps设置多少？
**A: 保守开始**
- 不确定时：workers=2, qps=3
- 一般情况：workers=3, qps=5
- 已知稳定：workers=5, qps=10

### Q: 还是触发限流怎么办？
**A: 降低初始值**
```bash
--workers 1 --qps 1  # 极度保守
```

### Q: 速度太慢怎么办？
**A: 系统会自动提速**。如果一直很慢，可以：
1. 稍微提高初始值
2. 检查是否有其他错误（非限流）
3. 查看日志了解原因

## 最佳实践

1. **总是使用 --adaptive**
2. **保守的初始值优于激进值**
3. **使用 --silent 减少输出**
4. **查看日志了解调整过程**
5. **大批量测试分批进行**

## 示例输出

```
Running 100 tests with adaptive rate limiting
Initial settings: workers=3, QPS=5.0
Executing batch: 3 tasks (workers=3, QPS=5.0, completed=0/100)
Rate limit hit! Adjusting: workers=2, qps=4
Slowing down: workers 3→2, QPS 5.0→4.0
Executing batch: 2 tasks (workers=2, QPS=4.0, completed=3/100)
...
Speeding up: workers 2→3, QPS 4.0→5.0
...
Final statistics:
  - Total tests: 100
  - Successful: 95
  - Failed: 5
  - Rate limit hits: 3
  - Final workers: 5
  - Final QPS: 8
```