# 5.3 Qwen模型数据清理报告

## 执行时间
2025-08-27 21:58

## 清理内容
清理所有qwen模型的flawed prompt类型数据（5.3缺陷工作流测试）

## 影响的模型
- qwen2.5-3b-instruct
- qwen2.5-7b-instruct
- qwen2.5-14b-instruct
- qwen2.5-32b-instruct
- qwen2.5-72b-instruct

## 清理的数据
- flawed_sequence_disorder (qwen2.5-72b-instruct)
- flawed_parameter_error (qwen2.5-72b-instruct)

## 备份信息
✅ **备份文件已创建**
- 文件名: `master_database_backup_20250827_215854.json`
- 位置: `pilot_bench_cumulative_results/`
- 大小: 224K

## 清理后状态
所有qwen模型现在只保留了`optimal` prompt类型的数据：
- ✅ 5.1基准测试数据 (optimal, easy)
- ✅ 5.2规模效应数据 (optimal, very_easy/medium)  
- ❌ 5.3缺陷工作流数据 (已清理)
- ✅ 5.4工具可靠性数据 (optimal, easy)
- ✅ 5.5提示敏感性数据 (optimal, easy)

## 恢复命令
如果需要恢复数据：
```bash
cp pilot_bench_cumulative_results/master_database_backup_20250827_215854.json \
   pilot_bench_cumulative_results/master_database.json
```

## 准备重新测试
现在可以重新运行5.3测试：
```bash
./run_systematic_test_final.sh --phase 5.3
```

## 状态
✅ 清理完成，备份已创建，准备重新测试
