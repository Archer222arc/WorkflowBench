# Ultra Parallel Runner 调试报告

生成时间: 2025-08-20T16:14:54.765074

## 分片日志文件

- `deepseek_r1_0528_74df_155731_274_p30069_004_DeepSeek_R1_0528_easy_0.log` (53.4 KB)
  - 错误: 0, 警告: 1
  - API调用: 65, 超时: 2
- `deepseek_r1_0528_74df_155801_288_p30069_005_DeepSeek_R1_0528_easy_1.log` (52.6 KB)
  - 错误: 0, 警告: 1
  - API调用: 65, 超时: 2
- `deepseek_r1_0528_74df_155821_297_p30069_006_DeepSeek_R1_0528_easy_2.log` (116.5 KB)
  - 错误: 1, 警告: 1
  - API调用: 183, 超时: 3
- `deepseek_v3_0324_94cb_155431_289_p29435_001_DeepSeek_V3_0324_easy_0.log` (62.1 KB)
  - 错误: 1, 警告: 1
  - API调用: 65, 超时: 2
- `deepseek_v3_0324_94cb_155501_299_p29435_002_DeepSeek_V3_0324_easy_1.log` (57.5 KB)
  - 错误: 0, 警告: 1
  - API调用: 64, 超时: 2
- `deepseek_v3_0324_94cb_155521_309_p29435_003_DeepSeek_V3_0324_easy_2.log` (143.0 KB)
  - 错误: 0, 警告: 1
  - API调用: 182, 超时: 13
- `qwen2_5_14b_instruct_70a9_160631_321_p31675_013_qwen2_5_14b_instruct_easy_key0.log` (74.5 KB)
  - 错误: 0, 警告: 1
  - API调用: 124, 超时: 11
- `qwen2_5_14b_instruct_70a9_160701_332_p31675_014_qwen2_5_14b_instruct_easy_key1.log` (76.1 KB)
  - 错误: 1, 警告: 1
  - API调用: 125, 超时: 12
- `qwen2_5_14b_instruct_70a9_160721_347_p31675_015_qwen2_5_14b_instruct_easy_key2.log` (1.8 KB)
  - 错误: 0, 警告: 0
  - API调用: 0, 超时: 0
- `qwen2_5_32b_instruct_f408_160331_441_p31148_010_qwen2_5_32b_instruct_easy_key0.log` (75.5 KB)
  - 错误: 0, 警告: 1
  - API调用: 124, 超时: 11
- `qwen2_5_32b_instruct_f408_160401_477_p31148_011_qwen2_5_32b_instruct_easy_key1.log` (75.3 KB)
  - 错误: 0, 警告: 1
  - API调用: 124, 超时: 12
- `qwen2_5_32b_instruct_f408_160421_494_p31148_012_qwen2_5_32b_instruct_easy_key2.log` (48.0 KB)
  - 错误: 0, 警告: 1
  - API调用: 64, 超时: 7
- `qwen2_5_3b_instruct_e046_161231_338_p33110_019_qwen2_5_3b_instruct_easy_key0.log` (76.2 KB)
  - 错误: 5, 警告: 1
  - API调用: 124, 超时: 12
- `qwen2_5_3b_instruct_e046_161301_354_p33110_020_qwen2_5_3b_instruct_easy_key1.log` (78.1 KB)
  - 错误: 9, 警告: 1
  - API调用: 124, 超时: 11
- `qwen2_5_3b_instruct_e046_161321_374_p33110_021_qwen2_5_3b_instruct_easy_key2.log` (50.9 KB)
  - 错误: 9, 警告: 1
  - API调用: 64, 超时: 5
- `qwen2_5_72b_instruct_560e_160031_296_p30642_007_qwen2_5_72b_instruct_easy_key0.log` (88.4 KB)
  - 错误: 23, 警告: 1
  - API调用: 124, 超时: 12
- `qwen2_5_72b_instruct_560e_160101_315_p30642_008_qwen2_5_72b_instruct_easy_key1.log` (105.0 KB)
  - 错误: 51, 警告: 1
  - API调用: 124, 超时: 12
- `qwen2_5_72b_instruct_560e_160121_331_p30642_009_qwen2_5_72b_instruct_easy_key2.log` (63.8 KB)
  - 错误: 27, 警告: 1
  - API调用: 64, 超时: 7
- `qwen2_5_7b_instruct_a95c_160931_375_p32224_016_qwen2_5_7b_instruct_easy_key0.log` (74.6 KB)
  - 错误: 0, 警告: 1
  - API调用: 124, 超时: 12
- `qwen2_5_7b_instruct_a95c_161001_430_p32224_017_qwen2_5_7b_instruct_easy_key1.log` (74.6 KB)
  - 错误: 0, 警告: 1
  - API调用: 124, 超时: 12
- `qwen2_5_7b_instruct_a95c_161021_429_p32224_018_qwen2_5_7b_instruct_easy_key2.log` (47.7 KB)
  - 错误: 0, 警告: 1
  - API调用: 64, 超时: 7

## 数据保存检查

- Parquet数据: 35 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
