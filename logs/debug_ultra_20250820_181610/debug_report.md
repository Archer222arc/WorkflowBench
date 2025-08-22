# Ultra Parallel Runner 调试报告

生成时间: 2025-08-20T18:19:50.708278

## 分片日志文件

- `deepseek_r1_0528_74df_181912_070_p65061_004_DeepSeek_R1_0528_easy_0.log` (26.8 KB)
  - 错误: 0, 警告: 1
  - API调用: 23, 超时: 2
- `deepseek_r1_0528_74df_181942_082_p65061_005_DeepSeek_R1_0528_easy_1.log` (18.4 KB)
  - 错误: 0, 警告: 1
  - API调用: 4, 超时: 0
- `deepseek_v3_0324_94cb_181612_049_p64499_001_DeepSeek_V3_0324_easy_0.log` (59.7 KB)
  - 错误: 0, 警告: 1
  - API调用: 65, 超时: 6
- `deepseek_v3_0324_94cb_181642_058_p64499_002_DeepSeek_V3_0324_easy_1.log` (54.1 KB)
  - 错误: 1, 警告: 1
  - API调用: 61, 超时: 3
- `deepseek_v3_0324_94cb_181702_070_p64499_003_DeepSeek_V3_0324_easy_2.log` (143.5 KB)
  - 错误: 0, 警告: 1
  - API调用: 182, 超时: 20

## 数据保存检查

- Parquet数据: 5 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
