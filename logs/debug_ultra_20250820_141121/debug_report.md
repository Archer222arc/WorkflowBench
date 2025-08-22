# Ultra Parallel Runner 调试报告

生成时间: 2025-08-20T14:18:09.780162

## 分片日志文件

- `deepseek_v3_0324_DeepSeek_V3_0324_easy_0_281367.log` (242.5 KB)
  - 错误: 4, 警告: 1
  - API调用: 352, 超时: 16
- `deepseek_v3_0324_DeepSeek_V3_0324_easy_1_311377.log` (253.0 KB)
  - 错误: 5, 警告: 1
  - API调用: 356, 超时: 13
- `deepseek_v3_0324_DeepSeek_V3_0324_easy_2_331475.log` (325.8 KB)
  - 错误: 9, 警告: 1
  - API调用: 474, 超时: 21

## 数据保存检查

- Parquet数据: 5 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
