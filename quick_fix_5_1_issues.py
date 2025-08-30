#!/usr/bin/env python3
"""
快速修复5.1超并发实验的数据记录问题
针对发现的配置不匹配问题提供立即可用的解决方案

修复内容：
1. 创建缺失的temp_results目录
2. 更新数据库统计信息
3. 应用智能checkpoint配置
4. 验证修复效果
"""

import os
import json
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def quick_fix_all():
    """执行所有快速修复"""
    logger.info("🚀 5.1超并发实验问题快速修复")
    logger.info("=" * 50)
    
    fixes_applied = []
    
    # 1. 创建temp_results目录
    if create_temp_results_dir():
        fixes_applied.append("创建temp_results目录")
    
    # 2. 更新数据库统计
    if update_database_statistics():
        fixes_applied.append("更新数据库统计")
    
    # 3. 设置智能环境变量
    if setup_smart_environment():
        fixes_applied.append("设置智能环境变量")
    
    # 4. 创建测试验证脚本
    if create_verification_test():
        fixes_applied.append("创建验证测试")
    
    # 5. 显示修复结果
    logger.info(f"\n✅ 快速修复完成! 应用了 {len(fixes_applied)} 项修复:")
    for fix in fixes_applied:
        logger.info(f"  ✓ {fix}")
    
    logger.info(f"\n🎯 建议的下一步操作:")
    logger.info(f"1. 运行验证测试: python3 verify_fix.py")
    logger.info(f"2. 使用新配置重新运行5.1测试")
    logger.info(f"3. 监控数据保存情况")

def create_temp_results_dir():
    """创建temp_results目录"""
    try:
        temp_dir = Path("temp_results")
        if not temp_dir.exists():
            temp_dir.mkdir(parents=True)
            logger.info("✅ 创建temp_results目录")
            return True
        else:
            logger.info("ℹ️  temp_results目录已存在")
            return False
    except Exception as e:
        logger.error(f"❌ 创建temp_results目录失败: {e}")
        return False

def update_database_statistics():
    """更新数据库统计信息"""
    try:
        # 检查update_summary_totals.py是否存在
        update_script = Path("update_summary_totals.py")
        if update_script.exists():
            logger.info("🔄 运行统计更新脚本...")
            
            # 尝试导入并运行
            try:
                import subprocess
                result = subprocess.run(['python3', 'update_summary_totals.py'], 
                                      capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    logger.info("✅ 数据库统计更新成功")
                    return True
                else:
                    logger.warning(f"⚠️ 统计更新返回码: {result.returncode}")
                    logger.info("请手动运行: python3 update_summary_totals.py")
                    return False
                    
            except subprocess.TimeoutExpired:
                logger.warning("⚠️ 统计更新超时，请手动运行")
                return False
            except Exception as e:
                logger.warning(f"⚠️ 统计更新异常: {e}")
                logger.info("请手动运行: python3 update_summary_totals.py")
                return False
        else:
            logger.warning("⚠️ update_summary_totals.py 不存在")
            return False
            
    except Exception as e:
        logger.error(f"❌ 数据库统计更新失败: {e}")
        return False

def setup_smart_environment():
    """设置智能环境变量"""
    try:
        # 创建环境变量设置脚本
        env_script_content = '''#!/bin/bash
# 智能数据收集器环境变量设置
# 解决5.1超并发实验的数据记录问题

echo "🔧 设置智能数据收集环境变量..."

# 基本配置
export USE_SMART_COLLECTOR="true"
export COLLECTOR_SCALE="small"  # 适合5个测试/分片的小规模配置
export NUM_TESTS="5"            # 每个分片的测试数量

# 存储格式
export STORAGE_FORMAT="json"    # 继续使用JSON格式

# 调试选项
export DEBUG_COLLECTOR="false"

echo "✅ 环境变量设置完成"
echo "   USE_SMART_COLLECTOR: $USE_SMART_COLLECTOR"
echo "   COLLECTOR_SCALE: $COLLECTOR_SCALE"
echo "   NUM_TESTS: $NUM_TESTS"
echo "   STORAGE_FORMAT: $STORAGE_FORMAT"

echo ""
echo "🎯 使用方法:"
echo "1. source ./smart_env.sh"  
echo "2. ./run_systematic_test_final.sh --phase 5.1"
echo ""
echo "或者直接运行:"
echo "USE_SMART_COLLECTOR=true COLLECTOR_SCALE=small ./run_systematic_test_final.sh --phase 5.1"
'''
        
        env_script = Path("smart_env.sh")
        with open(env_script, 'w') as f:
            f.write(env_script_content)
        
        # 设置执行权限
        env_script.chmod(0o755)
        
        logger.info("✅ 创建智能环境变量脚本: smart_env.sh")
        return True
        
    except Exception as e:
        logger.error(f"❌ 环境变量设置失败: {e}")
        return False

def create_verification_test():
    """创建验证测试脚本"""
    try:
        verify_script_content = '''#!/usr/bin/env python3
"""
验证智能数据收集器修复效果
测试新的数据收集机制是否正常工作
"""

import os
import json
import time
from pathlib import Path

def verify_environment():
    """验证环境配置"""
    print("🔍 验证环境配置...")
    
    # 检查目录
    temp_dir = Path("temp_results")
    if temp_dir.exists():
        print("  ✅ temp_results目录存在")
    else:
        print("  ❌ temp_results目录缺失")
        return False
    
    # 检查智能收集器文件
    required_files = [
        "smart_result_collector.py",
        "result_collector_adapter.py", 
        "smart_collector_config.py"
    ]
    
    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"  ❌ 缺失文件: {missing_files}")
        return False
    else:
        print("  ✅ 智能收集器文件完整")
    
    return True

def test_smart_collector():
    """测试智能收集器功能"""
    print("\\n🧪 测试智能收集器...")
    
    try:
        # 设置测试环境
        os.environ['USE_SMART_COLLECTOR'] = 'true'
        os.environ['COLLECTOR_SCALE'] = 'small'
        os.environ['NUM_TESTS'] = '3'
        
        # 导入智能收集器
        from result_collector_adapter import create_adaptive_collector
        
        # 创建收集器
        collector = create_adaptive_collector(
            max_memory_results=2,  # 小阈值测试
            max_time_seconds=10,   # 短时间测试
            adaptive_threshold=True
        )
        
        print("  ✅ 智能收集器创建成功")
        
        # 测试添加结果
        test_results = [
            {'model': 'test_model', 'success': True, 'score': 0.85},
            {'model': 'test_model', 'success': False, 'score': 0.45},
            {'model': 'test_model', 'success': True, 'score': 0.92}
        ]
        
        for i, result in enumerate(test_results):
            triggered = collector.add_result(result)
            print(f"  📊 添加测试结果 {i+1}: 触发保存={triggered}")
            time.sleep(0.5)
        
        # 强制保存剩余结果
        collector.force_save("verification_test")
        
        # 获取统计信息
        stats = collector.get_stats()
        print(f"  📈 收集器统计: {stats}")
        
        # 关闭收集器
        collector.shutdown()
        
        print("  ✅ 智能收集器测试成功")
        return True
        
    except Exception as e:
        print(f"  ❌ 智能收集器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_database_stats():
    """验证数据库统计"""
    print("\\n📊 验证数据库统计...")
    
    try:
        db_file = Path("pilot_bench_cumulative_results/master_database.json")
        if not db_file.exists():
            print("  ❌ 数据库文件不存在")
            return False
        
        with open(db_file, 'r') as f:
            db = json.load(f)
        
        # 检查models统计
        models = db.get('models', {})
        print(f"  📊 数据库中的模型: {len(models)} 个")
        
        empty_stats_count = 0
        for model_name, model_data in models.items():
            if not model_data.get('overall_stats'):
                empty_stats_count += 1
        
        if empty_stats_count > 0:
            print(f"  ⚠️ {empty_stats_count} 个模型的overall_stats为空")
        else:
            print("  ✅ 所有模型的overall_stats正常")
        
        # 检查summary
        summary = db.get('summary', {})
        total_tests = summary.get('total_tests', 0)
        if total_tests > 0:
            print(f"  ✅ summary.total_tests: {total_tests}")
        else:
            print(f"  ⚠️ summary.total_tests为0，需要更新统计")
        
        return empty_stats_count == 0 and total_tests > 0
        
    except Exception as e:
        print(f"  ❌ 数据库验证失败: {e}")
        return False

def test_configuration():
    """测试配置功能"""
    print("\\n⚙️ 测试配置功能...")
    
    try:
        from smart_collector_config import get_smart_collector_config, validate_config
        
        # 测试不同规模配置
        scales = ['small', 'medium', 'large', 'ultra']
        for scale in scales:
            config = get_smart_collector_config(scale=scale)
            issues = validate_config(config)
            if issues:
                print(f"  ❌ {scale}配置有问题: {issues}")
                return False
            else:
                print(f"  ✅ {scale}配置正常")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 配置测试失败: {e}")
        return False

def main():
    """主验证函数"""
    print("🔬 智能数据收集器修复验证")
    print("=" * 50)
    
    all_passed = True
    
    # 验证环境
    if not verify_environment():
        all_passed = False
    
    # 测试智能收集器
    if not test_smart_collector():
        all_passed = False
    
    # 验证数据库统计
    if not verify_database_stats():
        all_passed = False
    
    # 测试配置
    if not test_configuration():
        all_passed = False
    
    print("\\n" + "=" * 50)
    if all_passed:
        print("🎉 所有验证测试通过!")
        print("\\n✅ 修复成功，可以使用新的数据收集机制")
        print("\\n🎯 建议使用方式:")
        print("source ./smart_env.sh")
        print("./run_systematic_test_final.sh --phase 5.1")
    else:
        print("❌ 部分验证测试失败")
        print("\\n🔧 建议操作:")
        print("1. 检查缺失的文件")
        print("2. 运行 python3 update_summary_totals.py")
        print("3. 查看详细错误信息进行修复")

if __name__ == "__main__":
    main()
'''
        
        verify_script = Path("verify_fix.py")
        with open(verify_script, 'w') as f:
            f.write(verify_script_content)
        
        verify_script.chmod(0o755)
        
        logger.info("✅ 创建验证测试脚本: verify_fix.py")
        return True
        
    except Exception as e:
        logger.error(f"❌ 验证脚本创建失败: {e}")
        return False

if __name__ == "__main__":
    quick_fix_all()