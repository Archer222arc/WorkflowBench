# Ultra Parallel Runner 调试报告

生成时间: 2025-08-20T14:22:22.534384

## 分片日志文件

- `qwen2_5_72b_instruct_qwen2_5_72b_instruct_easy_key0_641515.log` (324.7 KB)
  - 错误: 242, 警告: 1
  - API调用: 394, 超时: 43
- `qwen2_5_72b_instruct_qwen2_5_72b_instruct_easy_key1_671520.log` (343.7 KB)
  - 错误: 289, 警告: 1
  - API调用: 390, 超时: 47
- `qwen2_5_72b_instruct_qwen2_5_72b_instruct_easy_key2_691527.log` (322.2 KB)
  - 错误: 257, 警告: 1
  - API调用: 356, 超时: 36

## 数据保存检查

- Parquet数据: 10 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
