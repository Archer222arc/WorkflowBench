# Ultra Parallel Runner 调试报告

生成时间: 2025-08-28T17:31:26.075912

## 分片日志文件

- `DeepSeek_R1_0528_e675_140616_761_p4239_002_DeepSeek_R1_0528_easy_0.log` (2441.0 KB)
  - 错误: 6, 警告: 4
  - API调用: 3592, 超时: 29
- `DeepSeek_R1_0528_e675_153658_823_p34040_006_DeepSeek_R1_0528_easy_0.log` (1598.0 KB)
  - 错误: 13, 警告: 10
  - API调用: 2328, 超时: 18
- `DeepSeek_R1_0528_e675_163838_671_p50619_009_DeepSeek_R1_0528_easy_0.log` (1638.7 KB)
  - 错误: 7, 警告: 1
  - API调用: 2391, 超时: 28
- `DeepSeek_V3_0324_797d_140546_816_p4084_001_DeepSeek_V3_0324_easy_0.log` (572.3 KB)
  - 错误: 9, 警告: 1
  - API调用: 699, 超时: 35
- `DeepSeek_V3_0324_797d_142229_579_p8735_004_DeepSeek_V3_0324_easy_0.log` (2081.4 KB)
  - 错误: 11, 警告: 2
  - API调用: 2358, 超时: 109
- `DeepSeek_V3_0324_797d_152200_448_p29441_005_DeepSeek_V3_0324_easy_0.log` (1869.4 KB)
  - 错误: 11, 警告: 1
  - API调用: 2369, 超时: 114
- `Llama_3_3_70B_Instruct_e007_140917_434_p5244_003_Llama_3_3_70B_Instruct_easy_0.log` (2952.9 KB)
  - 错误: 34, 警告: 303
  - API调用: 3576, 超时: 19
- `Llama_3_3_70B_Instruct_e007_154645_622_p37029_007_Llama_3_3_70B_Instruct_easy_0.log` (1.7 KB)
  - 错误: 0, 警告: 0
  - API调用: 0, 超时: 0
- `Llama_3_3_70B_Instruct_e007_154654_082_p37086_008_Llama_3_3_70B_Instruct_easy_0.log` (1.7 KB)
  - 错误: 0, 警告: 0
  - API调用: 0, 超时: 0

## 数据保存检查

- JSON数据库: 0 个测试
- Parquet数据: 40 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
