# Ultra Parallel Runner 调试报告

生成时间: 2025-08-20T22:30:17.126008

## 分片日志文件

- `deepseek_r1_0528_74df_222206_390_p1090_004_DeepSeek_R1_0528_easy_0.log` (34.8 KB)
  - 错误: 5, 警告: 1
  - API调用: 35, 超时: 7
- `deepseek_r1_0528_74df_222236_413_p1090_005_DeepSeek_R1_0528_easy_1.log` (35.4 KB)
  - 错误: 6, 警告: 1
  - API调用: 32, 超时: 6
- `deepseek_r1_0528_74df_222256_422_p1090_006_DeepSeek_R1_0528_easy_2.log` (64.0 KB)
  - 错误: 17, 警告: 1
  - API调用: 89, 超时: 15
- `deepseek_v3_0324_94cb_221906_353_p366_001_DeepSeek_V3_0324_easy_0.log` (64.3 KB)
  - 错误: 1, 警告: 1
  - API调用: 65, 超时: 6
- `deepseek_v3_0324_94cb_221936_366_p366_002_DeepSeek_V3_0324_easy_1.log` (59.2 KB)
  - 错误: 0, 警告: 1
  - API调用: 61, 超时: 3
- `deepseek_v3_0324_94cb_221956_379_p366_003_DeepSeek_V3_0324_easy_2.log` (139.3 KB)
  - 错误: 4, 警告: 1
  - API调用: 181, 超时: 13
- `qwen2_5_32b_instruct_f408_222806_420_p2268_010_qwen2_5_32b_instruct_easy_key0.log` (78.6 KB)
  - 错误: 0, 警告: 1
  - API调用: 124, 超时: 2
- `qwen2_5_32b_instruct_f408_222836_434_p2268_011_qwen2_5_32b_instruct_easy_key1.log` (79.4 KB)
  - 错误: 0, 警告: 1
  - API调用: 124, 超时: 2
- `qwen2_5_32b_instruct_f408_222856_448_p2268_012_qwen2_5_32b_instruct_easy_key2.log` (50.1 KB)
  - 错误: 0, 警告: 1
  - API调用: 64, 超时: 2
- `qwen2_5_72b_instruct_560e_222506_430_p1671_007_qwen2_5_72b_instruct_easy_key0.log` (92.7 KB)
  - 错误: 65, 警告: 1
  - API调用: 111, 超时: 7
- `qwen2_5_72b_instruct_560e_222536_452_p1671_008_qwen2_5_72b_instruct_easy_key1.log` (99.7 KB)
  - 错误: 87, 警告: 1
  - API调用: 99, 超时: 8
- `qwen2_5_72b_instruct_560e_222556_464_p1671_009_qwen2_5_72b_instruct_easy_key2.log` (61.5 KB)
  - 错误: 38, 警告: 1
  - API调用: 49, 超时: 5

## 数据保存检查

- JSON数据库: 0 个测试
- Parquet数据: 21 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
