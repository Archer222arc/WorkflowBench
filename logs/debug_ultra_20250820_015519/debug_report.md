# Ultra Parallel Runner 调试报告

生成时间: 2025-08-20T02:02:23.996182

## 分片日志文件

- `deepseek_v3_0324_DeepSeek_V3_0324_easy_0_119772.log` (249.3 KB)
  - 错误: 1, 警告: 1
  - API调用: 358, 超时: 18
- `deepseek_v3_0324_DeepSeek_V3_0324_easy_1_149778.log` (247.9 KB)
  - 错误: 5, 警告: 1
  - API调用: 356, 超时: 22
- `deepseek_v3_0324_DeepSeek_V3_0324_easy_2_169793.log` (321.8 KB)
  - 错误: 3, 警告: 1
  - API调用: 471, 超时: 25

## 数据保存检查

- Parquet数据: 5 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
