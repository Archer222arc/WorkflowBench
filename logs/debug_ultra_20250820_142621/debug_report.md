# Ultra Parallel Runner 调试报告

生成时间: 2025-08-20T14:29:30.988071

## 分片日志文件

- `qwen2_5_7b_instruct_a95c_142621_442_p4309_001_qwen2_5_7b_instruct_easy_key0.log` (208.6 KB)
  - 错误: 2, 警告: 1
  - API调用: 424, 超时: 35
- `qwen2_5_7b_instruct_a95c_142651_458_p4309_002_qwen2_5_7b_instruct_easy_key1.log` (207.7 KB)
  - 错误: 2, 警告: 1
  - API调用: 424, 超时: 35
- `qwen2_5_7b_instruct_a95c_142711_470_p4309_003_qwen2_5_7b_instruct_easy_key2.log` (181.5 KB)
  - 错误: 0, 警告: 1
  - API调用: 364, 超时: 32

## 数据保存检查

- Parquet数据: 20 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
