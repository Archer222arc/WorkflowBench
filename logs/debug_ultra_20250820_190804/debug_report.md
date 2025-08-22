# Ultra Parallel Runner 调试报告

生成时间: 2025-08-20T19:11:53.504025

## 分片日志文件

- `deepseek_r1_0528_74df_191106_858_p75500_004_DeepSeek_R1_0528_easy_0.log` (28.6 KB)
  - 错误: 0, 警告: 1
  - API调用: 27, 超时: 2
- `deepseek_r1_0528_74df_191136_872_p75500_005_DeepSeek_R1_0528_easy_1.log` (25.5 KB)
  - 错误: 0, 警告: 1
  - API调用: 20, 超时: 2
- `deepseek_v3_0324_94cb_190806_830_p74891_001_DeepSeek_V3_0324_easy_0.log` (60.5 KB)
  - 错误: 0, 警告: 1
  - API调用: 63, 超时: 3
- `deepseek_v3_0324_94cb_190836_844_p74891_002_DeepSeek_V3_0324_easy_1.log` (61.9 KB)
  - 错误: 1, 警告: 1
  - API调用: 64, 超时: 4
- `deepseek_v3_0324_94cb_190856_854_p74891_003_DeepSeek_V3_0324_easy_2.log` (135.0 KB)
  - 错误: 0, 警告: 1
  - API调用: 178, 超时: 11

## 数据保存检查

- Parquet数据: 5 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
