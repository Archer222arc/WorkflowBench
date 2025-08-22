# 配置文档

## 📋 概述

WorkflowBench Scale-Up 提供了灵活的配置系统，支持多种训练算法、设备配置和测试参数。本文档详细介绍了所有配置选项和最佳实践。

## 📁 配置文件结构

```
config/
├── config.json                    # 主配置文件 (生产环境)
├── ppo_m1_config.json            # PPO M1芯片优化配置
├── ppo_m1_overnight_config.json  # 长时间训练配置
└── training_config.json          # 独立训练参数配置
```

## ⚙️ 主配置文件 (config.json)

### API配置

```json
{
  "api_config": {
    "use_azure_openai": true,
    "azure_openai_api_key": "your_api_key_here",
    "azure_openai_api_base": "https://your-resource.openai.azure.com/",
    "azure_openai_api_version": "2024-12-01-preview",
    "azure_openai_deployment_name": "gpt-4o-mini",
    "azure_openai_model": "gpt-4o-mini",
    "openai_api_key": "sk-proj-...",
    "model": "gpt-4o-mini",
    "max_tokens": 2048,
    "temperature": 0.7,
    "top_p": 0.9,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0,
    "timeout": 30,
    "max_retries": 3,
    "retry_delay": 1.0
  }
}
```

**参数说明:**

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `use_azure_openai` | bool | true | 是否使用Azure OpenAI服务 |
| `azure_openai_api_key` | string | - | Azure OpenAI API密钥 |
| `azure_openai_api_base` | string | - | Azure OpenAI端点URL |
| `azure_openai_api_version` | string | "2024-12-01-preview" | Azure OpenAI API版本 |
| `azure_openai_deployment_name` | string | - | Azure部署名称 |
| `azure_openai_model` | string | - | Azure模型名称 |
| `openai_api_key` | string | - | OpenAI API密钥 (备用) |
| `model` | string | "gpt-4o-mini" | 使用的模型名称 |
| `max_tokens` | int | 2048 | 最大生成token数 |
| `temperature` | float | 0.7 | 温度参数 (0.0-2.0) |
| `top_p` | float | 0.9 | Top-p采样参数 |
| `frequency_penalty` | float | 0.0 | 频率惩罚 (-2.0到2.0) |
| `presence_penalty` | float | 0.0 | 存在惩罚 (-2.0到2.0) |
| `timeout` | int | 30 | 请求超时时间(秒) |
| `max_retries` | int | 3 | 最大重试次数 |
| `retry_delay` | float | 1.0 | 重试延迟(秒) |

### MDP框架配置

```json
{
  "mdp_config": {
    "state_dim": 512,
    "action_dim": 64,
    "max_steps": 50,
    "reward_scale": 1.0,
    "discount_factor": 0.99,
    "exploration_rate": 0.1,
    "state_normalization": true,
    "action_masking": true,
    "hierarchical_actions": false
  }
}
```

**参数说明:**

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `state_dim` | int | 512 | 状态特征维度 |
| `action_dim` | int | 64 | 动作空间维度 |
| `max_steps` | int | 50 | 每个episode最大步数 |
| `reward_scale` | float | 1.0 | 奖励缩放因子 |
| `discount_factor` | float | 0.99 | 折扣因子 (gamma) |
| `exploration_rate` | float | 0.1 | 探索率 (epsilon) |
| `state_normalization` | bool | true | 是否进行状态归一化 |
| `action_masking` | bool | true | 是否使用动作掩码 |
| `hierarchical_actions` | bool | false | 是否使用层次化动作 |

### 训练配置

```json
{
  "training_config": {
    "algorithm": "ppo",
    "learning_rate": 0.0003,
    "batch_size": 64,
    "episodes": 1000,
    "gamma": 0.99,
    "tau": 0.95,
    "clip_epsilon": 0.2,
    "value_loss_coef": 0.5,
    "entropy_coef": 0.01,
    "max_grad_norm": 0.5,
    "update_epochs": 4,
    "num_minibatches": 4,
    "target_kl": 0.01,
    "lr_schedule": "linear",
    "warmup_steps": 100
  }
}
```

**参数说明:**

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `algorithm` | string | "ppo" | 训练算法 ("ppo", "dqn", "a2c") |
| `learning_rate` | float | 0.0003 | 学习率 |
| `batch_size` | int | 64 | 批次大小 |
| `episodes` | int | 1000 | 训练回合数 |
| `gamma` | float | 0.99 | 折扣因子 |
| `tau` | float | 0.95 | GAE lambda参数 |
| `clip_epsilon` | float | 0.2 | PPO裁剪参数 |
| `value_loss_coef` | float | 0.5 | 价值损失系数 |
| `entropy_coef` | float | 0.01 | 熵损失系数 |
| `max_grad_norm` | float | 0.5 | 梯度裁剪阈值 |
| `update_epochs` | int | 4 | 每次更新的epoch数 |
| `num_minibatches` | int | 4 | 小批次数量 |
| `target_kl` | float | 0.01 | 目标KL散度 |
| `lr_schedule` | string | "linear" | 学习率调度策略 |
| `warmup_steps` | int | 100 | 预热步数 |

### 测试配置

```json
{
  "testing_config": {
    "strategies": ["baseline", "optimal", "cot"],
    "task_types": [
      "basic_task", 
      "simple_task", 
      "data_pipeline", 
      "api_integration", 
      "multi_stage_pipeline"
    ],
    "difficulties": ["easy", "medium", "hard"],
    "flaw_types": [
      "missing_middle", 
      "order_flaw_swap", 
      "semantic_mismatch"
    ],
    "severities": ["light", "medium", "severe"],
    "test_count_per_combination": 10,
    "parallel_tests": 4,
    "timeout_per_test": 120,
    "save_detailed_logs": true,
    "generate_visualizations": true
  }
}
```

## 🖥️ PPO M1配置 (ppo_m1_config.json)

针对Apple M1/M2芯片优化的PPO训练配置:

```json
{
  "training": {
    "algorithm": "ppo",
    "episodes": 2000,
    "batch_size": 32,
    "learning_rate": 0.0001,
    "gamma": 0.99,
    "gae_lambda": 0.95,
    "clip_epsilon": 0.2,
    "value_loss_coef": 0.5,
    "entropy_coef": 0.01,
    "max_grad_norm": 0.5,
    "update_epochs": 4,
    "num_minibatches": 4,
    "target_kl": 0.01,
    "early_stopping": true,
    "patience": 100
  },
  "device_config": {
    "device": "mps",
    "use_mixed_precision": false,
    "compile_model": true,
    "memory_efficient": true,
    "dataloader_num_workers": 2
  },
  "optimization": {
    "gradient_accumulation_steps": 2,
    "memory_efficient": true,
    "use_checkpoint": true,
    "pin_memory": false,
    "persistent_workers": true
  },
  "checkpoint": {
    "save_interval": 100,
    "max_checkpoints": 5,
    "save_best_only": true,
    "monitor_metric": "episode_reward"
  }
}
```

**M1优化说明:**

- `device: "mps"`: 使用Metal Performance Shaders
- `use_mixed_precision: false`: M1暂不支持混合精度
- `compile_model: true`: 启用模型编译优化
- `gradient_accumulation_steps: 2`: 减少内存使用
- `batch_size: 32`: 适合M1内存的批次大小

## 🌙 长时间训练配置 (ppo_m1_overnight_config.json)

适合过夜长时间训练的配置:

```json
{
  "training": {
    "algorithm": "ppo",
    "episodes": 10000,
    "batch_size": 64,
    "learning_rate": 0.0001,
    "lr_schedule": "cosine",
    "warmup_steps": 500,
    "gamma": 0.995,
    "gae_lambda": 0.98,
    "clip_epsilon": 0.2,
    "value_loss_coef": 0.5,
    "entropy_coef": 0.005,
    "max_grad_norm": 1.0,
    "update_epochs": 6,
    "num_minibatches": 8,
    "target_kl": 0.02,
    "early_stopping": true,
    "patience": 500
  },
  "device_config": {
    "device": "mps",
    "use_mixed_precision": false,
    "compile_model": true,
    "memory_efficient": true
  },
  "logging": {
    "log_interval": 10,
    "eval_interval": 100,
    "checkpoint_interval": 200,
    "verbose": true,
    "tensorboard": true,
    "wandb": false
  },
  "checkpoint": {
    "save_interval": 200,
    "max_checkpoints": 10,
    "save_best_only": false,
    "auto_resume": true
  }
}
```

## 🎯 设备特定配置

### GPU配置 (CUDA)

```json
{
  "device_config": {
    "device": "cuda",
    "gpu_ids": [0, 1],
    "use_mixed_precision": true,
    "compile_model": true,
    "memory_efficient": false,
    "dataloader_num_workers": 8,
    "pin_memory": true,
    "persistent_workers": true,
    "gradient_checkpointing": false
  },
  "distributed": {
    "enable": true,
    "backend": "nccl",
    "init_method": "env://",
    "world_size": 2,
    "rank": 0
  }
}
```

### CPU配置

```json
{
  "device_config": {
    "device": "cpu",
    "num_threads": 8,
    "use_mkldnn": true,
    "dataloader_num_workers": 4,
    "pin_memory": false,
    "persistent_workers": false
  }
}
```

## 📊 算法特定配置

### PPO配置

```json
{
  "ppo_config": {
    "clip_epsilon": 0.2,
    "value_loss_coef": 0.5,
    "entropy_coef": 0.01,
    "max_grad_norm": 0.5,
    "update_epochs": 4,
    "num_minibatches": 4,
    "target_kl": 0.01,
    "gae_lambda": 0.95,
    "normalize_advantage": true,
    "clip_value_loss": true
  }
}
```

### DQN配置

```json
{
  "dqn_config": {
    "buffer_size": 100000,
    "learning_starts": 1000,
    "target_update_interval": 1000,
    "train_freq": 4,
    "gradient_steps": 1,
    "exploration_fraction": 0.1,
    "exploration_initial_eps": 1.0,
    "exploration_final_eps": 0.02,
    "double_q": true,
    "dueling": true,
    "prioritized_replay": false
  }
}
```

### A2C配置

```json
{
  "a2c_config": {
    "value_loss_coef": 0.5,
    "entropy_coef": 0.01,
    "max_grad_norm": 0.5,
    "rms_prop_eps": 1e-5,
    "use_rms_prop": true,
    "normalize_advantage": true,
    "gae_lambda": 1.0
  }
}
```

## 🔧 高级配置选项

### 网络架构配置

```json
{
  "network_config": {
    "policy_network": {
      "hidden_dims": [256, 256],
      "activation": "relu",
      "use_batch_norm": false,
      "use_layer_norm": true,
      "dropout": 0.1,
      "init_method": "orthogonal"
    },
    "value_network": {
      "hidden_dims": [256, 256],
      "activation": "relu",
      "use_batch_norm": false,
      "use_layer_norm": true,
      "dropout": 0.1,
      "init_method": "orthogonal"
    },
    "shared_backbone": false,
    "separate_optimizers": false
  }
}
```

### 数据增强配置

```json
{
  "data_augmentation": {
    "enable": true,
    "noise_level": 0.1,
    "dropout_rate": 0.1,
    "state_perturbation": 0.05,
    "reward_scaling": true,
    "state_stacking": 4
  }
}
```

### 正则化配置

```json
{
  "regularization": {
    "l1_coef": 0.0,
    "l2_coef": 0.0001,
    "spectral_norm": false,
    "weight_decay": 0.01,
    "gradient_penalty": 0.0
  }
}
```

## 📈 监控和日志配置

### 日志配置

```json
{
  "logging_config": {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file_handler": {
      "enabled": true,
      "filename": "logs/training_{timestamp}.log",
      "max_bytes": 10485760,
      "backup_count": 5
    },
    "console_handler": {
      "enabled": true,
      "level": "INFO"
    },
    "metrics_logging": {
      "enabled": true,
      "interval": 10,
      "metrics": [
        "episode_reward",
        "episode_length",
        "policy_loss",
        "value_loss",
        "entropy",
        "kl_divergence",
        "success_rate"
      ]
    }
  }
}
```

### 可视化配置

```json
{
  "visualization_config": {
    "enabled": true,
    "save_plots": true,
    "plot_interval": 100,
    "output_dir": "workflow_quality_results",
    "plots": {
      "training_curves": true,
      "reward_distribution": true,
      "success_rate": true,
      "flaw_sensitivity": true,
      "execution_time": true,
      "quality_breakdown": true
    },
    "plot_style": "seaborn",
    "figure_size": [12, 8],
    "dpi": 300
  }
}
```

## 🔒 安全配置

### API安全

```json
{
  "security_config": {
    "api_key_encryption": true,
    "request_signing": false,
    "rate_limiting": {
      "enabled": true,
      "requests_per_minute": 60,
      "burst_limit": 10
    },
    "audit_logging": true,
    "sensitive_data_masking": true
  }
}
```

## 💾 存储配置

### 检查点配置

```json
{
  "checkpoint_config": {
    "save_interval": 100,
    "max_checkpoints": 5,
    "save_best_only": true,
    "monitor_metric": "episode_reward",
    "mode": "max",
    "save_optimizer_state": true,
    "compression": "gzip",
    "async_save": true
  }
}
```

### 缓存配置

```json
{
  "cache_config": {
    "embedding_cache": {
      "enabled": true,
      "max_size": 10000,
      "ttl": 3600
    },
    "api_response_cache": {
      "enabled": true,
      "max_size": 1000,
      "ttl": 1800
    },
    "workflow_cache": {
      "enabled": true,
      "max_size": 5000,
      "ttl": 7200
    }
  }
}
```

## 🚀 性能优化配置

### 并行化配置

```json
{
  "parallelization_config": {
    "workflow_execution": {
      "max_workers": 4,
      "executor_type": "thread"
    },
    "training_data_generation": {
      "max_workers": 8,
      "executor_type": "process"
    },
    "evaluation": {
      "max_workers": 2,
      "executor_type": "thread"
    }
  }
}
```

### 内存优化配置

```json
{
  "memory_config": {
    "gradient_checkpointing": true,
    "activation_checkpointing": false,
    "memory_efficient_attention": true,
    "buffer_size_limit": "1GB",
    "garbage_collection_interval": 100,
    "clear_cache_interval": 500
  }
}
```

## 📝 配置验证

系统提供配置验证功能:

```python
from config_validator import ConfigValidator

# 验证配置
validator = ConfigValidator()
is_valid, errors = validator.validate_config("config/config.json")

if not is_valid:
    print("配置错误:")
    for error in errors:
        print(f"  - {error}")
```

## 🔄 配置热重载

支持运行时配置热重载:

```python
from config_manager import ConfigManager

config_manager = ConfigManager("config/config.json")
config_manager.enable_hot_reload()

# 配置会自动重载，无需重启程序
```

## 📖 配置模板

### 开发环境配置模板

```json
{
  "api_config": {
    "use_azure_openai": false,
    "openai_api_key": "your_dev_key",
    "model": "gpt-3.5-turbo",
    "max_tokens": 1024,
    "temperature": 0.8
  },
  "training_config": {
    "episodes": 100,
    "batch_size": 16,
    "learning_rate": 0.001
  },
  "logging_config": {
    "level": "DEBUG",
    "console_handler": {"enabled": true}
  }
}
```

### 生产环境配置模板

```json
{
  "api_config": {
    "use_azure_openai": true,
    "azure_openai_api_key": "${AZURE_OPENAI_API_KEY}",
    "model": "gpt-4o-mini",
    "max_tokens": 2048,
    "temperature": 0.7
  },
  "training_config": {
    "episodes": 5000,
    "batch_size": 64,
    "learning_rate": 0.0003
  },
  "logging_config": {
    "level": "INFO",
    "file_handler": {"enabled": true}
  }
}
```

---

*配置文档版本: v2.0*  
*最后更新: 2025-08-02*