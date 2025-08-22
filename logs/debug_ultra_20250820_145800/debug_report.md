# Ultra Parallel Runner 调试报告

生成时间: 2025-08-20T14:59:42.951972

## 分片日志文件

- `qwen2_5_72b_instruct_560e_145800_679_p13869_001_qwen2_5_72b_instruct_easy_key0.log` (90.8 KB)
  - 错误: 27, 警告: 1
  - API调用: 124, 超时: 12
- `qwen2_5_72b_instruct_560e_145830_694_p13869_002_qwen2_5_72b_instruct_easy_key1.log` (103.5 KB)
  - 错误: 54, 警告: 1
  - API调用: 120, 超时: 13
- `qwen2_5_72b_instruct_560e_145850_723_p13869_003_qwen2_5_72b_instruct_easy_key2.log` (65.0 KB)
  - 错误: 29, 警告: 1
  - API调用: 64, 超时: 7

## 数据保存检查

- Parquet数据: 20 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
