# Ultra Parallel Runner 调试报告

生成时间: 2025-08-20T15:27:55.624285

## 分片日志文件

- `qwen2_5_3b_instruct_e046_152500_026_p21301_001_qwen2_5_3b_instruct_easy_key0.log` (75.5 KB)
  - 错误: 5, 警告: 1
  - API调用: 124, 超时: 11
- `qwen2_5_3b_instruct_e046_152530_043_p21301_002_qwen2_5_3b_instruct_easy_key1.log` (75.6 KB)
  - 错误: 3, 警告: 1
  - API调用: 124, 超时: 11
- `qwen2_5_3b_instruct_e046_152550_063_p21301_003_qwen2_5_3b_instruct_easy_key2.log` (49.5 KB)
  - 错误: 4, 警告: 1
  - API调用: 64, 超时: 7

## 数据保存检查

- Parquet数据: 25 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
