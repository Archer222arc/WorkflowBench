# Ultra Parallel Runner 调试报告

生成时间: 2025-08-20T14:26:14.079018

## 分片日志文件

- `qwen2_5_14b_instruct_70a9_142321_541_p3595_001_qwen2_5_14b_instruct_easy_key0.log` (213.7 KB)
  - 错误: 12, 警告: 1
  - API调用: 423, 超时: 33
- `qwen2_5_14b_instruct_70a9_142351_558_p3595_002_qwen2_5_14b_instruct_easy_key1.log` (214.7 KB)
  - 错误: 16, 警告: 1
  - API调用: 426, 超时: 28
- `qwen2_5_14b_instruct_70a9_142411_579_p3595_003_qwen2_5_14b_instruct_easy_key2.log` (187.7 KB)
  - 错误: 14, 警告: 1
  - API调用: 366, 超时: 26

## 数据保存检查

- Parquet数据: 15 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
