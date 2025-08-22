# Ultra Parallel Runner 调试报告

生成时间: 2025-08-20T16:53:56.119711

## 分片日志文件

- `deepseek_r1_0528_74df_164918_930_p44131_004_DeepSeek_R1_0528_easy_0.log` (44.5 KB)
  - 错误: 0, 警告: 1
  - API调用: 56, 超时: 3
- `deepseek_r1_0528_74df_164948_951_p44131_005_DeepSeek_R1_0528_easy_1.log` (47.2 KB)
  - 错误: 0, 警告: 1
  - API调用: 61, 超时: 4
- `deepseek_r1_0528_74df_165008_985_p44131_006_DeepSeek_R1_0528_easy_2.log` (85.1 KB)
  - 错误: 0, 警告: 1
  - API调用: 142, 超时: 3
- `deepseek_v3_0324_94cb_164618_754_p43464_001_DeepSeek_V3_0324_easy_0.log` (58.7 KB)
  - 错误: 0, 警告: 1
  - API调用: 65, 超时: 9
- `deepseek_v3_0324_94cb_164648_775_p43464_002_DeepSeek_V3_0324_easy_1.log` (60.0 KB)
  - 错误: 0, 警告: 1
  - API调用: 62, 超时: 8
- `deepseek_v3_0324_94cb_164708_791_p43464_003_DeepSeek_V3_0324_easy_2.log` (135.4 KB)
  - 错误: 0, 警告: 1
  - API调用: 184, 超时: 14
- `qwen2_5_72b_instruct_560e_165218_900_p44865_007_qwen2_5_72b_instruct_easy_key0.log` (87.4 KB)
  - 错误: 21, 警告: 1
  - API调用: 124, 超时: 12
- `qwen2_5_72b_instruct_560e_165248_923_p44865_008_qwen2_5_72b_instruct_easy_key1.log` (98.1 KB)
  - 错误: 44, 警告: 1
  - API调用: 121, 超时: 13
- `qwen2_5_72b_instruct_560e_165308_945_p44865_009_qwen2_5_72b_instruct_easy_key2.log` (65.1 KB)
  - 错误: 29, 警告: 1
  - API调用: 64, 超时: 7

## 数据保存检查

- Parquet数据: 10 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
