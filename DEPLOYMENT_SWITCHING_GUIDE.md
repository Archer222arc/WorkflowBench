# 智能部署切换功能使用指南

## 概述

智能部署切换功能自动处理Azure OpenAI API的429 Too Many Requests错误，通过在多个部署实例间切换实现负载均衡和故障转移。

## 功能特性

### ✅ 自动429错误检测
- 监测API响应中的429错误码
- 识别"Too Many Requests"和"Rate limit"消息
- 自动触发部署切换逻辑

### ✅ 智能负载均衡
- 轮换使用不同部署实例
- 基于最少使用时间的负载均衡
- 避免集中在单一部署上

### ✅ 健康状态管理
- 自动标记失败的部署为不健康
- 失败计数和恢复机制
- 实时状态监控和报告

### ✅ 无缝集成
- 自动集成到现有测试流程
- 无需修改现有命令或脚本
- 透明的故障转移机制

## 支持的模型

目前支持以下具有多部署配置的模型：

### Azure开源模型
- **Llama-3.3-70B-Instruct** (3个部署)
  - Llama-3.3-70B-Instruct
  - Llama-3.3-70B-Instruct-2
  - Llama-3.3-70B-Instruct-3

- **DeepSeek-V3-0324** (3个部署)
  - DeepSeek-V3-0324
  - DeepSeek-V3-0324-2
  - DeepSeek-V3-0324-3

- **DeepSeek-R1-0528** (3个部署)
  - DeepSeek-R1-0528
  - DeepSeek-R1-0528-2
  - DeepSeek-R1-0528-3

## 使用方法

### 自动启用
智能部署切换功能会在以下情况下自动启用：

```bash
# 5.5提示敏感性测试 - Llama模型会自动使用部署切换
./test_5_5_prompt_sensitivity.sh Llama-3.3-70B-Instruct baseline

# 5.4工具可靠性测试 - DeepSeek模型也支持
./test_5_4_tool_reliability.sh DeepSeek-V3-0324 0.9

# 任何使用支持模型的测试
./run_systematic_test_final.sh --phase 5.1
```

### 手动测试
```bash
# 测试部署切换功能
python test_deployment_switching.py

# 查看智能部署管理器状态
python test_smart_deployment.py
```

## 工作原理

### 1. 客户端创建阶段
```python
# api_client_manager.py 中的智能部署选择
if model_name in parallel_deployments:
    deployment_manager = get_deployment_manager()
    best_deployment = deployment_manager.get_best_deployment(model_name)
```

### 2. API调用阶段
```python
# interactive_executor.py 中的429错误处理
if is_429_error:
    deployment_manager.mark_deployment_failed(current_deployment, "429")
    new_deployment = deployment_manager.get_best_deployment(self.model)
    self.llm_client = get_client_for_model(self.model, self.prompt_type, idealab_key_index)
```

### 3. 负载均衡算法
- **轮转选择**: 选择最少使用的部署
- **健康检查**: 过滤失败次数过多的部署
- **自动恢复**: 在所有部署失败时重置状态

## 监控和调试

### 查看部署状态
```python
from smart_deployment_manager import get_deployment_manager

manager = get_deployment_manager()
manager.print_status()
```

### 输出示例：
```
🚀 智能部署管理器状态:
📊 Llama-3.3-70B-Instruct:
  • Llama-3.3-70B-Instruct: ✅ 健康 (失败次数: 0, 上次使用: 15:01:19)
  • Llama-3.3-70B-Instruct-2: ❌ 不健康 (失败次数: 1, 上次使用: 15:01:20)  
  • Llama-3.3-70B-Instruct-3: ✅ 健康 (失败次数: 0, 上次使用: 15:01:20)
```

### 日志监控
在测试运行时，查看以下日志信息：
```bash
tail -f logs/batch_test_*.log | grep "429_ERROR\|deployment"
```

### 关键日志消息：
```
[429_ERROR] 429 Too Many Requests detected, attempting deployment switch...
[429_ERROR] Current deployment: Llama-3.3-70B-Instruct-2
[429_ERROR] Marked Llama-3.3-70B-Instruct-2 as failed due to 429 error
[429_ERROR] Switching from Llama-3.3-70B-Instruct-2 to Llama-3.3-70B-Instruct-3
[429_ERROR] Successfully switched to new deployment: Llama-3.3-70B-Instruct-3
```

## 实际测试结果

在实际5.5测试中观察到的成功案例：

### 测试场景
```bash
./test_5_5_prompt_sensitivity.sh Llama-3.3-70B-Instruct baseline
```

### 观察到的行为
1. **初始部署**: `Llama-3.3-70B-Instruct-2`
2. **遇到429错误**: Rate limit of 400000 per 60s exceeded
3. **自动切换到**: `Llama-3.3-70B-Instruct-3`
4. **再次遇到429**: 继续切换到 `Llama-3.3-70B-Instruct`
5. **测试继续**: 成功完成API调用，返回200 OK

### 性能改进
- **之前**: 遇到429错误后测试失败，需要手动重试
- **现在**: 自动切换部署，测试无缝继续，成功率显著提高

## 配置说明

### 智能部署管理器参数
```python
# smart_deployment_manager.py 配置
class SmartDeploymentManager:
    def __init__(self):
        self.failure_count = {}  # 失败计数阈值：5次
        self.deployment_health = {}  # 健康状态跟踪
        self.last_used = {}  # 负载均衡时间戳
```

### 恢复机制
- **健康检查**: 失败次数<5的部署被认为是健康的
- **自动重置**: 当所有部署都失败时，重置失败计数
- **成功恢复**: 成功的API调用会重置部署的失败计数

## 故障排除

### 常见问题

#### 1. 部署切换不生效
**检查**: 模型是否在支持列表中
```bash
python -c "from smart_deployment_manager import SmartDeploymentManager; 
m = SmartDeploymentManager(); print(m.parallel_deployments.keys())"
```

#### 2. 所有部署都失败
**解决**: 等待Azure配额恢复，或检查API密钥
```bash
# 手动重置部署状态
python -c "from smart_deployment_manager import get_deployment_manager;
m = get_deployment_manager(); [m.mark_deployment_success(d) for d in ['Llama-3.3-70B-Instruct', 'Llama-3.3-70B-Instruct-2', 'Llama-3.3-70B-Instruct-3']]"
```

#### 3. 日志中没有显示部署切换
**检查**: 确保使用正确的测试脚本
```bash
# 正确：使用bash测试脚本
./test_5_5_prompt_sensitivity.sh Llama-3.3-70B-Instruct baseline

# 错误：直接调用Python（绕过了智能部署管理器）
python smart_batch_runner.py --model Llama-3.3-70B-Instruct
```

## 总结

智能部署切换功能显著提高了Azure开源模型的测试稳定性和成功率。通过自动处理429错误并在多部署间负载均衡，系统能够更有效地利用Azure API配额，减少因单一部署限流导致的测试失败。

**关键优势**:
- 🚀 **自动化**: 无需人工干预的故障转移
- 💪 **稳定性**: 显著提高测试成功率
- 🔄 **负载均衡**: 充分利用所有可用部署
- 📊 **透明度**: 详细的状态监控和日志记录