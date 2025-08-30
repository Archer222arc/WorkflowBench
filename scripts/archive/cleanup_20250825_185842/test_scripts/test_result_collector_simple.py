#!/usr/bin/env python3
"""
ResultCollector简单验证测试
直接测试smart_batch_runner的ResultCollector集成
"""

import os
import sys
import json
import logging
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_smart_batch_runner_integration():
    """测试smart_batch_runner与ResultCollector的集成"""
    logger.info("🧪 测试smart_batch_runner与ResultCollector集成")
    
    # 设置环境变量
    os.environ['USE_RESULT_COLLECTOR'] = 'true'
    os.environ['STORAGE_FORMAT'] = 'json'
    
    try:
        # 导入必要模块
        sys.path.insert(0, '/Users/ruicheng/Documents/GitHub/WorkflowBench')
        from smart_batch_runner import run_batch_test_smart
        from result_collector import ResultCollector
        
        logger.info("✅ 模块导入成功")
        
        # 执行一个非常小的测试
        logger.info("🚀 开始小规模批次测试")
        
        # 创建ResultCollector实例验证其工作状态
        collector = ResultCollector()
        initial_count = collector.get_pending_count()
        logger.info(f"📊 测试前待处理文件数: {initial_count}")
        
        # 运行小规模测试（只测试1个实例）
        # 使用一个没有数据的配置来确保会执行测试
        result = run_batch_test_smart(
            model="DeepSeek-V3-0324",
            prompt_types="baseline",  # 使用baseline提示类型（可能没有数据）
            difficulty="medium",  # 使用medium难度（可能没有数据）
            task_types="basic_task",  # 使用basic_task（可能没有数据）
            num_instances=1,  # 只测试1个实例
            tool_success_rate=0.7,  # 使用不同的工具成功率
            use_result_collector=True  # 明确启用ResultCollector
        )
        
        logger.info(f"✅ 批次测试完成，结果: {result}")
        
        # 检查ResultCollector是否收到了结果
        final_count = collector.get_pending_count()
        logger.info(f"📊 测试后待处理文件数: {final_count}")
        
        if final_count > initial_count:
            logger.info("✅ ResultCollector成功接收到测试结果")
            
            # 收集并显示结果
            collected_results = collector.collect_all_results(cleanup=False)
            logger.info(f"📥 收集到 {len(collected_results)} 个结果批次")
            
            for i, batch in enumerate(collected_results):
                model = batch.get('model', 'unknown')
                count = batch.get('result_count', 0)
                logger.info(f"  批次 {i+1}: {model} - {count} 个结果")
            
            return True
        else:
            logger.warning("⚠️ ResultCollector未接收到新的结果，可能使用了传统模式")
            return False
            
    except ImportError as e:
        logger.error(f"❌ 模块导入失败: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ 测试执行异常: {e}")
        return False

def test_environment_detection():
    """测试环境变量检测机制"""
    logger.info("🧪 测试环境变量检测机制")
    
    try:
        # 导入ultra_parallel_runner验证环境变量检测
        from ultra_parallel_runner import UltraParallelRunner
        
        # 测试不同的环境变量配置
        test_cases = [
            {'USE_RESULT_COLLECTOR': 'true', 'expected': True},
            {'USE_RESULT_COLLECTOR': 'false', 'expected': False},
            {'USE_RESULT_COLLECTOR': '', 'expected': False},
        ]
        
        for case in test_cases:
            # 设置环境变量
            os.environ['USE_RESULT_COLLECTOR'] = case['USE_RESULT_COLLECTOR']
            
            # 创建实例（使用默认参数，应该从环境变量检测）
            runner = UltraParallelRunner()
            
            # 检查是否按预期检测
            detected = hasattr(runner, 'use_collector_mode') and runner.use_collector_mode
            expected = case['expected']
            
            if detected == expected:
                logger.info(f"✅ 环境变量 '{case['USE_RESULT_COLLECTOR']}' -> {detected} (预期: {expected})")
            else:
                logger.error(f"❌ 环境变量 '{case['USE_RESULT_COLLECTOR']}' -> {detected} (预期: {expected})")
                return False
        
        logger.info("✅ 环境变量检测机制工作正常")
        return True
        
    except Exception as e:
        logger.error(f"❌ 环境变量检测测试失败: {e}")
        return False

def main():
    """主测试函数"""
    logger.info("🎯 ResultCollector简单验证测试开始")
    logger.info("=" * 50)
    
    # 基础环境检测测试
    logger.info("\n📋 阶段1: 环境变量检测测试")
    env_test_passed = test_environment_detection()
    
    # smart_batch_runner集成测试
    logger.info("\n📋 阶段2: smart_batch_runner集成测试")
    integration_test_passed = test_smart_batch_runner_integration()
    
    # 总结
    logger.info("\n" + "=" * 50)
    if env_test_passed and integration_test_passed:
        logger.info("🎉 所有简单验证测试通过！")
        logger.info("✅ ResultCollector基本功能正常")
        logger.info("✅ 环境变量检测机制正常")
        logger.info("✅ smart_batch_runner集成正常")
        logger.info("💡 可以继续进行完整的超并发测试")
        return True
    else:
        logger.error("❌ 部分测试失败")
        if not env_test_passed:
            logger.error("  - 环境变量检测问题")
        if not integration_test_passed:
            logger.error("  - smart_batch_runner集成问题")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)