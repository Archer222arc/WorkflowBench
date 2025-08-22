# 代码库管理规范 v1.0

## 1. 版本控制规范

### 1.1 版本号规则 (Semantic Versioning)
格式：`MAJOR.MINOR.PATCH`
- **MAJOR**: 不兼容的API修改
- **MINOR**: 向后兼容的功能性新增
- **PATCH**: 向后兼容的问题修复

示例：
- `1.0.0` → `2.0.0`：重构并发机制（不兼容）
- `1.0.0` → `1.1.0`：添加新的测试模式（兼容）
- `1.0.0` → `1.0.1`：修复输出泄露问题（兼容）

### 1.2 分支管理
```
master (主分支)
├── develop (开发分支)
├── feature/* (功能分支)
├── bugfix/* (修复分支)
└── hotfix/* (紧急修复)
```

### 1.3 提交规范
格式：`<type>(<scope>): <subject>`

**Type类型**:
- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档更新
- `perf`: 性能优化
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/辅助工具

**示例**:
```bash
git commit -m "fix(ultra_parallel): 修复分片间串行等待问题"
git commit -m "perf(batch_runner): 优化API并发度到150"
git commit -m "docs(debug): 添加调试历史文档"
```

## 2. 代码变更流程

### 2.1 变更前检查清单
- [ ] 问题是否已在DEBUG_HISTORY.md中记录？
- [ ] 是否有相关的issue或任务？
- [ ] 影响范围评估完成？
- [ ] 是否需要备份原代码？

### 2.2 变更实施
1. **创建分支**
   ```bash
   git checkout -b bugfix/parallel-execution
   ```

2. **编写代码**
   - 遵循现有代码风格
   - 添加必要的注释
   - 保持向后兼容

3. **测试验证**
   ```bash
   # 单元测试
   python -m pytest tests/
   
   # 集成测试
   ./test_parallel_fix.sh
   ```

4. **提交变更**
   ```bash
   git add -p  # 交互式添加
   git commit  # 使用规范的提交信息
   ```

### 2.3 变更后文档
- 更新 `DEBUG_HISTORY.md`
- 更新 `CHANGELOG.md`
- 更新相关的使用文档

## 3. 关键文件版本追踪

### 核心文件清单
| 文件 | 用途 | 最后修改 | 版本 |
|------|------|----------|------|
| ultra_parallel_runner.py | 超并发执行器 | 2025-08-16 | v1.2.0 |
| smart_batch_runner.py | 智能批处理 | 2025-08-15 | v1.1.0 |
| batch_test_runner.py | 基础批处理 | 2025-08-14 | v1.0.5 |
| file_lock_manager.py | 文件锁管理 | 2025-08-16 | v1.0.0 |
| cumulative_data_structure.py | 数据结构 | 2025-08-15 | v3.0.0 |

### 配置文件
| 文件 | 用途 | 修改频率 |
|------|------|----------|
| CLAUDE.md | 项目主文档 | 每日 |
| config/api_config.json | API配置 | 每周 |
| config/model_routing.json | 模型路由 | 每周 |

## 4. 备份策略

### 4.1 自动备份
```python
# 在修改关键文件前自动备份
import shutil
from datetime import datetime

def backup_file(filepath):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{filepath}.backup_{timestamp}"
    shutil.copy2(filepath, backup_path)
    return backup_path
```

### 4.2 手动备份点
- 每次major版本发布前
- 重大重构前
- 批量测试前

### 4.3 备份位置
```
backups/
├── code/          # 代码备份
├── data/          # 数据备份
└── config/        # 配置备份
```

## 5. 代码审查清单

### 性能相关
- [ ] 是否存在串行瓶颈？
- [ ] 并发度是否合理？
- [ ] 是否有不必要的等待？

### 稳定性相关
- [ ] 错误处理是否完善？
- [ ] 是否有资源泄露？
- [ ] 并发安全性？

### 可维护性
- [ ] 代码是否易读？
- [ ] 注释是否充分？
- [ ] 是否遵循DRY原则？

## 6. 紧急回滚程序

### 快速回滚命令
```bash
# 查看最近的提交
git log --oneline -10

# 回滚到指定版本
git revert <commit-hash>

# 或者硬回滚（慎用）
git reset --hard <commit-hash>
```

### 备份恢复
```bash
# 从备份恢复
cp ultra_parallel_runner.py.backup_20250816_150000 ultra_parallel_runner.py
```

## 7. 监控与告警

### 关键指标监控
```python
# 监控脚本示例
def monitor_performance():
    metrics = {
        'api_success_rate': check_api_success(),
        'avg_response_time': get_avg_response_time(),
        'concurrent_processes': count_processes(),
        'db_write_failures': check_db_failures()
    }
    
    # 告警阈值
    if metrics['api_success_rate'] < 0.8:
        send_alert("API成功率低于80%")
    if metrics['avg_response_time'] > 60:
        send_alert("平均响应时间超过60秒")
```

### 日志规范
```python
import logging

# 统一日志格式
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    level=logging.INFO
)

# 关键操作必须记录
logger.info(f"开始并发测试: {model} - {num_instances} instances")
logger.error(f"分片执行失败: {shard_id} - {error}")
```

## 8. 文档同步

### 需要同步更新的文档
1. **代码修改时**:
   - DEBUG_HISTORY.md
   - CHANGELOG.md
   - 相关的API文档

2. **配置修改时**:
   - CLAUDE.md
   - CONFIG_GUIDE.md

3. **性能优化时**:
   - PERFORMANCE_BENCHMARK.md
   - DEBUG_HISTORY.md

### 文档模板
```markdown
## [日期] - [版本号]
### 问题
- 简要描述

### 解决方案
- 具体措施

### 影响
- 性能提升
- 副作用

### 验证
- 测试结果
```

## 10. 文件版本追踪表

### 核心文件修改记录
| 文件名 | 当前版本 | 最后修改 | 修改内容 | 影响范围 |
|--------|----------|----------|----------|----------|
| run_systematic_test_final.sh | v2.4.6 | 2025-08-17 | 修复环境变量传递（6处） | 5.1-5.5所有测试 |
| smart_batch_runner.py | v2.4.4 | 2025-08-17 | 修复prompt_type简化（2处） | 5.3缺陷测试 |
| batch_test_runner.py | v2.4.5 | 2025-08-17 | 添加return语句（行1544） | 所有批处理测试 |
| enhanced_cumulative_manager.py | v2.4.0 | 2025-08-17 | Parquet兼容性修复 | 数据存储 |
| parquet_cumulative_manager.py | v2.4.0 | 2025-08-17 | 添加兼容性方法 | Parquet存储 |

### 修复脚本归档记录
| 日期 | 问题 | 脚本数量 | 归档位置 |
|------|------|----------|----------|
| 2025-08-17 | 环境变量传递 | 10个 | scripts/fixes/env_variable_fix_20250817/ |
| 2025-08-17 | Parquet兼容性 | 6个 | scripts/archive/data_migration/ |
| 2025-08-16 | 并发性能 | 8个 | scripts/archive/test/ |

---
最后更新: 2025-08-17
版本: 1.1.0
维护者: Claude Assistant