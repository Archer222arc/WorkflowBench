# QPS限制机制修复文档

## 更新日期：2025-08-28

## 重大修复：QPS限制位置错误

### 问题描述
QPS限制原本在`batch_test_runner.py`中，只在每个任务开始时限制一次。但每个任务包含多轮对话（最多10轮），每轮都会调用API，导致实际QPS远超限制。

### 根本原因
```python
# 错误位置（batch_test_runner.py）
qps_limiter.acquire()  # 只限制一次
executor.execute_interactive()  # 内部有10轮API调用
    ├─ 轮1: API调用（无限制）
    ├─ 轮2: API调用（无限制）
    └─ 轮3: API调用（无限制）
```

### 修复方案
将QPS限制移到`interactive_executor.py`的`_get_llm_response()`方法：

```python
def _get_llm_response(self, conversation, state):
    # 在每次实际API调用前限流
    from qps_limiter import get_qps_limiter
    qps_limiter = get_qps_limiter(
        self.model,
        None,
        self.idealab_key_index
    )
    qps_limiter.acquire()  # 每个请求都限流
    
    # 然后调用API
    response = self.llm_client.chat.completions.create(...)
```

## 3个API Keys独立限流实现

### 当前配置
```python
self._ideallab_keys = [
    '3ddb1451943548a2a1f69fa2ab5a8d1f',  # key0
    '3d906058842b6cf4cee8aaa019f7e77b',  # key1
    '88a9a9010f2864bfb53996279dc6c3b9'   # key2
]
```

### State文件分离
- `/tmp/qps_limiter/ideallab_qwen_key0_qps_state.json`
- `/tmp/qps_limiter/ideallab_qwen_key1_qps_state.json`
- `/tmp/qps_limiter/ideallab_qwen_key2_qps_state.json`

### 性能提升
| 配置 | 总QPS | 30个请求耗时 | 相对性能 |
|------|-------|-------------|---------|
| 1 key | 10 | ~3秒 | 1x |
| 2 keys | 20 | ~1.5秒 | 2x |
| **3 keys** | **30** | **~1秒** | **3x** |

## 测试验证

### 测试脚本
- `test_qwen_qps_fix.py` - 2-key独立限流测试
- `test_3key_qps.py` - 3-key并行测试  
- `test_rapid_qps.py` - 快速连续请求测试
- `test_qps_per_request.py` - 多轮对话限流测试

### 测试结果
```
3个keys并行处理30个请求
- 总耗时: 0.972秒
- 实际总QPS: 30.9
- 理论总QPS: 30
- 效率: 102.9%
```

## 关键改进

1. **请求级限流**：每个API请求都受限，不是任务级
2. **独立Key限流**：每个API key独立的10 QPS限制
3. **跨进程同步**：使用文件系统确保多进程遵守限制
4. **精确控制**：使用time.sleep()强制间隔

## 影响范围

- ✅ 防止超过API服务器限制（避免429错误）
- ✅ qwen模型测试速度提升3倍
- ✅ 5.3缺陷工作流测试时间减少约67%
- ✅ 充分利用所有可用API资源

## 注意事项

1. 确保`idealab_key_index`正确传递到所有层级
2. 每个key仍然遵守10 QPS限制
3. State文件自动管理，无需手动干预
4. 适用于所有IdealLab模型（qwen、o3、gemini、kimi）