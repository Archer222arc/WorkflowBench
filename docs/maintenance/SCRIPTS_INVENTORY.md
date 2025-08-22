# 项目脚本清单

## 📋 脚本分类总览

经过清理后，项目中保留了以下有用的脚本文件，按功能分类整理：

### 🚀 核心系统脚本

#### MDP框架核心
- `generalized_mdp_framework.py` - MDP框架核心实现
- `unified_training_manager.py` - 统一训练管理器
- `mdp_workflow_generator.py` - MDP工作流生成器

#### 工作流处理
- `workflow_quality_test_flawed.py` - 工作流质量测试（主要版本）
- `flawed_workflow_generator.py` - 缺陷工作流生成器
- `interactive_executor.py` - 交互式执行器

#### 工具和管理
- `api_client_manager.py` - API客户端管理
- `tool_capability_manager.py` - 工具能力管理
- `mcp_embedding_manager.py` - MCP嵌入管理
- `operation_embedding_index.py` - 操作嵌入索引

### 🎯 训练和优化脚本

#### GPU训练
- `gpu_training_script.py` - RTX 4070 GPU训练脚本
- `gpu_training_script_H100.py` - H100 GPU训练脚本
- `train_ppo_m1_overnight.py` - M1芯片PPO过夜训练

#### 训练管理
- `unified_training_manager_dqn.py` - DQN训练管理器
- `smart_progressive_training.py` - 智能渐进训练
- `monitor_training.py` - 训练监控

#### 优化和测试
- `optimize_scoring_params.py` - 评分参数优化
- `repeat_best_params_test.py` - 最佳参数重复测试
- `phase2_scoring_improvement.py` - 阶段2评分改进

### 🧪 测试和验证脚本

#### 质量测试
- `workflow_quality_test.py` - 基础工作流质量测试
- `workflow_quality_test_bac.py` - 工作流质量测试备份版本
- `test_phase2_improvement.py` - 阶段2改进测试
- `current_progress_test.py` - 当前进度测试

#### 验证脚本
- `verify_phase23_complete.py` - 阶段2/3完成验证
- `verify_phase23_fixes.py` - 阶段2/3修复验证
- `test_model_compatibility.py` - 模型兼容性测试（新增）

### 📊 分析和可视化脚本

#### 数据分析
- `smart_regenerate_analysis.py` - 智能重新生成分析
- `diagnose_scoring_issue.py` - 评分问题诊断
- `diagnose_training.py` - 训练诊断
- `diagnose_workflow_issues.py` - 工作流问题诊断

#### 可视化
- `visualization_utils.py` - 可视化工具
- `visualize_flawed_results.py` - 缺陷结果可视化
- `training_curves_visualizer.py` - 训练曲线可视化
- `unified_visualization_system.py` - 统一可视化系统

### 🛠️ 工具和管理脚本

#### 任务生成
- `tool_and_task_generator.py` - 工具和任务生成器
- `enhance_task_descriptions.py` - 任务描述增强

#### 执行管理
- `run_phase2_test.py` - 运行阶段2测试
- `phase123_complete_integration.py` - 阶段1-3完整集成
- `phase23_reinforcement_training.py` - 阶段2/3强化训练

#### 工作流推理
- `workflow_reasoning_generator.py` - 工作流推理生成器
- `mac_workflow_generator.py` - Mac工作流生成器（新增）

### 🧹 维护和清理脚本

#### 清理工具
- `cleanup_backup_analysis.py` - 备份清理分析（新增）
- `analyze_temp_scripts.py` - 临时脚本分析（新增）

#### 修复工具
- `complete_fix_script.py` - 完整修复脚本
- `debug_workflow_fix.py` - 工作流调试修复
- `fix_tool_loading.py` - 工具加载修复

## 📈 脚本统计

- **总Python文件**: 140个（清理后）
- **临时脚本**: 45个（保留有用的）
- **核心脚本**: 95个
- **已删除**: 约82个重复和过时文件

## 🎯 推荐保留的重要脚本

### 生产环境必需
1. `generalized_mdp_framework.py` - 系统核心
2. `unified_training_manager.py` - 训练管理
3. `workflow_quality_test_flawed.py` - 质量测试
4. `gpu_training_script.py` - GPU训练
5. `mac_workflow_generator.py` - Mac端工作流生成

### 开发和调试
1. `test_model_compatibility.py` - 兼容性测试
2. `diagnose_training.py` - 训练诊断
3. `visualization_utils.py` - 可视化工具
4. `cleanup_backup_analysis.py` - 清理工具

### 实验和研究
1. `smart_progressive_training.py` - 高级训练
2. `optimize_scoring_params.py` - 参数优化
3. `smart_regenerate_analysis.py` - 智能分析

## 🗑️ 可进一步清理的脚本

如果需要进一步精简，以下脚本可以考虑删除：

### 低优先级测试脚本
- `current_progress_test.py` - 如果不再需要进度测试
- `test_phase2_improvement.py` - 如果阶段2已完成
- `repeat_best_params_test.py` - 如果参数已确定

### 重复功能脚本
- `workflow_quality_test_bac.py` - 备份版本，功能重复
- `workflow_quality_test_flawed_backup_interaction.py` - 过时版本

### 历史版本脚本
- `backup/` 目录下的所有文件 - 历史版本，可归档
- `backup_pc/` 目录下的文件 - PC端历史版本

## 📁 建议的文件组织

```
scale_up/
├── core/                    # 核心系统文件
│   ├── generalized_mdp_framework.py
│   ├── unified_training_manager.py
│   └── mdp_workflow_generator.py
├── training/                # 训练相关脚本
│   ├── gpu_training_script.py
│   ├── smart_progressive_training.py
│   └── optimize_scoring_params.py
├── testing/                 # 测试脚本
│   ├── workflow_quality_test_flawed.py
│   ├── test_model_compatibility.py
│   └── verify_phase23_complete.py
├── tools/                   # 工具脚本
│   ├── visualization_utils.py
│   ├── cleanup_backup_analysis.py
│   └── mac_workflow_generator.py
├── analysis/                # 分析脚本
│   ├── diagnose_training.py
│   └── smart_regenerate_analysis.py
└── archive/                 # 归档目录
    ├── backup/
    └── backup_pc/
```

---

*脚本清单版本: v1.0*  
*最后更新: 2025-08-02*  
*清理完成时间: 2025-08-02 00:10*