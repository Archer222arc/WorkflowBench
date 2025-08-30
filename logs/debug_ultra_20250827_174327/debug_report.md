# Ultra Parallel Runner 调试报告

生成时间: 2025-08-27T17:46:11.668187

## 分片日志文件

- `qwen2_5_14b_instruct_70a9_174344_513_p51476_005_qwen2_5_14b_instruct_very_easy_key0.log` (23.9 KB)
  - 错误: 0, 警告: 2
  - API调用: 5, 超时: 2
- `qwen2_5_14b_instruct_70a9_174349_563_p51476_006_qwen2_5_14b_instruct_very_easy_key1.log` (23.9 KB)
  - 错误: 0, 警告: 2
  - API调用: 5, 超时: 2
- `qwen2_5_14b_instruct_70a9_174459_756_p51610_015_qwen2_5_14b_instruct_medium_key0.log` (8.5 KB)
  - 错误: 0, 警告: 0
  - API调用: 3, 超时: 0
- `qwen2_5_14b_instruct_70a9_174504_825_p51610_016_qwen2_5_14b_instruct_medium_key1.log` (8.5 KB)
  - 错误: 0, 警告: 0
  - API调用: 3, 超时: 0
- `qwen2_5_32b_instruct_f408_174330_044_p51444_001_qwen2_5_32b_instruct_very_easy_key0.log` (95.6 KB)
  - 错误: 0, 警告: 2
  - API调用: 155, 超时: 2
- `qwen2_5_32b_instruct_f408_174335_099_p51444_002_qwen2_5_32b_instruct_very_easy_key1.log` (49.6 KB)
  - 错误: 0, 警告: 2
  - API调用: 59, 超时: 2
- `qwen2_5_32b_instruct_f408_174444_635_p51576_013_qwen2_5_32b_instruct_medium_key0.log` (10.5 KB)
  - 错误: 0, 警告: 0
  - API调用: 4, 超时: 0
- `qwen2_5_32b_instruct_f408_174449_701_p51576_014_qwen2_5_32b_instruct_medium_key1.log` (10.0 KB)
  - 错误: 0, 警告: 0
  - API调用: 4, 超时: 0
- `qwen2_5_3b_instruct_e046_174414_608_p51523_009_qwen2_5_3b_instruct_very_easy_key0.log` (10.5 KB)
  - 错误: 0, 警告: 0
  - API调用: 4, 超时: 0
- `qwen2_5_3b_instruct_e046_174419_674_p51523_010_qwen2_5_3b_instruct_very_easy_key1.log` (10.5 KB)
  - 错误: 0, 警告: 0
  - API调用: 4, 超时: 0
- `qwen2_5_3b_instruct_e046_174529_884_p51655_019_qwen2_5_3b_instruct_medium_key0.log` (4.3 KB)
  - 错误: 0, 警告: 0
  - API调用: 1, 超时: 0
- `qwen2_5_3b_instruct_e046_174534_941_p51655_020_qwen2_5_3b_instruct_medium_key1.log` (4.3 KB)
  - 错误: 0, 警告: 0
  - API调用: 1, 超时: 0
- `qwen2_5_72b_instruct_560e_174330_044_p51443_001_qwen2_5_72b_instruct_very_easy_key0.log` (86.8 KB)
  - 错误: 36, 警告: 1
  - API调用: 94, 超时: 2
- `qwen2_5_72b_instruct_560e_174335_099_p51443_002_qwen2_5_72b_instruct_very_easy_key1.log` (65.2 KB)
  - 错误: 24, 警告: 2
  - API调用: 61, 超时: 2
- `qwen2_5_72b_instruct_560e_174429_675_p51548_011_qwen2_5_72b_instruct_medium_key0.log` (10.5 KB)
  - 错误: 0, 警告: 0
  - API调用: 4, 超时: 0
- `qwen2_5_72b_instruct_560e_174434_738_p51548_012_qwen2_5_72b_instruct_medium_key1.log` (10.0 KB)
  - 错误: 0, 警告: 0
  - API调用: 4, 超时: 0
- `qwen2_5_7b_instruct_a95c_174359_534_p51497_007_qwen2_5_7b_instruct_very_easy_key0.log` (16.5 KB)
  - 错误: 0, 警告: 1
  - API调用: 4, 超时: 0
- `qwen2_5_7b_instruct_a95c_174404_583_p51497_008_qwen2_5_7b_instruct_very_easy_key1.log` (16.5 KB)
  - 错误: 0, 警告: 1
  - API调用: 4, 超时: 0
- `qwen2_5_7b_instruct_a95c_174514_996_p51631_017_qwen2_5_7b_instruct_medium_key0.log` (7.2 KB)
  - 错误: 0, 警告: 0
  - API调用: 2, 超时: 0
- `qwen2_5_7b_instruct_a95c_174520_089_p51631_018_qwen2_5_7b_instruct_medium_key1.log` (7.2 KB)
  - 错误: 0, 警告: 0
  - API调用: 2, 超时: 0

## 数据保存检查

- JSON数据库: 0 个测试
- Parquet数据: 40 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
