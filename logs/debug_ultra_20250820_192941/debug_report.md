# Ultra Parallel Runner 调试报告

生成时间: 2025-08-20T19:35:16.305697

## 分片日志文件

- `deepseek_r1_0528_74df_193243_225_p81564_004_DeepSeek_R1_0528_easy_0.log` (35.2 KB)
  - 错误: 0, 警告: 1
  - API调用: 41, 超时: 3
- `deepseek_r1_0528_74df_193313_238_p81564_005_DeepSeek_R1_0528_easy_1.log` (37.4 KB)
  - 错误: 0, 警告: 1
  - API调用: 44, 超时: 3
- `deepseek_r1_0528_74df_193333_248_p81564_006_DeepSeek_R1_0528_easy_2.log` (65.2 KB)
  - 错误: 0, 警告: 1
  - API调用: 106, 超时: 3
- `deepseek_v3_0324_94cb_192943_150_p80963_001_DeepSeek_V3_0324_easy_0.log` (59.3 KB)
  - 错误: 0, 警告: 1
  - API调用: 65, 超时: 3
- `deepseek_v3_0324_94cb_193013_164_p80963_002_DeepSeek_V3_0324_easy_1.log` (62.2 KB)
  - 错误: 0, 警告: 1
  - API调用: 65, 超时: 4
- `deepseek_v3_0324_94cb_193033_182_p80963_003_DeepSeek_V3_0324_easy_2.log` (138.6 KB)
  - 错误: 0, 警告: 1
  - API调用: 183, 超时: 8

## 数据保存检查

- Parquet数据: 5 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
