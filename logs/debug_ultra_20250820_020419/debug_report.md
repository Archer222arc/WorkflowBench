# Ultra Parallel Runner 调试报告

生成时间: 2025-08-20T02:07:45.469479

## 分片日志文件

- `qwen2_5_32b_instruct_qwen2_5_32b_instruct_easy_key0_659916.log` (212.7 KB)
  - 错误: 4, 警告: 1
  - API调用: 424, 超时: 37
- `qwen2_5_32b_instruct_qwen2_5_32b_instruct_easy_key1_689927.log` (210.3 KB)
  - 错误: 2, 警告: 1
  - API调用: 424, 超时: 33
- `qwen2_5_32b_instruct_qwen2_5_32b_instruct_easy_key2_709939.log` (186.7 KB)
  - 错误: 6, 警告: 1
  - API调用: 364, 超时: 31

## 数据保存检查

- Parquet数据: 15 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
