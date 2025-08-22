# 批量测试运行器使用指南

## 🚀 快速开始

### 推荐：自适应限流模式
自动调整速度，避免API限流

```bash
python batch_test_runner.py \
  --model qwen2.5-3b-instruct \
  --count 10 \
  --difficulty very_easy \
  --adaptive \
  --workers 3 \
  --qps 5 \
  --smart \
  --silent
```

## 三种运行模式对比

| 模式 | 命令参数 | 优点 | 缺点 | 适用场景 |
|-----|---------|------|------|---------|
| **自适应** | `--adaptive` | 自动调速，避免限流 | 初期较慢 | **推荐所有场景** |
| 固定并发 | `--concurrent` | 速度可控 | 易触发限流 | 小批量测试 |
| 串行 | (无参数) | 最稳定 | 最慢 | 调试单个测试 |

## 参数说明

### 基本参数
- `--model`: 测试模型名称
- `--count`: 每种组合的测试数量
- `--difficulty`: 任务难度 (very_easy/easy/medium/hard/very_hard)
- `--smart`: 智能选择需要的测试

### 自适应参数
- `--adaptive`: 启用自适应限流
- `--workers`: 初始并发数（建议2-5）
- `--qps`: 初始QPS（建议3-10）

### 输出控制
- `--silent`: 静默模式，减少输出
- `--debug`: 调试模式，详细输出

## 最佳实践

### 1. 小批量测试（< 10个）
```bash
python batch_test_runner.py \
  --model gpt-4o-mini \
  --count 2 \
  --adaptive \
  --workers 3 \
  --qps 5 \
  --smart
```

### 2. 中等批量测试（10-50个）
```bash
python batch_test_runner.py \
  --model qwen2.5-3b-instruct \
  --count 10 \
  --adaptive \
  --workers 2 \
  --qps 3 \
  --smart \
  --silent
```

### 3. 大批量测试（> 50个）
```bash
python batch_test_runner.py \
  --model qwen2.5-3b-instruct \
  --count 20 \
  --adaptive \
  --workers 1 \
  --qps 2 \
  --smart \
  --silent
```

## 自适应限流工作原理

1. **开始**: 使用保守的初始值（如 workers=3, qps=5）
2. **监控**: 实时检测API响应
3. **调整**:
   - 遇到限流 → 自动降速（×0.5-0.8）
   - 连续成功 → 自动提速（×1.2）
4. **智能重试**: 限流错误自动重试

## 查看日志

日志自动保存在 `logs/` 目录：

```bash
# 查看最新日志
ls -lt logs/ | head -2

# 监控限流调整
grep -E "Rate limit|Slowing down|Speeding up" logs/batch_test_*.log

# 查看进度
tail -f logs/batch_test_*.log
```

## 常见问题

### Q: 还是遇到限流怎么办？
降低初始值：
```bash
--workers 1 --qps 1  # 极度保守
```

### Q: 速度太慢？
1. 系统会自动提速（稳定运行10次后）
2. 可以稍微提高初始值（但不要太激进）

### Q: 选择 adaptive 还是 concurrent？
**总是选择 --adaptive**，除非：
- 测试数量很少（<5个）
- 你确定不会触发限流

## 示例输出

```
Running 50 tests with adaptive rate limiting
Initial settings: workers=3, QPS=5.0
Executing batch: 3 tasks (workers=3, QPS=5.0, completed=0/50)
Rate limit hit! Adjusting: workers=2, qps=4
Slowing down: workers 3→2, QPS 5.0→4.0
...
Speeding up: workers 2→3, QPS 4.0→5.0
...
Final statistics:
  - Total tests: 50
  - Successful: 45
  - Failed: 5
  - Rate limit hits: 2
  - Final workers: 4
  - Final QPS: 6
```