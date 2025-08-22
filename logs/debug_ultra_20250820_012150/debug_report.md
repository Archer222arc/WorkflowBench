# Ultra Parallel Runner 调试报告

生成时间: 2025-08-20T01:30:40.143000

## 分片日志文件

- `qwen2_5_3b_instruct_qwen2_5_3b_instruct_easy_key0_110503.log` (220.9 KB)
  - 错误: 55, 警告: 1
  - API调用: 424, 超时: 2
- `qwen2_5_3b_instruct_qwen2_5_3b_instruct_easy_key1_140508.log` (222.9 KB)
  - 错误: 55, 警告: 1
  - API调用: 424, 超时: 2
- `qwen2_5_3b_instruct_qwen2_5_3b_instruct_easy_key2_160516.log` (197.5 KB)
  - 错误: 54, 警告: 1
  - API调用: 364, 超时: 2

## 数据保存检查

- Parquet数据: 30 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
