#!/bin/bash
# OpenMP冲突修复脚本
# 用法: source fix_openmp.sh

echo "🔧 设置OpenMP环境变量..."
export KMP_DUPLICATE_LIB_OK=TRUE

echo "✅ OpenMP冲突修复环境变量已设置"
echo "   KMP_DUPLICATE_LIB_OK=$KMP_DUPLICATE_LIB_OK"

# 测试是否工作
echo "🧪 测试导入..."
python -c "
try:
    from mdp_workflow_generator import MDPWorkflowGenerator
    print('✅ 成功：所有模块可以正常导入')
except Exception as e:
    print(f'❌ 错误：{e}')
" 2>/dev/null || echo "❌ 测试失败，请检查Python环境"