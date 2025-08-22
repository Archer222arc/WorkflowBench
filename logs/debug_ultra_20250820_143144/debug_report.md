# Ultra Parallel Runner 调试报告

生成时间: 2025-08-20T14:39:24.529083

## 分片日志文件

- `deepseek_v3_0324_94cb_143144_894_p5987_001_DeepSeek_V3_0324_easy_0.log` (251.6 KB)
  - 错误: 2, 警告: 1
  - API调用: 359, 超时: 21
- `deepseek_v3_0324_94cb_143214_918_p5987_002_DeepSeek_V3_0324_easy_1.log` (249.3 KB)
  - 错误: 2, 警告: 1
  - API调用: 361, 超时: 20
- `deepseek_v3_0324_94cb_143234_934_p5987_003_DeepSeek_V3_0324_easy_2.log` (324.2 KB)
  - 错误: 5, 警告: 1
  - API调用: 475, 超时: 14

## 数据保存检查

- Parquet数据: 5 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
