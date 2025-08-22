# Ultra Parallel Runner 调试报告

生成时间: 2025-08-20T15:02:29.969798

## 分片日志文件

- `qwen2_5_32b_instruct_f408_150100_728_p14463_001_qwen2_5_32b_instruct_easy_key0.log` (75.1 KB)
  - 错误: 0, 警告: 1
  - API调用: 124, 超时: 12
- `qwen2_5_32b_instruct_f408_150130_762_p14463_002_qwen2_5_32b_instruct_easy_key1.log` (75.5 KB)
  - 错误: 0, 警告: 1
  - API调用: 124, 超时: 12
- `qwen2_5_32b_instruct_f408_150150_776_p14463_003_qwen2_5_32b_instruct_easy_key2.log` (48.0 KB)
  - 错误: 0, 警告: 1
  - API调用: 64, 超时: 7

## 数据保存检查

- Parquet数据: 25 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
