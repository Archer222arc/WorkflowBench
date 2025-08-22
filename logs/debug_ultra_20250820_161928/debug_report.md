# Ultra Parallel Runner 调试报告

生成时间: 2025-08-20T16:23:33.393405

## 分片日志文件

- `deepseek_r1_0528_74df_162229_786_p36014_004_DeepSeek_R1_0528_easy_0.log` (29.4 KB)
  - 错误: 0, 警告: 1
  - API调用: 29, 超时: 2
- `deepseek_r1_0528_74df_162259_798_p36014_005_DeepSeek_R1_0528_easy_1.log` (26.4 KB)
  - 错误: 0, 警告: 1
  - API调用: 22, 超时: 2
- `deepseek_r1_0528_74df_162319_809_p36014_006_DeepSeek_R1_0528_easy_2.log` (38.3 KB)
  - 错误: 0, 警告: 1
  - API调用: 50, 超时: 2
- `deepseek_v3_0324_94cb_161929_627_p35408_001_DeepSeek_V3_0324_easy_0.log` (57.7 KB)
  - 错误: 0, 警告: 1
  - API调用: 65, 超时: 5
- `deepseek_v3_0324_94cb_161959_642_p35408_002_DeepSeek_V3_0324_easy_1.log` (58.7 KB)
  - 错误: 1, 警告: 1
  - API调用: 65, 超时: 4
- `deepseek_v3_0324_94cb_162019_650_p35408_003_DeepSeek_V3_0324_easy_2.log` (136.2 KB)
  - 错误: 0, 警告: 1
  - API调用: 178, 超时: 6

## 数据保存检查

- Parquet数据: 5 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
