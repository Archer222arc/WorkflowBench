# Ultra Parallel Runner 调试报告

生成时间: 2025-08-20T01:14:06.255200

## 分片日志文件

- `deepseek_v3_0324_DeepSeek_V3_0324_easy_0_030280.log` (251.3 KB)
  - 错误: 3, 警告: 1
  - API调用: 364, 超时: 25
- `deepseek_v3_0324_DeepSeek_V3_0324_easy_1_060291.log` (248.0 KB)
  - 错误: 1, 警告: 1
  - API调用: 360, 超时: 11
- `deepseek_v3_0324_DeepSeek_V3_0324_easy_2_080312.log` (324.3 KB)
  - 错误: 0, 警告: 1
  - API调用: 475, 超时: 24

## 数据保存检查

- Parquet数据: 10 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
