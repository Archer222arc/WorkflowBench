# Ultra Parallel Runner 调试报告

生成时间: 2025-08-20T15:20:21.713539

## 分片日志文件

- `qwen2_5_14b_instruct_70a9_151859_540_p19822_001_qwen2_5_14b_instruct_easy_key0.log` (74.5 KB)
  - 错误: 3, 警告: 1
  - API调用: 124, 超时: 9
- `qwen2_5_14b_instruct_70a9_151929_551_p19822_002_qwen2_5_14b_instruct_easy_key1.log` (75.1 KB)
  - 错误: 3, 警告: 1
  - API调用: 124, 超时: 8
- `qwen2_5_14b_instruct_70a9_151949_562_p19822_003_qwen2_5_14b_instruct_easy_key2.log` (1.8 KB)
  - 错误: 0, 警告: 0
  - API调用: 0, 超时: 0

## 数据保存检查

- Parquet数据: 15 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
