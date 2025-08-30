# IdealLab API Key修复总结

## 问题描述
- 用户报告在测试5.3时出现错误：`无效的api key`
- 错误发生在使用`qwen-key1`时
- 用户确认只有前两个IdealLab API keys可用

## 根本原因
1. **API Key配置问题**：api_client_manager.py中配置了3个keys，但第3个key已不可用
2. **参数传递问题**：smart_batch_runner.py中参数名拼写不一致（idealab vs ideallab）

## 修复内容

### 1. 修复smart_batch_runner.py参数传递 ✅
- 第727行：添加`dest='idealab_key_index'`确保参数正确映射
- 现在`--idealab-key-index`参数能正确传递给内部变量

### 2. 更新api_client_manager.py ✅
- **移除不可用的第3个key**：
  ```python
  # 修改前：3个keys
  self._idealab_keys = [
      '956c41bd0f31beaf68b871d4987af4bb',  # key0
      '3d906058842b6cf4cee8aaa019f7e77b',  # key1
      '88a9a9010f2864bfb53996279dc6c3b9'   # key2 (不可用)
  ]
  
  # 修改后：只保留2个可用的keys
  self._idealab_keys = [
      '956c41bd0f31beaf68b871d4987af4bb',  # key0
      '3d906058842b6cf4cee8aaa019f7e77b'   # key1
  ]
  ```

- **更新prompt_key_strategy映射**：
  ```python
  # 修改后的策略（适应只有2个keys）
  'baseline': 0,  # 使用key0
  'cot': 1,       # 使用key1  
  'optimal': 1,   # 也使用key1（因为只有2个keys）
  'flawed': -1    # 轮询使用
  ```

### 3. ultra_parallel_runner.py配置确认 ✅
- 已正确配置为使用2个虚拟实例：qwen-key0, qwen-key1
- 第216行注释已更新为"利用2个API keys"

## 影响范围
- 所有qwen模型测试（5.1-5.5）
- 不影响其他模型（Azure模型使用不同的认证方式）

## 验证方法
```bash
# 测试5.3缺陷工作流
./run_systematic_test_final.sh --phase 5.3

# 或单独测试qwen模型
python smart_batch_runner.py \
  --model qwen2.5-3b-instruct \
  --idealab-key-index 0 \
  --prompt-types optimal \
  --num-instances 1 \
  --max-workers 2
```

## 状态
✅ 修复完成，IdealLab现在只使用2个可用的API keys
