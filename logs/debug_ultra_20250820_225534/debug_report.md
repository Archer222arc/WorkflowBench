# Ultra Parallel Runner 调试报告

生成时间: 2025-08-20T23:07:42.466335

## 分片日志文件

- `deepseek_r1_0528_74df_225835_590_p8582_004_DeepSeek_R1_0528_easy_0.log` (34.3 KB)
  - 错误: 5, 警告: 1
  - API调用: 35, 超时: 7
- `deepseek_r1_0528_74df_225905_617_p8582_005_DeepSeek_R1_0528_easy_1.log` (34.3 KB)
  - 错误: 5, 警告: 1
  - API调用: 35, 超时: 7
- `deepseek_r1_0528_74df_225925_629_p8582_006_DeepSeek_R1_0528_easy_2.log` (60.1 KB)
  - 错误: 15, 警告: 1
  - API调用: 95, 超时: 17
- `deepseek_v3_0324_94cb_225535_560_p8055_001_DeepSeek_V3_0324_easy_0.log` (59.8 KB)
  - 错误: 0, 警告: 1
  - API调用: 61, 超时: 4
- `deepseek_v3_0324_94cb_225605_572_p8055_002_DeepSeek_V3_0324_easy_1.log` (59.3 KB)
  - 错误: 0, 警告: 1
  - API调用: 63, 超时: 4
- `deepseek_v3_0324_94cb_225625_583_p8055_003_DeepSeek_V3_0324_easy_2.log` (138.2 KB)
  - 错误: 0, 警告: 1
  - API调用: 185, 超时: 9
- `qwen2_5_14b_instruct_70a9_230735_586_p10019_013_qwen2_5_14b_instruct_easy_key0.log` (12.9 KB)
  - 错误: 0, 警告: 1
  - API调用: 3, 超时: 0
- `qwen2_5_32b_instruct_f408_230435_561_p9536_010_qwen2_5_32b_instruct_easy_key0.log` (49.9 KB)
  - 错误: 0, 警告: 1
  - API调用: 64, 超时: 2
- `qwen2_5_32b_instruct_f408_230505_581_p9536_011_qwen2_5_32b_instruct_easy_key1.log` (50.1 KB)
  - 错误: 0, 警告: 1
  - API调用: 64, 超时: 2
- `qwen2_5_32b_instruct_f408_230525_600_p9536_012_qwen2_5_32b_instruct_easy_key2.log` (1.8 KB)
  - 错误: 0, 警告: 0
  - API调用: 0, 超时: 0
- `qwen2_5_72b_instruct_560e_230135_604_p9043_007_qwen2_5_72b_instruct_easy_key0.log` (61.7 KB)
  - 错误: 26, 警告: 1
  - API调用: 59, 超时: 3
- `qwen2_5_72b_instruct_560e_230205_633_p9043_008_qwen2_5_72b_instruct_easy_key1.log` (70.6 KB)
  - 错误: 35, 警告: 1
  - API调用: 64, 超时: 2
- `qwen2_5_72b_instruct_560e_230225_643_p9043_009_qwen2_5_72b_instruct_easy_key2.log` (1.8 KB)
  - 错误: 0, 警告: 0
  - API调用: 0, 超时: 0

## 数据保存检查

- JSON数据库: 0 个测试
- Parquet数据: 21 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
