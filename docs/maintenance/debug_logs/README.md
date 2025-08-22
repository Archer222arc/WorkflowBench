# 调试记录库说明

## 目录结构

```
debug_logs/
├── README.md                                    # 本文档
├── template.md                                  # 修改记录模板
├── 2025-08-16_parallel_fix.md                 # 并发执行优化（v1.2.0）
├── 2025-08-16_concurrent_write_fix.md          # 并发写入修复（v2.1.0→v2.2.0）
├── 2025-08-16_file_lock_implementation.md      # 文件锁机制（v1.1.0）
├── 2025-08-16_storage_system_upgrade.md        # 存储系统升级（v2.2.0）
└── 2025-08-15_api_timeout_fixes.md             # API超时修复（v1.0.0）
```

## 文件命名规范

格式：`YYYY-MM-DD_brief_description.md`

示例：
- `2025-08-16_parallel_fix.md` - 并发执行修复
- `2025-08-17_api_timeout.md` - API超时问题
- `2025-08-18_memory_leak.md` - 内存泄露修复

## 修改ID规范

格式：`TYPE-YYYYMMDD-XXX`

- **TYPE**: 
  - `FIX` - Bug修复
  - `FEAT` - 新功能
  - `PERF` - 性能优化
  - `REFACTOR` - 重构
  
- **YYYYMMDD**: 日期
- **XXX**: 当日序号（001-999）

示例：`FIX-20250816-001`

## 必填内容

每个修改记录必须包含：

1. **基本信息**
   - 修改ID
   - 时间戳
   - 修改者
   - 版本变化
   - 标签

2. **问题描述**
   - 用户反馈
   - 问题分析
   - 根本原因

3. **修改详情**
   - 具体文件
   - 行号范围
   - 代码对比

4. **测试结果**
   - 性能对比
   - 验证方法

5. **风险评估**
   - 副作用
   - 回滚方案

## 快速创建新记录

```bash
# 复制模板
cp template.md YYYY-MM-DD_description.md

# 编辑新文件
vim YYYY-MM-DD_description.md
```

## 搜索历史记录

```bash
# 按关键词搜索
grep -r "并发" *.md

# 按日期搜索
ls -la 2025-08-*.md

# 按类型搜索
grep -l "TYPE: performance" *.md
```

## 📚 现有文档索引

### 按时间排序
- **2025-08-15**: [API超时修复](./2025-08-15_api_timeout_fixes.md) - 解决API调用超时和重试机制
- **2025-08-16**: [文件锁实现](./2025-08-16_file_lock_implementation.md) - 防止并发写入冲突
- **2025-08-16**: [并发执行优化](./2025-08-16_parallel_fix.md) - 修复串行等待问题
- **2025-08-16**: [并发写入修复](./2025-08-16_concurrent_write_fix.md) - 解决数据不稳定问题
- **2025-08-16**: [存储系统升级](./2025-08-16_storage_system_upgrade.md) - Parquet增量存储

### 按问题类型
- **性能优化**: parallel_fix.md, storage_system_upgrade.md
- **数据完整性**: file_lock_implementation.md, concurrent_write_fix.md
- **网络稳定性**: api_timeout_fixes.md

### 按影响范围
- **系统级**: storage_system_upgrade.md (影响所有数据存储)
- **并发级**: parallel_fix.md, file_lock_implementation.md
- **API级**: api_timeout_fixes.md

## 维护规范

1. **及时性**: 修改完成后立即创建记录
2. **完整性**: 所有字段都要填写
3. **准确性**: 代码示例要准确
4. **可追溯**: 保留所有备份路径
5. **层次化**: 详细内容放在独立文件，索引保持简洁

## 🔗 相关文档
- [DEBUG_HISTORY.md](../DEBUG_HISTORY.md) - 主调试历史索引
- [CLAUDE.md](../../../CLAUDE.md) - 项目总体文档

---
最后更新: 2025-08-16 17:00:00
维护者: Claude Assistant