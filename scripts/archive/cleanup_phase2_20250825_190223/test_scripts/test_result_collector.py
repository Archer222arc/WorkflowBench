#!/usr/bin/env python3
"""
ResultCollector功能验证测试
测试小规模超并发模式下的数据收集完整性
"""

import os
import sys
import time
import json
from pathlib import Path
import subprocess
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_result_collector_basic():
    """基础功能测试：验证ResultCollector的核心功能"""
    logger.info("🧪 开始ResultCollector基础功能测试")
    
    # 确保result_collector.py可以正常导入
    try:
        from result_collector import ResultCollector, ResultAggregator
        logger.info("✅ ResultCollector模块导入成功")
    except ImportError as e:
        logger.error(f"❌ ResultCollector模块导入失败: {e}")
        return False
    
    # 创建测试数据
    test_results = [
        {
            "model": "test-model-1",
            "task_type": "simple_task", 
            "prompt_type": "optimal",
            "difficulty": "easy",
            "tool_success_rate": 0.8,
            "success": True,
            "execution_time": 25.5,
            "workflow_score": 0.95
        },
        {
            "model": "test-model-1",
            "task_type": "basic_task",
            "prompt_type": "optimal", 
            "difficulty": "easy",
            "tool_success_rate": 0.8,
            "success": False,
            "execution_time": 12.3,
            "workflow_score": 0.45
        }
    ]
    
    # 测试ResultCollector
    collector = ResultCollector("test_temp_results")
    
    # 添加测试结果
    result_file = collector.add_batch_result("test-model-1", test_results, 
                                           {"test_batch": "basic_test"})
    logger.info(f"✅ 成功添加批次结果，文件: {result_file}")
    
    # 检查待处理数量
    pending = collector.get_pending_count()
    logger.info(f"📊 待处理结果文件数量: {pending}")
    
    # 收集结果
    collected = collector.collect_all_results(cleanup=False)
    logger.info(f"✅ 收集到 {len(collected)} 个批次结果")
    
    # 验证数据完整性
    if len(collected) == 1:
        batch = collected[0]
        if (batch['model'] == 'test-model-1' and 
            batch['result_count'] == 2 and
            len(batch['results']) == 2):
            logger.info("✅ 数据完整性验证通过")
        else:
            logger.error("❌ 数据完整性验证失败")
            return False
    else:
        logger.error(f"❌ 期望收集到1个批次，实际收集到{len(collected)}个")
        return False
    
    # 测试聚合器
    aggregator = ResultAggregator()
    aggregated_db = aggregator.aggregate_results(collected)
    
    if 'test-model-1' in aggregated_db['models']:
        logger.info("✅ 结果聚合验证通过")
    else:
        logger.error("❌ 结果聚合验证失败")
        return False
    
    # 清理测试文件
    collector.clear_temp_files()
    test_temp_dir = Path("test_temp_results")
    if test_temp_dir.exists():
        test_temp_dir.rmdir()
    
    logger.info("✅ ResultCollector基础功能测试完成")
    return True

def test_ultra_parallel_integration():
    """集成测试：在真实的超并发环境中测试"""
    logger.info("🧪 开始超并发集成测试")
    
    # 创建小规模测试配置
    test_env = os.environ.copy()
    test_env['USE_RESULT_COLLECTOR'] = 'true'
    test_env['STORAGE_FORMAT'] = 'json'  # 使用JSON格式便于验证
    
    # 选择一个快速的模型进行小规模测试
    test_model = "DeepSeek-V3-0324"
    
    logger.info(f"📋 准备测试配置:")
    logger.info(f"  模型: {test_model}")
    logger.info(f"  使用ResultCollector: {test_env.get('USE_RESULT_COLLECTOR')}")
    logger.info(f"  存储格式: {test_env.get('STORAGE_FORMAT')}")
    
    # 执行小规模超并发测试
    # 只测试2个实例，每个实例2个任务，总共4个任务
    cmd = [
        'python', 'ultra_parallel_runner.py',
        '--model', test_model,
        '--prompt-types', 'optimal',
        '--difficulty', 'easy', 
        '--task-types', 'simple_task,basic_task',
        '--tool-success-rate', '0.8',
        '--num-instances', '2',  # 2个实例并发
        '--max-workers', '10'  # 较少的worker避免资源占用过多
    ]
    
    logger.info(f"🚀 执行命令: {' '.join(cmd)}")
    
    try:
        # 记录开始时间
        start_time = time.time()
        
        # 执行测试（设置较短的超时，避免长时间等待）
        process = subprocess.run(
            cmd, 
            env=test_env,
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        logger.info(f"⏱️ 测试执行时间: {execution_time:.2f}秒")
        
        # 检查执行结果
        if process.returncode == 0:
            logger.info("✅ 超并发测试执行成功")
            
            # 检查是否有ResultCollector相关的日志输出
            stdout = process.stdout
            if "ResultCollector" in stdout or "已提交" in stdout or "📤" in stdout:
                logger.info("✅ 发现ResultCollector活动日志")
                # 输出相关日志片段
                lines = stdout.split('\n')
                for line in lines:
                    if any(keyword in line for keyword in ["ResultCollector", "📤", "📥", "收集器"]):
                        logger.info(f"  📝 {line}")
            else:
                logger.warning("⚠️ 未发现ResultCollector活动日志")
            
        else:
            logger.error(f"❌ 超并发测试执行失败，返回码: {process.returncode}")
            logger.error(f"STDOUT: {process.stdout}")
            logger.error(f"STDERR: {process.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("❌ 测试超时（5分钟）")
        return False
    except Exception as e:
        logger.error(f"❌ 测试执行异常: {e}")
        return False
    
    # 检查temp_results目录
    temp_results_dir = Path("temp_results")
    if temp_results_dir.exists():
        temp_files = list(temp_results_dir.glob("*.json"))
        logger.info(f"📁 发现 {len(temp_files)} 个临时结果文件")
        
        if len(temp_files) > 0:
            logger.info("✅ ResultCollector正常工作，生成了临时结果文件")
            # 清理临时文件
            for temp_file in temp_files:
                temp_file.unlink()
            if not any(temp_results_dir.iterdir()):
                temp_results_dir.rmdir()
        else:
            logger.warning("⚠️ 没有发现临时结果文件，可能使用了传统模式")
    else:
        logger.warning("⚠️ 没有发现temp_results目录")
    
    # 检查最终数据库
    db_path = Path("pilot_bench_cumulative_results/master_database.json")
    if db_path.exists():
        try:
            with open(db_path, 'r') as f:
                db = json.load(f)
            
            if test_model in db.get('models', {}):
                model_data = db['models'][test_model]
                total_tests = model_data.get('total_tests', 0)
                logger.info(f"✅ 在数据库中找到 {test_model}，总测试数: {total_tests}")
                
                if total_tests > 0:
                    logger.info("✅ 数据保存验证通过")
                else:
                    logger.warning("⚠️ 模型数据存在但测试数为0")
            else:
                logger.warning(f"⚠️ 在数据库中未找到 {test_model}")
                
        except Exception as e:
            logger.error(f"❌ 读取数据库失败: {e}")
    else:
        logger.warning("⚠️ 数据库文件不存在")
    
    logger.info("✅ 超并发集成测试完成")
    return True

def main():
    """主测试函数"""
    logger.info("🎯 ResultCollector功能验证测试开始")
    logger.info("=" * 60)
    
    # 基础功能测试
    logger.info("\n📋 阶段1: 基础功能测试")
    basic_test_passed = test_result_collector_basic()
    
    if not basic_test_passed:
        logger.error("❌ 基础功能测试失败，跳过后续测试")
        return False
    
    # 集成测试
    logger.info("\n📋 阶段2: 超并发集成测试")
    integration_test_passed = test_ultra_parallel_integration()
    
    # 总结
    logger.info("\n" + "=" * 60)
    if basic_test_passed and integration_test_passed:
        logger.info("🎉 所有测试通过！ResultCollector可以正常使用")
        logger.info("💡 建议：可以在生产环境中启用ResultCollector")
        logger.info("📝 使用方法：export USE_RESULT_COLLECTOR=true")
        return True
    else:
        logger.error("❌ 部分测试失败，需要进一步调试")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)