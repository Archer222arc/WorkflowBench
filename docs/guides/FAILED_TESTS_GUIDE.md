# 失败测试重新运行系统使用指南

## 🎯 系统概述

这个系统提供了一套完整的失败测试管理和重新运行机制，用于处理在并发测试中因超时或其他原因失败的测试组。

## 📋 主要组件

### 1. 失败测试配置文件 (`failed_tests_config.json`)
- 记录失败测试的详细信息
- 包含模型、测试组、失败原因等结构化数据
- 支持版本化管理和追踪

### 2. 失败测试管理器 (`failed_tests_manager.sh`)
- 提供读取和处理失败测试配置的函数
- 支持概要显示、详细信息查看等功能
- 可独立使用或集成到其他脚本

### 3. 系统化测试脚本集成
- 在主测试脚本中集成了失败测试重新运行选项
- 支持交互式菜单操作
- 提供多种重测策略

## 🚀 使用方法

### 方法一：通过主测试脚本（推荐）

```bash
./run_systematic_test_final.sh
```

在主菜单中，如果检测到失败测试记录，会显示：
```
1) 🔄 继续上次测试
2) 🆕 完全重新开始（清理所有数据）
3) 📊 查看详细进度
4) 🎯 自定义起始阶段
5) 🔧 重新测试失败的组    <- 新增选项
6) ❌ 退出
```

选择 `5) 🔧 重新测试失败的组` 进入失败测试管理菜单。

### 方法二：独立使用失败测试管理器

```bash
# 导入管理器函数
source failed_tests_manager.sh

# 查看失败测试概要
show_failed_tests_summary

# 查看详细信息
show_failed_tests_details

# 生成重测命令
generate_retest_commands

# 检查特定模型是否在失败列表中
is_model_in_failed_list "qwen2.5-3b-instruct"
```

### 方法三：使用独立重测脚本

```bash
./rerun_failed_tests.sh
```

## 📊 失败测试管理菜单功能

### 1. 📖 查看详细失败信息
- 显示每个失败模型的具体信息
- 包含失败原因、测试参数等
- 列出需要重测的所有测试组

### 2. 🔄 重新运行所有失败的测试
- 自动运行所有失败和未完成的测试组
- 支持超时保护（2小时）
- 提供实时进度反馈和最终统计

### 3. 🎯 选择特定模型重新测试
- 可以选择单个模型进行重测
- 只重测选定模型的失败和剩余测试组
- 适合针对性问题解决

### 4. 🧹 清除失败测试记录
- 删除失败测试配置文件
- 清理后将不再显示失败测试选项
- 需要确认操作

## 🔧 配置文件结构

`failed_tests_config.json` 的结构：

```json
{
  "failed_tests_session": {
    "session_date": "2025-08-14",
    "session_description": "5.3 缺陷工作流测试中的超时失败",
    "total_failed_models": 4,
    "failed_groups": [
      {
        "model": "qwen2.5-3b-instruct",
        "status": "timeout_failed",
        "failed_groups": [
          {
            "group_name": "结构缺陷组",
            "prompt_types": "flawed_sequence_disorder,flawed_tool_misuse,flawed_parameter_error",
            "reason": "分片 qwen2.5-3b-instruct_easy_2 超时"
          }
        ],
        "remaining_groups": [
          {
            "group_name": "操作缺陷组",
            "prompt_types": "flawed_missing_step,flawed_redundant_operations"
          }
        ]
      }
    ],
    "test_parameters": {
      "difficulty": "easy",
      "task_types": "all", 
      "num_instances": 20
    },
    "cleanup_status": {
      "database_cleaned": true,
      "backup_created": "path/to/backup",
      "deleted_models": ["model1", "model2"]
    }
  }
}
```

## 📝 典型工作流程

### 1. 检测失败
当并发测试出现超时或失败时：
```bash
# 终止所有进程
pkill -f "python.*ultra_parallel_runner"

# 记录失败信息
# (手动或自动创建 failed_tests_config.json)
```

### 2. 清理数据库
```bash
python cleanup_timeout_results.py
```

### 3. 重新测试
```bash
./run_systematic_test_final.sh
# 选择 5) 🔧 重新测试失败的组
# 然后选择 2) 🔄 重新运行所有失败的测试
```

### 4. 验证结果
重测完成后，检查是否所有测试都已成功：
- 查看测试统计
- 检查数据库中的结果
- 如果成功，可以清除失败测试记录

## ⚠️ 注意事项

### 1. 超时设置
- 重测时设置了2小时超时保护
- 可以根据实际情况调整超时时间

### 2. 并发控制
- 重测时会使用 `ultra_parallel_runner.py`
- 确保系统资源足够支持并发测试

### 3. 数据安全
- 在清理数据库前会自动创建备份
- 失败测试记录可以手动备份

### 4. 依赖检查
- 确保 `ultra_parallel_runner.py` 存在且可执行
- 确保 Python 环境正确配置

## 🔍 故障排除

### 1. 配置文件问题
```bash
# 检查配置文件是否存在和格式正确
python -c "import json; print(json.load(open('failed_tests_config.json')))"
```

### 2. 权限问题
```bash
# 确保脚本有执行权限
chmod +x failed_tests_manager.sh
chmod +x run_systematic_test_final.sh
```

### 3. 依赖缺失
```bash
# 检查必要的文件
ls -la failed_tests_config.json failed_tests_manager.sh ultra_parallel_runner.py
```

## 📈 扩展功能

这个系统可以扩展支持：
- 自动失败检测和记录
- 更细粒度的重测控制
- 失败模式分析和预防
- 与 CI/CD 系统集成
- 测试结果可视化

## 📞 技术支持

如果遇到问题，请检查：
1. 日志文件中的错误信息
2. 配置文件的格式正确性
3. 系统资源是否充足
4. 网络连接是否稳定