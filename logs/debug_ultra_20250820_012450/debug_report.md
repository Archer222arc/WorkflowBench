# Ultra Parallel Runner 调试报告

生成时间: 2025-08-20T01:30:12.545663

## 分片日志文件

- `llama_3_3_70b_instruct_Llama_3_3_70B_Instruct_easy_0_290510.log` (234.0 KB)
  - 错误: 0, 警告: 31
  - API调用: 365, 超时: 2
- `llama_3_3_70b_instruct_Llama_3_3_70B_Instruct_easy_1_320525.log` (263.5 KB)
  - 错误: 1, 警告: 1
  - API调用: 364, 超时: 2
- `llama_3_3_70b_instruct_Llama_3_3_70B_Instruct_easy_2_340540.log` (343.2 KB)
  - 错误: 1, 警告: 1
  - API调用: 482, 超时: 3

## 数据保存检查

- Parquet数据: 30 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
