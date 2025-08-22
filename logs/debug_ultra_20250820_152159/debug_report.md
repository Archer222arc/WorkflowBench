# Ultra Parallel Runner 调试报告

生成时间: 2025-08-20T15:23:27.167220

## 分片日志文件

- `qwen2_5_7b_instruct_a95c_152159_994_p20672_001_qwen2_5_7b_instruct_easy_key0.log` (75.1 KB)
  - 错误: 2, 警告: 1
  - API调用: 124, 超时: 10
- `qwen2_5_7b_instruct_a95c_152230_008_p20672_002_qwen2_5_7b_instruct_easy_key1.log` (74.6 KB)
  - 错误: 0, 警告: 1
  - API调用: 124, 超时: 12
- `qwen2_5_7b_instruct_a95c_152250_028_p20672_003_qwen2_5_7b_instruct_easy_key2.log` (47.8 KB)
  - 错误: 1, 警告: 1
  - API调用: 64, 超时: 6

## 数据保存检查

- Parquet数据: 20 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
