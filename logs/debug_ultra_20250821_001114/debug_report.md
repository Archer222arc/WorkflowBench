# Ultra Parallel Runner 调试报告

生成时间: 2025-08-21T00:20:38.909850

## 分片日志文件

- `deepseek_r1_0528_74df_001417_230_p26298_004_DeepSeek_R1_0528_easy_0.log` (38.3 KB)
  - 错误: 9, 警告: 1
  - API调用: 23, 超时: 3
- `deepseek_r1_0528_74df_001447_244_p26298_005_DeepSeek_R1_0528_easy_1.log` (35.6 KB)
  - 错误: 10, 警告: 1
  - API调用: 20, 超时: 2
- `deepseek_r1_0528_74df_001507_271_p26298_006_DeepSeek_R1_0528_easy_2.log` (56.8 KB)
  - 错误: 28, 警告: 1
  - API调用: 50, 超时: 2
- `deepseek_v3_0324_94cb_001117_268_p25750_001_DeepSeek_V3_0324_easy_0.log` (62.8 KB)
  - 错误: 0, 警告: 1
  - API调用: 65, 超时: 3
- `deepseek_v3_0324_94cb_001147_287_p25750_002_DeepSeek_V3_0324_easy_1.log` (63.0 KB)
  - 错误: 0, 警告: 1
  - API调用: 65, 超时: 4
- `deepseek_v3_0324_94cb_001207_302_p25750_003_DeepSeek_V3_0324_easy_2.log` (132.4 KB)
  - 错误: 0, 警告: 1
  - API调用: 177, 超时: 4
- `qwen2_5_32b_instruct_f408_002017_298_p27428_010_qwen2_5_32b_instruct_easy_key0.log` (31.8 KB)
  - 错误: 0, 警告: 1
  - API调用: 37, 超时: 2
- `qwen2_5_72b_instruct_560e_001717_255_p26838_007_qwen2_5_72b_instruct_easy_key0.log` (96.5 KB)
  - 错误: 20, 警告: 1
  - API调用: 124, 超时: 2
- `qwen2_5_72b_instruct_560e_001747_270_p26838_008_qwen2_5_72b_instruct_easy_key1.log` (108.3 KB)
  - 错误: 47, 警告: 1
  - API调用: 118, 超时: 3
- `qwen2_5_72b_instruct_560e_001807_278_p26838_009_qwen2_5_72b_instruct_easy_key2.log` (69.6 KB)
  - 错误: 30, 警告: 1
  - API调用: 66, 超时: 3

## 数据保存检查

- JSON数据库: 0 个测试
- Parquet数据: 12 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
