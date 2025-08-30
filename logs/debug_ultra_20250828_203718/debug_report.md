# Ultra Parallel Runner 调试报告

生成时间: 2025-08-28T20:37:23.839106

## 分片日志文件

- `DeepSeek_V3_0324_797d_203718_796_p2142_001_DeepSeek_V3_0324_easy_0.log` (4.3 KB)
  - 错误: 0, 警告: 0
  - API调用: 1, 超时: 0

## 数据保存检查

- JSON数据库: 0 个测试
- Parquet数据: 40 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
