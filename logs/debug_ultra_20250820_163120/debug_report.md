# Ultra Parallel Runner 调试报告

生成时间: 2025-08-20T16:41:48.537591

## 分片日志文件

- `deepseek_r1_0528_74df_163422_264_p39430_004_DeepSeek_R1_0528_easy_0.log` (53.3 KB)
  - 错误: 1, 警告: 1
  - API调用: 65, 超时: 2
- `deepseek_r1_0528_74df_163452_283_p39430_005_DeepSeek_R1_0528_easy_1.log` (41.9 KB)
  - 错误: 0, 警告: 1
  - API调用: 51, 超时: 2
- `deepseek_r1_0528_74df_163512_296_p39430_006_DeepSeek_R1_0528_easy_2.log` (113.4 KB)
  - 错误: 0, 警告: 1
  - API调用: 182, 超时: 2
- `deepseek_v3_0324_94cb_163122_189_p38776_001_DeepSeek_V3_0324_easy_0.log` (60.6 KB)
  - 错误: 0, 警告: 1
  - API调用: 65, 超时: 6
- `deepseek_v3_0324_94cb_163152_202_p38776_002_DeepSeek_V3_0324_easy_1.log` (59.6 KB)
  - 错误: 0, 警告: 1
  - API调用: 63, 超时: 3
- `deepseek_v3_0324_94cb_163212_218_p38776_003_DeepSeek_V3_0324_easy_2.log` (128.4 KB)
  - 错误: 1, 警告: 1
  - API调用: 179, 超时: 4
- `qwen2_5_32b_instruct_f408_164022_345_p41263_010_qwen2_5_32b_instruct_easy_key0.log` (74.8 KB)
  - 错误: 0, 警告: 1
  - API调用: 124, 超时: 11
- `qwen2_5_32b_instruct_f408_164052_358_p41263_011_qwen2_5_32b_instruct_easy_key1.log` (74.9 KB)
  - 错误: 0, 警告: 1
  - API调用: 124, 超时: 11
- `qwen2_5_32b_instruct_f408_164112_415_p41263_012_qwen2_5_32b_instruct_easy_key2.log` (31.9 KB)
  - 错误: 0, 警告: 3
  - API调用: 28, 超时: 4
- `qwen2_5_72b_instruct_560e_163722_225_p40008_007_qwen2_5_72b_instruct_easy_key0.log` (80.1 KB)
  - 错误: 9, 警告: 1
  - API调用: 124, 超时: 12
- `qwen2_5_72b_instruct_560e_163752_239_p40008_008_qwen2_5_72b_instruct_easy_key1.log` (86.0 KB)
  - 错误: 19, 警告: 1
  - API调用: 124, 超时: 12
- `qwen2_5_72b_instruct_560e_163812_250_p40008_009_qwen2_5_72b_instruct_easy_key2.log` (1.8 KB)
  - 错误: 0, 警告: 0
  - API调用: 0, 超时: 0

## 数据保存检查

- Parquet数据: 20 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
