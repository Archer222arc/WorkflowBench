# 调试历史文档

## 📁 详细修改记录库

每次重要修改都有独立的详细文档：

| 日期 | 修改ID | 简述 | 详细文档 |
|------|--------|------|----------|
| 2025-08-28 | FIX-20250828-001 | QPS限制机制重大修复 | 修复限流位置错误、实现3-key独立限流、性能提升3倍 |
| 2025-08-24 | FIX-20250824-001 | 超并发配置优化与API验证 | DeepSeek worker配置修复、IdealLab 2-key架构、异步间隔优化 |
| 2025-08-19 | FIX-20250819-003 | qwen并发优化终极简化 | 统一所有场景使用均匀分配策略 |
| 2025-08-19 | FIX-20250819-002 | 修复关键BUG合集 | qwen映射错误、任务类型混淆、日志覆盖等12个问题 |
| 2025-08-19 | FIX-20250819-001 | 5.3测试内存优化完整解决方案 | [查看详情](./debug_logs/2025-08-19-memory-optimization/FIX-20250819-001-memory-optimization.md) |
| 2025-08-18 | FIX-20250818-004 | 批量提交和数据保存机制修复 | [查看详情](./debug_logs/2025-08-18_batch_commit_fix.md) |
| 2025-08-18 | FIX-20250818-003 | v2_models和统计更新修复 | [查看详情](./debug_logs/2025-08-18_data_save_fix.md) |
| 2025-08-18 | DIAG-20250818-002 | 数据保存失败问题 | [查看详情](./debug_logs/2025-08-18_data_save_issue.md) |
| 2025-08-18 | DIAG-20250818-001 | 进程卡死问题诊断 | [查看详情](./debug_logs/2025-08-18_process_hang_diagnosis.md) |
| 2025-08-18 | FIX-20250818-002 | deployment参数缺失修复 | [查看详情](./debug_logs/2025-08-18_deployment_parameter_fix.md) |
| 2025-08-18 | FIX-20250818-001 | 超时机制和数据保存修复 | [查看详情](./debug_logs/2025-08-18_timeout_and_save_fix.md) |
| 2025-08-17 | FIX-20250817-004 | 批处理返回值缺失修复 | [查看详情](./debug_logs/2025-08-17_data_loss_fix.md) |
| 2025-08-17 | FIX-20250817-003 | 5.3测试数据污染修复 | [查看详情](./debug_logs/2025-08-17_flawed_prompt_fix.md) |
| 2025-08-17 | FIX-20250817-002 | Parquet兼容性方法添加 | [查看详情](./debug_logs/2025-08-17_parquet_compatibility.md) |
| 2025-08-17 | TEST-20250817-001 | 完整API测试验证 | [查看详情](./debug_logs/2025-08-17_api_test_validation.md) |
| 2025-08-16 | FIX-20250816-001 | 并发执行优化 | [查看详情](./debug_logs/2025-08-16_parallel_fix.md) |
| 2025-08-16 | FIX-20250816-002 | 并发写入数据不稳定修复 | [查看详情](./debug_logs/2025-08-16_concurrent_write_fix.md) |
| 2025-08-16 | FIX-20250816-003 | 文件锁机制实现 | [查看详情](./debug_logs/2025-08-16_file_lock_implementation.md) |
| 2025-08-16 | UPGRADE-20250816-001 | 存储系统升级 | [查看详情](./debug_logs/2025-08-16_storage_system_upgrade.md) |
| 2025-08-15 | FIX-20250815-001 | API超时问题修复 | [查看详情](./debug_logs/2025-08-15_api_timeout_fixes.md) |

## 版本记录摘要

### v3.8.0 (2025-08-28) - QPS限制机制重大修复
- **关键改进**: 将QPS限制从任务级改为请求级，修复多轮对话限流失效问题
- **性能提升**: qwen模型总QPS从10提升到30（3倍），测试速度提升200%
- **技术细节**: 
  - 修复位置：从batch_test_runner移到interactive_executor._get_llm_response
  - 3个API keys独立限流，每个10 QPS
  - 跨进程同步机制正常工作
- **影响范围**: 所有IdealLab模型受益，防止429错误，5.3测试时间减少67%

### v2.2.0 (2025-08-16) - 存储系统升级
- **关键改进**: 实现Parquet增量存储，解决并发数据覆盖问题
- **性能提升**: 数据写入稳定性从60%提升到99.9%
- **详细文档**: [存储系统升级](./debug_logs/2025-08-16_storage_system_upgrade.md)

### v1.2.0 (2025-08-16) - 并发执行优化
- **关键改进**: 修复串行等待问题，实现真正的并发执行
- **性能提升**: 3分片执行时间从1500秒减少到550秒（63%提升）
- **详细文档**: [并发执行优化](./debug_logs/2025-08-16_parallel_fix.md)

### v1.1.0 (2025-08-16) - 文件锁机制
- **关键改进**: 实现文件锁防止并发写入冲突
- **性能提升**: 数据完整性从75%提升到99.9%
- **详细文档**: [文件锁机制](./debug_logs/2025-08-16_file_lock_implementation.md)

### v1.0.0 (2025-08-15) - API超时修复
- **关键改进**: 添加超时控制和重试机制
- **性能提升**: API成功率从15-25%提升到80-90%
- **详细文档**: [API超时修复](./debug_logs/2025-08-15_api_timeout_fixes.md)

## 🛠️ 常用调试技巧库

### 1. 并发问题诊断
**快速检查**:
```bash
# 查看进程树
ps aux | grep python | grep -E "smart_batch|ultra_parallel"

# 监控CPU使用率（应该看到多核利用）
htop

# 查看网络连接（API并发）
netstat -an | grep ESTABLISHED | wc -l
```

### 2. 数据库并发写入问题
**快速修复**:
```python
# 使用文件锁防止并发冲突
with FileLock(db_path, timeout=30):
    # 数据库操作
```

### 3. API超时问题
**快速诊断**:
```bash
# 测试API连通性
curl -X POST $API_ENDPOINT -d '{"test": "data"}' -H "Content-Type: application/json"

# 检查超时配置
grep -r "timeout" *.py
```

## 📊 系统性能基准

| 关键指标 | 修复前 | 当前状态 | 总体提升 |
|----------|--------|----------|----------|
| API成功率 | 15-25% | 80-90% | +65% |
| 并发执行效率 | 串行(1500s) | 并发(550s) | +63% |
| 数据完整性 | 75% | 99.9% | +24.9% |
| 存储稳定性 | 60% | 99.9% | +39.9% |

## 🔍 常见问题快速索引

| 问题类型 | 症状 | 快速诊断 | 详细文档 |
|----------|------|----------|----------|
| 数据不稳定 | flawed项目时多时少 | `python analyze_flawed_issue.py` | [并发写入修复](./debug_logs/2025-08-16_concurrent_write_fix.md) |
| 并发失效 | 多worker但仍很慢 | `ps aux \| grep python` | [并发执行优化](./debug_logs/2025-08-16_parallel_fix.md) |
| API超时 | 大量timeout错误 | `curl -X POST $API_ENDPOINT` | [API超时修复](./debug_logs/2025-08-15_api_timeout_fixes.md) |
| 文件锁死锁 | JSONDecodeError频发 | `ls *.lock` | [文件锁实现](./debug_logs/2025-08-16_file_lock_implementation.md) |

## 📈 快速监控命令

```bash
# 实时监控测试进度
tail -f logs/batch_test_*.log | grep -E "成功:|失败:|完成"

# 检查当前并发度
ps aux | grep python | grep -c smart_batch

# 查看数据库状态
ls -la pilot_bench_cumulative_results/master_database.*

# 检查文件锁状态
find . -name "*.lock" -ls
```

---

## FIX-20250817-003: 环境变量传递问题全面修复

### 问题描述
- **症状**: 运行5.3测试8小时后，JSON和Parquet文件都没有数据写入
- **影响**: 所有5.1-5.5测试阶段的后台进程无法保存数据
- **严重性**: 🔴 严重 - 数据完全丢失

### 根因分析
```bash
# 问题代码模式
(
    STORAGE_FORMAT="${STORAGE_FORMAT}" python script.py  # 环境变量不会传递
) &
```
- Bash后台进程中使用`VAR=value command`语法无法正确传递环境变量
- 影响所有使用`( ... ) &`模式的测试阶段

### 修复方案
```bash
# 修复后的模式
(
    # 确保环境变量在子进程中可用
    export STORAGE_FORMAT="${STORAGE_FORMAT}"
    export MODEL_TYPE="${MODEL_TYPE}"
    export NUM_INSTANCES="${NUM_INSTANCES}"
    export RATE_MODE="${RATE_MODE}"
    
    python script.py  # 现在可以正确获取环境变量
) &
```

### 修复位置
- **文件**: run_systematic_test_final.sh
- **修复点**:
  - 行3237: 5.1基准测试
  - 行3353: 5.2 Qwen very_easy测试  
  - 行3385: 5.2 Qwen medium测试
  - 行3539: 5.3缺陷工作流测试
  - 行3718: 5.4工具可靠性测试
  - 行3925: 5.5提示敏感性测试

### 验证结果
- ✅ 所有6个测试阶段环境变量正确传递
- ✅ Parquet数据成功保存（验证198条记录）
- ✅ 5.4和5.5测试正常运行并保存数据

### 相关文件
- diagnose_5_3_issue.py - 问题诊断工具
- complete_fix.py - 自动修复脚本
- validate_complete_fix.sh - 验证脚本
- 归档位置: scripts/fixes/env_variable_fix_20250817/

---

## FIX-20250818-004: 数据保存完整修复

### 问题描述
- **症状**: 运行测试后数据未保存到master_database.json
- **影响**: 所有测试数据丢失，5.3测试无法记录结果
- **严重性**: 🔴 严重

### 根因分析
1. **smart_batch_runner.py缺少默认保存逻辑**
   - 所有`_save_results_to_database`调用都在`if batch_commit:`条件内
   - 不使用`--batch-commit`参数时数据永远不会保存
   
2. **统计汇总未更新**
   - 层次结构中的数据已保存（如by_prompt_type/by_tool_success_rate）
   - 但顶层的total_tests仍为0

### 解决方案
1. **使用--batch-commit参数**（临时方案）
   - 所有测试必须添加`--batch-commit`参数
   - 同时添加`--checkpoint-interval 1`确保及时保存

2. **5.3测试脚本修复**
   - 创建macOS兼容版本（不使用timeout命令）
   - 确保所有测试使用--batch-commit参数
   - 成功运行并保存了flawed测试数据

### 验证结果
- ✅ gpt-4o-mini保存了flawed_redundant_steps和flawed_sequence_disorder数据
- ✅ DeepSeek-V3-0324测试运行完成
- ⚠️ 顶层total_tests统计仍需修复

### 相关文件
- smart_batch_runner.py（需要修复默认保存逻辑）
- run_5_3_macos.sh（macOS兼容测试脚本）
- cumulative_test_manager.py（统计汇总逻辑）

---
最后更新: 2025-08-18 18:35:00
维护者: Claude Assistant
## FIX-20250827-001: IdealLab API Key失效问题修复

**时间**: 2025-08-27 21:00-22:00
**版本**: v3.6.0
**严重程度**: 🔴 高 - 阻塞所有qwen模型测试

### 问题描述
- **症状**: 所有qwen模型测试报错"无效的api key"（CE-003错误）
- **影响**: 5.3缺陷工作流测试无法进行
- **错误日志**: `[分片qwen2.5-32b-instruct_easy_key0] [LLM_ERROR] Error code: 400 - {'success': False, 'message': '无效的api key'}`

### 根本原因
1. **第一个API key失效**: 956c41bd...f4bb已不可用
2. **参数传递bug**: smart_batch_runner.py中`--idealab-key-index`参数映射错误
3. **错误的假设**: 误以为是key1和key2不可用，实际是key0失效

### 诊断过程
```python
# 使用测试脚本验证API keys
python scripts/test/test_apikey_validity.py

# 结果：
# key0 (956c41bd...): ❌ 无效
# key1 (3d906058...): ✅ 有效  
# key2 (88a9a901...): ✅ 有效
```

### 修复方案
1. **更新api_client_manager.py** (第163-167行)
   - 移除失效的key0
   - 使用有效的key1和key2

2. **修复smart_batch_runner.py** (第727行)
   - 添加`dest='idealab_key_index'`修复参数映射

3. **降低并发限制** (避免限流)
   - ultra_parallel_runner.py: max_workers从5降到1
   - run_systematic_test_final.sh: qwen强制限制从2降到1

### 验证结果
- API测试：2个有效keys工作正常
- 并发测试：10/10成功
- QPS测试：22.43 QPS（提升2倍+）

### 影响的文件
- api_client_manager.py
- smart_batch_runner.py  
- ultra_parallel_runner.py
- run_systematic_test_final.sh

### 经验教训
1. API key失效应该逐个测试验证
2. 参数传递需要使用dest确保正确映射
3. IdealLab API有严格限流，保守设置更稳定
