# Ultra Parallel Runner 调试报告

生成时间: 2025-08-27T14:36:51.528888

## 分片日志文件

- `qwen2_5_14b_instruct_70a9_143255_463_p38392_005_qwen2_5_14b_instruct_very_easy_key0.log` (16.5 KB)
  - 错误: 0, 警告: 1
  - API调用: 4, 超时: 0
- `qwen2_5_14b_instruct_70a9_143300_528_p38392_006_qwen2_5_14b_instruct_very_easy_key1.log` (16.5 KB)
  - 错误: 0, 警告: 1
  - API调用: 4, 超时: 0
- `qwen2_5_14b_instruct_70a9_143413_184_p38646_015_qwen2_5_14b_instruct_medium_key0.log` (10.2 KB)
  - 错误: 0, 警告: 0
  - API调用: 4, 超时: 0
- `qwen2_5_14b_instruct_70a9_143418_288_p38646_016_qwen2_5_14b_instruct_medium_key1.log` (10.0 KB)
  - 错误: 0, 警告: 0
  - API调用: 4, 超时: 0
- `qwen2_5_32b_instruct_f408_143240_508_p38344_001_qwen2_5_32b_instruct_very_easy_key0.log` (75.5 KB)
  - 错误: 0, 警告: 1
  - API调用: 114, 超时: 2
- `qwen2_5_32b_instruct_f408_143245_553_p38344_002_qwen2_5_32b_instruct_very_easy_key1.log` (23.9 KB)
  - 错误: 0, 警告: 2
  - API调用: 5, 超时: 2
- `qwen2_5_32b_instruct_f408_143356_568_p38612_013_qwen2_5_32b_instruct_medium_key0.log` (10.0 KB)
  - 错误: 0, 警告: 0
  - API调用: 4, 超时: 0
- `qwen2_5_32b_instruct_f408_143401_825_p38612_014_qwen2_5_32b_instruct_medium_key1.log` (10.0 KB)
  - 错误: 0, 警告: 0
  - API调用: 4, 超时: 0
- `qwen2_5_3b_instruct_e046_143325_585_p38550_009_qwen2_5_3b_instruct_very_easy_key0.log` (10.5 KB)
  - 错误: 0, 警告: 0
  - API调用: 4, 超时: 0
- `qwen2_5_3b_instruct_e046_143330_623_p38550_010_qwen2_5_3b_instruct_very_easy_key1.log` (10.5 KB)
  - 错误: 0, 警告: 0
  - API调用: 4, 超时: 0
- `qwen2_5_3b_instruct_e046_143441_061_p38696_019_qwen2_5_3b_instruct_medium_key0.log` (4.3 KB)
  - 错误: 0, 警告: 0
  - API调用: 1, 超时: 0
- `qwen2_5_3b_instruct_e046_143446_205_p38696_020_qwen2_5_3b_instruct_medium_key1.log` (4.3 KB)
  - 错误: 0, 警告: 0
  - API调用: 1, 超时: 0
- `qwen2_5_72b_instruct_560e_143240_508_p38343_001_qwen2_5_72b_instruct_very_easy_key0.log` (31.9 KB)
  - 错误: 7, 警告: 2
  - API调用: 12, 超时: 2
- `qwen2_5_72b_instruct_560e_143245_552_p38343_002_qwen2_5_72b_instruct_very_easy_key1.log` (23.9 KB)
  - 错误: 0, 警告: 2
  - API调用: 5, 超时: 2
- `qwen2_5_72b_instruct_560e_143340_669_p38583_011_qwen2_5_72b_instruct_medium_key0.log` (10.5 KB)
  - 错误: 0, 警告: 0
  - API调用: 4, 超时: 0
- `qwen2_5_72b_instruct_560e_143345_769_p38583_012_qwen2_5_72b_instruct_medium_key1.log` (10.5 KB)
  - 错误: 0, 警告: 0
  - API调用: 4, 超时: 0
- `qwen2_5_7b_instruct_a95c_143312_675_p38459_007_qwen2_5_7b_instruct_very_easy_key0.log` (10.5 KB)
  - 错误: 0, 警告: 0
  - API调用: 4, 超时: 0
- `qwen2_5_7b_instruct_a95c_143317_757_p38459_008_qwen2_5_7b_instruct_very_easy_key1.log` (10.5 KB)
  - 错误: 0, 警告: 0
  - API调用: 4, 超时: 0
- `qwen2_5_7b_instruct_a95c_143426_648_p38675_017_qwen2_5_7b_instruct_medium_key0.log` (10.2 KB)
  - 错误: 0, 警告: 0
  - API调用: 4, 超时: 0
- `qwen2_5_7b_instruct_a95c_143431_791_p38675_018_qwen2_5_7b_instruct_medium_key1.log` (10.2 KB)
  - 错误: 0, 警告: 0
  - API调用: 4, 超时: 0

## 数据保存检查

- JSON数据库: 0 个测试
- Parquet数据: 40 条记录

## 建议

1. 检查各分片日志中的ERROR和WARNING
2. 查看是否有timeout或API调用问题
3. 验证数据是否正确保存
