# Ultra Parallel Runner 调试报告

生成时间: 2025-08-20T01:22:35.123142

## 分片日志文件

- `qwen2_5_7b_instruct_qwen2_5_7b_instruct_easy_key0_930442.log` (196.1 KB)
  - 错误: 7, 警告: 1
  - API调用: 424, 超时: 2
- `qwen2_5_7b_instruct_qwen2_5_7b_instruct_easy_key1_960451.log` (198.1 KB)
  - 错误: 10, 警告: 1
  - API调用: 424, 超时: 2
- `qwen2_5_7b_instruct_qwen2_5_7b_instruct_easy_key2_980457.log` (168.9 KB)
  - 错误: 3, 警告: 1
  - API调用: 364, 超时: 2

## 数据保存检查

- Parquet数据: 20 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
