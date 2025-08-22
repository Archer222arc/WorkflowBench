# Claude Assistant 项目文档 v3.0

## 项目概述
WorkflowBench Scale-Up - 基于MDP的智能工作流质量测试系统

**当前版本**: 3.2.1
**最后更新**: 2025-08-18 01:15
**项目状态**: 🟢 Active Development
**管理级别**: STRICT（严格代码管理）
**存储格式**: JSON + Parquet（双格式支持）

## 📊 项目进展追踪

### 当前测试进度
| 模型类型 | 总数 | 已完成 | 进行中 | 未开始 | 完成率 |
|---------|------|--------|--------|--------|--------|
| 开源模型 | 8 | 5 | 2 | 1 | 62.5% |
| 闭源模型 | 5 | 3 | 1 | 1 | 60% |

### 最新更新 (2025-08-18 10:00)
- 🚨 **v3.1.0 重大修复：超时机制和数据保存**
  - ✅ 修复worker线程超时机制失效（signal.SIGALRM不能在worker线程中使用）
  - ✅ 修复数据不保存问题（enable_database_updates错误设置为False）
  - ✅ 优化超时处理（API超时120秒，任务超时10分钟，批次20分钟强制结束）
  - ✅ 修复错误分类（timeout_errors正确识别）
  - ✅ 性能提升：8小时→20分钟（节省95%时间）
- 🔍 **v2.3.0 API测试验证**
  - ✅ 验证bash脚本所有14个模型API可用性
  - ✅ 创建完整API测试套件（3个测试脚本）
  - ✅ 归档测试脚本到scripts/test/api/
  - ✅ 测试成功率100% (14/14模型通过)
- 🎉 **v3.0 重大升级：完整项目重构**
  - ✅ 完成项目文件归档和组织（18个脚本归档）
  - ✅ 创建完整文档索引系统
  - ✅ 实现模型名称标准化（统一并行实例）
  - ✅ 建立debug知识库v2和维护指南
  - ✅ JSON到Parquet数据迁移完成（4,993条记录）
- 🔥 **双存储格式支持（v2.2功能）**
  - ✅ 实现JSON/Parquet双存储格式
  - ✅ 解决并发写入数据覆盖问题
  - ✅ 添加中断恢复和事务机制
- ✅ 修复DeepSeek-V3-0324分类（从闭源移至开源）
- ✅ 验证gpt-5-mini和kimi-k2可用性

## 📚 系统文档索引

### 核心文档
1. **[README.md](./README.md)** - 项目总体说明
2. **[QUICK_REFERENCE.md](./QUICK_REFERENCE.md)** - 快速参考指南
3. **[PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md)** - 项目结构说明

## 📁 数据存储结构说明

### 🆕 存储格式选择（v2.2新增）
系统现支持两种存储格式：
- **JSON格式**：传统方式，兼容性好，适合单进程，存储完整测试记录
- **Parquet格式**：高性能，并发安全，推荐用于生产环境，**仅存储汇总数据**

选择方式：
```bash
# 方式1：运行时选择
./run_systematic_test_final.sh  # 会显示选择菜单

# 方式2：环境变量
export STORAGE_FORMAT=parquet  # 或 json
```

#### ⚠️ Parquet格式重要特性
**设计决策**：Parquet格式被设计为**只存储汇总数据，不存储单个测试记录**
- **原因**：减少存储开销，提高查询性能，适合大规模测试
- **实现**：`ParquetDataManager.append_test_result()`是空操作（返回True）
- **数据流**：测试记录 → 实时聚合 → 定期刷新汇总到Parquet文件
- **查询**：所有统计基于汇总数据，通过累加`total`字段计算总数

### ⚠️ 数据同步重要注意事项（2025-08-17更新）

#### 数据字段要求
JSON数据必须包含完整的41个字段才能正确同步到Parquet：
- **基本统计字段** (12个): total, successful, partial, failed, success_rate等
- **质量分数字段** (4个): avg_workflow_score, avg_phase2_score, avg_quality_score, avg_final_score
- **错误统计字段** (9个): total_errors, tool_selection_errors, sequence_order_errors等
- **错误率字段** (8个): tool_selection_error_rate, parameter_error_rate等
- **辅助统计字段** (7个): assisted_success, assisted_failure, avg_assisted_turns等
- **其他字段** (1个): last_updated

#### 数据同步脚本
正确的同步脚本：`scripts/data_sync/sync_complete_json_to_parquet.py`
- ✅ 自动跳过llama-4-scout-17b
- ✅ 自动跳过task_type=unknown
- ✅ 自动跳过单独的prompt_type=flawed
- ✅ 保留所有51个字段（包括标识字段）

#### 数据清理规则
1. **必须删除的数据**：
   - llama-4-scout-17b（已停用的模型）
   - task_type=unknown（无效任务类型）
   - prompt_type=flawed（没有具体缺陷类型的）
   
2. **必须保留的数据**：
   - 具体的flawed类型（如flawed_sequence_disorder）
   - 所有质量分数和错误统计字段

### Master Database 层次结构
系统使用以下结构存储所有测试数据（JSON和Parquet格式均遵循此结构）：

```
master_database.json
├── models/
│   └── {model_name}/
│       ├── overall_stats: {total_tests, success_rate, tool_coverage_rate, ...}
│       ├── experiment_metrics: {tool_reliability_90, tool_reliability_80, ...}
│       └── by_prompt_type/
│           └── {prompt_type}/  # optimal, baseline, cot, flawed_*
│               ├── total_tests
│               ├── success_rate
│               └── by_tool_success_rate/
│                   └── {rate}/  # 0.9, 0.8, 0.7, 0.6
│                       └── by_difficulty/
│                           └── {difficulty}/  # very_easy, easy, medium, hard
│                               └── by_task_type/
│                                   └── {task_type}/  # simple_task, basic_task, etc.
│                                       ├── total
│                                       ├── successful
│                                       ├── partial
│                                       ├── failed
│                                       ├── success_rate
│                                       ├── partial_rate
│                                       ├── failure_rate
│                                       ├── weighted_success_score
│                                       ├── avg_execution_time
│                                       ├── avg_turns
│                                       ├── tool_coverage_rate
│                                       └── avg_tool_calls
├── test_groups/
│   └── {test_group_id}/
│       ├── model
│       ├── prompt_type
│       ├── difficulty
│       ├── tool_success_rate
│       ├── task_type
│       ├── num_instances
│       ├── total_tests
│       └── timestamp
└── summary/
    ├── total_tests
    ├── total_success
    ├── total_partial
    ├── total_failure
    ├── models_tested: [list of models]
    └── last_test_time
```

### 数据访问示例
```python
# 获取特定模型在特定配置下的成功率
model_data = db['models']['DeepSeek-V3-0324']
optimal_data = model_data['by_prompt_type']['optimal']
rate_08_data = optimal_data['by_tool_success_rate']['0.8']
easy_data = rate_08_data['by_difficulty']['easy']
simple_task_data = easy_data['by_task_type']['simple_task']
success_rate = simple_task_data['success_rate']
```

### 数据填表规则
- **默认配置**: 除非特别要求，所有实验结果表格默认使用以下配置的数据：
  - **Prompt类型**: `optimal`（最佳提示策略）
  - **难度**: `easy`（标准难度）
  - **工具成功率**: `0.8`（80%，默认可靠性）
- **原因**: 这是标准基准配置，便于横向对比不同模型
- **特殊情况**:
  - 5.2规模效应测试：需要very_easy和medium难度对比
  - 5.4工具可靠性测试：需要90%、70%、60%成功率对比
  - 5.5提示敏感性测试：需要baseline、cot等prompt类型对比

### 工具成功率分桶规则
- 工具成功率使用4位小数精度进行分桶：`round(tool_success_rate, 4)`
- 例如：0.7512 和 0.7513 会被分到不同的桶
- 常用桶：0.9, 0.8, 0.7, 0.6

## 🎯 模型命名规范（重要）

### 并行部署实例设计
多个Azure部署用于提高并发能力，命名规则如下：

#### 1. 基础模型名（用于数据统计）
```
DeepSeek-V3-0324        # 标准名称，所有统计归类到此
DeepSeek-R1-0528        # 标准名称
Llama-3.3-70B-Instruct  # 标准名称
```

#### 2. 并行部署名（用于API调用）
```
DeepSeek-V3-0324        # 主部署
DeepSeek-V3-0324-2      # 并行部署2
DeepSeek-V3-0324-3      # 并行部署3
```

#### 3. 命名传递规则
- **bash脚本 → ultra_parallel_runner**: 传递基础模型名
- **ultra_parallel_runner → smart_batch_runner**: 
  - `--model` 参数：传递基础模型名（用于统计）
  - 内部路由：使用具体部署名（如 -2, -3）
- **smart_batch_runner → API调用**: 使用具体部署名
- **数据保存**: 统一归类到基础模型名

#### 4. 大小写规范
- **必须保持一致的大小写格式**
- 正确：`DeepSeek-V3-0324-2`（与主部署一致）
- 错误：`deepseek-v3-0324-2`（小写不一致）

#### 5. normalize_model_name行为
- 用于数据统计时：去除 -2, -3 后缀
- 用于API调用时：保留完整部署名

### 示例流程
```bash
# 1. 用户请求
./run_systematic_test_final.sh --model "DeepSeek-V3-0324"

# 2. Ultra并行分片
Shard 1: api_name="DeepSeek-V3-0324", stat_name="DeepSeek-V3-0324"  
Shard 2: api_name="DeepSeek-V3-0324-2", stat_name="DeepSeek-V3-0324"
Shard 3: api_name="DeepSeek-V3-0324-3", stat_name="DeepSeek-V3-0324"

# 3. 数据保存
所有结果归类到: models["DeepSeek-V3-0324"]
```

### 技术文档
1. **系统架构** - `docs/architecture/`
   - SYSTEM_ARCHITECTURE.md - 系统架构和组件说明
   - DATABASE_STRUCTURE_V3.md - 数据库结构
   - DATA_FLOW_STATUS.md - 数据流状态

2. **维护文档** - `docs/maintenance/`
   - DEBUG_KNOWLEDGE_BASE.md - 调试知识库
   - CODE_CONVENTIONS.md - 代码规范
   - COMMON_ISSUES.md - 常见问题解决方案

3. **使用指南** - `docs/guides/`
   - BATCH_TEST_USAGE.md - 批量测试使用
   - PARALLEL_TESTING_GUIDE.md - 并行测试指南
   - FAILED_TESTS_GUIDE.md - 失败测试处理

### API文档
- `docs/api/` - 所有API相关文档
  - CLOSED_SOURCE_API_CONFIG.md
  - API_REFERENCE.md
  - MODEL_ROUTING_GUIDE.md

## 🔧 当前配置状态

### 支持的模型

#### 开源模型（8个）
```python
OPENSOURCE_MODELS = [
    "DeepSeek-V3-0324",      # Azure - ✅ 已验证
    "DeepSeek-R1-0528",      # Azure - ✅ 已验证
    "qwen2.5-72b-instruct",  # IdealLab
    "qwen2.5-32b-instruct",  # IdealLab
    "qwen2.5-14b-instruct",  # IdealLab
    "qwen2.5-7b-instruct",   # IdealLab
    "qwen2.5-3b-instruct",   # IdealLab
    "Llama-3.3-70B-Instruct" # Azure - ✅ 已验证
]
```

#### 闭源模型（5个）
```python
CLOSED_SOURCE_MODELS = [
    "gpt-4o-mini",           # Azure - ✅ 已验证
    "gpt-5-mini",            # Azure - ✅ 已验证（2025-08-16）
    "o3-0416-global",        # IdealLab - ✅ 已验证
    "gemini-2.5-flash-06-17",# IdealLab - ⚠️ 可能返回空content
    "kimi-k2"                # IdealLab - ✅ 已验证（2025-08-16）
]
```

## 🔍 代码修复规范 v5.1 [2025-08-18更新]

### 📚 知识库一致性验证
**必须执行的知识库查询**：
1. 从Project Knowledge读取错误涉及的所有文件
2. 确认文件的最新版本和行号对应关系
3. 查找所有调用该函数/类的位置
4. 验证与其他模块的依赖关系
5. 记录所有可用的工具函数和API接口
6. **验证存储格式相关的设计意图**（JSON vs Parquet）
7. **🔴 必须查看logs目录中的相关日志文件**（/Users/ruichengao/WorkflowBench/scale_up/scale_up/logs/）

### 📋 日志分析要求 [强制]
**修复前必须执行的日志检查**：
1. **查看最新的batch_test日志**：
   ```bash
   ls -lt /Users/ruichengao/WorkflowBench/scale_up/scale_up/logs/batch_test_*.log | head -5
   tail -100 [最新日志文件]  # 查看错误信息
   ```
2. **查看对应的debug日志**：
   ```bash
   ls -lt /Users/ruichengao/WorkflowBench/scale_up/scale_up/logs/debug_*.log | head -5
   grep -A 5 -B 5 "ERROR\|Exception\|Traceback" [相关debug日志]
   ```
3. **分析错误模式**：
   - 错误发生的时间点
   - 错误的频率（是否重复出现）
   - 错误的上下文（前后发生了什么）
   - 错误涉及的模型和配置

### 🎯 根本原因分析框架
**分析层次**：
- **日志证据**：从logs目录找到的实际错误信息和堆栈跟踪
- **直接原因**：导致错误的直接代码问题
- **根本原因**：更深层的设计或逻辑问题（接口设计、数据结构、状态管理、并发问题等）
- **设计意图**：理解代码背后的架构决策（如Parquet只存汇总）
- **一致性影响**：修复后需要更新的接口和相关文件

### 📝 解决方案原则
1. **基于日志证据**：修复必须针对logs中发现的实际错误
2. 使用知识库中已有的接口和函数
3. 遵循项目现有的设计模式
4. 避免硬编码，使用配置或常量
5. **禁止使用try-except**（需要直接暴露错误）
6. **禁止fallback方案**（缺少属性直接报错）
7. **必须输出完整函数**（禁止省略）
8. **理解设计意图**（如空操作可能是有意为之）

### 🔧 代码输出规范
- 必须输出完整函数，从函数定义到结束
- 包含所有必要的导入语句
- 在可能出错的地方添加print作为调试点
- 保持足够的上下文（至少10-15行）
- 使用配置文件中的常量，避免魔数
- 保留重要的设计注释（如"故意的空操作"）
- **在修复注释中引用日志文件名和行号**

### 📊 日志分析示例
**错误修复工作流示例**：
```bash
# 1. 找到最新错误
$ ls -lt logs/batch_test_*.log | head -1
logs/batch_test_20250818_001234.log

# 2. 查看错误详情
$ grep "ERROR" logs/batch_test_20250818_001234.log
[ERROR] Line 456: AttributeError: 'ParquetCumulativeManager' object has no attribute 'get_runtime_summary'

# 3. 查看错误上下文
$ sed -n '450,460p' logs/batch_test_20250818_001234.log

# 4. 基于日志证据修复代码
# 在parquet_cumulative_manager.py添加缺失的方法
# 参考：logs/batch_test_20250818_001234.log:456
```

### 🗄️ 存储格式设计规范
**Parquet格式核心设计**：
- **只存储汇总数据**，不存储单个测试记录（设计决策）
- `append_test_result()`返回True但不做操作是**正确的**
- 统计基于汇总数据，累加`total`字段而非计数行数
- 适用场景：大规模测试，关注统计结果

**JSON格式特性**：
- 存储完整测试记录和汇总
- 适用场景：小规模测试，需要详细记录

**修复存储相关问题时**：
1. 先确认使用的存储格式（STORAGE_FORMAT环境变量）
2. 理解该格式的设计意图
3. 不要将设计特性误判为bug

## 🔒 严格的开发规范 [强制执行]

### ⚠️ 强制管理命令（Claude Assistant必须遵守）

#### 🚨 每次代码修改前的强制流程
```bash
# 0. 检查日志文件（强制 - 新增）
ls -lt logs/batch_test_*.log | head -5
grep "ERROR\|Exception" logs/batch_test_*.log | tail -20

# 1. 备份当前文件（强制）
cp <target_file> <target_file>.backup_$(date +%Y%m%d_%H%M%S)

# 2. 创建分支（强制）
git checkout -b <type>/<description>

# 3. 运行测试（强制）
./test_parallel_fix.sh  # 或相应的测试脚本
```

#### 📝 每次修改后的强制更新
1. **立即更新DEBUG_HISTORY.md**
   ```markdown
   ### [日期] v[版本] - [简述]
   **文件**: [修改的文件]
   **行号**: [具体行号]
   **改动**: [具体改动内容]
   ```

2. **更新CHANGELOG.md**
   ```bash
   # 必须添加变更记录
   echo "## [版本] - $(date +%Y-%m-%d)" >> CHANGELOG.md
   ```

3. **更新CLAUDE.md维护记录**
   - 必须在"维护记录"部分添加条目
   - 必须更新版本号
   - 必须更新性能指标（如有变化）

### 必须遵守的规则

#### 1. 代码修改规范
- ❌ **禁止**创建fallback方法或简化版本
- ❌ **禁止**创建临时修复脚本（fix.py等）
- ❌ **禁止**使用模拟数据进行测试
- ❌ **禁止**直接在master分支修改
- ❌ **禁止**不备份就修改核心文件
- ✅ **必须**直接修复源文件
- ✅ **必须**理解现有代码结构后再修改
- ✅ **必须**使用完整功能的实现
- ✅ **必须**遵循git commit规范：`<type>(<scope>): <subject>`
- ✅ **必须**更新所有相关文档

#### 2. 文件管理规范
- ❌ **禁止**删除CLAUDE.md文件
- ❌ **禁止**删除核心配置文件
- ❌ **禁止**删除备份目录
- ❌ **禁止**删除DEBUG_HISTORY.md
- ❌ **禁止**删除CHANGELOG.md
- ✅ **必须**保留所有核心功能脚本
- ✅ **必须**定期备份重要数据
- ✅ **必须**维护文档同步

#### 3. 测试规范
- ✅ **必须**使用真实API进行测试
- ✅ **必须**记录所有测试结果
- ✅ **必须**处理所有错误情况
- ✅ **必须**验证修复的有效性
- ✅ **必须**在修改后运行回归测试

#### 4. 文档维护强制要求
每次代码修改必须同步更新：
- [ ] DEBUG_HISTORY.md - 添加调试记录
- [ ] CHANGELOG.md - 添加版本变更
- [ ] CLAUDE.md - 更新维护记录
- [ ] CODE_MANAGEMENT.md - 更新文件版本表

### 🔴 违规后果
如果不遵守以上规范：
1. 代码修改将被回滚
2. 需要重新按规范执行
3. 记录违规行为到日志

## 📈 性能指标追踪

### 关键指标
| 指标 | 目标值 | 当前值 | 状态 |
|------|--------|--------|------|
| API成功率 | >80% | 85-90% | 🟢 达标 |
| 工具覆盖率 | >90% | - | ⚫ 待测 |
| 平均响应时间 | <30s | ~25s | 🟢 达标 |
| 错误恢复率 | >70% | 75% | 🟢 达标 |
| **并发执行效率** | >60% | **63%** | 🟢 优秀 |
| **测试完成时间** | <30分钟 | **20分钟** | 🟢 优秀 |

### 错误分类统计
- **API超时**: 已增加到120秒超时，超时不再重试
- **参数错误**: 已移除不兼容参数
- **权限问题**: 部分IdealLab模型受限
- **任务超时**: 单任务10分钟硬限制，批次20分钟强制结束

## 🗂️ 项目结构

```
scale_up/
├── 📄 CLAUDE.md            # 本文档（核心，不可删除）
├── 📄 README.md            # 项目说明
├── 📄 QUICK_REFERENCE.md   # 快速参考
├── 📄 PROJECT_STRUCTURE.md # 结构说明
├── 📁 docs/                # 所有文档
│   ├── api/               # API文档
│   ├── guides/            # 使用指南
│   ├── architecture/      # 架构文档
│   ├── maintenance/       # 维护文档
│   └── reports/           # 测试报告
├── 📁 scripts/             # 脚本目录
│   └── test/             # 测试脚本
├── 📁 config/              # 配置文件
├── 📁 logs/                # 日志文件
└── 📁 pilot_bench_cumulative_results/ # 测试结果
```

## 🚨 重要警告

### 严禁删除的文件和目录
1. **CLAUDE.md** - 本文档，项目核心文档
2. **workflow_quality_results_backup_*/** - 历史备份数据
3. **config/** - 配置文件目录
4. **pilot_bench_cumulative_results/** - 测试数据库

### 重要的活跃目录
- `workflow_quality_results/` - 当前测试结果
- `checkpoints/` - 模型检查点
- `config/` - 配置文件
- `logs/` - 日志文件

## 📝 维护记录

### 2025-08-18 10:00 - 超时机制和数据保存重大修复 🚨
- ✅ **修复worker线程超时失效**
  - 问题：signal.SIGALRM只能在主线程工作，100个Azure worker在子线程中没有任何超时保护
  - 解决：使用嵌套ThreadPoolExecutor实现真正的超时控制
  - 影响：修复了测试运行8小时不结束的严重问题
- ✅ **修复数据不保存问题**
  - 问题：smart_batch_runner.py中enable_database_updates被错误设置为False
  - 解决：强制启用数据库实时更新
  - 影响：确保所有测试结果都被正确保存
- ✅ **优化超时处理**
  - API调用超时从60秒增加到120秒
  - 超时后不再重试（节省3分钟/次）
  - 所有模型统一10分钟任务超时
  - 批量任务20分钟强制结束
- ✅ **修复错误分类**
  - 修复"Test timeout after 10 minutes"被误分类为other_errors
  - 正确识别并计入timeout_errors统计
  - 默认启用GPT-5-nano分类提高准确性
- ✅ **性能大幅提升**
  - 时间节省：8小时→20分钟（节省95%）
  - 单任务：从可能永不结束到最多10分钟
  - API调用：从5分钟减少到2分钟
- 📊 当前版本：v3.1.0

### 2025-08-17 00:45 - API测试验证 ✅
- ✅ **验证所有bash脚本模型**：14个模型全部测试通过
- ✅ 创建API测试套件（3个测试脚本）
- ✅ 归档到scripts/test/api/目录
- ✅ 更新DEBUG_HISTORY.md和CHANGELOG.md
- 📊 当前版本：v2.3.0

### 2025-08-16 15:30 - 重大性能优化 🚀
- ✅ **修复关键并发问题**：分片执行从串行改为并发（性能提升63%）
- ✅ 创建调试历史文档系统 (DEBUG_HISTORY.md)
- ✅ 建立代码管理规范 (CODE_MANAGEMENT.md)
- ✅ 实现变更日志系统 (CHANGELOG.md)
- ✅ 优化进程输出管理（解决terminal泄露问题）
- 📊 当前版本：v1.2.0

### 2025-08-16 项目整理和模型更新
- ✅ 整理文档到相应目录（保留CLAUDE.md在根目录）
- ✅ 清理临时测试文件
- ✅ 修正DeepSeek-V3-0324分类
- ✅ 验证并添加gpt-5-mini
- ✅ 验证并添加kimi-k2
- ✅ 创建README.md和QUICK_REFERENCE.md
- ✅ 更新数据存储结构文档
- ✅ 完成5.1基准测试结果表创建
- ✅ 完成5.2 Qwen规模效应分析（含very_easy、easy、medium数据）
- ✅ 创建4.2.1规范汇总表
- ✅ 明确数据填表规则（默认使用optimal prompt）
- 📊 当前状态：77个Python文件，28个Shell脚本，36个MD文档

### 2025-08-15 API修复和优化
- ✅ 修复API超时问题（添加60秒timeout）
- ✅ 移除不兼容的max_tokens参数
- ✅ 配置Azure端点支持
- ✅ 实现智能模型路由

### 2025-08-14 自动维护系统
- ✅ 实现自动失败检测
- ✅ 添加智能重试机制
- ✅ 创建维护管理系统

### 2025-08-13 并行测试优化
- ✅ 实现超并行测试模式
- ✅ 添加多实例支持
- ✅ 优化并发策略

## 🎯 下一步计划

### 短期目标（本周）
- [ ] 提高API成功率到50%以上
- [ ] 完成5.1基准测试
- [ ] 修复所有已知的API问题
- [ ] 完善错误恢复机制

### 中期目标（本月）
- [ ] 完成所有开源模型测试
- [ ] 完成所有闭源模型测试
- [ ] 生成综合性能报告
- [ ] 优化系统性能

### 长期目标
- [ ] 实现完全自动化测试流程
- [ ] 添加更多模型支持
- [ ] 构建性能基准数据库
- [ ] 发布测试结果报告

## 🔍 快速命令参考

```bash
# 查看当前状态
./run_systematic_test_final.sh
选择：3) 📊 查看两种模型的进度

# 运行测试（推荐使用自定义workers数）
./run_systematic_test_final.sh --workers 20 --auto  # 稳定运行（推荐）
./run_systematic_test_final.sh --workers 50 --auto  # 中速运行
./run_systematic_test_final.sh --workers 100 --auto # 高速运行（需要足够内存）

# 组合参数使用
./run_systematic_test_final.sh --workers 30 --instances 10 --auto

# 查看进度
python view_test_progress.py

# 维护系统
python auto_failure_maintenance_system.py status

# 查看日志
tail -f logs/batch_test_*.log
```

## 📞 问题处理流程

1. **遇到问题时**：
   - 首先查看 `docs/maintenance/COMMON_ISSUES.md`
   - 检查 `logs/` 目录下的最新日志
   - 运行诊断脚本

2. **需要调试时**：
   - 查看 `docs/maintenance/DEBUG_KNOWLEDGE_BASE.md`
   - 使用调试模式运行
   - 记录所有错误信息

3. **提交修复时**：
   - 遵守代码规范
   - 添加适当的注释
   - 更新相关文档

---

---

## 📝 最新维护记录

### 2025-08-17 13:20 - 批处理返回值缺失修复 🔴
- ✅ **修复_run_single_test_safe缺少return语句**
  - 问题：batch_test_runner.py第1544行缺少return result
  - 影响：导致所有测试返回None，90个测试全部失败
  - 修复：添加return语句，所有测试恢复正常
- ✅ **数据恢复**
  - 创建restore_json_from_parquet.py脚本
  - 成功恢复197条测试记录（9个模型）
  - JSON数据库恢复完整性：83成功/114失败
- ✅ **系统文档更新**
  - 更新DEBUG_HISTORY.md添加FIX-20250817-004
  - 更新CHANGELOG.md发布v2.4.5
  - 创建完整修复文档2025-08-17_data_loss_fix.md
- 📊 当前版本：v2.4.5

### 2025-08-17 07:00 - 数据同步修复与文档更新
- ✅ **修复数据同步问题**
  - 识别并解决了JSON到Parquet同步时字段丢失问题
  - 恢复了包含完整41个字段的JSON备份
  - 使用sync_complete_json_to_parquet.py成功同步222条记录
  - 所有关键字段（质量分数、错误统计、辅助统计）现在都有值
- ✅ **更新同步脚本**
  - 添加自动过滤llama-4-scout-17b功能
  - 添加自动过滤unknown task_type功能
  - 添加数据质量检查和验证报告
- ✅ **更新系统文档**
  - 在CLAUDE.md中添加数据同步注意事项
  - 明确了41个必需字段的分类和要求
  - 添加了数据清理规则说明
- 📊 当前版本：v2.5.0

### 2025-08-17 07:30 - 5.3测试数据污染完整修复 🐛
- ✅ **彻底修复prompt_type简化问题**
  - 发现smart_batch_runner.py有两处代码都在简化prompt_type
  - 第220行：创建新任务时的简化（第一次修复）
  - 第655行：补充任务时的简化（本次追加修复）
  - 两处都改为保持原始prompt_type值
- ✅ **清理污染数据**
  - 清理了6条错误的DeepSeek-V3-0324记录
  - 包括被简化的"flawed"和错误的"baseline"记录
  - 同时清理了Parquet和JSON数据
- ✅ **验证修复效果**
  - 测试所有flawed类型都能正确保存
  - 确认缺陷注入机制不受影响
  - 创建完整的调试文档记录
- 📊 当前版本：v2.4.4

### 2025-08-17 06:30 - 数据清理与同步工具开发
- ✅ **创建JSON-Parquet双向同步工具**
  - 开发`sync_json_parquet.py`脚本，支持双向数据同步
  - 实现自动备份机制，保护原始数据
  - 添加数据验证功能，确保flawed记录有具体类型
- ✅ **清理无效测试数据**
  - 识别并删除10条无效的flawed记录（只有flawed没有具体类型）
  - 这些记录来自5.3测试运行时的配置问题
  - 清理后数据：234条有效记录，11个模型
- ✅ **数据同步与验证**
  - 成功同步Parquet和JSON数据，保持一致性
  - 验证所有83条flawed记录都有具体缺陷类型
  - 备份原始数据到`pilot_bench_cumulative_results/backups/`
- 📊 当前版本：v2.4.1

### 2025-08-17 05:30 - Parquet兼容性修复与代码整理
- ✅ **修复Parquet兼容性问题**
  - 为ParquetCumulativeManager添加三个缺失的兼容性方法
  - 修复AttributeError错误，确保与batch_test_runner.py完全兼容
  - 成功测试Parquet存储格式，验证241条记录正确保存
- ✅ **代码库整理**
  - 归档6个测试和数据迁移相关文件到`scripts/archive/`
  - 创建规范的目录结构：test、data_migration、debug、temp
  - 保持核心功能文件在主目录，提高项目可维护性
- ✅ **文档更新**
  - 更新DEBUG_HISTORY.md，添加FIX-20250817-002记录
  - 更新CHANGELOG.md，发布v2.4.0版本
  - 创建详细调试文档记录Parquet兼容性修复过程
- 📊 当前版本：v2.4.0

### 2025-08-17 15:30 - 全面修复环境变量传递问题 🔧
- ✅ **根因分析与诊断**
  - 发现run_systematic_test_final.sh中后台进程未正确传递环境变量
  - 识别6个关键位置需要修复（5.1-5.5各测试阶段）
  - 创建diagnose_5_3_issue.py诊断工具定位问题
- ✅ **全面修复实施**
  - 修复5.1基准测试后台进程环境变量传递（行3237）
  - 修复5.2 Qwen very_easy测试环境变量传递（行3353）
  - 修复5.2 Qwen medium测试环境变量传递（行3385）
  - 修复5.3缺陷工作流测试环境变量传递（行3539）
  - 修复5.4工具可靠性测试环境变量传递（行3718）
  - 修复5.5提示敏感性测试环境变量传递（行3925）
- ✅ **验证与测试工具**
  - 创建complete_fix.py自动修复脚本
  - 创建validate_complete_fix.sh验证脚本
  - 创建test_5_3_final.sh最终测试脚本
  - 确认所有6个测试阶段环境变量正确传递
- 📊 当前版本：v2.4.2

### 2025-08-18 00:30 - Parquet存储格式进度报告修复 🔧
- ❌ **初始错误理解**
  - 错误地认为Parquet格式应该存储单个测试记录
  - 修改了append_test_result方法添加增量文件（已回滚）
- ✅ **正确理解设计意图**
  - **Parquet格式设计为只存储汇总数据**，不存储单个记录
  - 这是有意的设计决策，用于提高性能和减少存储
- ✅ **修复进度报告问题**
  - 修复parquet_cumulative_manager.py的get_progress_report方法（行509-535）
  - 修复parquet_data_manager.py的compute_statistics方法（行207-266）
  - 现在正确累加汇总数据的total字段，而不是统计行数
- ✅ **验证修复效果**
  - DeepSeek-V3-0324: 151个测试正确显示
  - qwen2.5-72b-instruct: 750个测试正确显示
  - gpt-4o-mini: 14个测试正确显示
- ✅ **更新代码规范v5.0**
  - 将Parquet存储设计规范融入代码修复规范
  - 强调理解设计意图，避免误判设计特性为bug
  - 创建专门的设计文档PARQUET_STORAGE_DESIGN.md
- 📊 当前版本：v2.5.0

### 2025-08-18 11:15 - 测试5.3缺陷工作流并发现统计字段不一致问题
- ✅ **创建5.3缺陷工作流测试脚本**
  - 创建`test_5_3_flawed.sh`自动化测试脚本
  - 创建`test_5_3_single.sh`单模型测试脚本
  - 支持超并行模式运行7种缺陷类型测试
- ✅ **发现数据字段不一致bug**
  - 问题：数据库使用`success`字段，但查询代码查找`successful`字段
  - 影响：导致统计显示successful=0，但success_rate=100%
  - 示例：DeepSeek-V3-0324的simple_task实际有success=20，但查询显示successful=0
- ⚠️ **重要说明：关于run_systematic_test_final.sh脚本**
  - **这是默认的bash测试脚本** - 提到"bash脚本"或"测试脚本"时默认指此文件
  - 该脚本使用交互式菜单，需要用户输入选择
  - 包含5.1-5.5完整测试流程
  - 支持开源/闭源模型选择
  - 支持断点续测和进度保存
  - 可通过参数跳过交互：`--auto`, `--ultra-parallel`等
- 📊 当前版本：v2.5.1

### 2025-08-18 11:00 - 修复Parquet批量保存关键问题 🔥
- ✅ **修复checkpoint保存创建新manager实例问题**
  - **根本原因**：`batch_test_runner.py`的`_checkpoint_save`方法每次都创建新的EnhancedCumulativeManager实例
  - **影响**：新实例缓存为空，无法累积到100条记录触发auto-flush，导致数据永远不保存
  - **修复**：改为使用现有的self.manager实例（行1105-1106），保持缓存累积
  - **文件**：batch_test_runner.py，行1059-1122
- ✅ **解决测试进程卡死问题**
  - 发现24个进程运行超过8小时未终止（从凌晨2:45运行到上午10:50）
  - 网络连接显示为CLOSED但进程仍在运行，疑似死锁
  - 使用pkill终止所有卡住的smart_batch_runner进程
- ✅ **验证Parquet数据保存功能**
  - 运行小规模测试验证修复效果
  - 成功写入Parquet文件，今日记录从6条增加到7条
  - 文件最后修改时间更新到10:56:57，确认数据保存正常
- ✅ **关键发现**
  - 多进程环境下每个进程有独立内存空间，singleton模式无法跨进程共享
  - batch-commit模式下checkpoint保存是关键，必须使用同一manager实例
  - checkpoint_interval设置为20意味着每20个测试才保存一次
- 📊 当前版本：v2.5.0

### 2025-08-17 23:00 - 并发初始化问题诊断和修复
- ✅ **诊断并发初始化问题**
  - 发现150个workers同时初始化MDPWorkflowGenerator
  - 每个线程创建独立实例，导致内存耗尽
  - 日志显示多个BatchTestRunner同时初始化
- ✅ **识别数据未保存原因**
  - 程序在workflow生成后崩溃，未到执行阶段
  - 数据库最后更新时间：凌晨4:30
  - 没有数据被flush到磁盘
- ✅ **创建诊断和修复工具**
  - diagnose_concurrent_issue.py：诊断并发问题
  - fix_concurrent_initialization.py：单例模式修复方案
  - 建议降低workers数量到20-30个
- ✅ **更新代码规范**
  - 添加v4.0代码修复规范
  - 强调禁止try-except和fallback
  - 要求完整函数输出
- 📊 当前版本：v2.4.4

### 2025-08-17 20:50 - 任务ID兼容性和超时优化
- ✅ **修复任务ID显示问题**
  - 添加instance_id和id字段的兼容性处理
  - 任务库使用instance_id，代码期望id，导致显示为"unknown"
  - 修改batch_test_runner.py多处代码支持两种字段
- ✅ **优化批处理超时机制**
  - 将批处理超时从固定20分钟改为动态计算
  - 新策略：每个任务30秒，至少30分钟，最多2小时
  - 解决了120个任务在20分钟内被强制终止的问题
- ✅ **诊断测试停止原因**
  - 发现日志在workflow生成后立即停止
  - 批处理超时设置过短导致所有测试被终止
  - 任务ID显示为unknown影响调试
- 📊 当前版本：v2.4.3

---

**文档版本**: 3.1.0
**创建时间**: 2025-08-02 01:00:00
**最后更新**: 2025-08-18 11:00:00
**维护者**: Claude Assistant
**状态**: 🟢 Active | ✅ 项目已重构 | 📊 文档已完善 | 🚀 性能已优化
**管理级别**: 🔴 STRICT - 所有修改必须遵守强制流程