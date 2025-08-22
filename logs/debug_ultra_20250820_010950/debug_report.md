# Ultra Parallel Runner 调试报告

生成时间: 2025-08-20T01:14:44.255532

## 分片日志文件

- `qwen2_5_72b_instruct_qwen2_5_72b_instruct_easy_key0_390384.log` (296.5 KB)
  - 错误: 302, 警告: 1
  - API调用: 331, 超时: 25
- `qwen2_5_72b_instruct_qwen2_5_72b_instruct_easy_key1_420394.log` (306.3 KB)
  - 错误: 334, 警告: 1
  - API调用: 326, 超时: 29
- `qwen2_5_72b_instruct_qwen2_5_72b_instruct_easy_key2_440403.log` (250.9 KB)
  - 错误: 274, 警告: 1
  - API调用: 269, 超时: 27

## 数据保存检查

- Parquet数据: 10 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
