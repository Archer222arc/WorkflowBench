# IdealLab配置总结（避免限流）

## 当前配置 ✅

### 1. API Keys（2个有效）
- **key0**: 3d906058...e77b (原key1) ✅
- **key1**: 88a9a901...c3b9 (原key2) ✅
- ~~956c41bd...f4bb~~ (原key0已失效)

### 2. 并发限制（已调整为1）

#### ultra_parallel_runner.py
- **qwen模型** (第162-163行):
  - max_workers: 5 → **1**
  - max_qps: 10.0 → **5.0**
  
- **IdealLab闭源模型** (第194-195行):
  - max_workers: 5 → **1** 
  - max_qps: 10.0 → **5.0**

#### run_systematic_test_final.sh
- **qwen模型强制限制** (第3583行):
  - --max-workers 2 → **--max-workers 1**

### 3. 影响的模型
- **开源模型**: qwen2.5系列（3b/7b/14b/32b/72b）
- **闭源模型**: o3-0416-global, gemini-2.5-flash-06-17, kimi-k2, claude_sonnet4

## 配置理由
- IdealLab API有严格的限流策略
- 单个worker可以避免触发限流
- 虽然性能会降低，但稳定性更高

## 测试命令
```bash
# 运行5.3测试（qwen模型会自动使用max_workers=1）
./run_systematic_test_final.sh --phase 5.3

# 或手动测试
python smart_batch_runner.py \
  --model qwen2.5-3b-instruct \
  --prompt-types optimal \
  --num-instances 5 \
  --max-workers 1
```

## 注意事项
- 测试会比较慢（因为并发限制为1）
- 但应该不会再出现限流错误
- 如果仍有问题，可以进一步降低QPS限制

## 状态
✅ 配置完成，限流问题应该得到解决
