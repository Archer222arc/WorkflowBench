# 各Phase并发模式详细分析

## Phase 5.1 - 基准测试

### 开源模型（8个）
```
模型列表：
- DeepSeek-V3-0324 (Azure)
- DeepSeek-R1-0528 (Azure)
- qwen2.5-72b-instruct (IdealLab)
- qwen2.5-32b-instruct (IdealLab)
- qwen2.5-14b-instruct (IdealLab)
- qwen2.5-7b-instruct (IdealLab)
- qwen2.5-3b-instruct (IdealLab)
- Llama-3.3-70B-Instruct (Azure)
```

### 并发执行模式
- **串行执行**：每个模型依次执行，不并发
- **配置**：optimal + easy + all task types + 20 instances

### Qwen模型分片策略（修改后）
```
qwen2.5-72b → 1个分片，使用key0
qwen2.5-32b → 1个分片，使用key1
qwen2.5-14b → 1个分片，使用key2
qwen2.5-7b → 1个分片，使用key0
qwen2.5-3b → 1个分片，使用key1
```

### 执行流程
1. 模型按顺序执行
2. 每个qwen模型创建1个分片（之前是3个）
3. Azure模型创建1个分片，使用多个workers

---

## Phase 5.2 - Qwen规模效应测试

### 测试配置
- **模型**：5个Qwen模型
- **难度**：very_easy 和 medium（分开测试）
- **并发模式**：**所有模型同时运行**

### 并发执行详情
```bash
# 第一批：very_easy难度
qwen2.5-72b (very_easy) → key0 &
sleep 15
qwen2.5-32b (very_easy) → key1 &
sleep 15
qwen2.5-14b (very_easy) → key2 &
sleep 15
qwen2.5-7b (very_easy) → key0 &  # 与72b共享key0
sleep 15
qwen2.5-3b (very_easy) → key1 &  # 与32b共享key1

# 第二批：medium难度（同时启动）
qwen2.5-72b (medium) → key0 &
sleep 15
qwen2.5-32b (medium) → key1 &
sleep 15
qwen2.5-14b (medium) → key2 &
sleep 15
qwen2.5-7b (medium) → key0 &
sleep 15
qwen2.5-3b (medium) → key1 &
```

### 关键问题
- **10个进程并发运行**（5个模型×2个难度）
- 15秒延迟启动，但所有进程都在运行
- key0被4个进程使用（72b-very_easy, 7b-very_easy, 72b-medium, 7b-medium）
- key1被4个进程使用（32b-very_easy, 3b-very_easy, 32b-medium, 3b-medium）
- key2被2个进程使用（14b-very_easy, 14b-medium）

---

## Phase 5.3 - 缺陷工作流测试

### 测试配置
- **缺陷类型**：7种，分3组
- **模型**：所有开源模型（8个）

### 分组策略
```
组1（结构缺陷）：
- flawed_sequence_disorder
- flawed_incomplete_description

组2（操作缺陷）：
- flawed_missing_step
- flawed_insufficient_detail
- flawed_parameter_issues

组3（逻辑缺陷）：
- flawed_logical_inconsistency
- flawed_contradictory_instructions
```

### 并发执行模式
- **模型串行**：每个模型依次执行
- **组内并发**：每个模型的3组缺陷并发执行

### Qwen模型的Key分配（基于模型，不是组）
```
qwen2.5-72b：
  - 所有3组都使用key0

qwen2.5-32b：
  - 所有3组都使用key1

qwen2.5-14b：
  - 所有3组都使用key2

（以此类推）
```

---

## Phase 5.4 - 工具可靠性测试

### 测试配置
- **成功率**：0.9, 0.8, 0.7, 0.6, 0.5（5个级别）
- **模型**：所有模型

### 并发执行模式
- **模型串行**：每个模型依次执行
- **成功率串行**：每个成功率级别依次执行
- **无并发**：完全串行执行

### Qwen模型分片
- 每个测试创建1个分片，使用分配的key

---

## Phase 5.5 - 提示敏感性测试

### 测试配置
- **Prompt类型**：baseline, cot（2种）
- **模型**：所有模型

### 并发执行模式
- **模型串行**：每个模型依次执行
- **Prompt类型串行**：每种prompt依次执行
- **无并发**：完全串行执行

### Qwen模型分片
- 每个测试创建1个分片，使用分配的key

---

## 🔴 关键发现：Phase 5.2 存在严重的并发问题

### 问题分析
1. **Phase 5.2 是最严重的并发场景**
   - 10个进程同时运行
   - key0和key1各被4个进程使用
   - 即使有15秒延迟，但所有进程仍在并发

2. **实际QPS计算**
   ```
   key0: 4个进程 × 2 QPS = 8 QPS
   key1: 4个进程 × 2 QPS = 8 QPS
   key2: 2个进程 × 2 QPS = 4 QPS
   ```

3. **为什么还会限流**
   - IdealLab限制是10 QPS per key
   - 8 QPS接近限制，加上突发可能超限

### 建议的修复方案

#### 方案A：真正的串行执行（推荐）
```bash
# 不使用 & 后台执行，改为串行
for model in QWEN_MODELS; do
    run_test $model very_easy
    wait  # 等待完成
done

for model in QWEN_MODELS; do
    run_test $model medium
    wait  # 等待完成
done
```

#### 方案B：减少并发度
```bash
# 分批执行，每批最多3个模型
# 第一批：72b, 32b, 14b (各用不同key)
# 第二批：7b, 3b (等第一批完成)
```

#### 方案C：动态Key池管理
- 实现一个全局Key管理器
- 确保每个key同时只有一个模型使用
- 模型完成后释放key给下一个模型