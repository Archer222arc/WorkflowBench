# IdealLab API 诊断报告

## 当前状况
- **错误信息**: "无效的api key" (CE-003错误)
- **影响范围**: 所有qwen模型测试（key0和key1都失败）
- **API URL**: https://idealab.alibaba-inc.com/api/openai/v1 (保留使用)

## 已尝试的修复
1. ✅ 移除第3个不可用的key
2. ✅ 修复smart_batch_runner.py参数传递bug
3. ✅ 更新key映射策略

## 诊断结果
### API Keys状态
- **key0** (956c41bd...f4bb): ❌ 返回"无效的api key"
- **key1** (3d906058...e77b): ❌ 返回"无效的api key"

### 根本原因
由于你要求保留当前URL（阿里内网地址），问题应该是：
1. **API keys已失效**: 两个key都返回"无效的api key"错误
2. **需要新的API keys**: 当前的keys可能已过期或被禁用

## 建议解决方案

### 方案1：获取新的API keys
需要从IdealLab获取新的有效API keys，然后更新：
- `config/config.json` 中的 `ideallab_api_key` 字段
- `api_client_manager.py` 第164-165行的keys列表

### 方案2：临时禁用qwen模型测试
如果暂时无法获取新keys，可以：
1. 在测试脚本中跳过qwen模型
2. 专注于其他可用模型（DeepSeek、Llama等）

### 方案3：使用环境变量覆盖
可以通过设置环境变量临时使用其他可用的key：
```bash
export IDEALAB_API_KEY_OVERRIDE="your_valid_api_key"
./run_systematic_test_final.sh --phase 5.3
```

## 当前配置文件位置
- **API keys配置**: `api_client_manager.py` 第163-167行
- **URL配置**: `config/config.json` 的 `idealab_api_base` 字段
- **参数传递**: `smart_batch_runner.py` 第727行（已修复）

## 状态
⚠️ 等待有效的API keys才能继续qwen模型测试
