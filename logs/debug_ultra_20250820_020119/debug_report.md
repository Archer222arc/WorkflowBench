# Ultra Parallel Runner 调试报告

生成时间: 2025-08-20T02:05:51.734706

## 分片日志文件

- `qwen2_5_72b_instruct_qwen2_5_72b_instruct_easy_key0_479839.log` (330.3 KB)
  - 错误: 323, 警告: 1
  - API调用: 353, 超时: 55
- `qwen2_5_72b_instruct_qwen2_5_72b_instruct_easy_key1_509848.log` (276.6 KB)
  - 错误: 303, 警告: 1
  - API调用: 282, 超时: 54
- `qwen2_5_72b_instruct_qwen2_5_72b_instruct_easy_key2_529860.log` (254.0 KB)
  - 错误: 272, 警告: 1
  - API调用: 249, 超时: 47

## 数据保存检查

- Parquet数据: 10 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
