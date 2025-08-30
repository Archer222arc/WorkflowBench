# Ultra Parallel Runner 调试报告

生成时间: 2025-08-28T12:41:18.479467

## 分片日志文件

- `DeepSeek_R1_0528_e675_120306_076_p97531_002_DeepSeek_R1_0528_easy_0.log` (2026.1 KB)
  - 错误: 24, 警告: 6
  - API调用: 3478, 超时: 47
- `DeepSeek_V3_0324_797d_120235_978_p97064_001_DeepSeek_V3_0324_easy_0.log` (746.4 KB)
  - 错误: 8, 警告: 2
  - API调用: 713, 超时: 100
- `Llama_3_3_70B_Instruct_e007_123304_272_p32859_006_Llama_3_3_70B_Instruct_easy_0.log` (873.4 KB)
  - 错误: 13, 警告: 147
  - API调用: 1477, 超时: 8
- `qwen2_5_3b_instruct_e046_123304_272_p32852_006_qwen2_5_3b_instruct_easy_logic_defects_key2.log` (198.2 KB)
  - 错误: 0, 警告: 4
  - API调用: 373, 超时: 0
- `qwen2_5_72b_instruct_560e_120336_077_p97988_003_qwen2_5_72b_instruct_easy_struct_defects_key0.log` (1710.1 KB)
  - 错误: 2068, 警告: 6
  - API调用: 765, 超时: 4
- `qwen2_5_72b_instruct_560e_120336_079_p97989_003_qwen2_5_72b_instruct_easy_logic_defects_key2.log` (1121.6 KB)
  - 错误: 1335, 警告: 4
  - API调用: 498, 超时: 7
- `qwen2_5_72b_instruct_560e_120336_081_p97979_004_qwen2_5_72b_instruct_easy_operation_defects_key1.log` (1076.3 KB)
  - 错误: 1279, 警告: 4
  - API调用: 438, 超时: 3

## 数据保存检查

- JSON数据库: 0 个测试
- Parquet数据: 40 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
