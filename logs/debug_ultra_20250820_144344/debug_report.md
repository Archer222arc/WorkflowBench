# Ultra Parallel Runner 调试报告

生成时间: 2025-08-20T14:46:32.423396

## 分片日志文件

- `qwen2_5_14b_instruct_70a9_144344_917_p8913_001_qwen2_5_14b_instruct_easy_key0.log` (215.7 KB)
  - 错误: 11, 警告: 1
  - API调用: 426, 超时: 33
- `qwen2_5_14b_instruct_70a9_144414_939_p8913_002_qwen2_5_14b_instruct_easy_key1.log` (212.6 KB)
  - 错误: 16, 警告: 1
  - API调用: 424, 超时: 32
- `qwen2_5_14b_instruct_70a9_144434_948_p8913_003_qwen2_5_14b_instruct_easy_key2.log` (186.1 KB)
  - 错误: 11, 警告: 1
  - API调用: 367, 超时: 30

## 数据保存检查

- Parquet数据: 10 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
