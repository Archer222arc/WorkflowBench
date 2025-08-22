# Ultra Parallel Runner 调试报告

生成时间: 2025-08-20T01:18:38.944613

## 分片日志文件

- `qwen2_5_14b_instruct_qwen2_5_14b_instruct_easy_key0_750483.log` (196.7 KB)
  - 错误: 5, 警告: 1
  - API调用: 425, 超时: 6
- `qwen2_5_14b_instruct_qwen2_5_14b_instruct_easy_key1_780493.log` (199.3 KB)
  - 错误: 5, 警告: 1
  - API调用: 424, 超时: 5
- `qwen2_5_14b_instruct_qwen2_5_14b_instruct_easy_key2_800505.log` (173.5 KB)
  - 错误: 5, 警告: 1
  - API调用: 366, 超时: 7

## 数据保存检查

- Parquet数据: 15 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
