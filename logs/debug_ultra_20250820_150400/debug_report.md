# Ultra Parallel Runner 调试报告

生成时间: 2025-08-20T15:04:59.881115

## 分片日志文件

- `qwen2_5_14b_instruct_70a9_150400_816_p15307_001_qwen2_5_14b_instruct_easy_key0.log` (48.3 KB)
  - 错误: 2, 警告: 1
  - API调用: 66, 超时: 6
- `qwen2_5_14b_instruct_70a9_150430_825_p15307_002_qwen2_5_14b_instruct_easy_key1.log` (47.2 KB)
  - 错误: 3, 警告: 1
  - API调用: 66, 超时: 8
- `qwen2_5_14b_instruct_70a9_150450_832_p15307_003_qwen2_5_14b_instruct_easy_key2.log` (1.8 KB)
  - 错误: 0, 警告: 0
  - API调用: 0, 超时: 0

## 数据保存检查

- Parquet数据: 25 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
