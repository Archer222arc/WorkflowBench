#!/bin/bash
# PILOT-Bench 完整测试脚本

echo "🚀 开始 PILOT-Bench 完整测试"
echo "================================"

# 测试配置
MODELS=("gpt-4o-mini" "gpt-4o" "claude-3-haiku-20240307" "claude-3-sonnet-20240229")
TASK_TYPES=("simple_task" "basic_task" "data_pipeline" "api_integration" "multi_stage_pipeline")
PROMPT_TYPES=("xml" "json" "text")
DIFFICULTIES=("very_easy" "easy" "medium" "hard" "very_hard")

# 1. 快速验证测试（确保系统正常）
echo ""
echo "📝 步骤1: 快速验证测试"
python unified_test_runner.py \
  --mode batch \
  --models gpt-4o-mini \
  --task-types simple_task \
  --prompt-types xml \
  --repetitions 1 \
  --difficulty easy \
  --output quick_test.json

# 2. 小规模批量测试（每个组合5次）
echo ""
echo "📝 步骤2: 小规模批量测试"
python unified_test_runner.py \
  --mode batch \
  --models gpt-4o-mini \
  --task-types "${TASK_TYPES[@]}" \
  --prompt-types "${PROMPT_TYPES[@]}" \
  --repetitions 5 \
  --difficulty easy \
  --output small_batch_test.json

# 3. 并发性能测试（测试并发能力）
echo ""
echo "📝 步骤3: 并发性能测试"
python unified_test_runner.py \
  --mode concurrent \
  --models gpt-4o-mini \
  --task-types simple_task basic_task \
  --prompt-types xml json text \
  --repetitions 10 \
  --max-workers 20 \
  --qps 20 \
  --difficulty easy \
  --output concurrent_test.json

# 4. 多模型对比测试
echo ""
echo "📝 步骤4: 多模型对比测试"
for model in "${MODELS[@]}"; do
  echo "  测试模型: $model"
  python unified_test_runner.py \
    --mode batch \
    --models "$model" \
    --task-types "${TASK_TYPES[@]}" \
    --prompt-types "${PROMPT_TYPES[@]}" \
    --repetitions 3 \
    --difficulty easy \
    --output "model_test_${model}.json"
done

# 5. 累积完整测试（目标100次）
echo ""
echo "📝 步骤5: 累积完整测试（目标100次）"
python unified_test_runner.py \
  --mode cumulative \
  --models gpt-4o-mini \
  --target-count 100 \
  --continue \
  --max-retries 3 \
  --output cumulative_test_100.json

# 6. 不同难度测试
echo ""
echo "📝 步骤6: 不同难度测试"
for difficulty in "${DIFFICULTIES[@]}"; do
  echo "  测试难度: $difficulty"
  python unified_test_runner.py \
    --mode batch \
    --models gpt-4o-mini \
    --task-types simple_task basic_task \
    --prompt-types xml json \
    --repetitions 3 \
    --difficulty "$difficulty" \
    --output "difficulty_test_${difficulty}.json"
done

echo ""
echo "✅ 所有测试完成！"
echo "================================"
echo "测试报告已保存到当前目录"