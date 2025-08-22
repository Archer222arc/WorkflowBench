#!/bin/bash
# 生成所有难度版本的简单脚本

echo "🚀 Generating difficulty versions of task_library_enhanced_v3.json..."

# 检查环境变量
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ Error: OPENAI_API_KEY not set!"
    echo "Please run: export OPENAI_API_KEY='your-api-key'"
    exit 1
fi
INPUT_TASK=mcp_generated_library/task_library_parallel_20250710_042826.json
# 创建输出目录
mkdir -p mcp_generated_library/difficulty_versions
# 生成5个纯难度版本（每个100%单一难度）
echo ""
echo "📋 Generating pure difficulty versions..."
echo "=================================="

# for difficulty in very_easy easy medium hard very_hard; do
#     echo ""
#     echo "🎯 Generating $difficulty version..."
#     python enhance_task_descriptions.py \
#         --input-enhanced $INPUT_TASK \
#         --output mcp_generated_library/difficulty_versions/task_library_enhanced_v3_${difficulty}.json \
#         --update-descriptions-only \
#         --difficulty-mode single \
#         --difficulty-level $difficulty \
#         --workers 1000 \
#         --rate-limit 0.1
# done

# 生成混合难度版本
echo ""
echo "🎲 Generating mixed difficulty versions..."
echo "========================================"

# Easy-biased (30% very_easy, 50% easy, 15% medium, 4% hard, 1% very_hard)
echo ""
echo "📊 Generating easy-biased version..."
python enhance_task_descriptions.py \
    --input-enhanced $INPUT_TASK \
    --output mcp_generated_library/difficulty_versions/task_library_enhanced_v3_easy_biased.json \
    --update-descriptions-only \
    --difficulty-mode custom \
    --difficulty-distribution '{"very_easy":0.30,"easy":0.50,"medium":0.15,"hard":0.04,"very_hard":0.01}'\
    --workers 1000 \
    --rate-limit 0.1

# Medium-biased (balanced distribution)
echo ""
echo "📊 Generating medium-biased version..."
python enhance_task_descriptions.py \
    --input-enhanced $INPUT_TASK \
    --output mcp_generated_library/difficulty_versions/task_library_enhanced_v3_medium_biased.json \
    --update-descriptions-only \
    --difficulty-mode custom \
    --difficulty-distribution '{"very_easy":0.05,"easy":0.20,"medium":0.50,"hard":0.20,"very_hard":0.05}'\
    --workers 1000 \
    --rate-limit 0.1

# Hard-biased (1% very_easy, 4% easy, 15% medium, 50% hard, 30% very_hard)
echo ""
echo "📊 Generating hard-biased version..."
python enhance_task_descriptions.py \
    --input-enhanced $INPUT_TASK \
    --output mcp_generated_library/difficulty_versions/task_library_enhanced_v3_hard_biased.json \
    --update-descriptions-only \
    --difficulty-mode custom \
    --difficulty-distribution '{"very_easy":0.01,"easy":0.04,"medium":0.15,"hard":0.50,"very_hard":0.30}'\
    --workers 1000 \
    --rate-limit 0.1

echo ""
echo "✅ All versions generated successfully!"
echo ""
echo "📁 Output files:"
ls -la mcp_generated_library/difficulty_versions/task_library_enhanced_v3_*.json