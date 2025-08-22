#!/bin/bash

# 测试失败测试集成系统

echo "=========================================="
echo "🧪 测试失败测试重新运行系统"
echo "=========================================="

# 测试1: 检查失败测试管理器功能
echo ""
echo "测试1: 失败测试管理器功能"
echo "----------------------------------------"

if [ -f "failed_tests_manager.sh" ]; then
    echo "✅ failed_tests_manager.sh 文件存在"
    source failed_tests_manager.sh
    
    if check_failed_tests_config 2>/dev/null; then
        echo "✅ 失败测试配置文件存在"
        echo "📋 显示失败测试概要:"
        show_failed_tests_summary
    else
        echo "ℹ️  没有失败测试配置文件（这是正常的）"
    fi
else
    echo "❌ failed_tests_manager.sh 文件不存在"
fi

# 测试2: 检查配置文件格式
echo ""
echo "测试2: 配置文件格式验证"
echo "----------------------------------------"

if [ -f "failed_tests_config.json" ]; then
    echo "✅ failed_tests_config.json 文件存在"
    
    # 验证JSON格式
    if python3 -c "import json; json.load(open('failed_tests_config.json'))" 2>/dev/null; then
        echo "✅ JSON格式正确"
        
        # 显示基本信息
        python3 -c "
import json
with open('failed_tests_config.json', 'r') as f:
    config = json.load(f)
session = config['failed_tests_session']
print(f'📅 会话日期: {session[\"session_date\"]}')
print(f'🔢 失败模型数: {session[\"total_failed_models\"]}')
print(f'📝 描述: {session[\"session_description\"]}')
"
    else
        echo "❌ JSON格式错误"
    fi
else
    echo "ℹ️  failed_tests_config.json 文件不存在"
fi

# 测试3: 检查脚本集成
echo ""
echo "测试3: 主脚本集成检查"
echo "----------------------------------------"

if [ -f "run_systematic_test_final.sh" ]; then
    echo "✅ run_systematic_test_final.sh 文件存在"
    
    # 检查是否包含失败测试相关代码
    if grep -q "show_failed_tests_rerun_menu" run_systematic_test_final.sh; then
        echo "✅ 包含失败测试重新运行菜单函数"
    else
        echo "❌ 缺少失败测试重新运行菜单函数"
    fi
    
    if grep -q "source failed_tests_manager.sh" run_systematic_test_final.sh; then
        echo "✅ 包含失败测试管理器导入"
    else
        echo "❌ 缺少失败测试管理器导入"
    fi
    
    if grep -q "重新测试失败的组" run_systematic_test_final.sh; then
        echo "✅ 包含失败测试菜单选项"
    else
        echo "❌ 缺少失败测试菜单选项"
    fi
else
    echo "❌ run_systematic_test_final.sh 文件不存在"
fi

# 测试4: 检查依赖文件
echo ""
echo "测试4: 依赖文件检查"
echo "----------------------------------------"

files_to_check=(
    "ultra_parallel_runner.py"
    "cleanup_timeout_results.py"
    "rerun_failed_tests.sh"
)

for file in "${files_to_check[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file 存在"
        if [ -x "$file" ]; then
            echo "   ✅ 有执行权限"
        else
            echo "   ⚠️  无执行权限"
        fi
    else
        echo "❌ $file 不存在"
    fi
done

# 测试5: 功能性测试
echo ""
echo "测试5: 功能性测试"
echo "----------------------------------------"

if check_failed_tests_config 2>/dev/null; then
    echo "🧪 测试具体功能:"
    
    # 测试模型检查功能
    if is_model_in_failed_list "qwen2.5-3b-instruct" 2>/dev/null; then
        echo "✅ 模型失败检查功能正常"
    else
        echo "❌ 模型失败检查功能异常"
    fi
    
    # 测试命令生成功能
    echo "✅ 测试命令生成功能:"
    generate_retest_commands | head -5
else
    echo "ℹ️  跳过功能性测试（无失败测试配置）"
fi

echo ""
echo "=========================================="
echo "🎯 测试完成总结"
echo "=========================================="
echo ""
echo "✅ 系统集成测试完成"
echo ""
echo "🚀 使用方法:"
echo "   1. ./run_systematic_test_final.sh"
echo "   2. 选择 '5) 🔧 重新测试失败的组'"
echo "   3. 根据菜单选择相应操作"
echo ""
echo "📚 详细文档: FAILED_TESTS_GUIDE.md"